#include "host_client.h"

enum { HOLD_MS = 2000, POLL_MS = 100, LEASE_REFRESH_MS = 250,
       STALE_STATUS_MS = 250 };

static bool due(uint32_t now, uint32_t deadline)
{
    return (uint32_t)(now - deadline) < UINT32_C(0x80000000);
}

static void gesture(host_client *client, uint32_t now, bool allowed, bool right)
{
    if (!allowed) {
        client->right_released = false;
        client->hold_active = false;
    } else if (!right) {
        client->right_released = true;
        client->hold_active = false;
    } else if (client->right_released) {
        if (!client->hold_active) {
            client->hold_started_ms = now;
            client->hold_active = true;
        }
        if (now - client->hold_started_ms >= HOLD_MS) {
            client->right_released = false;
            client->local_requested = !client->local_requested;
            client->mode_pending = true;
            client->have_status = false;
            client->bus_due_ms = now;
        }
    }
}

static bool status_valid(const uint8_t packet[HOST_STATUS_BYTES])
{
    uint8_t flags = packet[1];
    if (packet[0] != HOST_CONTROL_VERSION || (flags & 0xc0u) ||
        packet[5] || packet[6] ||
        host_control_crc(packet, HOST_STATUS_BYTES - 1u) != packet[7]) return false;
    if (!(flags & HOST_STATUS_TIP_VALID)) return !packet[3] && !packet[4];
    const uint8_t required = HOST_STATUS_LOCAL | HOST_STATUS_ATTACHED | HOST_STATUS_CONTACT;
    return (flags & required) == required &&
           !(flags & (HOST_STATUS_TRANSITION | HOST_STATUS_FAULT));
}

void host_client_step(host_client *client, uint32_t now, bool qualified,
                      bool allow_gesture, bool right, host_transfer transfer)
{
    gesture(client, now, qualified && allow_gesture, right);
    if (!qualified) {
        client->local_requested = false;
        client->mode_pending = false;
        client->have_status = false;
        client->have_sequence = false;
        client->bus_due_ms = now;
        return;
    }
    if (client->have_sequence && now - client->last_sequence_ms >= STALE_STATUS_MS)
        client->have_status = false;
    if (!due(now, client->bus_due_ms)) return;
    client->bus_due_ms = now + POLL_MS;
    if (client->mode_pending ||
        (client->local_requested && due(now, client->lease_due_ms))) {
        uint8_t command[HOST_COMMAND_BYTES] = {HOST_CONTROL_VERSION, client->local_requested};
        command[2] = host_control_crc(command, 2);
        if (!transfer(false, command, sizeof(command))) {
            client->have_status = false;
        } else {
            client->mode_pending = false;
            client->lease_due_ms = now + LEASE_REFRESH_MS;
        }
        return;
    }
    uint8_t packet[HOST_STATUS_BYTES];
    if (!transfer(true, packet, sizeof(packet)) || !status_valid(packet)) {
        client->have_status = false;
        return;
    }
    if (!client->have_sequence || client->sequence != packet[2]) {
        client->have_sequence = true;
        client->sequence = packet[2];
        client->last_sequence_ms = now;
    }
    client->flags = packet[1];
    uint16_t bits = (uint16_t)(packet[3] | (packet[4] << 8));
    client->tip_centi_c = (int16_t)(bits <= INT16_MAX ? (int32_t)bits : (int32_t)bits - 65536);
    client->have_status = now - client->last_sequence_ms < STALE_STATUS_MS;
}
