#include "thermal_history.h"
#include <assert.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>

static thermal_history_t h;
static void sample(uint32_t sequence, uint64_t time, int32_t temperature, bool valid, bool source) {
    assert(thermal_history_sample(&h, (thermal_sample_t){.sequence=sequence,
        .started_ms=time-50,.sampled_ms=time,.tip_millic=temperature,
        .loss_sequence_at_start=h.event_sequence,
        .valid=valid,.source_at_start=source,.source_at_end=source},time));
}
static void setup(bool source) {
    thermal_history_init(&h, 42);
    thermal_history_source_snapshot(&h,source,0,0);
}
int main(void) {
    /* Booting without a source does not fabricate a removal baseline. */
    setup(false);sample(1,100,22000,true,false);
    assert(!thermal_history_latest(&h));
    thermal_history_source_snapshot(&h,true,0,500);
    sample(2,1100,22000,true,true);
    sample(3,2100,22500,true,true);
    sample(4,3100,23000,true,true);
    /* Cached10Hz polls cannot become extra1Hz samples or freshen their age. */
    thermal_sample_t cached=h.samples[3];
    assert(!thermal_history_sample(&h,cached,3150)&&h.sample_count==4);
    thermal_history_source_snapshot(&h,false,1,3200);
    const thermal_removal_t *e=thermal_history_latest(&h);
    assert(e&&e->docked_valid&&e->docked_age_ms==100&&e->last_docked.sampled_ms==3100);
    assert(e->trend_valid&&e->trend_millic_per_min==30000&&!e->after_loss_valid);
    /* A conversion straddling loss, failed conversion, and stale cache never
     * masquerade as the first fresh conversion started after observed loss. */
    assert(thermal_history_sample(&h,(thermal_sample_t){.sequence=5,.started_ms=3150,
        .sampled_ms=3250,.valid=true,.tip_millic=23100,.source_at_start=true},3250));
    assert(!e->after_loss_valid);
    sample(6,4250,0,false,false);assert(!e->after_loss_valid&&e->after_loss_attempted&&!e->first_attempt_after_loss.valid);
    sample(7,5250,23200,true,false);assert(e->after_loss_valid&&e->first_after_loss.sampled_ms==5250&&e->first_attempt_after_loss.sampled_ms==4250);
    sample(8,6250,23400,true,false);assert(e->first_after_loss.sampled_ms==5250);
    char json[THERMAL_STATUS_JSON_CAPACITY];
    assert(thermal_history_json(&h,6250,json,sizeof(json)));
    assert(strstr(json,"\"physical_removal_confirmed\":false")&&strstr(json,"\"charge_state\":\"unknown\""));
    assert(strstr(json,"\"first_after_loss_ms\":5250"));
    assert(!thermal_history_json(&h,6250,json,20)&&json[0]==0);

    /* Early loss is retained even with no charging completion or no sample. */
    setup(true);thermal_history_source_snapshot(&h,false,1,100);
    e=thermal_history_latest(&h);assert(e&&!e->docked_valid&&!e->trend_valid);
    thermal_history_source_snapshot(&h,true,1,150);
    assert(e->reconnected_before_sample);
    sample(1,250,22000,true,true);assert(!e->after_loss_valid);

    setup(true);thermal_history_source_snapshot(&h,false,1,100);
    sample(1,200,0,false,false);thermal_history_source_snapshot(&h,true,1,250);
    e=thermal_history_latest(&h);
    assert(e->reconnected_before_sample&&!e->reconnected_before_attempt&&e->after_loss_attempted&&!e->after_loss_valid);

    /* A brief loss/reconnect hidden between polls still changes the session,
     * retains the observed event and exposes ISR count without invented times. */
    setup(true);sample(1,100,22000,true,true);
    thermal_history_source_snapshot(&h,true,3,200);
    e=thermal_history_latest(&h);
    assert(h.dock_session==2&&h.source_loss_edges==3&&e->observed_ms==200&&e->reconnected_before_sample);
    assert(e->docked_valid&&!e->after_loss_valid);

    /* Invalid samples, gaps and stale last samples do not supply a trend or
     * default room temperature. A later good sample can supply the baseline. */
    setup(true);sample(1,100,22000,true,true);sample(2,1100,0,false,true);
    sample(3,2100,23000,true,true);thermal_history_source_snapshot(&h,false,1,2200);
    e=thermal_history_latest(&h);assert(e->docked_valid&&!e->trend_valid);
    setup(true);sample(1,100,22000,true,true);sample(2,2100,22500,true,true);
    sample(3,3100,23000,true,true);thermal_history_source_snapshot(&h,false,1,3200);
    assert(!thermal_history_latest(&h)->trend_valid);
    setup(true);sample(1,100,22000,true,true);thermal_history_source_snapshot(&h,false,1,1700);
    assert(!thermal_history_latest(&h)->docked_valid);
    setup(true);sample(1,100,INT_MAX,true,true);thermal_history_source_snapshot(&h,false,1,200);
    assert(!thermal_history_latest(&h)->docked_valid);

    /* Failed attempts remain in the short ring; old samples/events are bounded.
     * Every source loss records a candidate, regardless of charge progress. */
    setup(true);
    for(uint32_t i=1;i<=100;++i)sample(i,i*1000,22000,true,true);
    assert(h.sample_count==THERMAL_SAMPLE_CAPACITY&&h.samples[(h.sample_next+THERMAL_SAMPLE_CAPACITY-1)%THERMAL_SAMPLE_CAPACITY].sequence==100);
    for(uint32_t i=1;i<=25;++i) {
        thermal_history_source_snapshot(&h,false,i,100000+i*100);
        thermal_history_source_snapshot(&h,true,i,100000+i*100+50);
    }
    assert(h.event_count==THERMAL_EVENT_CAPACITY&&thermal_history_latest(&h)->sequence==25);
    thermal_history_source_snapshot(&h,true,25,10);assert(h.clock_fault);
    assert(thermal_history_json(&h,10,json,sizeof(json))&&strstr(json,"\"clock_valid\":false")&&strstr(json,"\"last_docked_millic\":null"));
    thermal_history_init(&h,43);assert(!h.sample_count&&!h.event_count&&!h.source_known&&!h.clock_fault);

    /* Worst-width timestamps/IDs and physically bounded data fit the declared
     * output size; this also catches format/argument changes under UBSan. */
    h.boot_id=UINT32_MAX;h.dock_session=UINT32_MAX;h.event_sequence=UINT32_MAX;
    h.source_loss_edges=UINT32_MAX;h.source_known=true;h.source_present=true;
    thermal_sample_t s={.sequence=UINT32_MAX,.started_ms=UINT64_MAX-101,
        .sampled_ms=UINT64_MAX-100,.tip_millic=-40000,.valid=true,.source_at_start=true,.source_at_end=true};
    assert(thermal_history_sample(&h,s,UINT64_MAX-100));
    thermal_history_source(&h,false,UINT64_MAX-50);
    s.sequence=1;s.started_ms=UINT64_MAX-11;s.sampled_ms=UINT64_MAX-10;
    s.source_at_start=s.source_at_end=false;s.tip_millic=125000;
    s.loss_sequence_at_start=h.event_sequence;
    assert(thermal_history_sample(&h,s,UINT64_MAX-10));
    assert(thermal_history_json(&h,UINT64_MAX,json,sizeof(json)));
    assert(strstr(json,"\"first_attempt_after_loss_valid\":true"));
    puts("Thermal history: actual sample age, loss/straddle/early removal, first fresh post-loss sample, invalid/gap/reconnect, bounded rings and reset/timebase tests pass.");
    return 0;
}
