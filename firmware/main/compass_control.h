#pragma once
#include <stdbool.h>
#include <stdint.h>

/* Engineering timing candidates; motor/field settling needs bench measurement. */
enum { COMPASS_LEASE_MS = 3000, COMPASS_PULSE_MS = 180,
       COMPASS_SETTLE_MS = 1000, COMPASS_SAMPLE_MAX_AGE_MS = 500 };
typedef enum {
    COMPASS_IDLE, COMPASS_WAITING, COMPASS_TURNING, COMPASS_PULSING, COMPASS_SETTLING
} compass_phase_t;
typedef struct {
    bool active;
    bool aligned;
    uint16_t target_deg;
    uint8_t tolerance_deg;
    uint8_t strength_percent;
    compass_phase_t phase;
    uint8_t stable_samples;
    uint64_t lease_until_ms;
    uint64_t pulse_until_ms;
    uint64_t settle_until_ms;
    uint64_t last_sample_ms;
    uint64_t fresh_after_ms;
} compass_control_t;

void compass_init(compass_control_t *c);
void compass_stop(compass_control_t *c);
/* Same settings renew the lease without restarting the pulse/sample cycle. */
bool compass_request(compass_control_t *c, unsigned target_deg, unsigned tolerance_deg,
                     unsigned strength_percent, uint64_t now_ms);
bool compass_renew(compass_control_t *c, unsigned target_deg, unsigned tolerance_deg,
                   unsigned strength_percent, uint64_t now_ms);
/* Returns a PWM request only. The independent r0 controller still gates output. */
unsigned compass_tick(compass_control_t *c, bool permitted, bool heading_valid,
                      int facing_mdeg, uint64_t sampled_ms, uint64_t now_ms);
int compass_bearing_error(int facing_mdeg, unsigned target_deg);
const char *compass_phase_name(compass_phase_t phase);
