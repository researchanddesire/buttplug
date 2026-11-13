#ifndef CASE_LINK_CANDIDATE_H
#define CASE_LINK_CANDIDATE_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

/* Pure protocol/cache candidate. No transport, register, flash or actuator IO. */
#define CL_PROTOCOL_SHA256 "4678caf5112116f93fc80a013288c87fad0e0572ccb57d29b35e8bd2dbe971a5"
#define CL_WIRE_BYTES 20u
#define CL_THERMAL_CAP 64u
#define CL_CHARGE_CAP 8u
#define CL_EVENT_CAP 16u
typedef enum { CL_THERMAL=1, CL_CHARGE, CL_SOURCE, CL_COMMAND, CL_RESULT, CL_FIRST_VALID } cl_kind;
typedef enum { CL_REJECTED=-1, CL_IGNORED=0, CL_ACCEPTED=1, CL_PARTIAL=2, CL_RESYNC=3 } cl_receive;
typedef enum { CL_UNKNOWN, CL_FRESH, CL_AGED, CL_INVALID } cl_quality;
typedef enum { CL_CURRENT, CL_TS, CL_VBAT, CL_CHG, CL_CE, CL_PGOOD, CL_CHARGE_FIELDS } cl_charge_field;
typedef struct {
    cl_kind kind;
    uint16_t sequence, field_faults;
    uint32_t boot_id;
    union {
        struct { uint8_t flags; uint32_t started, completed; int16_t centi_c; uint16_t ratio_q16; } thermal;
        struct { uint16_t validity, current_0p1_ma, ts_mv, vbat_mv; uint32_t completed; uint8_t status; } charge;
        struct { uint8_t flags; uint32_t loss, started, completed; } event;
        struct { uint8_t opcode; uint32_t session_id, case_tick, argument0, argument1; } command;
        struct { uint8_t result; uint32_t received, completed, session_id_echo; } result;
    } data;
} cl_frame;
typedef struct {
    uint32_t thermal_fresh_ms, ratio_fresh_ms, charge_fresh_ms[CL_CHARGE_FIELDS];
    uint32_t max_attempt_ms, max_gap_ms, max_anchor_age_ms, max_round_trip_ms;
    uint32_t combined_clock_drift_ppm, combined_timer_resolution_ms;
    uint16_t max_sequence_advance; /* 1 selects strict resync after any missing sequence */
} cl_policy;
typedef struct { bool initialized, fault; uint32_t prior; uint64_t extended; } cl_tick32_clock;
typedef struct { bool used; uint32_t timing_epoch; cl_frame frame; int64_t completed; uint64_t received; } cl_record;
typedef struct { bool used, have_source, have_valid; uint16_t sequence; cl_record source, valid; } cl_event_record;
typedef struct {
    cl_quality quality;
    bool has_value, latest_attempt_valid;
    int32_t value;
    uint64_t age_min_ms, age_max_ms;
} cl_value;
typedef struct {
    bool known;
    uint16_t newest;
    uint64_t received;
} cl_order;
typedef struct {
    cl_policy policy;
    uint32_t case_session_id, link_epoch, boot_id, retired_boots[4];
    uint32_t next_request_id, protocol_faults, missing_sequences, timing_epoch;
    uint8_t retired_count, retired_next;
    bool connected, boot_known, tick_known, clock_fault, snapshot_seen, resync_needed;
    bool history_continuous;
    uint64_t last_case_ms;
    int64_t tick_reference;
    struct { bool valid; int64_t lower, upper, plug_tick; uint64_t case_ms; } anchor;
    struct { bool active, boot_known, retryable; uint8_t opcode; uint16_t id; uint32_t boot_id; uint64_t sent_ms; uint8_t packet[20]; } pending;
    cl_order thermal_order, charge_order, source_order, valid_order;
    cl_record thermal[CL_THERMAL_CAP], charge[CL_CHARGE_CAP];
    cl_event_record events[CL_EVENT_CAP];
    uint8_t thermal_next, charge_next, event_next;
    bool have_result;
    cl_frame last_result;
} case_link;
typedef struct {
    bool have_source, have_first_valid, source_attempt_matched, first_valid_matched;
    bool same_loss_identity, interrupted, overflow;
    cl_frame source, first_valid, source_attempt, valid_attempt;
} cl_event_view;

bool cl_tick32_update(cl_tick32_clock *clock, uint32_t tick, uint64_t *extended);
/* Caller supplies a qualified fresh logical session nonce; never reuse it to
 * reset request IDs. Values and policy are explicit assumptions, not measured
 * clock accuracy or temperature/charge acceptance thresholds. */
bool case_link_init(case_link *state, uint32_t case_session_id, const cl_policy *policy, uint64_t now_ms);
bool case_link_new_session(case_link *state, uint32_t new_session_id, uint64_t now_ms);
uint32_t case_link_connect(case_link *state, uint64_t now_ms);
void case_link_disconnect(case_link *state, uint64_t now_ms);
bool case_link_poll(case_link *state, uint64_t now_ms);
/* Feed complete values with the epoch captured by the transport callback. Old
 * queued callbacks cannot attach to a later connection. Bytewise LE decoding
 * supports the deliberately unaligned charge fields on Cortex-M0+. */
cl_receive case_link_decode(cl_kind kind, const uint8_t *data, size_t length, cl_frame *frame);
cl_receive case_link_feed(case_link *state, uint32_t link_epoch, cl_kind kind,
                          const uint8_t *data, size_t length, uint64_t received_ms);
/* At most one pending request. IDs survive disconnects under the same nonce;
 * rotate the caller nonce before the 16-bit ID space is exhausted. A snapshot
 * result must be accepted before making an anchor request. ATT success alone
 * never completes the request. No retry generates a second request ID. */
bool case_link_command(case_link *state, uint8_t opcode, uint32_t argument0,
                       uint32_t argument1, uint64_t sent_ms, uint8_t out[CL_WIRE_BYTES]);
/* Retry a timed-out non-anchor operation with its original nonce/ID/payload.
 * This does not ask the sender to create another baseline. Anchor timeout
 * requires a fresh command/ID; an idempotent old anchor is not a new clock
 * observation. Starting another command explicitly discards retry context. */
bool case_link_retry(case_link *state, uint64_t sent_ms, uint8_t out[CL_WIRE_BYTES]);
cl_value case_link_temperature(const case_link *state, uint64_t now_ms);
cl_value case_link_ratio(const case_link *state, uint64_t now_ms);
cl_value case_link_charge(const case_link *state, cl_charge_field field, uint64_t now_ms);
bool case_link_event(const case_link *state, uint16_t sequence, cl_event_view *view);
#endif
