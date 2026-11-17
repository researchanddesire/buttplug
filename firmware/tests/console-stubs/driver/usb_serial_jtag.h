#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <stddef.h>
#include "esp_err.h"
typedef struct {size_t rx_buffer_size,tx_buffer_size;} usb_serial_jtag_driver_config_t;
esp_err_t usb_serial_jtag_driver_install(usb_serial_jtag_driver_config_t *config);
int usb_serial_jtag_read_bytes(void *buffer,uint32_t length,int timeout);
bool usb_serial_jtag_is_connected(void);
