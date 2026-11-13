#ifndef DOCK_APP_H
#define DOCK_APP_H
#include <stdbool.h>
#include <stdint.h>
#ifndef DOCK_UV_SENSE_MILLIOHM
#define DOCK_UV_SENSE_MILLIOHM 3650u
#endif

typedef enum { DOCK_BOOT, DOCK_PRESS_TO_ARM, DOCK_RELEASE_TO_ARM,
               DOCK_READY, DOCK_RUNNING, DOCK_COMPLETE, DOCK_FAULT } dock_state;
typedef enum { FAULT_NONE, FAULT_SOURCE, FAULT_LID_THERMAL, FAULT_NTC,
               FAULT_HOT, FAULT_MONITOR, FAULT_CURRENT_LIMIT,
               FAULT_LATCH, FAULT_LED_CURRENT, FAULT_LED_VOLTAGE } dock_fault;
typedef enum { SOURCE_UNATTACHED, SOURCE_DEFAULT, SOURCE_1A5, SOURCE_3A } dock_source;
typedef struct {
    uint32_t now_ms, monitor_ms;
    bool left, center, right; /* true=pressed, CENTER already hardware debounced */
    bool loop_a, loop_b, source_ok, release_seen, uv_run;
    bool device_limit_ok, uv_limit_ok, uv_vbus_present;
    bool ntc_valid, monitor_valid;
    int16_t base_centi_c, lid_centi_c;
    uint32_t base_uA, lid_uA, base_mV, lid_mV;
    dock_source source;
} dock_inputs;
typedef struct {
    dock_state state;
    dock_fault fault;
    bool arm, stop_n, led;
    bool previous_center, previous_left, previous_right, initialized;
    bool release_pending, start_pending, healthy_tracking, contrast_mode;
    bool both_tracking, both_handled;
    bool off_tracking;
    uint32_t healthy_since_ms, run_since_ms, start_request_ms, both_since_ms;
    uint32_t off_since_ms;
    uint16_t trial_seconds;
    uint8_t contrast;
    uint16_t remaining_seconds;
} dock_app;

void dock_init(dock_app *app);
void dock_step(dock_app *app, const dock_inputs *in);
const char *dock_state_text(dock_state state);
const char *dock_fault_text(dock_fault fault);
dock_source dock_decode_source(bool out1, bool out2);
bool dock_ntc_centi_c(uint16_t adc12, int16_t *temperature);
bool dock_ads_decode(unsigned channel, int16_t adc, uint32_t *value);
#endif
