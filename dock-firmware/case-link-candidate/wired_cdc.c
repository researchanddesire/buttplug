#include "wired_cdc.h"
#include <string.h>

static const char prefix[] = "case-v1 ";
static const char digits[] = "0123456789abcdef";
enum { PREFIX_BYTES = sizeof(prefix) - 1u, NONCE_OFFSET = 10, REQUEST_OFFSET = 19, PAYLOAD_OFFSET = 24 };

_Static_assert(WIRED_CDC_REQUEST_BYTES == PREFIX_BYTES + 2u * CL_WIRE_BYTES + 1u,
               "wire request length");
_Static_assert(WIRED_CDC_RESPONSE_BYTES == PAYLOAD_OFFSET + 2u * CL_WIRE_BYTES + 1u,
               "wire response length");

static bool decode_hex(const char *text, size_t length, uint32_t *value)
{
    uint32_t result = 0;
    for (size_t i = 0; i < length; ++i) {
        char c = text[i];
        unsigned digit;
        if (c >= '0' && c <= '9') digit = (unsigned)(c - '0');
        else if (c >= 'a' && c <= 'f') digit = (unsigned)(c - 'a' + 10);
        else if (c >= 'A' && c <= 'F') digit = (unsigned)(c - 'A' + 10);
        else return false;
        result = (result << 4) | digit;
    }
    *value = result;
    return true;
}

static void clear_input(wired_cdc *transport)
{
    transport->line_length = 0;
    transport->record_count = 0;
    transport->discard_line = false;
}

uint32_t wired_cdc_connect(wired_cdc *transport, case_link *link, uint64_t now_ms)
{
    memset(transport, 0, sizeof(*transport));
    transport->link = link;
    transport->epoch = case_link_connect(link, now_ms);
    return transport->epoch;
}

void wired_cdc_disconnect(wired_cdc *transport, uint64_t now_ms)
{
    if (transport->epoch) case_link_disconnect(transport->link, now_ms);
    transport->epoch = 0;
    clear_input(transport);
#ifdef COMPASS_WIRED_MAIN
    transport->replay.available = false;
#endif
}

bool wired_cdc_poll(wired_cdc *transport, uint64_t now_ms)
{
    if (!transport->epoch) return false;
    bool pending = transport->link->pending.active;
    if (case_link_poll(transport->link, now_ms) && (!pending || transport->link->pending.active)) return true;
    wired_cdc_disconnect(transport, now_ms);
    return false;
}

bool wired_cdc_request(wired_cdc *transport, uint8_t opcode, uint32_t argument,
                       uint64_t now_ms, char out[WIRED_CDC_REQUEST_BYTES])
{
    uint8_t packet[CL_WIRE_BYTES];
    if (!wired_cdc_poll(transport, now_ms) ||
        !case_link_command(transport->link, opcode, argument, 0, now_ms, packet)) return false;
    transport->record_count = 0;
    memcpy(out, prefix, PREFIX_BYTES);
    for (size_t i = 0; i < CL_WIRE_BYTES; ++i) {
        out[PREFIX_BYTES + 2u * i] = digits[packet[i] >> 4];
        out[PREFIX_BYTES + 2u * i + 1u] = digits[packet[i] & 15u];
    }
    out[WIRED_CDC_REQUEST_BYTES - 1u] = '\n';
    return true;
}

#ifdef COMPASS_WIRED_MAIN
uint8_t wired_cdc_next_request(const wired_cdc *transport, uint32_t *argument)
{
    const case_link *link = transport->link;
    *argument = 0;
    if (!link->snapshot_seen) return 1;
    if (!link->anchor.valid) return 2;
    if (transport->observed_loss.kind == CL_SOURCE && !transport->replay_attempted) {
        *argument = transport->observed_loss.sequence;
        return 4;
    }
    return 1;
}
#endif

static bool complete_shape(const wired_cdc *transport, const cl_frame *result)
{
    static const cl_kind snapshot[] = {CL_THERMAL, CL_CHARGE, CL_SOURCE, CL_FIRST_VALID};
    size_t count = transport->record_count;
    if (result->data.result.result || transport->link->pending.opcode == 2) return count == 0;
    if (transport->link->pending.opcode == 1) {
        if (count != sizeof(snapshot) / sizeof(snapshot[0])) return false;
        for (size_t i = 0; i < count; ++i)
            if (transport->records[i].kind != snapshot[i]) return false;
        return true;
    }
    if (count < 2 || transport->records[count - 2].kind != CL_SOURCE ||
        transport->records[count - 1].kind != CL_FIRST_VALID) return false;
    for (size_t i = 0; i < count - 2; ++i)
        if (transport->records[i].kind != CL_THERMAL) return false;
    return true;
}

static bool decode_record(const wired_cdc *transport, size_t index, uint32_t boot_id, cl_frame *record)
{
    return case_link_decode(transport->records[index].kind, transport->records[index].payload,
                            CL_WIRE_BYTES, record) != CL_REJECTED && record->boot_id == boot_id;
}

static bool matching_loss_sample(const cl_frame *sample, const cl_frame *event)
{
    enum { completed = 1u, source_at_start = 4u, source_at_end = 8u,
           source_changed = 16u, followed_loss = 64u };
    uint8_t mask = completed | source_at_start | source_at_end | source_changed | followed_loss;
    return (sample->data.thermal.flags & mask) == (completed | followed_loss) &&
           sample->data.thermal.started == event->data.event.started &&
           sample->data.thermal.completed == event->data.event.completed;
}

static bool complete_replay(const wired_cdc *transport, const cl_frame *result)
{
    size_t count = transport->record_count;
    if (transport->link->pending.opcode < 3 || result->data.result.result) return true;
    cl_frame source, valid;
    if (!decode_record(transport, count - 2u, result->boot_id, &source) ||
        !decode_record(transport, count - 1u, result->boot_id, &valid) ||
        !(source.data.event.flags & 1u) || source.sequence != valid.sequence ||
        source.data.event.loss != valid.data.event.loss) return false;
    bool first_attempt = !(source.data.event.flags & 8u);
    bool first_valid = !(valid.data.event.flags & 1u);
    for (size_t i = 0; i < count - 2u; ++i) {
        cl_frame sample;
        if (!decode_record(transport, i, result->boot_id, &sample)) return false;
        bool match = matching_loss_sample(&sample, &source);
#ifdef COMPASS_WIRED_MAIN
        if (transport->link->pending.opcode == 4)
            match = match && ((sample.data.thermal.flags & 2u) != 0) ==
                             ((source.data.event.flags & 16u) != 0);
#endif
        first_attempt |= match;
        first_valid |= matching_loss_sample(&sample, &valid) &&
                       (sample.data.thermal.flags & 2u) != 0;
    }
    return first_attempt && first_valid;
}

#ifdef COMPASS_WIRED_MAIN
static bool store_replay(wired_cdc *transport, const cl_frame *result)
{
    const cl_frame *observed = &transport->observed_loss;
    size_t count = transport->record_count - 2u;
    cl_frame source, valid;
    if (!decode_record(transport, count, result->boot_id, &source) ||
        !decode_record(transport, count + 1u, result->boot_id, &valid) ||
        observed->kind != CL_SOURCE || observed->boot_id != source.boot_id ||
        observed->sequence != source.sequence ||
        observed->data.event.loss != source.data.event.loss) return false;
    bool docked_seen = false;
    for (size_t i = 0; i < count; ++i) {
        cl_frame sample;
        if (!decode_record(transport, i, result->boot_id, &sample)) return false;
        uint8_t flags = sample.data.thermal.flags;
        uint32_t started = sample.data.thermal.started;
        uint32_t completed = sample.data.thermal.completed;
        uint32_t loss = source.data.event.loss;
        if (!(flags & 1u) || completed - started > transport->link->policy.max_attempt_ms) return false;
        if (((source.data.event.flags & 8u) && matching_loss_sample(&sample, &source)) ||
            ((valid.data.event.flags & 1u) && matching_loss_sample(&sample, &valid))) {
            if (started - loss >= UINT32_C(0x80000000)) return false;
        } else {
            if (docked_seen || i != 0 || (flags & 127u) != 15u ||
                loss - completed >= UINT32_C(0x80000000)) return false;
            docked_seen = true;
        }
        transport->replay.samples[i] = sample;
    }
    transport->replay.source = source;
    transport->replay.first_valid = valid;
    transport->replay.sample_count = count;
    transport->replay.available = true;
    return true;
}
#endif

static wired_cdc_result commit_batch(wired_cdc *transport, const cl_frame *result,
                                      const uint8_t payload[CL_WIRE_BYTES], uint64_t now_ms)
{
    case_link *link = transport->link;
    if (result->sequence != link->pending.id ||
        result->data.result.session_id_echo != link->case_session_id ||
        !complete_shape(transport, result) || !complete_replay(transport, result))
        return WIRED_CDC_FAILED;

    bool matching_boot = !link->pending.boot_known || link->pending.boot_id == result->boot_id;
#ifdef COMPASS_WIRED_MAIN
    uint8_t opcode = link->pending.opcode;
    cl_frame observed_loss = {0};
    if (opcode == 4 && matching_boot) {
        cl_receive status = case_link_feed(link, transport->epoch, CL_RESULT, payload, CL_WIRE_BYTES, now_ms);
        if (status != CL_ACCEPTED || !link->have_result) return WIRED_CDC_FAILED;
        transport->replay_attempted = true;
        transport->replay.available = false;
        if (!result->data.result.result && !store_replay(transport, result)) return WIRED_CDC_FAILED;
        return WIRED_CDC_COMPLETE;
    }
#endif
    if (matching_boot) {
        bool have_source_event = false;
        for (size_t i = 0; i < transport->record_count; ++i) {
            cl_kind kind = transport->records[i].kind;
            const uint8_t *data = transport->records[i].payload;
            cl_frame decoded;
            if (!decode_record(transport, i, result->boot_id, &decoded)) return WIRED_CDC_FAILED;
#ifdef COMPASS_WIRED_MAIN
            if (opcode == 1 && kind == CL_SOURCE) {
                if (decoded.data.event.flags & 1u) observed_loss = decoded;
                continue;
            }
            if (opcode == 1 && kind == CL_FIRST_VALID) continue;
#endif
            if (kind == CL_THERMAL && !decoded.data.thermal.flags) continue;
            if (kind == CL_CHARGE && decoded.data.charge.validity == 1024u &&
                !decoded.sequence && !decoded.data.charge.completed && !link->charge_order.known) continue;
            if (kind == CL_SOURCE) have_source_event = (decoded.data.event.flags & 1u) != 0;
            if (kind == CL_FIRST_VALID && !have_source_event) continue;

            cl_receive status = kind == CL_THERMAL || kind == CL_CHARGE
                ? case_link_feed_polled_sample(link, transport->epoch, kind, data, CL_WIRE_BYTES, now_ms)
                : case_link_feed(link, transport->epoch, kind, data, CL_WIRE_BYTES, now_ms);
            if (status == CL_REJECTED || status == CL_RESYNC) return WIRED_CDC_FAILED;
        }
    }
    cl_receive status = case_link_feed(link, transport->epoch, CL_RESULT, payload, CL_WIRE_BYTES, now_ms);
    if (status != CL_ACCEPTED || !link->have_result) return WIRED_CDC_FAILED;
#ifdef COMPASS_WIRED_MAIN
    if (opcode == 1 && !result->data.result.result) {
        const cl_frame *previous = &transport->observed_loss;
        if (previous->kind != observed_loss.kind || previous->boot_id != observed_loss.boot_id ||
            previous->sequence != observed_loss.sequence ||
            previous->data.event.loss != observed_loss.data.event.loss ||
            previous->data.event.flags != observed_loss.data.event.flags) {
            transport->replay_attempted = false;
            transport->replay.available = false;
        }
        transport->observed_loss = observed_loss;
    }
#endif
    return WIRED_CDC_COMPLETE;
}

static wired_cdc_result read_line(wired_cdc *transport, uint64_t now_ms)
{
    const char *line = transport->line;
    case_link *link = transport->link;
    size_t length = transport->line_length;
    if (length < PREFIX_BYTES || memcmp(line, prefix, PREFIX_BYTES) || !link->pending.active)
        return WIRED_CDC_WAITING;

    uint32_t nonce, request;
    if (length != WIRED_CDC_RESPONSE_BYTES - 1u || line[9] != ' ' ||
        line[18] != ' ' || line[23] != ' ' ||
        !decode_hex(line + NONCE_OFFSET, 8, &nonce) ||
        !decode_hex(line + REQUEST_OFFSET, 4, &request)) return WIRED_CDC_FAILED;
    if (nonce != link->case_session_id || request != link->pending.id) return WIRED_CDC_WAITING;

    cl_kind kind = (cl_kind)(line[8] - '0');
    if (kind < CL_THERMAL || kind > CL_FIRST_VALID || kind == CL_COMMAND) return WIRED_CDC_FAILED;
    uint8_t payload[CL_WIRE_BYTES];
    for (size_t i = 0; i < CL_WIRE_BYTES; ++i) {
        uint32_t value;
        if (!decode_hex(line + PAYLOAD_OFFSET + 2u * i, 2, &value)) return WIRED_CDC_FAILED;
        payload[i] = (uint8_t)value;
    }
    if (kind == CL_RESULT) {
        cl_frame result;
        if (case_link_decode(kind, payload, sizeof(payload), &result) != CL_ACCEPTED)
            return WIRED_CDC_FAILED;
        return commit_batch(transport, &result, payload, now_ms);
    }
    if (transport->record_count == WIRED_CDC_BATCH_RECORDS) return WIRED_CDC_FAILED;
    size_t index = transport->record_count++;
    transport->records[index].kind = kind;
    memcpy(transport->records[index].payload, payload, sizeof(payload));
    return WIRED_CDC_WAITING;
}

wired_cdc_result wired_cdc_receive(wired_cdc *transport, uint32_t epoch,
                                   const uint8_t *bytes, size_t length, uint64_t now_ms)
{
    if (!epoch || epoch != transport->epoch) return WIRED_CDC_WAITING;
    if (!wired_cdc_poll(transport, now_ms)) return WIRED_CDC_FAILED;
    wired_cdc_result outcome = WIRED_CDC_WAITING;
    for (size_t i = 0; i < length; ++i) {
        char c = (char)bytes[i];
        if (c == '\r' || c == '\n') {
            if (!transport->discard_line && transport->line_length) {
                wired_cdc_result status = read_line(transport, now_ms);
                if (status == WIRED_CDC_FAILED) {
                    wired_cdc_disconnect(transport, now_ms);
                    return status;
                }
                if (status == WIRED_CDC_COMPLETE) {
                    outcome = status;
                    transport->record_count = 0;
                }
            }
            transport->discard_line = false;
            transport->line_length = 0;
        } else if (!transport->discard_line) {
            if (transport->line_length == sizeof(transport->line)) transport->discard_line = true;
            else transport->line[transport->line_length++] = c;
        }
    }
    return outcome;
}
