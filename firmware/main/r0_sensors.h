#pragma once
#include "esp_err.h"
#include "proto_control.h"
typedef struct {
    int temperature_millic;
    uint32_t temperature_sequence;
    uint64_t temperature_started_ms, temperature_sampled_ms;
    bool temperature_source_at_start, temperature_source_at_end, temperature_source_changed;
    int battery_mv;
#ifdef BOARD_EVT1_ONE_BOARD
    int pack_temperature_millic;
    uint64_t pack_temperature_sampled_ms;
    bool pack_temperature_valid;
#endif
    int16_t accel[3];
    int16_t mag[3];
    bool temperature_valid;
    bool battery_valid;
    bool accel_valid;
    bool mag_valid;
    bool adc_calibrated;
} r0_sample_t;
esp_err_t r0_sensors_init(void);
void r0_sensors_sleep(void);
void r0_sensors_sample(r0_sample_t *sample);
