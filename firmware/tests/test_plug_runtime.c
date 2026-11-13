#include <assert.h>
#include <math.h>
#include <stdio.h>
#include "plug_runtime.h"

int main(void) {
    float out;
    plug_scale_t scale = {0,100,0,25};
    assert(plug_map_scale(scale,50,true,0,25,&out) && out==12.5f);
    assert(plug_map_scale(scale,100,true,0,10,&out) && out==10);
    scale.output_min=25; scale.output_max=0;
    assert(plug_map_scale(scale,100,true,0,25,&out) && out==0);
    assert(!plug_map_scale(scale,NAN,true,0,25,&out));
    assert(!plug_map_scale(scale,50,false,0,25,&out));
    assert(plug_map_threshold(20,true,60,true,50));
    assert(!plug_map_threshold(60,true,70,true,50));
    assert(!plug_map_threshold(0,false,70,true,50));
    plug_wear_t wear = {0}; plug_wear_start(&wear,100);
    plug_wear_tick(&wear,PLUG_WEAR_CONFIRMED,false,true,false,200,200);
    plug_wear_tick(&wear,PLUG_WEAR_CONFIRMED,false,true,false,300,300);
    assert(wear.elapsed_ms==200 && wear.confirmed_ms==0);
    plug_wear_tick(&wear,PLUG_WEAR_CONFIRMED,true,true,false,400,400);
    plug_wear_tick(&wear,PLUG_WEAR_CONFIRMED,true,true,false,500,500);
    assert(wear.confirmed_ms==100);
    plug_wear_tick(&wear,PLUG_WEAR_REMOVED,true,true,false,600,600);
    assert(wear.confirmed_ms==100 && wear.state==PLUG_WEAR_REMOVED);
    plug_wear_tick(&wear,PLUG_WEAR_CONFIRMED,true,true,false,700,700);
    plug_wear_tick(&wear,PLUG_WEAR_CONFIRMED,true,true,false,5000,5000);
    assert(wear.confirmed_ms==100); /* no credit across a gap */
    plug_wear_pause(&wear);
    plug_wear_tick(&wear,PLUG_WEAR_CONFIRMED,true,true,false,5100,5100);
    assert(wear.confirmed_ms==100 && wear.state==PLUG_WEAR_PAUSED);
    plug_wear_start(&wear,5200);
    assert(wear.confirmed_ms==100 && wear.session_id==1);
    plug_wear_tick(&wear,PLUG_WEAR_CONFIRMED,true,true,true,5300,5300);
    assert(wear.confirmed_ms==100 && wear.state==PLUG_WEAR_UNKNOWN);
    plug_wear_end(&wear);
    plug_wear_start(&wear,6000);
    assert(wear.session_id==2 && wear.confirmed_ms==0);
    puts("PASS: configurable scaling/inversion/clamps, edge triggers, separate elapsed/qualified wear, removal, pause, gap and dock accounting");
}
