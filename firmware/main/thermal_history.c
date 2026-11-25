#include "thermal_history.h"
#include <inttypes.h>
#include <stdio.h>
#include <string.h>

void thermal_history_init(thermal_history_t *h, uint32_t boot_id) {
    memset(h, 0, sizeof(*h));
    h->boot_id = boot_id;
}
const thermal_removal_t *thermal_history_latest(const thermal_history_t *h) {
    return h->event_count ? &h->events[(h->event_next + THERMAL_EVENT_CAPACITY - 1) % THERMAL_EVENT_CAPACITY] : NULL;
}
static bool fresh(uint64_t sampled, uint64_t now) {
    return sampled <= now && now - sampled <= THERMAL_FRESH_MS;
}
static bool advance(thermal_history_t *h, uint64_t now) {
    if (h->clock_fault) return false;
    if (now < h->observed_ms) {
        /* A new boot must explicitly reinitialize the history. Keep records
         * for diagnosis, but do not reuse them in another timebase. */
        h->clock_fault = true;
        return false;
    }
    h->observed_ms = now;
    return true;
}
void thermal_history_source(thermal_history_t *h, bool present, uint64_t now) {
    if (!advance(h, now)) return;
    if (!h->source_known) {
        h->source_known = true;
        h->source_present = present;
        if (present) { ++h->dock_session; h->connected_ms = now; }
        return;
    }
    if (present == h->source_present) return;
    h->source_present = present;
    if (present) {
        if (h->event_count) {
            thermal_removal_t *e = &h->events[(h->event_next + THERMAL_EVENT_CAPACITY - 1) % THERMAL_EVENT_CAPACITY];
            if (!e->after_loss_valid) e->reconnected_before_sample = true;
            if (!e->after_loss_attempted) e->reconnected_before_attempt = true;
        }
        ++h->dock_session;
        h->connected_ms = now;
        return;
    }
    thermal_removal_t e = {.sequence = ++h->event_sequence,
        .dock_session = h->dock_session, .observed_ms = now};
    /* Walk backward only within this connection and a continuous, valid
     * 30s window. An invalid or ambiguous attempt breaks the trend. */
    thermal_sample_t oldest = {0};
    unsigned count = 0;
    for (size_t i = 0; i < h->sample_count; ++i) {
        const thermal_sample_t *s = &h->samples[(h->sample_next + THERMAL_SAMPLE_CAPACITY - 1 - i) % THERMAL_SAMPLE_CAPACITY];
        if (s->dock_session != h->dock_session || !s->docked || !s->valid || s->sampled_ms > now) break;
        if (!count) {
            if (!fresh(s->sampled_ms, now)) break;
            e.last_docked = *s;
            e.docked_age_ms = now - s->sampled_ms;
            e.docked_valid = true;
        } else if (oldest.sampled_ms - s->sampled_ms > THERMAL_FRESH_MS) break;
        if (e.last_docked.sampled_ms - s->sampled_ms > 30000) break;
        oldest = *s;
        ++count;
    }
    if (count >= 3 && e.last_docked.sampled_ms - oldest.sampled_ms >= 2000) {
        int64_t delta = (int64_t)e.last_docked.tip_millic - oldest.tip_millic;
        e.trend_millic_per_min = (int32_t)(delta * 60000 / (int64_t)(e.last_docked.sampled_ms - oldest.sampled_ms));
        e.trend_valid = true;
    }
    h->events[h->event_next] = e;
    h->event_next = (h->event_next + 1) % THERMAL_EVENT_CAPACITY;
    if (h->event_count < THERMAL_EVENT_CAPACITY) ++h->event_count;
    else h->event_overflow = true;
}
bool thermal_history_sample(thermal_history_t *h, thermal_sample_t s, uint64_t now) {
    if (!advance(h, now) || !h->source_known || s.started_ms > s.sampled_ms || s.sampled_ms > now) return false;
    if (h->sample_count) {
        const thermal_sample_t *prior = &h->samples[(h->sample_next + THERMAL_SAMPLE_CAPACITY - 1) % THERMAL_SAMPLE_CAPACITY];
        if (s.sequence == prior->sequence || s.sampled_ms <= prior->sampled_ms) return false;
    }
    s.valid = s.valid && fresh(s.sampled_ms, now) && s.tip_millic >= -40000 && s.tip_millic <= 125000;
    s.dock_session = h->dock_session;
    s.docked = h->source_present && s.source_at_start && s.source_at_end && !s.source_changed && s.started_ms >= h->connected_ms;
    h->samples[h->sample_next] = s;
    h->sample_next = (h->sample_next + 1) % THERMAL_SAMPLE_CAPACITY;
    if (h->sample_count < THERMAL_SAMPLE_CAPACITY) ++h->sample_count;
    if (!h->source_present && h->event_count) {
        thermal_removal_t *e = &h->events[(h->event_next + THERMAL_EVENT_CAPACITY - 1) % THERMAL_EVENT_CAPACITY];
        if (!e->reconnected_before_sample && !s.source_changed && s.loss_sequence_at_start == e->sequence &&
            !s.source_at_start && !s.source_at_end && s.started_ms >= e->observed_ms) {
            if (!e->after_loss_attempted) {
                e->first_attempt_after_loss = s;
                e->after_loss_attempted = true;
            }
            if (!e->after_loss_valid && s.valid) {
                e->first_after_loss = s;
                e->after_loss_valid = true;
            }
        }
    }
    return true;
}
void thermal_history_source_snapshot(thermal_history_t *h, bool present, uint32_t edges, uint64_t now) {
    if (h->edge_counter_known && edges != h->source_loss_edges && h->source_known && h->source_present)
        thermal_history_source(h, false, now);
    h->source_loss_edges = edges;
    h->edge_counter_known = true;
    thermal_history_source(h, present, now);
}
size_t thermal_history_json(const thermal_history_t *h, uint64_t now, char *out, size_t capacity) {
    if (!out || !capacity) return 0;
    const thermal_removal_t *e = thermal_history_latest(h);
    const thermal_sample_t *s = h->sample_count ? &h->samples[(h->sample_next + THERMAL_SAMPLE_CAPACITY - 1) % THERMAL_SAMPLE_CAPACITY] : NULL;
    char tip[16] = "null", sample_ms[24] = "null", loss_ms[24] = "null";
    char docked[16] = "null", docked_ms[24] = "null", age[24] = "null", trend[16] = "null";
    char after[16] = "null", after_ms[24] = "null", attempted_ms[24] = "null";
    bool clock_valid = !h->clock_fault && now >= h->observed_ms;
    if (clock_valid && s) {
        snprintf(sample_ms, sizeof(sample_ms), "%" PRIu64, s->sampled_ms);
        if (s->valid && fresh(s->sampled_ms, now)) snprintf(tip, sizeof(tip), "%" PRId32, s->tip_millic);
    }
    if (e && clock_valid) {
        snprintf(loss_ms, sizeof(loss_ms), "%" PRIu64, e->observed_ms);
        if (e->docked_valid) {
            snprintf(docked, sizeof(docked), "%" PRId32, e->last_docked.tip_millic);
            snprintf(docked_ms, sizeof(docked_ms), "%" PRIu64, e->last_docked.sampled_ms);
            snprintf(age, sizeof(age), "%" PRIu64, e->docked_age_ms);
        }
        if (e->trend_valid) snprintf(trend, sizeof(trend), "%" PRId32, e->trend_millic_per_min);
        if (e->after_loss_valid) {
            snprintf(after, sizeof(after), "%" PRId32, e->first_after_loss.tip_millic);
            snprintf(after_ms, sizeof(after_ms), "%" PRIu64, e->first_after_loss.sampled_ms);
        }
        if (e->after_loss_attempted)
            snprintf(attempted_ms, sizeof(attempted_ms), "%" PRIu64, e->first_attempt_after_loss.sampled_ms);
    }
    int n = snprintf(out, capacity,
        "{\"protocol\":\"thermal-v1\",\"boot_id\":%" PRIu32 ",\"uptime_ms\":%" PRIu64
        ",\"clock_valid\":%s,\"source_known\":%s,\"source_present\":%s,\"dock_session\":%" PRIu32
        ",\"sample_ms\":%s,\"tip_millic\":%s,\"history_samples\":%u,\"retained_events\":%u"
        ",\"source_loss_edges\":%" PRIu32 ",\"loss_sequence\":%" PRIu32 ",\"source_lost_ms\":%s,\"physical_removal_confirmed\":false"
        ",\"last_docked_millic\":%s,\"last_docked_ms\":%s,\"docked_age_at_loss_ms\":%s"
        ",\"trend_millic_per_min\":%s,\"first_after_loss_millic\":%s,\"first_after_loss_ms\":%s"
        ",\"first_attempt_after_loss_ms\":%s,\"first_attempt_after_loss_valid\":%s"
        ",\"reconnected_before_attempt\":%s"
        ",\"reconnected_before_sample\":%s,\"charge_state\":\"unknown\",\"uv_state\":\"unknown\"}",
        h->boot_id, now, clock_valid ? "true" : "false", h->source_known ? "true" : "false",
        h->source_present ? "true" : "false", h->dock_session, sample_ms, tip,
        (unsigned)h->sample_count, (unsigned)h->event_count, h->source_loss_edges, e ? e->sequence : 0, loss_ms,
        docked, docked_ms, age, trend, after, after_ms, attempted_ms,
        clock_valid && e && e->after_loss_attempted && e->first_attempt_after_loss.valid ? "true" : "false",
        e && e->reconnected_before_attempt ? "true" : "false",
        e && e->reconnected_before_sample ? "true" : "false");
    if (n < 0 || (size_t)n >= capacity) { out[0] = 0; return 0; }
    return (size_t)n;
}
