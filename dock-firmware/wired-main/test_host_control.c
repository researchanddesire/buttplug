#include "host_control.h"
#include <assert.h>

static void expect(host_control *state, uint32_t now, bool requested, bool healthy,
                   bool blank, bool local, bool run)
{
    host_outputs value = host_control_step(state, now, requested, healthy);
    assert(value.blank == blank && value.local == local && value.run_usb == run);
}

int main(void)
{
    host_control state = {0};
    uint32_t start = UINT32_MAX - 20u;
    expect(&state, start, false, true, false, false, false);
    expect(&state, start, true, false, false, false, false);
    expect(&state, start, true, true, true, false, false);
    expect(&state, start + 99, true, true, true, false, false);
    expect(&state, start + 100, true, true, true, true, false);
    expect(&state, start + 109, true, true, true, true, false);
    expect(&state, start + 110, true, true, false, true, true);
    expect(&state, start + 111, false, true, true, true, false);
    expect(&state, start + 210, true, true, true, true, false);
    expect(&state, start + 211, true, true, true, false, false);
    expect(&state, start + 221, true, true, false, false, false);
    expect(&state, start + 222, true, true, true, false, false);
    expect(&state, start + 500, true, false, false, false, false);
    expect(&state, start + 600, true, true, true, false, false);
    expect(&state, start + 700, true, true, true, true, false);
    expect(&state, start + 710, true, true, false, true, true);
    expect(&state, start + 711, true, false, false, false, false);
    uint8_t request[HOST_COMMAND_BYTES] = {HOST_CONTROL_VERSION, 1, 0};
    request[2] = host_control_crc(request, HOST_COMMAND_BYTES - 1u);
    bool local = false;
    assert(host_control_command(request, &local) && local);
    request[1] = 0;
    assert(!host_control_command(request, &local));
    request[2] = host_control_crc(request, HOST_COMMAND_BYTES - 1u);
    assert(host_control_command(request, &local) && !local);
    return 0;
}
