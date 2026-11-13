/* Link-only exercise for the STM32 adapter and bridge callback. */
#include "stm32_sc16_i2c.h"

static case_sc16_i2c adapter;
static sc16_bridge bridge;

void _start(void)
{
    if (case_sc16_i2c_init(&adapter)) {
        sc16_init(&bridge, case_sc16_i2c_transfer, &adapter);
        if (sc16_start_after_reset(&bridge)) (void)sc16_step(&bridge);
    }
    for (;;) {}
}
