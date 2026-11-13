# A separate binary for the candidate radio schematic and existing dock control.
include Makefile

RADIO_DEFINES = -DDOCK_UV_SENSE_MILLIOHM=4220u
RADIO_CFLAGS = -mcpu=cortex-m0plus -mthumb -std=c11 -Os -g3 -ffreestanding -fno-builtin \
    -fno-unwind-tables -fno-asynchronous-unwind-tables -ffunction-sections \
    -fdata-sections -Wall -Wextra -Werror -I../include -I../vendor/st -I../vendor/cmsis
RADIO_SOURCES = ../src/startup.c ../src/runtime.c ../src/board_stm32l071.c \
    ../src/dock_app.c ../src/ntc.c ../src/lcd.c radio_main.c sc16_bridge.c stm32_sc16_i2c.c nina_startup.c
RADIO_HEADERS = $(wildcard *.h ../include/*.h)

.PHONY: radio-runtime radio-runtime-test
radio-runtime: build/dock-radio-schedule.elf

radio-runtime-test: | build
	$(HOST_CC) $(HOST_FLAGS) $(RADIO_DEFINES) -I../include ../src/dock_app.c test_radio_runtime.c -o build/test-radio-runtime
	build/test-radio-runtime

build/dock-radio-schedule.elf: $(RADIO_SOURCES) $(RADIO_HEADERS) ../stm32l071cb.ld radio-runtime.mk | build
	$(CROSS)gcc $(RADIO_CFLAGS) $(RADIO_DEFINES) -nostdlib -Wl,--gc-sections,-Map,build/dock-radio-schedule.map \
		-T../stm32l071cb.ld $(RADIO_SOURCES) -lgcc -o $@
	$(CROSS)size $@
