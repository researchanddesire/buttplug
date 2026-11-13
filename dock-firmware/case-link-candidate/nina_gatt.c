#include "nina_gatt.h"

enum { GATT_TIMEOUT_MS = 5000, GATT_RX_BYTES_PER_STEP = 32 };
static const char hex_chars[] = "0123456789ABCDEF";
static const char service_uuid[] = "AD3C100064244A93BEFD6AB278057A86";

static bool take(const char **p, const char *expected)
{
    const char *start = *p;
    while (*expected && *start == *expected) {
        ++start;
        ++expected;
    }
    if (*expected) return false;
    *p = start;
    return true;
}

static int nibble(char c)
{
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    return -1;
}

static bool number(const char **p, uint16_t *out)
{
    unsigned value = 0;
    if (**p < '0' || **p > '9') return false;
    do {
        value = value * 10 + (unsigned)(*(*p)++ - '0');
        if (value > UINT16_MAX) return false;
    } while (**p >= '0' && **p <= '9');
    *out = (uint16_t)value;
    return true;
}

static bool field(const char **p, uint16_t *out)
{
    return number(p, out) && take(p, ",");
}

static bool peer(const char **p, const nina_gatt *gatt)
{
    uint16_t connection;
    return field(p, &connection) && connection == gatt->connection;
}

static char *append(char *out, const char *text)
{
    while (*text) *out++ = *text++;
    return out;
}

static char *decimal(char *out, uint16_t value)
{
    char reversed[5];
    unsigned length = 0;
    do {
        reversed[length++] = (char)('0' + value % 10u);
        value /= 10u;
    } while (value);
    while (length) *out++ = reversed[--length];
    return out;
}

static char *command(nina_gatt *gatt, const char *verb)
{
    return append(decimal(append(gatt->command, verb), gatt->connection), ",");
}

static uint16_t descriptor_end(const nina_gatt *gatt)
{
    return gatt->subscribing == CL_FIRST_VALID ? gatt->last :
           gatt->declaration[gatt->subscribing + 1] - 1;
}

static void set_stage(nina_gatt *gatt, nina_gatt_state state, uint64_t now)
{
    gatt->state = state;
    gatt->deadline = (uint32_t)now + GATT_TIMEOUT_MS;
    gatt->sent = false;
    char *out;
    cl_kind kind = gatt->subscribing;
    switch (state) {
    case NINA_GATT_SERVICE:
        out = append(command(gatt, "AT+UBTGDPU="), service_uuid);
        break;
    case NINA_GATT_CHARACTERISTICS:
        out = decimal(append(decimal(command(gatt, "AT+UBTGDCS="), gatt->first), ","), gatt->last);
        break;
    case NINA_GATT_DESCRIPTOR:
        out = decimal(append(decimal(command(gatt, "AT+UBTGDCD="), gatt->value[kind]), ","),
                      descriptor_end(gatt));
        break;
    case NINA_GATT_SUBSCRIBE:
        out = append(decimal(command(gatt, "AT+UBTGWC="), gatt->descriptor), ",1");
        break;
    default:
        return;
    }
    *out++ = '\r';
    *out = '\0';
}

void nina_gatt_stop(nina_gatt *gatt, uint64_t now)
{
    if (gatt->link && gatt->link->link_epoch == gatt->epoch)
        case_link_disconnect(gatt->link, now);
    *gatt = (nina_gatt){0};
}

static void fail(nina_gatt *gatt, uint64_t now)
{
    nina_gatt_stop(gatt, now);
    gatt->state = NINA_GATT_FAILED;
}

bool nina_gatt_begin(nina_gatt *gatt, case_link *link, uint16_t connection, uint64_t now)
{
    if (gatt->state != NINA_GATT_OFF || link->connected || connection == UINT16_MAX) return false;
    uint32_t epoch = case_link_connect(link, now);
    if (!epoch) return false;
    *gatt = (nina_gatt){.link = link, .epoch = epoch, .connection = connection};
    set_stage(gatt, NINA_GATT_SERVICE, now);
    return true;
}

static bool service(nina_gatt *gatt, const char *p)
{
    uint16_t first, last;
    if (!peer(&p, gatt) || !field(&p, &first) || !number(&p, &last) || *p ||
        !first || first >= last || gatt->first) return false;
    gatt->first = first;
    gatt->last = last;
    return true;
}

static bool characteristic(nina_gatt *gatt, const char *p)
{
    uint16_t declaration, value;
    if (!peer(&p, gatt) || !field(&p, &declaration)) return false;
    int high = nibble(*p++);
    if (high < 0) return false;
    int low = nibble(*p++);
    if (low < 0 || !take(&p, ",") || !field(&p, &value)) return false;
    unsigned properties = (unsigned)(high * 16 + low);
    if (declaration <= gatt->first || value <= declaration || value > gatt->last) return false;
    unsigned kind = 0;
    for (unsigned i = 0; i < sizeof(service_uuid) - 1; ++i) {
        int digit = nibble(*p++);
        if (digit < 0) return false;
        if (i == 7) kind = (unsigned)digit;
        else if (digit != nibble(service_uuid[i])) return false;
    }
    if (*p || kind < CL_THERMAL || kind > CL_FIRST_VALID || gatt->value[kind]) return false;
    unsigned required = kind == CL_COMMAND ? 0x08u : 0x12u;
    if (properties != required) return false;
    gatt->declaration[kind] = declaration;
    gatt->value[kind] = value;
    return true;
}

static bool descriptor(nina_gatt *gatt, const char *p)
{
    uint16_t owner, handle;
    if (!peer(&p, gatt) || !field(&p, &owner) || !field(&p, &handle) ||
        owner != gatt->value[gatt->subscribing] || handle <= owner ||
        handle > descriptor_end(gatt) || !take(&p, "2902") || *p || gatt->descriptor) return false;
    gatt->descriptor = handle;
    return true;
}

static bool payload(const nina_gatt *gatt, const char *p,
                    uint16_t *handle, uint8_t bytes[CL_WIRE_BYTES])
{
    if (!peer(&p, gatt) || !field(&p, handle) || !*handle) return false;
    for (unsigned i = 0; i < CL_WIRE_BYTES; ++i) {
        int high = nibble(*p++);
        if (high < 0) return false;
        int low = nibble(*p++);
        if (low < 0) return false;
        bytes[i] = (uint8_t)(high * 16 + low);
    }
    return !*p;
}

static bool notification(nina_gatt *gatt, const char *p, uint64_t now)
{
    uint16_t handle;
    uint8_t bytes[CL_WIRE_BYTES];
    if (!payload(gatt, p, &handle, bytes)) return false;
    for (cl_kind kind = CL_THERMAL; kind <= CL_FIRST_VALID; ++kind) {
        if (kind != CL_COMMAND && gatt->value[kind] == handle) {
            if (kind == CL_RESULT && gatt->state == NINA_GATT_WRITE && !gatt->sent) return true;
            /* The remote may notify while CCCDs are being enabled. The
             * first snapshot command will request a coherent starting point. */
            if (gatt->state == NINA_GATT_READY || gatt->state == NINA_GATT_WRITE ||
                gatt->state == NINA_GATT_READ)
                return case_link_feed(gatt->link, gatt->epoch, kind, bytes, sizeof(bytes), now) != CL_REJECTED;
            return true;
        }
    }
    return false;
}

static bool response_ok(nina_gatt *gatt, uint64_t now)
{
    switch (gatt->state) {
    case NINA_GATT_SERVICE:
        if (!gatt->first) return false;
        set_stage(gatt, NINA_GATT_CHARACTERISTICS, now);
        return true;
    case NINA_GATT_CHARACTERISTICS:
        for (cl_kind kind = CL_THERMAL; kind <= CL_FIRST_VALID; ++kind) {
            if (!gatt->value[kind] || (kind != CL_THERMAL &&
                gatt->declaration[kind] <= gatt->value[kind - 1])) return false;
        }
        gatt->subscribing = CL_THERMAL;
        set_stage(gatt, NINA_GATT_DESCRIPTOR, now);
        return true;
    case NINA_GATT_DESCRIPTOR:
        if (!gatt->descriptor) return false;
        set_stage(gatt, NINA_GATT_SUBSCRIBE, now);
        return true;
    case NINA_GATT_SUBSCRIBE:
        if (gatt->subscribing == CL_FIRST_VALID) {
            set_stage(gatt, NINA_GATT_READY, now);
            return true;
        }
        ++gatt->subscribing;
        if (gatt->subscribing == CL_COMMAND) ++gatt->subscribing;
        gatt->descriptor = 0;
        set_stage(gatt, NINA_GATT_DESCRIPTOR, now);
        return true;
    case NINA_GATT_WRITE:
        set_stage(gatt, NINA_GATT_READY, now);
        return true;
    case NINA_GATT_READ:
        if (!gatt->have_read || case_link_feed(gatt->link, gatt->epoch, gatt->reading,
            gatt->read_bytes, sizeof(gatt->read_bytes), now) == CL_REJECTED) return false;
        set_stage(gatt, NINA_GATT_READY, now);
        return true;
    default:
        return false;
    }
}

static bool receive_line(nina_gatt *gatt, const char *p, uint64_t now)
{
    if (take(&p, "+UUBTGN:")) return notification(gatt, p, now);
    if (!gatt->sent) return false;
    if (take(&p, "OK") && !*p) return response_ok(gatt, now);
    if (gatt->state == NINA_GATT_SERVICE && take(&p, "+UBTGDPU:")) return service(gatt, p);
    if (gatt->state == NINA_GATT_CHARACTERISTICS && take(&p, "+UBTGDCS:")) return characteristic(gatt, p);
    if (gatt->state == NINA_GATT_DESCRIPTOR && take(&p, "+UBTGDCD:")) return descriptor(gatt, p);
    if (gatt->state == NINA_GATT_READ && take(&p, "+UBTGR:")) {
        uint16_t handle;
        if (gatt->have_read || !payload(gatt, p, &handle, gatt->read_bytes) ||
            handle != gatt->value[gatt->reading]) return false;
        gatt->have_read = true;
        return true;
    }
    /* Includes ERROR, startup/reset, and disconnect on the owned ACL. */
    return false;
}

static bool try_send(nina_gatt *gatt, sc16_bridge *bridge)
{
    size_t length = 0;
    while (gatt->command[length]) ++length;
    return sc16_send(bridge, (const uint8_t *)gatt->command, length);
}

nina_gatt_state nina_gatt_step(nina_gatt *gatt, sc16_bridge *bridge, uint64_t now)
{
    if (gatt->state == NINA_GATT_OFF || gatt->state == NINA_GATT_FAILED) return gatt->state;
    if (bridge->state != SC16_READY || !gatt->link->connected ||
        gatt->link->link_epoch != gatt->epoch ||
        (gatt->state != NINA_GATT_READY && (uint32_t)((uint32_t)now - gatt->deadline) < 0x80000000u) ||
        !case_link_poll(gatt->link, now)) {
        fail(gatt, now);
        return gatt->state;
    }
    if (gatt->state == NINA_GATT_WRITE && !gatt->sent && !gatt->link->pending.active)
        set_stage(gatt, NINA_GATT_READY, now);

    uint8_t bytes[GATT_RX_BYTES_PER_STEP];
    size_t count = sc16_receive(bridge, bytes, sizeof(bytes));
    for (size_t i = 0; i < count; ++i) {
        uint8_t c = bytes[i];
        if (c == '\r' || c == '\n') {
            if (!gatt->length) continue;
            gatt->line[gatt->length] = '\0';
            gatt->length = 0;
            if (receive_line(gatt, gatt->line, now)) continue;
        } else if (c >= ' ' && c <= '~' && gatt->length < sizeof(gatt->line) - 1) {
            gatt->line[gatt->length++] = (char)c;
            continue;
        }
        fail(gatt, now);
        return gatt->state;
    }
    /* Let old queued lines drain before admitting another command. */
    if (!count && !gatt->length && !gatt->sent && gatt->state != NINA_GATT_READY)
        gatt->sent = try_send(gatt, bridge);
    return gatt->state;
}

bool nina_gatt_write(nina_gatt *gatt, sc16_bridge *bridge, uint8_t opcode,
                     uint32_t arg0, uint32_t arg1, uint64_t now)
{
    if (gatt->state != NINA_GATT_READY || bridge->state != SC16_READY ||
        !gatt->link->connected || gatt->link->link_epoch != gatt->epoch) return false;
    uint8_t bytes[CL_WIRE_BYTES];
    if (!case_link_command(gatt->link, opcode, arg0, arg1, now, bytes)) return false;
    char *out = append(decimal(command(gatt, "AT+UBTGW="), gatt->value[CL_COMMAND]), ",");
    for (unsigned i = 0; i < sizeof(bytes); ++i) {
        *out++ = hex_chars[bytes[i] >> 4];
        *out++ = hex_chars[bytes[i] & 15];
    }
    *out++ = '\r';
    *out = '\0';
    set_stage(gatt, NINA_GATT_WRITE, now);
    return true;
}

bool nina_gatt_read(nina_gatt *gatt, cl_kind kind, uint64_t now)
{
    if (gatt->state != NINA_GATT_READY || kind < CL_THERMAL || kind > CL_FIRST_VALID ||
        kind == CL_COMMAND || kind == CL_RESULT) return false;
    char *out = decimal(command(gatt, "AT+UBTGR="), gatt->value[kind]);
    *out++ = '\r';
    *out = '\0';
    gatt->reading = kind;
    gatt->have_read = false;
    set_stage(gatt, NINA_GATT_READ, now);
    return true;
}
