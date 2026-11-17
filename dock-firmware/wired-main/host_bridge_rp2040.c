#include "host_bridge.h"
#include "hardware/sync.h"
#include "pico/i2c_slave.h"
#include "pico/stdlib.h"
#include "hardware/watchdog.h"
#include <string.h>

enum { HOST_SDA = 0, HOST_SCL = 1, LOCAL_READY = 2, USB_BREAK = 3,
       CONTACT_OK = 4, LIMIT_FAULT_N = 5 };
static host_control control;
static bool requested;
static bool have_command;
static uint32_t last_command_ms;
static volatile uint8_t mailbox;
static volatile bool mailbox_ready;
static uint8_t rx[HOST_COMMAND_BYTES];
static unsigned rx_length;
static unsigned tx_index;
static uint8_t published[HOST_STATUS_BYTES], tx[HOST_STATUS_BYTES];
static uint8_t sequence;

static void drain_write(i2c_inst_t *i2c)
{
    while (i2c_get_read_available(i2c)) {
        uint8_t byte = i2c_read_byte_raw(i2c);
        if (rx_length < HOST_COMMAND_BYTES) rx[rx_length++] = byte;
        else rx_length = HOST_COMMAND_BYTES + 1u;
    }
}

static void bus_event(i2c_inst_t *i2c, i2c_slave_event_t event)
{
    if (event == I2C_SLAVE_RECEIVE) {
        drain_write(i2c);
    } else if (event == I2C_SLAVE_REQUEST) {
        if (!tx_index) memcpy(tx, published, sizeof(tx));
        uint8_t value = tx_index < HOST_STATUS_BYTES ? tx[tx_index++] : 0xff;
        i2c_write_byte_raw(i2c, value);
    } else {
        /* The SDK dispatches FINISH before a coincident RX_FULL callback. */
        drain_write(i2c);
        bool local;
        if (rx_length == HOST_COMMAND_BYTES && host_control_command(rx, &local)) {
            mailbox = (uint8_t)local;
            mailbox_ready = true;
        }
        rx_length = 0;
        tx_index = 0;
    }
}

void host_bridge_init(void)
{
    gpio_init(LOCAL_READY);
    gpio_init(USB_BREAK);
    gpio_put(LOCAL_READY, false);
    gpio_put(USB_BREAK, false);
    gpio_set_dir(LOCAL_READY, GPIO_OUT);
    gpio_set_dir(USB_BREAK, GPIO_OUT);
    gpio_init(CONTACT_OK);
    gpio_init(LIMIT_FAULT_N);
    gpio_set_function(HOST_SDA, GPIO_FUNC_I2C);
    gpio_set_function(HOST_SCL, GPIO_FUNC_I2C);
    host_bridge_publish(0, 0);
    i2c_init(i2c0, 100000);
    i2c_slave_init(i2c0, HOST_CONTROL_ADDRESS, bus_event);
    /* Recover PC selection if the event loop stops servicing the lease. */
    watchdog_enable(HOST_LEASE_MS, false);
}

host_outputs host_bridge_step(uint32_t now, bool *fault, bool *contact)
{
    watchdog_update();
    uint32_t irqs = save_and_disable_interrupts();
    if (mailbox_ready) {
        requested = mailbox != 0;
        last_command_ms = now;
        have_command = true;
        mailbox_ready = false;
    }
    restore_interrupts(irqs);
    *fault = !gpio_get(LIMIT_FAULT_N);
    *contact = gpio_get(CONTACT_OK);
    bool permitted = *contact && !*fault;
    if (!permitted || now - last_command_ms >= HOST_LEASE_MS) have_command = false;
    return host_control_step(&control, now, requested && have_command, permitted);
}

void host_bridge_select(host_outputs output)
{
    /* Blank before touching selection. Release blank after selection. */
    if (output.blank) gpio_put(USB_BREAK, true);
    gpio_put(LOCAL_READY, output.local);
    if (!output.blank) gpio_put(USB_BREAK, false);
}

void host_bridge_publish(uint8_t flags, int16_t centi_c)
{
    uint16_t bits = (flags & HOST_STATUS_TIP_VALID) ? (uint16_t)centi_c : 0;
    uint8_t packet[HOST_STATUS_BYTES] = {HOST_CONTROL_VERSION, flags, sequence++,
                                       (uint8_t)bits, (uint8_t)(bits >> 8), 0, 0, 0};
    packet[HOST_STATUS_BYTES - 1u] = host_control_crc(packet, HOST_STATUS_BYTES - 1u);
    uint32_t irqs = save_and_disable_interrupts();
    memcpy(published, packet, sizeof(packet));
    restore_interrupts(irqs);
}
