#include "case_link.h"
#include "test_vectors.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static case_link s;
static uint32_t epoch;
static unsigned scenarios;
static void p16(uint8_t *p,uint16_t x){p[0]=(uint8_t)x;p[1]=(uint8_t)(x>>8);}
static void p32(uint8_t *p,uint32_t x){p16(p,(uint16_t)x);p16(p+2,(uint16_t)(x>>16));}
static uint16_t get16(const uint8_t *p){return (uint16_t)((uint16_t)p[0]|(uint16_t)((uint16_t)p[1]<<8));}
static cl_policy policy(void){cl_policy p={.thermal_fresh_ms=1500,.ratio_fresh_ms=1500,.max_attempt_ms=500,.max_gap_ms=10000,.max_anchor_age_ms=60000,.max_round_trip_ms=1000,.combined_clock_drift_ppm=1000,.combined_timer_resolution_ms=2,.max_sequence_advance=4};for(unsigned i=0;i<6;i++)p.charge_fresh_ms[i]=2000;return p;}
static void response(uint8_t p[20],uint16_t id,uint32_t nonce,uint32_t boot,uint32_t start,uint32_t end){memset(p,0,20);p[0]=1;p16(p+2,id);p32(p+4,boot);p32(p+8,start);p32(p+12,end);p32(p+16,nonce);}
static void thermal(uint8_t p[20],uint16_t seq,uint32_t boot,uint32_t start,uint32_t end,uint8_t flags,int16_t temp,uint16_t ratio){memset(p,0,20);p[0]=1;p[1]=flags;p16(p+2,seq);p32(p+4,boot);p32(p+8,start);p32(p+12,end);p16(p+16,(uint16_t)temp);p16(p+18,ratio);}
static void charge(uint8_t p[20],uint16_t seq,uint32_t tick,uint16_t validity,uint16_t current,uint16_t ts,uint16_t vbat,uint8_t status){memset(p,0,20);p[0]=1;p16(p+1,validity);p16(p+3,seq);p32(p+5,77);p32(p+9,tick);p16(p+13,current);p16(p+15,ts);p16(p+17,vbat);p[19]=status;}
static void event(uint8_t p[20],uint16_t seq,uint32_t loss,uint32_t start,uint32_t end,uint8_t flags){memset(p,0,20);p[0]=1;p[1]=flags;p16(p+2,seq);p32(p+4,77);p32(p+8,loss);p32(p+12,start);p32(p+16,end);}
static void boot(void){cl_policy p=policy();assert(case_link_init(&s,0xc001,&p,1000));epoch=case_link_connect(&s,1000);assert(epoch);}
static void anchor(uint32_t t1,uint32_t t2){uint8_t p[20],cmd[20];assert(case_link_command(&s,1,0,0,1000,cmd));response(p,get16(cmd+2),s.case_session_id,77,6005,6006);assert(case_link_feed(&s,epoch,CL_RESULT,p,20,1010)==CL_ACCEPTED);assert(s.snapshot_seen&&!s.anchor.valid);assert(case_link_command(&s,2,0,0,1020,cmd));response(p,get16(cmd+2),s.case_session_id,77,t1,t2);assert(case_link_feed(&s,epoch,CL_RESULT,p,20,1030)==CL_ACCEPTED);assert(s.anchor.valid&&!s.resync_needed);}
static void bootstrap(void){boot();anchor(6025,6027);}
static void golden(void){
 cl_frame f;assert(case_link_decode(CL_THERMAL,golden_thermal,20,&f)==CL_ACCEPTED);assert(f.sequence==0xfffe&&f.boot_id==0x12345678&&f.data.thermal.centi_c==-1234&&f.data.thermal.ratio_q16==0x8000&&f.data.thermal.started==0xfffffff0&&f.data.thermal.completed==16);
 uint8_t unaligned[21];memcpy(unaligned+1,golden_charge,20);assert(case_link_decode(CL_CHARGE,unaligned+1,20,&f)==CL_ACCEPTED);assert(f.sequence==0x7654&&f.boot_id==0x89abcdef&&f.data.charge.completed==0x10203040&&f.data.charge.current_0p1_ma==987&&f.data.charge.ts_mv==1234&&f.data.charge.vbat_mv==4123&&f.data.charge.status==0x25);
 assert(case_link_decode(CL_SOURCE,golden_source,20,&f)==CL_ACCEPTED&&f.data.event.loss==100&&f.data.event.started==120&&f.data.event.completed==160);
 assert(case_link_decode(CL_COMMAND,golden_command,20,&f)==CL_ACCEPTED&&f.sequence==0xfffd&&f.data.command.session_id==0x23456789&&f.data.command.case_tick==0xfffffff0);
 assert(case_link_decode(CL_RESULT,golden_result,20,&f)==CL_ACCEPTED&&f.data.result.session_id_echo==0x23456789&&f.data.result.received==0xfffffff8&&f.data.result.completed==4);
 assert(case_link_decode(CL_FIRST_VALID,golden_first_valid,20,&f)==CL_ACCEPTED&&f.data.event.started==140&&f.data.event.completed==180);
}
static void reject_and_partial(void){
 cl_frame f;uint8_t p[40]={0};memcpy(p,golden_charge,20);
 for(size_t n=0;n<=40;n++)if(n!=20)assert(case_link_decode(CL_CHARGE,p,n,&f)==CL_REJECTED);
 assert(case_link_decode(CL_CHARGE,NULL,20,&f)==CL_REJECTED);p[0]=2;assert(case_link_decode(CL_CHARGE,p,20,&f)==CL_REJECTED);p[0]=1;p[2]|=0x20;assert(case_link_decode(CL_CHARGE,p,20,&f)==CL_REJECTED);
 memcpy(p,golden_charge,20);p16(p+13,0xffff);assert(case_link_decode(CL_CHARGE,p,20,&f)==CL_PARTIAL&&!(f.data.charge.validity&1)&&(f.data.charge.validity&2)&&f.field_faults==1);
 p16(p+1,0x7e);p16(p+13,1);assert(case_link_decode(CL_CHARGE,p,20,&f)==CL_PARTIAL);
 memcpy(p,golden_charge,20);p16(p+1,0x37f);assert(case_link_decode(CL_CHARGE,p,20,&f)==CL_PARTIAL&&!(f.data.charge.validity&3));
 thermal(p,0,0,0,0,0x83,INT16_MIN,0xffff);assert(case_link_decode(CL_THERMAL,p,20,&f)==CL_PARTIAL&&!(f.data.thermal.flags&0x82));
 thermal(p,0,0,0,0,0x81,INT16_MIN,0x8000);assert(case_link_decode(CL_THERMAL,p,20,&f)==CL_ACCEPTED&&(f.data.thermal.flags&0x80));
 p[1]=0x80;assert(case_link_decode(CL_THERMAL,p,20,&f)==CL_PARTIAL);
 event(p,0,0,0,0,0x80);assert(case_link_decode(CL_SOURCE,p,20,&f)==CL_REJECTED);p[1]=8;assert(case_link_decode(CL_SOURCE,p,20,&f)==CL_REJECTED);p[1]=8;assert(case_link_decode(CL_FIRST_VALID,p,20,&f)==CL_REJECTED);
}
static void snapshot_and_nonce(void){
 boot();uint8_t cmd[20],p[20];assert(!case_link_command(&s,2,0,0,1000,cmd));assert(case_link_command(&s,1,0,0,1000,cmd));uint16_t id=get16(cmd+2);
 response(p,id,0xdead,77,6005,6006);assert(case_link_feed(&s,epoch,CL_RESULT,p,20,1005)==CL_IGNORED&&s.pending.active&&!s.snapshot_seen);
 response(p,(uint16_t)(id+1),s.case_session_id,77,6005,6006);assert(case_link_feed(&s,epoch,CL_RESULT,p,20,1006)==CL_IGNORED);
 response(p,id,s.case_session_id,77,6005,6006);assert(case_link_feed(&s,epoch,CL_RESULT,p,20,1010)==CL_ACCEPTED&&s.snapshot_seen);
 assert(case_link_command(&s,2,0,0,1020,cmd));response(p,get16(cmd+2),0xdead,77,6025,6027);assert(case_link_feed(&s,epoch,CL_RESULT,p,20,1030)==CL_IGNORED&&!s.anchor.valid);
 response(p,get16(cmd+2),s.case_session_id,77,6025,6027);assert(case_link_feed(&s,epoch,CL_RESULT,p,20,1031)==CL_ACCEPTED&&s.anchor.valid);
 assert(s.anchor.lower==4994&&s.anchor.upper==5007);
}
static void freshness_and_delay(void){
 bootstrap();uint8_t p[20];thermal(p,0,77,6080,6100,0x83,3210,0x5000);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1120)==CL_ACCEPTED);
 cl_value a=case_link_temperature(&s,1200);assert(a.quality==CL_FRESH&&a.value==3210&&a.age_min_ms>=90&&a.age_max_ms<=115);
 thermal(p,1,77,6081,6101,0x83,3200,0x5000);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,4000)==CL_ACCEPTED);a=case_link_temperature(&s,4000);assert(a.quality==CL_AGED&&a.age_min_ms>2800);
 assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,4100)==CL_IGNORED);cl_value b=case_link_temperature(&s,4100);assert(b.age_min_ms>a.age_min_ms&&b.value==3200);
 thermal(p,2,77,10000,10020,1,INT16_MIN,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,5030)==CL_ACCEPTED);b=case_link_temperature(&s,5030);assert(b.quality==CL_INVALID&&b.has_value&&b.value==3200&&b.age_min_ms>3800);
 thermal(p,3,77,10030,10050,0x81,INT16_MIN,0x4000);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,5060)==CL_ACCEPTED);assert(case_link_ratio(&s,5070).quality==CL_FRESH&&case_link_ratio(&s,5070).value==0x4000);assert(case_link_temperature(&s,5070).quality==CL_INVALID);
}
static void independent_charge(void){
 bootstrap();uint8_t p[20];charge(p,0,6100,0x7f,500,1300,4100,7);assert(case_link_feed(&s,epoch,CL_CHARGE,p,20,1120)==CL_ACCEPTED);
 assert(case_link_charge(&s,CL_CURRENT,1200).quality==CL_FRESH&&case_link_charge(&s,CL_CURRENT,1200).value==500);assert(case_link_charge(&s,CL_CURRENT,1200).age_max_ms>=350);
 charge(p,1,6200,0x2d,450,0xffff,4110,5);assert(case_link_feed(&s,epoch,CL_CHARGE,p,20,1220)==CL_ACCEPTED);
 assert(case_link_charge(&s,CL_TS,1230).quality==CL_INVALID&&case_link_charge(&s,CL_TS,1230).value==1300);assert(case_link_charge(&s,CL_CE,1230).quality==CL_INVALID);assert(case_link_charge(&s,CL_PGOOD,1230).quality==CL_FRESH&&case_link_charge(&s,CL_PGOOD,1230).value==1);
 charge(p,2,6300,0x2d,0xffff,0xffff,4120,5);assert(case_link_feed(&s,epoch,CL_CHARGE,p,20,1320)==CL_PARTIAL);assert(case_link_charge(&s,CL_CURRENT,1330).quality==CL_INVALID&&case_link_charge(&s,CL_CURRENT,1330).value==450);assert(case_link_charge(&s,CL_VBAT,1330).quality==CL_FRESH);
}
static void uncertainty_and_expiry(void){
 bootstrap();uint8_t p[20];thermal(p,0,77,6080,6100,3,2500,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1120)==CL_ACCEPTED);
 cl_value a=case_link_temperature(&s,2595);assert(a.quality==CL_UNKNOWN&&a.age_min_ms<1500&&a.age_max_ms>1500);
 assert(case_link_temperature(&s,61031).quality==CL_UNKNOWN);assert(case_link_poll(&s,61031)&&!s.anchor.valid&&!s.snapshot_seen);
}
static void wraps(void){
 boot();anchor(0xfffffff9,0xfffffffc);uint8_t p[20];thermal(p,0xffff,77,0xfffffff8,0x10,3,-100,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1060)==CL_ACCEPTED);assert(case_link_temperature(&s,1070).quality==CL_FRESH);
 thermal(p,0,77,0x11,0x20,3,0,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1075)==CL_ACCEPTED);assert(s.thermal_order.newest==0&&case_link_temperature(&s,1080).value==0);
 cl_tick32_clock c={0};uint64_t t;assert(cl_tick32_update(&c,0xfffffffe,&t)&&t==0xfffffffe);assert(cl_tick32_update(&c,2,&t)&&t==UINT64_C(0x100000002));assert(!cl_tick32_update(&c,0x80000002,&t)&&c.fault);
}
static void reordered_and_conflicts(void){
 bootstrap();uint8_t p[20];thermal(p,10,77,6080,6100,3,1000,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1120)==CL_ACCEPTED);
 thermal(p,9,77,5980,6000,3,900,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1130)==CL_ACCEPTED);assert(s.thermal_order.newest==10&&case_link_temperature(&s,1140).value==1000);
 int64_t ref=s.tick_reference;thermal(p,10,77,6080,7000000,3,999,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1150)==CL_REJECTED&&s.tick_reference==ref);
 thermal(p,11,77,5800,5900,3,1100,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1160)==CL_RESYNC&&!s.anchor.valid);assert(case_link_temperature(&s,1160).quality==CL_UNKNOWN);
}
static void missing_and_ambiguous(void){
 bootstrap();s.policy.max_sequence_advance=1;uint8_t p[20];thermal(p,0,77,6080,6100,3,1000,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1120)==CL_ACCEPTED);
 thermal(p,2,77,6180,6200,3,1200,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1220)==CL_RESYNC);assert(s.resync_needed&&!s.anchor.valid&&s.missing_sequences==1&&!s.history_continuous);
 bootstrap();thermal(p,0,77,6080,6100,3,1000,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1120)==CL_ACCEPTED);thermal(p,0x8000,77,6180,6200,3,1200,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1220)==CL_RESYNC);
 bootstrap();thermal(p,0,77,6080,6100,3,1000,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1120)==CL_ACCEPTED);thermal(p,1,77,6100+0x80000000u,6100+0x80000000u,3,1200,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1220)==CL_REJECTED&&s.resync_needed);
}
static void distinct_source_attempts(void){
 bootstrap();uint8_t p[20];cl_event_view v;event(p,3,6090,6100,6120,0x0d);assert(case_link_feed(&s,epoch,CL_SOURCE,p,20,1130)==CL_ACCEPTED);event(p,3,6090,6300,6320,1);assert(case_link_feed(&s,epoch,CL_FIRST_VALID,p,20,1330)==CL_ACCEPTED);
 assert(case_link_event(&s,3,&v)&&v.same_loss_identity&&!v.source_attempt_matched&&!v.first_valid_matched);
 thermal(p,10,77,6100,6120,0x61,INT16_MIN,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1340)==CL_ACCEPTED);thermal(p,11,77,6300,6320,0x43,2710,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1350)==CL_ACCEPTED);
 assert(case_link_event(&s,3,&v)&&v.source_attempt_matched&&v.first_valid_matched&&!(v.source_attempt.data.thermal.flags&2)&&(v.valid_attempt.data.thermal.flags&2));assert(v.source_attempt.sequence==10&&v.valid_attempt.sequence==11);
 event(p,3,6090,0,0,1);assert(case_link_feed(&s,epoch,CL_SOURCE,p,20,1360)==CL_IGNORED);assert(case_link_event(&s,3,&v)&&v.source_attempt_matched);
 event(p,3,6090,6100,6120,0x6d);assert(case_link_feed(&s,epoch,CL_SOURCE,p,20,1370)==CL_ACCEPTED);assert(case_link_event(&s,3,&v)&&v.interrupted&&v.overflow);
 event(p,3,6091,6300,6320,1);assert(case_link_feed(&s,epoch,CL_FIRST_VALID,p,20,1380)==CL_REJECTED&&s.resync_needed);assert(!case_link_event(&s,3,&v));
}
static void completion_updates(void){
 bootstrap();uint8_t p[20];thermal(p,0,77,6100,0,0,INT16_MIN,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1120)==CL_ACCEPTED);thermal(p,0,77,6100,6120,3,2800,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1130)==CL_ACCEPTED);assert(case_link_temperature(&s,1140).quality==CL_FRESH);
 thermal(p,0,77,6100,0,0,INT16_MIN,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1150)==CL_IGNORED);thermal(p,0,77,6100,6120,3,2801,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1160)==CL_REJECTED);assert(case_link_temperature(&s,1170).value==2800);
}
static void reconnect_and_boot(void){
 bootstrap();uint8_t p[20],cmd[20];thermal(p,0,77,6080,6100,3,3000,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1120)==CL_ACCEPTED);assert(case_link_command(&s,3,0,0,1130,cmd));uint32_t old=epoch;case_link_disconnect(&s,1140);epoch=case_link_connect(&s,1150);assert(epoch!=old&&!s.pending.active&&!s.anchor.valid);assert(case_link_feed(&s,old,CL_THERMAL,p,20,1)==CL_REJECTED&&!s.clock_fault);
 thermal(p,0,88,6080,6100,3,3000,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1160)==CL_ACCEPTED&&case_link_temperature(&s,1170).quality==CL_UNKNOWN);
 thermal(p,1,99,100,120,3,2000,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1180)==CL_ACCEPTED&&s.boot_id==99);thermal(p,1,88,6200,6220,3,4000,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1190)==CL_IGNORED&&s.boot_id==99);
}
static void timeout_retry_and_exhaustion(void){
 bootstrap();uint8_t cmd[20],copy[20],p[20];assert(case_link_command(&s,3,0,0,1100,cmd));uint32_t count=s.next_request_id;assert(!case_link_command(&s,3,0,0,1101,copy));assert(case_link_poll(&s,2101)&&!s.pending.active&&s.pending.retryable);assert(case_link_retry(&s,2102,copy)&&memcmp(cmd,copy,20)==0&&s.next_request_id==count);
 response(p,get16(cmd+2),s.case_session_id,77,6105,6106);assert(case_link_feed(&s,epoch,CL_RESULT,p,20,2110)==CL_ACCEPTED&&!s.pending.retryable);assert(!case_link_retry(&s,2111,copy));
 s.next_request_id=65535;assert(case_link_command(&s,1,0,0,2120,cmd)&&get16(cmd+2)==65535);response(p,65535,s.case_session_id,77,7125,7126);assert(case_link_feed(&s,epoch,CL_RESULT,p,20,2130)==CL_ACCEPTED);assert(!case_link_command(&s,1,0,0,2140,cmd));assert(!case_link_new_session(&s,s.case_session_id,2141));assert(case_link_new_session(&s,0xc002,2142)&&s.next_request_id==0&&!s.anchor.valid);assert(case_link_command(&s,1,0,0,2143,cmd)&&get16(cmd+2)==0);
}
static void bad_anchor_and_clock(void){
 boot();uint8_t p[20],cmd[20];assert(case_link_command(&s,1,0,0,1000,cmd));response(p,get16(cmd+2),s.case_session_id,77,6005,6006);assert(case_link_feed(&s,epoch,CL_RESULT,p,20,1010)==CL_ACCEPTED);assert(case_link_command(&s,2,0,0,1020,cmd));response(p,get16(cmd+2),s.case_session_id,77,6025,6045);assert(case_link_feed(&s,epoch,CL_RESULT,p,20,1030)==CL_REJECTED&&!s.anchor.valid);
 bootstrap();assert(case_link_command(&s,2,0,0,1100,cmd));response(p,get16(cmd+2),s.case_session_id,77,6105,6106);assert(case_link_feed(&s,epoch,CL_RESULT,p,20,2101)==CL_IGNORED);assert(!case_link_retry(&s,2102,p));assert(case_link_poll(&s,2103));assert(!case_link_poll(&s,2102)&&s.clock_fault);assert(!case_link_command(&s,1,0,0,2110,cmd));
}
static void bounded_rings(void){
 bootstrap();uint8_t p[20];for(unsigned i=0;i<80;i++){thermal(p,(uint16_t)i,77,6080+i*10,6100+i*10,3,(int16_t)i,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1120+i*10)==CL_ACCEPTED);}unsigned n=0;for(unsigned i=0;i<CL_THERMAL_CAP;i++)n+=s.thermal[i].used;assert(n==CL_THERMAL_CAP&&case_link_temperature(&s,1920).value==79);
 for(unsigned i=0;i<20;i++){event(p,(uint16_t)i,7000+i,0,0,1);assert(case_link_feed(&s,epoch,CL_SOURCE,p,20,1930+i)==CL_ACCEPTED);}cl_event_view v;assert(!case_link_event(&s,0,&v)&&case_link_event(&s,19,&v));
}
static void bounded_input_fuzz(void){cl_frame f;uint32_t x=0x12345678;uint8_t p[20];for(unsigned k=0;k<5000;k++){for(unsigned i=0;i<20;i++){x^=x<<13;x^=x>>17;x^=x<<5;p[i]=(uint8_t)x;}p[0]=1;(void)case_link_decode((cl_kind)(1+k%6),p,20,&f);}}
static void excessive_gap_and_policy(void){
 bootstrap();uint8_t p[20];thermal(p,0,77,6080,6100,3,1000,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1120)==CL_ACCEPTED);thermal(p,1,77,17000,17020,3,1100,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,12030)==CL_RESYNC&&s.resync_needed&&!s.anchor.valid);
 cl_policy q=policy();q.combined_clock_drift_ppm=0;assert(!case_link_init(&s,1,&q,0));q=policy();q.max_sequence_advance=32768;assert(!case_link_init(&s,1,&q,0));q=policy();q.charge_fresh_ms[2]=0;assert(!case_link_init(&s,1,&q,0));
}
static void completion_chronology_regression(void){
 bootstrap();uint8_t p[20];thermal(p,10,77,7000,0,0,INT16_MIN,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,2010)==CL_ACCEPTED);thermal(p,11,77,7200,7250,3,3700,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,2260)==CL_ACCEPTED);assert(case_link_temperature(&s,2260).value==3700);
 thermal(p,10,77,7000,7300,3,2000,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,2310)==CL_RESYNC&&s.resync_needed);assert(case_link_temperature(&s,2310).quality==CL_UNKNOWN&&!case_link_temperature(&s,2310).has_value);
 bootstrap();thermal(p,10,77,7000,0,0,INT16_MIN,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,2010)==CL_ACCEPTED);thermal(p,11,77,7200,7250,3,3700,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,2260)==CL_ACCEPTED);thermal(p,10,77,7000,7200,3,2000,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,2310)==CL_ACCEPTED);assert(case_link_temperature(&s,2310).value==3700);
}
static void reanchor_does_not_remap_old_history(void){
 bootstrap();uint8_t p[20],cmd[20];thermal(p,0,77,6080,6100,3,3700,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1120)==CL_ACCEPTED);uint32_t old=s.timing_epoch;thermal(p,100,77,980,1000,3,2000,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1220)==CL_RESYNC&&s.timing_epoch!=old);
 assert(case_link_command(&s,1,0,0,1230,cmd));response(p,get16(cmd+2),s.case_session_id,77,1005,1006);assert(case_link_feed(&s,epoch,CL_RESULT,p,20,1240)==CL_ACCEPTED);assert(case_link_command(&s,2,0,0,1250,cmd));response(p,get16(cmd+2),s.case_session_id,77,1015,1017);assert(case_link_feed(&s,epoch,CL_RESULT,p,20,1260)==CL_ACCEPTED);
 assert(!case_link_temperature(&s,1260).has_value);thermal(p,100,77,1020,1040,3,2000,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1290)==CL_ACCEPTED);assert(case_link_temperature(&s,1290).quality==CL_FRESH&&case_link_temperature(&s,1290).value==2000);assert(case_link_charge(&s,(cl_charge_field)-1,1290).quality==CL_UNKNOWN);
}
static void causal_flags_not_timestamp_equality(void){
 const uint8_t flags[4]={3,0x43,0x47,0x53};
 for(unsigned i=0;i<4;i++){bootstrap();uint8_t p[20];thermal(p,1,77,6100,6120,flags[i],2800,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1130)==CL_ACCEPTED);event(p,1,6100,6100,6120,0x1d);assert(case_link_feed(&s,epoch,CL_SOURCE,p,20,1140)==CL_ACCEPTED);cl_event_view v;assert(case_link_event(&s,1,&v)&&v.source_attempt_matched==(i==1));}
 bootstrap();uint8_t p[20];thermal(p,0,77,0,1,0x43,2800,0xffff);assert(case_link_feed(&s,epoch,CL_THERMAL,p,20,1130)==CL_ACCEPTED);event(p,0,0,0,1,0x1d);assert(case_link_feed(&s,epoch,CL_SOURCE,p,20,1140)==CL_ACCEPTED);cl_event_view v;assert(case_link_event(&s,0,&v)&&v.source_attempt_matched);
}
#define RUN(f) do{f();++scenarios;}while(0)
int main(void){RUN(golden);RUN(reject_and_partial);RUN(snapshot_and_nonce);RUN(freshness_and_delay);RUN(independent_charge);RUN(uncertainty_and_expiry);RUN(wraps);RUN(reordered_and_conflicts);RUN(missing_and_ambiguous);RUN(distinct_source_attempts);RUN(completion_updates);RUN(reconnect_and_boot);RUN(timeout_retry_and_exhaustion);RUN(bad_anchor_and_clock);RUN(bounded_rings);RUN(bounded_input_fuzz);RUN(excessive_gap_and_policy);RUN(completion_chronology_regression);RUN(reanchor_does_not_remap_old_history);RUN(causal_flags_not_timestamp_equality);printf("%u behavior scenarios passed; sizeof(case_link)=%zu bytes\n",scenarios,sizeof(case_link));return 0;}
