CROSS ?= arm-none-eabi-
CC = $(CROSS)gcc
OBJCOPY = $(CROSS)objcopy
SIZE = $(CROSS)size
PROFILE ?= direct
CFLAGS = -mcpu=cortex-m0plus -mthumb -std=c11 -Os -g3 -ffunction-sections -fdata-sections -ffreestanding -fno-builtin -fno-unwind-tables -fno-asynchronous-unwind-tables -Wall -Wextra -Werror -Iinclude -Ivendor/st -Ivendor/cmsis
SOURCES = src/startup.c src/runtime.c src/main.c src/board_stm32l071.c src/dock_app.c src/ntc.c src/lcd.c
ifeq ($(PROFILE),wired)
BUILD ?= build/wired
CFLAGS += -DDOCK_WIRED_MAIN -DDOCK_UV_SENSE_MILLIOHM=4220u -Iwired-main
SOURCES += src/host_bus_stm32.c
OBJECTS += $(BUILD)/host_client.o $(BUILD)/host_control.o
else ifeq ($(PROFILE),direct)
BUILD ?= build
else
$(error Unknown dock firmware profile: $(PROFILE))
endif
OBJECTS += $(patsubst src/%.c,$(BUILD)/%.o,$(SOURCES))
.PHONY: all test clean
all: $(BUILD)/dock-evt1.bin $(BUILD)/dock-evt1.hex
$(BUILD):
	mkdir -p $@
$(BUILD)/%.o: src/%.c | $(BUILD)
	$(CC) $(CFLAGS) -MMD -MP -c $< -o $@
$(BUILD)/%.o: wired-main/%.c | $(BUILD)
	$(CC) $(CFLAGS) -MMD -MP -c $< -o $@
$(BUILD)/dock-evt1.elf: $(OBJECTS) stm32l071cb.ld
	$(CC) -mcpu=cortex-m0plus -mthumb -nostdlib -Wl,--gc-sections,-Map,$(BUILD)/dock-evt1.map -Tstm32l071cb.ld $(OBJECTS) -lgcc -o $@
	$(SIZE) $@
$(BUILD)/%.bin: $(BUILD)/%.elf
	$(OBJCOPY) -O binary $< $@
$(BUILD)/%.hex: $(BUILD)/%.elf
	$(OBJCOPY) -O ihex $< $@
test:
	./tests/run.sh
clean:
	rm -rf $(BUILD)
-include $(OBJECTS:.o=.d)
