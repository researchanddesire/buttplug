#pragma once
#define R0_STATUS_JSON_CAPACITY 1024
#define R0_THERMAL_JSON_CAPACITY 1024
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"
#include "compass_protocol.h"

enum { R0_CMD_STOP = 0, R0_CMD_DUTY = 1, R0_CMD_LINK_LOST = 2 };
typedef struct {
    uint8_t opcode;
    uint8_t value;
    uint16_t target_deg;
    uint8_t tolerance_deg;
    uint64_t sent_ms;
} r0_command_t;
bool r0_enqueue(uint8_t opcode, uint8_t value);
bool r0_enqueue_compass(const compass_command_t *command);
size_t r0_status_json(char *buffer, size_t size);
size_t r0_compass_status_json(char *buffer, size_t size);
size_t r0_wear_status_json(char *buffer, size_t size);
size_t r0_thermal_status_json(char *buffer, size_t size);
uint64_t r0_now_ms(void);
esp_err_t r0_radio_init(void);
esp_err_t r0_wifi_session(bool enabled);
bool r0_wifi_active(void);
#ifdef BOARD_EVT1
#include "case_runtime.h"
bool r0_case_connected(uint16_t connection);
void r0_case_disconnected(uint16_t connection);
bool r0_case_read(uint16_t connection, uint8_t kind, uint8_t out[CT_WIRE_BYTES]);
bool r0_case_command(uint16_t connection, const uint8_t data[CT_WIRE_BYTES], uint64_t received_ms);
bool r0_case_next(uint16_t connection, uint8_t subscribed, uint64_t now_ms, ct_transmission_t *transmission);
void r0_case_sent(uint16_t connection, const ct_transmission_t *transmission);
#endif
