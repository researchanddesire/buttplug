"""Saved-native/STEP/mesh and static checks for the inert contact seal fixture."""
from pathlib import Path
import hashlib
import itertools
import json
import math
import sys
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
import Mesh
from OCC.Core.BRepGProp import brepgprop
from OCC.Core.GProp import GProp_GProps
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hardware/cad/manufacturing-layout/charging-dock'
OUT=SOURCE/'contact-seal-trial';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((OUT/'review.json').read_text())
assert sha(OUT/'ContactSealTrial.FCStd')==r['native_sha256']
assert sha(ROOT/'tools/build_contact_seal_trial.py')==r['builder_sha256']
assert sha(SOURCE/'ChargingDock.FCStd')==r['source_dock_native_sha256']
assert sha(SOURCE/'contact-seal-spec.json')==r['contact_seal_spec_sha256']
D=A.openDocument(str(OUT/'ContactSealTrial.FCStd'))
def sh(n):return D.getObject(n).Shape
def vol(s):
    if s.isNull():return 0
    p=GProp_GProps();brepgprop.VolumePropertiesGK(Part.__toPythonOCC__(s),p,1e-9,True,True,False,False,False);return p.Mass()
checks={}
for n,files in r['exports'].items():
    shape=sh(n);assert shape.isValid() and len(shape.Solids)==1,n
    for kind,digest in files.items():
        path=OUT/(n+{'STEP_sha256':'.step','view_STL_sha256':'-view.stl','print_STL_sha256':'.stl','section_view_STL_sha256':'-section-view.stl'}[kind]);assert sha(path)==digest
        if kind=='STEP_sha256':
            back=Part.Shape();back.read(str(path));assert back.isValid() and len(back.Solids)==1,n
            diff=vol(shape.cut(back))+vol(back.cut(shape));assert diff<.01,(n,diff)
            checks[n]={'STEP_symmetric_difference_mm3':diff}
        else:
            m=Mesh.Mesh(str(path))
            if kind=='section_view_STL_sha256':
                assert m.CountFacets>0 and abs(m.BoundBox.ZMin)<1e-6 and abs(m.BoundBox.ZMax)<1e-6,n
                continue
            assert m.isSolid(),n
            if kind=='print_STL_sha256':
                assert abs(m.BoundBox.ZMin)<1e-4
                assert abs(abs(m.Volume)-vol(shape))<max(.1,vol(shape)*.001)
                checks[n]['print_size_xyz_mm']=[m.BoundBox.XLength,m.BoundBox.YLength,m.BoundBox.ZLength]
names=list(r['exports']);pairs=0
for a,b in itertools.combinations(names,2):
    assert vol(sh(a).common(sh(b)))<1e-5,(a,b);pairs+=1
assert vol(sh('FixtureOuterSeal').cut(sh('FixtureOuterGland')))<1e-5,'Outer fixture seal not contained'
free_outer=2*math.pi**2*4.75*.75**2
assert abs(vol(sh('FixtureOuterSeal'))-free_outer)<1e-5
post=sh('ContactPost');assert abs(post.BoundBox.YMin+2.3)<1e-6
assert abs(sh('ContactInnerSeal').BoundBox.YMax)<1e-6
assert abs(sh('ContactNut').BoundBox.YMin-1.6)<1e-6
# A continuous clear water column connects the hose port to the contact face.
for radius,y,length in ((1.2,-28,13),(2.9,-15,12.6)):
    water=Part.makeCylinder(radius,length,A.Vector(0,y,0),A.Vector(0,1,0))
    assert vol(water.common(sh('ContactSealCup')))<1e-6,'Blocked water path'
assert abs(sh('ContactSealPlate').BoundBox.YLength-1.6)<1e-6
r['geometry_checks']={'valid_parts':len(checks),'static_pairs':pairs,'positive_intersections':[],
    'water_path_clear':True,'fixture_ring_volume_preserved':True,
    'scope':'Nominal saved geometry only; no seal force, deformation, tool, pressure capability or physical leak qualification'}
r['verified_parts']=checks;r['verifier_sha256']=sha(Path(__file__));(OUT/'review.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(r['geometry_checks']),flush=True)
