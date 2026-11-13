HOST_CC ?= cc
CROSS ?= /private/tmp/dock-arm-toolchain/arm-gnu-toolchain-13.3.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-
HOST_FLAGS = -std=c11 -O1 -g -Wall -Wextra -Werror -pedantic -fsanitize=undefined -fno-omit-frame-pointer
TARGET_FLAGS = -mcpu=cortex-m0plus -mthumb -std=c11 -Os -g3 -ffreestanding -fno-builtin -Wall -Wextra -Werror -pedantic
.PHONY: test compile-only roundtrip peer-review
build:
	mkdir -p build
test: | build
	python3 generate_vectors.py
	$(HOST_CC) $(HOST_FLAGS) case_link.c test_case_link.c -o build/test-case-link
	build/test-case-link
roundtrip: | build
	$(HOST_CC) $(HOST_FLAGS) -I../../firmware/main case_link.c ../../firmware/main/case_telemetry.c ../../firmware/main/thermal_history.c test_sender_roundtrip.c -o build/test-sender-roundtrip
	build/test-sender-roundtrip
peer-review: | build
	$(HOST_CC) $(HOST_FLAGS) case_link.c peer-regression.c -o build/test-peer-regression
	build/test-peer-regression
compile-only: | build
	$(CROSS)gcc $(TARGET_FLAGS) -c case_link.c -o build/case_link.o
	$(CROSS)gcc $(TARGET_FLAGS) -nostdlib -Wl,-Map,build/compile-only.map -Tcompile_only.ld case_link.c compile_only.c ../src/runtime.c -lgcc -o build/compile-only.elf
	$(CROSS)size build/compile-only.elf
