#include "case_telemetry.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void hex(const char *s, uint8_t *out) {
    for (size_t i=0;i<20;++i) { char b[3]={s[2*i],s[2*i+1],0};out[i]=(uint8_t)strtoul(b,NULL,16); }
}
static void matches(const ct_packet_t *p, unsigned kind, const char *expected) {
    uint8_t bytes[20];hex(expected,bytes);assert(p->kind==kind&&!memcmp(bytes,p->data,20));
}
static void p16(uint8_t *p, uint16_t x) { p[0]=(uint8_t)x;p[1]=(uint8_t)(x>>8); }
static void p32(uint8_t *p, uint32_t x) { for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(x>>(8*i)); }
static void command(uint8_t out[20], uint8_t op, uint16_t id, uint32_t nonce, uint32_t arg) {
    memset(out,0,20);out[0]=1;out[1]=op;p16(out+2,id);p32(out+4,nonce);p32(out+12,arg);
}
static unsigned result(const ct_reply_t *r) {
    assert(r->count&&r->frames[r->count-1].kind==CT_RESULT);return r->frames[r->count-1].data[1];
}
static thermal_history_t h;
static ct_session_t session;
static void attempt(uint32_t seq,uint64_t start,uint64_t end,bool source,bool valid,int32_t temp) {
    assert(thermal_history_sample(&h,(thermal_sample_t){.sequence=seq,.started_ms=start,.sampled_ms=end,
        .loss_sequence_at_start=h.event_sequence,.source_at_start=source,.source_at_end=source,
        .valid=valid,.tip_millic=temp},end));
}
int main(void) {
    /* Literal vectors were independently authored with Python struct by the
     * case receiver owner, including unaligned charge fields and tick wrap. */
    thermal_history_init(&h,0x12345678);
    thermal_sample_t sample={.sequence=65534,.started_ms=0xfffffff0ULL,.sampled_ms=0x100000010ULL,
        .tip_millic=-12340,.valid=true,.ratio_valid=true,.raw_ratio_q16=32768,
        .source_at_start=true,.source_at_end=true,.docked=true};
    ct_packet_t packet;ct_encode_sample(&h,&sample,&packet);
    matches(&packet,1,"018ffeff78563412f0ffffff100000002efb0080");
    ct_charge_t charge={.acquired=true,.sequence=30292,.validity=127,.completed_ms=0x10203040,
        .current_0p1_ma=987,.ts_mv=1234,.vbat_mv=4123,.raw_status=37};
    ct_encode_charge(0x89abcdef,&charge,&packet);
    matches(&packet,2,"017f005476efcdab8940302010db03d2041b1025");
    thermal_removal_t event={.sequence=86,.observed_ms=100,.after_loss_attempted=true,.after_loss_valid=true,
        .first_attempt_after_loss={.started_ms=120,.sampled_ms=160,.valid=true},
        .first_after_loss={.started_ms=140,.sampled_ms=180,.valid=true}};
    ct_encode_source(&h,&event,false,&packet);matches(&packet,3,"011d5600785634126400000078000000a0000000");
    ct_encode_source(&h,&event,true,&packet);matches(&packet,6,"0101560078563412640000008c000000b4000000");
    uint8_t bytes[20];hex("0102fdff89674523f0ffffff0000000000000000",bytes);
    ct_command_t c;assert(ct_parse_command(bytes,20,&c)&&c.request_id==65533&&c.session_id==0x23456789&&c.opcode==2&&c.case_ms==0xfffffff0);
    ct_encode_result(h.boot_id,&c,CT_OK,0xfffffff8ULL,0x100000004ULL,&packet);
    matches(&packet,5,"0100fdff78563412f8ffffff0400000089674523");
    assert(!ct_parse_command(bytes,19,&c)&&!ct_parse_command(bytes,21,&c));
    bytes[0]=2;assert(!ct_parse_command(bytes,20,&c));

    /* Unavailable fields have explicit sentinels; valid temperature does not
     * invent optional ratio or any charger-completion/Ready interpretation. */
    sample.ratio_valid=false;ct_encode_sample(&h,&sample,&packet);
    assert(!(packet.data[1]&128)&&packet.data[18]==255&&packet.data[19]==255);
    sample.valid=false;ct_encode_sample(&h,&sample,&packet);
    assert(!(packet.data[1]&2)&&(packet.data[1]&32)&&packet.data[16]==0&&packet.data[17]==128);
    charge.current_0p1_ma=0xffff;ct_encode_charge(h.boot_id,&charge,&packet);
    assert(!(packet.data[1]&CT_ISET_VALID)&&packet.data[13]==255&&packet.data[14]==255);
    ct_encode_charge(h.boot_id,NULL,&packet);assert(packet.data[1]==0&&packet.data[2]==4&&packet.data[13]==255);

    thermal_history_init(&h,42);ct_session_init(&session);thermal_history_source_snapshot(&h,true,0,0);
    attempt(1,50,100,true,true,22000);
    thermal_history_source_snapshot(&h,false,1,200);
    /* A zero-duration/pre-observation attempt with the same millisecond tick
     * is not proof of causal post-loss order. The pre-start event ID decides. */
    assert(thermal_history_sample(&h,(thermal_sample_t){.sequence=2,.started_ms=200,.sampled_ms=200,
        .loss_sequence_at_start=0,.valid=true,.tip_millic=22100},200));
    assert(!thermal_history_latest(&h)->after_loss_attempted);
    attempt(3,210,250,false,false,0);attempt(4,310,350,false,true,22200);
    const thermal_removal_t *e=thermal_history_latest(&h);
    assert(e->after_loss_attempted&&e->after_loss_valid&&!e->first_attempt_after_loss.valid);
    ct_reply_t reply,duplicate;command(bytes,3,0,0x11223344,0);
    assert(ct_execute(&session,&h,NULL,bytes,20,400,401,&reply)&&result(&reply)==CT_OK&&reply.count==6);
    assert(h.event_count==1&&h.event_sequence==1);
    unsigned thermal_count=0;
    for(size_t i=0;i<reply.count;++i)if(reply.frames[i].kind==CT_THERMAL)++thermal_count;
    assert(thermal_count==3); /* last docked, failed attempt, first valid */
    assert(ct_execute(&session,&h,NULL,bytes,20,500,501,&duplicate)&&reply.count==duplicate.count&&
           !memcmp(reply.frames,duplicate.frames,reply.count*sizeof(ct_packet_t)));
    assert(h.event_count==1); /* Duplicate did not create another baseline. */
    bytes[8]=1;assert(ct_execute(&session,&h,NULL,bytes,20,600,601,&duplicate)&&result(&duplicate)==CT_INVALID_ARGUMENT);

    /* Replay carries acquisition timestamps, even when routine sample history
     * has rolled over. Required event copies are retained in their own ring. */
    for(uint32_t i=5;i<80;++i)attempt(i,1000+i*1000,1050+i*1000,false,true,22500);
    command(bytes,4,1,0x11223344,1);
    assert(ct_execute(&session,&h,NULL,bytes,20,81000,81001,&reply)&&result(&reply)==CT_OK&&reply.count==6);
    assert(reply.frames[0].data[12]==100&&reply.frames[1].data[12]==250);
    for(uint16_t id=2;id<12;++id) {
        command(bytes,2,id,0x11223344,0);
        assert(ct_execute(&session,&h,NULL,bytes,20,82000,82001,&reply)&&result(&reply)==CT_OK);
    }
    command(bytes,3,0,0x11223344,0);
    assert(ct_execute(&session,&h,NULL,bytes,20,83000,83001,&reply)&&result(&reply)==CT_HISTORY_UNAVAILABLE);
    assert(h.event_count==1);
    command(bytes,2,65535,0x11223344,0);assert(ct_execute(&session,&h,NULL,bytes,20,84000,84001,&reply)&&result(&reply)==CT_OK);
    command(bytes,2,0,0x11223344,0);assert(ct_execute(&session,&h,NULL,bytes,20,85000,85001,&reply)&&result(&reply)==CT_HISTORY_UNAVAILABLE);
    command(bytes,2,0,0x55667788,0);assert(ct_execute(&session,&h,NULL,bytes,20,86000,86001,&reply)&&result(&reply)==CT_OK);
    assert(reply.frames[0].data[16]==0x88&&reply.frames[0].data[19]==0x55);

    command(bytes,1,1,0x55667788,0);assert(ct_execute(&session,&h,NULL,bytes,20,87000,90001,&reply)&&result(&reply)==CT_BUSY_OR_STALE);
    command(bytes,0x80,2,0x55667788,0);assert(ct_execute(&session,&h,NULL,bytes,20,91000,91001,&reply)&&result(&reply)==CT_UNSUPPORTED);
    command(bytes,2,3,0x55667788,1);assert(ct_execute(&session,&h,NULL,bytes,20,92000,92001,&reply)&&result(&reply)==CT_INVALID_ARGUMENT);
    command(bytes,4,4,0x55667788,999);assert(ct_execute(&session,&h,NULL,bytes,20,93000,93001,&reply)&&result(&reply)==CT_HISTORY_UNAVAILABLE);
    command(bytes,1,5,0x55667788,0);assert(ct_execute(&session,&h,NULL,bytes,20,94000,94001,&reply)&&result(&reply)==CT_OK&&reply.count==5);
    h.clock_fault=true;command(bytes,1,6,0x55667788,0);
    assert(ct_execute(&session,&h,NULL,bytes,20,95000,95001,&reply)&&result(&reply)==CT_BUSY_OR_STALE&&reply.count==1);
    ct_snapshot(&h,&charge,&reply);assert(!(reply.frames[0].data[1]&1)&&!(reply.frames[1].data[1]&CT_VBAT_VALID));
    puts("Case sender: independent20-byte fixtures, invalid fields, causal post-loss order, bounded replay/idempotency, session echo, stale/unsupported commands and clock faults pass.");
    return 0;
}
