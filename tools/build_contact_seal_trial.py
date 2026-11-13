"""Single-contact inert hydrostatic fixture; FreeCAD Python, no electronics.

Uses the saved dock's actual post/inner face-seal geometry. This fixture is
not a product part, molding tool, pressure vessel or finished wet qualification.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
import MeshPart

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hardware/cad/manufacturing-layout/charging-dock'
OUT=SOURCE/'contact-seal-trial';OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((SOURCE/'review.json').read_text())
assert sha(SOURCE/'ChargingDock.FCStd')==r['native_sha256']
S=A.openDocument(str(SOURCE/'ChargingDock.FCStd'))
D=A.newDocument('ContactSealTrial');D.Label='Inert single-contact face-seal hydrostatic fixture'
groups={n:D.addObject('App::DocumentObjectGroup',n) for n in ('FixtureParts','ContactReferences','SoftGoods','Construction')}
roles={}
def feat(name,shape,group):
    assert shape.isValid() and len(shape.Solids)==1,name
    o=D.addObject('PartDesign::Feature',name);o.Shape=shape;groups[group].addObject(o);roles[name]=o;return o
def cyl(radius,y,length,x=0,z=0):return Part.makeCylinder(radius,length,A.Vector(x,y,z),A.Vector(0,1,0))
def bounds(s):
    b=s.BoundBox;return [getattr(b,n) for n in ('XMin','YMin','ZMin','XMax','YMax','ZMax')]

spec=r['contact_seal'];hole=spec['gland']['bore_diameter_mm']
plate=Part.makeBox(24,1.6,24,A.Vector(-12,0,-12)).cut(cyl(hole/2,-.1,1.8))
cup=Part.makeBox(24,18,24,A.Vector(-12,-18,-12)).cut(cyl(3,-15,15.1))
gland=cyl(6,-1.1,1.11).cut(cyl(3.9,-1.11,1.13))
cup=cup.cut(gland)
stem=cyl(2.2,-28,10).fuse(Part.makeCone(2,2.5,2,A.Vector(0,-28,0),A.Vector(0,1,0))).fuse(
    Part.makeCone(2.5,2.2,2,A.Vector(0,-26,0),A.Vector(0,1,0)))
cup=cup.fuse(stem).cut(cyl(1.25,-28.1,13.2)).removeSplitter()
for x in (-9,9):
    for z in (-9,9):
        plate=plate.cut(cyl(1.65,-.1,1.8,x,z))
        cup=cup.cut(cyl(1.65,-18.1,18.2,x,z))
feat('ContactSealPlate',plate,'FixtureParts');feat('ContactSealCup',cup,'FixtureParts')
for source,name,group in (
        ('Target_GND','ContactPost','ContactReferences'),
        ('TargetNut_GND','ContactNut','ContactReferences'),
        ('TargetSeal_GND','ContactInnerSeal','SoftGoods')):
    o=S.getObject(r['native_roles'].get(source,source));assert o is not None,source
    shape=o.Shape.copy();shape.translate(A.Vector(38,24.5,-11.5));feat(name,shape,group)
# A separate8x1.5 fixture O-ring keeps test water in the cup. It is not a
# product seal. Same volume-preserving display convention as the inner seal.
rr,b=4.95,.55;a=4.75*.75**2/(rr*b)
edge=Part.Ellipse(A.Vector(rr+a,-b,0),A.Vector(rr,0,0),A.Vector(rr,-b,0)).toShape()
outer=Part.Face(Part.Wire([edge])).revolve(A.Vector(),A.Vector(0,1,0),360)
feat('FixtureOuterSeal',outer,'SoftGoods')
feat('FixtureOuterGland',gland,'Construction')
D.recompute();native=OUT/'ContactSealTrial.FCStd';D.saveAs(str(native))
exports={}
for name,o in roles.items():
    if name=='FixtureOuterGland':continue
    step=OUT/(name+'.step');o.Shape.exportStep(str(step))
    view=OUT/(name+'-view.stl');mesh=MeshPart.meshFromShape(Shape=o.Shape,LinearDeflection=.025,AngularDeflection=.15,Relative=False)
    assert mesh.isSolid(),name;mesh.write(str(view))
    exports[name]={'STEP_sha256':sha(step),'view_STL_sha256':sha(view)}
    wires=o.Shape.slice(A.Vector(0,0,1),0)
    section=Part.makeFace(wires,'Part::FaceMakerBullseye');faces=[]
    for f in section.Faces:
        f=f.copy()
        if f.normalAt(0,0).z<0:f.reverse()
        faces.append(f)
    path=OUT/(name+'-section-view.stl')
    MeshPart.meshFromShape(Shape=Part.makeCompound(faces),LinearDeflection=.01,AngularDeflection=.1,Relative=False).write(str(path))
    exports[name]['section_view_STL_sha256']=sha(path)
    if name in ('ContactSealPlate','ContactSealCup'):
        shape=o.Shape.copy();shape.rotate(A.Vector(),A.Vector(1,0,0),90 if name=='ContactSealPlate' else -90)
        bb=shape.BoundBox;shape.translate(A.Vector(-bb.XMin,-bb.YMin,-bb.ZMin))
        mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.025,AngularDeflection=.15,Relative=False)
        assert mesh.isSolid();path=OUT/(name+'.stl');mesh.write(str(path));exports[name]['print_STL_sha256']=sha(path)
report={'scope':'Inert single-contact hydrostatic fixture; fit prints only until actual counterface finish/material and seals are qualified',
    'native_sha256':sha(native),'builder_sha256':sha(Path(__file__)),
    'source_dock_native_sha256':r['native_sha256'],'contact_seal_spec_sha256':r['contact_seal_spec_sha256'],
    'exports':exports,'bounds':{n:bounds(o.Shape) for n,o in roles.items()},
    'frame':'Contact centerX/Z0, metal bearing/plate outsideY0; original GND post translated(38,24.5,-11.5). Water cup extends-Y; exposed nut/tail+Y.',
    'print_parts':['ContactSealPlate','ContactSealCup'],
    'hardware':{'M3x30_bolt':4,'M3_nut':4,'M3_washer':8,'custom_contact_post':1,'M2_contact_nut':1,'HANSA_FLEX_OR2_0_5_trial_inner_seal':1,'HANSA_FLEX_OR8_1_5_fixture_outer_seal':1,'4mm_ID_6mm_OD_silicone_hose_1_2m':1},
    'fixture_outer_seal_source':'https://shop.hansa-flex.de/en_GB/sealing-equipment/static-seals/o-rings/nbr-o-rings/or-8-1-5/p/OR8-1-5',
    'test':'Open water-column hydrostatic screen only. No compressed air, electronics, battery or casting in this fixture. Contact tail/nut stay open for dye/witness inspection. Cup perimeter leaks are separately visible and invalidate a run.',
    'limits':'No physical print/assembly/leak result. Printed plate roughness is not a qualified product sealing face. Fixture outer-ring and hose fits, clamp loads and test duration/head are trial settings, not an IP rating or complete wet/cleaning/material validation.'}
(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'native':str(native),'exports':len(exports),'print_parts':report['print_parts']}),flush=True)
