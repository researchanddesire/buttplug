#include "compass_protocol.h"
#include <string.h>

bool compass_decode_command(const uint8_t *b, size_t n, compass_command_t *out) {
    if (!b || !out || (n != 2 && n != 6)) return false;
    compass_command_t c = {0};
    c.opcode = b[0];
    if (n == 2) {
        c.value = b[1];
        if (c.opcode >= PLUG_CMD_START && c.opcode <= PLUG_CMD_END) {
            if (c.value != 1) return false;
            *out = c; return true;
        }
        if ((c.opcode != COMPASS_CMD_STOP && c.opcode != COMPASS_CMD_DUTY) ||
            c.value > 25 || (c.opcode == COMPASS_CMD_STOP && c.value)) return false;
    } else {
        if ((c.opcode != COMPASS_CMD_DIRECTION && c.opcode != COMPASS_CMD_RENEW) || b[1] != COMPASS_PROTOCOL_VERSION)
            return false;
        c.target_deg = (uint16_t)b[2] | ((uint16_t)b[3] << 8);
        c.tolerance_deg = b[4];
        c.value = b[5];
        if (c.target_deg >= 360 || c.tolerance_deg < 5 || c.tolerance_deg > 45 ||
            c.value < 1 || c.value > 25) return false;
    }
    *out = c;
    return true;
}
