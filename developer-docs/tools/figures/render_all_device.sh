#!/bin/sh
# Render every device figure at full quality (raw renders into developer-docs/.cache/figures/raw/).
HERE="$(cd "$(dirname "$0")" && pwd)"
for s in hero dockface exploded cutaway step01 step02 step03 step04 step05 step06 step07 step08 step09; do
  blender -b --python "$HERE/render_device.py" -- "$s" > "$HERE/../../.cache/figures/raw/$s.log" 2>&1 && echo "ok $s" || echo "FAILED $s"
done
