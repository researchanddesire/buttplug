#ifndef NINA_GATT_H
#define NINA_GATT_H

#include "case_link.h"
#include "sc16_bridge.h"

typedef enum {
    NINA_GATT_OFF,
    NINA_GATT_SERVICE,
    NINA_GATT_CHARACTERISTICS,
    NINA_GATT_DESCRIPTOR,
    NINA_GATT_SUBSCRIBE,
    NINA_GATT_READY,
    NINA_GATT_WRITE,
    NINA_GATT_READ,
    NINA_GATT_FAILED,
} nina_gatt_state;

typedef struct {
    case_link *link;
    uint32_t epoch, deadline;
    uint16_t connection, first, last, descriptor;
    uint16_t value[CL_FIRST_VALID + 1];
    uint16_t declaration[CL_FIRST_VALID + 1];
    cl_kind subscribing;
    nina_gatt_state state;
    cl_kind reading;
    bool sent, have_read;
    uint8_t read_bytes[CL_WIRE_BYTES];
    unsigned length;
    char line[80], command[80];
} nina_gatt;

/* After connection to the commissioned identity and verification of its
 * authenticated, encrypted link. The caller owns ACL, identity and security.
 * Use a clean command channel, with no prior command pending and echo off.
 * Reset before a new ACL and whenever the link loses authentication. */
bool nina_gatt_begin(nina_gatt *gatt, case_link *link, uint16_t connection, uint64_t now);
void nina_gatt_stop(nina_gatt *gatt, uint64_t now);
nina_gatt_state nina_gatt_step(nina_gatt *gatt, sc16_bridge *bridge, uint64_t now);

/* Call only when ready. Serial enqueue and ATT acknowledgement are distinct
 * from the plug's corresponding result notification. */
bool nina_gatt_write(nina_gatt *gatt, sc16_bridge *bridge, uint8_t opcode,
                     uint32_t arg0, uint32_t arg1, uint64_t now);
/* Read one telemetry value. The result characteristic stays command-driven. */
bool nina_gatt_read(nina_gatt *gatt, cl_kind kind, uint64_t now);

#endif
