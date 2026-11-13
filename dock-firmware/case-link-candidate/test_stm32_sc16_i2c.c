#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "stm32_sc16_i2c.h"
#include "stm32l071xx.h"
#include "board_pins.h"
#include "test_stm32_sc16_i2c_model.h"

I2C_TypeDef model_i2c;
GPIO_TypeDef model_gpio_b, model_gpio_c, model_gpio_h;
RCC_TypeDef model_rcc;
TIM_TypeDef model_tim;

typedef enum {
    COMPLETE, NO_ACK, ARBITRATION_LOST, SPURIOUS_BERR, EARLY_STOP,
    SOURCE_DROP, STALL, WEDGED, PARTIAL_READ_STALL, FINAL_STOP_STALL
} behavior;

static struct {
    behavior behavior;
    uint32_t tick, started_at, controls[3];
    unsigned starts, stops, resets, clears, flushes, tx_count, rx_count, left;
    uint8_t written[9];
    bool read, auto_end, reset_settled, timer_frozen;
} bus;

uint32_t now_ticks(void)
{
    if (!bus.timer_frozen) bus.tick += 20;
    return bus.tick;
}

uint32_t bus_status(void)
{
    return I2C2->ISR;
}

void bus_control(uint32_t value)
{
    if (value & I2C_CR2_STOP) {
        assert(I2C2->ISR & I2C_ISR_BUSY);
        ++bus.stops;
        if (bus.behavior != WEDGED) I2C2->ISR = I2C_ISR_STOPF;
        return;
    }
    assert(value & I2C_CR2_START);
    assert((value & I2C_CR2_SADD) == SC16_ADDRESS * 2);
    assert(bus.starts < sizeof(bus.controls) / sizeof(bus.controls[0]));
    bus.controls[bus.starts++] = value;
    I2C2->CR2 = value & ~I2C_CR2_START;
    bus.left = (value & I2C_CR2_NBYTES) >> I2C_CR2_NBYTES_Pos;
    bus.read = (value & I2C_CR2_RD_WRN) != 0;
    bus.auto_end = (value & I2C_CR2_AUTOEND) != 0;
    if (bus.starts == 1) bus.started_at = bus.tick;
    else assert(I2C2->ISR == (I2C_ISR_BUSY | I2C_ISR_TC));
    I2C2->ISR = I2C_ISR_BUSY;
    switch (bus.behavior) {
    case NO_ACK:
        I2C2->ISR = I2C_ISR_NACKF | I2C_ISR_STOPF | I2C_ISR_TXIS;
        return;
    case ARBITRATION_LOST:
        I2C2->ISR |= I2C_ISR_ARLO;
        return;
    case WEDGED:
        return;
    default:
        I2C2->ISR |= bus.read ? I2C_ISR_RXNE : I2C_ISR_TXIS;
    }
    if (bus.behavior == SPURIOUS_BERR) I2C2->ISR |= I2C_ISR_BERR;
}

static void finish_byte(void)
{
    assert(bus.left);
    if (!--bus.left) I2C2->ISR = bus.auto_end ? I2C_ISR_STOPF : I2C_ISR_BUSY | I2C_ISR_TC;
}

void bus_write(uint8_t value)
{
    assert(I2C2->ISR & I2C_ISR_TXIS);
    assert(!bus.read && bus.tx_count < sizeof(bus.written));
    bus.written[bus.tx_count++] = value;
    finish_byte();
    switch (bus.behavior) {
    case STALL:
        I2C2->ISR = I2C_ISR_BUSY;
        break;
    case SOURCE_DROP:
        model_gpio_c.IDR = 0;
        break;
    case EARLY_STOP:
        I2C2->ISR = I2C_ISR_STOPF | I2C_ISR_TXIS;
        break;
    default:
        break;
    }
}

uint8_t bus_read(void)
{
    assert(I2C2->ISR & I2C_ISR_RXNE);
    assert(bus.read);
    finish_byte();
    if (bus.behavior == PARTIAL_READ_STALL) I2C2->ISR = I2C_ISR_BUSY;
    if (bus.behavior == FINAL_STOP_STALL && !bus.left) I2C2->ISR = I2C_ISR_BUSY;
    return (uint8_t)(0x40u + bus.rx_count++);
}

void bus_clear(uint32_t bits)
{
    assert((bits & I2C_ICR_TIMOUTCF) == 0); /* I2C2 has no SMBus timeout. */
    if (bits == I2C_ICR_BERRCF) ++bus.clears;
    I2C2->ISR &= ~bits;
}

void bus_flush_tx(void) { ++bus.flushes; }

void peripheral_enable(uint32_t value)
{
    I2C2->CR1 = value;
    if (value & I2C_CR1_PE) {
        assert(bus.reset_settled);
    } else {
        I2C2->ISR = 0;
        I2C2->CR2 = 0;
        ++bus.resets;
    }
}

void apb_settle(void)
{
    assert((I2C2->CR1 & I2C_CR1_PE) == 0);
    bus.reset_settled = true;
    bus.tick += 3;
}

static case_sc16_i2c setup(behavior scenario)
{
    memset(&bus, 0, sizeof(bus));
    bus.behavior = scenario;
    I2C2->ISR = 0;
    I2C2->CR1 = I2C_CR1_PE;
    I2C2->TIMINGR = 0x0042272bu;
    RCC->APB1ENR = RCC_APB1ENR_I2C2EN;
    RCC->ICSCR = RCC_ICSCR_MSIRANGE_6;
    RCC->IOPENR = RCC_IOPENR_GPIOHEN;
    model_gpio_b.IDR = (1u << MON_I2C_SCL_PIN) | (1u << MON_I2C_SDA_PIN);
    model_gpio_c.IDR = 1u << SOURCE_OK_PIN;
    GPIOH->MODER = 1u << 2;
    GPIOH->ODR = 1u << 1;
    case_sc16_i2c adapter;
    assert(case_sc16_i2c_init(&adapter));
    assert(TIM2->ARR == UINT16_MAX && TIM2->PSC == 0);
    assert(I2C2->TIMINGR == 0x0042272bu);
    return adapter;
}

static bool transfer(case_sc16_i2c *adapter, const uint8_t *tx, uint8_t *rx, size_t count)
{
    return case_sc16_i2c_transfer(adapter, SC16_ADDRESS, 0x78, tx, rx, count, 2500);
}

static void normal_transfers(void)
{
    uint8_t data[8] = {0, 1, 2, 3, 4, 5, 6, 7};
    case_sc16_i2c adapter = setup(COMPLETE);
    assert(transfer(&adapter, data, NULL, sizeof(data)));
    assert(bus.starts == 1 && !bus.stops && !bus.resets);
    assert(bus.controls[0] == (0x9au | I2C_CR2_AUTOEND | I2C_CR2_START | (9u << I2C_CR2_NBYTES_Pos)));
    assert(bus.tx_count == 9 && bus.written[0] == 0x78 && !memcmp(bus.written + 1, data, sizeof(data)));

    adapter = setup(SPURIOUS_BERR);
    assert(transfer(&adapter, NULL, data, sizeof(data)));
    assert(bus.starts == 2 && !bus.stops && !bus.resets && bus.clears == 2);
    assert(bus.controls[0] == (0x9au | I2C_CR2_START | (1u << I2C_CR2_NBYTES_Pos)));
    assert(bus.controls[1] == (0x9au | I2C_CR2_AUTOEND | I2C_CR2_START | I2C_CR2_RD_WRN | (8u << I2C_CR2_NBYTES_Pos)));
    for (unsigned i = 0; i < sizeof(data); ++i) assert(data[i] == 0x40u + i);
}

static void faults(void)
{
    uint8_t data[] = {1, 2};
    case_sc16_i2c adapter = setup(NO_ACK);
    assert(!transfer(&adapter, data, NULL, sizeof(data)) && adapter.last_result == CASE_I2C_NACK);
    assert(!bus.tx_count && !bus.stops && !bus.resets && bus.flushes == 1);
    assert(!adapter.bus_needs_recovery);

    adapter = setup(ARBITRATION_LOST);
    assert(!transfer(&adapter, data, NULL, sizeof(data)) && adapter.last_result == CASE_I2C_ARBITRATION_LOST);
    assert(!bus.stops && !bus.resets && adapter.bus_needs_recovery);

    adapter = setup(EARLY_STOP);
    assert(!transfer(&adapter, data, NULL, sizeof(data)) && adapter.last_result == CASE_I2C_SHORT_TRANSFER);
    assert(bus.tx_count == 1 && !bus.stops && !bus.resets);

    adapter = setup(SOURCE_DROP);
    assert(!transfer(&adapter, data, NULL, sizeof(data)) && adapter.last_result == CASE_I2C_SOURCE_LOST);
    assert(bus.tx_count == 1 && bus.stops == 1 && !bus.resets);

    adapter = setup(STALL);
    bus.tick = UINT16_MAX - 30; /* Deadline crosses timer wrap. */
    assert(!transfer(&adapter, data, NULL, sizeof(data)) && adapter.last_result == CASE_I2C_DEADLINE);
    assert(bus.tx_count == 1 && bus.stops == 1 && !bus.resets);
    assert(bus.tick - bus.started_at < 10000);

    adapter = setup(WEDGED);
    assert(!transfer(&adapter, data, NULL, sizeof(data)) && adapter.last_result == CASE_I2C_DEADLINE);
    assert(bus.stops == 1 && bus.resets == 1 && adapter.peripheral_reset && adapter.bus_needs_recovery);
    assert(bus.tick - bus.started_at < 10000 && I2C2->CR1 == I2C_CR1_PE);
    assert(!transfer(&adapter, data, NULL, sizeof(data)) && adapter.last_result == CASE_I2C_NOT_READY);
    assert(bus.starts == 1);

    adapter = setup(PARTIAL_READ_STALL);
    assert(!transfer(&adapter, NULL, data, sizeof(data)) && adapter.last_result == CASE_I2C_DEADLINE);
    assert(bus.rx_count == 1 && data[0] == 1 && data[1] == 2);

    adapter = setup(FINAL_STOP_STALL);
    assert(!transfer(&adapter, NULL, data, sizeof(data)) && adapter.last_result == CASE_I2C_DEADLINE);
    assert(bus.rx_count == 2 && bus.stops == 1 && data[0] == 1 && data[1] == 2);

    adapter = setup(WEDGED);
    bus.timer_frozen = true;
    assert(!transfer(&adapter, data, NULL, sizeof(data)) && adapter.last_result == CASE_I2C_DEADLINE);
    assert(bus.stops == 1 && bus.resets == 1 && adapter.bus_needs_recovery);
}

static void no_start_paths(void)
{
    uint8_t data = 0;
    case_sc16_i2c adapter = setup(COMPLETE);
    assert(!case_sc16_i2c_transfer(&adapter, 0x48, 0, &data, NULL, 1, 2500));
    assert(adapter.last_result == CASE_I2C_BAD_ARGUMENT && !bus.starts);
    GPIOH->MODER = 0;
    assert(!transfer(&adapter, &data, NULL, 1) && adapter.last_result == CASE_I2C_SOURCE_LOST);
    GPIOH->MODER = 1u << 2;
    I2C2->ISR = I2C_ISR_BUSY;
    assert(!transfer(&adapter, &data, NULL, 1) && adapter.last_result == CASE_I2C_BUSY);
    assert(adapter.bus_needs_recovery && !bus.starts && !bus.stops && !bus.resets);

    adapter = setup(COMPLETE);
    GPIOB->IDR = 0;
    assert(!transfer(&adapter, &data, NULL, 1) && adapter.last_result == CASE_I2C_BUSY);
    assert(adapter.bus_needs_recovery && !bus.starts);

    adapter = setup(COMPLETE);
    RCC->APB1ENR &= ~RCC_APB1ENR_TIM2EN;
    assert(!transfer(&adapter, &data, NULL, 1) && adapter.last_result == CASE_I2C_NOT_READY);
    assert(!bus.starts);
}

int main(void)
{
    normal_transfers();
    faults();
    no_start_paths();
    puts("SC16 I2C2 adapter: repeated START, W1C flags, source gate, deadline wrap, STOP/reset and recovery latch passed");
    return 0;
}
