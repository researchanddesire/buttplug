#!/bin/sh
# Re-render the dock shots whose anchors or materials changed after the first pass.
HERE="$(cd "$(dirname "$0")" && pwd)"
RAW="$HERE/../../.cache/figures/raw"
for s in hero base_inside d3 lid_inside; do
  blender -b --python "$HERE/render_dock.py" -- "$s" > "$RAW/dock-$s.log" 2>&1 && echo "ok dock $s" || echo "FAILED dock $s"
done
