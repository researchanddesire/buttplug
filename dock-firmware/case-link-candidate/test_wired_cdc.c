#include "wired_cdc.h"
#include "case_telemetry.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static case_link link_state;
static wired_cdc transport;
static thermal_history_t history;
static ct_session_t sender;
static uint32_t epoch;
static const cl_policy policy = {
    .thermal_fresh_ms = 1500, .ratio_fresh_ms = 1500,
    .charge_fresh_ms = {2000, 2000, 2000, 2000, 2000, 2000},
    .max_attempt_ms = 500, .max_gap_ms = 10000,
    .max_anchor_age_ms = 60000, .max_round_trip_ms = 1000,
    .combined_clock_drift_ppm = 1000, .combined_timer_resolution_ms = 2,
    .max_sequence_advance = 4,
};

static size_t line_for(char line[80], const ct_packet_t *packet, uint32_t session, uint16_t request)
{
    int position = snprintf(line, 80, "case-v1 %u %08x %04x ", packet->kind, session, request);
    assert(position == 24);
    for (size_t i = 0; i < CT_WIRE_BYTES; ++i)
        position += snprintf(line + position, 80u - (size_t)position, "%02x", packet->data[i]);
    line[position++] = '\r';
    line[position++] = '\n';
    return (size_t)position;
}

static wired_cdc_result frame(const ct_packet_t *packet, const ct_command_t *command, uint64_t now)
{
    char line[80];
    size_t count = line_for(line, packet, command->session_id, command->request_id);
    assert(wired_cdc_receive(&transport, epoch, (uint8_t *)line, 9, now) == WIRED_CDC_WAITING);
    return wired_cdc_receive(&transport, epoch, (uint8_t *)line + 9, count - 9, now);
}

static ct_command_t request_arg(uint8_t opcode, uint32_t argument, uint64_t now,
                                const ct_charge_t *charge, ct_reply_t *response)
{
    char line[WIRED_CDC_REQUEST_BYTES];
    assert(wired_cdc_request(&transport, opcode, argument, now, line));
    assert(!memcmp(line, "case-v1 ", 8) && line[sizeof(line) - 1u] == '\n');
    uint8_t bytes[20];
    for (size_t i = 0; i < sizeof(bytes); ++i) {
        unsigned value;
        char pair[] = {line[8 + i * 2u], line[9 + i * 2u], 0};
        assert(sscanf(pair, "%2x", &value) == 1);
        bytes[i] = (uint8_t)value;
    }
    ct_command_t cmd;
    assert(ct_parse_command(bytes, sizeof(bytes), &cmd));
    assert(cmd.opcode == opcode && cmd.argument0 == argument &&
           cmd.case_ms == now && cmd.session_id == link_state.case_session_id);
    assert(ct_execute(&sender, &history, charge, bytes, sizeof(bytes), now + 5002, now + 5004, response));
    return cmd;
}

static ct_command_t request(uint8_t opcode, uint64_t now, const ct_charge_t *charge, ct_reply_t *response)
{
    return request_arg(opcode, 0, now, charge, response);
}

static void reply(const ct_reply_t *response, const ct_command_t *command, uint64_t now)
{
    assert(response->count > 0);
    for (size_t i = 0; i + 1 < response->count; ++i) {
        assert(frame(&response->frames[i], command, now) == WIRED_CDC_WAITING);
        assert(link_state.pending.active);
    }
    assert(frame(&response->frames[response->count - 1], command, now) == WIRED_CDC_COMPLETE);
    assert(!link_state.pending.active);
}

static void sample(uint32_t sequence, uint64_t now, int32_t temperature)
{
    thermal_sample_t value = {.sequence = sequence, .started_ms = now - 20, .sampled_ms = now,
                              .tip_millic = temperature, .valid = true,
                              .source_at_start = true, .source_at_end = true};
    assert(thermal_history_sample(&history, value, now));
}

#ifdef COMPASS_WIRED_MAIN
static void product_reconnect_replay(void)
{
    thermal_history_init(&history, 77);
    thermal_history_source(&history, true, 5000);
    ct_session_init(&sender);
    assert(case_link_init(&link_state, 0x01234567, &policy, 100));
    epoch = wired_cdc_connect(&transport, &link_state, 100);
    sample(10, 5400, 33000);
    ct_reply_t response;
    ct_command_t command = request(1, 410, NULL, &response);
    reply(&response, &command, 420);
    command = request(2, 425, NULL, &response);
    reply(&response, &command, 435);
    uint32_t argument;
    assert(wired_cdc_next_request(&transport, &argument) == 1);
    wired_cdc_disconnect(&transport, 440);

    thermal_history_source(&history, false, 5440);
    thermal_sample_t lost = {.sequence = 11, .started_ms = 5450, .sampled_ms = 5470,
                              .loss_sequence_at_start = history.event_sequence};
    assert(thermal_history_sample(&history, lost, 5470));
    lost.sequence++;
    lost.started_ms = 5500;
    lost.sampled_ms = 5520;
    lost.valid = true;
    lost.tip_millic = 32000;
    assert(thermal_history_sample(&history, lost, 5520));
    thermal_history_source(&history, true, 25000);
    sample(31, 25400, 36000);

    epoch = wired_cdc_connect(&transport, &link_state, 20400);
    assert(wired_cdc_next_request(&transport, &argument) == 1);
    command = request(1, 20410, NULL, &response);
    reply(&response, &command, 20420);
    assert(wired_cdc_next_request(&transport, &argument) == 2);
    command = request(2, 20425, NULL, &response);
    reply(&response, &command, 20435);
    assert(wired_cdc_next_request(&transport, &argument) == 4 && argument == history.event_sequence);
    command = request_arg(4, argument, 20440, NULL, &response);
    assert(response.count == 6);
    reply(&response, &command, 20450);
    assert(transport.replay.available && transport.replay.sample_count == 3);
    assert(transport.replay.source.data.event.loss == 5440);
    assert(transport.replay.source.data.event.completed == 5470);
    assert(transport.replay.first_valid.data.event.completed == 5520);
    assert(transport.replay.samples[0].data.thermal.centi_c == 3300);
    assert(!(transport.replay.samples[1].data.thermal.flags & 2u));
    assert(transport.replay.samples[2].data.thermal.centi_c == 3200);
    assert(case_link_temperature(&link_state, 20450).value == 3600);
    assert(link_state.anchor.valid && link_state.thermal_order.newest == 31);
    assert(wired_cdc_next_request(&transport, &argument) == 1);

    /* A rapid redock before conversion remains an interrupted source loss.
     * It must neither retain the previous event nor invent an after-sample. */
    thermal_history_source(&history, false, 25500);
    thermal_history_source(&history, true, 25501);
    command = request(1, 20510, NULL, &response);
    reply(&response, &command, 20520);
    assert(!transport.replay.available);
    assert(wired_cdc_next_request(&transport, &argument) == 4 && argument == history.event_sequence);
    command = request_arg(4, argument, 20530, NULL, &response);
    reply(&response, &command, 20540);
    assert(transport.replay.available && transport.replay.sample_count == 1);
    assert(transport.replay.source.data.event.flags & 2u);
    assert(!(transport.replay.first_valid.data.event.flags & 1u));

    /* A coherent batch for a different event cannot replace the snapshot's
     * observed identity, even with the same plug boot and request nonce. */
    command = request_arg(4, (uint16_t)(history.event_sequence - 1u), 20545, NULL, &response);
    for (size_t i = 0; i + 1u < response.count; ++i)
        assert(frame(&response.frames[i], &command, 20550) == WIRED_CDC_WAITING);
    assert(frame(&response.frames[response.count - 1u], &command, 20551) == WIRED_CDC_FAILED);
    assert(!transport.replay.available);
    thermal_history_init(&history, 78);
    epoch = wired_cdc_connect(&transport, &link_state, 20560);
    command = request(1, 20570, NULL, &response);
    reply(&response, &command, 20580);
    command = request(2, 20590, NULL, &response);
    reply(&response, &command, 20600);
    assert(wired_cdc_next_request(&transport, &argument) == 1);
    assert(!transport.replay.available);
    assert(case_link_temperature(&link_state, 20600).quality == CL_UNKNOWN);
}
#endif

static void verify_console_capture(const char *path)
{
    FILE *stream = fopen(path, "rb");
    assert(stream);
    assert(case_link_init(&link_state, 0x00112233, &policy, 1000));
    link_state.next_request_id = 0x7a;
    epoch = wired_cdc_connect(&transport, &link_state, 1000);
    char request_line[WIRED_CDC_REQUEST_BYTES];
    assert(wired_cdc_request(&transport, 1, 0, 1000, request_line));
    bool snapshot = false, anchor = false;
    int c;
    while ((c = fgetc(stream)) != EOF) {
        uint8_t byte = (uint8_t)c;
        wired_cdc_result result = wired_cdc_receive(&transport, epoch, &byte, 1, snapshot ? 1060 : 1010);
        assert(result != WIRED_CDC_FAILED);
        if (result != WIRED_CDC_COMPLETE) continue;
        if (!snapshot) {
            assert(link_state.snapshot_seen && link_state.boot_id == 123);
            assert(wired_cdc_request(&transport, 2, 0, 1050, request_line));
            snapshot = true;
        } else {
            assert(!anchor && link_state.anchor.valid);
            anchor = true;
        }
    }
    assert(!ferror(stream) && snapshot && anchor);
    assert(fclose(stream) == 0);
    assert(case_link_temperature(&link_state, 1060).quality == CL_UNKNOWN);
}

int main(int argc, char **argv)
{
    thermal_history_init(&history, 77);
    thermal_history_source(&history, true, 5000);
    ct_session_init(&sender);
    assert(case_link_init(&link_state, 0x01234567, &policy, 100));
    epoch = wired_cdc_connect(&transport, &link_state, 100);
    assert(epoch);
    ct_reply_t response;
    ct_command_t command = request(1, 110, NULL, &response);
    assert(response.count == 5);
    char noise[80];
    memset(noise, 'x', sizeof(noise));
    noise[sizeof(noise) - 1u] = '\n';
    assert(wired_cdc_receive(&transport, epoch, (uint8_t *)noise, sizeof(noise), 115) == WIRED_CDC_WAITING);
    ct_command_t wrong = command;
    ++wrong.session_id;
    assert(frame(&response.frames[0], &wrong, 116) == WIRED_CDC_WAITING);
    assert(transport.record_count == 0);
    assert(frame(&response.frames[0], &command, 117) == WIRED_CDC_WAITING);
    assert(!link_state.boot_known && !link_state.snapshot_seen);
    for (size_t i = 1; i + 1 < response.count; ++i)
        assert(frame(&response.frames[i], &command, 118) == WIRED_CDC_WAITING);
    assert(frame(&response.frames[response.count - 1], &command, 119) == WIRED_CDC_COMPLETE);
    command = request(2, 120, NULL, &response);
    reply(&response, &command, 130);
    assert(link_state.anchor.valid);

    sample(1, 5400, 33000);
    ct_charge_t charge = {.acquired = true, .sequence = 1, .validity = CT_VBAT_VALID,
                          .vbat_mv = 4000, .completed_ms = 5400};
    command = request(1, 410, &charge, &response);
    reply(&response, &command, 420);
    sample(11, 6400, 34500);
    charge.sequence = 11;
    charge.completed_ms = 6400;
    command = request(1, 1410, &charge, &response);
    reply(&response, &command, 1420);
    cl_value temperature = case_link_temperature(&link_state, 1420);
    assert(link_state.anchor.valid && !link_state.history_continuous && link_state.missing_sequences == 18);
    assert(temperature.quality == CL_FRESH && temperature.value == 3450);
    assert(case_link_charge(&link_state, CL_VBAT, 1420).value == 4000);

    command = request(3, 1425, NULL, &response);
    assert(response.count == 1 && response.frames[0].data[1] == CT_HISTORY_UNAVAILABLE);
    reply(&response, &command, 1435);

    thermal_history_source(&history, false, 6440);
    thermal_sample_t lost = {.sequence = 12, .started_ms = 6441, .sampled_ms = 6450,
                              .loss_sequence_at_start = history.event_sequence,
                              .valid = true, .tip_millic = 34000};
    assert(thermal_history_sample(&history, lost, 6450));
    command = request(3, 1460, NULL, &response);
    assert(response.count == 5);
    reply(&response, &command, 1470);
    cl_event_view event;
    assert(case_link_event(&link_state, history.event_sequence, &event));
    assert(event.first_valid_matched && event.source_attempt_matched);

    command = request(3, 1480, NULL, &response);
    for (size_t i = 2; i + 1 < response.count; ++i)
        assert(frame(&response.frames[i], &command, 1485) == WIRED_CDC_WAITING);
    assert(frame(&response.frames[response.count - 1], &command, 1486) == WIRED_CDC_FAILED);
    assert(!transport.epoch && !link_state.connected);

    epoch = wired_cdc_connect(&transport, &link_state, 1490);
    command = request(1, 1500, &charge, &response);
    assert(frame(&response.frames[0], &command, 1510) == WIRED_CDC_WAITING);
    assert(frame(&response.frames[response.count - 1], &command, 1511) == WIRED_CDC_FAILED);
    assert(!transport.epoch && !link_state.connected);

    uint32_t old_epoch = epoch;
    epoch = wired_cdc_connect(&transport, &link_state, 1520);
    assert(epoch && epoch != old_epoch);
    command = request(1, 1530, &charge, &response);
    size_t bytes = line_for(noise, &response.frames[0], command.session_id, command.request_id);
    assert(wired_cdc_receive(&transport, old_epoch, (uint8_t *)noise, bytes, 1540) == WIRED_CDC_WAITING);
    assert(transport.record_count == 0);
    assert(!wired_cdc_poll(&transport, 2531) && !link_state.connected);
    assert(case_link_temperature(&link_state, 2531).quality == CL_UNKNOWN);

    old_epoch = epoch;
    epoch = wired_cdc_connect(&transport, &link_state, 2781);
    assert(epoch && epoch != old_epoch);
    ct_command_t abandoned = command;
    command = request(1, 2790, &charge, &response);
    assert(command.request_id == abandoned.request_id + 1u);
    bytes = line_for(noise, &response.frames[0], abandoned.session_id, abandoned.request_id);
    assert(wired_cdc_receive(&transport, epoch, (uint8_t *)noise, bytes, 2800) == WIRED_CDC_WAITING);
    assert(transport.record_count == 0 && link_state.pending.id == command.request_id);
    reply(&response, &command, 2801);
    command = request(2, 2810, NULL, &response);
    reply(&response, &command, 2820);
    assert(link_state.anchor.valid);

    link_state.next_request_id = UINT16_MAX;
    command = request(1, 2830, &charge, &response);
    assert(command.request_id == UINT16_MAX);
    reply(&response, &command, 2840);
    char line[WIRED_CDC_REQUEST_BYTES];
    assert(!wired_cdc_request(&transport, 1, 0, 2850, line));
    wired_cdc_disconnect(&transport, 2850);
    uint32_t old_session = command.session_id;
    assert(!case_link_new_session(&link_state, old_session, 3100));
    assert(case_link_new_session(&link_state, old_session + 1u, 3100));
    epoch = wired_cdc_connect(&transport, &link_state, 3100);
    assert(epoch);
    command = request(1, 3110, &charge, &response);
    assert(command.request_id == 0 && command.session_id == old_session + 1u);
    bytes = line_for(noise, &response.frames[0], old_session, command.request_id);
    assert(wired_cdc_receive(&transport, epoch, (uint8_t *)noise, bytes, 3115) == WIRED_CDC_WAITING);
    assert(transport.record_count == 0 && link_state.pending.active);
    reply(&response, &command, 3120);

    assert(argc == 1 || argc == 2);
    if (argc == 2) verify_console_capture(argv[1]);
#ifdef COMPASS_WIRED_MAIN
    product_reconnect_replay();
#endif
    puts("Wired CDC roundtrip passed: tagged batches, timing anchor, sampled gaps, replay result, timeout recovery, and request rollover.");
    return 0;
}
