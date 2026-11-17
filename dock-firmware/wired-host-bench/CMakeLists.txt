cmake_minimum_required(VERSION 3.17)
include($ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake)
project(compass_wired_host C CXX ASM)
set(CMAKE_C_STANDARD 11)
pico_sdk_init()

option(COMPASS_USB_SMOKE "Read thermal-status from the existing plug firmware" OFF)
option(COMPASS_WIRED_MAIN "Build for the wired Main RP2040 pinout and I2C control" OFF)
if(COMPASS_USB_SMOKE AND COMPASS_WIRED_MAIN)
    message(FATAL_ERROR "The wired Main target requires framed telemetry")
endif()
add_executable(compass_wired_host
    main.c
    ../case-link-candidate/case_link.c
    ../case-link-candidate/wired_cdc.c
)
target_include_directories(compass_wired_host PRIVATE . ../case-link-candidate)
target_compile_options(compass_wired_host PRIVATE -Wall -Wextra)
if(COMPASS_USB_SMOKE)
    target_compile_definitions(compass_wired_host PRIVATE COMPASS_USB_SMOKE=1)
endif()
target_link_libraries(compass_wired_host PRIVATE pico_stdlib pico_rand tinyusb_host)
if(COMPASS_WIRED_MAIN)
    target_compile_definitions(compass_wired_host PRIVATE COMPASS_WIRED_MAIN=1)
    target_sources(compass_wired_host PRIVATE
        ../wired-main/host_bridge_rp2040.c
        ../wired-main/host_control.c
    )
    target_include_directories(compass_wired_host PRIVATE ../wired-main)
    target_link_libraries(compass_wired_host PRIVATE pico_i2c_slave)
    pico_enable_stdio_uart(compass_wired_host 0)
else()
    pico_enable_stdio_uart(compass_wired_host 1)
endif()
pico_enable_stdio_usb(compass_wired_host 0)
pico_add_extra_outputs(compass_wired_host)
