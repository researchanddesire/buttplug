#pragma once
#include <stdbool.h>
#include <stdint.h>

/* ADS1115 PGA +/-4.096 V (125 uV/count). Reference is excitation / 2. */
bool evt_ntc_temperature(int16_t tip, int16_t reference_before,
                         int16_t reference_after, int *millic);
bool evt_pack_ntc_temperature(int16_t pack, int16_t reference_before,
                              int16_t reference_after, int *millic);

/* Assembly calibration, registered to the molded flange/back arrow.
 * Includes separate package-axis registration and magnetic soft-iron correction.
 * No wearer pose calibration is required.
 */
typedef struct {
    uint32_t version;
    float accel_to_flange[9];
    float mag_to_flange[9];
    float mag_offset_ut[3];
    float arrow[3];
} evt_compass_cal_t;
bool evt_compass_cal_valid(const evt_compass_cal_t *cal);
bool evt_heading(const float accel_mg[3], const float mag_ut[3],
                 const evt_compass_cal_t *cal, bool docked, bool motor_running,
                 int *heading_mdeg);
