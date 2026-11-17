"""Export the exact steel keeper and check its pocket and dock datums."""

from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.BRepExtrema import BRepExtrema_DistShapeShape
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder
from OCC.Core.gp import gp_Ax2, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
ORDER = HERE.parents[1]
sys.path.insert(0, str(ORDER / "hinge-mockup"))
from export_pin_and_exterior import bounds, compare, read_native, step, volume

CAD = ROOT / "hardware/cad"
DEVICE = CAD / "manufacturing-layout/evt1-integration/contact-module-trial/single-board"
EXTERIOR = DEVICE / "exterior/SingleFlangeExterior.FCStd"
COVER = DEVICE / "closure-review/FlangeClosureReview.FCStd"
DOCK = CAD / "evt1-assembly/review-051/DockAssembly-051-review.zip"
INTERFACE = HERE.parent / "exchange-check.json"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def translate(shape, offset):
    move = gp_Trsf()
    move.SetTranslation(gp_Vec(*offset))
    return BRepBuilderAPI_Transform(shape, move, False).Shape()


def gap(left, right):
    check = BRepExtrema_DistShapeShape(left, right)
    assert check.IsDone()
    return check.Value()


def overlap(left, right):
    check = BRepAlgoAPI_Common(left, right)
    assert check.IsDone()
    return abs(volume(check.Shape()))


def cylinder(x, y, z, diameter, depth):
    axis = gp_Ax2(gp_Pnt(x, y, z), gp_Dir(0, 1, 0))
    return BRepPrimAPI_MakeCylinder(axis, diameter / 2, depth).Shape()


def main():
    interface = json.loads(INTERFACE.read_bytes())
    assert digest(EXTERIOR) == interface["device_exterior_sha256"]
    fixture = json.loads((DEVICE / "closure-review/closure-fit.json").read_bytes())
    assert digest(COVER) == fixture["native_sha256"]
    frame = json.loads((DEVICE / "exterior/source-binding.json").read_bytes())
    assert digest(EXTERIOR) == frame["native_sha256"]
    report = {
        "scope": "Two nominal keeper solids in the drilled cover and Rev051 docking frame",
        "source_sha256": {
            str(path.relative_to(ROOT)): digest(path)
            for path in (EXTERIOR, COVER, DOCK, INTERFACE, Path(__file__).resolve())
        },
        "keepers": {},
        "maximum_trial_disc_mm": [8.05, 1.05],
        "physical_validation": False,
    }
    with (
        ZipFile(EXTERIOR) as device,
        ZipFile(COVER) as enclosure,
        ZipFile(DOCK) as dock,
        TemporaryDirectory() as tmp,
    ):
        scratch = Path(tmp)
        prefix = "DockAssembly-051/"
        assert dock.read(prefix + "sources/SingleFlangeExterior.FCStd") == EXTERIOR.read_bytes()
        native = dock.read(prefix + "DockAssembly.FCStd")
        assert sha256(native).hexdigest() == interface["dock_native_sha256"]
        fixture_info = json.loads(dock.read(prefix + "native-check.json"))
        magnet_bounds = fixture_info["closed_component_bounds_mm"]
        cover = read_native(enclosure, "ClosureCover", scratch)
        skin = read_native(enclosure, "SavedSkin", scratch)
        pcb = read_native(enclosure, "FlangePCB", scratch)
        canonical = None
        for i, (x, z) in enumerate(((-14.5, -8.0), (3.0, -10.5))):
            name = f"SteelKeeper{i}"
            keeper = read_native(device, name, scratch)
            v = bounds(keeper)
            expected = (x - 4, -28.3, z - 4, x + 4, -27.3, z + 4)
            assert all(math.isclose(a, b, abs_tol=1e-7) for a, b in zip(v, expected)), v
            assert math.isclose(volume(keeper), 16 * math.pi, abs_tol=1e-7)
            local = translate(keeper, (-x, 28.3, -z))
            if canonical is None:
                canonical = local
            equality = compare(canonical, local)
            physical_pose = bounds(translate(keeper, frame["dock_translation_mm"]))
            magnet = magnet_bounds[f"ContactMagnet{i}"]
            assert all(abs(physical_pose[k] - magnet[k]) < 1e-6 for k in (0, 2, 3, 5))
            axial_gap = physical_pose[1] - magnet[4]
            assert math.isclose(axial_gap, 2.7, abs_tol=1e-7)
            cover_intersection, skin_intersection = overlap(keeper, cover), overlap(keeper, skin)
            assert max(cover_intersection, skin_intersection) < 1e-6
            largest_trial = cylinder(x, -28.3, z, 8.05, 1.05)
            assert overlap(largest_trial, cover) < 1e-6
            assert overlap(largest_trial, pcb) < 1e-6
            pocket_before_floor = cylinder(x, -28.31, z, 8.19, 0.009)
            pocket_inside_wall = cylinder(x, -28.299, z, 8.19, 1.098)
            assert overlap(pocket_before_floor, cover) > 0
            assert overlap(pocket_inside_wall, cover) < 1e-6
            report["keepers"][name] = {
                "product_bounds_mm": v,
                "dock_bounds_mm": physical_pose,
                "keeper_to_magnet_face_mm": round(axial_gap, 6),
                "cover_minimum_gap_mm": round(gap(keeper, cover), 6),
                "cover_overlap_mm3": cover_intersection,
                "skin_minimum_gap_mm": round(gap(keeper, skin), 6),
                "skin_overlap_mm3": skin_intersection,
                "maximum_trial_disc_clears_drilled_cover_and_PCB": True,
                "pocket_gauge_8p19_diameter_1p098_depth_clears": True,
                "PCB_clearance_to_maximum_trial_disc_mm": round(gap(largest_trial, pcb), 6),
                "identical_to_neutral_export": equality,
            }
        report["exchange"] = step(HERE / "SteelKeeper-8x1.step", [("SteelKeeper", canonical)])
    (HERE / "keeper-review.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
