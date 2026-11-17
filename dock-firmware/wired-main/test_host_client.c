#include "host_client.h"
#include <assert.h>
#include <stdio.h>

static host_control target;
static uint32_t now, last_write;
static bool host_request, host_lease, offline, frozen, corrupt, invalid;
static unsigned read_count, write_count, pc_count;
static uint8_t sequence;
static uint8_t latest_flags;

static bool exchange(bool read, uint8_t *data, unsigned length)
{
    if (offline) return false;
    if (!read) {
        assert(length == HOST_COMMAND_BYTES);
        assert(host_control_command(data, &host_request));
        last_write = now;
        host_lease = true;
        ++write_count;
        if (!host_request) ++pc_count;
        return true;
    }
    assert(length == HOST_STATUS_BYTES);
    ++read_count;
    if (!frozen) ++sequence;
    latest_flags = HOST_STATUS_CONTACT;
    host_outputs out = host_control_step(&target, now,
        host_request && host_lease && now - last_write < HOST_LEASE_MS, true);
    if (out.blank) latest_flags |= HOST_STATUS_TRANSITION;
    if (out.run_usb) latest_flags |= HOST_STATUS_LOCAL | HOST_STATUS_ATTACHED | HOST_STATUS_TIP_VALID;
    if (invalid) latest_flags = HOST_STATUS_TIP_VALID;
    data[0] = HOST_CONTROL_VERSION;
    data[1] = latest_flags;
    data[2] = sequence;
    data[3] = latest_flags & HOST_STATUS_TIP_VALID ? 0x88 : 0;
    data[4] = latest_flags & HOST_STATUS_TIP_VALID ? 0xff : 0;
    data[5] = data[6] = 0;
    data[7] = host_control_crc(data, 7) ^ (corrupt ? 1u : 0u);
    return true;
}

static void tick(host_client *client, unsigned count, bool power, bool allowed, bool right)
{
    for (unsigned i = 0; i < count; ++i) {
        now += 10;
        if (host_lease && now - last_write >= HOST_LEASE_MS) host_lease = false;
        host_control_step(&target, now, host_request && host_lease, power);
        host_client_step(client, now, power, allowed, right, exchange);
    }
}

int main(void)
{
    now = UINT32_MAX - 2200u;
    host_client client = {.bus_due_ms = now};
    tick(&client, 240, true, true, true);
    assert(read_count && !write_count && !client.local_requested);
    tick(&client, 2, true, true, false);
    tick(&client, 100, true, true, true);
    tick(&client, 100, true, false, true);
    tick(&client, 220, true, true, true);
    assert(!write_count);
    tick(&client, 2, true, true, false);
    tick(&client, 200, true, true, true);
    assert(!client.local_requested);
    tick(&client, 1, true, true, true);
    assert(client.local_requested && host_request && write_count == 1);
    tick(&client, 110, true, false, false);
    assert(write_count >= 4 && client.have_status);
    assert(client.flags & HOST_STATUS_TIP_VALID);
    assert(client.tip_centi_c == -120);

    frozen = true;
    tick(&client, 30, true, false, false);
    assert(!client.have_status);
    frozen = false;
    tick(&client, 20, true, false, false);
    assert(client.have_status);
    corrupt = true;
    tick(&client, 20, true, false, false);
    assert(!client.have_status);
    corrupt = false;
    invalid = true;
    tick(&client, 20, true, false, false);
    assert(!client.have_status);
    invalid = false;
    offline = true;
    tick(&client, 100, true, false, false);
    assert(!client.have_status && !host_lease && target.phase == HOST_PC);
    offline = false;
    tick(&client, 30, true, false, false);
    assert(client.have_status && (client.flags & HOST_STATUS_TIP_VALID));

    tick(&client, 2, true, true, false);
    tick(&client, 201, true, true, true);
    assert(!client.local_requested && !host_request && pc_count == 1);
    tick(&client, 20, true, true, true);
    assert(target.phase == HOST_PC && !(client.flags & HOST_STATUS_TIP_VALID));
    tick(&client, 2, true, true, false);
    tick(&client, 201, true, true, true);
    assert(client.local_requested);
    tick(&client, 1, false, true, true);
    assert(!client.local_requested && !client.have_status);
    tick(&client, 250, true, true, true);
    assert(!client.local_requested && target.phase == HOST_PC);
    puts("PASS: wired client command, recovery, mode gesture and stale data");
}
