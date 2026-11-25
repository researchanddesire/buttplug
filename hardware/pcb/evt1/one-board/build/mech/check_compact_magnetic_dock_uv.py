from hashlib import sha256
import json
import math
from pathlib import Path

import FreeCAD as App
import Part

directory = Path("mech").resolve()
native_path = directory / "CompactMagneticDock.FCStd"
native = App.openDocument(str(native_path))
shell = [native.Base, native.Lid, native.ServiceCover]
assert all(obj.Shape.isValid() and len(obj.Shape.Solids) == 1 for obj in shell)
front = native.Lid.Placement.Rotation.multVec(App.Vector(0, -1, 0))
opening_deg = math.degrees(math.atan2(front.z, -front.y))
assert abs(opening_deg - 105) < 0.01

emitters = [obj for obj in native.FixedUV.Group if obj.Label.endswith("VLMU35CB20-275-120")]
assert len(emitters) == 4
assert all(len(emitter.Shape.Solids) == 10 for emitter in emitters)
targets = native.LidInterlockTargets.Group
assert len(targets) == 2
systems = [*native.Plug.Group, *native.DockHardware.Group, *native.FixedUV.Group, *targets]
solids = [solid for obj in shell + systems for solid in obj.Shape.Solids]
native_volume = sum(solid.Volume for solid in solids)
fits = json.loads((directory / "compact-magnetic-dock-fit.json").read_text())
assert len(fits["uv_c"]["emitters"]) == 4
assert not any(fits[name] for name in ("load_overlaps", "lid_overlaps", "head_overlaps"))
assert not fits["uv_c"]["mount_overlaps"]

counts = {}
positions = {}
for name in ("CompactMagneticDock", "CompactMagneticDockClosed"):
    shape = Part.read(str(directory / (name + ".step")))
    assert shape.isValid() and len(shape.Solids) == len(solids), (name, len(shape.Solids), len(solids))
    assert abs(shape.Volume - native_volume) < native_volume * 1e-4, name
    counts[name] = len(shape.Solids)
    # Identify both Hall targets by Ø2 × 1 volume and mirrored station X.
    centers = [solid.CenterOfMass for solid in shape.Solids
               if abs(solid.Volume - math.pi) < 1e-5 and abs(abs(solid.CenterOfMass.x) - 36.5) < 1e-4]
    positions[name] = [tuple(round(coord, 4) for coord in center) for center in centers]
    assert len(centers) == 2, (name, positions[name])
    if name.endswith("Closed"):
        assert all(abs(center.y + 9.2) < 0.01 and abs(center.z - 34.68) < 0.01 for center in centers)
    else:
        assert all(center.y > 170 and center.z > 170 for center in centers), positions[name]
centerline_hits = []
for site in fits["uv_c"]["emitters"]:
    origin = App.Vector(*site["optical_center_mm"])
    direction = App.Vector(*site["optical_normal"])
    ray = Part.makeLine(origin + direction * 0.01, origin + direction * 30)
    intercepts = [(round((v.Point - origin).dot(direction), 3), obj.Label)
                  for obj in (native.Base, *native.Plug.Group)
                  for v in obj.Shape.section(ray).Vertexes
                  if (v.Point - origin).dot(direction) >= 0]
    centerline_hits.append((site["side"], site["height"], min(intercepts) if intercepts else None))
report = {"native_sha256": sha256(native_path.read_bytes()).hexdigest(),
          "solid_counts": counts, "lid_target_positions_mm": positions,
          "geometric_centerline_hits_distance_mm": centerline_hits}
Path("build/mech/compact-magnetic-dock-uv-readback.json").write_text(json.dumps(report, indent=2) + "\n")
