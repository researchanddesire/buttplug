idf_component_register(SRCS "main.c" "proto_control.c" "plug_runtime.c" "thermal_history.c" "case_telemetry.c" "case_runtime.c" "evt_case_radio.c" "compass_control.c" "compass_protocol.c" "r0_sensors.c" "evt1_sensors.c" "evt_math.c" "evt_console.c" "r0_radio.c"
    INCLUDE_DIRS "."
    REQUIRES esp_driver_gpio esp_driver_ledc esp_driver_i2c esp_adc esp_timer
             esp_wifi esp_netif esp_event esp_http_server bt nvs_flash esp_system json esp_driver_usb_serial_jtag)
