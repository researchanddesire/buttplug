"""Bound every elastic assembly intersection to the actual five catch heads."""
from pathlib import Path
import hashlib,json,sys
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
H=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();V=A.Vector
d=A.openDocument(str(H/'DeviceSeatingTrial.FCStd'));d.recompute()
heads=[Part.makeCylinder(1.701,.602,V(x,y,13.899))for x,y in[(-28,54),(28,54),(0,54),(-24,106.5),(24,106.5)]]
allowed=Part.makeCompound(heads);checks=[]
for p in[o for o in d.Objects if o.TypeId=='PartDesign::Body'and o.Name!='SeatLinerCoupon']:
 for lift in(0,.25,.5,1,2,5):
  s=p.Shape.copy();s.translate(V(0,0,lift));common=s.common(d.SeatLinerCoupon.Shape);excess=common.cut(allowed).Volume
  assert excess<1e-5,(p.Name,lift,excess)
  checks.append({'part':p.Name,'lift_Z_mm':lift,'catch_head_intersection_mm3':common.Volume,'outside_actual_head_regions_mm3':excess})
r={'native_sha256':sha(H/'DeviceSeatingTrial.FCStd'),'checker_sha256':sha(Path(__file__)),'bounded_lift_samples':checks,'actual_catch_head_region_mm':{'radius':1.701,'Z':[13.899,14.501]},'all_other_rigid_intersections_zero':True,'elastic_hole_passage_not_physically_validated':True}
(H/'catch-loading-checks.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS',len(checks),'boundedheadpassages')
