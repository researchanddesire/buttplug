include Makefile

.PHONY: nina-startup-test nina-startup-compile
nina-startup-test: | build
	$(HOST_CC) $(HOST_FLAGS) sc16_bridge.c nina_startup.c test_nina_startup.c -o build/test-nina-startup
	build/test-nina-startup

nina-startup-compile: | build
	$(CROSS)gcc $(TARGET_FLAGS) -c nina_startup.c -o build/nina_startup.o
	$(CROSS)size build/nina_startup.o
