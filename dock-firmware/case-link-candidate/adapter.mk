# Keep the candidate separate from the production dock build.
include Makefile

STM32_HEADERS = -I../include -I../vendor/st -I../vendor/cmsis

.PHONY: adapter-test adapter-compile
adapter-test: | build
	$(HOST_CC) $(HOST_FLAGS) -Wno-int-to-pointer-cast $(STM32_HEADERS) -DCASE_SC16_I2C_MODEL stm32_sc16_i2c.c test_stm32_sc16_i2c.c -o build/test-stm32-sc16-i2c
	build/test-stm32-sc16-i2c

adapter-compile: | build
	$(CROSS)gcc $(TARGET_FLAGS) $(STM32_HEADERS) -fstack-usage -c stm32_sc16_i2c.c -o build/stm32_sc16_i2c.o
	$(CROSS)gcc $(TARGET_FLAGS) -nostdlib -Wl,-Map,build/sc16-i2c-link.map -Tcompile_only.ld stm32_sc16_i2c.c sc16_bridge.c stm32_sc16_i2c_compile.c ../src/runtime.c $(STM32_HEADERS) -lgcc -o build/sc16-i2c-link.elf
	$(CROSS)size build/stm32_sc16_i2c.o
	$(CROSS)size build/sc16-i2c-link.elf
