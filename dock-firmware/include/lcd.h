#ifndef DOCK_LCD_H
#define DOCK_LCD_H
#include "dock_app.h"
void lcd_init(uint8_t contrast);
void lcd_render(const dock_app *app,const dock_inputs *in);
#ifdef DOCK_WIRED_MAIN
#include "host_client.h"
void lcd_render_host(const host_client *host, bool qualified, bool mode_access);
#endif
void lcd_flush(void);
void lcd_flush_page(unsigned page);
void lcd_contrast(uint8_t contrast);
#endif
