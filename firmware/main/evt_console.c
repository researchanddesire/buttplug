#ifdef BOARD_EVT1
#include "evt_console.h"
#include "r0_app.h"
#include <stdio.h>
#include <string.h>
#include "cJSON.h"
#include "driver/gpio.h"
#include "driver/usb_serial_jtag.h"
#include "esp_attr.h"
#include "esp_idf_version.h"
#include "esp_intr_alloc.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "hal/usb_serial_jtag_ll.h"
#include "nvs.h"
#include "sdkconfig.h"

#if !CONFIG_IDF_TARGET_ESP32C3 || ESP_IDF_VERSION != ESP_IDF_VERSION_VAL(5, 5, 3)
#error "EVT1 USB pad policy requires the audited ESP32-C3 ESP-IDF 5.5.3 LL"
#endif

/* Software attach debounce only; not a measured connector qualification. */
#define DOCK_QUALIFY_MS 100U
#define RX_BUFFER_SIZE 1024U
static portMUX_TYPE usb_lock = portMUX_INITIALIZER_UNLOCKED;
static volatile uint32_t detach_generation;
static uint32_t observed_generation;
static bool qualifying;
static uint64_t dock_low_since;
static bool install_attempted;
static bool session_attached;

static char line[1024];
static size_t used;
static bool overflow;
static bool receiver_ready;

static void IRAM_ATTR pad_off_locked(void) {
    usb_serial_jtag_ll_phy_enable_pad(false);
    usb_serial_jtag_ll_disable_intr_mask(USB_SERIAL_JTAG_INTR_SERIAL_OUT_RECV_PKT);
}
static void pad_off(void) {
    portENTER_CRITICAL(&usb_lock);
    pad_off_locked();
    portEXIT_CRITICAL(&usb_lock);
}
static void IRAM_ATTR dock_detached(void *arg) {
    (void)arg;
    portENTER_CRITICAL_ISR(&usb_lock);
    /* This must precede bookkeeping and never wait for the application loop. */
    pad_off_locked();
    ++detach_generation;
    portEXIT_CRITICAL_ISR(&usb_lock);
}
static void clear_receiver(void) {
    used = 0;
    overflow = false;
    uint8_t discard[128];
    /* Pads/RX interrupt are already off. Remove peripheral bytes before the
     * ring buffer, so a pending old packet cannot appear in a later session. */
    portENTER_CRITICAL(&usb_lock);
    (void)usb_serial_jtag_ll_read_rxfifo(discard, sizeof(discard));
    usb_serial_jtag_ll_clr_intsts_mask(USB_SERIAL_JTAG_INTR_SERIAL_OUT_RECV_PKT);
    portEXIT_CRITICAL(&usb_lock);
    if (receiver_ready) {
        for (unsigned i = 0; i <= RX_BUFFER_SIZE / sizeof(discard); ++i)
            if (usb_serial_jtag_read_bytes(discard, sizeof(discard), 0) <= 0) break;
    }
}
void evt_console_disconnect(void) {
    pad_off();
    session_attached = false;
    qualifying = false;
    clear_receiver();
}
uint32_t evt_console_source_snapshot(bool *present) {
    portENTER_CRITICAL(&usb_lock);
    uint32_t generation = detach_generation;
    *present = gpio_get_level(CONFIG_R0_PIN_DOCK_N) == 0;
    portEXIT_CRITICAL(&usb_lock);
    return generation;
}
static bool session_valid(void) {
    portENTER_CRITICAL(&usb_lock);
    bool valid = session_attached && detach_generation == observed_generation &&
                 gpio_get_level(CONFIG_R0_PIN_DOCK_N) == 0;
    if (!valid) pad_off_locked();
    portEXIT_CRITICAL(&usb_lock);
    if (!valid) {
        session_attached = false;
        qualifying = false;
        clear_receiver();
    }
    return valid;
}
esp_err_t evt_console_transport_init(uint64_t now_ms) {
    pad_off();
    used = 0; overflow = false;
    install_attempted = false; receiver_ready = false; session_attached = false;
    detach_generation = 0; observed_generation = 0;
    qualifying = false;
    esp_err_t err = gpio_install_isr_service(ESP_INTR_FLAG_IRAM);
    if (err != ESP_OK) return err;
    if ((err = gpio_set_intr_type(CONFIG_R0_PIN_DOCK_N, GPIO_INTR_POSEDGE)) != ESP_OK)
        return err;
    if ((err = gpio_isr_handler_add(CONFIG_R0_PIN_DOCK_N, dock_detached, NULL)) != ESP_OK)
        return err;
    if ((err = esp_register_shutdown_handler(pad_off)) != ESP_OK) return err;
    portENTER_CRITICAL(&usb_lock);
    observed_generation = detach_generation;
    qualifying = gpio_get_level(CONFIG_R0_PIN_DOCK_N) == 0;
    dock_low_since = now_ms;
    portEXIT_CRITICAL(&usb_lock);
    clear_receiver();
    return ESP_OK;
}
esp_err_t evt_console_transport_tick(uint64_t now_ms) {
    portENTER_CRITICAL(&usb_lock);
    uint32_t generation = detach_generation;
    bool present = gpio_get_level(CONFIG_R0_PIN_DOCK_N) == 0;
    if (!present || generation != observed_generation) pad_off_locked();
    portEXIT_CRITICAL(&usb_lock);
    if (!present || generation != observed_generation) {
        observed_generation = generation;
        evt_console_disconnect();
    }
    if (!present) return ESP_OK;
    if (!qualifying) { qualifying = true; dock_low_since = now_ms; }
    if (now_ms - dock_low_since < DOCK_QUALIFY_MS) return ESP_OK;

    esp_err_t err = ESP_OK;
    if (!install_attempted) {
        install_attempted = true;
        usb_serial_jtag_driver_config_t config = {
            .rx_buffer_size = RX_BUFFER_SIZE, .tx_buffer_size = 2048};
        err = usb_serial_jtag_driver_install(&config);
        /* The helper enables pads, even on a subsequently failed install.
         * Always close that window before rechecking physical presence. */
        pad_off();
        receiver_ready = err == ESP_OK;
    }
    if (!session_attached) clear_receiver();
    portENTER_CRITICAL(&usb_lock);
    present = gpio_get_level(CONFIG_R0_PIN_DOCK_N) == 0 &&
              detach_generation == observed_generation;
    if (present) {
        if (receiver_ready)
            usb_serial_jtag_ll_ena_intr_mask(USB_SERIAL_JTAG_INTR_SERIAL_OUT_RECV_PKT);
        usb_serial_jtag_ll_phy_enable_pad(true);
    } else pad_off_locked();
    session_attached = present;
    portEXIT_CRITICAL(&usb_lock);
    if (!present) evt_console_disconnect();
    /* Keep stdout on its nonblocking console path and retain its bus clock.
     * Even if RX install failed, qualified docking permits native USB recovery. */
    return err;
}

void evt_console_load_calibration(evt_compass_cal_t *cal) {
    memset(cal, 0, sizeof(*cal));
    nvs_handle_t handle;
    if (nvs_open("evt1", NVS_READONLY, &handle) == ESP_OK) {
        size_t length = sizeof(*cal);
        esp_err_t err = nvs_get_blob(handle, "compass", cal, &length);
        nvs_close(handle);
        if (err != ESP_OK || length != sizeof(*cal) || !evt_compass_cal_valid(cal))
            memset(cal, 0, sizeof(*cal));
    }
}
static bool array(cJSON *root, const char *name, float *out, unsigned count) {
    cJSON *value = cJSON_GetObjectItemCaseSensitive(root, name);
    if (!cJSON_IsArray(value) || cJSON_GetArraySize(value) != (int)count) return false;
    for (unsigned i = 0; i < count; i++) {
        cJSON *item = cJSON_GetArrayItem(value, (int)i);
        if (!cJSON_IsNumber(item)) return false;
        out[i] = (float)item->valuedouble;
    }
    return true;
}
static esp_err_t store(const evt_compass_cal_t *cal, bool erase) {
    if (!session_valid()) return ESP_ERR_INVALID_STATE;
    nvs_handle_t handle;
    esp_err_t err = nvs_open("evt1", NVS_READWRITE, &handle);
    if (err != ESP_OK) return err;
    if (!session_valid()) { nvs_close(handle); return ESP_ERR_INVALID_STATE; }
    err = erase ? nvs_erase_key(handle, "compass") : nvs_set_blob(handle, "compass", cal, sizeof(*cal));
    if (erase && err == ESP_ERR_NVS_NOT_FOUND) err = ESP_OK;
    if (err == ESP_OK) err = session_valid() ? nvs_commit(handle) : ESP_ERR_INVALID_STATE;
    nvs_close(handle);
    return err;
}
static void command(evt_compass_cal_t *cal) {
    if (!session_valid()) return;
    if (!strcmp(line, "status")) {
        char json[R0_STATUS_JSON_CAPACITY];
        r0_status_json(json, sizeof(json));
        printf("%s\n", json);
    } else if (!strcmp(line, "thermal-status")) {
        char json[R0_THERMAL_JSON_CAPACITY];
        if (r0_thermal_status_json(json, sizeof(json))) printf("%s\n", json);
    } else if (!strcmp(line, "help")) {
        puts("EVT1 USB: status | thermal-status | compass-cal {version,accel_to_flange[9],mag_to_flange[9],mag_offset_ut[3],arrow[3]} | compass-clear");
    } else if (!strcmp(line, "compass-clear")) {
        esp_err_t err = store(cal, true);
        if (err == ESP_OK) memset(cal, 0, sizeof(*cal));
        printf("EVT1 compass-clear: %s\n", esp_err_to_name(err));
    } else if (!strncmp(line, "compass-cal ", 12)) {
        evt_compass_cal_t proposed = {0};
        const char *end = NULL;
        cJSON *root = cJSON_ParseWithOpts(line + 12, &end, true);
        cJSON *version = root ? cJSON_GetObjectItemCaseSensitive(root, "version") : NULL;
        bool ok = cJSON_IsObject(root) && cJSON_IsNumber(version) && version->valuedouble == 1 &&
                  array(root, "accel_to_flange", proposed.accel_to_flange, 9) &&
                  array(root, "mag_to_flange", proposed.mag_to_flange, 9) &&
                  array(root, "mag_offset_ut", proposed.mag_offset_ut, 3) &&
                  array(root, "arrow", proposed.arrow, 3);
        proposed.version = 1;
        cJSON_Delete(root);
        if (!ok || !evt_compass_cal_valid(&proposed)) { puts("EVT1 error: invalid factory calibration"); return; }
        esp_err_t err = store(&proposed, false);
        if (err == ESP_OK) *cal = proposed;
        printf("EVT1 compass-cal: %s\n", esp_err_to_name(err));
    } else if (used) {
        puts("EVT1 error: unknown USB command; use help");
    }
}
void evt_console_poll(evt_compass_cal_t *cal) {
    if (!session_attached) return; /* Do not restart an in-progress qualification. */
    if (!session_valid() || !receiver_ready) return;
    char input[128];
    int length = usb_serial_jtag_read_bytes(input, sizeof(input), 0);
    for (int i = 0; i < length; i++) {
        if (!session_valid()) return; /* Discard the entire old-session buffer. */
        unsigned char c = (unsigned char)input[i];
        if (c == '\n' || c == '\r') {
            if (overflow) puts("EVT1 error: USB command too long");
            else { line[used] = 0; command(cal); }
            used = 0; overflow = false;
        } else if (c < 32 || c > 126) {
            overflow = true; /* Never execute a suffix after invalid input. */
        } else if (!overflow) {
            if (used + 1 >= sizeof(line)) overflow = true;
            else line[used++] = (char)c;
        }
    }
}
#endif
