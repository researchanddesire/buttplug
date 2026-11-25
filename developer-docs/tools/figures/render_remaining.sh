#!/bin/sh
# Remaining dock shots, then the single-part device shots.
HERE="$(cd "$(dirname "$0")" && pwd)"
RAW="$HERE/../../.cache/figures/raw"
for s in base_inside lid_inside contact_head d1 d2 d3 d4 d5 d6 d7 d8 d9; do
  blender -b --python "$HERE/render_dock.py" -- "$s" > "$RAW/dock-$s.log" 2>&1 && echo "ok dock $s" || echo "FAILED dock $s"
done
for s in part_body part_cap part_nut part_tray part_cover part_cover_in part_plunger part_cradle part_skin part_oring; do
  blender -b --python "$HERE/render_device.py" -- "$s" > "$RAW/$s.log" 2>&1 && echo "ok $s" || echo "FAILED $s"
done
