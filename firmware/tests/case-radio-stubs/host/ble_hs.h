#pragma once
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include "ble_gap.h"
struct os_mbuf { uint16_t len;uint8_t data[64]; };
#define OS_MBUF_PKTLEN(m) ((m)->len)
enum { BLE_GATT_ACCESS_OP_READ_CHR=0,BLE_GATT_ACCESS_OP_WRITE_CHR=1,BLE_GATT_SVC_TYPE_PRIMARY=1 };
enum { BLE_GATT_CHR_F_READ=1,BLE_GATT_CHR_F_READ_ENC=2,BLE_GATT_CHR_F_READ_AUTHEN=4,
       BLE_GATT_CHR_F_NOTIFY=8,BLE_GATT_CHR_F_WRITE=16,BLE_GATT_CHR_F_WRITE_ENC=32,BLE_GATT_CHR_F_WRITE_AUTHEN=64 };
enum { BLE_ATT_ERR_INSUFFICIENT_AUTHEN=5,BLE_ATT_ERR_INVALID_OFFSET=7,
       BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN=13,BLE_ATT_ERR_UNLIKELY=14,
       BLE_ATT_ERR_INSUFFICIENT_RES=17,BLE_ATT_ERR_VALUE_NOT_ALLOWED=19 };
struct ble_gatt_chr_def;
struct ble_gatt_access_ctxt { uint8_t op;uint16_t offset;struct os_mbuf *om;const struct ble_gatt_chr_def *chr; };
typedef int ble_gatt_access_fn(uint16_t,uint16_t,struct ble_gatt_access_ctxt*,void*);
struct ble_gatt_chr_def { const ble_uuid_t *uuid;ble_gatt_access_fn *access_cb;void *arg;uint16_t flags;uint16_t *val_handle; };
struct ble_gatt_svc_def { uint8_t type;const ble_uuid_t *uuid;const struct ble_gatt_chr_def *characteristics; };
int ble_gatts_count_cfg(const struct ble_gatt_svc_def *services);
int ble_gatts_add_svcs(const struct ble_gatt_svc_def *services);
int ble_gatts_notify_custom(uint16_t connection,uint16_t handle,struct os_mbuf *om);
int ble_hs_mbuf_to_flat(const struct os_mbuf *om,void *out,uint16_t capacity,uint16_t *length);
int os_mbuf_append(struct os_mbuf *om,const void *data,uint16_t length);
