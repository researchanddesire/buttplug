#include "case_link.h"
#include <limits.h>
#include <string.h>
static void need_resync(case_link *s);
static void next_timing_epoch(case_link *s){++s->timing_epoch;if(!s->timing_epoch)++s->timing_epoch;}

static uint16_t r16(const uint8_t *p) { return (uint16_t)((uint16_t)p[0] | (uint16_t)((uint16_t)p[1]<<8)); }
static uint32_t r32(const uint8_t *p) { return (uint32_t)r16(p) | ((uint32_t)r16(p+2)<<16); }
static void w16(uint8_t *p,uint16_t x) { p[0]=(uint8_t)x;p[1]=(uint8_t)(x>>8); }
static void w32(uint8_t *p,uint32_t x) { w16(p,(uint16_t)x);w16(p+2,(uint16_t)(x>>16)); }
static bool duration(uint32_t from,uint32_t to,uint32_t *delta) { *delta=to-from;return *delta<UINT32_C(0x80000000); }
static bool unwrap(int64_t reference,uint32_t raw,int64_t *out) {
    uint32_t d=raw-(uint32_t)reference;
    if(d==UINT32_C(0x80000000))return false;
    *out=reference+(d<UINT32_C(0x80000000)?(int64_t)d:-(int64_t)(UINT64_C(0x100000000)-d));return true;
}
bool cl_tick32_update(cl_tick32_clock *c,uint32_t tick,uint64_t *out) {
    if(!c||!out||c->fault)return false;
    if(!c->initialized) {c->initialized=true;c->extended=tick;}
    else {uint32_t d=tick-c->prior;if(d>=UINT32_C(0x80000000)){c->fault=true;return false;}c->extended+=d;}
    c->prior=tick;*out=c->extended;return true;
}
cl_receive case_link_decode(cl_kind kind,const uint8_t *p,size_t n,cl_frame *f) {
    if(!p||!f||n!=20||p[0]!=1||kind<CL_THERMAL||kind>CL_FIRST_VALID)return CL_REJECTED;
    memset(f,0,sizeof(*f));f->kind=kind;f->sequence=r16(p+2);f->boot_id=r32(p+4);
    if(kind==CL_THERMAL) {
        uint8_t flags=p[1];uint16_t u=r16(p+16);
        f->data.thermal.flags=flags;f->data.thermal.started=r32(p+8);f->data.thermal.completed=r32(p+12);
        f->data.thermal.centi_c=u<=INT16_MAX?(int16_t)u:(int16_t)(-(int32_t)(UINT32_C(65536)-u));
        f->data.thermal.ratio_q16=r16(p+18);
        if((flags&2)&&(!(flags&1)||u==UINT16_C(0x8000))) {f->field_faults|=2;f->data.thermal.flags&=(uint8_t)~2u;}
        if((flags&128)&&(!(flags&1)||r16(p+18)==UINT16_MAX)) {f->field_faults|=128;f->data.thermal.flags&=(uint8_t)~128u;}
    } else if(kind==CL_CHARGE) {
        uint16_t v=r16(p+1);if(v&UINT16_C(0xe000)||p[19]&128)return CL_REJECTED;
        f->sequence=r16(p+3);f->boot_id=r32(p+5);f->data.charge.validity=v;
        f->data.charge.completed=r32(p+9);f->data.charge.current_0p1_ma=r16(p+13);
        f->data.charge.ts_mv=r16(p+15);f->data.charge.vbat_mv=r16(p+17);f->data.charge.status=p[19];
        uint16_t values[3]={r16(p+13),r16(p+15),r16(p+17)};
        for(unsigned i=0;i<3;i++)if(((v&(1u<<i))!=0)==(values[i]==UINT16_MAX)) {
            f->field_faults|=(uint16_t)(1u<<i);f->data.charge.validity&=(uint16_t)~(1u<<i);
        }
        if((v&0x101u)==0x101u){f->field_faults|=1;f->data.charge.validity&=(uint16_t)~1u;}
        if((v&0x202u)==0x202u){f->field_faults|=2;f->data.charge.validity&=(uint16_t)~2u;}
    } else if(kind==CL_SOURCE||kind==CL_FIRST_VALID) {
        if(p[1]&(kind==CL_SOURCE?128u:248u))return CL_REJECTED;
        f->data.event.flags=p[1];f->data.event.loss=r32(p+8);f->data.event.started=r32(p+12);f->data.event.completed=r32(p+16);
        if(kind==CL_SOURCE&&((p[1]&8)&&!(p[1]&4)))return CL_REJECTED;
        if(kind==CL_SOURCE&&((p[1]&16)&&!(p[1]&8)))return CL_REJECTED;
    } else if(kind==CL_COMMAND) {
        if(p[1]<1||p[1]>4)return CL_REJECTED;
        f->boot_id=0;f->data.command.opcode=p[1];f->data.command.session_id=r32(p+4);
        f->data.command.case_tick=r32(p+8);f->data.command.argument0=r32(p+12);f->data.command.argument1=r32(p+16);
    } else {
        if(p[1]>5)return CL_REJECTED;
        f->data.result.result=p[1];f->data.result.received=r32(p+8);f->data.result.completed=r32(p+12);f->data.result.session_id_echo=r32(p+16);
    }
    return f->field_faults?CL_PARTIAL:CL_ACCEPTED;
}
static void clear_data(case_link *s) {
    next_timing_epoch(s);
    memset(s->thermal,0,sizeof(s->thermal));memset(s->charge,0,sizeof(s->charge));memset(s->events,0,sizeof(s->events));
    memset(&s->thermal_order,0,sizeof(s->thermal_order));memset(&s->charge_order,0,sizeof(s->charge_order));
    memset(&s->source_order,0,sizeof(s->source_order));memset(&s->valid_order,0,sizeof(s->valid_order));
    s->thermal_next=s->charge_next=s->event_next=0;s->anchor.valid=false;s->pending.active=false;s->pending.retryable=false;
    s->tick_known=false;s->snapshot_seen=false;s->resync_needed=true;s->history_continuous=true;s->have_result=false;
}
static bool clock_ok(case_link *s,uint64_t now) {
    if(s->clock_fault)return false;
    if(now<s->last_case_ms||now>(uint64_t)INT64_MAX/4) {s->clock_fault=true;clear_data(s);return false;}
    s->last_case_ms=now;return true;
}
static bool valid_policy(const cl_policy *p) {
    if(!p||!p->thermal_fresh_ms||!p->ratio_fresh_ms||!p->max_attempt_ms||!p->max_gap_ms||!p->max_anchor_age_ms||!p->max_round_trip_ms||!p->combined_timer_resolution_ms||!p->combined_clock_drift_ppm||!p->max_sequence_advance||p->max_sequence_advance>=32768||p->combined_clock_drift_ppm>1000000)return false;
    if(p->max_attempt_ms>=UINT32_C(0x80000000)||p->max_gap_ms>=UINT32_C(0x80000000)||p->max_anchor_age_ms>=UINT32_C(0x80000000)||p->max_round_trip_ms>=UINT32_C(0x80000000))return false;
    for(unsigned i=0;i<CL_CHARGE_FIELDS;i++)if(!p->charge_fresh_ms[i])return false;
    return true;
}
bool case_link_init(case_link *s,uint32_t nonce,const cl_policy *p,uint64_t now) {
    if(!s||!valid_policy(p)||now>(uint64_t)INT64_MAX/4)return false;
    memset(s,0,sizeof(*s));s->policy=*p;s->case_session_id=nonce;s->last_case_ms=now;s->resync_needed=true;return true;
}
bool case_link_new_session(case_link *s,uint32_t nonce,uint64_t now) {
    if(!clock_ok(s,now)||nonce==s->case_session_id)return false;
    clear_data(s);s->case_session_id=nonce;s->next_request_id=0;return true;
}
uint32_t case_link_connect(case_link *s,uint64_t now) {
    if(!clock_ok(s,now))return 0;
    clear_data(s);s->connected=true;s->boot_known=false;s->retired_count=s->retired_next=0;
    ++s->link_epoch;if(!s->link_epoch)++s->link_epoch;return s->link_epoch;
}
void case_link_disconnect(case_link *s,uint64_t now) { (void)clock_ok(s,now);clear_data(s);s->connected=false; }
bool case_link_poll(case_link *s,uint64_t now) {
    if(!clock_ok(s,now))return false;
    if(s->pending.active&&now-s->pending.sent_ms>s->policy.max_round_trip_ms){s->pending.active=false;s->pending.retryable=s->pending.opcode!=2;}
    if(s->anchor.valid&&now-s->anchor.case_ms>s->policy.max_anchor_age_ms)need_resync(s);
    return true;
}
static bool adopt_boot(case_link *s,uint32_t boot) {
    if(s->boot_known&&s->boot_id==boot)return true;
    for(unsigned i=0;i<s->retired_count;i++)if(s->retired_boots[i]==boot)return false;
    if(s->boot_known) {
        s->retired_boots[s->retired_next]=s->boot_id;s->retired_next=(uint8_t)((s->retired_next+1)%4);
        if(s->retired_count<4)++s->retired_count;
        clear_data(s);
    }
    s->boot_known=true;s->boot_id=boot;return true;
}
static void need_resync(case_link *s) {
    next_timing_epoch(s);s->tick_known=false;s->anchor.valid=false;s->snapshot_seen=false;
    s->resync_needed=true;s->history_continuous=false;s->pending.active=false;s->pending.retryable=false;
    memset(&s->thermal_order,0,sizeof(s->thermal_order));memset(&s->charge_order,0,sizeof(s->charge_order));
    memset(&s->source_order,0,sizeof(s->source_order));memset(&s->valid_order,0,sizeof(s->valid_order));
}
static bool extend(case_link *s,uint32_t raw,int64_t *out) {
    if(!s->tick_known){*out=raw;return true;}
    if(!unwrap(s->tick_reference,raw,out)){need_resync(s);return false;}
    return true;
}
static void commit_tick(case_link *s,int64_t tick){if(!s->tick_known||tick>s->tick_reference)s->tick_reference=tick;s->tick_known=true;}
/* -1 older, 0 same, 1 newest. Excessive gaps force resnapshot/anchor. */
static int order(case_link *s,cl_order *o,uint16_t sequence,uint64_t now) {
    if(!o->known){o->known=true;o->newest=sequence;o->received=now;return 1;}
    uint16_t delta=(uint16_t)(sequence-o->newest);
    if(delta==32768){need_resync(s);return -2;}
    if(now-o->received>s->policy.max_gap_ms){need_resync(s);return -2;}
    if(!delta)return 0;
    if(delta<32768){
        if(delta>1){s->missing_sequences+=(uint32_t)delta-1;s->history_continuous=false;}
        if(delta>s->policy.max_sequence_advance){need_resync(s);return -2;}
        o->newest=sequence;o->received=now;return 1;
    }
    return -1;
}
static uint32_t completed(const cl_frame *f) {
    if(f->kind==CL_THERMAL)return f->data.thermal.flags&1?f->data.thermal.completed:f->data.thermal.started;
    if(f->kind==CL_CHARGE)return f->data.charge.completed;
    return (f->kind==CL_FIRST_VALID?(f->data.event.flags&1):(f->data.event.flags&8))?f->data.event.completed:f->data.event.loss;
}
static bool record_time(case_link *s,const cl_frame *f,int64_t *tick) {
    uint32_t span;
    if(f->kind==CL_THERMAL&&(f->data.thermal.flags&1)&&(!duration(f->data.thermal.started,f->data.thermal.completed,&span)||span>s->policy.max_attempt_ms))return false;
    if((f->kind==CL_SOURCE&&(f->data.event.flags&8))||(f->kind==CL_FIRST_VALID&&(f->data.event.flags&1))) {
        if(!duration(f->data.event.loss,f->data.event.started,&span)||!duration(f->data.event.started,f->data.event.completed,&span)||span>s->policy.max_attempt_ms)return false;
    }
    return extend(s,completed(f),tick);
}
static bool same_frame(const cl_frame *a,const cl_frame *b) {
    if(a->kind!=b->kind||a->sequence!=b->sequence||a->boot_id!=b->boot_id||a->field_faults!=b->field_faults)return false;
    if(a->kind==CL_THERMAL)return a->data.thermal.flags==b->data.thermal.flags&&a->data.thermal.started==b->data.thermal.started&&a->data.thermal.completed==b->data.thermal.completed&&a->data.thermal.centi_c==b->data.thermal.centi_c&&a->data.thermal.ratio_q16==b->data.thermal.ratio_q16;
    if(a->kind==CL_CHARGE)return a->data.charge.validity==b->data.charge.validity&&a->data.charge.completed==b->data.charge.completed&&a->data.charge.current_0p1_ma==b->data.charge.current_0p1_ma&&a->data.charge.ts_mv==b->data.charge.ts_mv&&a->data.charge.vbat_mv==b->data.charge.vbat_mv&&a->data.charge.status==b->data.charge.status;
    if(a->kind==CL_SOURCE||a->kind==CL_FIRST_VALID)return a->data.event.flags==b->data.event.flags&&a->data.event.loss==b->data.event.loss&&a->data.event.started==b->data.event.started&&a->data.event.completed==b->data.event.completed;
    return false;
}
static cl_receive store_ring(case_link *s,cl_record *ring,unsigned cap,uint8_t *next,cl_order *o,const cl_frame *f,uint64_t now) {
    int64_t tick;if(!record_time(s,f,&tick)){++s->protocol_faults;return CL_REJECTED;}
    for(unsigned i=0;i<cap;i++)if(ring[i].used&&ring[i].timing_epoch==s->timing_epoch&&ring[i].frame.sequence==f->sequence) {
        if(same_frame(&ring[i].frame,f))return CL_IGNORED;
        if(f->kind==CL_THERMAL&&(ring[i].frame.data.thermal.flags&1)&&!(f->data.thermal.flags&1)&&ring[i].frame.data.thermal.started==f->data.thermal.started)return CL_IGNORED;
        /* Only an unfinished attempt may acquire its completion. The start
         * is immutable; a completed invalid attempt cannot turn into valid. */
        if(f->kind==CL_THERMAL&&!(ring[i].frame.data.thermal.flags&1)&&(f->data.thermal.flags&1)&&ring[i].frame.data.thermal.started==f->data.thermal.started) {
            if(o->known&&o->newest!=f->sequence)for(unsigned j=0;j<cap;j++)if(ring[j].used&&ring[j].timing_epoch==s->timing_epoch&&ring[j].frame.sequence==o->newest&&tick>ring[j].completed){++s->protocol_faults;need_resync(s);return CL_RESYNC;}
            ring[i]=(cl_record){.used=true,.timing_epoch=s->timing_epoch,.frame=*f,.completed=tick,.received=now};commit_tick(s,tick);return f->field_faults?CL_PARTIAL:CL_ACCEPTED;
        }
        ++s->protocol_faults;return CL_REJECTED;
    }
    const cl_record *prior=NULL;
    if(o->known)for(unsigned i=0;i<cap;i++)if(ring[i].used&&ring[i].timing_epoch==s->timing_epoch&&ring[i].frame.sequence==o->newest)prior=&ring[i];
    int direction=order(s,o,f->sequence,now);if(direction==-2)return CL_RESYNC;
    if(prior&&((direction>0&&tick<prior->completed)||(direction<0&&tick>prior->completed))){++s->protocol_faults;need_resync(s);return CL_RESYNC;}
    if(direction<0&&s->tick_reference-tick>(int64_t)s->policy.max_gap_ms)return CL_IGNORED;
    ring[*next]=(cl_record){.used=true,.timing_epoch=s->timing_epoch,.frame=*f,.completed=tick,.received=now};*next=(uint8_t)((*next+1)%cap);
    commit_tick(s,tick);
    return f->field_faults?CL_PARTIAL:CL_ACCEPTED;
}
static cl_receive store_event(case_link *s,const cl_frame *f,uint64_t now) {
    /* An empty source/first-valid snapshot carries no event. */
    if(f->kind==CL_SOURCE&&!(f->data.event.flags&1))return CL_IGNORED;
    int64_t tick;if(!record_time(s,f,&tick)){++s->protocol_faults;return CL_REJECTED;}
    cl_event_record *e=NULL;
    for(unsigned i=0;i<CL_EVENT_CAP;i++)if(s->events[i].used&&s->events[i].sequence==f->sequence&&
        ((s->events[i].have_source&&s->events[i].source.timing_epoch==s->timing_epoch)||(s->events[i].have_valid&&s->events[i].valid.timing_epoch==s->timing_epoch)))e=&s->events[i];
    if(!e){e=&s->events[s->event_next];memset(e,0,sizeof(*e));e->used=true;e->sequence=f->sequence;s->event_next=(uint8_t)((s->event_next+1)%CL_EVENT_CAP);}
    cl_record *r=f->kind==CL_SOURCE?&e->source:&e->valid;bool exists=f->kind==CL_SOURCE?e->have_source:e->have_valid;
    cl_record *other=f->kind==CL_SOURCE?&e->valid:&e->source;bool other_exists=f->kind==CL_SOURCE?e->have_valid:e->have_source;
    if(other_exists&&other->frame.data.event.loss!=f->data.event.loss){++s->protocol_faults;need_resync(s);return CL_REJECTED;}
    if(exists) {
        if(same_frame(&r->frame,f))return CL_IGNORED;
        uint8_t old=r->frame.data.event.flags,new_flags=f->data.event.flags;
        bool available=f->kind==CL_SOURCE?(old&4)!=0:(old&1)!=0;
        bool done=f->kind==CL_SOURCE?(old&8)!=0:(old&1)!=0;
        bool new_available=f->kind==CL_SOURCE?(new_flags&4)!=0:(new_flags&1)!=0;
        bool new_done=f->kind==CL_SOURCE?(new_flags&8)!=0:(new_flags&1)!=0;
        if(r->frame.data.event.loss==f->data.event.loss&&(new_flags&old)==new_flags&&
           (!new_available||r->frame.data.event.started==f->data.event.started)&&(!new_done||r->frame.data.event.completed==f->data.event.completed))return CL_IGNORED;
        if(r->frame.data.event.loss!=f->data.event.loss||(old&new_flags)!=old||
           (available&&r->frame.data.event.started!=f->data.event.started)||(done&&r->frame.data.event.completed!=f->data.event.completed)) {
            ++s->protocol_faults;return CL_REJECTED;
        }
    }
    cl_order *o=f->kind==CL_SOURCE?&s->source_order:&s->valid_order;
    if(order(s,o,f->sequence,now)==-2)return CL_RESYNC;
    *r=(cl_record){.used=true,.timing_epoch=s->timing_epoch,.frame=*f,.completed=tick,.received=now};
    commit_tick(s,tick);
    if(f->kind==CL_SOURCE)e->have_source=true;else e->have_valid=true;
    return CL_ACCEPTED;
}
static cl_receive result(case_link *s,const cl_frame *f,uint64_t now) {
    if(!s->pending.active||f->sequence!=s->pending.id||f->data.result.session_id_echo!=s->case_session_id)return CL_IGNORED;
    if(s->pending.boot_known&&s->pending.boot_id!=f->boot_id){(void)adopt_boot(s,f->boot_id);s->pending.active=false;need_resync(s);return CL_RESYNC;}
    if(!adopt_boot(s,f->boot_id))return CL_IGNORED;
    uint8_t opcode=s->pending.opcode;uint64_t t0=s->pending.sent_ms;
    s->pending.active=false;s->pending.retryable=false;s->last_result=*f;s->have_result=true;
    if(f->data.result.result!=0)return CL_ACCEPTED;
    if(opcode==1){s->snapshot_seen=true;return CL_ACCEPTED;}
    if(opcode!=2)return CL_ACCEPTED;
    uint32_t processing;int64_t t1,t2;
    if(!s->snapshot_seen||!duration(f->data.result.received,f->data.result.completed,&processing)||
       processing>now-t0+2u*(uint64_t)s->policy.combined_timer_resolution_ms||!extend(s,f->data.result.received,&t1)) {
        ++s->protocol_faults;need_resync(s);return CL_REJECTED;
    }
    t2=t1+processing;int64_t lo=t2-(int64_t)now,hi=t1-(int64_t)t0;
    if(lo>hi){++s->protocol_faults;need_resync(s);return CL_REJECTED;}
    s->anchor.lower=lo-(int64_t)s->policy.combined_timer_resolution_ms;
    s->anchor.upper=hi+(int64_t)s->policy.combined_timer_resolution_ms;
    s->anchor.plug_tick=t2;s->anchor.case_ms=now;s->anchor.valid=true;s->resync_needed=false;
    commit_tick(s,t2);
    return CL_ACCEPTED;
}
cl_receive case_link_feed(case_link *s,uint32_t epoch,cl_kind kind,const uint8_t *bytes,size_t n,uint64_t now) {
    if(!s||!s->connected||epoch!=s->link_epoch||!case_link_poll(s,now))return CL_REJECTED;
    cl_frame f;cl_receive decoded=case_link_decode(kind,bytes,n,&f);
    if(decoded==CL_REJECTED||kind==CL_COMMAND){++s->protocol_faults;return CL_REJECTED;}
    if(f.field_faults)++s->protocol_faults;
    if(kind==CL_RESULT)return result(s,&f,now);
    if(!adopt_boot(s,f.boot_id))return CL_IGNORED;
    if(kind==CL_THERMAL)return store_ring(s,s->thermal,CL_THERMAL_CAP,&s->thermal_next,&s->thermal_order,&f,now);
    if(kind==CL_CHARGE)return store_ring(s,s->charge,CL_CHARGE_CAP,&s->charge_next,&s->charge_order,&f,now);
    return store_event(s,&f,now);
}
bool case_link_command(case_link *s,uint8_t opcode,uint32_t a,uint32_t b,uint64_t now,uint8_t out[20]) {
    if(!s||!out||!case_link_poll(s,now)||!s->connected||s->pending.active||opcode<1||opcode>4||s->next_request_id>UINT16_MAX)return false;
    if(opcode==2&&(!s->boot_known||!s->snapshot_seen))return false;
    uint16_t id=(uint16_t)s->next_request_id++;memset(out,0,20);out[0]=1;out[1]=opcode;
    w16(out+2,id);w32(out+4,s->case_session_id);w32(out+8,(uint32_t)now);w32(out+12,a);w32(out+16,b);
    s->pending.active=true;s->pending.retryable=false;s->pending.boot_known=s->boot_known;s->pending.boot_id=s->boot_id;s->pending.opcode=opcode;s->pending.id=id;s->pending.sent_ms=now;s->have_result=false;memcpy(s->pending.packet,out,20);
    return true;
}
bool case_link_retry(case_link *s,uint64_t now,uint8_t out[20]) {
    if(!s||!out||!case_link_poll(s,now)||!s->connected||s->pending.active||!s->pending.retryable||s->pending.opcode==2)return false;
    if(s->pending.boot_known&&(!s->boot_known||s->pending.boot_id!=s->boot_id))return false;
    memcpy(out,s->pending.packet,20);s->pending.active=true;s->pending.retryable=false;s->pending.sent_ms=now;s->have_result=false;return true;
}
static bool age(const case_link *s,int64_t tick,uint32_t bundle,uint64_t now,uint64_t *minimum,uint64_t *maximum) {
    if(!s->connected||s->clock_fault||!s->anchor.valid||s->resync_needed||now<s->last_case_ms||now<s->anchor.case_ms||now-s->anchor.case_ms>s->policy.max_anchor_age_ms||now>(uint64_t)INT64_MAX/4)return false;
    int64_t delta=tick-s->anchor.plug_tick;if(delta<=-(INT64_C(1)<<31)||delta>=(INT64_C(1)<<31))return false;
    uint64_t span=(uint64_t)(delta<0?-delta:delta)+(now-s->anchor.case_ms);
    uint64_t drift=(span*s->policy.combined_clock_drift_ppm+999999)/1000000;
    int64_t low=(int64_t)now-tick+s->anchor.lower-(int64_t)drift;
    int64_t high=(int64_t)now-tick+s->anchor.upper+(int64_t)drift+bundle;
    if(high<0)return false;
    *minimum=low>0?(uint64_t)low:0;*maximum=(uint64_t)high;return true;
}
static const cl_record *latest(const cl_record *r,unsigned n,uint32_t epoch) {
    const cl_record *best=NULL;for(unsigned i=0;i<n;i++)if(r[i].used&&r[i].timing_epoch==epoch&&(!best||r[i].completed>best->completed||(r[i].completed==best->completed&&(uint16_t)(r[i].frame.sequence-best->frame.sequence)<32768)))best=&r[i];return best;
}
static cl_value value(const case_link *s,const cl_record *records,unsigned n,unsigned bit,bool ratio,cl_charge_field charge,uint64_t now) {
    cl_value out={0};const cl_record *last=latest(records,n,s->timing_epoch),*best=NULL;if(!last)return out;
    for(unsigned i=0;i<n;i++)if(records[i].used&&records[i].timing_epoch==s->timing_epoch) {
        const cl_frame *f=&records[i].frame;uint16_t flags=f->kind==CL_THERMAL?f->data.thermal.flags:f->data.charge.validity;
        if((flags&(1u<<bit))&&(!best||records[i].completed>best->completed))best=&records[i];
    }
    uint16_t flags=last->frame.kind==CL_THERMAL?last->frame.data.thermal.flags:last->frame.data.charge.validity;
    out.latest_attempt_valid=(flags&(1u<<bit))!=0;if(!best){out.quality=out.latest_attempt_valid?CL_UNKNOWN:CL_INVALID;return out;}
    out.has_value=true;const cl_frame *f=&best->frame;
    if(f->kind==CL_THERMAL)out.value=ratio?f->data.thermal.ratio_q16:f->data.thermal.centi_c;
    else if(charge==CL_CURRENT)out.value=f->data.charge.current_0p1_ma;
    else if(charge==CL_TS)out.value=f->data.charge.ts_mv;
    else if(charge==CL_VBAT)out.value=f->data.charge.vbat_mv;
    else out.value=(f->data.charge.status>>(charge-CL_CHG))&1;
    if(!out.latest_attempt_valid){out.quality=CL_INVALID;(void)age(s,best->completed,f->kind==CL_CHARGE?250:0,now,&out.age_min_ms,&out.age_max_ms);return out;}
    if(!age(s,best->completed,f->kind==CL_CHARGE?250:0,now,&out.age_min_ms,&out.age_max_ms))return out;
    uint32_t fresh=f->kind==CL_CHARGE?s->policy.charge_fresh_ms[charge]:(ratio?s->policy.ratio_fresh_ms:s->policy.thermal_fresh_ms);
    out.quality=out.age_max_ms<=fresh?CL_FRESH:(out.age_min_ms>fresh?CL_AGED:CL_UNKNOWN);return out;
}
cl_value case_link_temperature(const case_link *s,uint64_t now){return value(s,s->thermal,CL_THERMAL_CAP,1,false,CL_CURRENT,now);}
cl_value case_link_ratio(const case_link *s,uint64_t now){return value(s,s->thermal,CL_THERMAL_CAP,7,true,CL_CURRENT,now);}
cl_value case_link_charge(const case_link *s,cl_charge_field f,uint64_t now){cl_value unknown={0};return (unsigned)f<CL_CHARGE_FIELDS?value(s,s->charge,CL_CHARGE_CAP,(unsigned)f,false,f,now):unknown;}
static bool match_attempt(const case_link *s,const cl_frame *e,bool require_valid,cl_frame *out) {
    unsigned matches=0;for(unsigned i=0;i<CL_THERMAL_CAP;i++)if(s->thermal[i].used&&s->thermal[i].timing_epoch==s->timing_epoch) {
        const cl_frame *f=&s->thermal[i].frame;
        uint8_t flags=f->data.thermal.flags;
        if((flags&1)&&(flags&64)&&!(flags&28)&&(!require_valid||(flags&2))&&f->data.thermal.started==e->data.event.started&&f->data.thermal.completed==e->data.event.completed){*out=*f;++matches;}
    }
    return matches==1;
}
bool case_link_event(const case_link *s,uint16_t sequence,cl_event_view *v) {
    if(!v)return false;
    memset(v,0,sizeof(*v));
    for(unsigned i=0;i<CL_EVENT_CAP;i++)if(s->events[i].used&&s->events[i].sequence==sequence&&
       ((s->events[i].have_source&&s->events[i].source.timing_epoch==s->timing_epoch)||(s->events[i].have_valid&&s->events[i].valid.timing_epoch==s->timing_epoch))) {
        const cl_event_record *e=&s->events[i];v->have_source=e->have_source;v->have_first_valid=e->have_valid;
        if(e->have_source){v->source=e->source.frame;v->interrupted=(v->source.data.event.flags&66)!=0;v->overflow=(v->source.data.event.flags&32)!=0;
            if(v->source.data.event.flags&8){v->source_attempt_matched=match_attempt(s,&v->source,false,&v->source_attempt);
                if(v->source_attempt_matched&&((v->source.data.event.flags&16)!=0)!=((v->source_attempt.data.thermal.flags&2)!=0))v->source_attempt_matched=false;}}
        if(e->have_valid){v->first_valid=e->valid.frame;v->interrupted=v->interrupted||(v->first_valid.data.event.flags&2)!=0;v->overflow=v->overflow||(v->first_valid.data.event.flags&4)!=0;
            if(v->first_valid.data.event.flags&1)v->first_valid_matched=match_attempt(s,&v->first_valid,true,&v->valid_attempt);}
        v->same_loss_identity=e->have_source&&e->have_valid&&v->source.boot_id==v->first_valid.boot_id&&v->source.data.event.loss==v->first_valid.data.event.loss;
        return true;
    }
    return false;
}
