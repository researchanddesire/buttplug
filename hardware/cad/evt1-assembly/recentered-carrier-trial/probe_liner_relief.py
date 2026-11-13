"""Exact source-profile wall check for the approved bounded liner relief."""
from pathlib import Path
import json,sys
import FreeCAD as App
import Part
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
import build_evt1_dock_recentered_carrier as m
out=Path(__file__).resolve().parent
source=App.openDocument(str(m.SHELL)); carrier=App.openDocument(str(out/'RecenteredCarrierTrial.FCStd'))
doc=App.newDocument('LinerReliefProbe'); body=doc.addObject('PartDesign::Body','LowerLinerReliefContext')
seed=body.newObject('PartDesign::Feature','ExactSourceLowerChamber');seed.Shape=source.LowerChamber.Shape.copy()
ns=m._profiles(doc);sk=ns['rr'](body,'ApprovedReliefProfile',10.6,10.6,.8,37.1,(-43,19))
cut=ns['pocket'](body,'ApprovedReliefPocket',sk,24)
outer=source.ChamberOuterProfile.Shape.Wires[0].copy(); outer.translate(App.Vector(0,0,-11))
inner=source.ChamberCavityProfile.Shape.Wires[0].copy(); inner.translate(App.Vector(0,0,-37))
relief=sk.Shape.Wires[0].copy();relief.translate(App.Vector(0,0,-37.1))
relieved=Part.Face(inner).fuse(Part.Face(relief)).removeSplitter()
assert len(relieved.Faces)==1
remaining=outer.distToShape(relieved.Faces[0].OuterWire)
collar=carrier.RecenteredCarrier.Shape.common(m.box(-49,13,13.3,-37,25,14.3))
clear=collar.distToShape(body.Shape)
collar_wire=carrier.RecenteredCarrierFloorLightTrapProfile0.Shape.Wires[0].copy()
collar_wire.translate(App.Vector(0,0,-13.3))
lateral=collar_wire.distToShape(relief)[0]
baseline=carrier.RecenteredCarrier.Shape.common(source.LowerChamber.Shape)
poses=[]
for z in (0,.1,.25,.5,1,2,3,4,6,8,10,12,15,20,25,30,35,40):
 s=carrier.RecenteredCarrier.Shape.copy();s.translate(App.Vector(0,0,z)); v=s.common(body.Shape).Volume
 poses.append({'Z_lift_mm':z,'intersection_mm3':v});assert v<1e-6,(z,v)
result={'source_path':str(m.SHELL),'source_SHA256':m.sha(m.SHELL),
        'negative_original_collar_intersection_mm3':baseline.Volume,
        'negative_original_bounds_mm':m.bounds(baseline),
        'relief_WH_R_centerXYZ_depth_mm':[10.6,10.6,.8,-43,19,37.1,24],
        'remaining_outer_to_actual_relieved_inner_wire_mm':remaining[0],
        'remaining_wall_nearest_points':[[list(a),list(b)]for a,b in remaining[1]],
        'actual_collar_clearance_mm':clear[0],
        'actual_profile_lateral_clearance_mm':lateral,
        'axial_ledge_note':'Relief starts13.1 below collar13.3, so true minimum is0.2; lateral profile offset is0.3',
        'collar_nearest_points':[[list(a),list(b)]for a,b in clear[1]],
        'carrier_lift_checks':poses,'BOP_check':str(body.Shape.check(True))}
assert remaining[0]>=1 and abs(clear[0]-.2)<1e-6 and abs(lateral-.3)<1e-6,result
doc.recompute();doc.saveAs(str(out/'LinerReliefProbe.FCStd'))
(out/'liner-relief-probe.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2),flush=True)
