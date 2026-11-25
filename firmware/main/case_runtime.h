#pragma once
#include "case_telemetry.h"

#define CT_PEER_CAPACITY 3u
#define CT_USB_CONNECTION (UINT32_C(1) << 16)
#define CT_RUNTIME_CAPACITY (CT_PEER_CAPACITY + 1u)
#define CT_ROUTINE_MASK ((1u<<CT_THERMAL)|(1u<<CT_CHARGE)|(1u<<CT_SOURCE)|(1u<<CT_FIRST_VALID))
typedef struct {
    ct_packet_t packet;
    uint32_t epoch, token;
    size_t index;
    bool command_reply;
} ct_transmission_t;
typedef struct {
    bool active, request_queued, have_result;
    uint32_t connection, epoch, reply_serial, sent_revision[7];
    uint64_t next_routine_ms;
    uint8_t routine_pending;
    size_t reply_next;
    ct_session_t session;
    ct_reply_t reply;
    ct_packet_t result;
} ct_peer_t;
typedef struct {
    size_t slot;
    uint32_t epoch;
    uint64_t received_ms;
    uint8_t data[CT_WIRE_BYTES];
} ct_pending_t;
typedef struct {
    bool ready;
    uint32_t next_epoch, revision[7];
    ct_packet_t current[7];
    ct_peer_t peers[CT_RUNTIME_CAPACITY];
    ct_pending_t commands[CT_RUNTIME_CAPACITY];
    size_t command_next, command_count;
} ct_runtime_t;

/* One application mutex must cover every access. Processing is main-task only;
 * Transports can open/close, queue, copy a read or peek/ack a response.
 * USB has a reserved slot and receives only solicited command replies.
 * No function calls a transport, writes flash or changes an actuator. */
void ct_runtime_init(ct_runtime_t *runtime);
bool ct_runtime_open(ct_runtime_t *runtime, uint32_t connection);
void ct_runtime_close(ct_runtime_t *runtime, uint32_t connection);
bool ct_runtime_read(const ct_runtime_t *runtime, uint32_t connection, uint8_t kind, uint8_t out[CT_WIRE_BYTES]);
bool ct_runtime_enqueue(ct_runtime_t *runtime, uint32_t connection, const uint8_t data[CT_WIRE_BYTES], uint64_t received_ms);
void ct_runtime_update(ct_runtime_t *runtime, const thermal_history_t *history,
                       const ct_charge_t *charge, uint64_t (*clock_ms)(void));
/* Subscription filtering happens before an offer. Failed sends consume no
 * offer; successful sends ack only the exact connection epoch/queue token.
 * Routine values coalesce to at most one update per kind per1000ms cycle. */
bool ct_runtime_peek(ct_runtime_t *runtime, uint32_t connection, uint8_t subscribed,
                     uint64_t now_ms, ct_transmission_t *transmission);
void ct_runtime_sent(ct_runtime_t *runtime, uint32_t connection, const ct_transmission_t *transmission);
