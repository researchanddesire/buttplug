#ifndef BOARD_H
#define BOARD_H
#include "dock_app.h"
bool board_init(void);
uint32_t board_millis(void);
void board_delay_us(uint32_t us);
void board_delay_ms(uint32_t ms);
void board_lcd_reset(bool high);
void board_lcd_write(bool data, uint8_t byte);
bool board_sample(dock_inputs *in);
void board_outputs(const dock_app *app);
void board_watchdog_heartbeat(void);
#ifdef DOCK_WIRED_MAIN
void board_host_bus_init(void);
bool board_host_bus_transfer(bool read, uint8_t *data, unsigned length);
#endif
void board_fail_stop(void) __attribute__((noreturn));
#endif
