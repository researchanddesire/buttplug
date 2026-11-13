#include <stdint.h>
#include "board.h"
#include "stm32l071xx.h"
extern uint32_t _estack,_sidata,_sdata,_edata,_sbss,_ebss;
int main(void);
void SysTick_Handler(void);
void Reset_Handler(void){
    __disable_irq();
    uint32_t *s=&_sidata;
    for(uint32_t *d=&_sdata;d<&_edata;) *d++=*s++;
    for(uint32_t *d=&_sbss;d<&_ebss;) *d++=0;
    SystemInit();(void)main();board_fail_stop();
}
void HardFault_Handler(void){board_fail_stop();}
void Default_Handler(void){board_fail_stop();}
typedef void(*vector)(void);
#define D Default_Handler
__attribute__((section(".isr_vector"),used))
const vector vectors[]={
 (vector)&_estack,Reset_Handler,D,HardFault_Handler,D,D,D,D,D,D,D,D,D,D,D,SysTick_Handler,
 D,D,D,D,D,D,D,D,D,D,D,D,D,D,D,D,D,D,D,D,D,D,D,D,D,D,D,D,D,D,D,D
};
