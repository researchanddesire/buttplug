#pragma once
#include "evt_math.h"
#include "esp_err.h"
/* Application-only USB policy; ROM/reset behavior is outside this gate. */
esp_err_t evt_console_transport_init(uint64_t now_ms);
esp_err_t evt_console_transport_tick(uint64_t now_ms);
void evt_console_disconnect(void);
/* Atomic raw PGOOD snapshot and rising-edge count; no physical-removal claim. */
uint32_t evt_console_source_snapshot(bool *present);
void evt_console_load_calibration(evt_compass_cal_t *cal);
void evt_console_poll(evt_compass_cal_t *cal);
