#include "board.h"
#include "lcd.h"
#include "stm32l071xx.h"
int main(void){
    dock_app app;dock_inputs in={0};dock_init(&app);
    if(!board_init())board_fail_stop();
    lcd_init(app.contrast);
    uint32_t display_ms=board_millis()-200;
    uint8_t shown_contrast=app.contrast;
    for(;;){
        uint32_t loop_start=board_millis();
        if(!board_sample(&in))board_fail_stop();
        dock_step(&app,&in);board_outputs(&app);
        if(shown_contrast!=app.contrast){lcd_contrast(app.contrast);shown_contrast=app.contrast;}
        if((uint32_t)(in.now_ms-display_ms)>=200){
            lcd_render(&app,&in);lcd_flush();display_ms=in.now_ms;
        }
        if((uint32_t)(board_millis()-loop_start)>100)board_fail_stop();
        /* Only reached after successful ADC/I2C, state/output and scheduled
           display work. No timer ISR, error path or independent task feeds WDI. */
        board_watchdog_heartbeat();
        while((uint32_t)(board_millis()-loop_start)<10)__WFI();
    }
}
