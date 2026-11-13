#include "evt_case_radio.h"
#include "r0_app.h"
#include "host/ble_hs.h"
#include "host/ble_hs_mbuf.h"
#include "nimble/nimble_npl.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const struct ble_gatt_svc_def *service;
static struct ble_gap_conn_desc connections[8];
static bool alive[8],allocation_fails;
static int registration_error,send_error;
static unsigned allocations,frees,sent;
static uint16_t sent_connection[128],sent_handle[128];
static uint8_t sent_values[128][20];
static struct ble_npl_event *queued;
static struct ble_npl_eventq queue;
static ct_runtime_t runtime;
static thermal_history_t history;
static uint64_t tick;

uint64_t r0_now_ms(void) { return tick++; }
bool r0_case_connected(uint16_t c) { return ct_runtime_open(&runtime,c); }
void r0_case_disconnected(uint16_t c) { ct_runtime_close(&runtime,c); }
bool r0_case_read(uint16_t c,uint8_t k,uint8_t out[20]) { return ct_runtime_read(&runtime,c,k,out); }
bool r0_case_command(uint16_t c,const uint8_t p[20],uint64_t rx) { return ct_runtime_enqueue(&runtime,c,p,rx); }
bool r0_case_next(uint16_t c,uint8_t mask,uint64_t now,ct_transmission_t *t) { return ct_runtime_peek(&runtime,c,mask,now,t); }
void r0_case_sent(uint16_t c,const ct_transmission_t *t) { ct_runtime_sent(&runtime,c,t); }
int ble_gap_conn_find(uint16_t c,struct ble_gap_conn_desc *out) {
    if(c>=8||!alive[c])return 1;*out=connections[c];return 0;
}
int ble_gatts_count_cfg(const struct ble_gatt_svc_def *s) {
    assert(s[0].type==BLE_GATT_SVC_TYPE_PRIMARY&&s[1].type==0);return registration_error;
}
int ble_gatts_add_svcs(const struct ble_gatt_svc_def *s) {
    service=s;unsigned count=0;
    for(const struct ble_gatt_chr_def *c=s[0].characteristics;c->uuid;++c) {
        const ble_uuid128_t *u=(const ble_uuid128_t*)c->uuid;unsigned k=u->value[12];assert(k>=1&&k<=6);
        *c->val_handle=(uint16_t)(0x100+k);++count;
        if(k==CT_COMMAND)assert(c->flags==(BLE_GATT_CHR_F_WRITE|BLE_GATT_CHR_F_WRITE_ENC|BLE_GATT_CHR_F_WRITE_AUTHEN));
        else assert(c->flags==(BLE_GATT_CHR_F_READ|BLE_GATT_CHR_F_READ_ENC|BLE_GATT_CHR_F_READ_AUTHEN|BLE_GATT_CHR_F_NOTIFY));
    }
    assert(count==6);return 0;
}
struct os_mbuf *ble_hs_mbuf_from_flat(const void *p,uint16_t n) {
    assert(n==20);if(allocation_fails)return NULL;
    struct os_mbuf *m=malloc(sizeof(*m));assert(m);m->len=n;memcpy(m->data,p,n);++allocations;return m;
}
int ble_gatts_notify_custom(uint16_t c,uint16_t h,struct os_mbuf *m) {
    assert(alive[c]&&connections[c].sec_state.encrypted&&connections[c].sec_state.authenticated&&connections[c].sec_state.key_size>=16);
    assert(m->len==20&&h>=0x101&&h<=0x106&&h!=0x104);
    if(!send_error) { assert(sent<128);sent_connection[sent]=c;sent_handle[sent]=h;memcpy(sent_values[sent++],m->data,20); }
    free(m);++frees;return send_error;
}
int ble_hs_mbuf_to_flat(const struct os_mbuf *m,void *p,uint16_t capacity,uint16_t *n) {
    if(m->len>capacity)return 1;*n=m->len;memcpy(p,m->data,*n);return 0;
}
int os_mbuf_append(struct os_mbuf *m,const void *p,uint16_t n) {
    if(m->len+n>sizeof(m->data))return 1;memcpy(m->data+m->len,p,n);m->len+=n;return 0;
}
void ble_npl_event_init(struct ble_npl_event *e,ble_npl_event_fn *fn,void *arg) { *e=(struct ble_npl_event){.fn=fn,.arg=arg};queued=NULL; }
void ble_npl_eventq_put(struct ble_npl_eventq *q,struct ble_npl_event *e) { assert(q==&queue);if(!e->queued) { e->queued=true;queued=e; } }
struct ble_npl_eventq *nimble_port_get_dflt_eventq(void) { return &queue; }
static void run(void) { if(queued) { struct ble_npl_event *e=queued;queued=NULL;e->queued=false;e->fn(e); } }
static void update(void) { ct_runtime_update(&runtime,&history,NULL,r0_now_ms); }
static void connect(uint16_t c) {
    alive[c]=true;connections[c].conn_handle=c;
    struct ble_gap_event e={.type=BLE_GAP_EVENT_CONNECT,.connect={.status=0,.conn_handle=c}};evt_case_radio_gap_event(&e);
}
static void authorize(uint16_t c) { connections[c].sec_state=(struct ble_gap_sec_state){.encrypted=1,.authenticated=1,.key_size=16}; }
static void subscribe(uint16_t c) {
    for(unsigned k=1;k<=6;++k)if(k!=CT_COMMAND) {
        struct ble_gap_event e={.type=BLE_GAP_EVENT_SUBSCRIBE,.subscribe={.conn_handle=c,.attr_handle=(uint16_t)(0x100+k),.cur_notify=1}};
        evt_case_radio_gap_event(&e);
    }
}
static int access_value(uint16_t connection,unsigned k,unsigned op,struct os_mbuf *m,unsigned offset) {
    const struct ble_gatt_chr_def *c=&service[0].characteristics[k-1];
    struct ble_gatt_access_ctxt ctxt={.op=(uint8_t)op,.offset=(uint16_t)offset,.om=m,.chr=c};
    return c->access_cb(connection,*c->val_handle,&ctxt,c->arg);
}
static void cmd(struct os_mbuf *m,unsigned id,unsigned nonce) {
    memset(m,0,sizeof(*m));m->len=20;m->data[0]=1;m->data[1]=2;m->data[2]=(uint8_t)id;m->data[4]=(uint8_t)nonce;
}
int main(void) {
    ct_runtime_init(&runtime);thermal_history_init(&history,42);thermal_history_source_snapshot(&history,true,0,0);tick=100;update();
    registration_error=1;assert(evt_case_radio_init()==ESP_FAIL);evt_case_radio_publish();assert(!queued);
    registration_error=0;assert(evt_case_radio_init()==ESP_OK);
    const uint8_t expected_uuid[16]={0x86,0x7a,0x05,0x78,0xb2,0x6a,0xfd,0xbe,0x93,0x4a,0x24,0x64,0,0x10,0x3c,0xad};
    assert(!memcmp(evt_case_service_uuid.value,expected_uuid,16));
    connect(1);subscribe(1);run();assert(!sent);
    struct os_mbuf m={0};assert(access_value(1,CT_THERMAL,BLE_GATT_ACCESS_OP_READ_CHR,&m,0)==BLE_ATT_ERR_INSUFFICIENT_AUTHEN);
    cmd(&m,0,10);assert(access_value(1,CT_COMMAND,BLE_GATT_ACCESS_OP_WRITE_CHR,&m,0)==BLE_ATT_ERR_INSUFFICIENT_AUTHEN&&runtime.command_count==0);
    connections[1].sec_state.encrypted=1;evt_case_radio_publish();run();assert(!sent);
    connections[1].sec_state.authenticated=1;connections[1].sec_state.key_size=7;evt_case_radio_publish();run();assert(!sent);
    authorize(1);m.len=0;assert(access_value(1,CT_THERMAL,BLE_GATT_ACCESS_OP_READ_CHR,&m,0)==0&&m.len==20);
    assert(access_value(1,CT_THERMAL,BLE_GATT_ACCESS_OP_READ_CHR,&m,1)==BLE_ATT_ERR_INVALID_OFFSET);
    cmd(&m,0,10);m.len=19;assert(access_value(1,CT_COMMAND,BLE_GATT_ACCESS_OP_WRITE_CHR,&m,0)==BLE_ATT_ERR_INVALID_ATTR_VALUE_LEN);
    m.len=20;m.data[0]=2;assert(access_value(1,CT_COMMAND,BLE_GATT_ACCESS_OP_WRITE_CHR,&m,0)==BLE_ATT_ERR_VALUE_NOT_ALLOWED);
    cmd(&m,0,10);assert(access_value(1,CT_COMMAND,BLE_GATT_ACCESS_OP_WRITE_CHR,&m,0)==0);
    assert(access_value(1,CT_COMMAND,BLE_GATT_ACCESS_OP_WRITE_CHR,&m,0)==BLE_ATT_ERR_INSUFFICIENT_RES);update();
    ct_transmission_t original,retry;assert(r0_case_next(1,1u<<CT_RESULT,tick,&original));
    allocation_fails=true;evt_case_radio_publish();run();assert(!sent&&r0_case_next(1,1u<<CT_RESULT,tick,&retry)&&retry.index==original.index);
    allocation_fails=false;send_error=1;evt_case_radio_publish();run();
    assert(allocations==frees&&!sent&&r0_case_next(1,1u<<CT_RESULT,tick,&retry)&&!memcmp(retry.packet.data,original.packet.data,20));
    send_error=0;evt_case_radio_publish();run();assert(sent&&sent_handle[0]==0x105&&sent_values[0][16]==10&&allocations==frees);

    connect(2);authorize(2);subscribe(2);run();
    cmd(&m,1,10);assert(access_value(1,CT_COMMAND,BLE_GATT_ACCESS_OP_WRITE_CHR,&m,0)==0);
    cmd(&m,0,20);assert(access_value(2,CT_COMMAND,BLE_GATT_ACCESS_OP_WRITE_CHR,&m,0)==0);update();
    m.len=0;assert(access_value(1,CT_RESULT,BLE_GATT_ACCESS_OP_READ_CHR,&m,0)==0&&m.data[16]==10);
    m.len=0;assert(access_value(2,CT_RESULT,BLE_GATT_ACCESS_OP_READ_CHR,&m,0)==0&&m.data[16]==20);
    assert(r0_case_next(1,1u<<CT_RESULT,tick,&original));
    struct ble_gap_event e={.type=BLE_GAP_EVENT_DISCONNECT,.disconnect={.conn={.conn_handle=1}}};evt_case_radio_gap_event(&e);alive[1]=false;
    connect(1);authorize(1);subscribe(1);cmd(&m,0,30);
    assert(access_value(1,CT_COMMAND,BLE_GATT_ACCESS_OP_WRITE_CHR,&m,0)==0);update();r0_case_sent(1,&original);
    assert(r0_case_next(1,1u<<CT_RESULT,tick,&retry)&&retry.epoch!=original.epoch&&retry.packet.data[16]==30);
    evt_case_radio_reset();unsigned previous=sent;evt_case_radio_publish();run();assert(sent==previous&&allocations==frees);
    m.len=0;assert(access_value(1,CT_RESULT,BLE_GATT_ACCESS_OP_READ_CHR,&m,0)==BLE_ATT_ERR_INSUFFICIENT_RES);
    puts("Case GATT boundary: authenticated16-byte-key access/notifications, fixed values, malformed writes, task queueing, resource retry/mbuf ownership, peers/epochs and reset pass.");
    return 0;
}
