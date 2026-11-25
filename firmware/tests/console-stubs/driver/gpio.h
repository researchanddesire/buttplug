#pragma once
#include "esp_err.h"
#define GPIO_INTR_POSEDGE 1
esp_err_t gpio_install_isr_service(int flags);
esp_err_t gpio_set_intr_type(int pin,int type);
esp_err_t gpio_isr_handler_add(int pin,void (*handler)(void *),void *arg);
int gpio_get_level(int pin);
