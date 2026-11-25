#include <inttypes.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sdkconfig.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "driver/gpio.h"
#include "driver/ledc.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_sleep.h"
#include "esp_timer.h"
#include "esp_task_wdt.h"
#include "nvs_flash.h"
#include "r0_app.h"
#include "r0_sensors.h"
#ifdef BOARD_EVT1
#include "evt_console.h"
#include "evt_case_radio.h"
#include "compass_control.h"
#include "plug_runtime.h"
#include "thermal_history.h"
_Static_assert(R0_THERMAL_JSON_CAPACITY >= THERMAL_STATUS_JSON_CAPACITY, "thermal snapshot buffer too small");
#include "esp_random.h"
#ifdef BOARD_EVT1_ONE_BOARD
#define HARDWARE_PROFILE "evt1-one-board"
#else
#define HARDWARE_PROFILE "evt1"
#endif
static evt_compass_cal_t compass_cal;
static int heading_mdeg;
static bool heading_valid;
static uint64_t magnetic_settle_until;
static compass_control_t compass;
static const char *heading_status = "uncalibrated";
static char compass_json[512] = "{\"booting\":true}";
static plug_wear_t wear;
static uint32_t wear_boot_id;
static char wear_json[256] = "{\"booting\":true}";
static thermal_history_t thermal;
static uint32_t temperature_loss_sequence_at_start;
static ct_runtime_t case_runtime;
static ct_charge_t case_charge;
static char thermal_json[R0_THERMAL_JSON_CAPACITY] = "{\"booting\":true}";
#else
#define HARDWARE_PROFILE "prototype-r0"
#endif

static const char *TAG = "r0";
static QueueHandle_t commands;
static SemaphoreHandle_t status_lock;
static char status_json[R0_STATUS_JSON_CAPACITY] = "{\"booting\":true}";
static r0_control_t control;
static r0_sample_t sample;
static uint64_t sample_ms;
static bool pwm_ready;
static atomic_bool stop_requested;
uint64_t r0_now_ms(void) { return (uint64_t)esp_timer_get_time() / 1000; }
#ifdef BOARD_EVT1
bool r0_case_connected(uint32_t connection) {
    if(!status_lock)return false;
    xSemaphoreTake(status_lock,portMAX_DELAY);bool ok=ct_runtime_open(&case_runtime,connection);
    xSemaphoreGive(status_lock);return ok;
}
void r0_case_disconnected(uint32_t connection) {
    if(!status_lock)return;
    xSemaphoreTake(status_lock,portMAX_DELAY);ct_runtime_close(&case_runtime,connection);xSemaphoreGive(status_lock);
}
bool r0_case_read(uint32_t connection,uint8_t kind,uint8_t out[CT_WIRE_BYTES]) {
    if(!status_lock)return false;
    xSemaphoreTake(status_lock,portMAX_DELAY);bool ok=ct_runtime_read(&case_runtime,connection,kind,out);
    xSemaphoreGive(status_lock);return ok;
}
bool r0_case_command(uint32_t connection,const uint8_t data[CT_WIRE_BYTES],uint64_t rx) {
    if(!status_lock)return false;
    xSemaphoreTake(status_lock,portMAX_DELAY);bool ok=ct_runtime_enqueue(&case_runtime,connection,data,rx);
    xSemaphoreGive(status_lock);return ok;
}
bool r0_case_next(uint32_t connection,uint8_t subscribed,uint64_t now,ct_transmission_t *tx) {
    if(!status_lock)return false;
    xSemaphoreTake(status_lock,portMAX_DELAY);bool ok=ct_runtime_peek(&case_runtime,connection,subscribed,now,tx);
    xSemaphoreGive(status_lock);return ok;
}
void r0_case_sent(uint32_t connection,const ct_transmission_t *tx) {
    if(!status_lock)return;
    xSemaphoreTake(status_lock,portMAX_DELAY);ct_runtime_sent(&case_runtime,connection,tx);xSemaphoreGive(status_lock);
}
#endif
bool r0_enqueue(uint8_t opcode, uint8_t value) {
    compass_command_t command = {.opcode = opcode, .value = value};
    return r0_enqueue_compass(&command);
}
bool r0_enqueue_compass(const compass_command_t *command) {
    uint8_t opcode = command->opcode;
    if (opcode == R0_CMD_STOP || opcode == R0_CMD_LINK_LOST) {
        atomic_store(&stop_requested, true);
        return true;
    }
    r0_command_t cmd = {.opcode = opcode, .value = command->value,
        .target_deg = command->target_deg, .tolerance_deg = command->tolerance_deg,
        .sent_ms = r0_now_ms()};
    return commands && xQueueSend(commands, &cmd, 0) == pdTRUE;
}
size_t r0_compass_status_json(char *buffer, size_t size) {
#ifdef BOARD_EVT1
    if (!status_lock || !size) return 0;
    xSemaphoreTake(status_lock, portMAX_DELAY);
    size_t n = (size_t)snprintf(buffer, size, "%s", compass_json);
    xSemaphoreGive(status_lock);
    return n < size ? n : size - 1;
#else
    return r0_status_json(buffer, size);
#endif
}
size_t r0_status_json(char *buffer, size_t size) {
    if (!status_lock || !size) return 0;
    xSemaphoreTake(status_lock, portMAX_DELAY);
    size_t n = (size_t)snprintf(buffer, size, "%s", status_json);
    xSemaphoreGive(status_lock);
    return n < size ? n : size - 1;
}
static void motor_off(void) {
    gpio_set_level(CONFIG_R0_PIN_ARM, 0);
    if (pwm_ready) ledc_stop(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, 0);
    gpio_set_level(CONFIG_R0_PIN_PWM, 0);
}
size_t r0_wear_status_json(char *buffer, size_t size) {
#ifdef BOARD_EVT1
    if (!status_lock || !size) return 0;
    xSemaphoreTake(status_lock, portMAX_DELAY);
    size_t n = (size_t)snprintf(buffer, size, "%s", wear_json);
    xSemaphoreGive(status_lock);
    return n < size ? n : size - 1;
#else
    (void)buffer; (void)size; return 0;
#endif
}
size_t r0_thermal_status_json(char *buffer, size_t size) {
#ifdef BOARD_EVT1
    if (!status_lock || !size) return 0;
    xSemaphoreTake(status_lock, portMAX_DELAY);
    int n = snprintf(buffer, size, "%s", thermal_json);
    xSemaphoreGive(status_lock);
    if (n < 0 || (size_t)n >= size) { buffer[0] = 0; return 0; }
    return (size_t)n;
#else
    (void)buffer; (void)size; return 0;
#endif
}
static esp_err_t outputs_init(void) {
    gpio_set_level(CONFIG_R0_PIN_ARM, 0);
    gpio_set_level(CONFIG_R0_PIN_PWM, 0);
    gpio_config_t out = {.pin_bit_mask = (1ULL << CONFIG_R0_PIN_PWM) | (1ULL << CONFIG_R0_PIN_ARM),
                        .mode = GPIO_MODE_OUTPUT};
    esp_err_t err = gpio_config(&out);
    if (err != ESP_OK) return err;
    motor_off();
    ledc_timer_config_t timer = {.speed_mode = LEDC_LOW_SPEED_MODE, .duty_resolution = LEDC_TIMER_8_BIT,
        .timer_num = LEDC_TIMER_0, .freq_hz = 20000, .clk_cfg = LEDC_AUTO_CLK};
    if ((err = ledc_timer_config(&timer)) != ESP_OK) return err;
    ledc_channel_config_t channel = {.gpio_num = CONFIG_R0_PIN_PWM, .speed_mode = LEDC_LOW_SPEED_MODE,
        .channel = LEDC_CHANNEL_0, .timer_sel = LEDC_TIMER_0, .duty = 0, .hpoint = 0};
    if ((err = ledc_channel_config(&channel)) != ESP_OK) return err;
    pwm_ready = true;
    return esp_register_shutdown_handler(motor_off);
}
static void motor_apply(void) {
    gpio_set_level(CONFIG_R0_PIN_ARM, 0);
    uint32_t duty = control.output_percent * 255U / 100U;
    if (!duty) { motor_off(); return; }
    if (ledc_set_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0, duty) != ESP_OK ||
        ledc_update_duty(LEDC_LOW_SPEED_MODE, LEDC_CHANNEL_0) != ESP_OK) {
        motor_off();
        control.faults |= R0_FAULT_HARDWARE;
        r0_stop(&control);
        return;
    }
    /* Physical AND gate also rejects docked state; do not rely on this read alone. */
    if (gpio_get_level(CONFIG_R0_PIN_DOCK_N) != 0)
        gpio_set_level(CONFIG_R0_PIN_ARM, 1);
}
typedef struct { bool stable; bool raw; uint64_t changed_ms; uint64_t pressed_ms; } button_t;
static bool button_release(button_t *b, int pin, uint64_t now, uint64_t *held) {
    bool pressed = gpio_get_level(pin) == 0;
    if (pressed != b->raw) { b->raw = pressed; b->changed_ms = now; }
    if (pressed == b->stable || now - b->changed_ms < 40) return false;
    b->stable = pressed;
    if (pressed) {
        b->pressed_ms = now;
        if (pin == CONFIG_R0_PIN_POWER_N) { r0_stop(&control); motor_off(); }
        return false;
    }
    *held = now - b->pressed_ms;
    return true;
}
#ifdef BOARD_EVT1
static void observe_thermal_source(uint64_t now) {
    bool present;
    uint32_t generation = evt_console_source_snapshot(&present);
    /* Brief losses that reconnect between polls still invalidate the old
     * connection. Multiple ISR edges may coalesce into one observed event;
     * expose the raw count and never invent their individual timestamps. */
    thermal_history_source_snapshot(&thermal, present, generation, now);
}
static void update_heading(uint64_t now) {
    heading_valid = false;
    if (control.inputs.docked) heading_status = "docked";
    else if (!evt_compass_cal_valid(&compass_cal)) heading_status = "uncalibrated";
    else if (control.output_percent) heading_status = "motor";
    else if (now < magnetic_settle_until || sample_ms <= magnetic_settle_until)
        heading_status = "settling";
    else if (!sample.accel_valid || !sample.mag_valid || now < sample_ms ||
             now - sample_ms > COMPASS_SAMPLE_MAX_AGE_MS) heading_status = "stale";
    else {
        float acceleration[3], magnetic_field[3];
        for (unsigned i = 0; i < 3; i++) {
            acceleration[i] = sample.accel[i] * .98f;
            magnetic_field[i] = sample.mag[i] * .15f;
        }
        heading_valid = evt_heading(acceleration, magnetic_field, &compass_cal,
            false, false, &heading_mdeg);
        heading_status = heading_valid ? "ready" : "disturbed";
    }
}
static void publish_compass(uint64_t now) {
    if (!thermal_history_json(&thermal, now, thermal_json, sizeof(thermal_json)))
        snprintf(thermal_json, sizeof(thermal_json), "{\"error\":\"status_overflow\"}");
    snprintf(wear_json, sizeof(wear_json),
        "{\"protocol\":\"plug-v1\",\"boot_id\":%" PRIu32 ",\"session_id\":%" PRIu32
        ",\"active\":%s,\"state\":\"%s\",\"elapsed_ms\":%" PRIu64
        ",\"confirmed_wear_ms\":%" PRIu64 ",\"detector_qualified\":false}",
        wear_boot_id, wear.session_id, wear.active ? "true" : "false",
        plug_wear_state_name(wear.state), wear.elapsed_ms, wear.confirmed_ms);
    char bearing[16] = "null", temperature[16] = "null", battery[16] = "null";
    /* The factory arrow points BACK. Rad shows the opposite, facing direction. */
    if (heading_valid) snprintf(bearing, sizeof(bearing), "%d", (heading_mdeg + 180000) % 360000);
    if (sample.temperature_valid) snprintf(temperature, sizeof(temperature), "%d", sample.temperature_millic);
    if (sample.battery_valid) snprintf(battery, sizeof(battery), "%d", sample.battery_mv);
    uint64_t remaining = compass.active && now < compass.lease_until_ms ? compass.lease_until_ms - now : 0;
    int n = snprintf(compass_json, sizeof(compass_json),
        "{\"protocol\":\"compass-v1\",\"uptime_ms\":%" PRIu64 ",\"armed\":%s,\"limits_ready\":%s,"
        "\"docked\":%s,\"faults\":%" PRIu32 ",\"duty_percent\":%u,\"max_duty_percent\":%u,"
        "\"heading_mdeg\":%s,\"heading_status\":\"%s\",\"temperature_millic\":%s,\"battery_mv\":%s,"
        "\"mode\":\"%s\",\"target_deg\":%u,\"tolerance_deg\":%u,\"strength_percent\":%u,"
        "\"phase\":\"%s\",\"lease_remaining_ms\":%" PRIu64 "}",
        now, control.armed ? "true" : "false", r0_limits_ready(&control) ? "true" : "false",
        control.inputs.docked ? "true" : "false", control.faults,
        control.output_percent, control.limits.max_duty_percent,
        bearing, heading_status, temperature, battery,
        compass.active ? "direction" : control.requested_percent ? "manual" : "idle",
        compass.target_deg, compass.tolerance_deg, compass.strength_percent,
        compass_phase_name(compass.phase), remaining);
    if (n < 0 || (size_t)n >= sizeof(compass_json))
        snprintf(compass_json, sizeof(compass_json), "{\"error\":\"status_overflow\"}");
}
#endif
static void publish(uint64_t now) {
    xSemaphoreTake(status_lock, portMAX_DELAY);
#ifdef BOARD_EVT1_ONE_BOARD
    char pack_temperature[16] = "null";
    if (sample.pack_temperature_valid && now >= sample.pack_temperature_sampled_ms &&
        now - sample.pack_temperature_sampled_ms <= 1500)
        snprintf(pack_temperature, sizeof(pack_temperature), "%d", sample.pack_temperature_millic);
#endif
    snprintf(status_json, sizeof(status_json),
        "{\"protocol\":\"r0\",\"hardware\":\"" HARDWARE_PROFILE "\",\"uptime_ms\":%" PRIu64 ",\"armed\":%s,\"faults\":%" PRIu32
        ",\"docked\":%s,\"limits_ready\":%s,\"duty_percent\":%u,\"temperature_millic\":%d,"
        "\"battery_mv\":%d,\"sensor_age_ms\":%" PRIu64 ",\"sensor_valid\":%s,"
        "\"accel_raw\":[%d,%d,%d],\"adc_calibrated\":%s,\"wifi\":%s"
#ifdef BOARD_EVT1
        ",\"sample_uptime_ms\":%" PRIu64 ",\"accel_valid\":%s,\"mag_raw\":[%d,%d,%d],\"mag_valid\":%s,\"compass_calibrated\":%s,"
        "\"heading_valid\":%s,\"heading_mdeg\":%d"
#ifdef BOARD_EVT1_ONE_BOARD
        ",\"pack_temperature_millic\":%s,\"pack_temperature_sampled_ms\":%" PRIu64
#endif
#else
        ",\"accel_int_n\":%d"
#endif
        "}",
        now, control.armed ? "true" : "false", control.faults,
        control.inputs.docked ? "true" : "false", r0_limits_ready(&control) ? "true" : "false",
        control.output_percent, sample.temperature_millic, sample.battery_mv, now - sample_ms,
        control.inputs.sensors_valid ? "true" : "false", sample.accel[0], sample.accel[1], sample.accel[2],
        sample.adc_calibrated ? "true" : "false", r0_wifi_active() ? "true" : "false"
#ifdef BOARD_EVT1
        , sample_ms, sample.accel_valid ? "true" : "false", sample.mag[0], sample.mag[1], sample.mag[2],
        sample.mag_valid ? "true" : "false",
        evt_compass_cal_valid(&compass_cal) ? "true" : "false",
        heading_valid ? "true" : "false", heading_valid ? heading_mdeg : 0
#ifdef BOARD_EVT1_ONE_BOARD
        , pack_temperature, sample.pack_temperature_sampled_ms
#endif
#else
        , gpio_get_level(CONFIG_R0_PIN_ACCEL_INT_N)
#endif
        );
#ifdef BOARD_EVT1
    publish_compass(now);
    ct_runtime_update(&case_runtime,&thermal,&case_charge,r0_now_ms);
#endif
    xSemaphoreGive(status_lock);
}
void app_main(void) {
    /* First peripheral actions force both motor requests low. Hardware pulldowns cover ROM/reset. */
    ESP_ERROR_CHECK(outputs_init());
    commands = xQueueCreate(8, sizeof(r0_command_t));
    status_lock = xSemaphoreCreateMutex();
    if (!commands || !status_lock) { motor_off(); abort(); }
    const r0_limits_t limits = {
#ifdef CONFIG_R0_MOTOR_BENCH_ENABLE
        .motor_enabled = true,
#else
        .motor_enabled = false,
#endif
        .max_duty_percent = CONFIG_R0_MAX_DUTY_PERCENT,
        .temperature_trip_millic = CONFIG_R0_TEMPERATURE_TRIP_MILLIC,
        .battery_min_mv = CONFIG_R0_BATTERY_MIN_MV, .lease_ms = 3000,
        .arm_window_ms = 60000, .sensor_stale_ms = 2500,
    };
    r0_control_init(&control, limits);
    gpio_config_t inputs = {.pin_bit_mask = (1ULL << CONFIG_R0_PIN_POWER_N) |
        (1ULL << CONFIG_R0_PIN_MODE_N) | (1ULL << CONFIG_R0_PIN_DOCK_N)
#ifndef BOARD_EVT1
        | (1ULL << CONFIG_R0_PIN_ACCEL_INT_N)
#endif
        , .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE};
    ESP_ERROR_CHECK(gpio_config(&inputs));
#ifdef BOARD_EVT1
    /* Gate exposed USB pads before NVS/calibration/driver initialization. */
    ESP_ERROR_CHECK(evt_console_transport_init(r0_now_ms()));
#endif
    esp_err_t err = nvs_flash_init();
    if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        err = nvs_flash_init();
    }
    ESP_ERROR_CHECK(err);
#ifdef BOARD_EVT1
    compass_init(&compass);
    thermal_history_init(&thermal, 0);
    ct_runtime_init(&case_runtime);
    observe_thermal_source(r0_now_ms());
    evt_console_load_calibration(&compass_cal);
#endif
    err = r0_sensors_init();
    if (err != ESP_OK) ESP_LOGE(TAG, "Sensor initialization failed: %s; reboot after fixing hardware", esp_err_to_name(err));
    ESP_ERROR_CHECK(r0_radio_init());
#ifdef BOARD_EVT1
    /* nimble_port_init enables BT entropy; this profile disables modem sleep.
     * Assign before the first published status, rather than sampling the
     * pseudo-random startup stream. A32-bit tag is not globally unique. */
    wear_boot_id = esp_random();
    thermal.boot_id = wear_boot_id;
#endif
    esp_task_wdt_config_t wdt = {.timeout_ms = 2000, .idle_core_mask = 1, .trigger_panic = true};
    err = esp_task_wdt_reconfigure(&wdt);
    if (err == ESP_ERR_INVALID_STATE) err = esp_task_wdt_init(&wdt);
    ESP_ERROR_CHECK(err);
    ESP_ERROR_CHECK(esp_task_wdt_add(NULL));
    button_t power = {0}, mode = {0};
    bool power_ready = gpio_get_level(CONFIG_R0_PIN_POWER_N) != 0;
    unsigned mode_index = 0;
    const uint8_t duties[] = {0, 10, 20, 25};
    uint64_t next_sample = 0, next_log = 0, wifi_until = 0;
    ESP_LOGW(TAG, "Hardware %s. Motor default disabled; local arm required. No physical validation.", HARDWARE_PROFILE);
    for (;;) {
        uint64_t now = r0_now_ms();
#ifdef BOARD_EVT1
        err = evt_console_transport_tick(now);
        if (err != ESP_OK) ESP_LOGE(TAG, "USB command receiver: %s", esp_err_to_name(err));
        observe_thermal_source(now);
#endif
        if (now >= next_sample) {
#ifdef BOARD_EVT1
            uint32_t tip_before = sample.temperature_sequence;
            uint32_t loss_before = thermal.event_sequence;
            bool charge_source_before;
            uint32_t charge_edges_before = evt_console_source_snapshot(&charge_source_before);
#endif
            r0_sensors_sample(&sample);
            now = r0_now_ms();
            sample_ms = now;
#ifdef BOARD_EVT1
            if (sample.temperature_sequence != tip_before) temperature_loss_sequence_at_start = loss_before;
            bool charge_source_after;
            uint32_t charge_edges_after = evt_console_source_snapshot(&charge_source_after);
            ++case_charge.sequence;
            case_charge.acquired = true;
            case_charge.completed_ms = sample_ms;
            /* The original-body profile observes only PGOOD and calibrated VBAT. */
            case_charge.validity = CT_MEASUREMENT_GAP;
            case_charge.raw_status = 0;
            case_charge.current_0p1_ma = case_charge.ts_mv = case_charge.vbat_mv = UINT16_MAX;
            if (charge_source_before == charge_source_after && charge_edges_before == charge_edges_after) {
                case_charge.validity |= CT_PGOOD_VALID;
                if (charge_source_after) case_charge.raw_status |= 4u;
            }
            if (sample.battery_valid && sample.battery_mv >= 0 && sample.battery_mv < UINT16_MAX) {
                case_charge.validity |= CT_VBAT_VALID;
                case_charge.vbat_mv = (uint16_t)sample.battery_mv;
            }
            next_sample = now + 100; /* Motion10Hz; driver pulses NTC only1Hz. */
#else
            next_sample = now + CONFIG_R0_SAMPLE_PERIOD_MS;
#endif
        }
        r0_inputs_t in = {.docked = gpio_get_level(CONFIG_R0_PIN_DOCK_N) == 0,
            .sensors_valid = sample.temperature_valid && sample.battery_valid && sample.accel_valid,
            .sampled_ms = sample_ms, .temperature_millic = sample.temperature_millic,
            .battery_mv = sample.battery_mv};
#ifdef BOARD_EVT1
        observe_thermal_source(now);
        if (sample.temperature_sequence)
            thermal_history_sample(&thermal, (thermal_sample_t){
                .sequence = sample.temperature_sequence,
                .started_ms = sample.temperature_started_ms,
                .sampled_ms = sample.temperature_sampled_ms,
                .loss_sequence_at_start = temperature_loss_sequence_at_start,
                .tip_millic = sample.temperature_millic,
                .valid = sample.temperature_valid,
                .source_at_start = sample.temperature_source_at_start,
                .source_changed = sample.temperature_source_changed,
                .source_at_end = sample.temperature_source_at_end}, now);
#endif
        r0_control_tick(&control, in, now);
        uint64_t held;
#ifdef BOARD_EVT1
        /* Dock presence also pulls GPIO1 low for deep-sleep wake. Discard its
         * entire gesture, including undock release; never sleep while docked.
         */
        if (in.docked) { power_ready = false; power = (button_t){0}; }
        else
#endif
        if (!power_ready && gpio_get_level(CONFIG_R0_PIN_POWER_N) != 0) {
            power_ready = true; power = (button_t){0};
        }
        if (power_ready && button_release(&power, CONFIG_R0_PIN_POWER_N, now, &held)) {
            if (held >= 3000) ESP_LOGI(TAG, "Fault clear: %s", r0_local_clear(&control, now) ? "accepted; disarmed" : "rejected");
            else if (held >= 1000) {
                r0_stop(&control); motor_off();
#ifdef BOARD_EVT1
                evt_console_disconnect();
#endif
                ESP_ERROR_CHECK(esp_deep_sleep_enable_gpio_wakeup(1ULL << CONFIG_R0_PIN_POWER_N, ESP_GPIO_WAKEUP_GPIO_LOW));
                ESP_LOGI(TAG, "Software off: deep sleep; press power to wake. Battery remains connected.");
                ESP_ERROR_CHECK(esp_task_wdt_delete(NULL));
                if (r0_wifi_active()) r0_wifi_session(false);
                r0_sensors_sleep();
                esp_deep_sleep_start();
            }
        }
        if (button_release(&mode, CONFIG_R0_PIN_MODE_N, now, &held)) {
            if (held >= 3000) {
                r0_stop(&control); motor_off();
                bool on = !r0_wifi_active();
                if (r0_wifi_session(on) == ESP_OK) wifi_until = on ? now + 300000 : 0;
            } else if (held >= 1000) {
#ifdef BOARD_EVT1
                compass_stop(&compass);
#endif
                ESP_LOGI(TAG, "Local arm: %s", r0_local_arm(&control, now) ? "accepted (60s)" : "rejected");
            } else {
#ifdef BOARD_EVT1
                compass_stop(&compass);
#endif
                mode_index = (mode_index + 1) % (sizeof(duties)/sizeof(duties[0]));
                bool accepted = r0_request_motor(&control, duties[mode_index], now);
                ESP_LOGI(TAG, "Local mode %u%%: %s (3s lease)", duties[mode_index], accepted ? "accepted" : "rejected");
            }
        }
        bool priority_stop = atomic_exchange(&stop_requested, false);
        if (priority_stop) {
            r0_stop(&control);
#ifdef BOARD_EVT1
            compass_stop(&compass);
#endif
        }
        r0_command_t cmd;
        while (xQueueReceive(commands, &cmd, 0) == pdTRUE) {
            if (priority_stop) continue;
            if (cmd.opcode == R0_CMD_STOP || cmd.opcode == R0_CMD_LINK_LOST) r0_stop(&control);
            else if (cmd.opcode == R0_CMD_DUTY && now >= cmd.sent_ms && now - cmd.sent_ms <= 500) {
#ifdef BOARD_EVT1
                compass_stop(&compass);
#endif
                r0_request_motor(&control, cmd.value, now);
            }
#ifdef BOARD_EVT1
            else if ((cmd.opcode == COMPASS_CMD_DIRECTION || cmd.opcode == COMPASS_CMD_RENEW) &&
                     now >= cmd.sent_ms && now - cmd.sent_ms <= 500 &&
                     control.armed && !control.faults && !in.docked && r0_limits_ready(&control) &&
                     cmd.value <= control.limits.max_duty_percent) {
                if (cmd.opcode == COMPASS_CMD_RENEW)
                    compass_renew(&compass, cmd.target_deg, cmd.tolerance_deg, cmd.value, now);
                else {
                    if (!compass.active) r0_request_motor(&control, 0, now);
                    compass_request(&compass, cmd.target_deg, cmd.tolerance_deg, cmd.value, now);
                }
            } else if (cmd.opcode >= PLUG_CMD_START && cmd.opcode <= PLUG_CMD_END &&
                       now >= cmd.sent_ms && now - cmd.sent_ms <= 500) {
                if (cmd.opcode == PLUG_CMD_START && !in.docked) plug_wear_start(&wear,now);
                else if (cmd.opcode != PLUG_CMD_START) {
                    if (cmd.opcode == PLUG_CMD_PAUSE) plug_wear_pause(&wear);
                    else plug_wear_end(&wear);
                    compass_stop(&compass); r0_stop(&control);
                }
            }
#endif
        }
        if (r0_wifi_active() && now >= wifi_until) {
            r0_stop(&control); motor_off();
            r0_wifi_session(false);
        }
#ifdef BOARD_EVT1
        /* No qualified wear classifier exists yet. Temperature/motion alone
         * must not silently become proof of wear or Lockbox credit.
         */
        plug_wear_tick(&wear, PLUG_WEAR_UNKNOWN, false, in.sensors_valid,
                       in.docked, sample_ms, now);
        update_heading(now);
        if (compass.active) {
            unsigned duty = compass_tick(&compass, control.armed && !control.faults &&
                !in.docked && r0_limits_ready(&control), heading_valid,
                (heading_mdeg + 180000) % 360000, sample_ms, now);
            if (!compass.active || !r0_request_motor(&control, duty, now)) {
                compass_stop(&compass);
                r0_stop(&control);
            }
        }
#endif
        if (atomic_exchange(&stop_requested, false)) {
            r0_stop(&control);
#ifdef BOARD_EVT1
            compass_stop(&compass);
#endif
        }
        r0_control_tick(&control, in, now);
        motor_apply();
#ifdef BOARD_EVT1
        if (control.output_percent || in.docked) magnetic_settle_until = now + 1000;
        evt_console_poll(&compass_cal);
        update_heading(now);
#endif
        publish(now);
#ifdef BOARD_EVT1
        evt_case_radio_publish();
#endif
        if (now >= next_log) {
            char line[R0_STATUS_JSON_CAPACITY]; r0_status_json(line, sizeof(line)); ESP_LOGI(TAG, "%s", line);
            next_log = now + 5000;
        }
        ESP_ERROR_CHECK(esp_task_wdt_reset());
        vTaskDelay(pdMS_TO_TICKS(20));
    }
}
