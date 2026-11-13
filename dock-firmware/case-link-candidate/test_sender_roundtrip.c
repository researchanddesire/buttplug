/* Independent receiver-side tests linked to the actual C3 pure sender. */
#include "case_link.h"
#include "test_vectors.h"
#include "case_telemetry.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static case_link client;
static thermal_history_t history;
static ct_session_t server;
static uint32_t epoch;
static cl_policy policy(void){cl_policy p={.thermal_fresh_ms=1500,.ratio_fresh_ms=1500,.charge_fresh_ms={2000,2000,2000,2000,2000,2000},.max_attempt_ms=500,.max_gap_ms=10000,.max_anchor_age_ms=60000,.max_round_trip_ms=1000,.combined_clock_drift_ppm=1000,.combined_timer_resolution_ms=2,.max_sequence_advance=4};return p;}
static void feed(const ct_reply_t *r,uint64_t now){for(size_t i=0;i<r->count;i++){cl_receive v=case_link_feed(&client,epoch,(cl_kind)r->frames[i].kind,r->frames[i].data,20,now);if(v!=CL_ACCEPTED&&v!=CL_IGNORED)fprintf(stderr,"roundtrip kind=%u status=%d flags=%u at%llu\n",r->frames[i].kind,v,r->frames[i].data[1],(unsigned long long)now);assert(v==CL_ACCEPTED||v==CL_IGNORED);}}
static void golden_crossdecode(void){
 ct_packet_t p;cl_frame decoded;
 thermal_history_init(&history,0x12345678);thermal_sample_t sample={.sequence=0xfffe,.started_ms=0xfffffff0,.sampled_ms=UINT64_C(0x100000010),.tip_millic=-12340,.raw_ratio_q16=0x8000,.valid=true,.ratio_valid=true,.source_at_start=true,.source_at_end=true};
 ct_encode_sample(&history,&sample,&p);assert(memcmp(p.data,golden_thermal,20)==0);assert(case_link_decode((cl_kind)p.kind,p.data,20,&decoded)==CL_ACCEPTED&&decoded.data.thermal.centi_c==-1234);
 ct_charge_t charge={.acquired=true,.sequence=0x7654,.validity=0x7f,.completed_ms=0x10203040,.current_0p1_ma=987,.ts_mv=1234,.vbat_mv=4123,.raw_status=0x25};
 ct_encode_charge(0x89abcdef,&charge,&p);assert(memcmp(p.data,golden_charge,20)==0);assert(case_link_decode((cl_kind)p.kind,p.data,20,&decoded)==CL_ACCEPTED&&decoded.data.charge.current_0p1_ma==987);
 thermal_removal_t e={.sequence=0x56,.observed_ms=100,.after_loss_attempted=true,.after_loss_valid=true,.first_attempt_after_loss={.started_ms=120,.sampled_ms=160,.valid=true},.first_after_loss={.started_ms=140,.sampled_ms=180,.valid=true}};
 ct_encode_source(&history,&e,false,&p);assert(memcmp(p.data,golden_source,20)==0);assert(case_link_decode((cl_kind)p.kind,p.data,20,&decoded)==CL_ACCEPTED);
 ct_encode_source(&history,&e,true,&p);assert(memcmp(p.data,golden_first_valid,20)==0);assert(case_link_decode((cl_kind)p.kind,p.data,20,&decoded)==CL_ACCEPTED);
 ct_command_t cmd;assert(ct_parse_command(golden_command,20,&cmd)&&cmd.session_id==0x23456789&&cmd.request_id==0xfffd&&cmd.case_ms==0xfffffff0);ct_encode_result(0x12345678,&cmd,CT_OK,0xfffffff8,UINT64_C(0x100000004),&p);assert(memcmp(p.data,golden_result,20)==0);assert(case_link_decode((cl_kind)p.kind,p.data,20,&decoded)==CL_ACCEPTED&&decoded.data.result.session_id_echo==0x23456789);
}
static void actual_history_and_handshake(void){
 thermal_history_init(&history,77);thermal_history_source(&history,true,6000);ct_session_init(&server);cl_policy pol=policy();assert(case_link_init(&client,0xaabbccdd,&pol,1000));epoch=case_link_connect(&client,1000);
 uint8_t cmd[20];ct_reply_t r;assert(case_link_command(&client,1,0,0,1000,cmd));assert(ct_execute(&server,&history,NULL,cmd,20,6005,6006,&r));ct_reply_complete(&server,cmd,&r,6008);feed(&r,1010);assert(client.snapshot_seen);
 assert(case_link_command(&client,2,0,0,1020,cmd));assert(ct_execute(&server,&history,NULL,cmd,20,6025,6026,&r));ct_reply_complete(&server,cmd,&r,6027);feed(&r,1030);assert(client.anchor.valid&&client.last_result.data.result.completed==6027);
 thermal_sample_t t={.sequence=1,.started_ms=6010,.sampled_ms=6050,.tip_millic=37000,.valid=true,.source_at_start=true,.source_at_end=true};assert(thermal_history_sample(&history,t,6050));thermal_history_source(&history,false,6070);
 t=(thermal_sample_t){.sequence=2,.started_ms=6070,.sampled_ms=6120,.loss_sequence_at_start=history.event_sequence,.tip_millic=0,.valid=false};assert(thermal_history_sample(&history,t,6120));
 t=(thermal_sample_t){.sequence=3,.started_ms=6150,.sampled_ms=6190,.loss_sequence_at_start=history.event_sequence,.tip_millic=35000,.valid=true};assert(thermal_history_sample(&history,t,6190));
 const thermal_sample_t *stored=&history.samples[(history.sample_next+THERMAL_SAMPLE_CAPACITY-1)%THERMAL_SAMPLE_CAPACITY];ct_packet_t p;ct_encode_sample(&history,stored,&p);assert(p.data[1]&64);assert(case_link_feed(&client,epoch,(cl_kind)p.kind,p.data,20,1200)==CL_ACCEPTED);assert(case_link_temperature(&client,1200).quality==CL_FRESH&&case_link_temperature(&client,1200).value==3500);
 assert(case_link_command(&client,3,0,0,1210,cmd));assert(ct_execute(&server,&history,NULL,cmd,20,6215,6216,&r));ct_reply_complete(&server,cmd,&r,6218);assert(r.count>=5);feed(&r,1220);assert(client.last_result.data.result.completed==6218);cl_event_view v;assert(case_link_event(&client,1,&v)&&v.source_attempt_matched&&v.first_valid_matched&&v.same_loss_identity);assert(v.source_attempt.sequence==2&&!(v.source_attempt.data.thermal.flags&2)&&v.valid_attempt.sequence==3&&(v.valid_attempt.data.thermal.flags&2));assert(v.source.data.event.started==v.source.data.event.loss);assert(history.event_count==1);
 cl_value before=case_link_temperature(&client,1220);ct_reply_t copy=r;assert(ct_execute(&server,&history,NULL,cmd,20,6225,6226,&r)&&r.count==copy.count&&r.from_cache);ct_reply_complete(&server,cmd,&r,6228);for(size_t i=0;i<r.count;i++)assert(memcmp(r.frames[i].data,copy.frames[i].data,20)==0);feed(&r,1230);cl_value after=case_link_temperature(&client,1230);assert(after.age_min_ms>=before.age_min_ms+9&&after.value==before.value&&history.event_count==1);
 history.clock_fault=true;assert(ct_execute(&server,&history,NULL,cmd,20,6230,6231,&r)&&!r.from_cache&&r.count==1);ct_reply_complete(&server,cmd,&r,6232);history.clock_fault=false;assert(ct_execute(&server,&history,NULL,cmd,20,6235,6236,&r)&&r.from_cache&&r.count==copy.count);for(size_t i=0;i<r.count;i++)assert(memcmp(r.frames[i].data,copy.frames[i].data,20)==0);
}
int main(void){assert(strcmp(CT_PROTOCOL_SHA256,CL_PROTOCOL_SHA256)==0);golden_crossdecode();actual_history_and_handshake();puts("Actual C3 sender/STM32 candidate roundtrip passed: six golden values, nonce/anchor handshake, original-timestamp replay and separate invalid-first/valid-later loss records");return 0;}
