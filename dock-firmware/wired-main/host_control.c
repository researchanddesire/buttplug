#include "host_control.h"

uint8_t host_control_crc(const uint8_t *data, unsigned length)
{
    uint8_t crc = 0;
    for (unsigned i = 0; i < length; ++i) {
        crc ^= data[i];
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = (uint8_t)((crc << 1) ^ ((crc & 0x80u) ? 0x07u : 0u));
    }
    return crc;
}

bool host_control_command(const uint8_t command[HOST_COMMAND_BYTES], bool *local)
{
    if (command[0] != HOST_CONTROL_VERSION || command[1] > 1 ||
        command[2] != host_control_crc(command, HOST_COMMAND_BYTES - 1u)) return false;
    *local = command[1] != 0;
    return true;
}

static void enter(host_control *state, enum host_phase phase, uint32_t now)
{
    state->phase = phase;
    state->changed_ms = now;
}

host_outputs host_control_step(host_control *state, uint32_t now,
                               bool requested, bool permitted)
{
    if (!permitted) enter(state, HOST_PC, now);
    uint32_t elapsed = now - state->changed_ms;
    switch (state->phase) {
    case HOST_PC:
        if (requested && permitted) enter(state, HOST_TO_LOCAL, now);
        break;
    case HOST_TO_LOCAL:
        if (!requested) enter(state, HOST_PC, now);
        else if (elapsed >= HOST_BREAK_MS) enter(state, HOST_LOCAL_SETTLE, now);
        break;
    case HOST_LOCAL_SETTLE:
        if (!requested) enter(state, HOST_TO_PC, now);
        else if (elapsed >= HOST_SELECT_SETTLE_MS) enter(state, HOST_LOCAL, now);
        break;
    case HOST_LOCAL:
        if (!requested) enter(state, HOST_TO_PC, now);
        break;
    case HOST_TO_PC:
        if (elapsed >= HOST_BREAK_MS) enter(state, HOST_PC_SETTLE, now);
        break;
    case HOST_PC_SETTLE:
        if (elapsed >= HOST_SELECT_SETTLE_MS) enter(state, HOST_PC, now);
        break;
    }
    switch (state->phase) {
    case HOST_TO_LOCAL: return (host_outputs){.blank = true};
    case HOST_LOCAL_SETTLE: return (host_outputs){.blank = true, .local = true};
    case HOST_LOCAL: return (host_outputs){.local = true, .run_usb = true};
    case HOST_TO_PC: return (host_outputs){.blank = true, .local = true};
    case HOST_PC_SETTLE: return (host_outputs){.blank = true};
    default: return (host_outputs){0};
    }
}
