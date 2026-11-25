#include "case_telemetry.h"
#include <limits.h>
#include <string.h>

static uint16_t get16(const uint8_t *p) { return (uint16_t)(p[0] | ((uint16_t)p[1]<<8)); }
static uint32_t get32(const uint8_t *p) { return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24; }
static void put16(uint8_t *p, uint16_t v) { p[0]=(uint8_t)v; p[1]=(uint8_t)(v>>8); }
static void put32(uint8_t *p, uint32_t v) { for (unsigned i=0;i<4;++i) p[i]=(uint8_t)(v>>(i*8)); }
static void blank(ct_packet_t *p, ct_kind kind) { memset(p,0,sizeof(*p));p->kind=(uint8_t)kind;p->data[0]=1; }
bool ct_parse_command(const uint8_t *p, size_t length, ct_command_t *out) {
    if (!p || !out || length!=CT_WIRE_BYTES || p[0]!=1) return false;
    *out=(ct_command_t){.opcode=p[1],.request_id=get16(p+2),.session_id=get32(p+4),
        .case_ms=get32(p+8),.argument0=get32(p+12),.argument1=get32(p+16)};
    return true;
}
static bool follows_loss(const thermal_history_t *h, const thermal_sample_t *s) {
    if (s->source_at_start || s->source_at_end || s->source_changed) return false;
    for (size_t i=0;i<h->event_count;++i) {
        const thermal_removal_t *e=&h->events[(h->event_next+THERMAL_EVENT_CAPACITY-1-i)%THERMAL_EVENT_CAPACITY];
        if (s->dock_session==e->dock_session && s->loss_sequence_at_start==e->sequence && s->started_ms>=e->observed_ms) return true;
    }
    return false;
}
void ct_encode_sample(const thermal_history_t *h, const thermal_sample_t *s, ct_packet_t *out) {
    blank(out,CT_THERMAL);put32(out->data+4,h->boot_id);
    put16(out->data+16,0x8000);put16(out->data+18,0xffff);
    if (!s || h->clock_fault || s->started_ms>s->sampled_ms || s->sampled_ms-s->started_ms>=0x80000000ULL) return;
    uint8_t f=1u;
    bool valid=s->valid && s->started_ms<=s->sampled_ms && s->tip_millic>=-40000 && s->tip_millic<=125000;
    if (valid) { f|=2u;put16(out->data+16,(uint16_t)(int16_t)(s->tip_millic/10)); }
    else f|=32u;
    if (s->source_at_start) f|=4u;
    if (s->source_at_end) f|=8u;
    if (s->source_changed || s->source_at_start!=s->source_at_end) f|=16u;
    if (follows_loss(h,s)) f|=64u;
    if (s->ratio_valid && s->raw_ratio_q16!=0xffff) { f|=128u;put16(out->data+18,s->raw_ratio_q16); }
    out->data[1]=f;put16(out->data+2,(uint16_t)s->sequence);
    put32(out->data+8,(uint32_t)s->started_ms);put32(out->data+12,(uint32_t)s->sampled_ms);
    /* The current driver leaves ratio_valid false; temperature validity never
     * silently makes this optional independent field available. */
}
void ct_encode_charge(uint32_t boot_id, const ct_charge_t *c, ct_packet_t *out) {
    blank(out,CT_CHARGE);put32(out->data+5,boot_id);
    uint16_t v=c && c->acquired ? (uint16_t)(c->validity&0x1fffu) : CT_MEASUREMENT_GAP;
    if (c && c->acquired) {
        put16(out->data+3,c->sequence);put32(out->data+9,(uint32_t)c->completed_ms);
        out->data[19]=(uint8_t)(c->raw_status&0x7fu);
        if (c->current_0p1_ma==0xffff) v&=(uint16_t)~CT_ISET_VALID;
        if (c->ts_mv==0xffff) v&=(uint16_t)~CT_TS_VALID;
        if (c->vbat_mv==0xffff) v&=(uint16_t)~CT_VBAT_VALID;
    }
    put16(out->data+1,v);
    put16(out->data+13,c && (v&CT_ISET_VALID) ? c->current_0p1_ma : 0xffff);
    put16(out->data+15,c && (v&CT_TS_VALID) ? c->ts_mv : 0xffff);
    put16(out->data+17,c && (v&CT_VBAT_VALID) ? c->vbat_mv : 0xffff);
}
void ct_encode_source(const thermal_history_t *h, const thermal_removal_t *e, bool first_valid, ct_packet_t *out) {
    blank(out,first_valid?CT_FIRST_VALID:CT_SOURCE);put32(out->data+4,h->boot_id);
    if (!e || h->clock_fault) return;
    uint8_t f=0;
    if (first_valid) {
        if (e->after_loss_valid) f|=1u;
        if (e->reconnected_before_sample) f|=2u;
        if (h->event_overflow) f|=4u;
    } else {
        f=1u;
        if (e->reconnected_before_attempt) f|=2u;
        if (e->after_loss_attempted) f|=12u;
        if (e->after_loss_attempted && e->first_attempt_after_loss.valid) f|=16u;
        if (h->event_overflow) f|=32u;
        if (e->reconnected_before_sample) f|=64u;
    }
    out->data[1]=f;put16(out->data+2,(uint16_t)e->sequence);put32(out->data+8,(uint32_t)e->observed_ms);
    const thermal_sample_t *s=first_valid ? (e->after_loss_valid?&e->first_after_loss:NULL) :
        (e->after_loss_attempted?&e->first_attempt_after_loss:NULL);
    if (s) { put32(out->data+12,(uint32_t)s->started_ms);put32(out->data+16,(uint32_t)s->sampled_ms); }
}
void ct_encode_result(uint32_t boot_id, const ct_command_t *c, ct_result result, uint64_t rx, uint64_t done, ct_packet_t *out) {
    blank(out,CT_RESULT);out->data[1]=(uint8_t)result;put16(out->data+2,c->request_id);
    put32(out->data+4,boot_id);put32(out->data+8,(uint32_t)rx);put32(out->data+12,(uint32_t)done);put32(out->data+16,c->session_id);
}
static void add(ct_reply_t *r, const ct_packet_t *p) {
    for (size_t i=0;i<r->count;++i)
        if (r->frames[i].kind==p->kind && !memcmp(r->frames[i].data,p->data,CT_WIRE_BYTES)) return;
    if (r->count<CT_REPLY_CAPACITY) r->frames[r->count++]=*p;
}
static const thermal_sample_t *latest_sample(const thermal_history_t *h) {
    return h->sample_count ? &h->samples[(h->sample_next+THERMAL_SAMPLE_CAPACITY-1)%THERMAL_SAMPLE_CAPACITY] : NULL;
}
void ct_snapshot(const thermal_history_t *h, const ct_charge_t *c, ct_reply_t *r) {
    memset(r,0,sizeof(*r));ct_packet_t p;
    ct_encode_sample(h,latest_sample(h),&p);add(r,&p);
    ct_encode_charge(h->boot_id,h->clock_fault?NULL:c,&p);add(r,&p);
    const thermal_removal_t *e=thermal_history_latest(h);
    ct_encode_source(h,e,false,&p);add(r,&p);ct_encode_source(h,e,true,&p);add(r,&p);
}
void ct_session_init(ct_session_t *s) { memset(s,0,sizeof(*s)); }
static void replay(const thermal_history_t *h, const thermal_removal_t *e, ct_reply_t *r) {
    ct_packet_t p;
    if (e->docked_valid) { ct_encode_sample(h,&e->last_docked,&p);add(r,&p); }
    if (e->after_loss_attempted) { ct_encode_sample(h,&e->first_attempt_after_loss,&p);add(r,&p); }
    if (e->after_loss_valid) { ct_encode_sample(h,&e->first_after_loss,&p);add(r,&p); }
    ct_encode_source(h,e,false,&p);add(r,&p);ct_encode_source(h,e,true,&p);add(r,&p);
}
bool ct_execute(ct_session_t *s, const thermal_history_t *h, const ct_charge_t *charge,
                const uint8_t *data, size_t length, uint64_t rx, uint64_t now, ct_reply_t *r) {
    ct_command_t c;if (!ct_parse_command(data,length,&c) || !s || !h || !r) return false;
    memset(r,0,sizeof(*r));
    if (h->clock_fault || now<rx) {
        ct_encode_result(h->boot_id,&c,CT_BUSY_OR_STALE,rx,now,&r->frames[r->count++]);return true;
    }
    if (!s->session_known || s->session_id!=c.session_id) {
        ct_session_init(s);s->session_known=true;s->session_id=c.session_id;
    }
    for (size_t i=0;i<CT_IDEMPOTENCY_CAPACITY;++i) {
        if (s->cache[i].used && s->cache[i].request_id==c.request_id) {
            if (!memcmp(data,s->cache[i].command,CT_WIRE_BYTES)) { *r=s->cache[i].reply;r->from_cache=true;return true; }
            ct_encode_result(h->boot_id,&c,CT_INVALID_ARGUMENT,rx,now,&r->frames[r->count++]);return true;
        }
    }
    ct_result result=CT_OK;
    bool old=s->highwater_known && c.request_id<=s->highwater;
    if (old) result=CT_HISTORY_UNAVAILABLE;
    else if (now-rx>CT_COMMAND_MAX_AGE_MS) result=CT_BUSY_OR_STALE;
    else if (c.opcode<1 || c.opcode>4) result=CT_UNSUPPORTED;
    else if (c.argument1 || (c.opcode!=4 && c.argument0) || c.argument0>UINT16_MAX) result=CT_INVALID_ARGUMENT;
    else if (c.opcode==1) ct_snapshot(h,charge,r);
    else if (c.opcode==3 || c.opcode==4) {
        const thermal_removal_t *e=c.opcode==3 ? thermal_history_latest(h) : NULL;
        if (c.opcode==4)
            for (size_t i=0;i<h->event_count;++i) {
                const thermal_removal_t *candidate=&h->events[(h->event_next+THERMAL_EVENT_CAPACITY-1-i)%THERMAL_EVENT_CAPACITY];
                if ((uint16_t)candidate->sequence==(uint16_t)c.argument0) { e=candidate;break; }
            }
        if (e) replay(h,e,r);else result=CT_HISTORY_UNAVAILABLE;
    }
    ct_packet_t p;ct_encode_result(h->boot_id,&c,result,rx,now,&p);add(r,&p);
    if (!old) {
        s->highwater_known=true;s->highwater=c.request_id;
        ct_cached_reply_t *cache=&s->cache[s->next];cache->used=true;cache->request_id=c.request_id;
        memcpy(cache->command,data,CT_WIRE_BYTES);cache->reply=*r;s->next=(s->next+1)%CT_IDEMPOTENCY_CAPACITY;
    }
    return true;
}
void ct_reply_complete(ct_session_t *s, const uint8_t data[CT_WIRE_BYTES], ct_reply_t *r, uint64_t now) {
    if (r->from_cache) return;
    ct_cached_reply_t *cache=NULL;
    for (size_t i=0;i<CT_IDEMPOTENCY_CAPACITY;++i)
        if (s->cache[i].used && !memcmp(s->cache[i].command,data,CT_WIRE_BYTES) &&
            s->cache[i].reply.count==r->count &&
            !memcmp(s->cache[i].reply.frames,r->frames,r->count*sizeof(ct_packet_t))) cache=&s->cache[i];
    for (size_t i=0;i<r->count;++i)
        if (r->frames[i].kind==CT_RESULT) put32(r->frames[i].data+12,(uint32_t)now);
    if (cache) cache->reply=*r;
}
