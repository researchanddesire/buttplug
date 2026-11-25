#ifdef BOARD_EVT1
#include "r0_sensors.h"
#include "evt_math.h"
#include "evt_console.h"
#include <stdlib.h>
#include <string.h>
#include "sdkconfig.h"
#include "driver/gpio.h"
#include "driver/i2c_master.h"
#include "esp_adc/adc_oneshot.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static i2c_master_dev_handle_t temperature, accel, magnetic;
static adc_oneshot_unit_handle_t adc;
static adc_cali_handle_t calibration;
static bool calibrated, initialized;
static bool tip_valid;
static int tip_millic;
static uint64_t tip_ms, next_tip;
static uint64_t tip_started_ms;
static uint32_t tip_sequence;
static bool tip_source_start, tip_source_end, tip_source_changed;
#ifdef BOARD_EVT1_ONE_BOARD
static bool pack_valid;
static int pack_millic;
static uint64_t pack_ms;
#endif
static esp_err_t read_reg(i2c_master_dev_handle_t dev, uint8_t reg, uint8_t *b, size_t n) {
    return i2c_master_transmit_receive(dev, &reg, 1, b, n, 30);
}
static esp_err_t write8(i2c_master_dev_handle_t dev, uint8_t reg, uint8_t value) {
    uint8_t b[] = {reg, value};
    return i2c_master_transmit(dev, b, sizeof(b), 30);
}
static esp_err_t write16(i2c_master_dev_handle_t dev, uint8_t reg, uint16_t value) {
    uint8_t b[] = {reg, (uint8_t)(value >> 8), (uint8_t)value};
    return i2c_master_transmit(dev, b, sizeof(b), 30);
}
static esp_err_t read16(uint8_t reg, uint16_t *value) {
    uint8_t b[2];
    esp_err_t err = read_reg(temperature, reg, b, sizeof(b));
    if (err == ESP_OK) *value = ((uint16_t)b[0] << 8) | b[1];
    return err;
}
static esp_err_t checked_write(i2c_master_dev_handle_t dev, uint8_t reg, uint8_t value) {
    uint8_t actual;
    esp_err_t err = write8(dev, reg, value);
    if (err == ESP_OK) err = read_reg(dev, reg, &actual, 1);
    return err != ESP_OK ? err : actual == value ? ESP_OK : ESP_ERR_INVALID_RESPONSE;
}
static esp_err_t conversion(unsigned channel, int16_t *result) {
    /* OS=start, single-ended, +/-4.096V, single-shot, 128SPS, comparator off. */
    uint16_t config = (uint16_t)(0xc383u | (channel << 12));
    esp_err_t err = write16(temperature, 1, config);
    if (err != ESP_OK) return err;
    uint64_t deadline = (uint64_t)esp_timer_get_time() + 40000;
    do {
        vTaskDelay(pdMS_TO_TICKS(10));
        uint16_t actual;
        if ((err = read16(1, &actual)) != ESP_OK) return err;
        if ((actual & 0x7fffu) != (config & 0x7fffu)) return ESP_ERR_INVALID_RESPONSE;
        if (actual & 0x8000u) {
            uint16_t value;
            if ((err = read16(0, &value)) == ESP_OK) *result = (int16_t)value;
            return err;
        }
    } while ((uint64_t)esp_timer_get_time() < deadline);
    return ESP_ERR_TIMEOUT;
}
static bool ntc_sample(unsigned channel, bool (*to_temperature)(int16_t, int16_t, int16_t, int *),
                       int *millic) {
    int16_t before = 0, reading = 0, after = 0;
    gpio_set_level(CONFIG_R0_PIN_ACCEL_INT_N, 1); /* EVT1 GPIO10 = excitation. */
    vTaskDelay(pdMS_TO_TICKS(10));
    bool ok = conversion(1, &before) == ESP_OK && conversion(channel, &reading) == ESP_OK &&
              conversion(1, &after) == ESP_OK;
    /* Every success/error/timeout path removes excitation before returning. */
    gpio_set_level(CONFIG_R0_PIN_ACCEL_INT_N, 0);
    return ok && to_temperature(reading, before, after, millic);
}
esp_err_t r0_sensors_init(void) {
    gpio_set_level(CONFIG_R0_PIN_ACCEL_INT_N, 0);
    gpio_config_t excitation = {.pin_bit_mask = 1ULL << CONFIG_R0_PIN_ACCEL_INT_N,
                                .mode = GPIO_MODE_OUTPUT};
    esp_err_t err = gpio_config(&excitation);
    if (err != ESP_OK) return err;
    i2c_master_bus_handle_t bus;
    i2c_master_bus_config_t bus_config = {.i2c_port = I2C_NUM_0,
        .sda_io_num = CONFIG_R0_PIN_SDA, .scl_io_num = CONFIG_R0_PIN_SCL,
        .clk_source = I2C_CLK_SRC_DEFAULT, .glitch_ignore_cnt = 7,
        .flags.enable_internal_pullup = false};
    if ((err = i2c_new_master_bus(&bus_config, &bus)) != ESP_OK) return err;
    i2c_device_config_t config = {.dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = 0x48, .scl_speed_hz = 100000};
    if ((err = i2c_master_bus_add_device(bus, &config, &temperature)) != ESP_OK) return err;
    config.device_address = 0x19;
    if ((err = i2c_master_bus_add_device(bus, &config, &accel)) != ESP_OK) return err;
    config.device_address = 0x1e;
    if ((err = i2c_master_bus_add_device(bus, &config, &magnetic)) != ESP_OK) return err;
    vTaskDelay(pdMS_TO_TICKS(20));
    uint8_t id;
    if ((err = read_reg(accel, 0x0f, &id, 1)) != ESP_OK) return err;
    if (id != 0x33) return ESP_ERR_INVALID_RESPONSE;
    if ((err = read_reg(magnetic, 0x4f, &id, 1)) != ESP_OK) return err;
    if (id != 0x40) return ESP_ERR_INVALID_RESPONSE;
    /* LSM303AGR rev11: accel25Hz XYZ, high-resolution +/-2g, BDU;
     * mag10Hz high-resolution continuous, temperature compensation, BDU,
     * internal offset cancellation. Do not write factory trim registers.
     */
    if ((err = checked_write(accel, 0x23, 0x88)) != ESP_OK ||
        (err = checked_write(accel, 0x20, 0x37)) != ESP_OK ||
        (err = checked_write(magnetic, 0x61, 0x02)) != ESP_OK ||
        (err = checked_write(magnetic, 0x62, 0x10)) != ESP_OK ||
        (err = checked_write(magnetic, 0x60, 0x80)) != ESP_OK) return err;
    adc_oneshot_unit_init_cfg_t adc_config = {.unit_id = ADC_UNIT_1};
    if ((err = adc_oneshot_new_unit(&adc_config, &adc)) != ESP_OK) return err;
    adc_oneshot_chan_cfg_t channel_config = {.atten = ADC_ATTEN_DB_12, .bitwidth = ADC_BITWIDTH_DEFAULT};
    if ((err = adc_oneshot_config_channel(adc, ADC_CHANNEL_0, &channel_config)) != ESP_OK) return err;
    adc_cali_curve_fitting_config_t cal = {.unit_id = ADC_UNIT_1, .chan = ADC_CHANNEL_0,
        .atten = ADC_ATTEN_DB_12, .bitwidth = ADC_BITWIDTH_DEFAULT};
    calibrated = adc_cali_create_scheme_curve_fitting(&cal, &calibration) == ESP_OK;
    initialized = true;
    return ESP_OK;
}
void r0_sensors_sleep(void) {
    gpio_set_level(CONFIG_R0_PIN_ACCEL_INT_N, 0);
    if (!initialized) return;
    (void)write16(temperature, 1, 0x4383);
    (void)write8(accel, 0x20, 0x00);
    (void)write8(magnetic, 0x60, 0x83);
}
void r0_sensors_sample(r0_sample_t *s) {
    memset(s, 0, sizeof(*s));
    if (!initialized) return;
    uint64_t now = (uint64_t)esp_timer_get_time() / 1000;
    if (now >= next_tip) {
        uint32_t edges_before = evt_console_source_snapshot(&tip_source_start);
        tip_started_ms = (uint64_t)esp_timer_get_time() / 1000;
        tip_valid = ntc_sample(0, evt_ntc_temperature, &tip_millic);
        tip_ms = (uint64_t)esp_timer_get_time() / 1000;
        uint32_t edges_after = evt_console_source_snapshot(&tip_source_end);
        tip_source_changed = edges_before != edges_after || tip_source_start != tip_source_end;
        ++tip_sequence;
        next_tip = tip_ms + 1000;
#ifdef BOARD_EVT1_ONE_BOARD
        /* Timestamp the tip and its source observation before the separate pack read. */
        pack_valid = ntc_sample(2, evt_pack_ntc_temperature, &pack_millic);
        pack_ms = (uint64_t)esp_timer_get_time() / 1000;
#endif
    }
    now = (uint64_t)esp_timer_get_time() / 1000;
    s->temperature_valid = tip_valid && now >= tip_ms && now - tip_ms <= 1500;
    s->temperature_sequence = tip_sequence;
    s->temperature_started_ms = tip_started_ms;
    s->temperature_sampled_ms = tip_ms;
    s->temperature_source_at_start = tip_source_start;
    s->temperature_source_at_end = tip_source_end;
    s->temperature_source_changed = tip_source_changed;
    if (s->temperature_valid) s->temperature_millic = tip_millic;
#ifdef BOARD_EVT1_ONE_BOARD
    s->pack_temperature_valid = pack_valid && now >= pack_ms && now - pack_ms <= 1500;
    s->pack_temperature_sampled_ms = pack_ms;
    if (s->pack_temperature_valid) s->pack_temperature_millic = pack_millic;
#endif
    uint8_t status, config, b[6];
    s->accel_valid = read_reg(accel, 0x20, &config, 1) == ESP_OK && config == 0x37 &&
        read_reg(accel, 0x23, &config, 1) == ESP_OK && config == 0x88 &&
        read_reg(accel, 0x27, &status, 1) == ESP_OK && (status & 0x08) &&
        read_reg(accel, 0xa8, b, sizeof(b)) == ESP_OK;
    if (s->accel_valid)
        for (unsigned i = 0; i < 3; i++) s->accel[i] = r0_decode_axis(&b[2*i]) / 16;
    s->mag_valid = read_reg(magnetic, 0x60, &config, 1) == ESP_OK && config == 0x80 &&
        read_reg(magnetic, 0x61, &config, 1) == ESP_OK && config == 0x02 &&
        read_reg(magnetic, 0x62, &config, 1) == ESP_OK && config == 0x10 &&
        read_reg(magnetic, 0x67, &status, 1) == ESP_OK && (status & 0x08) &&
        read_reg(magnetic, 0x68, b, sizeof(b)) == ESP_OK;
    if (s->mag_valid) {
        for (unsigned i = 0; i < 3; i++) {
            s->mag[i] = r0_decode_axis(&b[2*i]);
            if (abs((int)s->mag[i]) >= 32700) s->mag_valid = false;
        }
    }
    int raw, mv;
    s->adc_calibrated = calibrated;
    s->battery_valid = calibrated && adc_oneshot_read(adc, ADC_CHANNEL_0, &raw) == ESP_OK &&
                       adc_cali_raw_to_voltage(calibration, raw, &mv) == ESP_OK;
    if (s->battery_valid) s->battery_mv = mv * CONFIG_R0_VBAT_DIVIDER_NUMERATOR /
                                                    CONFIG_R0_VBAT_DIVIDER_DENOMINATOR;
}
#endif
