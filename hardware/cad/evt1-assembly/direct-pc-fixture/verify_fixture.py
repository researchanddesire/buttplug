"""Cold reopen the editable fixture and compare its three STEP print exports."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

import FreeCAD as App
import Part

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--package", type=Path, default=Path(__file__).resolve().parent)
parser.add_argument("--steps", type=Path, help="Check the exchanged solids in this directory.")
parser.add_argument("--compare-native", type=Path, help="Compare retained mating geometry against a saved fixture.")
parser.add_argument("--output", type=Path, help="Write check results to an explicit path.")
args = parser.parse_args()
root = args.package
native = root / "Compass EVT1 - Direct PC Contact Fixture.FCStd"
report = json.loads((root / "fixture-fit.json").read_text())
def digest(path):
    return sha256(path.read_bytes()).hexdigest()

assert digest(native) == report["native_sha256"], native
d = App.openDocument(str(native))
d.recompute()
steps = {}
for name in ("BenchSaddle", "PreloadBar", "PogoRetainer"):
    source = d.getObject(name).Shape
    assert source.isValid() and len(source.Solids) == 1, name
    if args.steps is None:
        continue
    step = args.steps / (name + ".step")
    imported = Part.read(str(step))
    assert all(s.isValid() and len(s.Solids) == 1 for s in (source, imported)), name
    shared = abs(source.common(imported, 1e-7).Volume)
    difference = abs(source.Volume - shared) + abs(imported.Volume - shared)
    assert difference < .004, (name, difference)
    steps[name] = {"export_sha256": digest(step), "volume_mm3": round(source.Volume, 6),
                   "difference_mm3": round(difference, 7)}
assert d.getObject("DeckBlank").Visibility is False
assert d.getObject("InstalledDockContactCarrier").Visibility is False
for name in ("J94PinBoard", "RevisedContinuousSkin", "MetalBody", "MotorThermistorCap",
             "CT1", "CT2", "CT3", "CT4", *(f"P{i}Tip" for i in (91, 92, 93, 94))):
    witness = d.getObject(name)
    assert witness.Shape.isValid() and len(witness.Shape.Solids) == 1, name
assert d.getObject("SourceBindings").ProductAssemblySHA256 in report["assembly_sources"].values()
# Move the empty bar over the fully seated plug, with both push screws withdrawn.
bar = d.getObject("PreloadBar").Shape
seated = [d.getObject(name).Shape for name in (
    "RevisedContinuousSkin", "MetalBody", "MotorThermistorCap", "CT1", "CT2", "CT3", "CT4"
)]
bar_sweep = []
for lift in range(24, -1, -2):
    moved = bar.copy()
    moved.translate(App.Vector(0, 0, lift))
    interference = max(abs(moved.common(item, 1e-7).Volume) for item in seated)
    assert interference < 1e-4, (lift, interference)
    bar_sweep.append({"lift_mm":lift, "maximum_common_volume_mm3":round(interference, 7)})
native_difference = {}
if args.compare_native:
    comparison = App.openDocument(str(args.compare_native))
    assert comparison is not d, "Use an independent source file for comparison."
    names = ("BenchSaddle", "PreloadBar", "PogoRetainer", "J94PinBoard",
             "RevisedContinuousSkin", "MetalBody", "MotorThermistorCap",
             "CT1", "CT2", "CT3", "CT4", *(f"P{i}Tip" for i in (91, 92, 93, 94)))
    for name in names:
        first = d.getObject(name).Shape
        second = comparison.getObject(name).Shape
        shared = abs(first.common(second, 1e-7).Volume)
        difference = abs(first.Volume - shared) + abs(second.Volume - shared)
        assert difference < .004, (name, difference)
        native_difference[name] = round(difference, 7)
    App.closeDocument(comparison.Name)
App.closeDocument(d.Name)
evidence = {"native_sha256": digest(native), "cold_reopen": "pass", "steps": steps, "bar_installation_poses": bar_sweep, "native_differences_mm3": native_difference}
if args.output:
    args.output.write_text(json.dumps(evidence, indent=2) + "\n")
print(json.dumps(evidence, indent=2))
