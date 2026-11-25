#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
test_binary=$(mktemp /tmp/buttplug-case-radio.XXXXXX)
trap 'rm -f "$test_binary"' EXIT
cc -std=c11 -Wall -Wextra -Werror -fsanitize=undefined -DBOARD_EVT1=1 \
  -I tests/case-radio-stubs -I tests/console-stubs -I main \
  tests/test_case_radio.c main/evt_case_radio.c main/case_runtime.c \
  main/case_telemetry.c main/thermal_history.c -o "$test_binary"
"$test_binary"
