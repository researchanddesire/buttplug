#include "pico/rand.h"
#include "pico/stdlib.h"
#include "tusb.h"
#include "wired_cdc.h"
#include <stdio.h>
#ifdef COMPASS_WIRED_MAIN
#include "host_bridge.h"
#include "hardware/clocks.h"
#endif

enum { NO_INTERFACE = 0xff, C3_VID = 0x303a, C3_PID = 0x1001 };
static uint8_t active = NO_INTERFACE;
static uint64_t next_poll;
#ifdef COMPASS_WIRED_MAIN
static bool allow_mount;
#endif
#ifndef COMPASS_USB_SMOKE
static case_link link;
static wired_cdc cdc;
/* Starting points for the bench only. Calibrate actual combined drift and
 * request timing before using age bounds in a product decision. */
static const cl_policy policy = {
    .thermal_fresh_ms = 1500, .ratio_fresh_ms = 1500,
    .charge_fresh_ms = {2000, 2000, 2000, 2000, 2000, 2000},
    .max_attempt_ms = 500, .max_gap_ms = 10000,
    .max_anchor_age_ms = 60000, .max_round_trip_ms = 1500,
    .combined_clock_drift_ppm = 1000, .combined_timer_resolution_ms = 2,
    .max_sequence_advance = 4,
};
#endif

static uint64_t now_ms(void)
{
    return to_ms_since_boot(get_absolute_time());
}

void tuh_cdc_mount_cb(uint8_t index)
{
#ifdef COMPASS_WIRED_MAIN
    if (!allow_mount) return;
#endif
    tuh_itf_info_t info;
    uint16_t vid, pid;
    if (active != NO_INTERFACE || !tuh_cdc_itf_get_info(index, &info) ||
        !tuh_vid_pid_get(info.daddr, &vid, &pid) ||
        vid != C3_VID || pid != C3_PID || info.desc.bInterfaceNumber != 0) return;
    active = index;
    uint64_t now = now_ms();
    next_poll = now + 250;
#ifndef COMPASS_USB_SMOKE
    if (!wired_cdc_connect(&cdc, &link, now)) active = NO_INTERFACE;
#endif
#ifndef COMPASS_WIRED_MAIN
    printf("CDC mounted, address %u, interface %u\n", info.daddr, info.desc.bInterfaceNumber);
#endif
}

void tuh_cdc_umount_cb(uint8_t index)
{
    if (index != active) return;
#ifndef COMPASS_USB_SMOKE
    wired_cdc_disconnect(&cdc, now_ms());
#endif
    active = NO_INTERFACE;
#ifndef COMPASS_WIRED_MAIN
    puts("CDC detached");
#endif
}

#ifdef COMPASS_WIRED_MAIN
static void schedule_cdc_recovery(uint64_t now)
{
    wired_cdc_disconnect(&cdc, now);
    next_poll = now + 250u;
}

static void restart_cdc(uint64_t now)
{
    if (now < next_poll || !tuh_cdc_mounted(active)) return;
    next_poll = now + 250u;
    if (link.next_request_id > UINT16_MAX &&
        !case_link_new_session(&link, link.case_session_id + 1u, now)) return;

    tuh_cdc_read_clear(active);
    tuh_cdc_write_clear(active);
    /* End any partial command left in the plug's line parser. */
    static const char newline = '\n';
    if (tuh_cdc_write(active, &newline, 1) != 1) return;
    tuh_cdc_write_flush(active);
    wired_cdc_connect(&cdc, &link, now);
}
#endif

static void service_cdc(uint64_t now)
{
#ifdef COMPASS_WIRED_MAIN
    if (!cdc.epoch) {
        restart_cdc(now);
        return;
    }
    if (link.next_request_id > UINT16_MAX && !link.pending.active) {
        schedule_cdc_recovery(now);
        return;
    }
#endif
    uint8_t rx[64];
    uint32_t count = tuh_cdc_read(active, rx, sizeof(rx));
#ifdef COMPASS_USB_SMOKE
    static const char command[] = "thermal-status\n";
    if (count) fwrite(rx, 1, count, stdout);
    if (now >= next_poll && tuh_cdc_write_available(active) >= sizeof(command) - 1) {
        tuh_cdc_write(active, command, sizeof(command) - 1);
        tuh_cdc_write_flush(active);
        next_poll = now + 1000;
    }
#else
    if (count) {
        wired_cdc_result result = wired_cdc_receive(&cdc, cdc.epoch, rx, count, now);
        if (result == WIRED_CDC_COMPLETE) {
#ifndef COMPASS_WIRED_MAIN
            cl_value t = case_link_temperature(&link, now);
            printf("reply %u, status %u, tip quality %u, centiC %ld\n",
                   link.last_result.sequence, link.last_result.data.result.result,
                   t.quality, (long)(t.has_value ? t.value : 0));
#endif
            if (link.snapshot_seen && !link.anchor.valid) next_poll = now;
        }
    }
    if (!wired_cdc_poll(&cdc, now)) {
#ifdef COMPASS_WIRED_MAIN
        schedule_cdc_recovery(now);
#else
        puts("CDC transaction failed. Reconnect the plug.");
        active = NO_INTERFACE;
#endif
        return;
    }
    if (now < next_poll || tuh_cdc_write_available(active) < WIRED_CDC_REQUEST_BYTES) return;
    uint32_t argument = 0;
#ifdef COMPASS_WIRED_MAIN
    uint8_t opcode = wired_cdc_next_request(&cdc, &argument);
#else
    uint8_t opcode = link.snapshot_seen && !link.anchor.valid ? 2 : 1;
#endif
    char request[WIRED_CDC_REQUEST_BYTES];
    if (!wired_cdc_request(&cdc, opcode, argument, now, request)) return;
    if (tuh_cdc_write(active, request, sizeof(request)) != sizeof(request)) {
#ifdef COMPASS_WIRED_MAIN
        schedule_cdc_recovery(now);
#else
        wired_cdc_disconnect(&cdc, now);
        active = NO_INTERFACE;
        puts("Short CDC write. Reconnect the plug.");
#endif
        return;
    }
    tuh_cdc_write_flush(active);
    next_poll = now + 1000;
#endif
}

int main(void)
{
#ifndef COMPASS_WIRED_MAIN
    stdio_init_all();
#endif
#ifndef COMPASS_USB_SMOKE
#ifdef COMPASS_WIRED_MAIN
    set_sys_clock_48mhz();
#endif
    if (!case_link_init(&link, get_rand_32(), &policy, now_ms())) return 1;
#endif
    const tusb_rhport_init_t host = {.role = TUSB_ROLE_HOST, .speed = TUSB_SPEED_FULL};
    if (!tusb_init(0, &host)) return 1;
#ifdef COMPASS_WIRED_MAIN
    /* The host controller can listen on its isolated branch in PC mode. */
    host_bridge_init();
    uint64_t last_status = 0;
    uint8_t last_flags = 0;
#else
    puts("Compass USB host bench");
#endif
    for (;;) {
#ifdef COMPASS_WIRED_MAIN
        uint64_t now = now_ms();
        bool fault, contact;
        host_outputs output = host_bridge_step((uint32_t)now, &fault, &contact);
        allow_mount = output.run_usb;
        host_bridge_select(output);
        if (!output.run_usb && active != NO_INTERFACE) tuh_cdc_umount_cb(active);
        tuh_task_ext(0, false);
        now = now_ms();
        if (output.run_usb && active != NO_INTERFACE) service_cdc(now);
        uint8_t flags = 0;
        if (output.run_usb) flags |= HOST_STATUS_LOCAL;
        if (output.blank) flags |= HOST_STATUS_TRANSITION;
        if (active != NO_INTERFACE) flags |= HOST_STATUS_ATTACHED;
        if (contact) flags |= HOST_STATUS_CONTACT;
        if (fault) flags |= HOST_STATUS_FAULT;
        int16_t centi_c = 0;
        if (active != NO_INTERFACE) {
            cl_value tip = case_link_temperature(&link, now);
            if (tip.quality == CL_FRESH && tip.has_value && tip.latest_attempt_valid &&
                tip.value >= INT16_MIN && tip.value <= INT16_MAX) {
                flags |= HOST_STATUS_TIP_VALID;
                centi_c = (int16_t)tip.value;
            }
        }
        if (flags != last_flags || now - last_status >= 50u) {
            host_bridge_publish(flags, centi_c);
            last_flags = flags;
            last_status = now;
        }
#else
        tuh_task_ext(0, false);
        if (active != NO_INTERFACE) service_cdc(now_ms());
#endif
        tight_loop_contents();
    }
}
