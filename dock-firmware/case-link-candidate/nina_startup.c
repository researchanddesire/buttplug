#include "nina_startup.h"

static const uint8_t at_command[] = "AT\r";
static const uint8_t umrs_command[] = "AT+UMRS?\r";

static nina_startup_state enter(nina_startup *startup, nina_startup_state state,
                                 uint32_t now_ms)
{
    startup->state = state;
    startup->phase_started_ms = now_ms;
    startup->line_len = 0;
    return state;
}

static nina_startup_state fail(nina_startup *startup, nina_startup_fault fault)
{
    startup->fault = fault;
    startup->state = NINA_STARTUP_FAILED;
    return startup->state;
}

void nina_startup_reset(nina_startup *startup)
{
    startup->state = NINA_STARTUP_OFF;
    startup->fault = NINA_STARTUP_FAULT_NONE;
    startup->phase_started_ms = 0;
    startup->last_rx_ms = 0;
    startup->line_len = 0;
    startup->uart_settings_seen = false;
}

bool nina_startup_begin(nina_startup *startup, const sc16_bridge *bridge,
                        uint32_t now_ms)
{
    if (startup->state != NINA_STARTUP_OFF || bridge->state != SC16_READY) {
        return false;
    }
    startup->last_rx_ms = now_ms;
    enter(startup, NINA_STARTUP_DRAIN, now_ms);
    return true;
}

static bool line_is(const char *line, const char *expected)
{
    while (*line != '\0' && *line == *expected) {
        ++line;
        ++expected;
    }
    return *line == *expected;
}

static const char *skip_prefix(const char *line, const char *prefix)
{
    while (*prefix != '\0') {
        if (*line++ != *prefix++) {
            return NULL;
        }
    }
    return line;
}

static const char *skip_spaces(const char *text)
{
    while (*text == ' ') {
        ++text;
    }
    return text;
}

static bool uart_settings_match(const char *field)
{
    static const uint32_t expected[] = {115200, 1, 8, 1, 1};

    for (size_t index = 0; index < sizeof(expected) / sizeof(expected[0]); ++index) {
        uint32_t value = 0;
        field = skip_spaces(field);
        if (*field < '0' || *field > '9') {
            return false;
        }
        while (*field >= '0' && *field <= '9') {
            value = 10 * value + (uint32_t)(*field++ - '0');
            if (value > expected[index]) {
                return false;
            }
        }
        if (value != expected[index]) {
            return false;
        }
        field = skip_spaces(field);
        const char delimiter = index == 4 ? '\0' : ',';
        if (*field++ != delimiter) {
            return false;
        }
    }
    return true;
}

static nina_startup_state process_line(nina_startup *startup, uint32_t now_ms)
{
    startup->line[startup->line_len] = '\0';
    startup->line_len = 0;
    const char *line = startup->line;

    if (startup->state == NINA_STARTUP_WAIT_AT) {
        if (line_is(line, "OK")) {
            return enter(startup, NINA_STARTUP_SEND_UMRS, now_ms);
        }
        if (line_is(line, "AT") || line_is(line, "+STARTUP")) {
            return startup->state;
        }
    } else {
        if (line_is(line, "AT+UMRS?") && !startup->uart_settings_seen) {
            return startup->state;
        }
        const char *settings = skip_prefix(line, "+UMRS:");
        if (settings != NULL && !startup->uart_settings_seen) {
            if (!uart_settings_match(settings)) {
                return fail(startup, NINA_STARTUP_FAULT_UART_SETTINGS);
            }
            startup->uart_settings_seen = true;
            return startup->state;
        }
        if (line_is(line, "OK") && startup->uart_settings_seen) {
            return enter(startup, NINA_STARTUP_READY, now_ms);
        }
    }
    return fail(startup, NINA_STARTUP_FAULT_RESPONSE);
}

static nina_startup_state receive_response(nina_startup *startup,
                                          sc16_bridge *bridge, uint32_t now_ms)
{
    const nina_startup_state waiting = startup->state;
    for (size_t index = 0; index < NINA_STARTUP_BYTES_PER_STEP; ++index) {
        uint8_t byte;
        if (sc16_receive(bridge, &byte, 1) == 0) {
            break;
        }
        if (byte == '\r' || byte == '\n') {
            if (startup->line_len != 0 && process_line(startup, now_ms) != waiting) {
                break;
            }
        } else {
            if (byte < ' ' || byte > '~' || startup->line_len == sizeof(startup->line) - 1) {
                return fail(startup, NINA_STARTUP_FAULT_RESPONSE);
            }
            startup->line[startup->line_len++] = (char)byte;
        }
    }
    return startup->state;
}

static nina_startup_state send_command(nina_startup *startup, sc16_bridge *bridge,
                                      uint32_t now_ms)
{
    /* Finish the previous response's framing, but don't use queued text as
     * evidence for a command that has yet to be sent. */
    for (size_t index = 0; index < NINA_STARTUP_BYTES_PER_STEP; ++index) {
        uint8_t byte;
        if (sc16_receive(bridge, &byte, 1) == 0) {
            const bool probe = startup->state == NINA_STARTUP_SEND_AT;
            const uint8_t *command = probe ? at_command : umrs_command;
            const size_t size = probe ? sizeof(at_command) : sizeof(umrs_command);
            if (sc16_send(bridge, command, size - 1)) {
                return enter(startup, probe ? NINA_STARTUP_WAIT_AT : NINA_STARTUP_WAIT_UMRS,
                             now_ms);
            }
            break;
        }
        if (byte != '\r' && byte != '\n') {
            return fail(startup, NINA_STARTUP_FAULT_RESPONSE);
        }
    }
    return startup->state;
}

nina_startup_state nina_startup_step(nina_startup *startup, sc16_bridge *bridge,
                                     uint32_t now_ms)
{
    if (startup->state == NINA_STARTUP_OFF || startup->state == NINA_STARTUP_FAILED) {
        return startup->state;
    }
    if (bridge->state != SC16_READY) {
        return fail(startup, NINA_STARTUP_FAULT_BRIDGE);
    }
    if (startup->state == NINA_STARTUP_READY) {
        return startup->state;
    }
    if ((uint32_t)(now_ms - startup->phase_started_ms) >= NINA_STARTUP_PHASE_TIMEOUT_MS) {
        return fail(startup, NINA_STARTUP_FAULT_TIMEOUT);
    }

    switch (startup->state) {
    case NINA_STARTUP_DRAIN: {
        uint8_t stale[NINA_STARTUP_BYTES_PER_STEP];
        if (sc16_receive(bridge, stale, sizeof(stale)) != 0) {
            startup->last_rx_ms = now_ms;
        } else if ((uint32_t)(now_ms - startup->last_rx_ms) >= NINA_STARTUP_DRAIN_QUIET_MS) {
            return enter(startup, NINA_STARTUP_SEND_AT, now_ms);
        }
        break;
    }
    case NINA_STARTUP_SEND_AT:
    case NINA_STARTUP_SEND_UMRS:
        return send_command(startup, bridge, now_ms);
    case NINA_STARTUP_WAIT_AT:
    case NINA_STARTUP_WAIT_UMRS:
        return receive_response(startup, bridge, now_ms);
    default:
        break;
    }
    return startup->state;
}
