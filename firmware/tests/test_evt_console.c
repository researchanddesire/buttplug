#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "evt_console.h"
#include "driver/gpio.h"
#include "driver/usb_serial_jtag.h"
#include "hal/usb_serial_jtag_ll.h"
#include "nvs.h"
#include "cJSON.h"

static int dock_level,critical_depth,install_count,read_count,erase_count,commit_count,status_count;
static bool pads,rx_irq,install_fails,detach_in_install,redock_in_install,detach_in_read,detach_in_nvs;
static bool installing;
static int service_error;
static void (*detach_handler)(void *);
static void *detach_arg;
static void (*shutdown_handler)(void);
static char queued[2048],fifo[64];
static size_t queued_size,fifo_size;
static unsigned pad_off_events;

void fake_enter(void) {++critical_depth;}
void fake_exit(void) {assert(critical_depth>0);--critical_depth;}
static void detach(bool redock) {
    assert(critical_depth==0 && detach_handler);
    dock_level=1;
    unsigned before=pad_off_events;
    detach_handler(detach_arg);
    assert(!pads && !rx_irq && pad_off_events==before+1);
    if(redock)dock_level=0;
}
static void enqueue(const char *text) {
    size_t n=strlen(text);assert(queued_size+n<=sizeof(queued));
    memcpy(queued+queued_size,text,n);queued_size+=n;
}
esp_err_t gpio_install_isr_service(int flags) {assert(flags==1);return service_error;}
esp_err_t gpio_set_intr_type(int pin,int type) {assert(pin==20&&type==GPIO_INTR_POSEDGE);return ESP_OK;}
esp_err_t gpio_isr_handler_add(int pin,void (*handler)(void *),void *arg) {
    assert(pin==20);detach_handler=handler;detach_arg=arg;return ESP_OK;
}
int gpio_get_level(int pin) {assert(pin==20);return dock_level;}
esp_err_t esp_register_shutdown_handler(void (*handler)(void)) {shutdown_handler=handler;return ESP_OK;}
void usb_serial_jtag_ll_phy_enable_pad(bool enabled) {
    if(enabled&&!pads&&!installing)assert(queued_size==0&&fifo_size==0);
    pads=enabled;if(!enabled)++pad_off_events;
}
void usb_serial_jtag_ll_disable_intr_mask(uint32_t mask) {
    assert(mask==USB_SERIAL_JTAG_INTR_SERIAL_OUT_RECV_PKT);assert(!pads);rx_irq=false;
}
void usb_serial_jtag_ll_ena_intr_mask(uint32_t mask) {assert(mask==USB_SERIAL_JTAG_INTR_SERIAL_OUT_RECV_PKT);rx_irq=true;}
void usb_serial_jtag_ll_clr_intsts_mask(uint32_t mask) {assert(mask==USB_SERIAL_JTAG_INTR_SERIAL_OUT_RECV_PKT);}
int usb_serial_jtag_ll_read_rxfifo(uint8_t *out,uint32_t length) {
    assert(!pads&&!rx_irq);size_t n=fifo_size<length?fifo_size:length;
    memcpy(out,fifo,n);memmove(fifo,fifo+n,fifo_size-n);fifo_size-=n;return(int)n;
}
esp_err_t usb_serial_jtag_driver_install(usb_serial_jtag_driver_config_t *config) {
    ++install_count;assert(config->rx_buffer_size==1024&&config->tx_buffer_size==2048);
    installing=true;
    if(detach_in_install)detach(redock_in_install);
    /* Model the helper re-enabling pads AFTER a detach ISR, including failure. */
    usb_serial_jtag_ll_phy_enable_pad(true);rx_irq=true;installing=false;
    return install_fails?ESP_FAIL:ESP_OK;
}
int usb_serial_jtag_read_bytes(void *out,uint32_t length,int timeout) {
    assert(timeout==0);++read_count;size_t n=queued_size<length?queued_size:length;
    memcpy(out,queued,n);memmove(queued,queued+n,queued_size-n);queued_size-=n;
    if(detach_in_read){detach_in_read=false;detach(true);}
    return(int)n;
}
esp_err_t nvs_open(const char *name,int mode,nvs_handle_t *handle) {
    assert(!strcmp(name,"evt1"));*handle=1;
    if(mode==NVS_READONLY){assert(!pads);return ESP_ERR_NVS_NOT_FOUND;}
    if(detach_in_nvs){detach_in_nvs=false;detach(true);}
    return ESP_OK;
}
esp_err_t nvs_get_blob(nvs_handle_t h,const char*n,void*d,size_t*l){(void)h;(void)n;(void)d;(void)l;return ESP_ERR_NVS_NOT_FOUND;}
esp_err_t nvs_erase_key(nvs_handle_t h,const char*n){(void)h;assert(!strcmp(n,"compass"));++erase_count;return ESP_OK;}
esp_err_t nvs_set_blob(nvs_handle_t h,const char*n,const void*d,size_t l){(void)h;(void)n;(void)d;(void)l;return ESP_OK;}
esp_err_t nvs_commit(nvs_handle_t h){(void)h;++commit_count;return ESP_OK;}
void nvs_close(nvs_handle_t h){(void)h;}
const char *esp_err_to_name(esp_err_t e){return e==ESP_OK?"ESP_OK":"error";}
size_t r0_status_json(char *out,size_t length){++status_count;return(size_t)snprintf(out,length,"{\"ok\":true}");}
size_t r0_thermal_status_json(char *out,size_t length){return(size_t)snprintf(out,length,"{\"protocol\":\"thermal-v1\"}");}
cJSON *cJSON_GetObjectItemCaseSensitive(const cJSON*r,const char*n){(void)r;(void)n;return NULL;}
int cJSON_IsArray(const cJSON*v){(void)v;return 0;}
int cJSON_GetArraySize(const cJSON*v){(void)v;return 0;}
cJSON *cJSON_GetArrayItem(const cJSON*v,int i){(void)v;(void)i;return NULL;}
int cJSON_IsNumber(const cJSON*v){(void)v;return 0;}
cJSON *cJSON_ParseWithOpts(const char*t,const char**e,int r){(void)t;(void)e;(void)r;return NULL;}
int cJSON_IsObject(const cJSON*v){(void)v;return 0;}
void cJSON_Delete(cJSON*v){(void)v;}

static evt_compass_cal_t cal;
static void reset(bool docked) {
    dock_level=docked?0:1;critical_depth=0;install_count=read_count=erase_count=commit_count=status_count=0;
    pads=true;rx_irq=true;install_fails=detach_in_install=redock_in_install=detach_in_read=detach_in_nvs=false;
    installing=false;service_error=0;detach_handler=NULL;shutdown_handler=NULL;queued_size=fifo_size=0;pad_off_events=0;
    assert(evt_console_transport_init(0)==ESP_OK);
    assert(!pads&&!rx_irq&&install_count==0&&shutdown_handler);
    evt_console_load_calibration(&cal);assert(install_count==0&&!pads);
}
static void connect_at(uint64_t now) {
    dock_level=0;assert(evt_console_transport_tick(now)==ESP_OK);
    evt_console_poll(&cal); /* Qualification must survive normal polling. */
    assert(!pads);
    assert(evt_console_transport_tick(now+99)==ESP_OK&&!pads);
    assert(evt_console_transport_tick(now+100)==ESP_OK&&pads);
}
int main(void) {
    reset(false);assert(evt_console_transport_tick(1000)==ESP_OK&&!pads&&install_count==0);
    connect_at(1000);assert(install_count==1);enqueue("status\n");evt_console_poll(&cal);assert(status_count==1);
    bool source_present;
    assert(evt_console_source_snapshot(&source_present)==0&&source_present&&pads&&rx_irq);
    enqueue("thermal-status\n");evt_console_poll(&cal);assert(pads&&rx_irq);
    detach(true);
    assert(evt_console_source_snapshot(&source_present)==1&&source_present&&!pads&&!rx_irq);

    reset(true);assert(evt_console_transport_tick(99)==ESP_OK&&!pads);
    evt_console_poll(&cal);assert(evt_console_transport_tick(100)==ESP_OK&&pads&&install_count==1);

    reset(false);dock_level=0;assert(evt_console_transport_tick(0)==ESP_OK);
    assert(evt_console_transport_tick(50)==ESP_OK&&!pads);detach(true);
    assert(evt_console_transport_tick(100)==ESP_OK&&!pads);
    assert(evt_console_transport_tick(199)==ESP_OK&&!pads);
    assert(evt_console_transport_tick(200)==ESP_OK&&pads&&install_count==1);

    reset(false);connect_at(0);enqueue("compass-cl");evt_console_poll(&cal);
    enqueue("ear\n");detach(true);evt_console_poll(&cal);
    assert(!pads&&queued_size==0&&erase_count==0);connect_at(200);
    enqueue("ear\n");evt_console_poll(&cal);assert(erase_count==0);
    enqueue("compass-clear\n");evt_console_poll(&cal);assert(erase_count==1&&commit_count==1&&install_count==1);

    reset(false);connect_at(0);enqueue("compass-clear\n");detach(true);
    evt_console_poll(&cal);assert(erase_count==0&&queued_size==0);connect_at(200);assert(erase_count==0);

    reset(false);connect_at(0);enqueue("compass-clear\n");detach_in_read=true;
    evt_console_poll(&cal);assert(!pads&&erase_count==0&&commit_count==0);connect_at(200);
    enqueue("status\n");evt_console_poll(&cal);assert(status_count==1&&install_count==1);

    reset(true);install_fails=true;
    assert(evt_console_transport_tick(100)==ESP_FAIL&&pads&&install_count==1);
    for(unsigned i=0;i<20;++i)assert(evt_console_transport_tick(101+i)==ESP_OK);
    detach(true);assert(!pads);assert(evt_console_transport_tick(200)==ESP_OK);
    assert(evt_console_transport_tick(300)==ESP_OK&&pads&&install_count==1);
    enqueue("compass-clear\n");evt_console_poll(&cal);assert(erase_count==0&&read_count==0);

    reset(true);detach_in_install=true;redock_in_install=true;
    assert(evt_console_transport_tick(100)==ESP_OK&&!pads&&install_count==1);
    detach_in_install=false;connect_at(200);assert(install_count==1);

    reset(true);install_fails=true;detach_in_install=true;
    assert(evt_console_transport_tick(100)==ESP_FAIL&&!pads&&install_count==1);
    assert(evt_console_transport_tick(200)==ESP_OK&&!pads&&install_count==1);
    detach_in_install=false;connect_at(300);assert(install_count==1&&read_count==0);

    reset(true);memcpy(fifo,"status\n",7);fifo_size=7;enqueue("compass-clear\n");
    assert(evt_console_transport_tick(100)==ESP_OK&&pads&&fifo_size==0&&queued_size==0);
    evt_console_poll(&cal);assert(erase_count==0&&status_count==0);
    enqueue("status\n");assert(evt_console_transport_tick(200)==ESP_OK);
    evt_console_poll(&cal);assert(status_count==1); /* Preserve healthy-session RX. */

    reset(false);connect_at(0);enqueue("compass-cl");evt_console_poll(&cal);enqueue("ear\n");
    memcpy(fifo,"status\n",7);fifo_size=7;evt_console_disconnect();
    assert(!pads&&queued_size==0&&fifo_size==0);connect_at(200);enqueue("ear\n");evt_console_poll(&cal);assert(!erase_count);
    shutdown_handler();assert(!pads&&!rx_irq);

    reset(false);connect_at(0);detach_in_nvs=true;enqueue("compass-clear\n");evt_console_poll(&cal);
    assert(!pads&&erase_count==0&&commit_count==0);

    service_error=ESP_FAIL;pads=true;assert(evt_console_transport_init(0)==ESP_FAIL&&!pads);
    puts("EVT1 console/PHY boundary: startup,100ms bounce,detach/reconnect,staleRX,partialcommand,installfailure/installrace,sleep/shutdown andNVS-entry detach pass.");
    return 0;
}
