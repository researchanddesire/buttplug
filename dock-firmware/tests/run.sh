#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p tests/.build
${HOST_CC:-cc} -std=c11 -O1 -g -Wall -Wextra -Werror -fsanitize=${SANITIZERS:-undefined} \
  -fno-omit-frame-pointer -Iinclude src/dock_app.c src/ntc.c src/lcd.c tests/test_behavior.c \
  -o tests/.build/test_behavior
tests/.build/test_behavior
