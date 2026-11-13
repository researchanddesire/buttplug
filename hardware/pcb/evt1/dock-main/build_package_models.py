"""Editable FreeCAD selected TI package reconstructions from primary drawings.

Run in FreeCADcmd. Nominal XY and published maximum height are used; tolerance
limits are recorded separately. Undimensioned cosmetic marks/internal dies
are omitted. Not OEM CAD and not a received-part dimensional qualification.
"""
from pathlib import Path
import hashlib,json,math
import FreeCAD as A
import Part,Sketcher
H=Path(__file__).resolve().parent;OUT=H/'DockMain.3dshapes';OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
records={}
def package(name):
 d=A.newDocument(name);p=d.addObject('App::Part',name);p.Label=name;return d,p
def box(d,p,name,x,y,z,w,l,h,color):
 body=d.addObject('PartDesign::Body',name);p.addObject(body)
 f=body.newObject('PartDesign::AdditiveBox',name+'Box');f.Length=w;f.Width=l;f.Height=h
 f.Placement.Base=A.Vector(x-w/2,y-l/2,z);d.recompute()
 if A.GuiUp:body.ViewObject.ShapeColor=color;f.ViewObject.ShapeColor=color
 return body
BLACK=(.12,.12,.13);METAL=(.72,.74,.76)
def save(d,p,name,dimensions,source):
 d.recompute();bodies=[b for b in p.Group if b.TypeId=='PartDesign::Body']
 assert all(b.Shape.isValid()and len(b.Shape.Solids)==1 for b in bodies)
 native=OUT/(name+'.FCStd');step=OUT/(name+'.step');d.saveAs(str(native));Part.export(bodies,str(step))
 bb=Part.makeCompound([b.Shape for b in bodies]).optimalBoundingBox(False,False)
 records[name]={'native':native.name,'native_sha256':sha(native),'STEP':step.name,'STEP_sha256':sha(step),
 'editable_native_bodies':len(bodies),'bounds_mm':[bb.XMin,bb.YMin,bb.ZMin,bb.XMax,bb.YMax,bb.ZMax],
 'dimensions':dimensions,'primary_source':source,'classification':'selected-package dimensional reconstruction; NOT OEM CAD',
 'omitted':'internal die/bonding, undimensioned edge cosmetics/markings; no process/reflow/tolerance qualification',
 'model_frame':'PCB+X and model+Y up; nativePCB+Y maps model-Y; seating planeZ0'}
 pdfs={'TPS22950_YBH6':'/private/tmp/compass-router-bounded/tps22950.pdf','TPS3431_DRB8':'/private/tmp/compass-safety/tps3431.pdf','TPS22992_RXP8':'/private/tmp/compass-safety/tps22992.pdf','TUSB320_RWB12':'/private/tmp/compass-router-bounded/tusb320lai.pdf'}
 records[name]['primary_PDF_sha256']=sha(Path(pdfs[name]))
 A.closeDocument(d.Name)
# TPS22950YBHR: YBH0006-C02 page21. BallA1 at model(-.2,+.4).
d,p=package('TPS22950_YBH6')
box(d,p,'SiliconBody',0,0,.16,.706,1.106,.24,BLACK)
r=.205/2;bh=.16;rt=math.sqrt(r*r-(bh-r)**2)
for row,y in [('A',.4),('B',0),('C',-.4)]:
 for col,x in [('1',-.2),('2',.2)]:
  b=d.addObject('PartDesign::Body','Ball'+row+col);p.addObject(b)
  s=b.newObject('Sketcher::SketchObject','Profile'+row+col)
  s.Placement=A.Placement(A.Vector(x,y,0),A.Rotation(A.Vector(1,0,0),90))
  s.addGeometry(Part.Arc(A.Vector(0,0,0),A.Vector(r,r,0),A.Vector(rt,bh,0)),False)
  s.addGeometry(Part.LineSegment(A.Vector(rt,bh,0),A.Vector(0,bh,0)),False)
  s.addGeometry(Part.LineSegment(A.Vector(0,bh,0),A.Vector(0,0,0)),False)
  f=b.newObject('PartDesign::Revolution','SolderBall'+row+col);f.Profile=s;f.ReferenceAxis=(s,['V_Axis']);f.Angle=360
  if A.GuiUp:s.Visibility=False;f.ViewObject.ShapeColor=METAL;b.ViewObject.ShapeColor=METAL
  d.recompute()
save(d,p,'TPS22950_YBH6',{'body_nominal_XY_mm':[.706,1.106],'body_XY_min_mm':[.686,1.086],'body_XY_max_mm':[.726,1.126],
 'overall_max_height_mm':.4,'ball_diameter_nominal_mm':.205,'ball_diameter_min_max_mm':[.185,.225],
 'ball_height_nominal_mm':.16,'ball_height_min_max_mm':[.13,.19],'pitch_mm':.4,
 'note':'Spheres cut at published nominal stand-off; totalheight uses publishedmax because no nominal totalheight isgiven.'},
 'https://www.ti.com/lit/ds/symlink/tps22950.pdf#page=21 YBH0006-C02 4226594/A03/2021')
# TPS3431SDRBR: DRB0008A, published1.0mm maxheight; trueEP fingers.
d,p=package('TPS3431_DRB8')
box(d,p,'MoldBody',0,0,.05,3,3,.95,BLACK)
for side,x in [('Left',-1.3),('Right',1.3)]:
 for i,y in enumerate((.975,.325,-.325,-.975),1):box(d,p,side+'Terminal'+str(i),x,y,0,.4,.31,.05,METAL)
ep=box(d,p,'ExposedThermalPad',0,0,0,1.5,1.75,.05,METAL)
for x in(-.325,.325):
 for sign in(-1,1):
  f=ep.newObject('PartDesign::AdditiveBox','EPFinger'+str(len(ep.Group)))
  f.Length=.23;f.Width=.65;f.Height=.05;f.Placement.Base=A.Vector(x-.115,sign*1.175-.325,0)
  if A.GuiUp:f.ViewObject.ShapeColor=METAL
  d.recompute()
save(d,p,'TPS3431_DRB8',{'body_nominal_XY_mm':[3,3],'body_XY_min_mm':[2.9,2.9],'body_XY_max_mm':[3.1,3.1],
 'overall_max_height_mm':1,'side_contact_width_length_nominal_mm':[.31,.4],'side_contact_width_min_max_mm':[.25,.37],
 'side_contact_length_min_max_mm':[.3,.5],'pitch_mm':.65,'EP_nominal_XY_mm':[1.5,1.75],
 'EP_XY_tolerance_mm':.1,'four_EP_finger_width_reference_mm':.23,'EP_finger_X_centres_mm':[-.325,.325],
 'EP_finger_outer_Y_mm':[-1.5,1.5],'standoff_range_mm':[0,.05],
 'note':'Terminalcornerradii notdimensioned: rectangular terminals retain publishedexternal extents. Fingers overlapEP by0.025mm to form oneeditable metalbody.'},
 'https://www.ti.com/lit/ds/symlink/tps3431.pdf DRB0008A4218875/A01/2018 packageoutline')
# TPS22992RXPR: RXP0008A; endpadlength0.375, not middlepad0.5.
d,p=package('TPS22992_RXP8')
box(d,p,'MoldBody',0,0,.05,1.25,1.5,.75,BLACK)
for side,sign in [('Left',-1),('Right',1)]:
 for y in(.5,-.5):box(d,p,side+'Corner'+('A'if y>0 else'B'),sign*.5,y,0,.25,.25,.05,METAL)
 box(d,p,side+'PowerTerminal',sign*.375,0,0,.5,.25,.05,METAL)
for label,sign in [('Top',1),('Bottom',-1)]:box(d,p,label+'EndTerminal',0,sign*(.75-.375/2),0,.25,.375,.05,METAL)
save(d,p,'TPS22992_RXP8',{'body_nominal_XY_mm':[1.25,1.5],'body_XY_min_mm':[1.15,1.4],'body_XY_max_mm':[1.35,1.6],
 'overall_max_height_mm':.8,'contact_width_nominal_mm':.25,'contact_width_min_max_mm':[.2,.3],
 'corner_contact_length_nominal_mm':.25,'corner_contact_length_min_max_mm':[.2,.3],
 'middle_contact_length_nominal_mm':.5,'middle_contact_length_min_max_mm':[.4,.6],
 'end_contact_length_nominal_mm':.375,'end_contact_length_min_max_mm':[.325,.425],
 'standoff_range_mm':[0,.05],'note':'Contacts are actual package terminals, shorter thanPCB solderlands; eight0.25wide contacts with asymmetric lengths.'},
 'https://www.ti.com/lit/ds/symlink/tps22992.pdf#page=26 RXP0008A4225934/A05/2020')
# TUSB320HAIRWBR: primary RWB0012A; pads follow actual footprint pin frame.
d,p=package('TUSB320_RWB12')
box(d,p,'MoldBody',0,0,.025,1.6,1.6,.375,BLACK)
for number,x,y in [(1,-.55,.2),(2,-.55,-.2),(7,.55,-.2),(8,.55,.2)]:
 box(d,p,'Terminal'+str(number),x,y,0,.5,.2,.13,METAL)
for row,nums in [(-1,(3,4,5,6)),(1,(12,11,10,9))]:
 for x,num in zip((-.6,-.2,.2,.6),nums):box(d,p,'Terminal'+str(num),x,row*.65,0,.2,.3,.13,METAL)
save(d,p,'TUSB320_RWB12',{'body_nominal_XY_mm':[1.6,1.6],'body_XY_min_mm':[1.55,1.55],'body_XY_max_mm':[1.65,1.65],
 'overall_max_height_mm':.4,'contact_width_nominal_mm':.2,'contact_width_min_max_mm':[.15,.25],
 'four_side_contact_length_nominal_mm':.5,'four_side_contact_length_min_max_mm':[.4,.6],
 'eight_end_contact_length_nominal_mm':.3,'eight_end_contact_length_min_max_mm':[.2,.4],
 'contact_thickness_reference_mm':.13,'pitch_mm':.4,'standoff_range_mm':[0,.05],
 'note':'Pin1 undimensioned corner clip omitted. Metalreference thickness0.13 is represented; native pad1(-X,-Y) maps model(-X,+Y). Body starts at stand-off midrange0.025.'},
 'https://www.ti.com/lit/ds/symlink/tusb320lai.pdf#page=35 RWB0012A4221631/B07/2017')
(OUT/'custom-model-provenance.json').write_text(json.dumps({'FreeCAD':A.Version(),'packages':records,'primary_drawings_visually_inspected':True,'independent_RXP_DRB_peer_review':'uv_power2026-11-12; correctedendpadRXP0.375mm','physical_validation':False},indent=2)+'\n')
print('Selected native packages built',list(records))
