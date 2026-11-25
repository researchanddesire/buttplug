#include "compass_control.h"
#include <stdlib.h>
#include <string.h>

void compass_init(compass_control_t *c) {
    memset(c, 0, sizeof(*c));
    c->tolerance_deg = 15;
    c->strength_percent = 10;
}
void compass_stop(compass_control_t *c) {
    c->active = false;
    c->aligned = false;
    c->phase = COMPASS_IDLE;
    c->stable_samples = 0;
    c->lease_until_ms = 0;
    c->pulse_until_ms = 0;
    c->settle_until_ms = 0;
}
bool compass_request(compass_control_t *c, unsigned target, unsigned tolerance,
                     unsigned strength, uint64_t now) {
    if (target >= 360 || tolerance < 5 || tolerance > 45 || strength < 1 || strength > 25)
        return false;
    bool changed = !c->active || now >= c->lease_until_ms || c->target_deg != target ||
                   c->tolerance_deg != tolerance || c->strength_percent != strength;
    if (changed) {
        /* A changed target cannot reuse the preceding target's pulse or bearing. */
        uint64_t settle = c->settle_until_ms;
        if (c->phase == COMPASS_PULSING) settle = now + COMPASS_SETTLE_MS;
        compass_stop(c);
        c->target_deg = (uint16_t)target;
        c->tolerance_deg = (uint8_t)tolerance;
        c->strength_percent = (uint8_t)strength;
        c->phase = settle > now ? COMPASS_SETTLING : COMPASS_WAITING;
        c->settle_until_ms = settle;
        c->fresh_after_ms = settle > now ? settle : now;
        c->last_sample_ms = 0;
    }
    c->active = true;
    c->lease_until_ms = now + COMPASS_LEASE_MS;
    return true;
}
bool compass_renew(compass_control_t *c, unsigned target, unsigned tolerance, unsigned strength, uint64_t now) {
    if (!c->active || now >= c->lease_until_ms || c->target_deg != target ||
        c->tolerance_deg != tolerance || c->strength_percent != strength) return false;
    c->lease_until_ms = now + COMPASS_LEASE_MS;
    return true;
}
int compass_bearing_error(int heading, unsigned target) {
    return (heading - (int)target * 1000 + 540000) % 360000 - 180000;
}
unsigned compass_tick(compass_control_t *c, bool permitted, bool valid,
                      int heading, uint64_t sampled, uint64_t now) {
    if (!c->active) return 0;
    if (!permitted || now >= c->lease_until_ms) { compass_stop(c); return 0; }
    if (c->phase == COMPASS_PULSING) {
        /* Heading is intentionally invalid while the motor is running. */
        if (now < c->pulse_until_ms) return c->strength_percent;
        c->phase = COMPASS_SETTLING;
        c->settle_until_ms = now + COMPASS_SETTLE_MS;
        c->fresh_after_ms = c->settle_until_ms;
        c->stable_samples = 0;
        return 0;
    }
    if (now < c->settle_until_ms) { c->phase = COMPASS_SETTLING; return 0; }
    if (!valid || heading < 0 || heading >= 360000 || sampled > now ||
        now - sampled > COMPASS_SAMPLE_MAX_AGE_MS || sampled <= c->fresh_after_ms) {
        c->phase = COMPASS_WAITING;
        c->stable_samples = 0;
        c->aligned = false;
        return 0;
    }
    if (sampled == c->last_sample_ms) return 0;
    c->last_sample_ms = sampled;
    int error = abs(compass_bearing_error(heading, c->target_deg));
    unsigned window = (unsigned)c->tolerance_deg * 1000 + (c->aligned ? 3000U : 0U);
    if ((unsigned)error > window) {
        c->aligned = false;
        c->stable_samples = 0;
        c->phase = COMPASS_TURNING;
        return 0;
    }
    c->aligned = true;
    c->phase = COMPASS_WAITING;
    if (++c->stable_samples < 2) return 0;
    c->phase = COMPASS_PULSING;
    c->pulse_until_ms = now + COMPASS_PULSE_MS;
    return c->strength_percent;
}
const char *compass_phase_name(compass_phase_t p) {
    switch (p) {
        case COMPASS_WAITING: return "waiting";
        case COMPASS_TURNING: return "turning";
        case COMPASS_PULSING: return "pulse";
        case COMPASS_SETTLING: return "settling";
        default: return "idle";
    }
}
