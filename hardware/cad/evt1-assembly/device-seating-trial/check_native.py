"""Cold saved-native checks against immutable dock/device source geometry."""
from pathlib import Path
import hashlib,json,math,runpy,sys
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];V=App.Vector
M=runpy.run_path(str(ROOT/'tools/build_evt1_dock_device_seats.py'));sha=M['sha'];report=json.loads((HERE/'review.json').read_text())
assert report['builder_sha256']==sha(ROOT/'tools/build_evt1_dock_device_seats.py')
assert sha(M['HOST'])==M['HOST_SHA']and sha(M['PRODUCT'])==M['PRODUCT_SHA']
d=App.openDocument(str(HERE/'DeviceSeatingTrial.FCStd'));d.recompute()
bodies=[o for o in d.Objects if o.TypeId=='PartDesign::Body'];soft=[o for o in bodies if o!=d.SeatLinerCoupon]
for b in bodies:assert b.Shape.isValid()and len(b.Shape.Solids)==1,b.Name
profiles=[o for o in d.Objects if o.TypeId=='Sketcher::SketchObject']
assert all(s.FullyConstrained for s in profiles)
print('Savednativevalid',len(bodies),flush=True)
actual=d.ActualDevice.Shape;parts=[(o.Name,o.Shape)for o in d.ActualDevice.Group]
assert len(parts)==9
source_doc=d.ActualDeviceMetalBody.LinkedObject.Document
# Correct exterior frame; inner intersections are deliberately not selected.
surface=[]
for x,y in M['PADS']:
 s=d.ActualDeviceContinuousSkin.Shape.section(Part.makeLine(V(x,y,0),V(x,y,60)))
 zs=sorted(v.Point.z for v in s.Vertexes);assert abs(zs[0]-13)<1e-7
 surface.append({'xy_mm':[x,y],'actual_outer_Z_mm':zs[0],'other_ray_surfaces_Z_mm':zs[1:]})
contacts=[]
for role in M['ROLES'][3:7]:
 b=d.getObject('ActualDevice'+role).Shape.optimalBoundingBox(False,False)
 assert abs(b.YMin-23.2)<1e-5 and abs((b.ZMin+b.ZMax)/2-43.5)<1e-5
 contacts.append({'role':role,'face_Y_mm':b.YMin,'centre_Z_mm':(b.ZMin+b.ZMax)/2})
# Purchased/native mechanical source conservation, host cache vs source pose.
host=App.openDocument(str(M['HOST']));parity=[]
for role in M['ROLES'][:7]:
 a=host.getObject('Device'+role).Shape;c=d.getObject('ActualDevice'+role).Shape
 extra=a.cut(c).Volume+c.cut(a).Volume
 assert extra<1e-5,(role,extra);parity.append({'role':role,'symmetric_difference_mm3':extra})
print('Sourceparitypassed',len(parity),flush=True)
# In-memory derivative of actual selected liner, with native edit history.
t=App.newDocument('ActualLinerSeatCheck');liner=t.addObject('PartDesign::Body','ActualLinerDerivative');M['feature'](liner,'FrozenActualLiner',host.LowerChamber.Shape.copy())
M['apply_liner_reliefs'](liner);M['apply_liner_saddle'](liner)
modified_liner=liner.Shape.copy();assert modified_liner.isValid()
# All new softgoods vs actual host components and adjusted actual liner.
base=[]
for o in host.BaseModule.Group:
 if o.Name in('DeviceAssembly','LowerChamberInstance')or not hasattr(o,'Shape')or o.Shape.isNull():continue
 base.append((o.Name,o.Shape.copy()))
base.append(('ActualModifiedLiner',modified_liner))
# Independent lid opening transform; no mutation/recompute of the host.
open_pose=App.Placement(V(),App.Rotation(V(1,0,0),-110),V(0,164.4,40.15))
for o in host.LidModule.Group:
 if not hasattr(o,'Shape')or o.Shape.isNull():continue
 s=o.Shape.copy();s.Placement=open_pose.multiply(s.Placement);base.append((o.Name,s))
def clash(a,other):
 if not a.BoundBox.intersect(other.BoundBox):return 0
 return a.common(other).Volume
pairs=[]
for i,a in enumerate(soft):
 for b in soft[i+1:]:
  v=clash(a.Shape,b.Shape);assert v<1e-5,(a.Name,b.Name,v)
  pairs.append({'pair':[a.Name,b.Name],'mm3':v})
 for name,s in base:
  if not a.Shape.BoundBox.intersect(s.BoundBox):continue
  v=clash(a.Shape,s);assert v<1e-5,(a.Name,name,v)
  pairs.append({'pair':[a.Name,name],'mm3':v})
print('Staticpairs',len(pairs),flush=True)
# The source-derived coupon itself must not intrude into any device surface.
for name,s in parts:
 v=clash(d.SeatLinerCoupon.Shape,s);assert v<1e-5,('coupon',name,v)
# New support surfaces, actual revised liner and all frozen host obstacles.
obstacles=base+[(o.Name,o.Shape)for o in soft];poses=[]
for phase,offsets in [('lower',[(3,2*i)for i in range(36)]),('mate',[(.25*i,0)for i in range(13)])]:
 for y,z in offsets:
  moved=actual.copy();moved.translate(V(0,y,z));eligible=0;hits=[]
  for name,s in obstacles:
   if not moved.BoundBox.intersect(s.BoundBox):continue
   eligible+=1;v=clash(moved,s)
   if v>1e-4:hits.append({'name':name,'mm3':v})
  assert not hits,(phase,y,z,hits)
  poses.append({'phase':phase,'offset_Y_mm':y,'lift_Z_mm':z,'eligible_actual_BRep_pairs':eligible,'intersections':hits})
print('49deviceposespassed',len(poses),flush=True)
# Coupon loading: put loose layers over the integral catches and lower from
# above. Intentional elastic closed-hole silicone assembly is not rigid BOP.
loading=[]
for p in soft:
 for z in(0,.25,.5,1,2,5):
  s=p.Shape.copy();s.translate(V(0,0,z));vol=clash(s,d.SeatLinerCoupon.Shape)
  loading.append({'part':p.Name,'lift_Z_mm':z,'intersection_mm3':vol,'catch_head_flex_assembly_required':vol>1e-5})
 # Final received pose must be clash-free; no rigid claim for passing its hole
 # over larger head. PET has explicit slit, silicone needs controlled stretch.
 assert loading[-6]['intersection_mm3']<1e-5,p.Name
# Nominal sheet and printed land arithmetic across published free-sheetlimits.
stack=[]
for sheet in(.203,.2284,.2484,.279,.305):
 n=min(range(5),key=lambda n:abs(12.65+n*M['PET']+sheet-13))
 top=12.65+n*M['PET']+sheet;assert abs(top-13)<=.0254+1e-9
 stack.append({'trial_loaded_sheet_mm':sheet,'PET_layers':n,'result_Z_mm':top,'quantization_error_mm':top-13,'this_is_not_a_modulus_prediction':True})
# Geometry sections from saved real parts, not a conceptual illustration.
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="660" viewBox="0 0 1200 660">','<rect width="1200" height="660" fill="#faf9f5"/>','<text x="20" y="28" font-family="Arial" font-size="18">Actual source-derived device seating · no physical force or UV-cleaning result</text>']
shapes=[(d.SeatLinerCoupon.Shape,'#b6a882'),(actual,'#546c62')]+[(p.Shape,'#6ba9c3'if'PET'in p.Name else'#8a679d')for p in soft]
for i,(title,axis,coord,center,scale,zc)in enumerate([('Three flange pads / Y30','xz',30,0,10,11),('Narrow maximum-radius saddle / Y106.5','xz',106.5,0,17,11),('Skin / tail / keeper / X−28','yz',-28,39,14,11)]):
 x0=20+400*i;svg.append(f'<text x="{x0}" y="63" font-family="Arial" font-size="13">{title}</text>')
 if axis=='xz':pts=[V(center-50,coord,10),V(center+50,coord,10),V(center+50,coord,17),V(center-50,coord,17)]
 else:pts=[V(coord,20,10),V(coord,58,10),V(coord,58,17),V(coord,20,17)]
 plane=Part.Face(Part.makePolygon(pts+[pts[0]]))
 for s,col in shapes:
  for e in s.section(plane).Edges:
   coords=[]
   for p in e.discretize(Deflection=.015):
    xx=p.x-center if axis=='xz'else p.y-center
    coords.append(f'{x0+190+xx*scale:.3f},{280-(p.z-zc)*scale:.3f}')
   svg.append(f'<polyline points="{" ".join(coords)}" fill="none" stroke="{col}" stroke-width="1.3"/>')
svg.extend(['<text x="20" y="340" font-family="Arial" font-size="13">Cream: actual printable floor/support · green: purchased/native device · blue: registered PET · purple: solid silicone sheet</text>',
'<text x="20" y="366" font-family="Arial" font-size="13">Pad areas and tails shadow device surfaces. Transparent appearance gives no275nm transmission credit. Remove and clean contact surfaces separately.</text>'])
# Top plan of actual new native geometry with exact line work.
for s,col in shapes[:1]+shapes[2:]:
 for e in s.Edges:
  pp=e.discretize(Deflection=.08);coords=' '.join(f'{600+p.x*4:.2f},{605-(p.y-23)*2.7:.2f}'for p in pp)
  svg.append(f'<polyline points="{coords}" fill="none" stroke="{col}" stroke-width=".7"/>')
svg.extend(['<text x="20" y="620" font-family="Arial" font-size="13">Plan: three6×4mm pads, narrow7×4mm body band; tails end at accessible integral catches, no loose hardware or adhesive.</text>','</svg>']);(HERE/'native-sections.svg').write_text('\n'.join(svg)+'\n')
result={'native_sha256':sha(HERE/'DeviceSeatingTrial.FCStd'),'builder_sha256':sha(ROOT/'tools/build_evt1_dock_device_seats.py'),'checker_sha256':sha(Path(__file__)),'host_sha256':sha(M['HOST']),'device_sha256':sha(M['PRODUCT']),'valid_native_bodies':len(bodies),'fully_constrained_profiles':len(profiles),'device_native_links':len(parts),'cold_host_source_pose_conservation':parity,'actual_surface_samples':surface,'contact_frame':contacts,'static_eligible_pairs':pairs,'device_poses':poses,'softgoods_catch_loading_samples':loading,'received_sheet_stack_arithmetic':stack,'actual_modified_liner_volume_mm3':modified_liner.Volume,'source_master_saved_or_edited':False,'physical_validation':False,'elastic_tail_assembly_validated':False}
(HERE/'native-readback.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'native_bodies':len(bodies),'profiles':len(profiles),'device_links':len(parts),'static_pairs':len(pairs),'device_poses':len(poses),'seat_loading_samples':len(loading),'stack_trials':len(stack)}))
