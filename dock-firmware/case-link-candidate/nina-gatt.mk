include Makefile

PLUG_SRC = ../../firmware/main

.PHONY: nina-gatt-test nina-gatt-compile
nina-gatt-test: | build
	$(HOST_CC) $(HOST_FLAGS) -I$(PLUG_SRC) nina_gatt.c sc16_bridge.c case_link.c \
		$(PLUG_SRC)/case_telemetry.c $(PLUG_SRC)/thermal_history.c test_nina_gatt.c -o build/test-nina-gatt
	build/test-nina-gatt

nina-gatt-compile: | build
	$(CROSS)gcc $(TARGET_FLAGS) -fstack-usage -c nina_gatt.c -o build/nina_gatt.o
	$(CROSS)size build/nina_gatt.o
