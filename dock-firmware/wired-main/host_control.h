#ifndef COMPASS_HOST_CONTROL_H
#define COMPASS_HOST_CONTROL_H

#include <stdbool.h>
#include <stdint.h>

#define HOST_CONTROL_ADDRESS 0x38u
#define HOST_CONTROL_VERSION 1u
#define HOST_COMMAND_BYTES 3u
#define HOST_STATUS_BYTES 8u
#define HOST_LEASE_MS 750u
#define HOST_BREAK_MS 100u
#define HOST_SELECT_SETTLE_MS 10u

enum host_status_flag {
    HOST_STATUS_LOCAL = 1u, HOST_STATUS_TRANSITION = 2u, HOST_STATUS_ATTACHED = 4u,
    HOST_STATUS_TIP_VALID = 8u, HOST_STATUS_CONTACT = 16u, HOST_STATUS_FAULT = 32u
};

enum host_phase { HOST_PC, HOST_TO_LOCAL, HOST_LOCAL_SETTLE, HOST_LOCAL,
                  HOST_TO_PC, HOST_PC_SETTLE };

typedef struct {
    enum host_phase phase;
    uint32_t changed_ms;
} host_control;

typedef struct {
    bool blank, local, run_usb;
} host_outputs;

uint8_t host_control_crc(const uint8_t *data, unsigned length);
bool host_control_command(const uint8_t command[HOST_COMMAND_BYTES], bool *local);
host_outputs host_control_step(host_control *state, uint32_t now_ms,
                               bool request_local, bool hardware_permitted);

#endif
