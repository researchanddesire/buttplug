#include "nina_startup.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    sc16_bridge bridge;
    nina_startup startup;
    uint32_t now_ms;
} fixture;

static void init(fixture *test, uint32_t now_ms)
{
    sc16_init(&test->bridge, NULL, NULL);
    nina_startup_reset(&test->startup);
    assert(!nina_startup_begin(&test->startup, &test->bridge, now_ms));
    test->bridge.state = SC16_READY;
    test->now_ms = now_ms;
    assert(nina_startup_begin(&test->startup, &test->bridge, now_ms));
    assert(!nina_startup_begin(&test->startup, &test->bridge, now_ms));
}

/* Seed the software RX queue in place of the independently tested SC16
 * transfer path. The production enqueue/dequeue functions remain linked. */
static void feed(fixture *test, const char *data)
{
    sc16_queue *rx = &test->bridge.rx;
    while (*data != '\0') {
        assert(rx->count < SC16_QUEUE_SIZE);
        rx->bytes[(rx->head + rx->count) % SC16_QUEUE_SIZE] = (uint8_t)*data++;
        ++rx->count;
    }
}

static void expect_tx(fixture *test, const char *command)
{
    sc16_queue *tx = &test->bridge.tx;
    assert(tx->count == strlen(command));
    for (size_t index = 0; command[index] != '\0'; ++index) {
        assert(tx->bytes[(tx->head + index) % SC16_QUEUE_SIZE] == (uint8_t)command[index]);
    }
    tx->head = (uint8_t)((tx->head + tx->count) % SC16_QUEUE_SIZE);
    tx->count = 0;
}

static void step(fixture *test, uint32_t advance_ms, nina_startup_state expected)
{
    test->now_ms += advance_ms;
    assert(nina_startup_step(&test->startup, &test->bridge, test->now_ms) == expected);
    assert(test->startup.state == expected);
}

static void send_at(fixture *test)
{
    step(test, NINA_STARTUP_DRAIN_QUIET_MS, NINA_STARTUP_SEND_AT);
    step(test, 1, NINA_STARTUP_WAIT_AT);
    expect_tx(test, "AT\r");
}

static void send_umrs(fixture *test)
{
    send_at(test);
    feed(test, "\r\nOK\r\n");
    step(test, 1, NINA_STARTUP_SEND_UMRS);
    step(test, 1, NINA_STARTUP_WAIT_UMRS);
    expect_tx(test, "AT+UMRS?\r");
}

static void expect_failure(fixture *test, nina_startup_fault fault)
{
    assert(test->startup.fault == fault);
    assert(!nina_startup_begin(&test->startup, &test->bridge, test->now_ms));
    step(test, 5000, NINA_STARTUP_FAILED);
    assert(test->startup.fault == fault);
    expect_tx(test, "");
}

static void split_and_drain(void)
{
    fixture test;
    init(&test, UINT32_MAX - 40);
    test.bridge.rx.head = SC16_QUEUE_SIZE - 2;
    test.bridge.tx.head = SC16_QUEUE_SIZE - 1;
    feed(&test, "\r\n+STARTUP\r\n\r\n+UMRS:115200,1,8,1,1\r\nOK\r\n");
    step(&test, 5, NINA_STARTUP_DRAIN);
    assert(test.bridge.rx.count > 0);
    step(&test, 5, NINA_STARTUP_DRAIN);
    assert(test.bridge.rx.count == 0);
    step(&test, NINA_STARTUP_DRAIN_QUIET_MS - 1, NINA_STARTUP_DRAIN);
    expect_tx(&test, "");
    step(&test, 1, NINA_STARTUP_SEND_AT);
    step(&test, 1, NINA_STARTUP_WAIT_AT);
    expect_tx(&test, "AT\r");
    feed(&test, "\r\n+STARTUP\r\nAT\r\r\nO");
    step(&test, 1, NINA_STARTUP_WAIT_AT);
    feed(&test, "K\r");
    step(&test, 1, NINA_STARTUP_SEND_UMRS);
    feed(&test, "\n");
    step(&test, 1, NINA_STARTUP_WAIT_UMRS);
    expect_tx(&test, "AT+UMRS?\r");
    feed(&test, "AT+UMRS?\r\r\n+UMRS: 115200, 1, 8");
    step(&test, 1, NINA_STARTUP_WAIT_UMRS);
    feed(&test, ", 1, 1 \r\n");
    step(&test, 1, NINA_STARTUP_WAIT_UMRS);
    feed(&test, "\r\nOK\r\nNEXT\r\n");
    step(&test, 1, NINA_STARTUP_READY);
    assert(test.startup.fault == NINA_STARTUP_FAULT_NONE);
    step(&test, 5000, NINA_STARTUP_READY);
    uint8_t out[8];
    assert(sc16_receive(&test.bridge, out, sizeof(out)) == 7);
    assert(memcmp(out, "\nNEXT\r\n", 7) == 0);
    expect_tx(&test, "");
}

static void stale_and_ordering(void)
{
    fixture test;
    init(&test, 0);
    send_at(&test);
    feed(&test, "\r\nOK\r\n+UMRS:115200,1,8,1,1\r\nOK\r\n");
    step(&test, 1, NINA_STARTUP_SEND_UMRS);
    step(&test, 1, NINA_STARTUP_FAILED);
    expect_failure(&test, NINA_STARTUP_FAULT_RESPONSE);

    const char *responses[] = {
        "\r\nOK\r\n",
        "+UMRS:115200,1,8,1,1\r\n+UMRS:115200,1,8,1,1\r\nOK\r\n",
        "+UMRS:115200,1,8,1,1\r\n+STARTUP\r\nOK\r\n",
        "+UMRS:115200,1,8,1,1\r\nERROR\r\n",
        "+UMRS:115200,1,8,1,1\r\n0\r\n",
        "\r\n\xff\r\n",
        "thislineexceedstheparserboundxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx\r\n",
    };
    for (size_t index = 0; index < sizeof(responses) / sizeof(responses[0]); ++index) {
        init(&test, 0);
        send_umrs(&test);
        feed(&test, responses[index]);
        for (unsigned slice = 0; slice < 3 && test.startup.state == NINA_STARTUP_WAIT_UMRS; ++slice) {
            nina_startup_step(&test.startup, &test.bridge, ++test.now_ms);
        }
        assert(test.startup.state == NINA_STARTUP_FAILED);
        expect_failure(&test, NINA_STARTUP_FAULT_RESPONSE);
    }
}

static void settings_and_overflow(void)
{
    const char *wrong[] = {
        "+UMRS:57600,1,8,1,1\r\n",
        "+UMRS:115200,2,8,1,1\r\n",
        "+UMRS:115200,1,7,1,1\r\n",
        "+UMRS:115200,1,8,2,1\r\n",
        "+UMRS:115200,1,8,1,2\r\n",
        "+UMRS:115200,1,8,1\r\n",
        "+UMRS:115200,1,8,1,1,0\r\n",
        "+UMRS:115200,1,8,1,1oops\r\n",
        "+UMRS:4295082496,1,8,1,1\r\n",
    };
    for (size_t index = 0; index < sizeof(wrong) / sizeof(wrong[0]); ++index) {
        fixture test;
        init(&test, 0);
        send_umrs(&test);
        feed(&test, wrong[index]);
        step(&test, 1, NINA_STARTUP_FAILED);
        expect_failure(&test, NINA_STARTUP_FAULT_UART_SETTINGS);
    }
}

static void deadlines_and_bridge_fault(void)
{
    fixture test;
    init(&test, 0);
    for (unsigned elapsed = 0; elapsed < NINA_STARTUP_PHASE_TIMEOUT_MS;
         elapsed += NINA_STARTUP_DRAIN_QUIET_MS - 1) {
        feed(&test, "\r\n+STARTUP\r\n");
        assert(nina_startup_step(&test.startup, &test.bridge, elapsed) == NINA_STARTUP_DRAIN);
    }
    step(&test, NINA_STARTUP_PHASE_TIMEOUT_MS, NINA_STARTUP_FAILED);
    expect_failure(&test, NINA_STARTUP_FAULT_TIMEOUT);

    init(&test, 0);
    send_at(&test);
    step(&test, NINA_STARTUP_PHASE_TIMEOUT_MS - 1, NINA_STARTUP_WAIT_AT);
    feed(&test, "\r\nOK\r\n");
    step(&test, 1, NINA_STARTUP_FAILED);
    expect_failure(&test, NINA_STARTUP_FAULT_TIMEOUT);

    init(&test, UINT32_MAX - 10);
    send_umrs(&test);
    feed(&test, "+UMRS:115200,1,8,1,1\r\n");
    step(&test, NINA_STARTUP_PHASE_TIMEOUT_MS - 1, NINA_STARTUP_WAIT_UMRS);
    step(&test, 1, NINA_STARTUP_FAILED);
    expect_failure(&test, NINA_STARTUP_FAULT_TIMEOUT);

    init(&test, 0);
    send_at(&test);
    feed(&test, "\r\nOK\r\n");
    test.bridge.state = SC16_FAULT;
    step(&test, 1, NINA_STARTUP_FAILED);
    expect_failure(&test, NINA_STARTUP_FAULT_BRIDGE);
    sc16_stop(&test.bridge);
    nina_startup_reset(&test.startup);
    step(&test, 1, NINA_STARTUP_OFF);
    assert(test.startup.fault == NINA_STARTUP_FAULT_NONE);
    assert(!nina_startup_begin(&test.startup, &test.bridge, test.now_ms));
    assert(test.bridge.rx.count == 0 && test.bridge.tx.count == 0);
}

static void tx_backpressure(void)
{
    fixture test;
    init(&test, 0);
    step(&test, NINA_STARTUP_DRAIN_QUIET_MS, NINA_STARTUP_SEND_AT);
    uint8_t queued[SC16_QUEUE_SIZE] = {0};
    assert(sc16_send(&test.bridge, queued, sizeof(queued)));
    step(&test, NINA_STARTUP_PHASE_TIMEOUT_MS - 1, NINA_STARTUP_SEND_AT);
    assert(test.bridge.tx.count == SC16_QUEUE_SIZE);
    step(&test, 1, NINA_STARTUP_FAILED);
    assert(test.bridge.tx.count == SC16_QUEUE_SIZE);
    sc16_stop(&test.bridge);
    expect_failure(&test, NINA_STARTUP_FAULT_TIMEOUT);
}

int main(void)
{
    split_and_drain();
    stale_and_ordering();
    settings_and_overflow();
    deadlines_and_bridge_fault();
    tx_backpressure();
    puts("NINA startup: 5 groups passed (23 scenarios)");
    return 0;
}
