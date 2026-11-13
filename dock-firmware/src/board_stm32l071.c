/* Direct peripheral access against ST's unmodified CMSIS device header.
 * Clock/ADC/I2C programming: RM0377; physical GPIOs: DS10690 LQFP48.
 * No USB controller/PHY is used by this MCU. */
#include "board.h"
#include "stm32l071xx.h"
#include "board_pins.h"

uint32_t SystemCoreClock=4194304u;
static volatile uint32_t ticks;
static unsigned ads_channel;
static uint32_t ads_started_ms, complete_scan_ms;
static uint32_t ads_values[4];
static bool have_scan;
typedef struct { bool stable, candidate; uint32_t since; } debounce;
static debounce left_button, right_button;

void SystemInit(void) { SCB->VTOR=0x08000000u; }
void SystemCoreClockUpdate(void) { SystemCoreClock=4194304u; }
void SysTick_Handler(void) { ++ticks; } /* Never service the watchdog here. */
uint32_t board_millis(void) { return ticks; }
static void write_pin(GPIO_TypeDef *p, unsigned n, bool high) { p->BSRR=1u<<(n+(high?0:16)); }
static bool read_pin(GPIO_TypeDef *p,unsigned n) { return (p->IDR&(1u<<n))!=0; }
static void mode(GPIO_TypeDef *p,unsigned n,unsigned value) {
    p->MODER=(p->MODER&~(3u<<(2*n)))|(value<<(2*n));
    p->PUPDR&=~(3u<<(2*n));
    p->OSPEEDR&=~(3u<<(2*n)); /* Low speed reduces EMI and GPIO load. */
}
void board_delay_us(uint32_t us) {
    /* SysTick counts core clocks. Round up to5cycles/us at nominal4.194MHz;
       unlike a compiler-dependent volatile loop this also keeps full-frame
       writes comfortably within the main-loop watchdog budget. Interrupts
       can lengthen the delay, never shorten it. SysTick is already enabled
       before ADC regulator startup or any LCD/watchdog operation. */
    uint32_t remaining=((SystemCoreClock+999999u)/1000000u)*us;
    uint32_t previous=SysTick->VAL;
    while(remaining){
        uint32_t now=SysTick->VAL;
        uint32_t delta=previous>=now?previous-now:previous+SysTick->LOAD+1u-now;
        if(delta>=remaining)break;
        remaining-=delta;previous=now;
    }
}
void board_delay_ms(uint32_t ms) {
    uint32_t start=ticks;
    while ((uint32_t)(ticks-start)<ms) __WFI();
}
void board_lcd_reset(bool high) { write_pin(LCD_RESETn_PORT,LCD_RESETn_PIN,high); }
void board_lcd_write(bool data,uint8_t byte) {
    write_pin(LCD_CSn_PORT,LCD_CSn_PIN,false); write_pin(LCD_A0_PORT,LCD_A0_PIN,data);
    /* Only PA0..7 are touched. PA8 STOPn and PA9 WDI must be preserved. */
    LCD_DB0_PORT->BSRR=((uint32_t)(~byte&255u)<<16)|byte;
    board_delay_us(2); write_pin(LCD_WRn_PORT,LCD_WRn_PIN,false);
    board_delay_us(2); write_pin(LCD_WRn_PORT,LCD_WRn_PIN,true);
    board_delay_us(2); write_pin(LCD_CSn_PORT,LCD_CSn_PIN,true);
}
static bool wait_bits(volatile uint32_t *r,uint32_t bits,bool set,uint32_t timeout) {
    uint32_t start=ticks;
    while (((*r&bits)!=0)!=set) if ((uint32_t)(ticks-start)>timeout) return false;
    return true;
}
static bool clock_setup(void) {
    RCC->APB1ENR|=RCC_APB1ENR_PWREN;
    RCC->CR|=RCC_CR_MSION;
    uint32_t n=100000;
    while (!(RCC->CR&RCC_CR_MSIRDY)) if (!--n) return false;
    /* Reset MSI is2.097MHz. Range3 is legal before raising MSI to4.194MHz. */
    PWR->CR=(PWR->CR&~PWR_CR_VOS)|PWR_CR_VOS;
    n=100000; while(PWR->CSR&PWR_CSR_VOSF) if (!--n) return false;
    RCC->ICSCR=(RCC->ICSCR&~RCC_ICSCR_MSIRANGE)|RCC_ICSCR_MSIRANGE_6;
    RCC->CFGR&=~(RCC_CFGR_SW|RCC_CFGR_HPRE|RCC_CFGR_PPRE1|RCC_CFGR_PPRE2);
    n=100000; while((RCC->CFGR&RCC_CFGR_SWS)!=RCC_CFGR_SWS_MSI) if (!--n) return false;
    FLASH->ACR&=~FLASH_ACR_LATENCY;
    return (PWR->CR&PWR_CR_VOS)==PWR_CR_VOS &&
           (RCC->ICSCR&RCC_ICSCR_MSIRANGE)==RCC_ICSCR_MSIRANGE_6;
}
static bool adc_init(void) {
    RCC->APB2ENR|=RCC_APB2ENR_ADCEN;
    ADC1->CFGR1=0;
    ADC1->CFGR2=ADC_CFGR2_CKMODE_0; /* Synchronous PCLK/2 =2.097MHz. */
    ADC1->SMPR=ADC_SMPR_SMPR; /* Longest160.5cycle sampling for filtered NTCs. */
    ADC1->CR=ADC_CR_ADVREGEN; board_delay_us(30);
    ADC1->CR|=ADC_CR_ADCAL;
    if (!wait_bits(&ADC1->CR,ADC_CR_ADCAL,false,5)) return false;
    ADC1->ISR=ADC_ISR_ADRDY; ADC1->CR|=ADC_CR_ADEN;
    return wait_bits(&ADC1->ISR,ADC_ISR_ADRDY,true,5);
}
static bool adc_read(unsigned channel,uint16_t *out) {
    ADC1->CHSELR=1u<<channel; ADC1->ISR=ADC_ISR_EOC|ADC_ISR_EOS|ADC_ISR_OVR;
    ADC1->CR|=ADC_CR_ADSTART;
    if (!wait_bits(&ADC1->ISR,ADC_ISR_EOC,true,3)) return false;
    *out=(uint16_t)ADC1->DR; return true;
}
static bool i2c_wait(uint32_t flag) {
    uint32_t start=ticks;
    for(;;) {
        if (I2C2->ISR&(I2C_ISR_NACKF|I2C_ISR_BERR|I2C_ISR_ARLO|I2C_ISR_OVR)) return false;
        if (I2C2->ISR&flag) return true;
        if ((uint32_t)(ticks-start)>5) return false;
    }
}
static bool i2c_transfer(uint8_t *data,unsigned length,bool read) {
    if (I2C2->ISR&I2C_ISR_BUSY) return false;
    I2C2->ICR=I2C_ICR_STOPCF|I2C_ICR_NACKCF|I2C_ICR_BERRCF|I2C_ICR_ARLOCF|I2C_ICR_OVRCF;
    I2C2->CR2=(0x48u<<1)|(length<<I2C_CR2_NBYTES_Pos)|I2C_CR2_AUTOEND|
              I2C_CR2_START|(read?I2C_CR2_RD_WRN:0);
    for(unsigned j=0;j<length;++j) {
        if (!i2c_wait(read?I2C_ISR_RXNE:I2C_ISR_TXIS)) return false;
        if(read)data[j]=(uint8_t)I2C2->RXDR;else I2C2->TXDR=data[j];
    }
    if(!i2c_wait(I2C_ISR_STOPF)) return false;
    I2C2->ICR=I2C_ICR_STOPCF; return true;
}
static bool ads_write(uint16_t config) {
    uint8_t bytes[3]={1,(uint8_t)(config>>8),(uint8_t)config};
    return i2c_transfer(bytes,3,false);
}
static bool ads_read(uint8_t reg,uint16_t *out) {
    uint8_t data[2];
    if (!i2c_transfer(&reg,1,false)||!i2c_transfer(data,2,true)) return false;
    *out=(uint16_t)((data[0]<<8)|data[1]); return true;
}
static bool ads_start(void) {
    unsigned pga=ads_channel<2?4:1;
    uint16_t cfg=(uint16_t)(0x8000u|((4u+ads_channel)<<12)|(pga<<9)|0x0100u|(4u<<5)|3u);
    if(!ads_write(cfg))return false;
    ads_started_ms=ticks;return true;
}
static bool ads_service(void) {
    uint32_t age=(uint32_t)(ticks-ads_started_ms);
    if(age<10)return true;
    uint16_t status,raw;
    if(!ads_read(1,&status))return false;
    if(!(status&0x8000u))return age<30;
    if(!ads_read(0,&raw))return false;
    /* Check MUX/PGA/mode/rate readback; never accept a reset-default channel. */
    unsigned pga=ads_channel<2?4:1;
    uint16_t expected=(uint16_t)(((4u+ads_channel)<<12)|(pga<<9)|0x0100u|(4u<<5)|3u);
    if((status&0x7fffu)!=expected)return false;
    if(!dock_ads_decode(ads_channel,(int16_t)raw,&ads_values[ads_channel]))return false;
    if(++ads_channel==4){ads_channel=0;have_scan=true;complete_scan_ms=ticks;}
    return ads_start();
}
static bool button(debounce *b,bool raw) {
    if(raw!=b->candidate){b->candidate=raw;b->since=ticks;}
    if((uint32_t)(ticks-b->since)>=25)b->stable=b->candidate;
    return b->stable;
}
bool board_init(void) {
    RCC->IOPENR|=RCC_IOPENR_GPIOAEN|RCC_IOPENR_GPIOBEN|RCC_IOPENR_GPIOCEN;
    (void)RCC->IOPENR;
    write_pin(MCU_STOPn_PORT,MCU_STOPn_PIN,false);write_pin(MCU_ARM_PORT,MCU_ARM_PIN,false);write_pin(WDI_PORT,WDI_PIN,false);
    mode(GPIOA,8,1);mode(GPIOB,15,1);mode(GPIOA,9,1);
    if(!clock_setup())return false;
    if(SysTick_Config(SystemCoreClock/1000u))return false;
    __enable_irq();
    for(unsigned j=0;j<8;++j)mode(GPIOA,j,1);
    for(unsigned j=10;j<13;++j)mode(GPIOA,j,0);
    mode(GPIOA,15,0); /* Preserve PA13/PA14 SWD reset settings. */
    mode(GPIOB,0,3);mode(GPIOB,1,3);
    for(unsigned j=2;j<5;++j)mode(GPIOB,j,0);
    for(unsigned j=5;j<10;++j)mode(GPIOB,j,1);
    for(unsigned j=12;j<15;++j)mode(GPIOB,j,0);
    for(unsigned j=13;j<16;++j)mode(GPIOC,j,0);
    write_pin(LCD_WRn_PORT,LCD_WRn_PIN,true);write_pin(LCD_CSn_PORT,LCD_CSn_PIN,true);write_pin(LCD_RESETn_PORT,LCD_RESETn_PIN,false);write_pin(STATUS_LED_PORT,STATUS_LED_PIN,false);
    for(unsigned j=10;j<=11;++j){mode(GPIOB,j,2);GPIOB->OTYPER|=1u<<j;
        GPIOB->AFR[1]=(GPIOB->AFR[1]&~(15u<<((j-8)*4)))|(6u<<((j-8)*4));}
    RCC->APB1ENR|=RCC_APB1ENR_I2C2EN;
    I2C2->CR1=0;
    I2C2->TIMINGR=(4u<<20)|(2u<<16)|(39u<<8)|43u; /* ~50kHz at4.194MHz; analogfilter on. */
    I2C2->CR1=I2C_CR1_PE;
    return adc_init() && ads_start();
}
bool board_sample(dock_inputs *i) {
    uint16_t base,lid;
    if(!adc_read(NTC_BASE_ADC_CHANNEL,&base)||!adc_read(NTC_LID_ADC_CHANNEL,&lid)||!ads_service())return false;
    i->now_ms=ticks;
    i->left=button(&left_button,!read_pin(BTN_LEFTn_PORT,BTN_LEFTn_PIN));
    i->center=!read_pin(BTN_CENTERn_DEBOUNCED_PORT,BTN_CENTERn_DEBOUNCED_PIN); /* MAX6816 output, no second software debounce. */
    i->right=button(&right_button,!read_pin(BTN_RIGHTn_PORT,BTN_RIGHTn_PIN));
    i->loop_a=read_pin(LOOP_A_PORT,LOOP_A_PIN);i->loop_b=read_pin(LOOP_B_PORT,LOOP_B_PIN);i->source_ok=read_pin(SOURCE_OK_PORT,SOURCE_OK_PIN);
    i->uv_run=read_pin(UV_RUN_PORT,UV_RUN_PIN);i->release_seen=read_pin(RELEASE_SEEN_PORT,RELEASE_SEEN_PIN);
    i->device_limit_ok=read_pin(DEVICE_LIMIT_FAULTn_PORT,DEVICE_LIMIT_FAULTn_PIN);i->uv_limit_ok=read_pin(UV_LIMIT_FAULTn_PORT,UV_LIMIT_FAULTn_PIN);
    i->uv_vbus_present=read_pin(UV_VBUS_MON_PORT,UV_VBUS_MON_PIN);
    i->source=dock_decode_source(read_pin(CC_OUT1_PORT,CC_OUT1_PIN),read_pin(CC_OUT2_PORT,CC_OUT2_PIN));
    i->ntc_valid=dock_ntc_centi_c(base,&i->base_centi_c)&&dock_ntc_centi_c(lid,&i->lid_centi_c);
    i->monitor_valid=have_scan;i->monitor_ms=complete_scan_ms;
    i->base_uA=ads_values[0];i->lid_uA=ads_values[1];i->base_mV=ads_values[2];i->lid_mV=ads_values[3];
    return true;
}
void board_outputs(const dock_app *a) {
    /* Stop first on interruption; arm last on permission. Neither pin is a
       software UV-start strobe: hardware fresh CENTER clocks own UV_RUN. */
    if(!a->stop_n){write_pin(MCU_STOPn_PORT,MCU_STOPn_PIN,false);write_pin(MCU_ARM_PORT,MCU_ARM_PIN,false);}
    else {write_pin(MCU_ARM_PORT,MCU_ARM_PIN,a->arm);write_pin(MCU_STOPn_PORT,MCU_STOPn_PIN,true);}
    write_pin(STATUS_LED_PORT,STATUS_LED_PIN,a->led);
}
void board_watchdog_heartbeat(void) {
    /* TPS3431 responds to falling edges only. A toggle every loop would put
       two worst-case100ms loops between falling edges, exceeding170ms tWDmin.
       Complete one high/low pulse per successful loop instead. */
    write_pin(WDI_PORT,WDI_PIN,true);board_delay_us(2);write_pin(WDI_PORT,WDI_PIN,false);
}
void board_fail_stop(void) {
    write_pin(MCU_STOPn_PORT,MCU_STOPn_PIN,false);write_pin(MCU_ARM_PORT,MCU_ARM_PIN,false);
    __disable_irq();for(;;)__WFI(); /* External watchdog remains active. */
}
