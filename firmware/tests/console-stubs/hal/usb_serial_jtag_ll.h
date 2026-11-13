#pragma once
#include <stdbool.h>
#include <stdint.h>
#define USB_SERIAL_JTAG_INTR_SERIAL_OUT_RECV_PKT (1U<<2)
void usb_serial_jtag_ll_phy_enable_pad(bool enabled);
void usb_serial_jtag_ll_disable_intr_mask(uint32_t mask);
void usb_serial_jtag_ll_ena_intr_mask(uint32_t mask);
int usb_serial_jtag_ll_read_rxfifo(uint8_t *buffer,uint32_t length);
void usb_serial_jtag_ll_clr_intsts_mask(uint32_t mask);
