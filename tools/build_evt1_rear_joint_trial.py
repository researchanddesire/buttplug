"""Selected thin nut and a two-jaw axial driver; separate inert trial.

The product metal, flange source and human BOM are immutable. Run with
FreeCAD Python. Cosmetic threads/chamfers and physical fastening strength
are not inferred from this nominal geometry.
"""
from pathlib import Path
import hashlib, json, math, sys
native_lib=Path('/Applications/FreeCAD.app/Contents/Resources/lib')
if native_lib.is_dir():sys.path.insert(0,str(native_lib))
import FreeCAD as App
import Part, Sketcher

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/cad/manufacturing-layout/evt1-integration/rear-joint-trial'
SOURCE=ROOT/'hardware/cad/manufacturing-layout/evt1-integration/EVT1Product.FCStd'
TRIAL=ROOT/'hardware/cad/manufacturing-layout/evt1-integration/contact-module-trial/single-board/archive/frozen-39-pre-mate-clearance/SingleFlangeBoardTrial.FCStd'
SOURCE_SHA='fe22bca30660e3cbf7244689a06a6230ae7b93f18c64489593fdc5829d02553f'
TRIAL_SHA='5c348efe59825bde7b0c91fa99e66e62f69fff4aa421e58338a5896c09de2b4f'
V=App.Vector
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def bounds(s):
 b=s.optimalBoundingBox(False,False)
 return [getattr(b,k)for k in('XMin','YMin','ZMin','XMax','YMax','ZMax')]

def cylinder(r,a,b):return Part.makeCylinder(r,b-a,V(0,a,0),V(0,1,0))

def hexagon(af,a,b):
 r=af/math.sqrt(3)
 ps=[V(r*math.cos(math.radians(30+60*i)),a,r*math.sin(math.radians(30+60*i)))for i in range(6)]
 return Part.Face(Part.makePolygon(ps+[ps[0]])).extrude(V(0,b-a,0))

def note(o,k,v):o.addProperty('App::PropertyString',k,'Engineering');setattr(o,k,v)

def extrusion(body,name,tool,subtract=False):
 """Native locked XZ profile with Pad/Pocket; supplied tool lies along Y."""
 bb=tool.optimalBoundingBox(False,False);a,b=bb.YMin,bb.YMax
 sk=body.newObject('Sketcher::SketchObject',name+'Profile')
 sk.Placement=App.Placement(V(0,a,0),App.Rotation(V(1,0,0),90))
 for solid in tool.Solids:
  fs=[f for f in solid.Faces if f.BoundBox.YLength<1e-6 and abs(f.BoundBox.YMin-a)<1e-6]
  assert len(fs)==1,(name,len(fs))
  for w in fs[0].Wires:
   for e in w.Edges:
    lo,hi=e.FirstParameter,e.LastParameter
    p=lambda t:V(e.valueAt(t).x,e.valueAt(t).z,0)
    if isinstance(e.Curve,Part.Line):g=Part.LineSegment(p(lo),p(hi))
    elif isinstance(e.Curve,Part.Circle):
     g=Part.Circle(V(e.Curve.Center.x,e.Curve.Center.z,0),V(0,0,1),e.Curve.Radius)if abs(hi-lo-2*math.pi)<1e-6 else Part.Arc(p(lo),p((lo+hi)/2),p(hi))
    else:raise TypeError(type(e.Curve))
    n=sk.addGeometry(g,False);sk.addConstraint(Sketcher.Constraint('Block',n))
 body.Document.recompute();assert sk.FullyConstrained
 f=body.newObject('PartDesign::Pocket'if subtract else'PartDesign::Pad',name)
 f.Profile=sk;f.Length=b-a;f.Reversed=not subtract
 body.Document.recompute();assert f.Shape.isValid()and len(f.Shape.Solids)==1,name
 sk.Visibility=False;return f

def main():
 assert sha(SOURCE)==SOURCE_SHA and sha(TRIAL)==TRIAL_SHA,'Source changed: explicitly revalidate trial'
 OUT.mkdir(parents=True,exist_ok=True);d=App.newDocument('RearJointServiceTrial')
 parts=d.addObject('App::Part','SelectedParts');context=d.addObject('App::Part','ImmutableContext')
 source=App.openDocument(str(SOURCE));trial=App.openDocument(str(TRIAL))
 ctx={}
 for key,o in [('MetalBody',source.MetalBody),('Tray',trial.ProposedFlangeTray),('PackGrowth',source.PackGrowthAllowance)]:
  b=d.addObject('PartDesign::Body','Source'+key);context.addObject(b)
  f=b.newObject('PartDesign::Feature','Source'+key+'Snapshot');f.Shape=o.Shape.copy()
  note(b,'SourceFile',str(Path(o.Document.FileName).relative_to(ROOT)));note(b,'SourceSHA256',sha(o.Document.FileName));ctx[key]=b
 nut=d.addObject('PartDesign::Body','IFME10028');parts.addObject(nut)
 extrusion(nut,'PublishedHex24AF',hexagon(24,-14,-10))
 extrusion(nut,'ThreadMinorPilot',cylinder(8.5,-14.01,-9.99),True)
 note(nut,'ManufacturerPartNumber','ifm E10028; pack of2; stainless316Ti/1.4571')
 note(nut,'SourceURL','https://www.ifm.com/gb/en/product/E10028')
 note(nut,'ModelBasis','Published24AF x4 andM18x1. Drawing also labels27 across corners without tolerances. Unspecified corner/chamfer detail is conservatively modeled as the full regular24AF hex (27.7128 corner span); no27mm maximum credit. Thread pilot only, no thread flanks or strength rating.')
 driver=d.addObject('PartDesign::Body','TwoJawDriver');parts.addObject(driver)
 extrusion(driver,'DriverHub',cylinder(14.1,-34,-29))
 fingers=Part.makeCompound([Part.makeBox(1.975,18.6,2.5,V(x,-29,-1.25))for x in(-14.1,12.125)]).common(cylinder(14.1,-29,-10.4))
 extrusion(driver,'TwoAxialJaws',fingers)
 extrusion(driver,'WrenchShank10AF',Part.makeBox(10,20.01,10,V(-5,-54,-5)))
 note(driver,'Manufacturing','Custom machined steel two-jaw trial tool;18.6mm arms,2.5mm tangential width,24.25AF opening,OD28.2 outer circular limit.10AF shank accepts a workshop drive. Edge breaks/root fillets, material/heat treatment, actual engagement and proof torque remain to qualify; no print/strength release.')
 note(driver,'Scope','Opposing jaws use whichever nut-flat pair lies within30deg of productX. Rear hub stays behind the Tray; jaws pass the integral contact supports before electronics/pack/loom.0.4mm tip setback from bare nut front; prospective0.3mm washer leaves0.1mm. Nut locking is not implemented.')
 d.recompute();d.saveAs(str(OUT/'RearJointServiceTrial.FCStd'))
 shape=driver.Shape;rows=[]
 # Tool is used before rear half, PCB, pack and loom. The real pack is
 # intentionally absent from this loading path, and checked separately.
 paths=[('axial_two_jaw',a,o)for a in range(-30,31,5)for o in(-30,-20,-12,-8,-6,-4,-3,-2,-1,-.5,0)]
 for phase,angle,offset in paths:
   s=shape.copy();s.rotate(V(),V(0,1,0),angle);s.translate(V(0,offset,0))
   hits=[]
   fixed=[(name,ctx[name].Shape)for name in('MetalBody','Tray')]
   n=nut.Shape.copy();n.rotate(V(),V(0,1,0),angle);fixed.append(('AlignedNut',n))
   for name,b in fixed:
    if s.BoundBox.intersect(b.BoundBox):
     v=s.common(b).Volume
     if v>1e-5:hits.append({'part':name,'volume_mm3':v})
   rows.append({'phase':phase,'angle_deg':angle,'withdrawal_Y_mm':offset,'intersections':hits})
 nut_checks=[]
 for angle in range(0,61):
  s=nut.Shape.copy();s.rotate(V(),V(0,1,0),angle)
  nut_checks.append({'angle_deg':angle,'Tray_common_mm3':s.common(ctx['Tray'].Shape).Volume})
 report={'status':'Separate selected-nut/service-tool nominal trial; nut locking OPEN',
  'source_product_sha256':SOURCE_SHA,'source_mechanical_sha256':TRIAL_SHA,
  'builder_sha256':sha(__file__),'native_sha256':sha(OUT/'RearJointServiceTrial.FCStd'),
  'nut':{'mpn':'ifmE10028','AF_mm':24,'thickness_mm':4,'thread':'M18x1','drawing_corner_span_mm':27,'clearance_corner_span_mm':24/math.cos(math.pi/6),'manufacturer_tolerances_unspecified':True,'pack_quantity':2,'thread_gaging_strength_and_actual_chamfers_qualified':False},
  'tool':{'finger_OD_limit_mm':28.2,'hub_OD_mm':28.2,'AF_mm':24.25,'jaw_width_mm':2.5,'jaw_length_mm':18.6,'body_bounds_mm':bounds(shape),'maximum_usable_torque_Nm':None,'physical_qualification':False,'sequence':'Choose opposing nut flats within30deg of productX; align jaws before axial insertion. Hub remains outside Tray.'},
  'tool_loading':rows,'nut_rotation':nut_checks,
  'pass':not any(x['intersections']for x in rows)and all(x['Tray_common_mm3']<1e-5 for x in nut_checks),
  'physical_validation':False,'full_product_order_ready':False}
 (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n')
 for b in(nut,driver):Part.export([b],str(OUT/(b.Name+'.step')))
 print(json.dumps({'pass':report['pass'],'tool_poses':len(rows),'nut_poses':len(nut_checks)},indent=2),flush=True)
 App.closeDocument(source.Name);App.closeDocument(trial.Name);App.closeDocument(d.Name)
if __name__=='__main__':main()
