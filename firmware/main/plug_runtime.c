#include "plug_runtime.h"
#include <math.h>

bool plug_map_scale(plug_scale_t m, float input, bool valid, float floor, float ceiling, float *output) {
    if (!output || !valid || !isfinite(input) || !isfinite(m.input_min) || !isfinite(m.input_max) ||
        !isfinite(m.output_min) || !isfinite(m.output_max) || !isfinite(floor) || !isfinite(ceiling) ||
        m.input_max <= m.input_min || ceiling < floor) return false;
    float fraction = fmaxf(0, fminf(1,(input - m.input_min) / (m.input_max - m.input_min)));
    *output = fmaxf(floor,fminf(ceiling,m.output_min + fraction * (m.output_max - m.output_min)));
    return true;
}
bool plug_map_threshold(float previous, bool previous_valid, float input, bool valid, float threshold) {
    return valid && previous_valid && isfinite(previous) && isfinite(input) && isfinite(threshold) &&
           previous < threshold && input >= threshold;
}
void plug_wear_start(plug_wear_t *w, uint64_t now) {
    if (!w->active) { w->session_id++; w->elapsed_ms = 0; w->confirmed_ms = 0; }
    w->active = true; w->paused = false; w->prior_confirmed = false;
    w->last_ms = now; w->state = PLUG_WEAR_UNKNOWN;
}
void plug_wear_pause(plug_wear_t *w) { w->paused = true; w->prior_confirmed = false; w->state = PLUG_WEAR_PAUSED; }
void plug_wear_end(plug_wear_t *w) { w->active = false; w->paused = false; w->prior_confirmed = false; w->state = PLUG_WEAR_UNKNOWN; }
void plug_wear_tick(plug_wear_t *w, plug_wear_state_t evidence, bool qualified,
                    bool sensors_valid, bool docked, uint64_t sampled, uint64_t now) {
    if (!w->active) return;
    if (now < w->last_ms) { w->prior_confirmed = false; w->state = PLUG_WEAR_UNKNOWN; return; }
    uint64_t delta = now - w->last_ms;
    w->elapsed_ms += delta; w->last_ms = now;
    bool confirmed = !w->paused && qualified && sensors_valid && !docked &&
        sampled <= now && now - sampled <= 1500 && evidence == PLUG_WEAR_CONFIRMED;
    /* Never count across a sampling gap, a state transition or unqualified evidence. */
    if (confirmed && w->prior_confirmed && delta <= 500) w->confirmed_ms += delta;
    w->prior_confirmed = confirmed;
    w->state = w->paused ? PLUG_WEAR_PAUSED : confirmed ? PLUG_WEAR_CONFIRMED :
        qualified && sensors_valid && !docked && evidence == PLUG_WEAR_REMOVED ? PLUG_WEAR_REMOVED : PLUG_WEAR_UNKNOWN;
}
const char *plug_wear_state_name(plug_wear_state_t state) {
    switch (state) { case PLUG_WEAR_CONFIRMED: return "confirmed"; case PLUG_WEAR_REMOVED: return "removed";
        case PLUG_WEAR_PAUSED: return "paused"; default: return "unknown"; }
}
