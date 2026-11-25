#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define THERMAL_SAMPLE_CAPACITY 64u
#define THERMAL_EVENT_CAPACITY 16u
#define THERMAL_FRESH_MS 1500u
#define THERMAL_STATUS_JSON_CAPACITY 1024u

typedef struct {
    uint32_t sequence, dock_session, loss_sequence_at_start;
    uint64_t started_ms, sampled_ms;
    int32_t tip_millic;
    uint16_t raw_ratio_q16;
    bool valid, ratio_valid, source_at_start, source_at_end, source_changed, docked;
} thermal_sample_t;

/* Source loss is an observation, not proof that the plug left the case.
 * Times share this boot's monotonic clock. No wall-clock time is invented. */
typedef struct {
    uint32_t sequence, dock_session;
    uint64_t observed_ms, docked_age_ms;
    thermal_sample_t last_docked, first_attempt_after_loss, first_after_loss;
    int32_t trend_millic_per_min;
    bool docked_valid, trend_valid, after_loss_attempted, after_loss_valid;
    bool reconnected_before_sample, reconnected_before_attempt;
} thermal_removal_t;

typedef struct {
    uint32_t boot_id, dock_session, event_sequence;
    uint32_t source_loss_edges;
    bool source_known, source_present, clock_fault, edge_counter_known, event_overflow;
    uint64_t observed_ms, connected_ms;
    thermal_sample_t samples[THERMAL_SAMPLE_CAPACITY];
    thermal_removal_t events[THERMAL_EVENT_CAPACITY];
    size_t sample_next, sample_count, event_next, event_count;
} thermal_history_t;

void thermal_history_init(thermal_history_t *history, uint32_t boot_id);
void thermal_history_source(thermal_history_t *history, bool present, uint64_t now_ms);
/* Count comes from the raw PGOOD rising-edge ISR. A loss/reconnect between
 * polls invalidates the old connection; coalesced edges have no invented times. */
void thermal_history_source_snapshot(thermal_history_t *history, bool present, uint32_t loss_edges, uint64_t now_ms);
/* Call once per actual sensor attempt, including failures. Cached calls with
 * the same sequence/timestamp are ignored; never restamp a cached reading. */
bool thermal_history_sample(thermal_history_t *history, thermal_sample_t sample, uint64_t now_ms);
const thermal_removal_t *thermal_history_latest(const thermal_history_t *history);
/* Single-owner formatting; copy the result under the application's status
 * mutex before exposing it to other tasks. Returns0 on insufficient space. */
size_t thermal_history_json(const thermal_history_t *history, uint64_t now_ms, char *out, size_t capacity);
