#include "dock_app.h"
#include "lcd.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
static unsigned scenarios;
static dock_inputs healthy(uint32_t now){
 return(dock_inputs){.now_ms=now,.monitor_ms=now,.loop_a=true,.loop_b=true,.source_ok=true,
 .device_limit_ok=true,.uv_limit_ok=true,.ntc_valid=true,.monitor_valid=true,
 .base_centi_c=2500,.lid_centi_c=2500,.base_mV=3000,.lid_mV=3000,.source=SOURCE_1A5};
}
static void step(dock_app *a,dock_inputs *i){i->now_ms+=10;i->monitor_ms=i->now_ms;dock_step(a,i);}
static void boot(dock_app *a,dock_inputs *i){
 dock_init(a);for(unsigned n=0;n<110;++n)step(a,i);
 assert(a->state==DOCK_PRESS_TO_ARM && !a->arm && a->stop_n);
}
static void arm(dock_app *a,dock_inputs *i){
 i->center=true;step(a,i);assert(a->state==DOCK_RELEASE_TO_ARM && !a->arm);
 i->center=false;i->release_seen=true;step(a,i);assert(a->state==DOCK_READY && a->arm);
}
static void start(dock_app *a,dock_inputs *i){
 i->center=true;i->uv_run=true;i->uv_vbus_present=true;
 i->base_uA=54800;i->lid_uA=54800;i->base_mV=14000;i->lid_mV=14100;step(a,i);
 assert(a->state==DOCK_RUNNING && a->stop_n && !a->arm);
}
static void startup_and_fresh_edges(void){
 dock_app a;dock_inputs i=healthy(0);i.center=true;boot(&a,&i);
 for(unsigned n=0;n<100;++n)step(&a,&i);
 assert(a.state==DOCK_PRESS_TO_ARM && !a.arm);
 i.center=false;step(&a,&i);assert(!a.arm);arm(&a,&i);
 /* Waiting for a new press does not create a software-generated UV_RUN. */
 for(unsigned n=0;n<100;++n)step(&a,&i);
 assert(a.state==DOCK_READY && a.arm);start(&a,&i);++scenarios;
}
static void interruption_and_pending_press(void){
 dock_app a;dock_inputs i=healthy(0);boot(&a,&i);arm(&a,&i);start(&a,&i);
 i.loop_a=false;step(&a,&i);assert(a.state==DOCK_FAULT && !a.stop_n && !a.arm);
 /* Debounced CENTER remains held through interruption and recovery. */
 i.loop_a=true;i.uv_run=false;i.release_seen=false;i.base_uA=0;i.lid_uA=0;
 for(unsigned n=0;n<100;++n)step(&a,&i);
 assert(a.state==DOCK_FAULT && !a.stop_n && !a.arm);
 i.center=false;step(&a,&i);assert(a.state==DOCK_FAULT);
 i.center=true;step(&a,&i);assert(a.state==DOCK_RELEASE_TO_ARM && !a.arm);
 i.center=false;step(&a,&i);assert(!a.arm); /* Wait for physical latch acknowledgement. */
 i.release_seen=true;step(&a,&i);assert(a.state==DOCK_READY && a.arm);
 start(&a,&i);++scenarios;
}
static void each_interruption(void){
 for(unsigned n=0;n<9;++n){
  dock_app a;dock_inputs i=healthy(0);boot(&a,&i);arm(&a,&i);start(&a,&i);
  switch(n){
   case 0:i.loop_a=false;break;case 1:i.loop_b=false;break;
   case 2:i.source_ok=false;break;case 3:i.source=SOURCE_DEFAULT;break;
   case 4:i.ntc_valid=false;break;case 5:i.base_centi_c=3800;break;
   case 6:i.lid_centi_c=3800;break;case 7:i.device_limit_ok=false;break;
   case 8:i.uv_limit_ok=false;break;
  }
  step(&a,&i);assert(a.state==DOCK_FAULT && !a.arm && !a.stop_n);++scenarios;
 }
}
static void monitor_and_latch_faults(void){
 for(unsigned n=0;n<7;++n){
  dock_app a;dock_inputs i=healthy(0);boot(&a,&i);arm(&a,&i);start(&a,&i);
  i.center=false;for(unsigned t=0;t<31;++t)step(&a,&i);assert(a.state==DOCK_RUNNING);
  switch(n){case 0:i.base_uA=0;break;case 1:i.lid_uA=80000;break;
   case 2:i.base_mV=39000;break;case 3:i.lid_mV=1000;break;
   case 4:i.uv_run=false;break;case 5:i.uv_vbus_present=false;break;
   case 6:i.monitor_valid=false;break;}
  step(&a,&i);assert(a.state==DOCK_FAULT && !a.stop_n && !a.arm);++scenarios;
 }
 dock_app a;dock_inputs i=healthy(0);boot(&a,&i);arm(&a,&i);start(&a,&i);
 i.now_ms+=200;dock_step(&a,&i);assert(a.state==DOCK_FAULT && a.fault==FAULT_MONITOR);++scenarios;
 /* Unexpected hardware output while unarmed is an actual latch fault. */
 i=healthy(0);boot(&a,&i);i.uv_run=true;step(&a,&i);
 assert(a.state==DOCK_FAULT && a.fault==FAULT_LATCH && !a.stop_n);++scenarios;
}
static void timeout_wrap_and_cancel(void){
 dock_app a;dock_inputs i=healthy(UINT32_MAX-2500);boot(&a,&i);arm(&a,&i);start(&a,&i);
 i.center=false;for(unsigned t=0;t<3000;++t)step(&a,&i);
 assert(a.state==DOCK_COMPLETE && !a.stop_n && !a.arm && a.remaining_seconds==0);
 i.uv_run=false;i.release_seen=false;i.base_uA=0;i.lid_uA=0;
 for(unsigned t=0;t<1000;++t)step(&a,&i);
 assert(a.state==DOCK_COMPLETE && !a.stop_n);arm(&a,&i);start(&a,&i);
 i.center=false;step(&a,&i);i.center=true;i.uv_run=false;step(&a,&i);
 assert(a.state==DOCK_COMPLETE && !a.stop_n && !a.arm);++scenarios;
}
static void supervisor_and_rail_settling(void){
 dock_app a;dock_inputs i=healthy(0);boot(&a,&i);arm(&a,&i);start(&a,&i);
 i.center=false;i.uv_vbus_present=false;
 for(unsigned n=0;n<20;++n)step(&a,&i);assert(a.state==DOCK_RUNNING);
 i.uv_vbus_present=true;for(unsigned n=0;n<20;++n)step(&a,&i);assert(a.state==DOCK_RUNNING);
 i.loop_b=false;step(&a,&i);assert(a.state==DOCK_FAULT);
 i.loop_b=true;i.uv_run=false;i.release_seen=false;i.base_uA=0;i.lid_uA=0;
 step(&a,&i);i.center=true;step(&a,&i);assert(a.state==DOCK_FAULT && !a.stop_n);
 /* An early press held through the supervisor delay cannot count later. */
 for(unsigned n=0;n<60;++n)step(&a,&i);assert(a.state==DOCK_FAULT && !a.stop_n);
 i.center=false;step(&a,&i);arm(&a,&i);++scenarios;
}
static void menus_do_not_arm(void){
 dock_app a;dock_inputs i=healthy(0);boot(&a,&i);
 i.right=true;step(&a,&i);assert(a.trial_seconds==60 && !a.arm);
 i.right=false;step(&a,&i);i.right=true;step(&a,&i);assert(a.trial_seconds==120 && !a.arm);
 i.left=true;for(unsigned t=0;t<205;++t)step(&a,&i);assert(a.contrast_mode && !a.arm);
 i.left=false;i.right=false;step(&a,&i);i.right=true;step(&a,&i);
 assert(a.contrast==0x11 && !a.arm);++scenarios;
}
static void conversions(void){
 int16_t temp;uint32_t value;
 assert(dock_ntc_centi_c(2048,&temp) && temp==2500);
 assert(dock_ntc_centi_c(1678,&temp) && temp==3500);
 assert(dock_ntc_centi_c(1507,&temp) && temp==4000);
 assert(!dock_ntc_centi_c(0,&temp) && !dock_ntc_centi_c(4095,&temp));
#ifdef DOCK_WIRED_MAIN
 assert(dock_ads_decode(0,12800,&value) && value==47393);
#else
 assert(dock_ads_decode(0,12800,&value) && value==54794);
#endif
 assert(dock_ads_decode(2,19866,&value) && value>38990 && value<39010);
 assert(dock_ads_decode(3,32767,&value) && value>64000); /* No32-bit overflow. */
 assert(dock_ads_decode(0,-1,&value) && value==0);
 assert(!dock_ads_decode(0,-33,&value) && !dock_ads_decode(4,1,&value));
 assert(dock_decode_source(true,true)==SOURCE_UNATTACHED);
 assert(dock_decode_source(true,false)==SOURCE_DEFAULT);
 assert(dock_decode_source(false,true)==SOURCE_1A5);
 assert(dock_decode_source(false,false)==SOURCE_3A);++scenarios;
}
static unsigned commands,data_count,reset_count,delay_ms;
static uint8_t command_trace[128],screen[1024];
void board_lcd_write(bool data,uint8_t v){
 if(data){assert(data_count<1024);screen[data_count++]=v;}
 else {assert(commands<128);command_trace[commands++]=v;}
}
void board_lcd_reset(bool high){assert(high==(reset_count!=0));++reset_count;}
void board_delay_ms(uint32_t ms){delay_ms+=ms;}
static void save_display(const char *path){
 FILE *f=fopen(path,"w");assert(f);fputs("P1\n512 256\n",f);
 for(unsigned y=0;y<256;++y){for(unsigned x=0;x<512;++x){unsigned xx=x/4,yy=y/4;
  fprintf(f,"%u ",(screen[(yy/8)*128+xx]>>(yy%8))&1u);}fputc('\n',f);}fclose(f);
}
static void display_trace(void){
 lcd_init(0x10);const uint8_t start_trace[]={0xae,0xa2,0xa0,0xc8,0xa4,0x40,0x25,0x81,0x10,0x2f};
 assert(reset_count==2 && delay_ms==45 && data_count==1024);
 assert(!memcmp(start_trace,command_trace,sizeof(start_trace)) && command_trace[commands-1]==0xaf);
 for(unsigned j=0;j<1024;++j)assert(screen[j]==0);
 dock_app a;dock_inputs i=healthy(0);boot(&a,&i);arm(&a,&i);
 commands=0;data_count=0;lcd_render(&a,&i);lcd_flush();assert(data_count==1024 && commands==24);
 uint8_t full_screen[1024],full_commands[24];
 memcpy(full_screen,screen,sizeof(full_screen));memcpy(full_commands,command_trace,sizeof(full_commands));
 commands=0;data_count=0;
 lcd_flush_page(8);assert(commands==0 && data_count==0);
 for(unsigned page=0;page<8;++page){
  lcd_flush_page(page);assert(data_count==128*(page+1) && commands==3*(page+1));
 }
 assert(!memcmp(full_screen,screen,sizeof(full_screen)));
 assert(!memcmp(full_commands,command_trace,sizeof(full_commands)));
 unsigned lit=0;for(unsigned j=0;j<1024;++j)lit+=screen[j]!=0;assert(lit>200);
#ifdef DOCK_WIRED_MAIN
 i.loop_a=i.loop_b=false;step(&a,&i);
 assert(a.state==DOCK_FAULT && !a.arm && !a.stop_n);
 lcd_render(&a,&i);commands=0;data_count=0;lcd_flush();
 memcpy(full_screen,screen,sizeof(full_screen));
 host_client host={.local_requested=true,.have_status=true,
                   .flags=HOST_STATUS_LOCAL | HOST_STATUS_TIP_VALID,.tip_centi_c=2860};
 lcd_render_host(&host,true,true);commands=0;data_count=0;lcd_flush();
 assert(!memcmp(full_screen,screen,128) && !memcmp(full_screen+2*128,screen+2*128,3*128));
 assert(!memcmp(full_screen+7*128,screen+7*128,128) && memcmp(full_screen+128,screen+128,128));
 assert(memcmp(full_screen+5*128,screen+5*128,2*128));
 uint8_t shown[128];memcpy(shown,screen+5*128,sizeof(shown));
 save_display("tests/.build/display-wired-preview.pbm");
 host.have_status=false;
 lcd_render_host(&host,true,true);commands=0;data_count=0;lcd_flush();
 assert(memcmp(shown,screen+5*128,sizeof(shown)));
#else
 save_display("tests/.build/display-preview.pbm");
#endif
 ++scenarios;
}
int main(void){startup_and_fresh_edges();interruption_and_pending_press();each_interruption();
 monitor_and_latch_faults();timeout_wrap_and_cancel();supervisor_and_rail_settling();menus_do_not_arm();conversions();display_trace();
 printf("PASS: %u behavior scenarios, real app transitions/conversions/LCD bus trace\n",scenarios);return 0;}
