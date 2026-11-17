#ifndef COMPASS_HOST_CLIENT_H
#define COMPASS_HOST_CLIENT_H

#include "host_control.h"

typedef struct {
    bool local_requested, mode_pending, hold_active, right_released;
    bool have_status, have_sequence;
    uint8_t flags, sequence;
    int16_t tip_centi_c;
    uint32_t hold_started_ms, last_sequence_ms, bus_due_ms, lease_due_ms;
} host_client;

typedef bool (*host_transfer)(bool read, uint8_t *data, unsigned length);

void host_client_step(host_client *client, uint32_t now, bool qualified,
                      bool allow_gesture, bool right, host_transfer transfer);

#endif
