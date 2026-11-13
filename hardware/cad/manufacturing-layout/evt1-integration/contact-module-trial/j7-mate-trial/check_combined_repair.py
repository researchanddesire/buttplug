"""Disposable two-part placement repair, exact selected shapes/native pad outlines.

No electrical/native source mutation; the first mate trial remains preserved.
"""
from pathlib import Path
import sys,json,hashlib,re,importlib.util,math
R=Path(__file__).resolve().parents[6]
spec=importlib.util.spec_from_file_location('j7',R/'tools/build_evt1_single_flange_j7_loom.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
A=m.A;Part=m.Part;V=m.V;P=m.OUT
sha=m.sha
base=P/'SingleFlangeJ7MateTrial.FCStd';d=A.openDocument(str(base));d.recompute()
context={o.Name.removeprefix('Context_'):o for o in d.getObject('ImmutableAssemblyContext').Group}
source_sha=sha(base)
# Parse the actual native footprint pad shapes; no second live pcbnew BOARD.
def parse(text):
 stack=[[]]
 for t in re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^()\s]+',text):
  if t=='(':v=[];stack[-1].append(v);stack.append(v)
  elif t==')':stack.pop()
  else:stack[-1].append(json.loads(t) if t.startswith('"') else t)
 assert len(stack)==1;return stack[0][0]
def one(n,k):return next(v for v in n if isinstance(v,list) and v[0]==k)
pcb=m.R/'hardware/pcb/evt1/single-flange-study/single-flange-placement.kicad_pcb'
tree=parse(pcb.read_text());fps={}
for f in tree:
 if not isinstance(f,list) or not f or f[0]!='footprint':continue
 refs=[v for v in f if isinstance(v,list)and v[:2]==['fp_text','reference']]
 if refs:fps[refs[0][2]]=f

def padshapes(ref,x,z):
 f=fps[ref];at=one(f,'at');assert len(at)==3 or abs(float(at[3]))<1e-9
 result=[]
 for pad in f:
  if not isinstance(pad,list)or pad[0]!='pad':continue
  assert pad[3]=='roundrect'
  u,v=map(float,one(pad,'at')[1:3]);w,h=map(float,one(pad,'size')[1:]);rr=float(one(pad,'roundrect_rratio')[1])*min(w,h)
  # Native local pad Y-down becomes negative product Z. Quarter-circle
  # corners retain the actual pad radius rather than a rectangular proxy.
  xx,zz=x+u,z-v;y=-25.952
  a=Part.makeBox(w-2*rr,.10,h,V(xx-w/2+rr,y,zz-h/2))
  a=a.fuse(Part.makeBox(w,.10,h-2*rr,V(xx-w/2,y,zz-h/2+rr)))
  for sx in (-1,1):
   for sz in (-1,1):a=a.fuse(Part.makeCylinder(rr,.10,V(xx+sx*(w/2-rr),y,zz+sz*(h/2-rr)),V(0,1,0)))
  result.append((pad[1],a.removeSplitter()))
 return result

def shift_context(ref,dx,dz):
 o=context['Actual_'+ref+'_Solid0'];o.Placement.Base+=V(dx,0,dz);return o.Shape.copy()
# Parent's exact requested candidate; x6.3 is a further bounded alternative.
u75=shift_context('U75',7.3,5);u71=shift_context('U71',0,-1)
max71=Part.makeBox(1.05,.65,1.5,V(-1-.525,-25.952,-7-.75))
shapes={n:o.Shape.copy()for n,o in context.items()};bounds={n:m.bound(s)for n,s in shapes.items()}
for ref,x,z in (('U71',-1,-7),('U75',6.3,9)):
 context['Actual_'+ref+'_Solid0'].addProperty('App::PropertyString','DisposableStudyPose')
 context['Actual_'+ref+'_Solid0'].DisposableStudyPose='Product XZ '+str([x,z])+'; original source unchanged'
# Source pack-disconnect reservation is still an envelope, not received/OEM
# geometry. Preserve it explicitly as an additional conservative constraint.
pack=json.loads((R/'hardware/pcb/evt1/pack-spec.json').read_text())['lead_exit']['product_mated_connector_bounds_mm']
shapes['RequestedBatteryPowerConnectorReservation']=m.box_bound(pack);bounds['RequestedBatteryPowerConnectorReservation']=pack

j7g=d.getObject('J7MatingAssembly');h=d.getObject('J7SHR10Housing')
mating=[h]+[d.getObject('J7Terminal'+str(i))for i in range(1,11)]
mate=Part.makeCompound([m.globalshape(o)for o in mating]);mb=m.bound(mate)
# Actual socket front -2.475 and stop/back +.525 in header-local v. The
# inserted body reaches v+.525, so +3.00 X withdraws its tip to socket front.
# Add .25 mm nominal separation before the board-normal leg. Published 5 mm
# housing and 6.25 mm assembly are the external dimensional cross-check.
poses=[]
for i in range(27):poses.append(('axial',3.25*i/26,0.))
for i in range(1,33):poses.append(('board_normal',3.25,8*i/32))
region=mb.copy();region[3]+=3.25;region[4]+=8
empty=[];proofs=[]
for n,s in shapes.items():
 if not m.bb_common(region,bounds[n]):empty.append(n);continue
 if n in ('RevisedContinuousSkin','ProposedRearHalf','ProposedFlangeTray','MetalBody','MotorThermistorCap','BodyInsulatingSleeve'):
  vol=m.box_bound(region).common(s).Volume
  proofs.append({'part':n,'common_mm3':vol})
  if vol<1e-7:empty.append(n)
# Thin tool-tip cross-section is primary Ideal-Tek 2AE.SA.0 1.50 x .13 mm.
# Eight mm extension is an access reservation, NOT its unpublished shank.
tips=[]
for side in (-1,1):
 zz=5.5 if side>0 else -5.63
 tips.append(Part.makeBox(1.5,8,.13,V(-4.25,-25.842,zz)))
tip=Part.makeCompound(tips);tb=m.bound(tip)
results=[]
for leg,dx,dy in poses:
 q=mate.copy();q.translate(V(dx,dy,0));qb=mb.copy();qb[0]+=dx;qb[3]+=dx;qb[1]+=dy;qb[4]+=dy
 t=tip.copy();t.translate(V(dx,dy,0));tbb=tb.copy();tbb[0]+=dx;tbb[3]+=dx;tbb[1]+=dy;tbb[4]+=dy
 clashes=[];tip_clashes=[]
 for n,s in shapes.items():
  if n.startswith('Actual_J7_'):continue
  if n not in empty and m.bb_common(qb,bounds[n]):
   v=q.common(s).Volume
   if v>1e-7:clashes.append({'part':n,'common_mm3':v})
  # The support inside the header is excluded only for mate geometry. Tool
  # tips stay at the lip ends, so the actual fixed header is also tested.
  if m.bb_common(tbb,bounds[n]):
   v=t.common(s).Volume
   if v>1e-7:tip_clashes.append({'part':n,'common_mm3':v})
 results.append({'leg':leg,'translation_XY_mm':[dx,dy],'clashes':clashes,'tip_section_access_clashes':tip_clashes})
 print('COMBINED_POSE',leg,dx,dy,clashes,tip_clashes,flush=True)

def testpart(q,exclude=()):
 qb=m.bound(q);bad=[]
 for n,s in shapes.items():
  if any(n.startswith(v)for v in exclude):continue
  if m.bb_common(qb,bounds[n]):
   v=q.common(s).Volume
   if v>1e-7:bad.append({'part':n,'common_mm3':v})
 return bad
parts=[]
for ref,x,z,actual,mx in (('U71',-1,-7,u71,max71),('U75',6.3,9,u75,m.maximum_st_sot236(6.3,9))):
 tests=[]
 for label,q in (('selected_native',actual),('manufacturer_max_material',mx)):
  tests.append({'geometry':label,'clashes':testpart(q,('Actual_'+ref+'_',)),
   'bounds_mm':m.bound(q),'Tray_distance_mm':q.distToShape(shapes['ProposedFlangeTray'])[0]})
 pads=padshapes(ref,x,z)
 pd=[{'pin':n,'Tray_common_mm3':q.common(shapes['ProposedFlangeTray']).Volume,
      'Tray_distance_mm':q.distToShape(shapes['ProposedFlangeTray'])[0],
      'bounds_mm':m.bound(q)}for n,q in pads]
 parts.append({'ref':ref,'product_XZ_mm':[x,z],'model_checks':tests,'native_pad_checks':pd})
# Parent's .3 mm extra X alternative increases the pad-to-post reserve.
mx=m.maximum_st_sot236(6.3,9);pads=padshapes('U75',6.3,9)
extra={'U75_XZ_mm':[6.3,9],'manufacturer_max_clashes':testpart(mx,('Actual_U75_',)),
       'max_Tray_distance_mm':mx.distToShape(shapes['ProposedFlangeTray'])[0],
       'native_pad_min_Tray_distance_mm':min(q.distToShape(shapes['ProposedFlangeTray'])[0]for n,q in pads),
       'native_pad_Tray_common_mm3':sum(q.common(shapes['ProposedFlangeTray']).Volume for n,q in pads)}
# Park the housing at the outer end to make both movement legs inspectable;
# its saved assembly placement remains mated. Separate centreline annotations
# record the actual path without introducing an installed product component.
g=d.addObject('App::DocumentObjectGroup','InspectionPaths')
for name,points in [('J7InsertionPath',[V(0,0,0),V(3.25,0,0),V(3.25,8,0)])]:
 o=d.addObject('PartDesign::Feature',name);o.Shape=Part.makePolygon(points);g.addObject(o)
d.recompute();out=P/'CombinedClearanceTrial.FCStd';d.saveAs(str(out))
r={'status':'Disposable combined placement study; no ECAD/source promotion',
 'source_mate_trial_sha256':source_sha,'source_mechanical_sha256':m.NATIVE_SHA,'source_PCB_sha256':sha(pcb),
 'native_sha256':sha(out),'checker_sha256':sha(Path(__file__)),'repair_positions_XZ_mm':{'U75':[6.3,9],'U71':[-1,-7]},
 'disengagement':{'nominal_inserted_depth_mm':3.,'separation_before_normal_mm':.25,'straight_mm':3.25,'normal_mm':8.,
 'derivation':'Actual selected header socket front local v-2.475/back+.525 and public housing5 / assembly6.25 mm. Receiver tolerances and actual mating marks still need incoming check.'},
 'empty_region_proofs':{'bounds_mm':region,'proofs':proofs},'sampled_mating_poses':results,'parts':parts,
 'extra_U75_margin_alternative':extra,'tool':{'candidate':'Ideal-Tek2AE.SA.0','source':'https://www.ideal-tek.com/public/upload/PDS/2AE.SA.0.IT.pdf',
 'tip_section_mm':[1.5,.13],'access_extension_mm':8.,'scope':'Tip cross-section/access reservation only. Whole shank, jaw opening, grip force and safe handling require received tool/connector trial; no full-tool qualification.'},
 'pads_scope':'Exact source native roundrect XY outlines with .10 mm outward solder/inspection keepout; not measured solder shape.',
 'manufacturer_max_sources':{'U75':'https://www.st.com/resource/en/datasheet/usblc6-2.pdf p12, DS4260 Rev7',
 'U71':'https://www.ti.com/lit/ds/symlink/tps3422.pdf DRY0006A p26:1.05x1.50x.60, plus .05mm solder seating allowance'},
 'physical_validation':False}
(P/'combined-review.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'native':str(out),'bad_mating_poses':sum(bool(p['clashes'])for p in results),'bad_tip_poses':sum(bool(p['tip_section_access_clashes'])for p in results),'parts':parts,'extra':extra},indent=2),flush=True)
