#ifndef CASE_STM32_SC16_I2C_H
#define CASE_STM32_SC16_I2C_H

#include "sc16_bridge.h"

typedef enum {
    CASE_I2C_OK,
    CASE_I2C_NOT_READY,
    CASE_I2C_BAD_ARGUMENT,
    CASE_I2C_BUSY,
    CASE_I2C_SOURCE_LOST,
    CASE_I2C_NACK,
    CASE_I2C_ARBITRATION_LOST,
    CASE_I2C_PERIPHERAL_FAULT,
    CASE_I2C_SHORT_TRANSFER,
    CASE_I2C_DEADLINE,
} case_sc16_i2c_result;

typedef struct {
    case_sc16_i2c_result last_result;
    bool ready;
    bool bus_needs_recovery;
    bool peripheral_reset;
} case_sc16_i2c;

/* After board_init, with sole ownership of the idle I2C2 bus. This reserves
 * TIM2 as a free-running counter and checks the existing bus setup. */
bool case_sc16_i2c_init(case_sc16_i2c *adapter);

/* Matches sc16_transfer. The main scheduler must serialize this with ADS
 * transfers and qualify radio power/reset before calling the bridge. */
bool case_sc16_i2c_transfer(void *context, uint8_t address, uint8_t subaddress,
                            const uint8_t *tx, uint8_t *rx, size_t count,
                            uint32_t timeout_us);

#endif
