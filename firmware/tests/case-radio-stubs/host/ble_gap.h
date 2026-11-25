#pragma once
#include "ble_uuid.h"
enum { BLE_GAP_EVENT_CONNECT=0,BLE_GAP_EVENT_DISCONNECT=1,BLE_GAP_EVENT_ENC_CHANGE=10,BLE_GAP_EVENT_SUBSCRIBE=14 };
struct ble_gap_sec_state { unsigned encrypted,authenticated,bonded,key_size; };
struct ble_gap_conn_desc { struct ble_gap_sec_state sec_state;uint16_t conn_handle; };
struct ble_gap_event {
    int type;
    union {
        struct { int status;uint16_t conn_handle; } connect;
        struct { int reason;struct ble_gap_conn_desc conn; } disconnect;
        struct { int status;uint16_t conn_handle; } enc_change;
        struct { uint16_t conn_handle,attr_handle;uint8_t cur_notify; } subscribe;
    };
};
int ble_gap_conn_find(uint16_t connection,struct ble_gap_conn_desc *desc);
