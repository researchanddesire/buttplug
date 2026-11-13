#include "nina_gatt.h"
#include "case_telemetry.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static case_link link;
static nina_gatt client;
static sc16_bridge bridge;
static uint64_t now;
static ct_session_t sender;
static thermal_history_t history;
static const char digits[] = "0123456789ABCDEF";

static void start(uint64_t time)
{
    const cl_policy policy = {
        .thermal_fresh_ms = 1500, .ratio_fresh_ms = 1500,
        .charge_fresh_ms = {2000, 2000, 2000, 2000, 2000, 2000},
        .max_attempt_ms = 500, .max_gap_ms = 10000, .max_anchor_age_ms = 60000,
        .max_round_trip_ms = 1000, .combined_clock_drift_ppm = 1000,
        .combined_timer_resolution_ms = 2, .max_sequence_advance = 4,
    };
    bridge = (sc16_bridge){.state = SC16_READY};
    client = (nina_gatt){0};
    now = time;
    assert(case_link_init(&link, 0xaabbccdd, &policy, now));
    assert(nina_gatt_begin(&client, &link, 3, now));
}

static void receive(const char *text)
{
    /* Every third byte may be the end of a scheduling slice. */
    while (*text && client.state != NINA_GATT_FAILED) {
        unsigned bytes = 0;
        while (*text && bytes < 3) bridge.rx.bytes[bytes++] = (uint8_t)*text++;
        bridge.rx.head = 0;
        bridge.rx.count = (uint8_t)bytes;
        nina_gatt_step(&client, &bridge, ++now);
        assert(!bridge.rx.count);
    }
}

static void transmit(const char *expected)
{
    assert(!bridge.tx.count);
    nina_gatt_step(&client, &bridge, ++now);
    assert(bridge.tx.head == 0 && bridge.tx.count == strlen(expected));
    assert(memcmp(bridge.tx.bytes, expected, bridge.tx.count) == 0);
    bridge.tx.count = 0;
}

static void discover_characteristics(void)
{
    transmit("AT+UBTGDPU=3,AD3C100064244A93BEFD6AB278057A86\r");
    receive("\r\n+UBTGDPU:3,30,61\r\nOK\r\n");
    transmit("AT+UBTGDCS=3,30,61\r");
    receive("+UBTGDCS:3,31,12,32,AD3C100164244A93BEFD6AB278057A86\r\n"
            "+UBTGDCS:3,35,12,36,ad3c100264244a93befd6ab278057a86\r\n"
            "+UBTGDCS:3,39,12,40,AD3C100364244A93BEFD6AB278057A86\r\n"
            "+UBTGDCS:3,43,08,44,AD3C100464244A93BEFD6AB278057A86\r\n"
            "+UBTGDCS:3,47,12,48,AD3C100564244A93BEFD6AB278057A86\r\n"
            "+UBTGDCS:3,51,12,52,AD3C100664244A93BEFD6AB278057A86\r\nOK\r\n");
    assert(client.state == NINA_GATT_DESCRIPTOR);
}

static void discover(void)
{
    discover_characteristics();
    const unsigned handles[][3] = {{32,34,33}, {36,38,37}, {40,42,41}, {48,50,49}, {52,61,60}};
    for (unsigned i = 0; i < 5; ++i) {
        char line[80];
        snprintf(line, sizeof(line), "AT+UBTGDCD=3,%u,%u\r", handles[i][0], handles[i][1]);
        transmit(line);
        snprintf(line, sizeof(line), "+UBTGDCD:3,%u,%u,2902\r\nOK\r\n", handles[i][0], handles[i][2]);
        receive(line);
        snprintf(line, sizeof(line), "AT+UBTGWC=3,%u,1\r", handles[i][2]);
        transmit(line);
        receive("OK\r\n");
    }
    assert(client.state == NINA_GATT_READY);
}

static void receive_packet(const char *prefix, const ct_packet_t *packet)
{
    const unsigned handles[] = {0,32,36,40,44,48,52};
    char line[80];
    int written = snprintf(line, sizeof(line), "%s:3,%u,", prefix, handles[packet->kind]);
    assert(written > 0 && (size_t)written + 43 <= sizeof(line));
    char *p = line + written;
    for (unsigned i = 0; i < CT_WIRE_BYTES; ++i) {
        *p++ = digits[packet->data[i] >> 4];
        *p++ = digits[packet->data[i] & 15];
    }
    strcpy(p, "\r\n");
    receive(line);
}

static void execute(uint8_t opcode, bool result_first)
{
    uint64_t sent = now;
    assert(nina_gatt_write(&client, &bridge, opcode, 0, 0, now));
    assert(!nina_gatt_write(&client, &bridge, opcode, 0, 0, now));
    nina_gatt_step(&client, &bridge, ++now);
    const char prefix[] = "AT+UBTGW=3,44,";
    assert(bridge.tx.head == 0 && bridge.tx.count == sizeof(prefix) + CT_WIRE_BYTES * 2);
    assert(memcmp(bridge.tx.bytes, prefix, sizeof(prefix)-1) == 0);
    assert(bridge.tx.bytes[bridge.tx.count-1] == '\r');

    uint8_t data[CT_WIRE_BYTES];
    for (unsigned i = 0; i < sizeof(data); ++i) {
        const char *high = strchr(digits, bridge.tx.bytes[sizeof(prefix)-1 + 2*i]);
        const char *low = strchr(digits, bridge.tx.bytes[sizeof(prefix) + 2*i]);
        assert(high && low && *high && *low);
        data[i] = (uint8_t)((high-digits)*16 + low-digits);
    }
    bridge.tx.count = 0;
    ct_command_t decoded;
    assert(ct_parse_command(data, sizeof(data), &decoded));
    assert(decoded.opcode == opcode && decoded.case_ms == (uint32_t)sent);
    ct_reply_t response;
    assert(ct_execute(&sender, &history, NULL, data, sizeof(data), now+5000, now+5001, &response));
    ct_reply_complete(&sender, data, &response, now+5002);
    if (!result_first) {
        receive("OK\r\n");
        assert(client.state == NINA_GATT_READY && link.pending.active);
    }
    for (unsigned i = 0; i < response.count; ++i) receive_packet("+UUBTGN", &response.frames[i]);
    if (result_first) receive("OK\r\n");
    assert(client.state == NINA_GATT_READY && link.have_result && !link.pending.active);
}

int main(void)
{
    start(1000);
    discover();
    thermal_history_init(&history, 77);
    ct_session_init(&sender);
    execute(1, false);
    assert(link.snapshot_seen && !link.anchor.valid);
    execute(2, true);
    assert(link.anchor.valid);
    thermal_sample_t sample = {.sequence=1, .started_ms=now+4990, .sampled_ms=now+5000,
                               .tip_millic=37120, .valid=true};
    ct_packet_t packet;
    ct_encode_sample(&history, &sample, &packet);
    assert(!nina_gatt_read(&client, CL_RESULT, now));
    assert(nina_gatt_read(&client, CL_THERMAL, now));
    transmit("AT+UBTGR=3,32\r");
    receive_packet("+UBTGR", &packet);
    assert(case_link_temperature(&link, now).quality != CL_FRESH);
    receive("OK\r\n");
    assert(case_link_temperature(&link, now).quality == CL_FRESH);
    assert(case_link_temperature(&link, now).value == 3712);
    receive("+UUBTACLD:3\r\n");
    assert(client.state == NINA_GATT_FAILED && !link.connected);
    assert(case_link_temperature(&link, now).quality == CL_UNKNOWN);

    start(0);
    transmit("AT+UBTGDPU=3,AD3C100064244A93BEFD6AB278057A86\r");
    receive("+UBTGDPU:4,30,61\r\n");
    assert(client.state == NINA_GATT_FAILED);
    start(0);
    transmit("AT+UBTGDPU=3,AD3C100064244A93BEFD6AB278057A86\r");
    receive("+UBTGDPU:3,30,61\r\n+UBTGDPU:3,62,65\r\nOK\r\n");
    assert(client.state == NINA_GATT_FAILED);
    start(0);
    transmit("AT+UBTGDPU=3,AD3C100064244A93BEFD6AB278057A86\r");
    receive("+UBTGDPU:3,30,61\r\nOK\r\n");
    transmit("AT+UBTGDCS=3,30,61\r");
    receive("+UBTGDCS:3,31,12,32,AD3C100164244A93BEFD6AB278057A86\r\nOK\r\n");
    assert(client.state == NINA_GATT_FAILED);
    start(0);
    discover();
    receive("+UUBTGN:3,32,01\r\n");
    assert(client.state == NINA_GATT_FAILED);
    start(0);
    discover();
    receive("+UUBTGN:3,44,0000000000000000000000000000000000000000\r\n");
    assert(client.state == NINA_GATT_FAILED);
    start(0);
    discover();
    receive("+STARTUP\r\n");
    assert(client.state == NINA_GATT_FAILED);
    start(0);
    discover_characteristics();
    transmit("AT+UBTGDCD=3,32,34\r");
    receive("+UBTGDCD:3,32,37,2902\r\nOK\r\n");
    assert(client.state == NINA_GATT_FAILED);
    start(0);
    discover();
    assert(nina_gatt_write(&client, &bridge, 1, 0, 0, now));
    now += 1001;
    assert(nina_gatt_step(&client, &bridge, now) == NINA_GATT_READY);
    assert(!bridge.tx.count && !link.pending.active);
    start(0);
    discover();
    assert(nina_gatt_read(&client, CL_THERMAL, now));
    transmit("AT+UBTGR=3,32\r");
    receive_packet("+UBTGR", &packet);
    receive_packet("+UBTGR", &packet);
    assert(client.state == NINA_GATT_FAILED && !link.connected);
    start(0);
    bridge.state = SC16_FAULT;
    assert(nina_gatt_step(&client, &bridge, now) == NINA_GATT_FAILED && !link.connected);
    start(UINT32_MAX - 50);
    assert(nina_gatt_step(&client, &bridge, now+4999) == NINA_GATT_SERVICE);
    assert(nina_gatt_step(&client, &bridge, now+5000) == NINA_GATT_FAILED);
    start(0);
    ++link.link_epoch;
    assert(nina_gatt_step(&client, &bridge, now) == NINA_GATT_FAILED && link.connected);

    puts("NINA GATT: discovery, five subscriptions, reads, actual C3 sender roundtrip and fail-closed traces passed");
}
