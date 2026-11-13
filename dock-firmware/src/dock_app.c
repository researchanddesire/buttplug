#include "dock_app.h"

static uint32_t elapsed(uint32_t now, uint32_t then) { return now - then; }
void dock_init(dock_app *a) {
    *a = (dock_app){.state=DOCK_BOOT, .trial_seconds=30, .contrast=0x10};
}
dock_source dock_decode_source(bool one, bool two) {
    return one ? (two ? SOURCE_UNATTACHED : SOURCE_DEFAULT)
               : (two ? SOURCE_1A5 : SOURCE_3A);
}
static dock_fault safe_inputs(const dock_inputs *i, bool running, bool check_off_current) {
    if (!i->source_ok || i->source < SOURCE_1A5) return FAULT_SOURCE;
    if (!i->loop_a || !i->loop_b) return FAULT_LID_THERMAL;
    if (!i->device_limit_ok || !i->uv_limit_ok) return FAULT_CURRENT_LIMIT;
    if (!i->ntc_valid) return FAULT_NTC;
    if (i->base_centi_c >= 3800 || i->lid_centi_c >= 3800) return FAULT_HOT;
    if (!running && (i->base_centi_c < 1000 || i->lid_centi_c < 1000 ||
                     i->base_centi_c > 3500 || i->lid_centi_c > 3500)) return FAULT_HOT;
    if (!i->monitor_valid || elapsed(i->now_ms,i->monitor_ms)>150) return FAULT_MONITOR;
    if (i->base_mV>42000 || i->lid_mV>42000) return FAULT_LED_VOLTAGE;
    if (check_off_current && (i->base_uA>3000 || i->lid_uA>3000)) return FAULT_LED_CURRENT;
    return FAULT_NONE;
}
static void fail(dock_app *a, dock_fault fault) {
    a->state=DOCK_FAULT; a->fault=fault; a->arm=false; a->stop_n=false;
    a->release_pending=false; a->start_pending=false; a->healthy_tracking=false;
}
void dock_step(dock_app *a, const dock_inputs *i) {
    bool press=false, release=false, left=false, right=false;
    if (a->initialized) {
        press=i->center && !a->previous_center;
        release=!i->center && a->previous_center;
        left=i->left && !a->previous_left;
        right=i->right && !a->previous_right;
    }
    a->initialized=true;
    a->previous_center=i->center; a->previous_left=i->left; a->previous_right=i->right;
    a->arm=false; a->stop_n=false; a->led=false;
    bool active=a->state==DOCK_RUNNING || (a->state==DOCK_READY && i->uv_run);
    if (active) a->off_tracking=false;
    else if (!a->off_tracking) { a->off_tracking=true; a->off_since_ms=i->now_ms; }
    dock_fault health=safe_inputs(i,active,!active && elapsed(i->now_ms,a->off_since_ms)>=300);
    if (a->state==DOCK_BOOT) {
        a->fault=health;
        if (i->uv_run) { fail(a,FAULT_LATCH); return; }
        if (health!=FAULT_NONE) { a->healthy_tracking=false; return; }
        if (!a->healthy_tracking) { a->healthy_tracking=true; a->healthy_since_ms=i->now_ms; }
        if (elapsed(i->now_ms,a->healthy_since_ms)<1000) return;
        a->state=DOCK_PRESS_TO_ARM; a->fault=FAULT_NONE;
        /* No press sampled during startup can count as the first fresh press. */
        press=false; release=false;
    } else if (health!=FAULT_NONE) { fail(a,health); return; }

    if (a->state!=DOCK_RUNNING && a->state!=DOCK_READY && i->uv_run) {
        fail(a,FAULT_LATCH); return;
    }
    /* Hold both side buttons two seconds to select contrast instead of time.
       CENTER always belongs to the physical UV start/stop workflow. */
    if (a->state!=DOCK_RUNNING) {
        if (i->left && i->right) {
            if (!a->both_tracking) { a->both_tracking=true; a->both_since_ms=i->now_ms; }
            if (!a->both_handled && elapsed(i->now_ms,a->both_since_ms)>=2000) {
                a->contrast_mode=!a->contrast_mode; a->both_handled=true;
            }
        } else {
            a->both_tracking=false; a->both_handled=false;
            if (left || right) {
                if (a->contrast_mode) {
                    if (left && a->contrast>0) --a->contrast;
                    if (right && a->contrast<63) ++a->contrast;
                } else if (left) a->trial_seconds=a->trial_seconds==120?60:30;
                else a->trial_seconds=a->trial_seconds==30?60:120;
            }
        }
    }
    switch (a->state) {
    case DOCK_PRESS_TO_ARM:
        a->stop_n=true;
        if (press) { a->state=DOCK_RELEASE_TO_ARM; a->release_pending=false; }
        break;
    case DOCK_RELEASE_TO_ARM:
        a->stop_n=true;
        if (release) a->release_pending=true;
        if (a->release_pending && !i->center && i->release_seen) {
            a->state=DOCK_READY; a->fault=FAULT_NONE; a->arm=true;
            a->release_pending=false; a->start_pending=false;
        }
        break;
    case DOCK_READY:
        a->stop_n=true; a->arm=true; a->led=true;
        if (!i->release_seen) { fail(a,FAULT_LATCH); break; }
        if (i->uv_run) {
            a->state=DOCK_RUNNING; a->run_since_ms=i->now_ms;
            a->arm=false; a->start_pending=false;
            a->remaining_seconds=a->trial_seconds;
        } else if (press) { a->start_pending=true; a->start_request_ms=i->now_ms; }
        else if (a->start_pending && elapsed(i->now_ms,a->start_request_ms)>100) fail(a,FAULT_LATCH);
        break;
    case DOCK_RUNNING: {
        a->stop_n=true; a->led=(i->now_ms/250)%2!=0;
        uint32_t run_ms=elapsed(i->now_ms,a->run_since_ms);
        if (press || run_ms>=(uint32_t)a->trial_seconds*1000) {
            a->state=DOCK_COMPLETE; a->stop_n=false; a->remaining_seconds=0;
        } else if (!i->uv_run || !i->release_seen) fail(a,FAULT_LATCH);
        else if (run_ms>=300) {
            if (!i->uv_vbus_present) fail(a,FAULT_LATCH);
            else if (i->base_uA<45000 || i->base_uA>75000 || i->lid_uA<45000 || i->lid_uA>75000)
                fail(a,FAULT_LED_CURRENT);
            else if (i->base_mV<7000 || i->base_mV>19000 || i->lid_mV<7000 || i->lid_mV>19000)
                fail(a,FAULT_LED_VOLTAGE);
        }
        if (a->state==DOCK_RUNNING) a->remaining_seconds=(uint16_t)(a->trial_seconds-run_ms/1000);
        break;
    }
    case DOCK_FAULT:
        /* The hardware UV release supervisor can hold CLEARn low for420ms
           after raw interlocks recover. Do not consume an acknowledgement
           gesture while that supervisor can still discard the release edge. */
        if(!a->healthy_tracking){a->healthy_tracking=true;a->healthy_since_ms=i->now_ms;}
        if(elapsed(i->now_ms,a->healthy_since_ms)<500)break;
        /* fall through */
    case DOCK_COMPLETE:
        if (press) { a->state=DOCK_RELEASE_TO_ARM; a->stop_n=true; a->release_pending=false; }
        break;
    case DOCK_BOOT: break;
    }
}
const char *dock_state_text(dock_state s) {
    switch(s) {
    case DOCK_BOOT:return "CHECKING INTERLOCKS";
    case DOCK_PRESS_TO_ARM:return "PRESS THEN RELEASE";
    case DOCK_RELEASE_TO_ARM:return "RELEASE TO ARM";
    case DOCK_READY:return "READY: PRESS START";
    case DOCK_RUNNING:return "UV TRIAL RUNNING";
    case DOCK_COMPLETE:return "TIMER ENDED / STOPPED";
    case DOCK_FAULT:return "FAULT: PRESS-RELEASE";
    }
    return "INVALID STATE";
}
const char *dock_fault_text(dock_fault f) {
    switch(f) {
    case FAULT_NONE:return "";
    case FAULT_SOURCE:return "NEED 1.5A TYPE-C";
    case FAULT_LID_THERMAL:return "LID / THERMAL LOOP";
    case FAULT_NTC:return "TEMP SENSOR FAULT";
    case FAULT_HOT:return "TEMP OUTSIDE LIMIT";
    case FAULT_MONITOR:return "MONITOR NOT FRESH";
    case FAULT_CURRENT_LIMIT:return "POWER LIMIT FAULT";
    case FAULT_LATCH:return "INTERLOCK LATCH FAULT";
    case FAULT_LED_CURRENT:return "LED CURRENT FAULT";
    case FAULT_LED_VOLTAGE:return "LED VOLTAGE FAULT";
    }
    return "INVALID FAULT";
}
bool dock_ads_decode(unsigned channel, int16_t adc, uint32_t *value) {
    if (channel>3 || adc< -32 || value==0) return false;
    /* Ground-referenced channels can return a small negative code from ADC
       offset/noise. A32-count allocation is clamped to zero; larger negative
       excursions fail instead of wrapping into an unsigned current/voltage. */
    if(adc<0)adc=0;
    /* Channels0/1: +/-0.512V, 15.625uV/count across the UV sense resistor.
       Channels2/3: +/-4.096V, 125uV/count; divider1M/68k. */
    *value=channel<2 ? (uint32_t)adc*15625u/DOCK_UV_SENSE_MILLIOHM
                     : (uint32_t)adc*1068u/544u;
    return true;
}
