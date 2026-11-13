#ifndef NINA_STARTUP_H
#define NINA_STARTUP_H

#include "sc16_bridge.h"

enum {
    NINA_STARTUP_DRAIN_QUIET_MS = 60,
    NINA_STARTUP_PHASE_TIMEOUT_MS = 2000,
    NINA_STARTUP_BYTES_PER_STEP = 32,
};

typedef enum {
    NINA_STARTUP_OFF,
    NINA_STARTUP_DRAIN,
    NINA_STARTUP_SEND_AT,
    NINA_STARTUP_WAIT_AT,
    NINA_STARTUP_SEND_UMRS,
    NINA_STARTUP_WAIT_UMRS,
    NINA_STARTUP_READY,
    NINA_STARTUP_FAILED,
} nina_startup_state;

typedef enum {
    NINA_STARTUP_FAULT_NONE,
    NINA_STARTUP_FAULT_BRIDGE,
    NINA_STARTUP_FAULT_TIMEOUT,
    NINA_STARTUP_FAULT_RESPONSE,
    NINA_STARTUP_FAULT_UART_SETTINGS,
} nina_startup_fault;

/* Single task owner. Inspect state/fault for diagnostics only. */
typedef struct {
    nina_startup_state state;
    nina_startup_fault fault;
    uint32_t phase_started_ms;
    uint32_t last_rx_ms;
    char line[64];
    uint8_t line_len;
    bool uart_settings_seen;
} nina_startup;

void nina_startup_reset(nina_startup *startup);

/* Begin once per fresh hardware reset and SC16 configuration. The caller owns
 * power, hardware reset and SC16 servicing. On source loss, reset this state
 * and stop the SC16. No other UART consumer/producer may run during startup. */
bool nina_startup_begin(nina_startup *startup, const sc16_bridge *bridge,
                        uint32_t now_ms);

/* Advances using software queues only. At READY the next UART consumer may
 * read the bytes following the final result (possibly its trailing LF). */
nina_startup_state nina_startup_step(nina_startup *startup, sc16_bridge *bridge,
                                     uint32_t now_ms);

#endif
