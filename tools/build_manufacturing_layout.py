"""Four-part mechanical DFM study. Optional arguments: source P1 native, output folder.

Run with FreeCAD Python. Supplier tooling, fits, electrical revision and physical
validation are deliberately separate from this geometry study.
"""
from pathlib import Path
import sys,math,json,hashlib,itertools
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib');sys.path.insert(0,'/Users/lucianchapar/Documents/ChatGPT/buttplug-compass/tools')
import FreeCAD as A
import Part,MeshPart,Mesh
from simple_charging_wires_p1 import overlap
ROOT=Path(__file__).resolve().parents[1];OUT=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else ROOT/'hardware/cad/manufacturing-layout';OUT.mkdir(parents=True,exist_ok=True)
source=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'hardware/cad/prototype-p1/PrototypeP1.FCStd';report=json.loads((ROOT/'hardware/cad/prototype-p1/review.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(source)==report['native_sha256']
S=A.openDocument(str(source));D=A.newDocument('ManufacturingLayout');D.Label='Manufacturing layout / four rigid custom parts / engineering study'
construction=D.addObject('App::DocumentObjectGroup','Construction');parts=D.addObject('App::DocumentObjectGroup','ProductParts');refs=D.addObject('App::DocumentObjectGroup','ComponentReferences');printed=[]
def feat(name,shape,group=construction):
 o=D.addObject('PartDesign::Feature',name);o.Shape=shape;group.addObject(o);return o
def cyl(name,r,x,y,z,L,axis=(0,1,0)):
 o=D.addObject('Part::Cylinder',name);o.Radius=r;o.Height=L;o.Placement=A.Placement(A.Vector(x,y,z),A.Rotation(A.Vector(0,0,1),A.Vector(*axis)));construction.addObject(o);return o
def box(name,x,y,z,L,W,H):
 o=D.addObject('Part::Box',name);o.Length=L;o.Width=W;o.Height=H;o.Placement.Base=A.Vector(x,y,z);construction.addObject(o);return o
def boolean(kind,name,a,b):
 o=D.addObject('Part::'+kind,name);o.Base=a;o.Tool=b;o.Refine=True;construction.addObject(o);D.recompute();return o
def fuse(name,items):
 o=D.addObject('Part::MultiFuse',name);o.Shapes=items;o.Refine=True;construction.addObject(o);D.recompute();return o
def rr(hx,hz,r,y):
 V=lambda x,z:A.Vector(x,y,z);q=math.sqrt(.5);es=[]
 seq=[((-hx+r,-hz),(hx-r,-hz),None),((hx-r,-hz),(hx,-hz+r),(hx-r+r*q,-hz+r-r*q)),((hx,-hz+r),(hx,hz-r),None),((hx,hz-r),(hx-r,hz),(hx-r+r*q,hz-r+r*q)),((hx-r,hz),(-hx+r,hz),None),((-hx+r,hz),(-hx,hz-r),(-hx+r-r*q,hz-r+r*q)),((-hx,hz-r),(-hx,-hz+r),None),((-hx,-hz+r),(-hx+r,-hz),(-hx+r-r*q,-hz+r-r*q))]
 for a,b,m in seq:es.append(Part.makeLine(V(*a),V(*b))if m is None else Part.Arc(V(*a),V(*m),V(*b)).toShape())
 return Part.Wire(es)
def cone(name,r0,r1,x,y,z,L,axis):return feat(name,Part.makeCone(r0,r1,L,A.Vector(x,y,z),A.Vector(*axis)))
def final(name,o):
 o.Label=name;construction.removeObject(o);parts.addObject(o);D.recompute();assert o.Shape.isValid()and len(o.Shape.Solids)==1,(name,len(o.Shape.Solids));return o
# Two turned blanks. The body also needs two indexed collar flats; the cap
# needs one offset sensor drill. Threads use explicit pilot/root envelopes.
def profile(name,points):
    wire=Part.makePolygon([A.Vector(r,y,0) for r,y in points]+[A.Vector(points[0][0],points[0][1],0)])
    return feat(name,Part.Face(wire).revolve(A.Vector(),A.Vector(0,1,0),360))
def spline_edge(points):
    c=Part.BSplineCurve();c.interpolate([A.Vector(r,y,0)for r,y in points]);return c.toShape()
def dome_radius(y):return 18.669*math.sqrt(1-((y-55)/43.1)**2)
# Preserve the earlier bulge and 15 mm neck, stripping all former keys/thread cuts.
ys=[20+i*.5 for i in range(58)]
radii=[]
for y in ys:
    edges=S.getObject('KeyedBodyR25').Shape.section(Part.makePlane(100,100,A.Vector(-50,y,-50),A.Vector(0,1,0))).Edges
    radii.append((max(max(abs(e.BoundBox.XMin),abs(e.BoundBox.XMax))for e in edges),y))
V=lambda r,y:A.Vector(r,y,0)
rear_root_radius=(18-1.22687)/2
es=[Part.makeLine(V(0,-14.25),V(7.9,-14.25)),
    Part.makeLine(V(7.9,-14.25),V(rear_root_radius,-13.75)),
    Part.makeLine(V(rear_root_radius,-13.75),V(rear_root_radius,-10.25)),
    Part.makeLine(V(rear_root_radius,-10.25),V(8.2,-10.25)),
    Part.makeLine(V(8.2,-10.25),V(8.2,-9.5)),
    Part.makeLine(V(8.2,-9.5),V(10,-9.5)),
    Part.makeLine(V(10,-9.5),V(10,-8)),
    Part.makeLine(V(10,-8),V(12,-8)),Part.makeLine(V(12,-8),V(12,-7)),
    Part.makeLine(V(12,-7),V(9.75,-7)),Part.makeLine(V(9.75,-7),V(9.75,-3)),Part.makeLine(V(9.75,-3),V(10.5,-3)),
    spline_edge([(10.5,-3),(9.3,-2),(7.8,-.7),(7.5,0)]),
    Part.makeLine(V(7.5,0),V(7.5,20)),
    spline_edge(radii+[(18.575,51),(18.669,55)]),
    spline_edge([(dome_radius(55+i*9/40),55+i*9/40)for i in range(41)]),
    Part.makeLine(V(dome_radius(64),64),V(0,64)),Part.makeLine(V(0,64),V(0,-14.25))]
body=feat('TurnedBodyBlank',Part.Face(Part.Wire(es)).revolve(A.Vector(),A.Vector(0,1,0),360))
# Straight front bore and conical transition: no hidden internal bulge undercut.
bodyvoid=profile('BodyBoreAndThreadPilot',[(0,-14.35),(6,-14.35),(6,26),(14,33),(14,53.5),(15.2,53.5),(15.2,55.75),(14.25,55.75),(14.25,62.95),(15,63.7),(15,64.1),(0,64.1)])
body=boolean('Cut','BoredBody',body,bodyvoid)
facegland=boolean('Cut','CapFaceSealGlandTool',cyl('FaceGlandOuter',17.4,0,63.22,0,.88),cyl('FaceGlandInner',15.8,0,63.17,0,.98))
body=boolean('Cut','BodyFaceSealGland',body,facegland)
# Selected circular edges only: avoid blanket rounding of functional ring/seal
# corners. Socket entrance chamfer clears the body shoulder root radius.
def round_circles(name,obj,targets,radius):
    chosen=[]
    for e in obj.Shape.Edges:
        bb=e.BoundBox
        if bb.YLength<1e-5 and any(abs(bb.YMin-y)<1e-4 and abs(max(abs(bb.XMin),abs(bb.XMax))-r)<1e-4 for y,r in targets):chosen.append(e)
    assert len(chosen)==len(targets),(name,len(chosen),len(targets))
    sh=obj.Shape.makeFillet(radius,chosen)
    assert sh.isValid() and len(sh.Solids)==1,name
    return feat(name,sh)
body=round_circles('BodyBoreToolRadii',body,[(26,6),(33,14)],.4)
body=round_circles('BodySpigotRootRadius',body,[(-8,10)],.3)
body=round_circles('FaceGlandBottomRadii',body,[(63.22,15.8),(63.22,17.4)],.1)
for sign in (-1,1):
    tool=box('CollarFlatTool'+str(sign).replace('-','M'),-11,-9.51,9.2 if sign==1 else -13.2,22,1.51,4)
    body=boolean('Cut','BodyCollarFlat'+str(sign).replace('-','M'),body,tool)
body=final('MetalBody',body)
def dome(a,b,yc,y0):
    t=math.acos((y0-yc)/b)
    points=[A.Vector(a*math.sin(t*(1-i/60)),yc+b*math.cos(t*(1-i/60)),0)for i in range(61)]
    curve=Part.BSplineCurve();curve.interpolate(points)
    wire=Part.Wire([curve.toShape(),Part.makeLine(points[-1],A.Vector(0,y0,0)),Part.makeLine(A.Vector(0,y0,0),points[0])])
    return Part.Face(wire).revolve(A.Vector(),A.Vector(0,1,0),360)
capblank=feat('ShortTurnedNoseBlank',dome(18.669,43.1,55.,64))
spigot=profile('CapMaleThreadSpigot',[(0,54.75),(13.5,54.75),(14.07985,55.75),(14.07985,61.75),(13.8,61.75),(13.8,64.01),(0,64.01)])
cap=fuse('CapWithTurnedThreadSpigot',[capblank,spigot])
# Counterbore makes both small bores accessible at Y78. No deep annular keyway.
for i,t in enumerate([cyl('CapRearCounterbore',12.25,0,54.65,0,23.35),cyl('MotorBoreNominalFitTBD',5.55,0,77.9,0,15.4),fuse('OffsetSensorDrillWithPoint',[cyl('OffsetTipThermistorDrill',1.25,7.8,77.9,0,12.6),cone('SensorDrillPoint',1.25,0,7.8,90.5,0,1.25/math.tan(math.radians(70)),(0,1,0))])]):
    before=cap.Shape.Volume;removed=cap.Shape.common(t.Shape).Volume
    cap=boolean('Cut','CapCut'+str(i),cap,t);D.recompute()
    assert abs(cap.Shape.Volume-(before-removed))<.01,'Cap cut volume conservation failed'
cap=final('MotorThermistorCap',cap)
assert cap.Shape.Volume>5000 and cap.Shape.BoundBox.YLength>31,'Full cap was lost'
# Straight-draw open tray: 1.6mm nominal walls, 2deg shell draft, no rails/lips/side cores.
slope=math.tan(math.radians(2));outer=feat('DraftedTrayOutside',Part.makeLoft([rr(44-14.9*slope,16-14.9*slope,6-14.9*slope,-8),rr(44,16,6,-22.9)],True,False))
inner=feat('DraftedTrayCore',Part.makeLoft([rr(42.4-13.3*slope,14.4-13.3*slope,4.4-13.3*slope,-9.6),rr(42.4+.2*slope,14.4+.2*slope,4.4+.2*slope,-23.1)],True,False))
base=boolean('Cut','OpenTray',outer,inner);extras=[]
# Cover screws stay in plastic; they do not retain the body.
for i,z in enumerate((-13,13)):extras.append(cone('CaseScrewBoss'+str(i),2+13.3*math.tan(math.radians(.5)),2,12,-9.6,z,13.3,(0,-1,0)))
# Collar is recessed 0.5 mm within this 2 mm pad, allowing the nut to bear on plastic.
extras.append(feat('RootSocketPad',Part.makeCylinder(12,2.0,A.Vector(0,-10,0),A.Vector(0,1,0))))
for i,z in enumerate((-11.5,9.5)):
 extras.append(cone('PCBSeat'+str(i),2.4,2.4-8.7125*slope,-15.2,-9.6,z,8.7125,(0,-1,0)))
 extras.append(cone('PCBLocatingPin'+str(i),.72,.70,-15.2,-18.3125,z,1.2,(0,-1,0)))
# Open ribs support the reference pack; a standard removable adhesive/pull tab retains it.
for i,z in enumerate((-9.2,9.2)):
 a=Part.makePolygon([A.Vector(12,-9.6,z-.4),A.Vector(40.5,-9.6,z-.4),A.Vector(40.5,-9.6,z+.4),A.Vector(12,-9.6,z+.4),A.Vector(12,-9.6,z-.4)])
 b=Part.makePolygon([A.Vector(12.09,-14.5,z-.31),A.Vector(40.41,-14.5,z-.31),A.Vector(40.41,-14.5,z+.31),A.Vector(12.09,-14.5,z+.31),A.Vector(12.09,-14.5,z-.31)])
 extras.append(feat('PackSupportRib'+str(i),Part.makeLoft([a,b],True,False)))
base=fuse('TrayWithSeats',[base]+extras)
def double_d_wire(radius,half_flat,y):
    shape=Part.makeCylinder(radius,.1,A.Vector(0,y,0),A.Vector(0,1,0)).common(Part.makeBox(2*radius+2,.1,2*half_flat,A.Vector(-radius-1,y,-half_flat)))
    face=min(shape.Faces,key=lambda f:abs(f.CenterOfMass.y-y))
    assert abs(face.CenterOfMass.y-y)<1e-6
    return face.OuterWire
socket=feat('KeyedCollarSocketTool',Part.makeLoft([
    double_d_wire(10.1,9.3,-10.1),double_d_wire(10.1,9.3,-8.5),
    double_d_wire(10.6,9.8,-8),double_d_wire(10.6,9.8,-7.9)],True,True))
base=boolean('Cut','TrayKeyedSocket',base,socket)
# Local straight-draw nut well preserves the outside; wall here is about 1.25 mm.
base=boolean('Cut','TrayNutRotationWell',base,cone('DraftedNutWellCore',14.3,14.3+13.1*slope,0,-10,0,13.1,(0,-1,0)))
for i,z in enumerate((-13,13)):
    base=boolean('Cut','TrayCoverPilot'+str(i),base,cone('DraftedScrewCore'+str(i),.8,.8+5*math.tan(math.radians(.5)),12,-22.95,z,5.0,(0,1,0)))
# Front-side axial cores avoid tall solid posts. Leave a closed web before
# the cover pilot/PCB seat. Both cores pull along the same +/-Y mold axis.
for i,z in enumerate((-13,13)):
    base=boolean('Cut','CasePostFrontCore'+str(i),base,cone('CasePostCoreTool'+str(i),1.2,1.2-9.2*math.tan(math.radians(.5)),12,-8,z,9.2,(0,-1,0)))
for i,z in enumerate((-11.5,9.5)):
    base=boolean('Cut','PCBPostFrontCore'+str(i),base,cone('PCBPostCoreTool'+str(i),1.4,1.4-9.4*math.tan(math.radians(.5)),-15.2,-8,z,9.4,(0,-1,0)))
base=final('FlangeTray',base)
cover=feat('CoverPlateBlank',Part.Face(rr(44,16,6,-24.5)).extrude(A.Vector(0,1.6,0)));extras=[]
for i,z in enumerate((-11.5,9.5)):extras.append(cone('PCBHoldDown'+str(i),2.0,2.0-3.3875*slope,-15.2,-22.9,z,3.3875,(0,1,0)))
magaxes=[(-38.5,9.5),(-21,-10.5)]
for i,(x,z)in enumerate(magaxes):extras.append(cone('MagnetWall'+str(i),2.95,2.90,x,-22.9,z,1.1,(0,1,0)))
cover=fuse('CoverWithSimplePosts',[cover]+extras)
for i,z in enumerate((-13,13)):cover=boolean('Cut','CoverScrew'+str(i),cover,cyl('CoverPassage'+str(i),1.1,12,-24.6,z,1.8))
for i,x in enumerate((-21.35,-15.35)):cover=boolean('Cut','ButtonOpening'+str(i),cover,cyl('ButtonThroughHole'+str(i),2.5,x,-24.6,3.5125,1.8))
for i,z in enumerate((8,12)):
 cover=boolean('Cut','TargetStem'+str(i),cover,cyl('TargetStemHole'+str(i),.8,-32,-24.6,z,1.8))
 cover=boolean('Cut','TargetHead'+str(i),cover,cyl('TargetSeat'+str(i),.97,-32,-24.6,z,.86))
for i,(x,z)in enumerate(magaxes):cover=boolean('Cut','MagnetPocket'+str(i),cover,cyl('MagnetBore'+str(i),2.15,x,-23.7,z,2.0))
cover=final('RearCover',cover)
# Component space references: not adopted components or a routed-board revision.
bodyrefs=[S.getObject('BodyPCB_R17').Shape.copy()]+[S.getObject(n).Shape.copy()for n,q in report['roles'].items()if n.startswith('R17_')and q['bounds_xyz_mm'][1]>15]
bodyshape=bodyrefs[0].multiFuse(bodyrefs[1:]).removeSplitter();bodyshape.translate(A.Vector(0,10,0))
bodypcb=feat('BodyElectronicsReference',bodyshape,refs)
substrate=S.getObject('FlangePCB_R17').Shape.copy();tabs=[]
for z in (-10.5,10.5):tabs.append(Part.makeBox(6.2,1.,5.8,A.Vector(-17.4,-19.3125,6 if z>0 else -11.8)))
substrate=substrate.multiFuse(tabs).removeSplitter()
for z in (-10.5,10.5):substrate=substrate.cut(Part.makeCylinder(.9,1.2,A.Vector(-15.2,-19.4125,z),A.Vector(0,1,0)))
flangerefs=[substrate]+[S.getObject(n).Shape.copy()for n,q in report['roles'].items()if n.startswith('R17_')and q['bounds_xyz_mm'][4]<0]
flangeshape=flangerefs[0].multiFuse(flangerefs[1:]).removeSplitter();flangeshape.translate(A.Vector(0,0,-1))
flangepcb=feat('FlangeElectronicsMechanicalProposal',flangeshape,refs)
batteryshape=S.getObject('PackPublishedGaugeR33').Shape.copy();batteryshape.translate(A.Vector(0,1.5,0));battery=feat('UnselectedPackReference',batteryshape,refs)
motorshape=S.getObject('MotorMaxEnvelope').Shape.copy();motorshape.translate(A.Vector(0,5,-3.5));motor=feat('MotorReferenceFitTBD',motorshape,refs)
ntc=feat('TipThermistorHeadReference',Part.makeCylinder(.6,1.2,A.Vector(7.8,89.1,0),A.Vector(0,1,0)),refs)
pot=feat('TipPottingProcessSpace',Part.makeCylinder(1.25,2.4,A.Vector(7.8,88.1,0),A.Vector(0,1,0)).cut(ntc.Shape),refs)
for i in (1,2):
 s=S.getObject('PackNTCHeadR33_'+str(i)).Shape.copy();s.translate(A.Vector(0,1.5,0));feat('PackNTCReference'+str(i),s,refs)
for tag in ('Ground','Positive'):
 s=S.getObject('P1'+tag+'Contact').Shape.copy();s.translate(A.Vector(0,5.5,0));feat(tag+'TargetReference',s,refs)
for i,(x,z)in enumerate(magaxes):feat('MagnetReference'+str(i),Part.makeCylinder(2,1.5,A.Vector(x,-23.7,z),A.Vector(0,1,0)),refs)
# M18x1 sensor-style thin nut: generic 24 AF / 4 mm envelope, not vendor CAD.
nut_radius=24/math.sqrt(3)
vertices=[A.Vector(nut_radius*math.cos(math.radians(30+60*i)),-14,nut_radius*math.sin(math.radians(30+60*i)))for i in range(6)]
nut_blank=feat('ThinNutHexBlank',Part.Face(Part.makePolygon(vertices+[vertices[0]])).extrude(A.Vector(0,4,0)))
nut_outer=profile('ThinNutOuterChamfers',[(0,-14),(11.8,-14),(nut_radius,-13.6),(nut_radius,-10.4),(11.8,-10),(0,-10)])
nut=boolean('Common','ThinNutChamferedBlank',nut_blank,nut_outer)
nut_hole=profile('ThinNutFemalePilot',[(0,-14.1),(8.9,-14.1),(8.5,-13.7),(8.5,-10.3),(8.9,-9.9),(0,-9.9)])
nut=boolean('Cut','ThinRearNut',nut,nut_hole)
construction.removeObject(nut);refs.addObject(nut);nut.Label='ThinRearNut'
# Standard insulation and foam are process references, not scaffold parts.
soft=D.addObject('App::DocumentObjectGroup','StandardSoftGoods')
b=bodypcb.Shape.BoundBox
outer=Part.makeBox(b.XLength+.5,b.YLength+5,b.ZLength+.5,A.Vector(b.XMin-.25,b.YMin,b.ZMin-.25))
inside=Part.makeBox(b.XLength,b.YLength+5.2,b.ZLength,A.Vector(b.XMin,b.YMin-.1,b.ZMin))
feat('OpenEndedInsulatingSleeve',outer.cut(inside),soft)
for sign in (-1,1):
    x0,x1=(b.XMax+.25,12.25) if sign==1 else(-12.25,b.XMin-.25)
    pad=Part.makeBox(x1-x0,10,3,A.Vector(x0,59,-1.5))
    pad=pad.common(Part.makeCylinder(12.25,12,A.Vector(0,58,0),A.Vector(0,1,0)))
    feat('StandardFoamSpacer'+('Right'if sign==1 else'Left'),pad,soft)
# Compressed face-seal space, not a final elastomer shape. Candidate32x1 O-ring.
seal=Part.makeCylinder(17.105,.78,A.Vector(0,63.22,0),A.Vector(0,1,0)).cut(Part.makeCylinder(16.095,.88,A.Vector(0,63.17,0),A.Vector(0,1,0)))
feat('CapFaceSealProcessSpace',seal,soft)
# No socket adhesive or separate compression limiter is credited for retention.
# Silicone cuff is only a root termination section, NOT a completed flange boot.
cuff=profile('BootCuffBlank',[(12,-8),(14,-8),(10.5,-6),(10.5,-3),(9.75,-3),(9.75,-7),(12,-7)])
construction.removeObject(cuff);soft.addObject(cuff);cuff.Label='BondedBootCuffProcessSpace'
params=D.addObject('App::FeaturePython','DesignIntent')
for key,value in {'Status':'Turned metal with indexed collar flats; DFM study, not manufacturing release','MainParts':'CNC body and cap, open tray and rear cover; additional thin nut and silicone boot','Assembly':'Clamp keyed tray to body with rear nut before boards/pack; prewire cap module with flange tails disconnected','RearJoint':'M18x1 short rear stub + 24 AF x4 thin nut; 20mm collar/18.4mm opposing flats. Nut lock unselected; cover screws in plastic only','MetalOperations':'Body turning plus TWO opposing indexed collar flats; cap turning plus ONE offset axial thermistor drilling','TipInterface':'Offset two-wire NTC; existing TMP117 circuit/firmware not compatible','Retention':'Motor seats on metal; insulated body board uses two foam pads extending into cap counterbore','PlasticTooling':'Draw along Y; 1.6mm nominal walls, about1.25mm at drafted nut well,2deg shell draft; root pad2mm','ClosureThread':'M30x1.5 proposed6H/6g;6mm full male thread plus explicit lead-in and2.25mm reliefs. CAD pilot/root envelopes are NOT finished thread surfaces','RearThread':'M18x1 proposed6g/6H;3.5mm full male/root envelope plus0.5mm lead and0.75mm relief. Supplier gaging/strength/torque and nut lock OPEN','NoseSeal':'Candidate32x1 face O-ring; glandID31.6 OD34.8 depth0.78 atY64. Tolerances/closure/finish unresolved','SensorTooling':'2.5mm drill atX7.8;12.5mm cylindrical depth plus140deg point. Deep counterbore requires holder reach review; see DFM.md and review.json'}.items():
    params.addProperty('App::PropertyString',key,'DesignIntent');setattr(params,key,value)
D.recompute();active=list(parts.Group)+list(refs.Group);hits=[]
for a,b in itertools.combinations(active,2):
 vol=overlap(a.Shape,b.Shape)
 if vol>1e-4:hits.append({'a':a.Label,'b':b.Label,'intersection_mm3':vol})
print('ASSEMBLY INTERSECTIONS',json.dumps(hits),flush=True)
assert not hits,'Resolve full-assembly hard-part intersections'
for o in active:assert o.Shape.isValid(),o.Name
for o in list(parts.Group)+[nut]:
 o.Shape.exportStep(str(OUT/(o.Label+'.step')))
 # OCCT emits trailing spaces on wrapped STEP records; normalize before readback/hash.
 exchange=OUT/(o.Label+'.step');exchange.write_text('\n'.join(line.rstrip()for line in exchange.read_text().splitlines())+'\n')
 back=Part.Shape();back.read(str(OUT/(o.Label+'.step')));assert back.isValid()and len(back.Solids)==1
 # Plastic parts get a purposeful flat-face printing orientation.
 if o in (base,cover):
  s=o.Shape.copy();s.rotate(A.Vector(),A.Vector(1,0,0),-90 if o==base else 90);bb=s.BoundBox;s.translate(A.Vector(-bb.XMin,-bb.YMin,-bb.ZMin));m=MeshPart.meshFromShape(Shape=s,LinearDeflection=.04,AngularDeflection=.2,Relative=False);assert m.isSolid();m.write(str(OUT/(o.Label+'.stl')));printed.append(o.Label)
for o in active+list(soft.Group):
 m=MeshPart.meshFromShape(Shape=o.Shape,LinearDeflection=.08,AngularDeflection=.2,Relative=False);m.write(str(OUT/(o.Label+'-view.stl')))
clip=Part.makeBox(200,200,50,A.Vector(-100,-50,-50))
for o in (body,cap):MeshPart.meshFromShape(Shape=o.Shape.common(clip),LinearDeflection=.08,AngularDeflection=.2,Relative=False).write(str(OUT/(o.Label+'-half-view.stl')))
rearclip=Part.makeBox(60,23,25,A.Vector(-30,-25,-25))
for o in (body,base):MeshPart.meshFromShape(Shape=o.Shape.common(rearclip),LinearDeflection=.04,AngularDeflection=.15,Relative=False).write(str(OUT/(o.Label+'-rear-half-view.stl')))
native=OUT/'ManufacturingLayout.FCStd';D.saveAs(str(native));result={
'native_sha256':sha(native),'source_native_sha256':sha(source),'builder_sha256':sha(Path(__file__)),
'main_rigid_custom_parts':[o.Label for o in parts.Group],
'native_object_names':{o.Label:o.Name for o in parts.Group},
'manufacturing_intent':'Two main custom metal parts: turned body with two indexed collar flats and turned cap with one offset sensor drill. Additional catalog-type thin nut is not vendor CAD or selected hardware.',
'body_bore':'12mm neck through bore, conical transition Y26..33, 28mm straight front bore; no internal bulge undercut',
'cap_joint':{
    'seam_Y_mm':64,
    'thread_callout':'M30x1.5 proposed6H/6g, body female/cap male;6mm nominal full male length/four pitches; strength/galling/fit/gaging not validated',
    'CAD_representation':'Female pilot28.5mm and male BASIC root28.1597mm envelopes, NO helical teeth; callout controls, never machine envelopes as finished thread',
    'seal':'Candidate32x1 face O-ring; metal faces set closure. Nominal22percent squeeze/63percent cross-section fill; full tolerance/material/closure review pending',
    'seal_dimensions_mm':{'candidate_ID':32,'candidate_section':1,'gland_ID':2*D.getObject('FaceGlandInner').Radius.Value,'gland_OD':2*D.getObject('FaceGlandOuter').Radius.Value,'depth':64-D.getObject('FaceGlandOuter').Placement.Base.y,'face_Y':64},
    'reliefs':'BodyID30.4x2.25 atY53.5..55.75; cap rootOD27.6x2.25 atY61.75..64. Indicative tool runout, NOT DIN76 compliance claim',
    'lead_ins':'Cap leadY54.75..55.75; body entryY62.95..63.7. Exact radii/tool exits to supplier review'
},
'rear_joint':{'shoulder_OD_mm':24,'shoulder_Y_mm':-8,'bore_mm':12,'stub_end_Y_mm':-14.25,'shoulder_to_stub_tip_mm':6.25,'collar_OD_mm':20,'collar_AF_mm':18.4,'collar_Y_mm':[-9.5,-8],'socket_OD_mm':20.2,'socket_AF_mm':18.6,'socket_bearing_thickness_mm':2,'collar_setback_from_nut_face_mm':.5,'rear_thread_callout':'M18x1 proposed6g/6H; pilot/root envelopes only, NO helical teeth','male_basic_root_diameter_mm':2*rear_root_radius,'full_male_thread_Y_mm':[-13.75,-10.25],'full_male_thread_length_mm':3.5,'thread_relief':{'OD_mm':16.4,'Y_mm':[-10.25,-9.5]},'tip_lead_Y_mm':[-14.25,-13.75],'nut':{'object_name':nut.Name,'AF_mm':24,'thickness_mm':4,'Y_mm':[-14,-10],'female_pilot_diameter_mm':17,'source':'Festo SIED mounting-nut dimensions: M18x1,24AF,4mm nominal; generic chamfers, not vendor CAD. ifm E10028 confirms an available stainless M18x1 nut type, not this envelope certification.'},'nut_lock':'OPEN: no tab washer, safety wire, rivet, threadlocker or other lock selected/modelled','axial_path':'Body shoulder/tray2mm root pad/thin nut; collar recessed so nut clamps plastic. No compression limiter. Preload and pull-through unqualified.','torsion_path':'Opposing collar flats and matching tray socket; no socket adhesive credited','wet_boundary':'Bonded boot cuff over unchanged recessed OD19.5 land Y-7..-3, flush to OD21 upper shoulder. Full boot/service closure unfinished','nut_well':{'front_OD_mm':28.6,'front_Y_mm':-10,'draft_degrees':2,'approximate_local_wall_mm':1.25},'status':'User-approved threaded-stub/thin-nut direction; nominal modeled study. Final nut/material/tolerances/torque, nut locking, creep and loads OPEN'},
'cap_motor':{'pocket_diameter_mm':11.1,'motor_end_stop_Y_mm':93.3,'pocket_entry_Y_mm':78,'status':'Actual press/retention fit and force pending; metal shoulder, independent of thermistor'},
'cap_sensor':{'drill_diameter_mm':2.5,'axis_XZ_mm':[7.8,0],'entry_Y_mm':78,'cylindrical_end_Y_mm':90.5,'drill_tip_Y_mm':90.5+1.25/math.tan(math.radians(70)),'cylindrical_depth_mm':12.5,'depth_to_diameter':5,'web_to_motor_bore_mm':1,'radial_wall_at_cylinder_end_mm':dome_radius(90.5)-7.8-1.25,'status':'140deg drill point modeled; agree remaining wall/tool wander and offset sensor thermal response'},
'separate_soft_part':'Silicone outer boot incomplete; root cuff only process reference',
'body_board_forward_shift_mm':10,'body_board_support':'Insulating sleeve and two foam pads spanY59..69 into cap counterbore; retention/adhesive/assembly jig still to trial',
'plastic_post_coring':'Front-access cores: case posts9.2mm deep, PCB seats9.4mm deep,0.5deg core draft; closed webs remain behind pilots/seats. Screw engagement/strip/creep still unqualified',
'nominal_plastic_wall_mm':1.6,'shell_draft_degrees':2,
'case_fasteners':'Two M2x6 concept into cored plastic pilots atX12,Z+/-13; final thread form/material/torque/engagement pending. Cover closure only.',
'flange_repackaging':{'PCB_seat_X_mm':-15.2,'case_screw_X_mm':12,'unselected_pack_rearward_shift_from_ring_study_mm':1.5,'pack_bounds_Y_mm':[-22.5,-14.5],'note':'CAD-only PCB tab/post changes; routed boards and actual pack/loom not qualified'},
'magnet_axes_XZ_mm':magaxes,'print_oriented_plastic_parts':printed,
'unexpected_hard_part_intersections':hits,
'noncritical_tool_radii_mm':{'body_bore_transitions':.4,'rear_collar_root_before_flats':.3,'gland_bottom':.1,'tray_socket_front_chamfer':.5,'limits':'Collar-flat terminations and thread relief/gland corners need supplier callouts; motor-seat corner awaits actual case edge'},
'metal_volumes_mm3':{o.Label:o.Shape.Volume for o in (body,cap)},
'electrical_changes_required':['Two-wire offset tip NTC analogue front end/calibration/fault handling','Flange PCB tabs/NPTHs and placement need actual layout/DRC','Cap/body-board loom with flange tails free during threading; actual insertion/service trial','Revised charging magnet mate'],
'dfm_sources':['https://www.protolabs.com/en-gb/services/cnc-machining/cnc-turning/','https://www.protolabs.com/resources/design-tips/mastering-complex-features-on-machined-parts/','https://www.festo.com/media/catalog/205036_documentation.pdf','https://www.ifm.com/gb/en/product/E10028','https://medias.schaeffler.cn/en/plp/Retainers','https://www.applerubber.com/seal-design-guide/seal-types-and-gland-design/o-ring-installation/','https://www.fictiv.com/articles/fictiv-cnc-machining-design-guide','https://hlhrapid.com/wp-content/uploads/2022/07/CNC-Machining-Design-Guide.pdf','https://www.hlhprototypes.com/design-tips-for-cnc-machining/','https://www.sandvik.coromant.com/en-gb/tools/silent-tools/what-is-silent-tools/application-guide-silent-tools/turning-appl-guide','https://books.industrialpress.com/9780831139322/machinerys-handbook-32-digital-edition/','https://guhring.com/Downloads/Item/9064050025000','https://www.haimer.com/shop/catalog/downloads/files/Tool-holders/Tool-holders_US.pdf'],
'scope':'DFM review study only. No material/stock supplier selected. Rear/nose thread fits and strength, nut lock, seal/boot, keyed-root strength/creep/pull-through, actual loom, tip drilling, machining/tooling, mass/wear and physical tests outstanding.'}
(OUT/'review.json').write_text(json.dumps(result,indent=2)+'\n');print('SAVED',native,flush=True)
