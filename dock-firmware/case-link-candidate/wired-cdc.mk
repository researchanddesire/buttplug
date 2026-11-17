include Makefile

WIRED_SENDER = ../../firmware/main
WIRED_SOURCES = wired_cdc.c case_link.c

.PHONY: wired-cdc-test wired-cdc-compile
wired-cdc-test: | build
	$(HOST_CC) $(HOST_FLAGS) -I$(WIRED_SENDER) $(WIRED_SOURCES) test_wired_cdc.c \
		$(WIRED_SENDER)/case_telemetry.c $(WIRED_SENDER)/thermal_history.c -o build/test-wired-cdc
	build/test-wired-cdc $(WIRED_CONSOLE_CAPTURE)
	$(HOST_CC) $(HOST_FLAGS) -DCOMPASS_WIRED_MAIN=1 -I$(WIRED_SENDER) $(WIRED_SOURCES) test_wired_cdc.c \
		$(WIRED_SENDER)/case_telemetry.c $(WIRED_SENDER)/thermal_history.c -o build/test-wired-cdc-main
	build/test-wired-cdc-main $(WIRED_CONSOLE_CAPTURE)

wired-cdc-compile: | build
	$(CROSS)gcc $(TARGET_FLAGS) -c wired_cdc.c -o build/wired_cdc.o
	$(CROSS)gcc $(TARGET_FLAGS) -c case_link.c -o build/case_link-wired.o
