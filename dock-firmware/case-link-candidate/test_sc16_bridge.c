#include "sc16_bridge.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    uint8_t lcr, mcr, efr, ier, tcr, tlr, dll, dlh, spr, iodir;
    uint8_t rx[SC16_FIFO_SIZE], tx[SC16_QUEUE_SIZE * 2];
    unsigned rx_count, tx_count, tx_space, transfers;
    uint8_t line_fault;
    bool fifo_enabled;
    bool bad_scratch;
    bool ignore_second_scratch;
    bool fail_fifo_read;
    bool fail_fifo_write;
    bool line_after_read;
} fake_uart;

static void mock_init(fake_uart *uart)
{
    memset(uart, 0, sizeof(*uart));
    uart->tx_space = SC16_FIFO_SIZE;
    uart->dll = 42;
    uart->dlh = 1;
}

static void register_access(uint8_t *target, const uint8_t *tx, uint8_t *rx)
{
    if (rx) {
        *rx = *target;
    } else {
        *target = *tx;
    }
}

static bool mock_transfer(void *context, uint8_t address, uint8_t subaddress,
                          const uint8_t *tx, uint8_t *rx, size_t count,
                          uint32_t timeout_us)
{
    fake_uart *uart = context;
    assert(address == 0x4d && (subaddress & 0x87) == 0);
    assert((rx != NULL) != (tx != NULL));
    assert(count > 0 && count <= SC16_BURST_SIZE);
    assert(timeout_us == SC16_TRANSFER_TIMEOUT_US);
    ++uart->transfers;
    unsigned reg = subaddress >> 3;
    if (reg != 0) {
        assert(count == 1);
    }
    if (reg == 3) {
        register_access(&uart->lcr, tx, rx);
        return true;
    }
    if (uart->lcr == 0xbf) {
        assert(reg == 2);
        if (tx && (*tx & 0xc0) != 0) {
            assert(uart->tcr == 0x6c && uart->tlr == 0);
            assert(uart->dll == 8 && uart->dlh == 0);
            assert(uart->fifo_enabled && uart->ier == 5);
        }
        register_access(&uart->efr, tx, rx);
        return true;
    }
    if (uart->lcr == 0x83) {
        assert(count == 1 && uart->ier == 0);
        assert(reg == 0 || reg == 1);
        register_access(reg == 0 ? &uart->dll : &uart->dlh, tx, rx);
        return true;
    }
    assert(uart->lcr == 3);
    if (reg == 0) {
        assert(uart->fifo_enabled && uart->efr == 0xd0);
        if (rx) {
            assert(count <= uart->rx_count);
            if (uart->fail_fifo_read) {
                /* Simulate an ambiguous partial transfer. */
                *rx = uart->rx[0];
                return false;
            }
            memcpy(rx, uart->rx, count);
            memmove(uart->rx, uart->rx + count, uart->rx_count - count);
            uart->rx_count -= (unsigned)count;
            if (uart->line_after_read) {
                uart->line_fault = 0x02;
            }
        } else {
            assert(count <= uart->tx_space);
            assert(count <= sizeof(uart->tx) - uart->tx_count);
            if (uart->fail_fifo_write) {
                uart->tx[uart->tx_count++] = tx[0];
                return false;
            }
            memcpy(uart->tx + uart->tx_count, tx, count);
            uart->tx_count += (unsigned)count;
            uart->tx_space -= (unsigned)count;
        }
        return true;
    }
    switch (reg) {
    case 1:
        register_access(&uart->ier, tx, rx);
        break;
    case 2:
        if (tx) {
            assert(*tx == 7 && uart->efr == 0x10);
            uart->fifo_enabled = true;
        } else {
            *rx = uart->fifo_enabled ? 0xc1 : 0x01;
        }
        break;
    case 4:
        register_access(&uart->mcr, tx, rx);
        break;
    case 5:
        assert(rx);
        *rx = (uint8_t)(0x60 | uart->line_fault |
                        (uart->rx_count ? 1 : 0));
        uart->line_fault &= (uint8_t)~0x02; /* LSR read clears overrun. */
        break;
    case 6:
        assert(uart->mcr == 4 && uart->efr == 0x10);
        register_access(&uart->tcr, tx, rx);
        break;
    case 7:
        if (uart->mcr == 4) {
            assert(uart->efr == 0x10);
            register_access(&uart->tlr, tx, rx);
        } else if (rx && uart->bad_scratch) {
            *rx = 0;
        } else if (tx && *tx == 0x5a && uart->ignore_second_scratch) {
            return true;
        } else {
            register_access(&uart->spr, tx, rx);
        }
        break;
    case 8:
        assert(rx);
        *rx = (uint8_t)uart->tx_space;
        break;
    case 9:
        assert(rx);
        *rx = (uint8_t)uart->rx_count;
        break;
    case 0x0a:
        register_access(&uart->iodir, tx, rx);
        break;
    case 0x0c:
    case 0x0e:
    case 0x0f:
        assert(tx && *tx == 0);
        break;
    default:
        assert(!"unexpected register");
    }
    return true;
}

static void step(sc16_bridge *bridge, fake_uart *uart, unsigned slices)
{
    for (unsigned i = 0; i < slices; ++i) {
        unsigned before = uart->transfers;
        sc16_step(bridge);
        assert(uart->transfers - before <= 1);
    }
}

static void start(sc16_bridge *bridge, fake_uart *uart)
{
    mock_init(uart);
    sc16_init(bridge, mock_transfer, uart);
    assert(sc16_start_after_reset(bridge));
    assert(!sc16_start_after_reset(bridge));
    step(bridge, uart, 38);
    assert(bridge->state == SC16_READY);
    assert(uart->transfers == 38 && !sc16_start_after_reset(bridge));
    assert(uart->tcr == 0x6c && uart->efr == 0xd0 &&
           uart->lcr == 3 && uart->iodir == 0);
}

static void flow_and_wrap(void)
{
    sc16_bridge bridge;
    fake_uart uart;
    uint8_t pattern[SC16_QUEUE_SIZE], out[SC16_QUEUE_SIZE];
    for (size_t i = 0; i < sizeof(pattern); ++i) {
        pattern[i] = (uint8_t)(i * 19 + 7);
    }
    start(&bridge, &uart);
    uart.tx_space = 0;
    assert(sc16_send(&bridge, pattern, sizeof(pattern)));
    assert(!sc16_send(&bridge, pattern, 1));
    step(&bridge, &uart, 9);
    assert(uart.tx_count == 0 && bridge.tx.count == SC16_QUEUE_SIZE);
    uart.tx_space = 61;
    step(&bridge, &uart, 46);
    assert(uart.tx_count == 61 && bridge.tx.count == 67);
    assert(sc16_send(&bridge, pattern, 61));
    for (unsigned i = 0; i < 2; ++i) {
        uart.tx_space = SC16_FIFO_SIZE;
        step(&bridge, &uart, 50);
    }
    assert(uart.tx_count == 189 && bridge.tx.count == 0);
    assert(memcmp(uart.tx, pattern, sizeof(pattern)) == 0);
    assert(memcmp(uart.tx + sizeof(pattern), pattern, 61) == 0);
    for (unsigned i = 0; i < 2; ++i) {
        memcpy(uart.rx, pattern + i * SC16_FIFO_SIZE, SC16_FIFO_SIZE);
        uart.rx_count = SC16_FIFO_SIZE;
        step(&bridge, &uart, 50);
    }
    assert(bridge.rx.count == SC16_QUEUE_SIZE);
    memcpy(uart.rx, pattern, 16);
    uart.rx_count = 16;
    step(&bridge, &uart, 12);
    assert(uart.rx_count == 16);
    assert(sc16_receive(&bridge, out, 61) == 61);
    assert(memcmp(out, pattern, 61) == 0);
    step(&bridge, &uart, 16);
    assert(uart.rx_count == 0);
    assert(sc16_receive(&bridge, out, sizeof(out)) == 83);
    assert(memcmp(out, pattern + 61, 67) == 0);
    assert(memcmp(out + 67, pattern, 16) == 0);
    /* Below the eight-byte interrupt watermark, polling still drains data. */
    uart.rx[0] = 0x5a;
    uart.rx_count = 1;
    step(&bridge, &uart, 8);
    assert(sc16_receive(&bridge, out, sizeof(out)) == 1 && out[0] == 0x5a);
}

static void line_faults(void)
{
    static const uint8_t errors[] = {0x02, 0x04, 0x08, 0x10, 0x80};
    for (size_t i = 0; i < sizeof(errors); ++i) {
        sc16_bridge bridge;
        fake_uart uart;
        uint8_t out;
        start(&bridge, &uart);
        uart.rx[0] = 0x7e;
        uart.rx_count = 1;
        uart.line_fault = errors[i];
        step(&bridge, &uart, 8);
        assert(bridge.state == SC16_FAULT && bridge.fault == SC16_FAULT_LINE);
        assert(bridge.lsr & errors[i]);
        assert(sc16_receive(&bridge, &out, 1) == 0);
        assert(uart.rx_count == 1);
    }
    sc16_bridge bridge;
    fake_uart uart;
    uint8_t out;
    start(&bridge, &uart);
    uart.rx_count = 1;
    uart.line_after_read = true;
    step(&bridge, &uart, 8);
    assert(bridge.fault == SC16_FAULT_LINE && uart.rx_count == 0);
    assert(sc16_receive(&bridge, &out, 1) == 0);
}

static void transfer_failure(void)
{
    sc16_bridge bridge;
    fake_uart uart;
    uint8_t out;
    start(&bridge, &uart);
    uart.rx_count = 1;
    uart.fail_fifo_read = true;
    step(&bridge, &uart, 8);
    assert(bridge.state == SC16_FAULT && bridge.fault == SC16_FAULT_BUS);
    assert(sc16_receive(&bridge, &out, 1) == 0);
    start(&bridge, &uart);
    uart.fail_fifo_write = true;
    const uint8_t command[] = {0x41, 0x54, 0x0d};
    assert(sc16_send(&bridge, command, sizeof(command)));
    step(&bridge, &uart, 8);
    assert(bridge.state == SC16_FAULT && bridge.fault == SC16_FAULT_BUS);
    assert(!sc16_send(&bridge, command, sizeof(command)));
    unsigned transfers = uart.transfers;
    step(&bridge, &uart, 50);
    assert(uart.transfers == transfers && uart.tx_count == 1);
}

static void readback_and_reset(void)
{
    sc16_bridge bridge;
    fake_uart uart;
    uint8_t out;
    mock_init(&uart);
    uart.bad_scratch = true;
    sc16_init(&bridge, mock_transfer, &uart);
    assert(sc16_start_after_reset(&bridge));
    step(&bridge, &uart, 9);
    assert(bridge.state == SC16_FAULT && bridge.fault == SC16_FAULT_READBACK);
    assert(uart.transfers == 5 && uart.efr == 0);
    mock_init(&uart);
    uart.spr = 0xa5; /* Scratch retains its value across hardware reset. */
    uart.ignore_second_scratch = true;
    assert(sc16_start_after_reset(&bridge));
    step(&bridge, &uart, 9);
    assert(bridge.state == SC16_FAULT && bridge.fault == SC16_FAULT_READBACK);
    assert(uart.transfers == 7 && uart.efr == 0);
    mock_init(&uart);
    assert(sc16_start_after_reset(&bridge));
    step(&bridge, &uart, 38);
    assert(bridge.state == SC16_READY && bridge.fault == SC16_FAULT_NONE);
    uart.rx_count = 65;
    step(&bridge, &uart, 1);
    assert(bridge.fault == SC16_FAULT_FIFO_LEVEL);
    start(&bridge, &uart);
    uart.rx[0] = 0x7e;
    uart.rx_count = 1;
    step(&bridge, &uart, 4);
    assert(bridge.rx.count == 1);
    assert(sc16_send(&bridge, uart.rx, 1));
    sc16_stop(&bridge);
    assert(sc16_receive(&bridge, &out, 1) == 0 && bridge.tx.count == 0);
    unsigned transfers = uart.transfers;
    step(&bridge, &uart, 50);
    assert(bridge.state == SC16_OFF && uart.transfers == transfers);
    sc16_init(&bridge, NULL, NULL);
    assert(!sc16_start_after_reset(&bridge));
}

int main(void)
{
    flow_and_wrap();
    line_faults();
    transfer_failure();
    readback_and_reset();
    puts("SC16 bridge: banked init, 8-byte slices, FIFO backpressure and wrap, short RX, line faults, ambiguous I2C failures, and reset passed");
    return 0;
}
