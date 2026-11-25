#pragma once
#include <stdbool.h>
#include <stdint.h>

typedef struct { float input_min, input_max, output_min, output_max; } plug_scale_t;
bool plug_map_scale(plug_scale_t mapping, float input, bool valid,
                    float output_floor, float output_ceiling, float *output);
bool plug_map_threshold(float previous, bool previous_valid, float input,
                       bool valid, float threshold);
typedef enum { PLUG_WEAR_UNKNOWN, PLUG_WEAR_CONFIRMED, PLUG_WEAR_REMOVED, PLUG_WEAR_PAUSED } plug_wear_state_t;
typedef struct {
    bool active, paused, prior_confirmed;
    uint32_t session_id;
    uint64_t last_ms, elapsed_ms, confirmed_ms;
    plug_wear_state_t state;
} plug_wear_t;
void plug_wear_start(plug_wear_t *wear, uint64_t now);
void plug_wear_pause(plug_wear_t *wear);
void plug_wear_end(plug_wear_t *wear);
/* Evidence must come from a qualified device classifier, never an app checkbox. */
void plug_wear_tick(plug_wear_t *wear, plug_wear_state_t evidence, bool classifier_qualified,
                    bool sensors_valid, bool docked, uint64_t sampled_ms, uint64_t now);
const char *plug_wear_state_name(plug_wear_state_t state);
