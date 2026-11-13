"""Read-only FreeCAD solid/extrema/native-body audit of local selected models."""
from pathlib import Path
import hashlib,json
import FreeCAD as A,Part
H=Path(__file__).resolve().parent;O=H/'DockMain.3dshapes';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((H/'model-plan.json').read_text());records=[]
for lib,row in sorted(plan['footprint_models'].items()):
 path=O/row['local_STEP'];assert sha(path)==row['sha256'];shape=Part.read(str(path));assert shape.isValid() and shape.Solids and all(s.isValid()for s in shape.Solids)
 bb=shape.optimalBoundingBox(False,False);records.append({'footprint':lib,'STEP':path.name,'sha256':sha(path),'solid_count':len(shape.Solids),'volume_mm3':shape.Volume,'bounds_mm':[bb.XMin,bb.YMin,bb.ZMin,bb.XMax,bb.YMax,bb.ZMax]})
custom=json.loads((O/'custom-model-provenance.json').read_text())['packages'];native=[]
for name,row in custom.items():
 path=O/row['native'];before=sha(path);d=A.openDocument(str(path));d.recompute();bodies=[b for b in d.Objects if b.TypeId=='PartDesign::Body'];assert len(bodies)==row['editable_native_bodies']
 assert all(b.Shape.isValid()and len(b.Shape.Solids)==1 for b in bodies)
 compound=Part.makeCompound([b.Shape for b in bodies]);step=Part.read(str(O/row['STEP']));assert abs(compound.Volume-step.Volume)<1e-6
 A.closeDocument(d.Name);assert sha(path)==before
 native.append({'native':path.name,'sha256':before,'editable_bodies':len(bodies),'STEP_volume_matches_mm3_tolerance':1e-6})
usb=json.loads((O/'usb120-model-provenance.json').read_text());d=A.openDocument(str(O/usb['native']));d.recompute();bodies=[b for b in d.Objects if b.TypeId=='PartDesign::Body'];assert len(bodies)==36 and all(b.Shape.isValid()and len(b.Shape.Solids)==1 for b in bodies)
compound=Part.makeCompound([b.Shape for b in bodies]);step=Part.read(str(O/usb['STEP']));assert abs(compound.Volume-step.Volume)<1e-6;A.closeDocument(d.Name)
native.append({'native':usb['native'],'sha256':sha(O/usb['native']),'editable_bodies':36,'four_native_stake_extrusions_in_two_shell_bodies':True})
report={'status':'pass: local STEP solid validity/analytic extrema and selected native-body readback','FreeCAD':A.Version(),'model_plan_sha256':sha(H/'model-plan.json'),'STEP_footprint_families':records,'editable_native_readback':native,'physical_received_part_or_fit_validation':False,'note':'Standard KiCad families are attributed nominal package models; custom TI packages/USB stake derivative are dimensional reconstructions, not OEM exact CAD.'}
(H/'model-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(report['status'],len(records),'families')
