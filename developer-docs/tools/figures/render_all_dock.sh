#!/bin/sh
# Render every dock figure at full quality (raw renders into developer-docs/.cache/figures/raw/).
HERE="$(cd "$(dirname "$0")" && pwd)"
for s in hero open base_inside lid_inside contact_head d1 d2 d3 d4 d5 d6 d7 d8 d9; do
  blender -b --python "$HERE/render_dock.py" -- "$s" > "$HERE/../../.cache/figures/raw/dock-$s.log" 2>&1 && echo "ok $s" || echo "FAILED $s"
done
