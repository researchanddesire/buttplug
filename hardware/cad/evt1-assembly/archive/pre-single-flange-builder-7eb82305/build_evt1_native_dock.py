"""Editable FreeCAD bodies/assembly for the pocket-toy dock. Run in FreeCAD GUI.

Sketches, additive/subtractive lofts and pockets are the authoring source.
No STL conversion or fit-envelope component substitutes are used here.
"""
from pathlib import Path
import json,math,hashlib,sys,importlib,time
import FreeCAD as App
import FreeCADGui as Gui
import Part,Sketcher
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
OUT=ROOT/'hardware/cad/evt1-assembly';OUT.mkdir(parents=True,exist_ok=True)
started=time.monotonic()
def progress(stage):
    (OUT/'build-progress.json').write_text(json.dumps({
        'stage':stage,'elapsed_seconds':time.monotonic()-started,
        'time_unix':time.time(),'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
progress('starting native component construction')
for existing in list(App.listDocuments().values()):
    if existing.Name=='CompassDockNative' or existing.FileName==str(OUT/'DockAssembly.FCStd'):
        App.closeDocument(existing.Name)
D=App.newDocument('CompassDockNative')
D.Label='Compass dock / editable EVT assembly / nominal review'
params=D.addObject('Spreadsheet::Sheet','Parameters')
for row,(alias,value) in enumerate((('CaseWidth','130 mm'),('CaseLength','165 mm'),('CornerRadius','50 mm'),('CenterY','77.5 mm'),('SplitHeight','40 mm'),('OverallHeight','68 mm'),('Wall','3 mm'),('HingeY','164.4 mm'),('HingeZ','40.15 mm')),1):
    params.set('A'+str(row),alias);params.set('B'+str(row),value);params.setAlias('B'+str(row),alias)
motion=D.addObject('App::FeaturePython','Motion')
motion.addProperty('App::PropertyAngle','OpeningAngle','Hinge')
motion.OpeningAngle=0
# Keeping this driver outside the geometry spreadsheet avoids rebuilding every
# case loft/pocket when only the hinge angle changes.
D.recompute()
designs=D.addObject('App::Part','ComponentDesigns');designs.Label='Editable component bodies'
assembly=D.addObject('Assembly::AssemblyObject','DockAssembly');assembly.Type='Assembly';joints=assembly.newObject('Assembly::JointGroup','Joints')
parts=[];profile_checks=[];upper_parts=[];selected=[];extra_base_components=[];extra_lid_components=[]
external_sources=[]
source_documents={}
COLORS={'base':(.19,.20,.22),'lid':(1.0,.32,.045),'cream':(.90,.86,.76),'blue':(.02,.57,.81)}
def body(name,color):
    b=D.addObject('PartDesign::Body',name);designs.addObject(b)
    if b.ViewObject:b.ViewObject.ShapeColor=COLORS[color]
    parts.append(b);return b

def rr(b,name,w,h,r,z,center=(0,77.5),expressions=None):
    s=b.newObject('Sketcher::SketchObject',name);s.Placement.Base=App.Vector(center[0],center[1],z)
    hx,hy=w/2,h/2;v=lambda x,y:App.Vector(x,y,0);q=math.sqrt(.5)
    seq=[((-hx+r,-hy),(hx-r,-hy),None),((hx-r,-hy),(hx,-hy+r),(hx-r+r*q,-hy+r-r*q)),((hx,-hy+r),(hx,hy-r),None),((hx,hy-r),(hx-r,hy),(hx-r+r*q,hy-r+r*q)),((hx-r,hy),(-hx+r,hy),None),((-hx+r,hy),(-hx,hy-r),(-hx+r-r*q,hy-r+r*q)),((-hx,hy-r),(-hx,-hy+r),None),((-hx,-hy+r),(-hx+r,-hy),(-hx+r-r*q,-hy+r-r*q))]
    for a,c,m in seq:s.addGeometry(Part.LineSegment(v(*a),v(*c)) if m is None else Part.Arc(v(*a),v(*m),v(*c)),False)
    for i in range(8):s.addConstraint(Sketcher.Constraint('Tangent',i,2,(i+1)%8,1))
    for i in (0,4):s.addConstraint(Sketcher.Constraint('Horizontal',i))
    for i in (2,6):s.addConstraint(Sketcher.Constraint('Vertical',i))
    for i in (3,5,7):s.addConstraint(Sketcher.Constraint('Equal',1,i))
    for key,c in (('Corner',Sketcher.Constraint('Radius',1,r)),('Width',Sketcher.Constraint('DistanceX',6,1,2,1,w)),('Length',Sketcher.Constraint('DistanceY',0,1,4,1,h))):
        n=s.addConstraint(c);s.renameConstraint(n,key)
    s.addConstraint(Sketcher.Constraint('Symmetric',6,1,2,1,-1,1))
    if expressions:
        for key,value in expressions.items():s.setExpression('Constraints.'+key,value)
    D.recompute();assert s.FullyConstrained,(name,s.SolverMessages if hasattr(s,'SolverMessages') else 'Underconstrained')
    profile_checks.append(s.Name);s.Visibility=False;return s

def case_profile(b,name,w,h,r,z):
    return rr(b,name,w,h,r,z,expressions={'Width':'Parameters.CaseWidth'+('%+g mm'%(w-130)), 'Length':'Parameters.CaseLength'+('%+g mm'%(h-165)),'Corner':'Parameters.CornerRadius'+('%+g mm'%(r-50))})

def loft(b,name,profiles,subtract=False,ruled=False):
    o=b.newObject('PartDesign::SubtractiveLoft' if subtract else 'PartDesign::AdditiveLoft',name);o.Profile=profiles[0];o.Sections=profiles[1:];o.Ruled=ruled;D.recompute()
    assert not o.Shape.isNull() and o.Shape.isValid() and len(o.Shape.Solids)==1,name
    for s in profiles:s.Visibility=False
    return o

def pocket(b,name,s,length,reversed=False):
    o=b.newObject('PartDesign::Pocket',name);o.Profile=s;o.Length=length;o.Reversed=reversed;D.recompute();assert not o.Shape.isNull() and o.Shape.isValid() and len(o.Shape.Solids)==1,name;s.Visibility=False;return o

def pad(b,name,s,length):
    o=b.newObject('PartDesign::Pad',name);o.Profile=s;o.Length=length;D.recompute();assert o.Shape.isValid() and len(o.Shape.Solids)==1,name;s.Visibility=False;return o

def native_extrusions(b,name,tools,subtract=False):
    """Retain exact helper contours as native Pocket/Pad features, not frozen booleans."""
    assert tools,name
    boxes=[t.optimalBoundingBox(False,False)for t in tools]
    low,high=boxes[0].ZMin,boxes[0].ZMax
    assert all(abs(bb.ZMin-low)<1e-7 and abs(bb.ZMax-high)<1e-7 for bb in boxes),name
    # Helper cut regions may overlap (LCD carrier ears and capsule arms).
    # One sketch needs the union boundary, rather than intersecting loops.
    union=tools[0]
    for tool in tools[1:]:union=union.fuse(tool)
    tools=list(union.removeSplitter().Solids)
    assert tools,name
    boxes=[t.optimalBoundingBox(False,False)for t in tools]
    z=high if subtract else low
    s=b.newObject('Sketcher::SketchObject',name+'Profile');s.Placement.Base.z=z
    tool_contours=[]
    for tool,bb in zip(tools,boxes):
        faces=[f for f in tool.Faces if abs(f.optimalBoundingBox(False,False).ZMin-low)<1e-7
               and abs(f.optimalBoundingBox(False,False).ZMax-low)<1e-7]
        assert len(faces)==1,name
        assert abs(tool.Volume-faces[0].Area*(high-low))<1e-6,name
        face=faces[0];wires=[face.OuterWire]+[w for w in face.Wires if not w.isSame(face.OuterWire)]
        contours=[]
        for wire in wires:
            indices=[]
            for edge in wire.Edges:
                p=lambda t:App.Vector(edge.valueAt(t).x,edge.valueAt(t).y,0)
                a,c=edge.FirstParameter,edge.LastParameter
                if isinstance(edge.Curve,Part.Line):
                    geom=Part.LineSegment(p(a),p(c))
                else:
                    assert isinstance(edge.Curve,Part.Circle),(name,type(edge.Curve))
                    if abs(c-a-2*math.pi)<1e-7:
                        center=edge.Curve.Center
                        geom=Part.Circle(App.Vector(center.x,center.y,0),App.Vector(0,0,1),edge.Curve.Radius)
                    else:
                        geom=Part.Arc(p(a),p((a+c)/2),p(c))
                n=s.addGeometry(geom,False);s.addConstraint(Sketcher.Constraint('Block',n));indices.append(n)
            contours.append(indices)
        tool_contours.append(contours)
    D.recompute();assert s.FullyConstrained,name
    profile_checks.append(s.Name)
    rebuilt=[]
    for contours in tool_contours:
        faces=[Part.Face(Part.Wire([s.Geometry[i].toShape()for i in indices]))for indices in contours]
        face=faces[0]
        for hole in faces[1:]:face=face.cut(hole)
        face.translate(App.Vector(0,0,z))
        rebuilt.append(face.extrude(App.Vector(0,0,low-high if subtract else high-low)))
    generated=Part.makeCompound(rebuilt)
    original=Part.makeCompound(tools)
    assert generated.cut(original).Volume<1e-6 and original.cut(generated).Volume<1e-6,name
    return pocket(b,name,s,high-low)if subtract else pad(b,name,s,high-low)

def circle(b,name,r,position,rotation=None):
    s=b.newObject('Sketcher::SketchObject',name)
    s.Placement=App.Placement(App.Vector(*position),rotation or App.Rotation())
    s.addGeometry(Part.Circle(App.Vector(),App.Vector(0,0,1),r),False)
    s.addConstraint(Sketcher.Constraint('Coincident',0,3,-1,1))
    s.addConstraint(Sketcher.Constraint('Radius',0,r));D.recompute()
    assert s.FullyConstrained,name
    profile_checks.append(s.Name);return s

def xz_profile(b,name,w,h,r,position,front=True):
    s=rr(b,name,w,h,r,0,(0,0))
    s.Placement=App.Placement(App.Vector(*position),App.Rotation(App.Vector(1,0,0),-90 if front else 90))
    return s

def scallop(b,name,z,clearance=0):
    s=b.newObject('Sketcher::SketchObject',name);s.Placement.Base=App.Vector(0,78,z)
    pts=[]
    for i in range(144):
        t=2*math.pi*i/144;f=1+.045*math.cos(12*t)
        pts.append(App.Vector((40+clearance)*f*math.cos(t),(32+clearance)*f*math.sin(t),0))
    c=Part.BSplineCurve();c.interpolate(Points=pts,PeriodicFlag=True)
    s.addGeometry(c,False);s.addConstraint(Sketcher.Constraint('Block',0));D.recompute()
    assert s.FullyConstrained;profile_checks.append(s.Name);return s

def note(obj,prop,value,group='Engineering'):
    obj.addProperty('App::PropertyString',prop,group);setattr(obj,prop,value)

def open_source(path):
    path=path.resolve()
    if path in source_documents:return source_documents[path]
    for document in list(App.listDocuments().values()):
        if document.FileName==str(path):App.closeDocument(document.Name)
    doc=App.openDocument(str(path));source_documents[path]=doc
    external_sources.append({'file':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    return doc

base=body('LowerShell','base')
loft(base,'LowerOuterLoft',[case_profile(base,'BaseBottom',124,159,47,0),case_profile(base,'BaseBulge',130,165,50,4),case_profile(base,'BaseRim',130,165,50,40)],ruled=True)
pocket(base,'LowerCavity',case_profile(base,'LowerCavityProfile',124,159,47,40),37)
# Front-centre socket matches the concept; package geometry is linked below.
usb_window=rr(base,'USBOpeningProfile',11.4,5.6,.5,0,(0,0))
usb_window.Placement=App.Placement(App.Vector(0,-5.3,7.9),App.Rotation(App.Vector(1,0,0),90))
pocket(base,'USBOpening',usb_window,4.2)
usb_mcad=json.loads((ROOT/'hardware/pcb/evt1/dock/mcad.json').read_text())
for i,h in enumerate(h for h in usb_mcad['holes'] if h['ref'].startswith('H')):
    u,v=h['xy_mm'];x,y=v-11,u-1.5
    pad(base,'USBMountBoss'+str(i),circle(base,'USBMountProfile'+str(i),2.4,(x,y,3)),2.4)
    pocket(base,'USBMountPilot'+str(i),circle(base,'USBMountPilotProfile'+str(i),.8,(x,y,5.4)),4)
lid=body('UpperShell','lid');upper_parts.append(lid)
loft(lid,'UpperOuterLoft',[case_profile(lid,'LidRim',130,165,50,40.3),case_profile(lid,'LidBulge',132,167,51,44),case_profile(lid,'LidShoulder',124,159,47,62),case_profile(lid,'LidCrown',110,145,40,68)])
loft(lid,'UpperCavity',[case_profile(lid,'InnerLidRim',124,159,47,39.9),case_profile(lid,'InnerLidBulge',126,161,48,44),case_profile(lid,'InnerLidShoulder',118,153,44,60),case_profile(lid,'InnerLidRoof',112,147,41,64)],subtract=True)
# Real case opening; LCD part and its footprint are added from the selected drawing.
pocket(lid,'BezelSeat',scallop(lid,'BezelSeatProfile',68.1,.25),.7)
# A broad rounded control foot joins the scallops and contains the outer
# buttons' retained rails. The earlier ellipse did not support those rails.
pocket(lid,'BezelControlFootSeat',rr(lid,'BezelControlFootSeatProfile',72.5,17.5,7.25,68.1,(0,53)),.7)
# Selected LCD front glass passes into this opening; the bezel masks its rim.
pocket(lid,'DisplayOpening',rr(lid,'DisplayOpeningProfile',48.6,36.6,.5,69,(0,83)),9)
bezel=body('ScallopedBezel','cream');upper_parts.append(bezel)
pad(bezel,'BezelPlate',scallop(bezel,'ScallopedOutline',67.7),2.8)
pad(bezel,'BezelControlFoot',rr(bezel,'BezelControlFootProfile',72,17,7,67.7,(0,53)),2.8)
pocket(bezel,'DisplayWindow',rr(bezel,'DisplayWindowProfile',44.4,24.4,1,71,(0,87)),4)
# Clearance for the actual glass, not a fictitious display block.
pocket(bezel,'DisplayGlassSeat',rr(bezel,'DisplayGlassSeatProfile',48.6,36.6,.5,67.6,(0,83)),1.5,True)
import build_evt1_dock_button_mechanics as button_module
importlib.reload(button_module)
button_components=button_module.build_components(D)
button_cap_bodies=button_components['caps'];button_spring_bodies=button_components['springs']
for b in button_cap_bodies+button_spring_bodies:
    designs.addObject(b);parts.append(b);upper_parts.append(b)
fixed=button_components['fixed_features']
native_extrusions(lid,'ButtonRoofClearances',fixed['orange_roof_cuts'],True)
native_extrusions(lid,'ButtonRoofRetainedStops',fixed['orange_roof_downstop_and_return_adds'])
native_extrusions(bezel,'ButtonVisiblePassages',fixed['cream_bezel_cuts'][::2],True)
native_extrusions(bezel,'ButtonHiddenMotion',fixed['cream_bezel_cuts'][1::2],True)
native_extrusions(bezel,'ButtonBezelRetainedStops',fixed['cream_bezel_upstop_guide_adds'])
progress('retained button guides and scalloped control area constructed')
import build_evt1_dock_lcd_retention as lcd_retention_module
importlib.reload(lcd_retention_module)
lcd_retention=lcd_retention_module.build_components(D)
lcd_retention_group=D.addObject('App::Part','LCDRetentionModule');designs.addObject(lcd_retention_group)
for component in lcd_retention['parts']:lcd_retention_group.addObject(component)
extra_lid_components.append(lcd_retention_group);upper_parts.append(lcd_retention_group)
# The actual folded ribbon exits the glass below the bezel and turns beneath
# the lid roof. Both printed pieces need relief; hiding the FFC is not a fit.
pocket(lid,'DisplayRibbonBay',rr(lid,'DisplayRibbonBayProfile',15.2,8.5,.5,68.2,(0,61.3)),7)
pocket(bezel,'DisplayRibbonExit',rr(bezel,'DisplayRibbonExitProfile',15.2,8.5,.5,67.6,(0,61.3)),.6,True)

# A pin hinge built into both shells. Eye gaps are 0.4mm axial and the trial
# bore is 3.4mm for a custom 3mm pin; print/process fit still needs qualification.
axis_rotation=App.Rotation(App.Vector(0,1,0),90)
for i,(x,length) in enumerate(((-36,22),(14,22))):
    pad(base,'BaseHingeWeb'+str(i),rr(base,'BaseHingeWebProfile'+str(i),length,10,.8,34,(x+length/2,159.4)),6)
    pad(base,'BaseHingeEye'+str(i),circle(base,'BaseHingeEyeProfile'+str(i),4.25,(x,164.4,40.15),axis_rotation),length)
    pocket(base,'BaseHingeBore'+str(i),circle(base,'BaseHingeBoreProfile'+str(i),1.7,(x-.05,164.4,40.15),axis_rotation),length+.1,True)
pad(lid,'LidHingeWeb',rr(lid,'LidHingeWebProfile',27.2,10,.8,40.3,(0,159.4)),5.7)
pad(lid,'LidHingeEye',circle(lid,'LidHingeEyeProfile',4.25,(-13.6,164.4,40.15),axis_rotation),27.2)
pocket(lid,'LidHingeBore',circle(lid,'LidHingeBoreProfile',1.7,(-13.65,164.4,40.15),axis_rotation),27.3,True)
for i,x in enumerate((-36.2,13.8)):
    pocket(lid,'OuterHingeEyeClearance'+str(i),circle(lid,'OuterHingeEyeClearanceProfile'+str(i),4.55,(x,164.4,40.15),axis_rotation),22.4,True)
hinge_pin=body('CustomHingePin','base')
pad(hinge_pin,'HingePinShaft',circle(hinge_pin,'HingePinProfile',1.5,(-36.4,164.4,40.15),axis_rotation),72.8)
pad(hinge_pin,'HingePinHead',circle(hinge_pin,'HingePinHeadProfile',2.6,(-37.4,164.4,40.15),axis_rotation),1.01)
pocket(hinge_pin,'HingePinEndTapPilot',circle(hinge_pin,'HingePinEndTapProfile',.8,(36.5,164.4,40.15),axis_rotation),4.8)
note(hinge_pin,'Manufacturing','Custom turned stainless pin: diameter3 x72.8mm under-head length, diameter5.2 x1mm head; finish blind M2x0.4 thread at opposite end, >=4.3mm full thread, pilot depth4.7mm from end. Nominal0.79mm total axial eye clearance. Thread-major geometry, retention strength and loosening/received tolerances require trial.')
washer=body('HingeRetainingWasher','base')
s=circle(washer,'HingeWasherProfile',2.5,(36.4,164.4,40.15),axis_rotation)
s.addGeometry(Part.Circle(App.Vector(),App.Vector(0,0,1),1.1),False)
s.addConstraint(Sketcher.Constraint('Coincident',1,3,-1,1));s.addConstraint(Sketcher.Constraint('Radius',1,1.1))
D.recompute();assert s.FullyConstrained
pad(washer,'HingeWasherPad',s,.3)
note(washer,'ManufacturerPartNumber','PTS A12502A / M2 DIN125 A2 stainless')
note(washer,'SourceURL','https://www.pts-uk.com/products/washers/form-a-flat-washers/metric-a2/A12502A')
note(washer,'ModelBasis','Published plain washer profile: ID2.2, OD5.0..4.7, thickness0.25..0.35mm; nominal0.30mm model. Received inspection required. No edge breaks modeled.')

# Smooth cream chamber parts give the concept its interior. These are native
# components with real walls; UV metal backing, mounts and device seats follow.
liner=body('LowerChamber','cream')
pad(liner,'ChamberOuter',rr(liner,'ChamberOuterProfile',123.4,158.4,46.7,11),26)
pocket(liner,'ChamberCavity',rr(liner,'ChamberCavityProfile',119.4,154.4,44.7,37),24)
# Install the liner before the complete contact module. Only its two feet and
# the offset wire feedthrough penetrate the floor; collars/hood form light traps.
for i,x in enumerate((-43,-15)):
    pocket(liner,'ContactFootPassage'+str(i),
           rr(liner,'ContactFootPassageProfile'+str(i),8,8,.4,13.1,(x,19)),2.2)
pocket(liner,'ContactWireFloorPassage',
       rr(liner,'ContactWireFloorPassageProfile',6,2,.2,13.1,(-28,14)),2.2)
for i,x in enumerate((-25,25)):
    # The liner must pass the integral hinge webs during vertical installation,
    # not merely clear them at its final height. Slots run through its floor.
    pocket(liner,'HingeWebClearance'+str(i),rr(liner,'HingeWebClearanceProfile'+str(i),22.6,10.6,.4,37.1,(x,159.4)),26.2)
for i,(x,y) in enumerate(((-52,60),(52,60),(-52,115),(52,115))):
    pad(base,'ChamberMountBoss'+str(i),circle(base,'ChamberMountProfile'+str(i),2.6,(x,y,3)),8)
    pocket(base,'ChamberMountPilot'+str(i),circle(base,'ChamberMountPilotProfile'+str(i),.8,(x,y,11.05)),7.9)
    pocket(liner,'ChamberMountBore'+str(i),circle(liner,'ChamberMountBoreProfile'+str(i),1.1,(x,y,13.1)),2.2)
    # DIN965 heads have a finite cylindrical rim in addition to their cone.
    pocket(liner,'ChamberHeadRimClearance'+str(i),circle(liner,'ChamberHeadRimProfile'+str(i),2.15,(x,y,13.1)),.45)
    loft(liner,'ChamberMountCountersink'+str(i),[circle(liner,'ChamberSinkOuter'+str(i),2.15,(x,y,12.7)),circle(liner,'ChamberSinkInner'+str(i),1.1,(x,y,11.65))],subtract=True,ruled=True)
note(liner,'LoadingSequence','Install before device and UV modules; full-depth rear slots clear integral hinge webs. Four M2x6 countersunk screw candidates fasten floor to shell bosses. Finished tap/torque and UV backing remain unqualified.')
upper_liner=body('UpperChamber','cream');upper_parts.append(upper_liner)
loft(upper_liner,'UpperChamberOuter',[rr(upper_liner,'ChamberRim',123.4,158.4,46.7,40.6),rr(upper_liner,'ChamberRoof',110,145,40,57.5)])
loft(upper_liner,'UpperChamberVoid',[rr(upper_liner,'ChamberOpen',119.4,154.4,44.7,40.5),rr(upper_liner,'ChamberInsideRoof',106,141,38,55.5)],subtract=True)
pocket(upper_liner,'UpperHingeWebClearance',rr(upper_liner,'UpperHingeWebClearanceProfile',27.8,10.6,.4,46.2,(0,159.4)),5.8)
pocket(upper_liner,'ContactHeadCornerBay',rr(upper_liner,'ContactHeadCornerBayProfile',6.8,8.5,.3,53.4,(-43.2,17.85)),11.4)
note(upper_liner,'UVStatus','Plastic interior study; metal opaque UV backing, heatspreaders, apertures and leakage qualification are not yet implemented')
import build_evt1_dock_board_mounts as board_mount_module
importlib.reload(board_mount_module)
board_mount_checks=board_mount_module.add(D,base,lid,liner,upper_liner,
    {name:globals()[name]for name in ('circle','pad','pocket','loft','rr','note','native_extrusions')},
    bezel=bezel)
progress('actual PCB support posts and liner apertures constructed')
for target,key,label in ((lid,'roof_cuts','LCDCarrierRoofRelief'),(bezel,'bezel_gasket_cuts','LCDFrontPadSeats')):
    planes={}
    for shape in lcd_retention['fixed_features'][key]:
        bb=shape.optimalBoundingBox(False,False)
        planes.setdefault((round(bb.ZMin,6),round(bb.ZMax,6)),[]).append(shape)
    for i,tools in enumerate(planes.values()):native_extrusions(target,label+str(i),tools,True)
import build_evt1_dock_cutoff_mounts as cutoff_mount_module
importlib.reload(cutoff_mount_module)
cutoff_mount_checks=cutoff_mount_module.add(D,liner,upper_liner,
    {name:globals()[name]for name in ('circle','pad','pocket','native_extrusions','note')})
import build_evt1_dock_device_seats as seat_module
importlib.reload(seat_module)
device_seats=seat_module.build_components(D)
seat_module.apply_liner_reliefs(liner)
seat_saddle=seat_module.apply_liner_saddle(liner)
seat_group=D.addObject('App::Part','DeviceSeatingModule');designs.addObject(seat_group)
for component in device_seats['parts']:seat_group.addObject(component)
extra_base_components.append(seat_group)
import build_evt1_dock_uv_modules as uv_module
importlib.reload(uv_module)
for side,shell,destination in (('Base',base,extra_base_components),('Lid',lid,extra_lid_components)):
    thermal=uv_module.build_components(D,side=side,prefix='Dock'+side+'UV',include_board=False)
    group=D.addObject('App::Part',side+'UVThermalModule');designs.addObject(group)
    for component in thermal['parts']:group.addObject(component)
    destination.append(group)
    if side=='Lid':upper_parts.append(group)
    planes={}
    for shape in thermal['shell_shoulder_adds']:
        bb=shape.optimalBoundingBox(False,False)
        planes.setdefault((round(bb.ZMin,6),round(bb.ZMax,6)),[]).append(shape)
    for i,tools in enumerate(planes.values()):
        native_extrusions(shell,side+'UVThermalCaptureShoulder'+str(i),tools)
progress('shells, hinge and PCB mount features constructed')

# Actual purchased display and selected spring contact source models.
import build_evt1_dock_display as lcd_module
importlib.reload(lcd_module)
lcd=lcd_module.build(D,ffc_pose='installed');designs.addObject(lcd);upper_parts.append(lcd);selected.append(lcd)
lcd.Placement.Base=App.Vector(0,87,68.8)
lcd_checks=lcd_module.validate_installed(lcd)
import build_evt1_dock_lcd_socket as socket_module
importlib.reload(socket_module)
ui_shims=socket_module.build_trial_shims(D)
designs.addObject(ui_shims);upper_parts.append(ui_shims)
button_components['parameters'].set('B1','='+ui_shims.Parameters.Name+'.PCBTopZ')
D.recompute()
cutoff_settings=D.addObject('App::FeaturePython','LidCutoffActuatorSettings')
for prop in ('LeftBackout','RightBackout'):
    cutoff_settings.addProperty('App::PropertyLength',prop,'Commissioning trial')
    setattr(cutoff_settings,prop,cutoff_mount_module.NOMINAL_BACKOUT)
note(cutoff_settings,'Status','Nominal geometry only; received switches require electricalOP/RP and actualhead/nut adjustment, locked independently. Do not infer allowedtravel or opticalshutdown from these editable references.')
import build_evt1_dock_lid_cutoff as cutoff_module
importlib.reload(cutoff_module)
for name,x,prop in (('LidSwitchA',-50.5,'LeftBackout'),('LidSwitchB',50.5,'RightBackout')):
    component=cutoff_module.build(D,name,pose='operating_reference')
    component.Parameters.setExpression('BladeContactReferenceHeight','8.5 mm - '+cutoff_settings.Name+'.'+prop)
    component.Placement=App.Placement(App.Vector(x,30,31),App.Rotation(App.Vector(0,0,1),90))
    designs.addObject(component);extra_base_components.append(component)
import build_evt1_dock_pogo as pogo_module
importlib.reload(pogo_module)
pogo=pogo_module.build(D,.6);designs.addObject(pogo);selected.append(pogo)
pogo_checks=pogo_module.validate(pogo)
pogo.Visibility=False

# Native carrier follows the physical right-handed StepUp board frame. The
# wire lands are at Z45.3, not the mirrored Z41.7 of the earlier fit drawing.
carrier=body('ContactCarrier','cream')
pad(carrier,'CarrierBlank',rr(carrier,'CarrierBlankProfile',36,6.7,.4,17,(-28,19.35)),36)
for i,x in enumerate((-43,-15)):
    pad(carrier,'CarrierLeg'+str(i),rr(carrier,'CarrierLegProfile'+str(i),6,6.7,.2,8.4,(x,19.35)),8.9)
    pad(carrier,'CarrierFoot'+str(i),rr(carrier,'CarrierFootProfile'+str(i),7,7,.5,5.5,(x,19)),3)
    pad(carrier,'CarrierFloorLightTrap'+str(i),
        rr(carrier,'CarrierFloorLightTrapProfile'+str(i),10,10,.5,13.3,(x,19)),1)
    pocket(carrier,'CarrierMountBore'+str(i),circle(carrier,'CarrierMountBoreProfile'+str(i),1.25,(x,19,13.5)),8.1)
    pad(base,'ContactMountBoss'+str(i),circle(base,'ContactMountProfile'+str(i),3,(x,19,3)),2.5)
    pocket(base,'ContactMountPassage'+str(i),circle(base,'ContactMountPassageProfile'+str(i),1.65,(x,19,5.6)),5.7)
    pocket(base,'ContactHeadRimClearance'+str(i),circle(base,'ContactHeadRimProfile'+str(i),3,(x,19,-.05)),.5,True)
    loft(base,'ContactMountCountersink'+str(i),[circle(base,'ContactSinkOuter'+str(i),3,(x,19,.4)),circle(base,'ContactSinkInner'+str(i),1.65,(x,19,1.75))],subtract=True,ruled=True)
pocket(carrier,'PinBoardRecess',xz_profile(carrier,'PinBoardRecessProfile',28.4,10.4,.15,(-28,15.9,41.8),False),2.8962)
pocket(carrier,'CarrierWireWindow',xz_profile(carrier,'CarrierWireWindowProfile',22,3.2,.2,(-28,15.9,45.3),False),2.2)
pocket(carrier,'ContactLacingReturnChannel',
       xz_profile(carrier,'ContactLacingReturnProfile',14,2.6,.3,(-28,15.9,34),False),1.5)
for i,x in enumerate((-38,-32,-26,-20)):
    pocket(carrier,'BarrelClearance'+str(i),circle(carrier,'BarrelClearanceProfile'+str(i),1.05,(x,18.7,43.5),App.Rotation(App.Vector(1,0,0),90)),4.1)
    s=circle(carrier,'MetalFaceStopProfile'+str(i),1.5,(x,22.7,43.5),App.Rotation(App.Vector(1,0,0),-90))
    s.addGeometry(Part.Circle(App.Vector(),App.Vector(0,0,1),.9),False)
    s.addConstraint(Sketcher.Constraint('Coincident',1,3,-1,1));s.addConstraint(Sketcher.Constraint('Radius',1,.9));D.recompute();assert s.FullyConstrained
    pad(carrier,'MetalFaceStop'+str(i),s,.5)
for i,(x,z) in enumerate(((-38.5,24),(-21,21.5))):
    pocket(carrier,'KeeperMagnetPocket'+str(i),circle(carrier,'KeeperMagnetPocketProfile'+str(i),4.15,(x,15.9,z),App.Rotation(App.Vector(1,0,0),90)),6.3)
retainer=body('ContactRetainer','cream')
pad(retainer,'RetainerBack',rr(retainer,'RetainerBackProfile',36,2,.2,17,(-28,15)),32)
pad(retainer,'ContactWireLightTrapHood',
    rr(retainer,'ContactWireHoodProfile',8,8,.2,13.3,(-28,12)),7.7)
pocket(retainer,'ContactWireHoodInterior',
       rr(retainer,'ContactWireHoodInteriorProfile',6,6.4,.1,20.2,(-28,12)),6.9)
pad(retainer,'ContactWireLightTrapBaffle',
    rr(retainer,'ContactWireBaffleProfile',6,.8,.1,13.3,(-28,11.1)),3.7)
pocket(retainer,'ContactWireHoodEntry',
       xz_profile(retainer,'ContactWireHoodEntryProfile',6,2,.3,(-28,7.9,17.5),False),1.1)
for i,(x,z) in enumerate(((-38.5,24),(-21,21.5))):
    # The same selected stock coil as the buttons keeps the loose magnet at
    # its rigid front seat. It cannot rattle through the old3.2mm empty space.
    pocket(retainer,'MagnetSpringSeat'+str(i),
           circle(retainer,'MagnetSpringSeatProfile'+str(i),2.6,(x,16,z),App.Rotation(App.Vector(1,0,0),-90)),.6)
    pad(retainer,'MagnetSpringPilot'+str(i),
        circle(retainer,'MagnetSpringPilotProfile'+str(i),1,(x,15.4,z),App.Rotation(App.Vector(1,0,0),-90)),.8)
pad(retainer,'PinBoardPressurePad',xz_profile(retainer,'PinBoardPressurePadProfile',28,10,.1,(-28,16,41.8)),1.7962)
pocket(retainer,'RearWireWindow',xz_profile(retainer,'RearWireWindowProfile',22,3.2,.2,(-28,18,45.3)),4.2)
for i,x in enumerate((-38,-32,-26,-20)):
    pocket(retainer,'SolderTailPassage'+str(i),circle(retainer,'SolderTailPassageProfile'+str(i),.9,(x,18,43.5),App.Rotation(App.Vector(1,0,0),-90)),4.2)
for i,x in enumerate((-33,-23)):
    pocket(retainer,'ContactLoomLacingSlot'+str(i),
           xz_profile(retainer,'ContactLoomLacingSlotProfile'+str(i),2,2.2,.2,(x,13.9,34),False),2.3)
for i,x in enumerate((-41.5,-13.5)):
    pocket(carrier,'RetainerScrewPilot'+str(i),circle(carrier,'RetainerScrewPilotProfile'+str(i),.8,(x,15.9,33),App.Rotation(App.Vector(1,0,0),90)),6.3)
    pocket(retainer,'RetainerScrewBore'+str(i),circle(retainer,'RetainerScrewBoreProfile'+str(i),1.1,(x,16.1,33),App.Rotation(App.Vector(1,0,0),-90)),2.2)
note(carrier,'Interface','0.6mm pin compression; insulating annular stops bear on metal target faces atY23.2. Silicone carries no contact datum load. Magnet/source/retention and physical tolerances remain unqualified.')
note(carrier,'MountAccess','Two underside-access M3x12 countersunk screw candidates into 2.5mm pilot / 8mm-deep carrier taps; no blocked top driver path. Exact screws, resin tap/torque and UV screw-hole opacity still need qualification.')
note(retainer,'WireInterface','Actual StepUp B.Cu J94 wire lands Z45.3; pressure pad and wire window follow physical board orientation. Installed loom/strain relief remains to design.')
note(retainer,'MagnetRetention','Two selected LC014B02S coils at nominal3.8mm keep S-08-03-N magnets against the fixed front wall. Magnet±0.1mm length gives3.7..3.9mm coil length before print tolerances; received force/solidheight and retainer strength require an inert trial. Preassemble carrier/retainer/PCB/pins/magnets OUTSIDE case before underside mounting; rear screw driver access is blocked after installation.')
note(retainer,'FloorInterface','Install lowerliner first, then preassembledcontactmodule through two8mm floor openings. Integral10mm collars atZ13.3 overlap holes across0.3mm floor gap. Wirehood has an offsetentry/middlebaffle/floorport. PrefeedPLT.6SM-C throughslots andcarrierreturnchannelZ34 beforeclosingretainer; tightenaroundfourwirebundle aftersoldering. Installedwire/tieposes, opticalleakage and physicalassembly remain unqualified.')
magnet_source=D.addObject('PartDesign::Body','SelectedDockMagnet');designs.addObject(magnet_source)
pad(magnet_source,'SelectedDockMagnetCylinder',
    circle(magnet_source,'SelectedDockMagnetProfile',4,(0,0,0)),3)
note(magnet_source,'ManufacturerPartNumber','supermagnete S-08-03-N')
note(magnet_source,'SourceURL','https://www.supermagnete.de/eng/data_sheet_S-08-03-N.pdf')
note(magnet_source,'ModelBasis','Manufacturer published8mm diameter/3mm height,both±0.1mm; axialN45/Ni-Cu-Ni,max80C. Exact nominal cylindrical part. No installedholdingforce or compassqualification is inferred.')
magnet_spring_source=button_module.spring(D,'SelectedDockMagnetSpring',0,3.8,0)
designs.addObject(magnet_spring_source)
shape=magnet_spring_source.Tip.Shape.copy();shape.translate(App.Vector(0,-54,0));magnet_spring_source.Tip.Shape=shape
magnet_source.Visibility=False;magnet_spring_source.Visibility=False
import build_evt1_dock_front_closure as closure_module
importlib.reload(closure_module)
closure_plugs={}
for side,shell,chamber,destination in (
        ('lower',base,liner,extra_base_components),('upper',lid,upper_liner,extra_lid_components)):
    closure_module.add_catch(shell,side)
    closure_module.add_liner_clearance(chamber,side)
    group=D.addObject('App::Part','FrontClosure'+side.title()+'Contents');designs.addObject(group)
    plug=closure_module.build_retainer(D,group,side,'FrontClosure'+side.title()+'Plug')
    closure_plugs[side]=plug
    plug.ViewObject.ShapeColor=COLORS['cream']
    for i in range(2):closure_module.build_magnet(D,group,side,i,'FrontClosure'+side.title()+'Magnet'+str(i))
    closure_module.build_screw(D,group,side,'FrontClosure'+side.title()+'Screw')
    destination.append(group)
    if side=='upper':upper_parts.append(group)
import build_evt1_dock_uv_labyrinth as seam_module
importlib.reload(seam_module)
seam_features=seam_module.add_labyrinth(base,lid)
seam_module.add_liner_entry_relief(upper_liner)
seam_module.add_lower_liner_loading_slots(liner)
seam_module.add_lower_slot_baffles(closure_plugs['lower'])
note(lid,'GripFinish','Integral17x9mm front grip: mask/paint cream for the concept finish. No separate unsupported cover. Exterior finish/process and UV opacity still require qualification.')
base_module=D.addObject('App::Part','BaseModule');designs.addObject(base_module)
lid_module=D.addObject('App::Part','LidModule');designs.addObject(lid_module)
progress('carrier and selected source geometry constructed')
for b in parts+[lcd,ui_shims]+extra_base_components+extra_lid_components:
    if hasattr(b,'Tip'):
        for feature in b.Group:
            if hasattr(feature,'Visibility'):feature.Visibility=False
        b.Tip.Visibility=True
    if b in parts:b.ViewObject.ShapeColor=(.76,.77,.78) if b in (hinge_pin,washer)or b in button_spring_bodies else COLORS['base' if b==base else 'lid' if b==lid else 'blue' if b in button_cap_bodies else 'cream']
    link=D.addObject('App::Link',b.Name+'Instance');link.setLink(b)
    link.LinkPlacement=b.Placement
    if b is ui_shims:
        link.setExpression('Placement.Base.z',ui_shims.Parameters.Name+'.PCBTopZ')
    (lid_module if b in upper_parts else base_module).addObject(link);link.Visibility=True;b.Visibility=False
for i,x in enumerate((-38,-32,-26,-20)):
    link=D.addObject('App::Link','PogoContact'+str(i+1));link.setLink(pogo);base_module.addObject(link)
    link.LinkPlacement=App.Placement(App.Vector(x,18.7962,43.5),App.Rotation(App.Vector(0,0,1),App.Vector(0,1,0)))
for i,(x,z) in enumerate(((-38.5,24),(-21,21.5))):
    for role,source,y in (('Magnet',magnet_source,19.2),('MagnetSpring',magnet_spring_source,15.4)):
        link=D.addObject('App::Link','DockTarget'+role+str(i));link.setLink(source);base_module.addObject(link)
        link.LinkPlacement=App.Placement(App.Vector(x,y,z),App.Rotation(App.Vector(1,0,0),-90))
# Selected screw geometry is a native dimension reconstruction, with cosmetic
# threads omitted. Intentional thread-major/pilot intersections are checked
# separately from head/liner/shell clearance by the saved-file verifier.
import build_evt1_dock_fasteners as fastener_module
importlib.reload(fastener_module)
for key,locations in (
    ('M2x6',[(x,y,12.75) for x,y in ((-52,60),(52,60),(-52,115),(52,115))]),
    ('M3x12',[(x,19,.25) for x in (-43,-15)])):
    source=fastener_module.build(D,key);designs.addObject(source);source.Visibility=False
    for i,point in enumerate(locations):
        link=D.addObject('App::Link','ChamberScrew'+str(i) if key=='M2x6' else 'CarrierScrew'+str(i))
        link.setLink(source);base_module.addObject(link)
        link.LinkPlacement=App.Placement(App.Vector(*point),App.Rotation() if key=='M2x6' else App.Rotation(App.Vector(1,0,0),180))
        note(link,'MatingCheck','Nominal thread-major shape intentionally overlaps the tapped pilot only; no thread profile or fastening strength is modeled.')
# Upper liner uses the same selected countersunk source, turned toward the
# roof. The eight UV board screws use ordinary cylindrical socket heads.
for i,(x,y) in enumerate(board_mount_module.UPPER_LINER_HOLES):
    link=D.addObject('App::Link','UpperChamberScrew'+str(i));link.setLink(D.SelectedScrewM2x6)
    lid_module.addObject(link)
    link.LinkPlacement=App.Placement(App.Vector(x,y,55.75),App.Rotation(App.Vector(1,0,0),180))
socket_sources={}
for key in ('M2x4Socket','M2x6Socket','M2x10Socket'):
    source=fastener_module.build(D,key);designs.addObject(source);source.Visibility=False
    socket_sources[key]=source
for i,(x,y) in enumerate(board_mount_module.UI_HOLES):
    link=D.addObject('App::Link','UIBoardScrew'+str(i));link.setLink(socket_sources['M2x6Socket'])
    lid_module.addObject(link)
    link.LinkPlacement=App.Placement(App.Vector(x,y,board_mount_module.UI_F_PLANE-1),App.Rotation(App.Vector(1,0,0),180))
    link.setExpression('Placement.Base.z',ui_shims.Parameters.Name+'.PCBTopZ - 1 mm')
for i,(x,y) in enumerate(board_mount_module.BEZEL_HOLES):
    link=D.addObject('App::Link','BezelScrew'+str(i));link.setLink(socket_sources['M2x6Socket'])
    lid_module.addObject(link)
    link.LinkPlacement=App.Placement(App.Vector(x,y,64),App.Rotation(App.Vector(1,0,0),180))
for i,(x,y) in enumerate(((-8,5.5),(8,5.5),(-8,23.5),(8,23.5),(-44,64),(44,55.7))):
    link=D.addObject('App::Link','MainBoardScrew'+str(i));link.setLink(socket_sources['M2x4Socket'])
    base_module.addObject(link);link.LinkPlacement=App.Placement(App.Vector(x,y,6.4),App.Rotation())
for i,x in enumerate((-41.5,-13.5)):
    link=D.addObject('App::Link','ContactRetainerScrew'+str(i));link.setLink(socket_sources['M2x6Socket'])
    base_module.addObject(link)
    link.LinkPlacement=App.Placement(App.Vector(x,14,33),App.Rotation(App.Vector(1,0,0),90))
for side,module,z,rotation in (
        ('Lower',base_module,13.2,App.Rotation()),
        ('Upper',lid_module,55.3,App.Rotation(App.Vector(1,0,0),180))):
    for i,(x,y) in enumerate(board_mount_module.UV_HOLES):
        link=D.addObject('App::Link',side+'UVScrew'+str(i));link.setLink(socket_sources['M2x6Socket'])
        module.addObject(link);link.LinkPlacement=App.Placement(App.Vector(x,y,z),rotation)
link=D.addObject('App::Link','HingeRetainingScrew');link.setLink(socket_sources['M2x4Socket'])
base_module.addObject(link)
link.LinkPlacement=App.Placement(App.Vector(36.7,164.4,40.15),axis_rotation)
note(link,'Retention','Nominal3.7mm engagement into the custom pin. Washer retains the eyes without clamping them; thread/pin retention and loosening need received-part/process qualification.')
nut_source=fastener_module.build_M2_nut(D);designs.addObject(nut_source);nut_source.Visibility=False
for side,sign,prop in (('Left',-1,'LeftBackout'),('Right',1,'RightBackout')):
    for i,y in enumerate((26.75,33.25)):
        link=D.addObject('App::Link',side+'LidCutoffMountScrew'+str(i))
        link.setLink(socket_sources['M2x10Socket']);base_module.addObject(link)
        link.LinkPlacement=App.Placement(App.Vector(sign*47.6,y,31),App.Rotation(App.Vector(0,1,0),-90*sign))
    link=D.addObject('App::Link',side+'LidCutoffAdjuster');link.setLink(socket_sources['M2x10Socket'])
    lid_module.addObject(link)
    link.LinkPlacement=App.Placement(App.Vector(sign*50.5,37.55,39.5),App.Rotation(App.Vector(1,0,0),180))
    link.setExpression('Placement.Base.z','41.5 mm - '+cutoff_settings.Name+'.'+prop)
    nut=D.addObject('App::Link',side+'LidCutoffJamnut');nut.setLink(nut_source);lid_module.addObject(nut)
    nut.LinkPlacement=App.Placement(App.Vector(sign*50.5,37.55,41.5),App.Rotation())
# FreeCAD requires a saved owner before an external document can be linked.
# A temporary native keeps the last successful assembly intact during a build.
D.recompute();D.saveAs(str(OUT/'.DockAssembly-building.FCStd'))
pin_doc=open_source(OUT/'pcb/PinPCB.FCStd')
pin_root=next(o for o in pin_doc.Objects if o.TypeId=='App::Part' and not any(p.Document==pin_doc for p in o.InList))
pin_link=D.addObject('App::Link','PinBoardAssembly');pin_link.setLink(pin_root);base_module.addObject(pin_link)
pin_link.LinkPlacement=App.Placement(App.Vector(-28,18.7962,41.8),App.Rotation(App.Vector(1,0,0),-90))
pin_root.Visibility=False
for name,module,z,rotation in (
        ('UVBase',base_module,13.2,App.Rotation()),
        ('UVLid',lid_module,55.3,App.Rotation(App.Vector(0,1,0),180))):
    source_path=OUT/'pcb'/(name+'.FCStd')
    source_doc=open_source(source_path)
    source_root=next(o for o in source_doc.Objects if o.TypeId=='App::Part'
                     and not any(p.Document==source_doc for p in o.InList))
    link=D.addObject('App::Link',name+'BoardAssembly');link.setLink(source_root);module.addObject(link)
    # StepUp puts the front package datum at Z0 and centres this U-shaped
    # board at dockY110.5. Rotate the upper board about Y to face inward
    # without reflecting its crossbar or moving its emitters away from Y94.
    link.LinkPlacement=App.Placement(App.Vector(0,110.5,z),rotation)
    note(link,'IntegrationStatus','Routed source-bound StepUp board with selected component models; thermal backing, opacity, installed loom and powered/optical qualification remain open.')
    source_root.Visibility=False
ui_doc=open_source(OUT/'pcb/LidUI.FCStd')
ui_root=next(o for o in ui_doc.Objects if o.TypeId=='App::Part'
             and not any(p.Document==ui_doc for p in o.InList))
ui_link=D.addObject('App::Link','UIBoardAssembly');ui_link.setLink(ui_root);lid_module.addObject(ui_link)
ui_link.LinkPlacement=App.Placement(App.Vector(0,84.5,board_mount_module.UI_F_PLANE),App.Rotation())
ui_link.setExpression('Placement.Base.z',ui_shims.Parameters.Name+'.PCBTopZ')
ui_root.Visibility=False
note(ui_link,'TrialHeight','Equal0.5..1.5mm shims at fixedZ61.5 seats; startingF60.5 is a received-socket trial datum. Loaded contact height, cable insertion/bend and received fit are not qualified.')
# The PCB remains a separate StepUp source document, with a real external link.
pcb_path=OUT/'pcb/MainPCB.FCStd';pcb_doc=open_source(pcb_path)
pcb_root=next(o for o in pcb_doc.Objects if o.TypeId=='App::Part' and not any(p.Document==pcb_doc for p in o.InList))
pcb_link=D.addObject('App::Link','USBBoardAssembly');pcb_link.setLink(pcb_root);base_module.addObject(pcb_link)
# The shared source/controller/safety snapshot has its outline centre atY32.
# StepUp front0/back-1 maps to finished boardtop6.4/bottom5.4.
pcb_link.LinkPlacement=App.Placement(App.Vector(0,32,6.4),App.Rotation())
note(pcb_link,'ElectricalRevision','Actual shared source/controller/safety placement with138selected package models and12copper-only sites; source-boundMCADsnapshot. Final routed-board geometry parity and fabrication qualification are separate gates.')
# Link only the actual device's exterior pieces, never its former fit proxies.
product_doc=open_source(OUT/'sources/ReadableEVT1Product.FCStd')
device=D.addObject('App::Part','DeviceAssembly');base_module.addObject(device)
for role in ('MetalBody','MotorThermistorCap','ContinuousSkin','Contact_GND','Contact_USB_DM','Contact_USB_DP','Contact_DOCK_5V','SteelKeeper0','SteelKeeper1'):
    source=product_doc.getObject(role);assert source is not None and source.Shape.isValid(),role
    link=D.addObject('App::Link','Device'+role);link.setLink(source);device.addObject(link)
    link.LinkPlacement=App.Placement(App.Vector(0,50,32),App.Rotation())
    source.ViewObject.ShapeColor=(.08,.69,.68) if role=='ContinuousSkin' else (.78,.79,.79)
for obj in product_doc.Objects:
    if hasattr(obj,'Visibility'):obj.Visibility=False
for obj in pcb_doc.Objects:
    if not obj.InList and hasattr(obj,'Visibility'):obj.Visibility=False
base_instance=D.addObject('App::Link','BaseAssembly');base_instance.setLink(base_module);assembly.addObject(base_instance)
lid_instance=D.addObject('App::Link','LidAssembly');lid_instance.setLink(lid_module);assembly.addObject(lid_instance)
base_module.Visibility=False;lid_module.Visibility=False
note(assembly,'OpeningInstructions','Motion.OpeningAngle drives the lid about the modeled hinge. 0=closed,110=open. Joint is a free revolute, not a prescribed solver angle.')
# Native revolute joint between linked subassemblies; connector frames share
# the actual pin axis. The review angle also permits inspecting an open state.
import JointObject
ground=joints.newObject('App::FeaturePython','GroundedBase');JointObject.GroundedJoint(ground,base_instance);JointObject.ViewProviderGroundedJoint(ground.ViewObject)
joint=joints.newObject('App::FeaturePython','RearHinge');JointObject.Joint(joint,1);JointObject.ViewProviderJoint(joint.ViewObject)
joint.Detach1=True;joint.Detach2=True
joint.Reference1=(base_instance,['LowerShellInstance.','LowerShellInstance.']);joint.Reference2=(lid_instance,['UpperShellInstance.','UpperShellInstance.'])
joint.Placement1=App.Placement(App.Vector(0,164.4,40.15),axis_rotation);joint.Placement2=joint.Placement1
joint.AngleMin=0;joint.AngleMax=110;joint.Visibility=False;ground.Visibility=False
# Construct a fresh whole placement. Updating a negative Angle sub-property
# alone flips the canonical quaternion axis on repeated edits through zero.
lid_instance.setExpression('Placement','create(<<placement>>;create(<<vector>>;0;0;0);create(<<rotation>>;create(<<vector>>;1;0;0);-Motion.OpeningAngle);create(<<vector>>;0;Parameters.HingeY;Parameters.HingeZ))')
progress('native assembly and external StepUp links constructed')
D.recompute();App.setActiveDocument(D.Name);native=OUT/'DockAssembly.FCStd';D.saveAs(str(native))
Gui.activeDocument().activeView().viewAxonometric();Gui.activeDocument().activeView().fitAll();Gui.activeDocument().activeView().saveImage(str(OUT/'DockAssembly-native.png'),1600,1200,'White')
motion.OpeningAngle=110;D.recompute();Gui.activeDocument().activeView().fitAll();Gui.activeDocument().activeView().saveImage(str(OUT/'DockAssembly-open-native.png'),1600,1200,'White')
motion.OpeningAngle=0;D.recompute();D.save()
progress('native and review images saved')
result={'scope':'Editable EVT dock assembly with native shell/liner features, retained controls/display, source-linked StepUp PCBs, UV thermal modules, lid cutoffs, seam baffles, captured magnets and device seats. Nominal geometry review; received, powered and optical qualification remain open.','FreeCAD_version':App.Version(),'native_sha256':hashlib.sha256(native.read_bytes()).hexdigest(),'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'external_sources':external_sources,'assembly_type':assembly.TypeId,'joint_type':joint.JointType,'pogo_native_checks':pogo_checks,'lcd_installed_checks':lcd_checks,'bodies':[{'name':b.Name,'tip':b.Tip.TypeId,'valid':b.Shape.isValid(),'solids':len(b.Shape.Solids)} for b in parts],'fully_constrained_profiles':profile_checks,'remaining':['received hinge/catch/button/fastener fit, loads and retention','received LCD/FFC/socket stack and glass-load qualification','installed mated connectors, flexible looms and restraint','MJF/SLA tolerances, material properties and finished-part qualification','powered display/controller/USB and fault-injection validation','UV source-power, interlock, thermal, optical/leakage and cleaning validation'],'physical_validation':False,'full_product_order_ready':False}
result['board_mount_features']=board_mount_checks
result['lid_cutoff_mount_features']=cutoff_mount_checks
result['lcd_retention_received_stack']=lcd_retention['received_stack']
result['device_seat_received_stack']=device_seats['received_stack']
result['device_seat_shadow_limits']=device_seats['shadow_limits']
result['seam_feature_names']={key:feature.Name for key,feature in seam_features.items()}
result['authoring_helpers_sha256']={name:hashlib.sha256((ROOT/'tools'/name).read_bytes()).hexdigest()
    for name in ('build_evt1_dock_display.py','build_evt1_dock_pogo.py','build_evt1_dock_fasteners.py','build_evt1_dock_board_mounts.py','build_evt1_dock_lcd_socket.py','build_evt1_dock_lcd_retention.py','build_evt1_dock_button_mechanics.py','build_evt1_dock_cutoff_mounts.py','build_evt1_dock_lid_cutoff.py','build_evt1_dock_uv_modules.py','build_evt1_dock_front_closure.py','build_evt1_dock_uv_labyrinth.py','build_evt1_dock_device_seats.py')}
(OUT/'review.json').write_text(json.dumps(result,indent=2)+'\n')
print('Saved native dock bodies',native)
