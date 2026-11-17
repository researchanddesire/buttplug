#ifndef COMPASS_HOST_BRIDGE_H
#define COMPASS_HOST_BRIDGE_H
#include "host_control.h"

/* RP2040 implementation. Control messages and status contain no UV commands. */
void host_bridge_init(void);
host_outputs host_bridge_step(uint32_t now_ms, bool *fault, bool *contact);
void host_bridge_select(host_outputs output);
void host_bridge_publish(uint8_t flags, int16_t tip_centi_c);

#endif
