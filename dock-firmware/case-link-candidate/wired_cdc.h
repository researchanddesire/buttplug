#ifndef WIRED_CDC_H
#define WIRED_CDC_H

#include "case_link.h"

#define WIRED_CDC_REQUEST_BYTES 49u
#define WIRED_CDC_RESPONSE_BYTES 65u
#define WIRED_CDC_BATCH_RECORDS 5u

typedef enum { WIRED_CDC_WAITING, WIRED_CDC_COMPLETE, WIRED_CDC_FAILED } wired_cdc_result;

typedef struct {
    case_link *link;
    uint32_t epoch;
    size_t line_length, record_count;
    bool discard_line;
    char line[WIRED_CDC_RESPONSE_BYTES - 1u];
    struct {
        cl_kind kind;
        uint8_t payload[CL_WIRE_BYTES];
    } records[WIRED_CDC_BATCH_RECORDS];
#ifdef COMPASS_WIRED_MAIN
    /* Historical records retain plug ticks and stay outside the live cache. */
    cl_frame observed_loss;
    bool replay_attempted;
    struct {
        bool available;
        size_t sample_count;
        cl_frame source, first_valid, samples[WIRED_CDC_BATCH_RECORDS - 2u];
    } replay;
#endif
} wired_cdc;

/* Called only after the local USB host has enumerated the expected device.
 * The caller keeps the attach epoch with queued USB callbacks and must
 * disconnect on USB loss, ownership change or a failed write. */
uint32_t wired_cdc_connect(wired_cdc *transport, case_link *link, uint64_t now_ms);
void wired_cdc_disconnect(wired_cdc *transport, uint64_t now_ms);
bool wired_cdc_request(wired_cdc *transport, uint8_t opcode, uint32_t argument,
                       uint64_t now_ms, char out[WIRED_CDC_REQUEST_BYTES]);
/* Requests have exactly WIRED_CDC_REQUEST_BYTES bytes including LF, no NUL.
 * A response line may span multiple reads. No live cache data is published
 * until a complete matching result terminates the batch. */
wired_cdc_result wired_cdc_receive(wired_cdc *transport, uint32_t epoch,
                                   const uint8_t *bytes, size_t length, uint64_t now_ms);
bool wired_cdc_poll(wired_cdc *transport, uint64_t now_ms);
#ifdef COMPASS_WIRED_MAIN
uint8_t wired_cdc_next_request(const wired_cdc *transport, uint32_t *argument);
#endif

#endif
