"""Verify a third NTC and both tails on the underside of the offset pack."""
from hashlib import sha256
import json
from pathlib import Path
import sys

sys.path.insert(0, "/Applications/FreeCAD.app/Contents/Resources/lib")
assembly = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(assembly.parent.parent))
import FreeCAD as App
import Part
from body_pack_trial import _cylinder, _wire

doc = App.openDocument(str(assembly))
group = doc.addObject("App::DocumentObjectGroup", "PackTelemetryNTC")
group.Label = "Independent pack telemetry thermistor and tails"
color = (.34,.62,.72)

def add_variant(name, z):
    head = _cylinder(doc, group, name + "Head", "TH3 pack monitor NTC", (0, 43, z),
        1.5, 10, "Vishay NTCLE413E2103F524A maximum head envelope beneath broad pouch face.", color)
    wires = [_wire(doc, group, name+suffix, "J8 "+suffix,
        [(x,43,z),(x,35,z),(x,22,-2.70),(x,-14.6,-2.70)], .46, color,
        "Illustrative 0.46 mm insulated tail. Free endpoint before flange dressing.")
        for suffix,x in (("Sense",-.4),("Return",.4))]
    doc.recompute()
    return head, wires

def check(items, reference):
    pairs = [(a,b) for a in items for b in reference]
    results = []
    for a, b in pairs:
        assert a.Shape.isValid() and b.Shape.isValid(), (a.Name,b.Name)
        volume = a.Shape.common(b.Shape).Volume
        distance = a.Shape.distToShape(b.Shape)[0]
        results.append({"new": a.Name, "against": b.Name, "distance_mm": distance, "common_mm3": volume})
    assert not [result for result in results if result["common_mm3"]>1e-5], [
        result for result in results if result["common_mm3"]>1e-5]
    return results

meta = {"native_sha256":sha256(assembly.read_bytes()).hexdigest(),
        "third_thermistor": "TH3 / NTCLE413E2103F524A / 3 mm x 10 mm envelope",
        "scope": "Closed pose; routed to naked neck end; no retained wiring, assembly motion or physical test."}
fixed = [doc.MetalBody,doc.MotorThermistorCap,doc.BodyPackTrialMotor]
nominal = [*doc.BodyPackTrialTails.Group,doc.BodyPackTrialPack,
           doc.BodyPackTrialPackNTC1,doc.BodyPackTrialPackNTC2]
with_growth = [*(x for x in doc.BodyPackTrialTails.Group if "NTC" not in x.Name),
               *[x for x in doc.Objects if x.Name.startswith("BodyPackTrialGrowthNTC")],
               doc.BodyPackTrialGrowth,doc.BodyPackTrialPackNTC1AtGrowth,
               doc.BodyPackTrialPackNTC2AtGrowth]
for label,z,existing in (("nominal",-5.65,nominal),("growth",-6.2,with_growth)):
    head,wires = add_variant(label.capitalize(),z)
    meta[label]=check([head,*wires],fixed+existing)+check(wires[:1],wires[1:])
    print(label,len(meta[label]),"checks passed")
Path(sys.argv[2]).write_text(json.dumps(meta,indent=2)+"\n")
App.closeDocument(doc.Name)
