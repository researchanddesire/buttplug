#include "sc16_bridge.h"

enum {
    REG_FIFO = 0x00,
    REG_IER = 0x01,
    REG_FCR = 0x02,
    REG_IIR = 0x02,
    REG_LCR = 0x03,
    REG_MCR = 0x04,
    REG_LSR = 0x05,
    REG_TCR = 0x06,
    REG_SPR = 0x07,
    REG_TLR = 0x07,
    REG_TXLVL = 0x08,
    REG_RXLVL = 0x09,
    REG_IODIR = 0x0a,
    REG_IOINTENA = 0x0c,
    REG_IOCONTROL = 0x0e,
    REG_EFCR = 0x0f,
    REG_EFR = 0x02,
    REG_DLL = 0x00,
    REG_DLH = 0x01,
    LSR_ERRORS = 0x9e,
};

enum {
    RX_LEVEL,
    RX_LINE_BEFORE,
    RX_FIFO,
    RX_LINE_AFTER,
    TX_SPACE,
    TX_FIFO,
};

typedef struct {
    uint8_t reg;
    uint8_t value;
    uint8_t read_mask; /* Zero means a write. */
} sc16_config_op;

/* NXP Rev. 7.1, sections 7.4 and 8. Enter alternate register banks only
 * for the corresponding writes and readbacks. MCR[1] keeps RTS high
 * until auto RTS is enabled. DSR stays pulled high by the radio board. */
static const sc16_config_op config[] = {
    {REG_LCR, 0x03, 0},
    {REG_IER, 0x00, 0},
    {REG_MCR, 0x00, 0},
    {REG_SPR, 0xa5, 0},
    {REG_SPR, 0xa5, 0xff},
    {REG_SPR, 0x5a, 0},
    {REG_SPR, 0x5a, 0xff},
    {REG_LCR, 0xbf, 0},
    {REG_EFR, 0x10, 0},
    {REG_EFR, 0x10, 0xff},
    {REG_LCR, 0x03, 0},
    {REG_MCR, 0x04, 0},
    {REG_TCR, 0x6c, 0}, /* Stop at 48 and resume at 24 bytes. */
    {REG_TCR, 0x6c, 0xff},
    {REG_TLR, 0x00, 0}, /* Use FCR's 8-byte RX interrupt threshold. */
    {REG_TLR, 0x00, 0xff},
    {REG_MCR, 0x00, 0},
    {REG_MCR, 0x00, 0xf7},
    {REG_LCR, 0x83, 0},
    {REG_DLL, 0x08, 0}, /* 14.7456 MHz / (16 x 8) = 115200. */
    {REG_DLH, 0x00, 0},
    {REG_DLL, 0x08, 0xff},
    {REG_DLH, 0x00, 0xff},
    {REG_LCR, 0x03, 0},
    {REG_EFCR, 0x00, 0}, /* Normal TX/RX. */
    {REG_IOINTENA, 0x00, 0},
    {REG_IOCONTROL, 0x00, 0},
    {REG_IODIR, 0x00, 0},
    {REG_IODIR, 0x00, 0xff},
    {REG_FCR, 0x07, 0},
    /* Stable XTAL clocks are a caller precondition. The subsequent I2C
     * register accesses give the FIFO reset more than two XTAL clocks. */
    {REG_IIR, 0xc0, 0xc0},
    {REG_IER, 0x05, 0},
    {REG_IER, 0x05, 0xff},
    {REG_LCR, 0xbf, 0},
    {REG_EFR, 0xd0, 0}, /* Auto RTS/CTS, no software flow control. */
    {REG_EFR, 0xd0, 0xff},
    {REG_LCR, 0x03, 0},
    {REG_LCR, 0x03, 0xff},
};

_Static_assert((SC16_QUEUE_SIZE & (SC16_QUEUE_SIZE - 1)) == 0,
               "ring size must be a power of two");
_Static_assert(SC16_QUEUE_SIZE <= UINT8_MAX, "ring count must fit");
_Static_assert(sizeof(config) / sizeof(config[0]) <= UINT8_MAX,
               "configuration index must fit");

static void clear_queues(sc16_bridge *bridge)
{
    bridge->rx.head = 0;
    bridge->rx.count = 0;
    bridge->tx.head = 0;
    bridge->tx.count = 0;
    bridge->fifo_count = 0;
    bridge->phase = RX_LEVEL;
}

static void fail(sc16_bridge *bridge, sc16_fault reason)
{
    clear_queues(bridge);
    bridge->fault = reason;
    bridge->state = SC16_FAULT;
}

static unsigned queue_index(unsigned index)
{
    return index & (SC16_QUEUE_SIZE - 1);
}

static void append(sc16_queue *queue, const uint8_t *data, size_t count)
{
    for (size_t index = 0; index < count; ++index) {
        unsigned offset = queue->head + queue->count;
        queue->bytes[queue_index(offset)] = data[index];
        ++queue->count;
    }
}

static void consume(sc16_queue *queue, size_t count)
{
    queue->head = (uint8_t)queue_index(queue->head + count);
    queue->count -= (uint8_t)count;
}

static void copy_front(const sc16_queue *queue, uint8_t *data, size_t count)
{
    for (size_t index = 0; index < count; ++index) {
        data[index] = queue->bytes[queue_index(queue->head + index)];
    }
}

static unsigned minimum(unsigned a, unsigned b)
{
    return a < b ? a : b;
}

static bool transfer(sc16_bridge *bridge, uint8_t reg, const uint8_t *tx,
                     uint8_t *rx, size_t count)
{
    if (bridge->transfer(bridge->context, SC16_ADDRESS, (uint8_t)(reg << 3),
                         tx, rx, count, SC16_TRANSFER_TIMEOUT_US)) {
        return true;
    }
    fail(bridge, SC16_FAULT_BUS);
    return false;
}

static bool read(sc16_bridge *bridge, uint8_t reg, uint8_t *data, size_t count)
{
    return transfer(bridge, reg, NULL, data, count);
}

static bool write(sc16_bridge *bridge, uint8_t reg, const uint8_t *data,
                  size_t count)
{
    return transfer(bridge, reg, data, NULL, count);
}

static bool read_line(sc16_bridge *bridge)
{
    uint8_t lsr;
    if (!read(bridge, REG_LSR, &lsr, 1)) {
        return false;
    }
    bridge->lsr = lsr;
    if (lsr & LSR_ERRORS) {
        fail(bridge, SC16_FAULT_LINE);
        return false;
    }
    return true;
}

static void configure(sc16_bridge *bridge)
{
    const sc16_config_op *op = &config[bridge->config_index];
    if (op->read_mask != 0) {
        uint8_t readback;
        if (!read(bridge, op->reg, &readback, 1)) {
            return;
        }
        if ((readback & op->read_mask) != op->value) {
            fail(bridge, SC16_FAULT_READBACK);
            return;
        }
    } else if (!write(bridge, op->reg, &op->value, 1)) {
        return;
    }
    if (++bridge->config_index == sizeof(config) / sizeof(config[0])) {
        bridge->state = SC16_READY;
    }
}

static bool read_level(sc16_bridge *bridge, uint8_t reg, uint8_t *level)
{
    if (!read(bridge, reg, level, 1)) {
        return false;
    }
    if (*level > SC16_FIFO_SIZE) {
        fail(bridge, SC16_FAULT_FIFO_LEVEL);
        return false;
    }
    return true;
}

static void service(sc16_bridge *bridge)
{
    uint8_t level;
    switch (bridge->phase) {
    case RX_LEVEL:
        if (read_level(bridge, REG_RXLVL, &level)) {
            unsigned capacity = SC16_QUEUE_SIZE - bridge->rx.count;
            bridge->fifo_count = (uint8_t)minimum(SC16_BURST_SIZE,
                                                 minimum(level, capacity));
            bridge->phase = RX_LINE_BEFORE;
        }
        break;
    case RX_LINE_BEFORE:
        if (read_line(bridge)) {
            bridge->phase = bridge->fifo_count ? RX_FIFO : TX_SPACE;
        }
        break;
    case RX_FIFO:
        /* LSR was checked after taking the FIFO count. Characters that arrive
         * after that count cannot be part of this burst. */
        if (read(bridge, REG_FIFO, bridge->burst, bridge->fifo_count)) {
            bridge->phase = RX_LINE_AFTER;
        }
        break;
    case RX_LINE_AFTER:
        if (read_line(bridge)) {
            append(&bridge->rx, bridge->burst, bridge->fifo_count);
            bridge->phase = TX_SPACE;
        }
        break;
    case TX_SPACE:
        if (bridge->tx.count == 0) {
            bridge->phase = RX_LEVEL;
            break;
        }
        if (read_level(bridge, REG_TXLVL, &level)) {
            bridge->fifo_count = (uint8_t)minimum(SC16_BURST_SIZE,
                                      minimum(level, bridge->tx.count));
            bridge->phase = bridge->fifo_count ? TX_FIFO : RX_LEVEL;
        }
        break;
    case TX_FIFO:
        copy_front(&bridge->tx, bridge->burst, bridge->fifo_count);
        if (write(bridge, REG_FIFO, bridge->burst, bridge->fifo_count)) {
            consume(&bridge->tx, bridge->fifo_count);
            bridge->phase = RX_LEVEL;
        }
        break;
    }
}

void sc16_init(sc16_bridge *bridge, sc16_transfer adapter, void *context)
{
    bridge->transfer = adapter;
    bridge->context = context;
    sc16_stop(bridge);
}

bool sc16_start_after_reset(sc16_bridge *bridge)
{
    if (!bridge->transfer || bridge->state == SC16_CONFIGURING ||
        bridge->state == SC16_READY) {
        return false;
    }
    sc16_stop(bridge);
    bridge->state = SC16_CONFIGURING;
    return true;
}

void sc16_stop(sc16_bridge *bridge)
{
    clear_queues(bridge);
    bridge->config_index = 0;
    bridge->lsr = 0;
    bridge->fault = SC16_FAULT_NONE;
    bridge->state = SC16_OFF;
}

sc16_state sc16_step(sc16_bridge *bridge)
{
    if (bridge->state == SC16_CONFIGURING) {
        configure(bridge);
    } else if (bridge->state == SC16_READY) {
        service(bridge);
    }
    return bridge->state;
}

bool sc16_send(sc16_bridge *bridge, const uint8_t *data, size_t count)
{
    if (bridge->state != SC16_READY || (!data && count != 0) ||
        count > (size_t)(SC16_QUEUE_SIZE - bridge->tx.count)) {
        return false;
    }
    append(&bridge->tx, data, count);
    return true;
}

size_t sc16_receive(sc16_bridge *bridge, uint8_t *data, size_t capacity)
{
    if (bridge->state != SC16_READY || !data) {
        return 0;
    }
    size_t count = capacity < bridge->rx.count ? capacity : bridge->rx.count;
    copy_front(&bridge->rx, data, count);
    consume(&bridge->rx, count);
    return count;
}
