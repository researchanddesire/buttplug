"""Single flange PCB mechanical feasibility; source electrical artwork unchanged.

Body PCB remains. Actual requested pack/growth is linked; RF/PCB routing and
silicone button force/seals are acceptance work, never inferred from CAD.
"""
from pathlib import Path
import hashlib,json,math,sys
from types import SimpleNamespace
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part,Sketcher
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/cad/manufacturing-layout/evt1-integration/contact-module-trial/single-board'
SOURCE=OUT.parent.parent/'EVT1Product.FCStd'
SOURCE_SHA='fe22bca30660e3cbf7244689a06a6230ae7b93f18c64489593fdc5829d02553f'
PCB=ROOT/'hardware/pcb/evt1/flange/flange-evt1.kicad_pcb'
PCB_SHA='adafe46de7b49daa22fa35dc287eec4d7b18b601016ea3dcd0380f36db6c6e9e'
V=App.Vector
F=-26.952;B=-25.952;FACE=-30.;REAR=-28.7;INNER=-27.2;SKIN=-29.7
XS=(-16.,-10.,-4.,2.);ZC=10.
NETS=('GND','USB_DM_CONTACT','USB_DP_CONTACT','DOCK_5V')
MOUNTS=((-30,-10),(-38,10),(38,-10),(38,10))
BUTTONS=((-17,0),(-9,0))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def box(a,b):return Part.makeBox(b[0]-a[0],b[1]-a[1],b[2]-a[2],V(*a))
def fuse(ss):
 s=ss[0]
 for x in ss[1:]:s=s.fuse(x)
 return s.removeSplitter()
def cyl(r,y0,y1,x,z):return Part.makeCylinder(r,y1-y0,V(x,y0,z),V(0,1,0))
def cut(s,ts):
 for t in ts:s=s.cut(t)
 return s.removeSplitter()
_FIXED_BOUNDS={}
_LAST_A=None
def bound_values(v):return SimpleNamespace(**dict(zip(("XMin","YMin","ZMin","XMax","YMax","ZMax"),v)))
def volume_common(a,b,a_bounds=None,b_bounds=None):
 global _LAST_A
 # Cache exact bounds only after topological+location identity checks.
 if a_bounds is not None:aa=bound_values(a_bounds)
 elif _LAST_A and a.isSame(_LAST_A[0]):aa=_LAST_A[1]
 else:aa=a.optimalBoundingBox(False,False);_LAST_A=(a,aa)
 key=b.hashCode();bucket=_FIXED_BOUNDS.setdefault(key,[])
 bb=bound_values(b_bounds)if b_bounds is not None else next((bounds for old,bounds in bucket if b.isSame(old)),None)
 if bb is None:bb=b.optimalBoundingBox(False,False);bucket.append((b,bb))
 if any(getattr(aa,c+'Max')<=getattr(bb,c+'Min')+1e-8 or getattr(bb,c+'Max')<=getattr(aa,c+'Min')+1e-8 for c in('X','Y','Z')):return 0.
 if a.distToShape(b)[0]>1e-6:return 0.
 return a.common(b).Volume
def bnd(s):
 b=s.optimalBoundingBox(False,False);return[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]
def body(d,name,s,col,note=''):
 if name=='RevisedContinuousSkin' and len(s.Solids)!=1:
  Path('/private/tmp/compass-contact-module/skin-debug.json').write_text(json.dumps([{'volume':t.Volume,'bounds':bnd(t)}for t in s.Solids],indent=2))
 assert s.isValid()and len(s.Solids)==1,(name,len(s.Solids))
 b=d.addObject('PartDesign::Body',name);o=b.newObject('PartDesign::Feature',name+'Geometry');o.Shape=s;b.Tip=o
 if note:o.addProperty('App::PropertyString','EngineeringNote');o.EngineeringNote=note
 if b.ViewObject:b.ViewObject.ShapeColor=col
 return b

def native_y(b,name,tools,subtract=False):
 """Editable locked XZ sketch and a native Pad/Pocket along the Y direction."""
 joined=fuse(tools);lo=joined.BoundBox.YMin;hi=joined.BoundBox.YMax
 s=b.newObject('Sketcher::SketchObject',name+'Profile');s.Placement=App.Placement(V(0,lo if not subtract else hi,0),App.Rotation(V(1,0,0),90))
 for solid in joined.Solids:
  faces=[f for f in solid.Faces if f.BoundBox.YLength<1e-6 and abs(f.BoundBox.YMin-lo)<1e-6]
  assert len(faces)==1,(name,len(faces))
  for w in faces[0].Wires:
   for e in w.Edges:
    a,c=e.FirstParameter,e.LastParameter;p=lambda t:V(e.valueAt(t).x,e.valueAt(t).z,0)
    if isinstance(e.Curve,Part.Line):g=Part.LineSegment(p(a),p(c))
    elif isinstance(e.Curve,Part.Circle):
     g=Part.Circle(V(e.Curve.Center.x,e.Curve.Center.z,0),V(0,0,1),e.Curve.Radius)if abs(c-a-2*math.pi)<1e-6 else Part.Arc(p(a),p((a+c)/2),p(c))
    else:raise TypeError((name,type(e.Curve)))
    n=s.addGeometry(g,False);s.addConstraint(Sketcher.Constraint('Block',n))
 b.Document.recompute();assert s.FullyConstrained
 o=b.newObject('PartDesign::Pocket'if subtract else'PartDesign::Pad',name);o.Profile=s;o.Length=hi-lo;o.Reversed=True
 b.Document.recompute();assert o.Shape.isValid()and len(o.Shape.Solids)==1,(name,len(o.Shape.Solids));s.Visibility=False
 return o


def rr(w,h,r,y0,y1,cx=0,cz=0):
 return fuse([box((cx-w/2+r,y0,cz-h/2),(cx+w/2-r,y1,cz+h/2)),box((cx-w/2,y0,cz-h/2+r),(cx+w/2,y1,cz+h/2-r))]+[cyl(r,y0,y1,cx+sx*(w/2-r),cz+sz*(h/2-r))for sx in(-1,1)for sz in(-1,1)])
def source():
 assert sha(SOURCE)==SOURCE_SHA and sha(PCB)==PCB_SHA,'Immutable source changed'
 return next((d for d in App.listDocuments().values()if d.FileName==str(SOURCE)),None)or App.openDocument(str(SOURCE))
def fixed_features():
 return {'dimensions':{'PCB_F_Y_mm':F,'PCB_B_Y_mm':B,'PCB_finished_thickness_mm':1.,'PCB_XZ_mm':[82,26],'PCB_corner_radius_mm':3.,'rear_cover_outer_Y_mm':REAR,'rear_cover_inner_Y_mm':INNER,'rear_growth_mm':3.2,'rear_skin_outer_Y_mm':SKIN,'target_face_Y_mm':FACE,'target_X_mm':list(XS),'target_Z_mm':ZC,'target_proud_mm':.3,'contact_through_aperture_mm':3.7,'PCB_target_PTH_mm':.8636,'target_pad_proposal_mm':3.2,'mount_centres_XZ_mm':[list(m)for m in MOUNTS],'button_centres_XZ_mm':[list(b)for b in BUTTONS],'dock_device_translation_mm':[0,53.2,32],'dock_target_X_mm':list(XS),'dock_target_Z_mm':42.,'dock_target_Y_mm':23.2,'current_dock_upper_carrier_geometry_not_checked':True}}

def target_shape(x=0,z=0):
 # All axial/radial stations are published; undimensioned chamfer/tip radii omitted.
 neck=.067*25.4/2;head=.125*25.4/2;base=.100*25.4/2;tail=.030*25.4/2
 return fuse([cyl(head,FACE,FACE+.020*25.4,x,z),cyl(neck,FACE+.020*25.4,F-.0135*25.4,x,z),cyl(base,F-.0135*25.4,F,x,z),cyl(tail,F,F+.110*25.4,x,z)])

def build_components(d):
 src=source();ps={}
 board=d.addObject('PartDesign::Body','SingleFlangePCB');native_y(board,'Rounded82x26Outline',[rr(82,26,3,F,B)])
 native_y(board,'FourTargetPTH',[cyl(.8636/2,F-.01,B+.01,x,ZC)for x in XS],True)
 native_y(board,'FourMountClearances',[cyl(.8,F-.01,B+.01,x,z)for x,z in MOUNTS],True)
 native_y(board,'ExistingCaseAxisEdgeReliefs',[cyl(2.,F-.01,B+.01,12,z)for z in(-13,13)],True)
 # Exact selected antenna cutout will be replaced/bound to the native packing study.
 native_y(board,'ProvisionalAntennaEdgeNotch',[box((-41.01,F-.01,-7.2),(-35.6,B+.01,7.2))],True)
 if board.ViewObject:board.ViewObject.ShapeColor=(.12,.45,.24)
 ps['FlangePCB']=board
 for x,n in zip(XS,NETS):ps['Contact_'+n]=body(d,'Contact_'+n,target_shape(x,ZC),(.86,.73,.20),'Mill-Max1946-0-00-15-00-00-03-0; dimensioned primary stepped profile. Undimensioned chamfer/tip curves omitted. Current rating application-specific.')
 # Exact source outer contour is used; do not replace the flange by a box.
 original=src.getObject('RearHalf').Shape
 wires=original.slice(V(0,1,0),-24.0);outer=max(wires,key=lambda w:Part.Face(w).Area)
 face=Part.Face(outer);face.translate(V(0,REAR+24.0,0))
 extension=face.extrude(V(0,4.31,0))
 rear=body(d,'ProposedRearHalf',fuse([original,extension]),(.76,.73,.65),'Original perimeter and closure detail retained where not removed by explicit common PCB cavity; source outer88x32 unchanged.')
 native_y(rear,'SingleBoardDryCavity',[rr(83,27,3.5,INNER,-19.4)],True)
 native_y(rear,'FourWholeHeadApertures',[cyl(1.85,REAR-.01,INNER+.01,x,ZC)for x in XS],True)
 native_y(rear,'TwoButtonClearances',[rr(5.4,4.1,.4,REAR-.01,INNER+.01,x,z)for x,z in BUTTONS],True)
 native_y(rear,'TrayBracketReliefs',[box((x-2.2,-23.2,11.3),(x+2.2,-22.8,14.9))for x in XS],True)
 native_y(rear,'MovedKeeperPockets',[cyl(4.1,-28.3,-27.19,-14.5,-8),cyl(4.1,-28.3,-27.19,3,-10.5)],True)
 # Four locating standoffs carry mounting load; screws install from the open dry cavity.
 print('rear-before-seats',rear.Shape.Volume,bnd(rear.Shape),flush=True)
 native_y(rear,'FourBoardSeats',[cyl(1.75,INNER-.02,F,x,z)for x,z in MOUNTS])
 native_y(rear,'FourM1p4Pilots',[cyl(.55,-28.252,F+.01,x,z)for x,z in MOUNTS],True)
 ps['RearHalf']=rear
 # Integral Tray posts carry axial compression locally through the laminate thickness.
 # Full target tail is retained inside the post's bore; no solder/PCB bending credit.
 tray=body(d,'ProposedFlangeTray',src.getObject('FlangeTray').Shape.copy(),(.71,.70,.64))
 adds=[]
 for x in XS:
  adds.append(cyl(2.,B,-22.6,x,ZC))
 native_y(tray,'FourShortRoofBrackets',[box((x-2.,-23.,11.5),(x+2.,-22.6,14.7))for x in XS])
 native_y(tray,'FourLocalLaminateSupportPosts',adds)
 native_y(tray,'FourFullSoldertailBores',[cyl(.6,B-.01,-23.1,x,ZC)for x in XS],True)
 ps['Tray']=tray
 for i,(x,z)in enumerate(MOUNTS):
  # Screw underhead atPCB B, headtoward+Y, shaft toward-Y into integral RearHalf.
  s=fuse([cyl(1.25,B,B+.8,x,z),cyl(.7,B-2.,B,x,z)])
  ps['BoardScrew'+str(i)]=body(d,'BoardScrew'+str(i),s,(.65,.65,.65),'NBK SPA-M1.4-2-MC3; Ø2.5x.8head,M1.4x2shaft. Thread cosmetic omitted; pilot/tap/strip/bearing must be trialed.')
 for i,(x,z)in enumerate(BUTTONS):
  case=box((x-1.5,F-1.2,z-1.25),(x+1.5,F,z+1.25))
  case=fuse([case,cyl(.75,F-1.6,F-1.19,x,z)])
  ps['Switch'+str(i)]=body(d,'OmronB3U1000P_'+str(i),case,(.2,.2,.2),'Primary3x2.5body,1.2nominalbodyheight,Ø1.5plunger,total1.6(+.15/−.1). Contact terminals/internaldome omitted; actual selected footprint remains native source.')
  # The final skin has no penetrating nib: it loads a pre-cured closed cup.
  s=cyl(2.5,-29.8,-29.25,x,z)
  ps['IntegralSiliconeBoss'+str(i)]=body(d,'IntegralSiliconeBoss'+str(i),s,(.36,.6,.77),'Final continuous skin boss trial; restcrown.2mmbehindtargetface, no looseplunger. Force/overload/materialremaininertqualification.')
 # One permanent pre-cured insert: loaded common flange is captured between
 # PCB F and cover INNER, while two closed cups keep bulk overmold off switches.
 flange=rr(25.4,15.8,.7,INNER,F,-8,4.75)
 cups=[rr(5.2,3.9,.6,-29.25,F,x,z)for x,z in BUTTONS]
 inside=[rr(4.4,3.1,.2,-28.85,F+.01,x,z)for x,z in BUTTONS]
 necks=[cyl(1.6,-29.492,F,x,ZC)for x in XS]
 neck_holes=[cyl(.8,-29.502,F+.01,x,ZC)for x in XS]+[cyl(1.35,F-.3429,F+.01,x,ZC)for x in XS]
 diaphragm=cut(fuse([flange]+cups+necks),inside+neck_holes)
 ps['ButtonDiaphragm']=body(d,'PermanentSixOpeningDiaphragm',diaphragm,(.52,.70,.8),'Pre-cured one-piece6-openingbarrier:2closedbuttoncups+4targetnecksleeves. TrialDragonSkin20;freeflange.30/loaded.248. Targetneck1.60ID deliberatelyinterferes1.7018neck; stretch-over-headassembly/tear/compression/processsealnotqualified.')
 # Inert insert tooling: actual cavity and positive core separate alongY.
 a=box((-23,-31,-5.5),(7,INNER,15.5))
 a=cut(a,[rr(5.2,3.9,.6,-29.25,INNER+.01,x,z)for x,z in BUTTONS]+[cyl(1.6,-29.492,INNER+.01,x,ZC)for x in XS]+[cyl(.8,-31.01,-29.491,x,ZC)for x in XS])
 # Sprue/vent channels require process tuning; these are open parting channels.
 a=a.cut(cyl(.7,-31.01,INNER+.01,-13,2.4))
 ps['DiaphragmMoldA']=body(d,'DiaphragmMoldA',a,(.66,.66,.72),'Inerttwo-cupinserttrialtool A; pull−Y afterB+Y. Resin/cureinhibition, ventfill, shrinkandreceivedthicknessunqualified.')
 mb=box((-23,INNER,-5.5),(7,-25.3,15.5)).cut(rr(25.4,15.8,.7,INNER-.01,INNER+.30,-8,4.75))
 mb=fuse([mb]+[rr(4.4,3.1,.2,-28.85,-25.3,x,z)for x,z in BUTTONS]+[cyl(.8,-31.,-25.3,x,ZC)for x in XS]+[cyl(1.35,F-.3429,-25.3,x,ZC)for x in XS])
 ps['DiaphragmMoldB']=body(d,'DiaphragmMoldB',mb,(.66,.66,.72),'Inertcupcoretool B,pull+Y beforeA. .30freeflangecavity; assemblednativeflangemodel.248 representsnominalcapturegap only, notpredicteddeformation.')
 # Source keepers move with rear cover only to retain existing magnet axial gap.
 # Their RF incompatibility is reported, not silently hidden by this move.
 for i in range(2):
  q=src.getObject('SteelKeeper'+str(i)).Shape.copy();q.translate(V(24,-3.2,0))
  ps['MovedSteelKeeper'+str(i)]=body(d,'MovedSteelKeeper'+str(i),q,(.5,.5,.5),'Moves+24X/−3.2Y; matchingdockmagnetsmustmove+24X; device+3.2Y preservesaxialgap. FullRF/magneticqualificationremains.')
 mask=box((-19.5,FACE-2,6.8),(5.5,FACE-.6,13.2))
 mask=fuse([mask]+[cyl(1.7,FACE-.61,FACE,x,ZC)for x in XS])
 ps['FaceMask']=body(d,'ContactMoldingFaceMask',mask,(.56,.64,.78),'One process tool coversfourtargetfaces; withdraw−Y before lateral mold opening. Exact full cavity barrier/seal stillunimplemented.')
 return {'parts':ps,'fixed_features':fixed_features(),'status':'dimensional inert trial, not physical/electrical/RF/seal release'}

def active_mcaddata():
 """Explicit hash-bound source selection; never auto-adopt a changing PCB."""
 choice=OUT/'active-PCBA-source.json'
 if choice.exists():
  active=json.loads(choice.read_text());jp=ROOT/active['MCAD_path']
  assert sha(jp)==active['MCAD_sha256'],'Active PCBA MCAD changed; refresh its binding'
 else:jp=ROOT/'hardware/pcb/evt1/single-flange-study/mcad.json'
 data=json.loads(jp.read_text());assert sha(ROOT/data['native_board'])==data['board_sha256']
 return jp,data

def attach_actual_pcba(d,ps):
 """Bind the native placement study and EACH actual selected STEP model."""
 jp,data=active_mcaddata()
 assert sha(ROOT/data['native_board'])==data['board_sha256']
 sp=ROOT/data['native_KiCad_STEP'];assert sha(sp)==data['native_KiCad_STEP_sha256']
 finished=ROOT/data['finished_board_local_STEP'];assert sha(finished)==data['finished_board_local_STEP_sha256']
 assert sha(ROOT/data['finished_board_native'])==data['finished_board_native_sha256']
 raw=Part.read(str(finished));assert raw.isValid()and len(raw.Solids)==1 and abs(raw.BoundBox.ZLength-1.)<1e-6,'Exact1mmfinishedboardrequired'
 def transform(shape,rows):
  m=App.Matrix(*[v for row in rows for v in row]);q=shape.copy();q.transformShape(m,False,False);assert q.isValid();return q
 binding_path=ROOT/'hardware/pcb/evt1/single-flange-study/finished-board.json';assert sha(binding_path)==data['finished_board_binding_sha256']
 board_binding=json.loads(binding_path.read_text());board=transform(raw,board_binding['proper_local_to_product_matrix4'])
 ps['FlangePCB'].Visibility=False
 # Keep the editable contour study as hidden construction; native actualboard governschecks.
 actual=body(d,'ActualNativeFlangePCB',board,(.13,.44,.23),'Exact1mmfinished-boardPadSTEPfromnativeKiCadoutline/drills, source-boundMCAD; rawKiCad.91FR4exportisnotthisfinishedenvelope.')
 ps['FlangePCB']=actual;group=d.addObject('App::Part','Actual39PositionPCBA');group.addObject(actual)
 shapes={};rows=[]
 for c in data['components']:
  fp=ROOT/c['model'];assert sha(fp)==c['model_sha256'],c['ref']
  raw=Part.read(str(fp));assert not raw.isNull()and raw.isValid()and len(raw.Solids)>0,c['ref']
  q=transform(raw,c['model_to_product_matrix4']);shapes[c['ref']]=q
  sub=d.addObject('App::Part','Actual_'+c['ref']);group.addObject(sub)
  for i,t in enumerate(q.Solids):
   o=body(d,'Actual_'+c['ref']+'_Solid'+str(i),t,(.35,.38,.4),c['value']+'; actualselectedSTEP;source '+c['model']+' SHA256 '+c['model_sha256'])
   sub.addObject(o)
  rows.append({'ref':c['ref'],'source':c['model'],'sha256':c['model_sha256'],'solid_count':len(q.Solids),'volume_mm3':q.Volume,'bounds_mm':bnd(q),'model_to_product':c['model_to_product_matrix4']})
 # Construction profiles are retained for dimensionalcomparison but not installedtwice.
 for k in ['Contact_'+n for n in NETS]+['Switch0','Switch1']:
  ps[k].Visibility=False
 return {'json_path':str(jp.relative_to(ROOT)),'json_sha256':sha(jp),'board_sha256':data['board_sha256'],'STEP_sha256':data['native_KiCad_STEP_sha256'],'finished_board_STEP':str(finished.relative_to(ROOT)),'finished_board_STEP_sha256':sha(finished),'parts':rows,'shapes':shapes,'group':group}

def add_continuous_skin(d,ps,src):
 """Actual nominal skin design over a CLOSED cavity; no physical sealing inference."""
 # Same90x38/r7 exterior and root as the source overmoldtrial, rear extended3.2.
 outside=rr(90,38,7,SKIN,-6)
 es=[e for e in outside.Edges if e.BoundBox.YLength<1e-6];outside=outside.makeFillet(1.,es)
 root=src.getObject('ContinuousSkin').Shape.common(box((-100,-8,-100),(100,1,100)))
 arrow=src.getObject('ContinuousSkin').Shape.common(box((24.5,-26.9,-2.5),(36.5,-26.49,2.5)));arrow.translate(V(0,-3.2,0))
 outside=fuse([outside,root,arrow])
 # Source outerperimeters define the solid CLOSED insert volume, not cavityfill.
 old=src.getObject('RearHalf').Shape;w=max(old.slice(V(0,1,0),-24.),key=lambda w:Part.Face(w).Area)
 face=Part.Face(w);face.translate(V(0,REAR+24.,0));closed_rear=face.extrude(V(0,-22.89-REAR,0))
 tray=src.getObject('FlangeTray').Shape
 ws=[]
 for y in(-22.89,-8.01):ws.append(max(tray.slice(V(0,1,0),y),key=lambda w:Part.Face(w).Area))
 closed_tray=Part.makeLoft(ws,True,False)
 front_fill=Part.Face(ws[-1]).extrude(V(0,.02,0))
 inside=fuse([closed_rear,closed_tray,front_fill])
 skin=outside.cut(inside).cut(src.getObject('MetalBody').Shape.fuse(cyl(6.,-20,0,0,0)))
 # Deliberatelydryinsideclosedcups, notfilledbythefinalovermold.
 keep=[rr(5.2,3.9,.6,-29.25,F,x,z)for x,z in BUTTONS]+[cyl(1.6,-29.492,F,x,ZC)for x in XS]
 keep += [ps['Contact_'+n].Shape for n in NETS]
 skin=cut(skin,keep)
 annuli=[cyl(1.85,REAR-.01,INNER,x,ZC).cut(cyl(1.6,REAR-.02,INNER+.01,x,ZC))for x in XS]
 annuli +=[rr(5.4,4.1,.4,REAR-.01,INNER,x,z).cut(rr(5.2,3.9,.6,REAR-.02,INNER+.01,x,z))for x,z in BUTTONS]
 skin=fuse([skin]+annuli)
 skin=fuse([skin]+[ps['IntegralSiliconeBoss'+str(i)].Shape for i in range(2)])
 skin=skin.cut(ps['RearHalf'].Shape).cut(ps['Tray'].Shape).removeSplitter()
 o=body(d,'RevisedContinuousSkin',skin,(.40,.64,.77),'Source90x38/r7skin+originalroot, rear3.2growth; intendedclosed-cavitynominalshapeONLY. Cavitybarrier/metalinterfaces/cure/adhesionneedinertproof.')
 ps['ContinuousSkin']=o
 for i in range(2):ps['IntegralSiliconeBoss'+str(i)].Visibility=False
 return o

def review(d,ps,src):
 roles=['PackSizeReference','PackGrowthAllowance','PackNTC0','PackNTC1','BodyPCB','MetalBody','MotorThermistorCap','RearNutReference']
 for o in src.Objects:
  if o.Name.startswith('Body_'):roles.append(o.Name)
 refs=[src.getObject(n)for n in roles if src.getObject(n)]
 hardware=[(k,o.Shape)for k,o in ps.items()if k not in('RearHalf','Tray','FaceMask','ButtonDiaphragm','DiaphragmMoldA','DiaphragmMoldB','ContinuousSkin')and not k.startswith('IntegralSilicone')]
 checks=[];bad=[]
 for k,s in hardware:
  for o in refs:
   v=volume_common(s,o.Shape);checks.append([k,o.Name,v])
   if v>1e-6:bad.append(checks[-1])
 barrier=ps['ButtonDiaphragm'].Shape
 barrier_checks=[]
 for name in('RearHalf','FlangePCB','Switch0','Switch1'):
  barrier_checks.append({'part':name,'common_mm3':volume_common(barrier,ps[name].Shape)})
 soft_neck_interference=[{'target':n,'common_mm3':volume_common(barrier,ps['Contact_'+n].Shape),'purpose':'intendedsoftinterferenceonly,unvalidated'}for n in NETS]
 case_common=volume_common(ps['RearHalf'].Shape,ps['Tray'].Shape)
 skinchecks=[]
 if 'ContinuousSkin'in ps:
  for name,t in [('RearHalf',ps['RearHalf'].Shape),('Tray',ps['Tray'].Shape),('MetalBody',src.getObject('MetalBody').Shape),('PackGrowth',src.getObject('PackGrowthAllowance').Shape),('Barrier',barrier)]:skinchecks.append({'part':name,'common_mm3':volume_common(ps['ContinuousSkin'].Shape,t)})
 # PCB/tall targets/switches all load frominside toward-Y intoRearHalf apertures.
 moving=[(k,s)for k,s in hardware if k not in('MovedSteelKeeper0','MovedSteelKeeper1')and not k.startswith('BoardScrew')]
 moving.append(('PermanentBarrier',ps['ButtonDiaphragm'].Shape))
 loads=[]
 for i in range(33):
  dy=10-10*i/32;coll=[]
  for k,s in moving:
   q=s.copy();q.translate(V(0,dy,0));v=volume_common(q,ps['RearHalf'].Shape)
   if v>1e-6:coll.append([k,v])
  loads.append({'offset_Y_mm':dy,'collisions':coll})
 # Closing the RearHalf/board onto fixedTray/body/pack; no target friction model.
 closes=[]
 fixed=[('Tray',ps['Tray'].Shape)]+[(o.Name,o.Shape)for o in refs]
 for i in range(33):
  dy=-6+6*i/32;coll=[]
  for k,s in moving:
   q=s.copy();q.translate(V(0,dy,0))
   for n,t in fixed:
    v=volume_common(q,t)
    if v>1e-6:coll.append([k,n,v])
  closes.append({'offset_Y_mm':dy,'collisions':coll})
 native=[{'name':k,'valid':o.Shape.isValid(),'solids':len(o.Shape.Solids),'bounds_mm':bnd(o.Shape),'volume_mm3':o.Shape.Volume}for k,o in ps.items()]
 pack=src.getObject('PackGrowthAllowance').Shape
 return {'status':'source-bound single-flange-PCB inert mechanical feasibility; bodyPCB unchanged','sources':{'product_sha256':SOURCE_SHA,'flange_native_sha256':PCB_SHA},'dimensions':fixed_features()['dimensions'],'native_bodies':native,'source_hard_pairs':checks,'source_hard_clashes':bad,'whole_PCB_loading':loads,'RearHalf_closing':closes,'closed_rigid_halves_common_mm3':case_common,'permanent_barrier_hard_checks':barrier_checks,'continuous_skin_hard_checks':skinchecks,'unqualified_soft_neck_interferences':soft_neck_interference,'battery':{'selection':'BC-PACK-EVT1-001 requested protected pack; no supplier acceptance','growth_is_engineering_allowance':True,'growth_bounds_mm':bnd(pack),'PCB_B_to_growth_mm':-22.6-B,'max_parts_over_growth_budget_mm':2.95,'remaining_at2p95parts_mm':-22.6-(B+2.95),'pack_growth_to_whole_PCB_distance_mm':ps['FlangePCB'].Shape.distToShape(pack)[0],'component_packing_actual_native_binding_pending':d.getObject('Actual39PositionPCBA')is None},'contacts':{'manufacturer':'Mill-Max','mpn':'1946-0-00-15-00-00-03-0','quantity':4,'face_diameter_mm':3.175,'above_PCB_mm':3.048,'tail_below_mountshoulder_mm':2.794,'tail_beyond1mmPCB_mm':1.794,'recommended_hole_mm':.8636,'trial_land_diameter_mm':3.2,'land_is_project_proposal_not_recommended_by_manufacturer':True,'manufacturer_current_rating':'application specific','generic_height_tolerance_mm':.127,'generic_diameter_tolerance_mm':.0508,'generic_angle_tolerance_deg':2,'proposed_finished_aperture_min_max_mm':[3.7,3.8],'min_radial_clearance_atmaxdiameter_maxheight_2deg_50umoffset_mm':(3.7-(3.175+.0508))/2-(3.048+.127)*math.tan(math.radians(2))-.05,'PTH_shaft_and_solder_fixture_received_acceptance_open':True,'wetted_plating_brass_compatibility_qualified':False,'recommended_dock_stop_OD_mm':2.4,'recommended_shallow_stop_height_mm':.1,'dock_stop_native_implemented':False,'dock_stop_scope':'Not embedded in this flange native; implemented separately in recentered-carrier-trial/RecenteredCarrierTrial.FCStd','old_OD3_radial_margin_mm':.0875,'load_path':'Solid target baseØ2.54 -> supported laminate through-thickness -> integralTray annularpost. No solder or PCBflex loadcredit. Laminate bearing, flatness, targetshoulder/reflowstandoff and post strength require actual loadtrial.','physical_test':False},'buttons':{'selected':'OmronB3U-1000P','nominal_total_height_mm':1.6,'range_mm':[1.5,1.75],'permanent_barrier':'Singlepre-curedtwo-cupinsert; commonflangeclampedbetweenpositivecoverseatsandPCB','cup_dry_face_Y_mm':-28.85,'gap_at_nominal_switch_mm':.298,'gap_at_max_switch_mm':.148,'free_flange_mm':.30,'loaded_gap_mm':.248,'compression_force_and_perimeter_leak_acceptance':False,'restcrown_Y_mm':-29.8,'nominal_crown_to_carrier_front23p1_gap_mm':.3,'pretravel_mm':[.03,.35],'nominal_pretravel_mm':.15,'pretravel_is_not_max_overtravel':True,'silicone_material_force_and_hardstop_unqualified':True,'inert_force_displacement_trial_required':True},'RF':{'selected_module':'ESP32-C3-MINI-1-N4X integratedantenna','not_external_antenna':'No invented coax feed','left_antenna_notch_is_provisional':True,'keeper_move_XY_mm':[24,-3.2],'nominal_keeper0_left_edge_to_antenna_right_edge_mm':17.1,'allmetal_copper_and_actual_RF_measurement_acceptance':False,'radiated_RF_qualification':False},'molding':{'sequence':'Install PCB+contacts/buttons asoneassembly intoRearHalf;retain4stock screws;connectbodyloom/pack;closeTray+RearHalf;thenonecontinuoussiliconeovermold. Face mask withdraws−Y before lateral tool opening.','four_metal_silicone_boundaries_remain':True,'button_cavity_barrier_implemented_as_pre_cured_cup_insert':True,'button_barrier_trial_material':'Smooth-OnDragonSkin20; primaryTDS; no finalwetmaterialor275nmagingapproval','contact_cavity_barrier_implemented_as4pre_cured_sleeves':True,'sleeve_ID_mm':1.6,'neck_diameter_mm':1.7018,'nominal_diameter_interference_mm':.1018,'nominal_stretch_over_head_diameter_ratio':3.175/1.6,'four_metal_boundary_seals_physically_qualified':False,'final_skin_bond_to_precured_insert_qualified':False,'PCB_encapsulation_or_plating_seal_credit':False,'live_casting_release':False},'dock':{'device_translation_Y_mm':53.2,'target_face_Y_mm':23.2,'upper_PinPCB_relative_shift_XZ_mm':[22,-1.5],'do_not_translate_existing_M3feet':True,'native_carrier_stops_case_fit_remaining':True,'moved_keepers_preserve_old_axial_magnet_gap_only':True},'new_routed_PCB':False,'physical_validation':False}

def check_actual_pcba(ps,actual,src):
 refs=[('RearHalf',ps['RearHalf'].Shape),('Tray',ps['Tray'].Shape),('MetalBody',src.getObject('MetalBody').Shape),('BodyPCB',src.getObject('BodyPCB').Shape),('RearNut',src.getObject('RearNutReference').Shape),('PackGrowth',src.getObject('PackGrowthAllowance').Shape),('RequestedPack',src.getObject('PackSizeReference').Shape),('Keeper0',ps['MovedSteelKeeper0'].Shape),('Keeper1',ps['MovedSteelKeeper1'].Shape)]
 refs +=[('BoardScrew'+str(i),ps['BoardScrew'+str(i)].Shape)for i in range(4)]
 refs +=[('ContinuousSkin',ps['ContinuousSkin'].Shape),('PermanentBarrier',ps['ButtonDiaphragm'].Shape)]
 # These broad empty regions are checked against actual frozen shapes once.
 # Containment of an exact package bound in a verified empty box proves separation.
 voids={};proof=[]
 specs={
 'RearHalf':[(-37.9,F+.01,-13.4,37.9,20,13.4),(-41.4,F+.01,-9.9,41.4,20,9.9)],
 'ContinuousSkin':[(-37.9,F+.01,-15.9,37.9,-22.901,15.9),(-43.9,F+.01,-9.9,43.9,-22.901,9.9)],
 'Tray':[(-43.9,-40,-13.4,43.9,-22.901,7.9),(-43.9,-40,-13.4,-18.1,-22.901,13.4),(4.1,-40,-13.4,43.9,-22.901,13.4)]}
 refmap=dict(refs)
 for name,regions in specs.items():
  voids[name]=[]
  for bounds in regions:
   v=box(bounds[:3],bounds[3:]);overlap=v.common(refmap[name]).Volume
   assert overlap<1e-6,(name,bounds,overlap)
   voids[name].append(bounds);proof.append({'part':name,'verified_empty_box_mm':list(bounds),'native_common_mm3':overlap})
 known={p["ref"]:p["bounds_mm"]for p in actual["parts"]}
 def shifted(ref,dy=0):
  z=list(known[ref]);z[1]+=dy;z[4]+=dy;return z
 def collision(q,name,target,bounds):
  lo=bounds[:3];hi=bounds[3:]
  for v in voids.get(name,[]):
   if all(lo[i]>=v[i]+1e-8 and hi[i]<=v[i+3]-1e-8 for i in range(3)):return 0.
  return volume_common(q,target,a_bounds=bounds)
 results=[];bad=[];soft=[]
 for ref,s in actual['shapes'].items():
  for n,t in refs:
   v=collision(s,n,t,shifted(ref));results.append([ref,n,v])
   if n=='PermanentBarrier'and ref.startswith('CT'):
    soft.append([ref,v]);continue
   if v>1e-6:bad.append(results[-1])
 pairs=[]
 items=list(actual['shapes'].items())
 for i,(a,s)in enumerate(items):
  for b,t in items[i+1:]:
   v=volume_common(s,t,a_bounds=shifted(a),b_bounds=shifted(b))
   if v>1e-6:pairs.append([a,b,v])
 loaded=[];closed=[]
 for i in range(33):
  dy=10-10*i/32;fails=[]
  for ref,s in items:
   q=s.copy();q.translate(V(0,dy,0));v=collision(q,'RearHalf',ps['RearHalf'].Shape,shifted(ref,dy))
   if v>1e-6:fails.append([ref,v])
  loaded.append({'offset_Y_mm':dy,'collisions':fails})
  dy=-6+6*i/32;fails=[]
  for ref,s in items:
   q=s.copy();q.translate(V(0,dy,0))
   for n,t in refs:
    if n in('RearHalf','Keeper0','Keeper1','ContinuousSkin','PermanentBarrier')or n.startswith('BoardScrew'):continue
    v=collision(q,n,t,shifted(ref,dy))
    if v>1e-6:fails.append([ref,n,v])
  closed.append({'offset_Y_mm':dy,'collisions':fails})
 safe={k:v for k,v in actual.items()if k not in('shapes','group')}
 safe.update({'verified_empty_region_proofs':proof,'package_to_fixed_checks':results,'hard_clashes':bad,'actual_package_pair_clashes':pairs,'intentional_unqualified_contact_web_interference_mm3':soft,'whole_PCBA_loading':loaded,'whole_PCBA_closing':closed,'physical_validation':False})
 return safe

def export_target_model():
 """Reproduce the selectedtargetmodel; changingitrequiresPCBAmodelhashrefresh."""
 q=target_shape();q.rotate(V(0,0,0),V(1,0,0),-90);q.translate(V(0,0,F))
 d=App.newDocument('MillMax1946Source');o=body(d,'MillMax1946',q,(.86,.73,.2),'Primarydimensionedexternalprofile;mountz0,head+Z;undimensionedchamfer/tipcurvesomitted.')
 d.recompute();assert o.Shape.isValid()and len(o.Shape.Solids)==1
 folder=OUT/'models';folder.mkdir(parents=True,exist_ok=True);d.saveAs(str(folder/'MillMax1946.FCStd'));o.Tip.Shape.exportStep(str(folder/'MillMax1946.step'))
 r=Part.read(str(folder/'MillMax1946.step'));assert r.isValid()and len(r.Solids)==1 and abs(r.Volume-12.031202541537699)<1e-6
 return {'native':str(folder/'MillMax1946.FCStd'),'STEP':str(folder/'MillMax1946.step'),'STEP_sha256':sha(folder/'MillMax1946.step')}

def installed_objects(d):
 """Exact installed-only native objects for the parent/carrier sweeps."""
 names=['ProposedRearHalf','ProposedFlangeTray','RevisedContinuousSkin','PermanentSixOpeningDiaphragm','MovedSteelKeeper0','MovedSteelKeeper1']+['BoardScrew'+str(i)for i in range(4)]
 result=[d.getObject(n)for n in names if d.getObject(n)]
 group=d.getObject('Actual39PositionPCBA')
 if group:
  def walk(o):
   if o.TypeId=='PartDesign::Body':result.append(o)
   elif hasattr(o,'Group'):
    for x in o.Group:walk(x)
  walk(group)
 return result

def exterior_objects(d):
 """Exterior selected-part source; identity product frame before docktranslation."""
 result=[d.getObject(n)for n in('SourceMetalBody','SourceMotorThermistorCap','RevisedContinuousSkin','MovedSteelKeeper0','MovedSteelKeeper1')if d.getObject(n)]
 for ref in('CT1','CT2','CT3','CT4'):
  g=d.getObject('Actual_'+ref)
  if g:result.extend(o for o in g.Group if o.TypeId=='PartDesign::Body')
 return result

def build_full_candidate(d):
 """Native integration API; suppliedD mustalreadybesavedforlaterexternallinks."""
 src=source();r=build_components(d);actual=attach_actual_pcba(d,r['parts']);add_continuous_skin(d,r['parts'],src);d.recompute()
 return dict(r,actual_PCBA=actual,installed=installed_objects(d))

def main():
 OUT.mkdir(parents=True,exist_ok=True);src=source();d=App.newDocument('SingleFlangeBoardTrial');d.saveAs(str(OUT/'SingleFlangeBoardTrial.FCStd'))
 result=build_components(d);ps=result['parts'];d.recompute();d.save();actual=attach_actual_pcba(d,ps);d.recompute();d.save();add_continuous_skin(d,ps,src);group=d.addObject('App::Part','ImmutableProductSources')
 for n in ('PackSizeReference','PackGrowthAllowance','PackNTC0','PackNTC1','BodyPCB','MetalBody','MotorThermistorCap','RearNutReference'):
  o=src.getObject(n)
  if o:l=d.addObject('App::Link','Source'+n);l.setLink(o);group.addObject(l)
 d.recompute();d.save();rep=review(d,ps,src);rep['actual_PCBA']=check_actual_pcba(ps,actual,src);(OUT/'review.json').write_text(json.dumps(rep,indent=2)+'\n')
 ps['FaceMask'].Visibility=False;ps['RearHalf'].Visibility=False;ps['DiaphragmMoldA'].Visibility=False;ps['DiaphragmMoldB'].Visibility=False;d.recompute();d.save()
 for k in('FlangePCB','RearHalf','Tray','FaceMask','Contact_GND','ContinuousSkin','ButtonDiaphragm','DiaphragmMoldA','DiaphragmMoldB','ContinuousSkin'):Part.export([ps[k]],str(OUT/(k+'.step')))
 print(json.dumps({'native':str(OUT/'SingleFlangeBoardTrial.FCStd'),'bodies':len(ps),'hard_clashes':rep['source_hard_clashes'],'loading_failed_poses':sum(bool(a['collisions'])for a in rep['whole_PCB_loading']),'closing_failed_poses':sum(bool(a['collisions'])for a in rep['RearHalf_closing'])},indent=2),flush=True)
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='target':print(json.dumps(export_target_model(),indent=2))
 else:main()
