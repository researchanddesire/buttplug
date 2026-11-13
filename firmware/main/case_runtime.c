#include "case_runtime.h"
#include <string.h>

static ct_peer_t *peer(ct_runtime_t *r, uint16_t connection) {
    for(size_t i=0;i<CT_PEER_CAPACITY;++i)
        if(r->peers[i].active&&r->peers[i].connection==connection)return &r->peers[i];
    return NULL;
}
void ct_runtime_init(ct_runtime_t *r) { memset(r,0,sizeof(*r)); }
void ct_runtime_close(ct_runtime_t *r,uint16_t connection) {
    ct_peer_t *p=peer(r,connection);if(p)memset(p,0,sizeof(*p));
}
bool ct_runtime_open(ct_runtime_t *r,uint16_t connection) {
    ct_runtime_close(r,connection);
    for(size_t i=0;i<CT_PEER_CAPACITY;++i)if(!r->peers[i].active) {
        ct_peer_t *p=&r->peers[i];memset(p,0,sizeof(*p));
        p->active=true;p->connection=connection;p->epoch=++r->next_epoch;return true;
    }
    return false;
}
bool ct_runtime_read(const ct_runtime_t *r,uint16_t connection,uint8_t kind,uint8_t out[CT_WIRE_BYTES]) {
    if(!r->ready||kind<1||kind>6||kind==CT_COMMAND)return false;
    for(size_t i=0;i<CT_PEER_CAPACITY;++i) {
        const ct_peer_t *p=&r->peers[i];if(!p->active||p->connection!=connection)continue;
        if(kind==CT_RESULT) {
            if(!p->have_result)return false;
            memcpy(out,p->result.data,CT_WIRE_BYTES);
        }else memcpy(out,r->current[kind].data,CT_WIRE_BYTES);
        return true;
    }
    return false;
}
bool ct_runtime_enqueue(ct_runtime_t *r,uint16_t connection,const uint8_t data[CT_WIRE_BYTES],uint64_t rx) {
    ct_command_t command;
    if(!r->ready||!ct_parse_command(data,CT_WIRE_BYTES,&command))return false;
    ct_peer_t *p=peer(r,connection);
    if(!p||p->request_queued||p->reply_next<p->reply.count||r->command_count==CT_PEER_CAPACITY)return false;
    ct_pending_t *q=&r->commands[(r->command_next+r->command_count)%CT_PEER_CAPACITY];
    q->slot=(size_t)(p-r->peers);q->epoch=p->epoch;q->received_ms=rx;memcpy(q->data,data,CT_WIRE_BYTES);
    ++r->command_count;p->request_queued=true;return true;
}
void ct_runtime_update(ct_runtime_t *r,const thermal_history_t *h,const ct_charge_t *charge,uint64_t(*clock_ms)(void)) {
    ct_reply_t snapshot;ct_snapshot(h,charge,&snapshot);
    for(size_t i=0;i<snapshot.count;++i) {
        const ct_packet_t *f=&snapshot.frames[i];
        if(!r->ready||memcmp(r->current[f->kind].data,f->data,CT_WIRE_BYTES)) {
            r->current[f->kind]=*f;++r->revision[f->kind];
        }
    }
    r->ready=true;
    while(r->command_count) {
        ct_pending_t q=r->commands[r->command_next];
        r->command_next=(r->command_next+1)%CT_PEER_CAPACITY;--r->command_count;
        ct_peer_t *p=&r->peers[q.slot];
        if(!p->active||p->epoch!=q.epoch)continue;
        p->request_queued=false;
        if(!ct_execute(&p->session,h,charge,q.data,CT_WIRE_BYTES,q.received_ms,clock_ms(),&p->reply))continue;
        ct_reply_complete(&p->session,q.data,&p->reply,clock_ms());
        p->reply_next=0;++p->reply_serial;
        for(size_t i=0;i<p->reply.count;++i)if(p->reply.frames[i].kind==CT_RESULT) {
            p->result=p->reply.frames[i];p->have_result=true;
        }
    }
}
bool ct_runtime_peek(ct_runtime_t *r,uint16_t connection,uint8_t subscribed,uint64_t now,ct_transmission_t *t) {
    ct_peer_t *p=peer(r,connection);if(!p||!r->ready)return false;
    while(p->reply_next<p->reply.count) {
        ct_packet_t *f=&p->reply.frames[p->reply_next];
        if(!(subscribed&(1u<<f->kind))) { ++p->reply_next;continue; }
        *t=(ct_transmission_t){.packet=*f,.epoch=p->epoch,.token=p->reply_serial,
            .index=p->reply_next,.command_reply=true};return true;
    }
    if(now>=p->next_routine_ms) {
        p->routine_pending=0;
        for(unsigned kind=1;kind<=6;++kind)
            if((CT_ROUTINE_MASK&subscribed&(1u<<kind))&&r->revision[kind]!=p->sent_revision[kind])
                p->routine_pending|=(uint8_t)(1u<<kind);
        p->next_routine_ms=now+1000;
    }
    p->routine_pending&=subscribed;
    for(unsigned kind=1;kind<=6;++kind)if(p->routine_pending&(1u<<kind)) {
        *t=(ct_transmission_t){.packet=r->current[kind],.epoch=p->epoch,.token=r->revision[kind],.index=kind};return true;
    }
    return false;
}
void ct_runtime_sent(ct_runtime_t *r,uint16_t connection,const ct_transmission_t *t) {
    ct_peer_t *p=peer(r,connection);if(!p||p->epoch!=t->epoch)return;
    if(t->command_reply) {
        if(p->reply_serial==t->token&&p->reply_next==t->index&&p->reply_next<p->reply.count)++p->reply_next;
    }else if(t->index>=1&&t->index<=6&&(CT_ROUTINE_MASK&(1u<<t->index))) {
        p->sent_revision[t->index]=t->token;p->routine_pending&=(uint8_t)~(1u<<t->index);
    }
}
