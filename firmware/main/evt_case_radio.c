#ifdef BOARD_EVT1
#include "evt_case_radio.h"
#include "r0_app.h"
#include <string.h>
#include "host/ble_hs.h"
#include "host/ble_hs_mbuf.h"
#include "nimble/nimble_port.h"
#include "nimble/nimble_npl.h"

#define UUID(n) BLE_UUID128_INIT(0x86,0x7a,0x05,0x78,0xb2,0x6a,0xfd,0xbe,0x93,0x4a,0x24,0x64,n,0x10,0x3c,0xad)
const ble_uuid128_t evt_case_service_uuid=UUID(0);
static const ble_uuid128_t uuid[7]={UUID(0),UUID(1),UUID(2),UUID(3),UUID(4),UUID(5),UUID(6)};
static uint16_t handles[7];
static struct { bool used;uint16_t connection;uint8_t subscribed; } peers[CT_PEER_CAPACITY];
static struct ble_npl_event notify_event;
static bool ready;

static bool secure(uint16_t connection) {
    struct ble_gap_conn_desc desc;
    return ble_gap_conn_find(connection,&desc)==0 && desc.sec_state.encrypted &&
        desc.sec_state.authenticated && desc.sec_state.key_size>=16;
}
static int access(uint16_t connection,uint16_t attr,struct ble_gatt_access_ctxt *ctxt,void *arg) {
    (void)attr;uint8_t kind=(uint8_t)(uintptr_t)arg;
    if(!secure(connection))return BLE_ATT_ERR_INSUFFICIENT_AUTHEN;
    if(ctxt->offset)return BLE_ATT_ERR_INVALID_OFFSET;
    uint8_t data[CT_WIRE_BYTES];
    if(kind==CT_COMMAND&&ctxt->op==BLE_GATT_ACCESS_OP_WRITE_CHR) {
        uint64_t rx=r0_now_ms();uint16_t length=0;ct_command_t command;
        if(OS_MBUF_PKTLEN(ctxt->om)!=CT_WIRE_BYTES ||
            ble_hs_mbuf_to_flat(ctxt->om,data,sizeof(data),&length)!=0 || length!=CT_WIRE_BYTES)
            return BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN;
        if(!ct_parse_command(data,length,&command))return BLE_ATT_ERR_VALUE_NOT_ALLOWED;
        return r0_case_command(connection,data,rx)?0:BLE_ATT_ERR_INSUFFICIENT_RES;
    }
    if(kind!=CT_COMMAND&&ctxt->op==BLE_GATT_ACCESS_OP_READ_CHR) {
        if(!r0_case_read(connection,kind,data))return BLE_ATT_ERR_INSUFFICIENT_RES;
        return os_mbuf_append(ctxt->om,data,sizeof(data))==0?0:BLE_ATT_ERR_INSUFFICIENT_RES;
    }
    return BLE_ATT_ERR_UNLIKELY;
}
#define READ_FLAGS (BLE_GATT_CHR_F_READ|BLE_GATT_CHR_F_READ_ENC|BLE_GATT_CHR_F_READ_AUTHEN|BLE_GATT_CHR_F_NOTIFY)
#define READ_CHR(n) {.uuid=&uuid[n].u,.access_cb=access,.arg=(void*)(uintptr_t)n,.flags=READ_FLAGS,.val_handle=&handles[n]}
static const struct ble_gatt_svc_def services[]={
    {.type=BLE_GATT_SVC_TYPE_PRIMARY,.uuid=&evt_case_service_uuid.u,.characteristics=(struct ble_gatt_chr_def[]){
        READ_CHR(1),READ_CHR(2),READ_CHR(3),
        {.uuid=&uuid[4].u,.access_cb=access,.arg=(void*)(uintptr_t)4,
            .flags=BLE_GATT_CHR_F_WRITE|BLE_GATT_CHR_F_WRITE_ENC|BLE_GATT_CHR_F_WRITE_AUTHEN,.val_handle=&handles[4]},
        READ_CHR(5),READ_CHR(6),{0}}},{0}};
static void notify(struct ble_npl_event *event) {
    (void)event;unsigned budget=8;
    for(size_t i=0;i<CT_PEER_CAPACITY&&budget;++i) {
        if(!peers[i].used||!secure(peers[i].connection))continue;
        ct_transmission_t tx;
        while(budget&&r0_case_next(peers[i].connection,peers[i].subscribed,r0_now_ms(),&tx)) {
            struct os_mbuf *om=ble_hs_mbuf_from_flat(tx.packet.data,CT_WIRE_BYTES);
            if(!om)return;
            /* The pinned API consumes om on SUCCESS AND failure. Ack only
             * success; resource pressure leaves the same offer retryable. */
            int rc=ble_gatts_notify_custom(peers[i].connection,handles[tx.packet.kind],om);
            if(rc)return;
            r0_case_sent(peers[i].connection,&tx);--budget;
        }
    }
}
void evt_case_radio_publish(void) {
    if(ready)ble_npl_eventq_put(nimble_port_get_dflt_eventq(),&notify_event);
}
void evt_case_radio_reset(void) {
    for(size_t i=0;i<CT_PEER_CAPACITY;++i)if(peers[i].used)r0_case_disconnected(peers[i].connection);
    memset(peers,0,sizeof(peers));
}
void evt_case_radio_gap_event(const struct ble_gap_event *event) {
    if(event->type==BLE_GAP_EVENT_CONNECT&&event->connect.status==0) {
        for(size_t i=0;i<CT_PEER_CAPACITY;++i)if(!peers[i].used) {
            if(r0_case_connected(event->connect.conn_handle)) {
                peers[i].used=true;peers[i].connection=event->connect.conn_handle;peers[i].subscribed=0;
            }
            break;
        }
    }else if(event->type==BLE_GAP_EVENT_DISCONNECT) {
        uint16_t connection=event->disconnect.conn.conn_handle;r0_case_disconnected(connection);
        for(size_t i=0;i<CT_PEER_CAPACITY;++i)
            if(peers[i].used&&peers[i].connection==connection)memset(&peers[i],0,sizeof(peers[i]));
    }else if(event->type==BLE_GAP_EVENT_SUBSCRIBE) {
        for(size_t i=0;i<CT_PEER_CAPACITY;++i)if(peers[i].used&&peers[i].connection==event->subscribe.conn_handle)
            for(unsigned kind=1;kind<=6;++kind)if(kind!=CT_COMMAND&&handles[kind]==event->subscribe.attr_handle) {
                if(event->subscribe.cur_notify)peers[i].subscribed|=(uint8_t)(1u<<kind);
                else peers[i].subscribed&=(uint8_t)~(1u<<kind);
            }
        evt_case_radio_publish();
    }else if(event->type==BLE_GAP_EVENT_ENC_CHANGE)evt_case_radio_publish();
}
esp_err_t evt_case_radio_init(void) {
    ready=false;memset(peers,0,sizeof(peers));
    ble_npl_event_init(&notify_event,notify,NULL);
    int rc=ble_gatts_count_cfg(services);if(!rc)rc=ble_gatts_add_svcs(services);
    if(rc)return ESP_FAIL;
    ready=true;return ESP_OK;
}
#endif
