#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
mkdir -p tests/.build
${HOST_CC:-cc} -std=c11 -O1 -g -Wall -Wextra -Werror -fsanitize=${SANITIZERS:-undefined} \
  -fno-omit-frame-pointer -Iinclude src/dock_app.c src/ntc.c src/lcd.c tests/test_behavior.c \
  -o tests/.build/test_behavior
tests/.build/test_behavior
${HOST_CC:-cc} -std=c11 -O1 -g -Wall -Wextra -Werror -fsanitize=${SANITIZERS:-undefined} \
  -fno-omit-frame-pointer -Iwired-main wired-main/host_client.c wired-main/host_control.c \
  wired-main/test_host_client.c -o tests/.build/test_host_client
tests/.build/test_host_client
${HOST_CC:-cc} -std=c11 -O1 -g -Wall -Wextra -Werror -fsanitize=${SANITIZERS:-undefined} \
  -fno-omit-frame-pointer -DDOCK_WIRED_MAIN -DDOCK_UV_SENSE_MILLIOHM=4220u -Iinclude -Iwired-main \
  src/dock_app.c src/ntc.c src/lcd.c tests/test_behavior.c -o tests/.build/test_behavior_wired
tests/.build/test_behavior_wired
