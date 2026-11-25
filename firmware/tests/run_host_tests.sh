#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
test_binary=$(mktemp /tmp/buttplug-r0-test.XXXXXX)
trap 'rm -f "$test_binary"' EXIT
cc -std=c11 -Wall -Wextra -Werror -fsanitize=undefined -I main tests/test_control.c main/proto_control.c -o "$test_binary"
"$test_binary"
cc -std=c11 -Wall -Wextra -Werror -fsanitize=undefined -I main tests/test_compass_control.c main/compass_control.c main/compass_protocol.c main/proto_control.c -o "$test_binary"
"$test_binary"
cc -std=c11 -Wall -Wextra -Werror -fsanitize=undefined -I main tests/test_evt_math.c main/evt_math.c -lm -o "$test_binary"
"$test_binary"
cc -std=c11 -Wall -Wextra -Werror -fsanitize=undefined -I main tests/test_plug_runtime.c main/plug_runtime.c -lm -o "$test_binary"
"$test_binary"
cc -std=c11 -Wall -Wextra -Werror -fsanitize=undefined -I main tests/test_thermal_history.c main/thermal_history.c -o "$test_binary"
"$test_binary"
cc -std=c11 -Wall -Wextra -Werror -fsanitize=undefined -I main tests/test_case_telemetry.c main/case_telemetry.c main/thermal_history.c -o "$test_binary"
"$test_binary"
cc -std=c11 -Wall -Wextra -Werror -fsanitize=undefined -I main tests/test_case_runtime.c main/case_runtime.c main/case_telemetry.c main/thermal_history.c -o "$test_binary"
"$test_binary"
