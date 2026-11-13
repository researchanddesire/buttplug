#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
test_binary=$(mktemp /tmp/buttplug-evt-console.XXXXXX)
trap 'rm -f "$test_binary"' EXIT
cc -std=c11 -Wall -Wextra -Werror -fsanitize=undefined -DBOARD_EVT1=1 \
    -I tests/console-stubs -I main tests/test_evt_console.c main/evt_console.c \
    main/evt_math.c -lm -o "$test_binary"
"$test_binary"
