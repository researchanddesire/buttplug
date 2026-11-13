#include "case_runtime.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

static ct_runtime_t runtime;
static thermal_history_t history;
static uint64_t now;
static uint64_t clock_ms(void) { return now++; }
static void command(uint8_t p[20],uint8_t op,uint16_t id,uint32_t nonce) {
    memset(p,0,20);p[0]=1;p[1]=op;p[2]=(uint8_t)id;p[3]=(uint8_t)(id>>8);
    for(unsigned i=0;i<4;++i)p[4+i]=(uint8_t)(nonce>>(8*i));
}
static void update(void) { ct_runtime_update(&runtime,&history,NULL,clock_ms); }
static void setup(void) {
    ct_runtime_init(&runtime);thermal_history_init(&history,123);thermal_history_source_snapshot(&history,true,0,0);now=100;
}
int main(void) {
    setup();uint8_t bytes[20],out[20];ct_transmission_t tx,again;
    assert(ct_runtime_open(&runtime,7)&&!ct_runtime_read(&runtime,7,CT_THERMAL,out));
    command(bytes,2,0,42);assert(!ct_runtime_enqueue(&runtime,7,bytes,now));
    update();assert(ct_runtime_read(&runtime,7,CT_THERMAL,out)&&out[0]==1&&out[1]==0);
    assert(!ct_runtime_read(&runtime,7,CT_COMMAND,out)&&!ct_runtime_read(&runtime,7,CT_RESULT,out));
    assert(ct_runtime_enqueue(&runtime,7,bytes,now)&&!ct_runtime_enqueue(&runtime,7,bytes,now));
    update();assert(ct_runtime_read(&runtime,7,CT_RESULT,out)&&out[1]==CT_OK&&out[16]==42);
    assert(ct_runtime_peek(&runtime,7,1u<<CT_RESULT,now,&tx)&&tx.packet.kind==CT_RESULT);
    /* A failed transport send makes exactly the same offer retryable. */
    assert(ct_runtime_peek(&runtime,7,1u<<CT_RESULT,now+1,&again)&&
        again.epoch==tx.epoch&&again.token==tx.token&&!memcmp(again.packet.data,tx.packet.data,20));
    assert(!ct_runtime_enqueue(&runtime,7,bytes,now));
    ct_runtime_sent(&runtime,7,&tx);
    assert(!ct_runtime_peek(&runtime,7,1u<<CT_RESULT,now,&tx));

    /* Per-peer idempotency/result state: another client can use the same ID
     * without seeing this connection's result or blocking its own request. */
    assert(ct_runtime_open(&runtime,8));command(bytes,2,0,99);
    assert(ct_runtime_enqueue(&runtime,8,bytes,now));update();
    assert(ct_runtime_read(&runtime,7,CT_RESULT,out)&&out[16]==42);
    assert(ct_runtime_read(&runtime,8,CT_RESULT,out)&&out[16]==99);
    /* Do not acknowledge a new peer's queue with an old connection token. */
    assert(ct_runtime_peek(&runtime,8,1u<<CT_RESULT,now,&tx));ct_runtime_close(&runtime,8);
    assert(!ct_runtime_read(&runtime,8,CT_RESULT,out));assert(ct_runtime_open(&runtime,8));
    command(bytes,2,0,101);assert(ct_runtime_enqueue(&runtime,8,bytes,now));update();
    ct_runtime_sent(&runtime,8,&tx);
    assert(ct_runtime_peek(&runtime,8,1u<<CT_RESULT,now,&again)&&again.epoch!=tx.epoch&&again.packet.data[16]==101);
    ct_runtime_sent(&runtime,8,&again);

    /* Queued input from a dead epoch cannot run after handle reuse. */
    command(bytes,3,1,101);assert(ct_runtime_enqueue(&runtime,8,bytes,now));
    ct_runtime_close(&runtime,8);assert(ct_runtime_open(&runtime,8));update();
    assert(!ct_runtime_read(&runtime,8,CT_RESULT,out));

    setup();update();assert(ct_runtime_open(&runtime,1));
    /* Routine changes coalesce; four characteristics can be sent in one cycle
     * but a10Hz producer cannot create10Hz BLE traffic. Reads remain current. */
    unsigned count=0;
    while(ct_runtime_peek(&runtime,1,CT_ROUTINE_MASK,200,&tx)) { ct_runtime_sent(&runtime,1,&tx);++count; }
    assert(count==4);
    assert(thermal_history_sample(&history,(thermal_sample_t){.sequence=1,.started_ms=250,.sampled_ms=300,
        .source_at_start=true,.source_at_end=true,.valid=true,.tip_millic=22000},300));
    now=301;update();assert(!ct_runtime_peek(&runtime,1,CT_ROUTINE_MASK,1199,&tx));
    assert(ct_runtime_read(&runtime,1,CT_THERMAL,out)&&(out[1]&2));
    assert(ct_runtime_peek(&runtime,1,CT_ROUTINE_MASK,1200,&tx)&&tx.packet.kind==CT_THERMAL);
    ct_runtime_sent(&runtime,1,&tx);assert(!ct_runtime_peek(&runtime,1,CT_ROUTINE_MASK,1200,&tx));

    /* Unsubscribed responses are drained without sending; the current result
     * stays readable. Snapshot reply bursts fit without partial-queue loss. */
    command(bytes,1,0,500);assert(ct_runtime_enqueue(&runtime,1,bytes,now));update();
    assert(!ct_runtime_peek(&runtime,1,0,now,&tx));
    assert(ct_runtime_read(&runtime,1,CT_RESULT,out)&&out[1]==CT_OK);
    command(bytes,2,1,500);assert(ct_runtime_enqueue(&runtime,1,bytes,now));
    assert(ct_runtime_open(&runtime,2)&&ct_runtime_open(&runtime,3)&&!ct_runtime_open(&runtime,4));
    assert(ct_runtime_enqueue(&runtime,2,bytes,now)&&ct_runtime_enqueue(&runtime,3,bytes,now));
    assert(runtime.command_count==CT_PEER_CAPACITY);update();assert(runtime.command_count==0);
    puts("Case runtime: peer isolation, handle epochs, dead queued requests, bounded backpressure/retry, subscription filtering and1Hz coalescing pass.");
    return 0;
}
