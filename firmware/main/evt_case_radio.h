#pragma once
#ifdef BOARD_EVT1
#include "esp_err.h"
#include "host/ble_gap.h"
#include "host/ble_uuid.h"
extern const ble_uuid128_t evt_case_service_uuid;
esp_err_t evt_case_radio_init(void);
void evt_case_radio_gap_event(const struct ble_gap_event *event);
void evt_case_radio_reset(void);
/* Task-safe queueing only; all BLE sends run on the NimBLE event queue. */
void evt_case_radio_publish(void);
#endif
