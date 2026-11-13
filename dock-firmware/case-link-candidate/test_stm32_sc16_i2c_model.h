#ifndef CASE_SC16_I2C_MODEL_H
#define CASE_SC16_I2C_MODEL_H

extern I2C_TypeDef model_i2c;
extern GPIO_TypeDef model_gpio_b, model_gpio_c, model_gpio_h;
extern RCC_TypeDef model_rcc;
extern TIM_TypeDef model_tim;

#undef I2C2
#undef GPIOB
#undef GPIOC
#undef GPIOH
#undef RCC
#undef TIM2
#define I2C2 (&model_i2c)
#define GPIOB (&model_gpio_b)
#define GPIOC (&model_gpio_c)
#define GPIOH (&model_gpio_h)
#define RCC (&model_rcc)
#define TIM2 (&model_tim)

uint32_t bus_status(void);
void bus_control(uint32_t value);
void bus_clear(uint32_t bits);
void bus_flush_tx(void);
void bus_write(uint8_t value);
uint8_t bus_read(void);
uint32_t now_ticks(void);
void peripheral_enable(uint32_t value);
void apb_settle(void);

#endif
