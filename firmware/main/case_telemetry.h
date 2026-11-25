#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "thermal_history.h"

#define CT_PROTOCOL_SHA256 "4678caf5112116f93fc80a013288c87fad0e0572ccb57d29b35e8bd2dbe971a5"
#define CT_WIRE_BYTES 20u
#define CT_REPLY_CAPACITY 8u
#define CT_IDEMPOTENCY_CAPACITY 8u
#define CT_COMMAND_MAX_AGE_MS 2000u
typedef enum { CT_THERMAL=1, CT_CHARGE, CT_SOURCE, CT_COMMAND, CT_RESULT, CT_FIRST_VALID } ct_kind;
typedef enum { CT_OK, CT_UNSUPPORTED, CT_INVALID_ARGUMENT, CT_HISTORY_UNAVAILABLE,
               CT_BUSY_OR_STALE, CT_NOT_QUALIFIED } ct_result;
typedef struct { uint8_t kind, data[CT_WIRE_BYTES]; } ct_packet_t;
typedef struct { size_t count; bool from_cache; ct_packet_t frames[CT_REPLY_CAPACITY]; } ct_reply_t;
typedef struct {
    uint8_t opcode;
    uint16_t request_id;
    uint32_t session_id, case_ms, argument0, argument1;
} ct_command_t;
enum { CT_ISET_VALID=1u, CT_TS_VALID=2u, CT_VBAT_VALID=4u, CT_CHG_VALID=8u,
       CT_CE_VALID=16u, CT_PGOOD_VALID=32u, CT_HISTORY_CONTINUOUS=64u,
       CT_TIMER_FAULT=128u, CT_ISET_FAULT=256u, CT_TS_FAULT=512u,
       CT_MEASUREMENT_GAP=1024u, CT_BATTERY_QUALIFIED=2048u, CT_TERMINATION_CANDIDATE=4096u };
typedef struct {
    bool acquired;
    uint16_t sequence, validity, current_0p1_ma, ts_mv, vbat_mv;
    uint64_t completed_ms;
    uint8_t raw_status;
} ct_charge_t;
typedef struct {
    bool used;
    uint16_t request_id;
    uint8_t command[CT_WIRE_BYTES];
    ct_reply_t reply;
} ct_cached_reply_t;
typedef struct {
    bool session_known, highwater_known;
    uint32_t session_id;
    uint16_t highwater;
    size_t next;
    ct_cached_reply_t cache[CT_IDEMPOTENCY_CAPACITY];
} ct_session_t;

/* Bytewise LE encoding; no packed structs, IO, allocation, NVS or actuators. */
bool ct_parse_command(const uint8_t *data, size_t length, ct_command_t *command);
void ct_encode_sample(const thermal_history_t *history, const thermal_sample_t *sample, ct_packet_t *out);
void ct_encode_charge(uint32_t boot_id, const ct_charge_t *charge, ct_packet_t *out);
void ct_encode_source(const thermal_history_t *history, const thermal_removal_t *event, bool first_valid, ct_packet_t *out);
void ct_encode_result(uint32_t boot_id, const ct_command_t *command, ct_result result,
                      uint64_t received_ms, uint64_t completed_ms, ct_packet_t *out);
/* Four independently identified values, not an atomic acquisition bundle. */
void ct_snapshot(const thermal_history_t *history, const ct_charge_t *charge, ct_reply_t *reply);
void ct_session_init(ct_session_t *session);
/* Main-task owner only. Caller binds this state to one authenticated peer and
 * connection epoch. Command3 replays the latest real source-loss record; it
 * cannot manufacture a removal event. Command4 queries the most recent16
 * event sequences in the known same-boot modular window. Arguments not used
 * by an opcode must be zero. Cached duplicates replay their ORIGINAL result
 * timestamps and values; an evicted/reused ID returns history_unavailable. */
bool ct_execute(ct_session_t *session, const thermal_history_t *history,
                const ct_charge_t *charge, const uint8_t *command, size_t length,
                uint64_t received_ms, uint64_t completed_ms, ct_reply_t *reply);
/* Stamp semantic completion after execution. Cached duplicates retain their
 * original completion tick, including in the bounded idempotency cache. */
void ct_reply_complete(ct_session_t *session, const uint8_t command[CT_WIRE_BYTES],
                       ct_reply_t *reply, uint64_t completed_ms);
