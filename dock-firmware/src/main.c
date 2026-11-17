#include "board.h"
#include "lcd.h"
#include "stm32l071xx.h"
int main(void){
    dock_app app;dock_inputs in={0};dock_init(&app);
    if(!board_init())board_fail_stop();
    lcd_init(app.contrast);
#ifdef DOCK_WIRED_MAIN
    host_client usb = {0};
    usb.bus_due_ms = board_millis();
    board_host_bus_init();
#endif
    uint32_t display_ms=board_millis()-200;
    uint8_t shown_contrast=app.contrast;
    for(;;){
        uint32_t loop_start=board_millis();
        if(!board_sample(&in))board_fail_stop();
        dock_step(&app,&in);board_outputs(&app);
#ifdef DOCK_WIRED_MAIN
        bool qualified = in.source_ok && in.source >= SOURCE_1A5;
        bool mode_access = !in.loop_a && !in.loop_b && !app.arm && !in.uv_run &&
                           !in.center && !in.left && app.state != DOCK_RUNNING;
        host_client_step(&usb, in.now_ms, qualified, mode_access, in.right,
                         board_host_bus_transfer);
#endif
        if(shown_contrast!=app.contrast){lcd_contrast(app.contrast);shown_contrast=app.contrast;}
        if((uint32_t)(in.now_ms-display_ms)>=200){
            lcd_render(&app,&in);
#ifdef DOCK_WIRED_MAIN
            lcd_render_host(&usb, qualified, mode_access);
#endif
            lcd_flush();display_ms=in.now_ms;
        }
        if((uint32_t)(board_millis()-loop_start)>100)board_fail_stop();
        /* Only reached after successful ADC/I2C, state/output and scheduled
           display work. No timer ISR, error path or independent task feeds WDI. */
        board_watchdog_heartbeat();
        while((uint32_t)(board_millis()-loop_start)<10)__WFI();
    }
}
