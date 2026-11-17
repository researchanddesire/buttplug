#include "board.h"
#include "host_control.h"
#include "stm32l071xx.h"

enum { SCL = 1u << 0, SDA = 1u << 1, LINES = SCL | SDA };

static void line(unsigned mask, bool release)
{
    GPIOH->BSRR = release ? mask : mask << 16;
}

static bool high(unsigned mask)
{
    return (GPIOH->IDR & mask) == mask;
}

static bool clock_high(uint32_t start)
{
    line(SCL, true);
    while (!high(SCL)) {
        if (board_millis() - start >= 3u) return false;
    }
    board_delay_us(5);
    return board_millis() - start < 3u;
}

static bool bit(uint32_t start, bool release, bool *sample)
{
    line(SDA, release);
    board_delay_us(5);
    if (!clock_high(start)) return false;
    if (sample) *sample = high(SDA);
    line(SCL, false);
    return true;
}

static bool send_byte(uint32_t start, uint8_t value)
{
    for (unsigned mask = 0x80; mask; mask >>= 1) {
        bool level;
        bool release = (value & mask) != 0;
        if (!bit(start, release, &level) || level != release) return false;
    }
    bool nack;
    return bit(start, true, &nack) && !nack;
}

static bool receive_byte(uint32_t start, uint8_t *value, bool last)
{
    uint8_t result = 0;
    for (unsigned n = 0; n < 8; ++n) {
        bool level;
        if (!bit(start, true, &level)) return false;
        result = (uint8_t)((result << 1) | (uint8_t)level);
    }
    *value = result;
    return bit(start, last, 0);
}

void board_host_bus_init(void)
{
    /* U201.5 PH0=SCL and U201.6 PH1=SDA, isolated from MON_I2C. */
    RCC->IOPENR |= RCC_IOPENR_GPIOHEN;
    (void)RCC->IOPENR;
    line(LINES, true);
    GPIOH->OTYPER |= LINES;
    GPIOH->OSPEEDR &= ~15u;
    GPIOH->PUPDR &= ~15u;
    GPIOH->MODER = (GPIOH->MODER & ~15u) | 5u;
}

bool board_host_bus_transfer(bool read, uint8_t *data, unsigned length)
{
    if (length != (read ? HOST_STATUS_BYTES : HOST_COMMAND_BYTES) || !high(LINES))
        return false;
    uint32_t start = board_millis();
    board_delay_us(5);
    line(SDA, false);
    board_delay_us(5);
    line(SCL, false);
    bool ok = send_byte(start, (HOST_CONTROL_ADDRESS << 1) | (uint8_t)read);
    for (unsigned n = 0; ok && n < length; ++n) {
        ok = read ? receive_byte(start, &data[n], n + 1 == length)
                  : send_byte(start, data[n]);
    }
    line(SCL, false);
    line(SDA, false);
    board_delay_us(5);
    bool stopped = clock_high(start);
    line(LINES, true);
    return ok && stopped;
}
