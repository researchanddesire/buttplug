#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum { COMPASS_CMD_STOP = 0, COMPASS_CMD_DUTY = 1, COMPASS_CMD_DIRECTION = 3, COMPASS_CMD_RENEW = 4,
       PLUG_CMD_START = 5, PLUG_CMD_PAUSE = 6, PLUG_CMD_END = 7,
       COMPASS_PROTOCOL_VERSION = 1 };
typedef struct {
    uint8_t opcode;
    uint8_t value;
    uint16_t target_deg;
    uint8_t tolerance_deg;
} compass_command_t;

/* STOP/DUTY retain the two-byte R0 format. DIRECTION is exactly six bytes. */
bool compass_decode_command(const uint8_t *bytes, size_t length, compass_command_t *out);
