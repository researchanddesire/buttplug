#ifndef DOCK_RADIO_SCHEDULE_H
#define DOCK_RADIO_SCHEDULE_H

#include <stdbool.h>
#include <stdint.h>

/* Each slot starts after control/ADS work and the watchdog heartbeat.
 * Read millisecond ticks again before every transfer. One tick covers
 * sampling phase and the remaining allowance covers transfer and ISR work. */
enum {
    RADIO_CONTROL_PERIOD_MS = 10,
    RADIO_MIN_SLACK_MS = 4,
    LCD_MIN_SLACK_MS = 4,
    RADIO_STEPS_PER_SLOT = 3,
};

static inline bool radio_slot_available(uint32_t slot_start_ms, uint32_t now_ms)
{
    return now_ms - slot_start_ms <= RADIO_CONTROL_PERIOD_MS - RADIO_MIN_SLACK_MS;
}

#endif
