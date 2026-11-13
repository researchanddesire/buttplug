#include "stm32_sc16_i2c.h"

#include "stm32l071xx.h"
#include "board_pins.h"

/* Bench model hooks replace MMIO effects only. Register masks come from the
 * same pinned ST header in both builds. */
#ifdef CASE_SC16_I2C_MODEL
#include "test_stm32_sc16_i2c_model.h"
#else
#define bus_status() (I2C2->ISR)
#define bus_control(bits) (I2C2->CR2 = (bits))
#define bus_clear(bits) (I2C2->ICR = (bits))
#define bus_flush_tx() (I2C2->ISR = I2C_ISR_TXE)
#define bus_write(value) (I2C2->TXDR = (value))
#define bus_read() ((uint8_t)I2C2->RXDR)
#define now_ticks() (TIM2->CNT)
#define peripheral_enable(value) (I2C2->CR1 = (value))
#define apb_settle() do { __NOP(); __NOP(); __NOP(); } while (0)
#endif

enum {
    BOARD_I2C_TIMING = (4u << 20) | (2u << 16) | (39u << 8) | 43u,
    I2C_TICKS_PER_US_MIN = 4u,
    ABORT_RESERVE_TICKS = 400u,
    FINAL_CLEANUP_TICKS = 128u,
    TRANSFER_POLL_LIMIT = 1000u,
    TIMER_PROBE_READS = 64u,
    RADIO_REQUEST_PIN = 1u,
};

static const uint32_t clear_flags = I2C_ICR_STOPCF | I2C_ICR_NACKCF |
    I2C_ICR_BERRCF | I2C_ICR_ARLOCF | I2C_ICR_OVRCF;

static bool lines_released(void)
{
    return (MON_I2C_SCL_PORT->IDR & (1u << MON_I2C_SCL_PIN)) != 0 &&
           (MON_I2C_SDA_PORT->IDR & (1u << MON_I2C_SDA_PIN)) != 0;
}

static bool source_requested(void)
{
    return (SOURCE_OK_PORT->IDR & (1u << SOURCE_OK_PIN)) != 0 &&
           (RCC->IOPENR & RCC_IOPENR_GPIOHEN) != 0 &&
           ((GPIOH->MODER >> (2 * RADIO_REQUEST_PIN)) & 3u) == 1u &&
           (GPIOH->ODR & (1u << RADIO_REQUEST_PIN)) != 0;
}

bool case_sc16_i2c_init(case_sc16_i2c *adapter)
{
    if (!adapter) return false;
    *adapter = (case_sc16_i2c){.last_result = CASE_I2C_NOT_READY};
    if (!(RCC->APB1ENR & RCC_APB1ENR_I2C2EN) ||
        I2C2->CR1 != I2C_CR1_PE || I2C2->TIMINGR != BOARD_I2C_TIMING ||
        (RCC->CFGR & (RCC_CFGR_SWS | RCC_CFGR_HPRE | RCC_CFGR_PPRE1)) != RCC_CFGR_SWS_MSI ||
        (RCC->ICSCR & RCC_ICSCR_MSIRANGE) != RCC_ICSCR_MSIRANGE_6) return false;
    if ((bus_status() & I2C_ISR_BUSY) || !lines_released()) {
        adapter->last_result = CASE_I2C_BUSY;
        adapter->bus_needs_recovery = true;
        return false;
    }

    RCC->APB1ENR |= RCC_APB1ENR_TIM2EN;
    (void)RCC->APB1ENR;
    RCC->APB1SMENR |= RCC_APB1SMENR_TIM2SMEN;
    TIM2->CR1 = 0;
    TIM2->SMCR = 0;
    TIM2->DIER = 0;
    TIM2->PSC = 0;
    /* Use the low 16 bits explicitly. This provides a 15.6 ms nominal wrap
     * period and keeps the deadline arithmetic independent of timer width. */
    TIM2->ARR = UINT16_MAX;
    TIM2->EGR = TIM_EGR_UG;
    TIM2->SR = 0;
    TIM2->CR1 = TIM_CR1_CEN;
    uint16_t start = (uint16_t)now_ticks();
    for (unsigned read = 0; read < TIMER_PROBE_READS; ++read) {
        if ((uint16_t)now_ticks() != start) {
            adapter->last_result = CASE_I2C_OK;
            adapter->ready = true;
            return true;
        }
    }
    return false;
}

static bool expired(uint16_t start, unsigned ticks, unsigned *polls_left)
{
    /* Guard against a stalled timer or a long preemption that spans wrap. */
    if (!*polls_left) return true;
    --*polls_left;
    return (uint16_t)((uint16_t)now_ticks() - start) >= ticks;
}

static case_sc16_i2c_result wait_for(uint32_t flag, uint16_t start, unsigned ticks,
                                    unsigned *polls_left)
{
    for (;;) {
        if (expired(start, ticks, polls_left)) return CASE_I2C_DEADLINE;
        if (!source_requested()) return CASE_I2C_SOURCE_LOST;
        uint32_t status = bus_status();
        if (status & I2C_ISR_ARLO) return CASE_I2C_ARBITRATION_LOST;
        if (status & I2C_ISR_NACKF) return CASE_I2C_NACK;
        if (status & I2C_ISR_OVR) return CASE_I2C_PERIPHERAL_FAULT;
        /* ES0292 §2.12.4: clear a controller-mode BERR and let the
         * transaction proceed. Required byte/STOP flags still gate success. */
        if (status & I2C_ISR_BERR) bus_clear(I2C_ICR_BERRCF);
        /* RXNE can coexist with the final AUTOEND STOP while its last byte
         * still awaits a read. A STOP during a transmit phase or before
         * TC, however, means the write ended before the planned boundary. */
        if ((status & I2C_ISR_STOPF) && flag != I2C_ISR_RXNE && flag != I2C_ISR_STOPF) {
            return CASE_I2C_SHORT_TRANSFER;
        }
        if (status & flag) return CASE_I2C_OK;
        if (status & I2C_ISR_STOPF) return CASE_I2C_SHORT_TRANSFER;
    }
}

static void abort_transfer(case_sc16_i2c *adapter, uint16_t start, unsigned ticks,
                           unsigned *polls_left)
{
    uint32_t status = bus_status();
    bool arbitration_lost = (status & I2C_ISR_ARLO) != 0 ||
        adapter->last_result == CASE_I2C_ARBITRATION_LOST;
    if (!arbitration_lost && (status & I2C_ISR_BUSY) &&
        !(status & (I2C_ISR_STOPF | I2C_ISR_NACKF)) &&
        !(I2C2->CR2 & (I2C_CR2_START | I2C_CR2_STOP))) {
        bus_control(I2C2->CR2 | I2C_CR2_STOP);
    }

    /* NACK initiates its own STOP. On arbitration loss the winning
     * controller owns the bus, so do not send STOP or reset the peripheral. */
    if (!arbitration_lost) {
        while (!(status & (I2C_ISR_STOPF | I2C_ISR_ARLO)) && (status & I2C_ISR_BUSY) &&
               !expired(start, ticks, polls_left)) status = bus_status();
        if ((status & I2C_ISR_BUSY) && !(status & (I2C_ISR_STOPF | I2C_ISR_ARLO))) {
            uint32_t control = I2C2->CR1;
            peripheral_enable(control & ~I2C_CR1_PE);
            (void)I2C2->CR1;
            apb_settle();
            peripheral_enable(control);
            adapter->peripheral_reset = true;
        }
    }
    if (!(status & I2C_ISR_BUSY) || (status & I2C_ISR_STOPF)) {
        if (status & I2C_ISR_RXNE) (void)bus_read();
        bus_flush_tx();
    }
    bus_clear(clear_flags);
    if ((bus_status() & I2C_ISR_BUSY) || !lines_released() || adapter->peripheral_reset) {
        adapter->bus_needs_recovery = true;
    }
}

bool case_sc16_i2c_transfer(void *context, uint8_t address, uint8_t subaddress,
                            const uint8_t *tx, uint8_t *rx, size_t count,
                            uint32_t timeout_us)
{
    case_sc16_i2c *adapter = context;
    if (!adapter) return false;
    if (!adapter->ready || adapter->bus_needs_recovery ||
        (RCC->APB1ENR & (RCC_APB1ENR_TIM2EN | RCC_APB1ENR_I2C2EN)) !=
            (RCC_APB1ENR_TIM2EN | RCC_APB1ENR_I2C2EN) ||
        !(TIM2->CR1 & TIM_CR1_CEN) || !(I2C2->CR1 & I2C_CR1_PE)) {
        adapter->last_result = CASE_I2C_NOT_READY;
        return false;
    }
    if (address != SC16_ADDRESS || subaddress > 0x78u || (subaddress & 7u) ||
        !count || count > SC16_BURST_SIZE || ((tx == NULL) == (rx == NULL)) ||
        timeout_us > SC16_TRANSFER_TIMEOUT_US ||
        timeout_us <= ABORT_RESERVE_TICKS / I2C_TICKS_PER_US_MIN) {
        adapter->last_result = CASE_I2C_BAD_ARGUMENT;
        return false;
    }
    uint16_t start = (uint16_t)now_ticks();
    unsigned ticks = timeout_us * I2C_TICKS_PER_US_MIN;
    unsigned work_ticks = ticks - ABORT_RESERVE_TICKS;
    unsigned polls_left = TRANSFER_POLL_LIMIT;
    /* Retain a short portion of the caller's budget for the final PE
     * write/readback and status checks, even when no STOP can complete. */
    unsigned abort_ticks = ticks - FINAL_CLEANUP_TICKS;
    adapter->peripheral_reset = false;
    if (!source_requested()) {
        adapter->last_result = CASE_I2C_SOURCE_LOST;
        return false;
    }
    if ((bus_status() & I2C_ISR_BUSY) || !lines_released()) {
        adapter->last_result = CASE_I2C_BUSY;
        adapter->bus_needs_recovery = true;
        return false;
    }

    uint8_t received[SC16_BURST_SIZE];
    uint32_t target = (uint32_t)address << 1;
    uint32_t bytes = (uint32_t)(tx ? count + 1u : 1u);
    bus_clear(clear_flags);
    bus_control(target | (bytes << I2C_CR2_NBYTES_Pos) |
                I2C_CR2_START | (tx ? I2C_CR2_AUTOEND : 0u));
    case_sc16_i2c_result result = wait_for(I2C_ISR_TXIS, start, work_ticks, &polls_left);
    if (result != CASE_I2C_OK) goto failed;
    bus_write(subaddress);

    if (tx) {
        for (size_t i = 0; i < count; ++i) {
            result = wait_for(I2C_ISR_TXIS, start, work_ticks, &polls_left);
            if (result != CASE_I2C_OK) goto failed;
            bus_write(tx[i]);
        }
    } else {
        result = wait_for(I2C_ISR_TC, start, work_ticks, &polls_left);
        if (result != CASE_I2C_OK) goto failed;
        bus_control(target | ((uint32_t)count << I2C_CR2_NBYTES_Pos) |
                    I2C_CR2_START | I2C_CR2_RD_WRN | I2C_CR2_AUTOEND);
        for (size_t i = 0; i < count; ++i) {
            result = wait_for(I2C_ISR_RXNE, start, work_ticks, &polls_left);
            if (result != CASE_I2C_OK) goto failed;
            received[i] = bus_read();
        }
    }
    result = wait_for(I2C_ISR_STOPF, start, work_ticks, &polls_left);
    if (result != CASE_I2C_OK) goto failed;
    bus_clear(I2C_ICR_STOPCF);
    if (rx) {
        for (size_t i = 0; i < count; ++i) rx[i] = received[i];
    }
    adapter->last_result = CASE_I2C_OK;
    return true;

failed:
    adapter->last_result = result;
    abort_transfer(adapter, start, abort_ticks, &polls_left);
    return false;
}
