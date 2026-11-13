# Keep these targets separate from the frozen decoder validation Makefile.
include Makefile

.PHONY: bridge-test bridge-compile
bridge-test: | build
	$(HOST_CC) $(HOST_FLAGS) sc16_bridge.c test_sc16_bridge.c -o build/test-sc16-bridge
	build/test-sc16-bridge

bridge-compile: | build
	$(CROSS)gcc $(TARGET_FLAGS) -fstack-usage -c sc16_bridge.c -o build/sc16_bridge.o
	$(CROSS)size build/sc16_bridge.o
