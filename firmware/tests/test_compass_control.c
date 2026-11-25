#include <assert.h>
#include <stdio.h>
#include "compass_control.h"
#include "compass_protocol.h"
#include "proto_control.h"

static void packets(void) {
    compass_command_t c;
    const uint8_t stop[] = {0,0}, duty[] = {1,25}, north[] = {3,1,0,0,15,10};
    const uint8_t west[] = {3,1,14,1,5,25};
    assert(compass_decode_command(stop,2,&c) && c.opcode==0);
    assert(compass_decode_command(duty,2,&c) && c.value==25);
    assert(compass_decode_command(north,6,&c) && c.target_deg==0 && c.tolerance_deg==15);
    assert(compass_decode_command(west,6,&c) && c.target_deg==270 && c.value==25);
    const uint8_t renew[] = {4,1,14,1,5,25};
    assert(compass_decode_command(renew,6,&c) && c.opcode==COMPASS_CMD_RENEW);
    for (uint8_t opcode=PLUG_CMD_START; opcode<=PLUG_CMD_END; opcode++) {
        uint8_t command[] = {opcode,1};
        assert(compass_decode_command(command,2,&c) && c.opcode==opcode);
        command[1]=0; assert(!compass_decode_command(command,2,&c));
    }
    uint8_t bad[][6] = {{3,2,0,0,15,10}, {3,1,104,1,15,10}, {3,1,0,0,4,10},
        {3,1,0,0,46,10}, {3,1,0,0,15,0}, {3,1,0,0,15,26}, {2,1,0,0,15,10}};
    for (unsigned i=0;i<sizeof(bad)/sizeof(*bad);i++) assert(!compass_decode_command(bad[i],6,&c));
    assert(!compass_decode_command(north,5,&c));
    assert(!compass_decode_command(north,2,&c));
    assert(!compass_decode_command(NULL,6,&c));
    const uint8_t bad_stop[] = {0,1}, bad_duty[] = {1,26}, internal[] = {2,0};
    assert(!compass_decode_command(bad_stop,2,&c));
    assert(!compass_decode_command(bad_duty,2,&c));
    assert(!compass_decode_command(internal,2,&c));
}
static void pulses(void) {
    compass_control_t c; compass_init(&c);
    assert(compass_request(&c,0,15,10,100));
    assert(compass_tick(&c,true,true,359000,100,100)==0); /* pre-start sample */
    assert(compass_tick(&c,true,true,359000,200,200)==0);
    assert(compass_tick(&c,true,true,359000,200,220)==0); /* same sample */
    assert(compass_tick(&c,true,true,1000,300,300)==10);
    assert(c.phase==COMPASS_PULSING && c.aligned);
    assert(compass_tick(&c,true,false,0,300,479)==10); /* intentional blanking */
    assert(compass_renew(&c,0,15,10,480)); /* renew must not stretch pulse */
    assert(compass_tick(&c,true,false,0,300,480)==0);
    assert(c.phase==COMPASS_SETTLING);
    assert(compass_tick(&c,true,true,0,1400,1479)==0);
    assert(compass_tick(&c,true,true,0,1480,1480)==0); /* needs post-settle sample */
    assert(compass_tick(&c,true,true,0,1500,1500)==0);
    assert(compass_tick(&c,true,true,0,1600,1600)==10);
    assert(compass_tick(&c,false,true,0,1600,1620)==0 && !c.active);
    assert(compass_tick(&c,true,true,0,1700,1700)==0); /* no auto-resume */
    assert(!compass_renew(&c,0,15,10,1700));
}
static void rejection_and_changes(void) {
    compass_control_t c; compass_init(&c);
    assert(!compass_request(&c,360,15,10,100));
    assert(compass_request(&c,0,15,10,100));
    assert(compass_tick(&c,true,true,90000,200,200)==0 && c.phase==COMPASS_TURNING);
    assert(compass_tick(&c,true,false,0,300,300)==0);
    assert(compass_tick(&c,true,true,0,400,400)==0);
    assert(compass_tick(&c,true,true,0,400,1000)==0); /* stale resets sequence */
    assert(compass_tick(&c,true,true,0,1100,1100)==0);
    assert(compass_tick(&c,true,true,0,1200,1200)==10);
    assert(compass_request(&c,180,15,12,1250));
    assert(compass_tick(&c,true,true,180000,1300,1300)==0 && c.phase==COMPASS_SETTLING);
    assert(compass_tick(&c,true,true,180000,2300,2300)==0);
    assert(compass_tick(&c,true,true,180000,2400,2400)==12);
    assert(compass_tick(&c,true,false,0,2400,4250)==0 && !c.active); /* app lease */
    assert(compass_bearing_error(359000,0)==-1000);
    assert(compass_bearing_error(1000,359)==2000);
    assert(compass_bearing_error(180000,0)==-180000);
    compass_request(&c,0,15,10,5000);
    assert(compass_tick(&c,true,true,0,5101,5100)==0); /* future timestamp */
    assert(compass_tick(&c,true,true,-1,5200,5200)==0);
    assert(compass_tick(&c,true,true,360000,5300,5300)==0);
    compass_stop(&c);
    assert(!c.active && c.phase==COMPASS_IDLE);
    compass_request(&c,0,15,10,6000);
    assert(!compass_renew(&c,90,15,10,6100));
    assert(!compass_renew(&c,0,15,10,9000)); /* expiry wins even before tick */
}
static void independent_gate(void) {
    compass_control_t c; compass_init(&c);
    r0_control_t guard;
    r0_limits_t limits = {true,25,50000,3000,3000,60000,2500};
    r0_control_init(&guard,limits);
    r0_inputs_t input = {.sensors_valid=true,.temperature_millic=25000,.battery_mv=3800,.sampled_ms=100};
    r0_control_tick(&guard,input,100);
    assert(r0_local_arm(&guard,100));
    compass_request(&c,90,15,20,100);
    compass_tick(&c,true,true,90000,200,200);
    unsigned duty=compass_tick(&c,true,true,90000,300,300);
    assert(duty==20 && r0_request_motor(&guard,duty,300));
    input.docked=true; input.sampled_ms=320;
    r0_control_tick(&guard,input,320);
    assert(!guard.armed && guard.output_percent==0);
    assert(compass_tick(&c,guard.armed,true,90000,320,320)==0 && !c.active);
    input.docked=false; input.sampled_ms=400;
    r0_control_tick(&guard,input,400);
    assert(guard.output_percent==0 && !guard.armed);
}
int main(void) {
    packets(); pulses(); rejection_and_changes(); independent_gate();
    puts("PASS: Compass packet bounds, north wrap, fresh distinct samples, pulse/settle cycle, lease, retarget, stop, dock and independent motor gate");
}
