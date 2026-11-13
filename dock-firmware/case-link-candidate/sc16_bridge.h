#ifndef SC16_BRIDGE_H
#define SC16_BRIDGE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

enum {
    SC16_ADDRESS = 0x4d,
    SC16_FIFO_SIZE = 64,
    SC16_BURST_SIZE = 8,
    SC16_QUEUE_SIZE = 128,
    SC16_TRANSFER_TIMEOUT_US = 2500,
};

/* Transfer exactly one addressed register. For reads, write subaddress then
 * repeated START and read. For writes, send subaddress and payload together.
 * The deadline includes arbitration, STOP or abort. On false, some bytes
 * may have moved. The adapter serializes access to the shared bus. */
typedef bool (*sc16_transfer)(void *context, uint8_t address,
                             uint8_t subaddress, const uint8_t *tx,
                             uint8_t *rx, size_t count, uint32_t timeout_us);

typedef enum {
    SC16_OFF,
    SC16_CONFIGURING,
    SC16_READY,
    SC16_FAULT,
} sc16_state;

typedef enum {
    SC16_FAULT_NONE,
    SC16_FAULT_BUS,
    SC16_FAULT_READBACK,
    SC16_FAULT_FIFO_LEVEL,
    SC16_FAULT_LINE,
} sc16_fault;

typedef struct {
    uint8_t bytes[SC16_QUEUE_SIZE];
    uint8_t head;
    uint8_t count;
} sc16_queue;

/* Single task owner. Treat fields as private, except state, fault and lsr
 * for diagnostics. No API here is called from an interrupt. */
typedef struct {
    sc16_transfer transfer;
    void *context;
    sc16_queue rx, tx;
    uint8_t burst[SC16_BURST_SIZE];
    uint8_t config_index;
    uint8_t phase;
    uint8_t fifo_count;
    uint8_t lsr;
    sc16_state state;
    sc16_fault fault;
} sc16_bridge;

void sc16_init(sc16_bridge *bridge, sc16_transfer transfer, void *context);

/* Start only after the board has enabled qualified radio power, the shared
 * hardware reset has completed, and the qualified crystal startup delay has
 * elapsed. Recovery from a fault requires a fresh hardware reset first. */
bool sc16_start_after_reset(sc16_bridge *bridge);

/* On radio power loss, discard session bytes and stop issuing bus requests.
 * The board owns enable, reset, clock qualification and IRQ scheduling. */
void sc16_stop(sc16_bridge *bridge);

/* Advance at most one bounded transfer. Call repeatedly in scheduled slices
 * even without an IRQ edge. The bridge never waits for a FIFO to fill or drain. */
sc16_state sc16_step(sc16_bridge *bridge);

/* All-or-nothing software enqueue. Success means queued, not transmitted. */
bool sc16_send(sc16_bridge *bridge, const uint8_t *data, size_t count);

/* Consume up to capacity confirmed RX bytes. */
size_t sc16_receive(sc16_bridge *bridge, uint8_t *data, size_t capacity);

#endif
