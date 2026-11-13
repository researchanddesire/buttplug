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
void board_fail_stop(void) __attribute__((noreturn));
#endif
