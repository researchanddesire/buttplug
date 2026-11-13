#include "board.h"
#include "board_pins.h"
#include "lcd.h"
#include "nina_startup.h"
#include "radio_schedule.h"
#include "sc16_bridge.h"
#include "stm32_sc16_i2c.h"
#include "stm32l071xx.h"

_Static_assert(DOCK_UV_SENSE_MILLIOHM == 4220u, "radio schematic requires 4.22 ohm UV sense resistors");

enum {
    RADIO_REQUEST_PIN = 1,
    RADIO_BOOT_DELAY_MS = 150,
    RADIO_OFF_DELAY_MS = 150,
    DISPLAY_REFRESH_MS = 200,
};

typedef enum {
    RADIO_IDLE,
    RADIO_BOOTING,
    RADIO_CONFIGURING,
    RADIO_AT_STARTUP,
    RADIO_UART_VERIFIED,
    RADIO_FAILED,
} radio_state;

static sc16_bridge bridge;
static case_sc16_i2c adapter;
static nina_startup startup;
static radio_state radio;
static uint32_t radio_enabled_ms;
static uint32_t radio_disabled_ms;
/* Retained for bench bring-up over SWD. */
volatile nina_startup_state dock_radio_at_state;
volatile nina_startup_fault dock_radio_at_fault;
volatile sc16_fault dock_radio_bridge_fault;

static void radio_request(bool on)
{
    GPIOH->BSRR = 1u << (RADIO_REQUEST_PIN + (on ? 0 : 16));
}

static bool radio_source_present(void)
{
    return (SOURCE_OK_PORT->IDR & (1u << SOURCE_OK_PIN)) != 0;
}

static void radio_stop(radio_state state)
{
    radio_request(false);
    radio_disabled_ms = board_millis();
    sc16_stop(&bridge);
    nina_startup_reset(&startup);
    if (state == RADIO_IDLE) {
        dock_radio_at_state = NINA_STARTUP_OFF;
        dock_radio_at_fault = NINA_STARTUP_FAULT_NONE;
        dock_radio_bridge_fault = SC16_FAULT_NONE;
    }
    radio = state;
}

static void radio_fail_stop(void)
{
    radio_request(false);
    board_fail_stop();
}

static bool service_nina(void)
{
    if (radio != RADIO_AT_STARTUP) return true;
    dock_radio_at_state = nina_startup_step(&startup, &bridge, board_millis());
    dock_radio_at_fault = startup.fault;
    if (dock_radio_at_state == NINA_STARTUP_READY) {
        radio = RADIO_UART_VERIFIED;
        return false;
    }
    if (dock_radio_at_state != NINA_STARTUP_FAILED) return true;
    radio_stop(RADIO_FAILED);
    return false;
}

static void radio_init(void)
{
    RCC->IOPENR |= RCC_IOPENR_GPIOHEN;
    (void)RCC->IOPENR;
    radio_request(false);
    GPIOH->OTYPER &= ~(1u << RADIO_REQUEST_PIN);
    GPIOH->PUPDR &= ~(3u << (2 * RADIO_REQUEST_PIN));
    GPIOH->OSPEEDR &= ~(3u << (2 * RADIO_REQUEST_PIN));
    GPIOH->MODER = (GPIOH->MODER & ~(3u << (2 * RADIO_REQUEST_PIN))) |
                  (1u << (2 * RADIO_REQUEST_PIN));
    sc16_init(&bridge, case_sc16_i2c_transfer, &adapter);
    radio_disabled_ms = board_millis();
}

static bool radio_slice(uint32_t now_ms)
{
    if (!radio_source_present()) {
        if (radio != RADIO_IDLE) radio_stop(RADIO_IDLE);
        return false;
    }
    if (radio == RADIO_FAILED || radio == RADIO_UART_VERIFIED) return false;
    if (radio == RADIO_IDLE) {
        if (now_ms - radio_disabled_ms < RADIO_OFF_DELAY_MS) return false;
        if (!case_sc16_i2c_init(&adapter)) {
            radio_stop(RADIO_FAILED);
            if (adapter.bus_needs_recovery) radio_fail_stop();
            return false;
        }
        radio_request(true);
        radio_enabled_ms = now_ms;
        radio = RADIO_BOOTING;
        return false;
    }
    if (radio == RADIO_BOOTING) {
        if (now_ms - radio_enabled_ms < RADIO_BOOT_DELAY_MS) return false;
        if (!sc16_start_after_reset(&bridge)) {
            radio_stop(RADIO_FAILED);
            return false;
        }
        radio = RADIO_CONFIGURING;
    }
    sc16_state bridge_state = sc16_step(&bridge);
    if (bridge_state == SC16_FAULT) {
        dock_radio_bridge_fault = bridge.fault;
        radio_stop(adapter.last_result == CASE_I2C_SOURCE_LOST ? RADIO_IDLE : RADIO_FAILED);
        /* An unverified shared bus must not supply UV monitor values. */
        if (adapter.bus_needs_recovery) radio_fail_stop();
        return false;
    }
    if (radio == RADIO_CONFIGURING && bridge_state == SC16_READY) {
        if (!nina_startup_begin(&startup, &bridge, board_millis())) {
            radio_stop(RADIO_FAILED);
            return false;
        }
        radio = RADIO_AT_STARTUP;
    }
    return true;
}

int main(void)
{
    dock_app app;
    dock_inputs inputs = {0};
    dock_init(&app);
    if (!board_init()) board_fail_stop();
    radio_init();
    lcd_init(app.contrast);
    uint32_t display_ms = board_millis() - DISPLAY_REFRESH_MS;
    uint8_t shown_contrast = app.contrast;
    unsigned display_page = 8;

    for (;;) {
        uint32_t slot_start = board_millis();
        if (!board_sample(&inputs)) radio_fail_stop();
        dock_step(&app, &inputs);
        board_outputs(&app);
        if ((!inputs.source_ok || inputs.source < SOURCE_1A5) && radio != RADIO_IDLE) {
            radio_stop(RADIO_IDLE);
        }
        if (shown_contrast != app.contrast) {
            lcd_contrast(app.contrast);
            shown_contrast = app.contrast;
        }
        if (display_page == 8 && inputs.now_ms - display_ms >= DISPLAY_REFRESH_MS &&
            board_millis() - slot_start <= RADIO_CONTROL_PERIOD_MS - LCD_MIN_SLACK_MS) {
            lcd_render(&app, &inputs);
            display_ms = inputs.now_ms;
            display_page = 0;
        } else if (display_page < 8 &&
            board_millis() - slot_start <= RADIO_CONTROL_PERIOD_MS - LCD_MIN_SLACK_MS) {
            lcd_flush_page(display_page++);
        }
        if (board_millis() - slot_start > 100u) radio_fail_stop();
        board_watchdog_heartbeat();

        if (radio_slot_available(slot_start, board_millis())) service_nina();
        for (unsigned step = 0; inputs.source >= SOURCE_1A5 &&
             step < RADIO_STEPS_PER_SLOT &&
             radio_slot_available(slot_start, board_millis()); ++step) {
            if (!radio_slice(board_millis())) break;
            if (radio_slot_available(slot_start, board_millis()) && !service_nina()) break;
        }
        while (board_millis() - slot_start < RADIO_CONTROL_PERIOD_MS) __WFI();
    }
}
