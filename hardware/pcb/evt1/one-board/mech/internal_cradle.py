"""Printed internal cradle for the current compact Compass device.

mm, Z up, dock/front faces -Y. Rebuild in FreeCAD's offscreen GUI.
The existing metal, pack and motor datums are preserved. A horseshoe seats
against the narrowing body bore; the nose web limits motor rearward motion.
Soft bands and cushioning remain build items, with no pouch preload credited.
"""
import os, sys, json, math, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import FreeCAD as App, Part, Sketcher
from compass_datums import MECH, BUILD, log, box_xyz

# All dimensions in mm. Pouch and motor coordinates come from pack-spec.json
# and internals.py; the cap counterbore is measured from its saved STEP.
NAME = 'InternalCradle'
PACK_MIN = (-10.5, 31.75, -4.15)
PACK_SIZE = (21.0, 33.0, 6.3)
REAR_Y, REAR_T = 30.4, 1.1
SEAT_R, SEAT_INNER_R, SEAT_TOP_Z = 11.9, 8.0, 2.8
FLOOR_HALF_X, FLOOR_Y0, FLOOR_Y1 = 8.0, 31.0, 65.6
FLOOR_Z, FLOOR_T = -6.55, 1.2
SIDE_INNER_X, SIDE_T = 10.8, 1.0
SIDE_Z0, SIDE_Z1 = -2.0, 0.5
NOSE_Y, NOSE_T, NOSE_R, NOSE_TOP_Z = 65.05, 1.70, 11.9, 2.8
MOTOR_REAR_Y, MOTOR_STOP_Y, MOTOR_R = 67.0, 93.3, 5.55
BAR_HALF_X = 10.8
REAR_BAR_Z, REAR_BAR_H = 2.3, 1.2
NOSE_BAR_Y1, NOSE_BAR_Z, NOSE_BAR_H = 66.0, 2.3, 1.2
# Open cable trough: four tip/motor wires above the pack, three pack wires below
# in the neck. Rectangular stations of a constant-width ramp; no closed tunnels.
TRACK_YZ = [(-13.0, 1.8), (18.0, 1.8), (30.4, 3.5), (65.55, 3.5)]
TRACK_HALF_X, TRACK_WALL, TRACK_BASE_T, TRACK_WALL_H = 3.4, 1.0, 1.2, 1.6
BAND_Y, BAND_SLOT_X, BAND_SLOT_W, BAND_WIDTH = [42.0, 57.0], 5.7, 1.2, 3.6
EDGE_R = 0.3
COLOR = (0.90, 0.45, 0.12)

os.makedirs(BUILD, exist_ok=True)
log_path = BUILD + '/' + NAME + '.log'
if os.path.exists(log_path): os.remove(log_path)
exit_code = 1
try:
    doc = App.newDocument(NAME)
    body = doc.addObject('PartDesign::Body', NAME)
    body.Label = 'Internal cradle — battery / wire trough / motor stop'
    for key, val in [('PouchWidth',21.0),('PouchLength',33.0),('PouchThickness',6.3),
                     ('SideClearance',0.3),('LowerAllowance',1.2),('UpperAllowance',1.35),
                     ('MotorAxialGap',0.25),('CapBoreRadius',12.25),('SeatRadius',SEAT_R)]:
        body.addProperty('App::PropertyLength', key, 'Design dimensions'); setattr(body,key,val)
    body.addProperty('App::PropertyString','Status','Design dimensions')
    body.Status = 'EVT fit candidate; soft retention, tolerances and cap wiring require trial'
    tip = None
    def sketch(label, origin, rot=None):
        s = doc.addObject('Sketcher::SketchObject',label)
        body.addObject(s)
        s.Placement = App.Placement(App.Vector(*origin), rot or App.Rotation())
        return s
    def poly(s, pts):
        for a,b in zip(pts, pts[1:]+pts[:1]):
            s.addGeometry(Part.LineSegment(App.Vector(a[0],a[1],0),App.Vector(b[0],b[1],0)),False)
    def rect(s,a,b,c,d): poly(s,[(a,b),(c,b),(c,d),(a,d)])
    def pad(s,label,length,reverse=False):
        global tip
        doc.recompute()
        f=body.newObject('PartDesign::Pad',label); f.Profile=s; f.Length=length; f.Reversed=reverse
        doc.recompute()
        assert not f.Shape.isNull() and f.Shape.isValid() and len(f.Shape.Solids)==1, label+' failed: '+str(f.getStatusString())
        s.Visibility=False
        if tip: tip.Visibility=False
        tip=f
        return f
    xz_rot=App.Rotation(App.Vector(1,0,0),90)  # sketch normal -Y, reverse pad -> +Y
    s=sketch('RearTaperSeatProfile',(0,REAR_Y,0),xz_rot)
    xo=math.sqrt(SEAT_R**2-SEAT_TOP_Z**2); xi=math.sqrt(SEAT_INNER_R**2-SEAT_TOP_Z**2)
    s.addGeometry(Part.Arc(App.Vector(-xo,SEAT_TOP_Z,0),App.Vector(0,-SEAT_R,0),App.Vector(xo,SEAT_TOP_Z,0)),False)
    s.addGeometry(Part.LineSegment(App.Vector(xo,SEAT_TOP_Z,0),App.Vector(xi,SEAT_TOP_Z,0)),False)
    s.addGeometry(Part.Arc(App.Vector(xi,SEAT_TOP_Z,0),App.Vector(0,-SEAT_INNER_R,0),App.Vector(-xi,SEAT_TOP_Z,0)),False)
    s.addGeometry(Part.LineSegment(App.Vector(-xi,SEAT_TOP_Z,0),App.Vector(-xo,SEAT_TOP_Z,0)),False)
    pad(s,'RearTaperSeat',REAR_T,True)
    s=sketch('BatteryShelfProfile',(0,0,FLOOR_Z));rect(s,-FLOOR_HALF_X,FLOOR_Y0,FLOOR_HALF_X,FLOOR_Y1)
    pad(s,'BatteryShelf',FLOOR_T)
    for sign, label in [(-1,'Left'),(1,'Right')]:
        x0,x1=sorted([sign*SIDE_INNER_X,sign*(SIDE_INNER_X+SIDE_T)])
        s=sketch(label+'RailProfile',(0,0,SIDE_Z0));rect(s,x0,FLOOR_Y0,x1,FLOOR_Y1)
        pad(s,label+'BatteryRail',SIDE_Z1-SIDE_Z0)
    s=sketch('MotorStopProfile',(0,NOSE_Y,0),xz_rot)
    x=math.sqrt(NOSE_R**2-NOSE_TOP_Z**2)
    s.addGeometry(Part.Arc(App.Vector(-x,NOSE_TOP_Z,0),App.Vector(0,-NOSE_R,0),App.Vector(x,NOSE_TOP_Z,0)),False)
    s.addGeometry(Part.LineSegment(App.Vector(x,NOSE_TOP_Z,0),App.Vector(-x,NOSE_TOP_Z,0)),False)
    pad(s,'MotorRearStop',NOSE_T,True)
    s=sketch('RearTroughSupportProfile',(0,0,REAR_BAR_Z));rect(s,-BAR_HALF_X,REAR_Y,BAR_HALF_X,REAR_Y+REAR_T)
    pad(s,'RearTroughSupport',REAR_BAR_H)
    s=sketch('NoseTroughSupportProfile',(0,0,NOSE_BAR_Z));rect(s,-BAR_HALF_X,NOSE_Y,BAR_HALF_X,NOSE_BAR_Y1)
    pad(s,'NoseTroughSupport',NOSE_BAR_H)
    # Removable guide fastens after the pouch is loaded from +Z.
    mount_rows=[('Rear',[-5.0,5.0],29.8,FLOOR_Z),('Nose',[-8.0,8.0],66.7,-2.0)]
    for label,xs,y,z0 in mount_rows:
        for i,x in enumerate(xs):
            s=sketch(label+'GuideBossProfile'+str(i),(0,0,z0))
            s.addGeometry(Part.Circle(App.Vector(x,y,0),App.Vector(0,0,1),1.6),False)
            pad(s,label+'GuideBoss'+str(i),3.5-z0)
    s=sketch('GuidePilotProfile',(0,0,3.5))
    for _,xs,y,_ in mount_rows:
        for x in xs:s.addGeometry(Part.Circle(App.Vector(x,y,0),App.Vector(0,0,1),0.525),False)
    p=body.newObject('PartDesign::Pocket','GuideScrewPilots');p.Profile=s;p.Length=4.0
    doc.recompute();assert p.Shape.isValid() and len(p.Shape.Solids)==1
    s.Visibility=False;tip.Visibility=False;tip=p
    s=sketch('SoftBandSlotsProfile',(0,0,FLOOR_Z+FLOOR_T))
    for y in BAND_Y:
        for sign in [-1,1]:
            x=sign*BAND_SLOT_X
            rect(s,x-BAND_SLOT_W/2,y-BAND_WIDTH/2,x+BAND_SLOT_W/2,y+BAND_WIDTH/2)
    pocket=body.newObject('PartDesign::Pocket','SoftBandSlots');pocket.Profile=s;pocket.Length=FLOOR_T+0.1
    doc.recompute();s.Visibility=False;tip.Visibility=False;tip=pocket
    assert tip.Shape.isValid() and len(tip.Shape.Solids)==1
    # Round the long pack-facing rail edges. Each radius is explicit/editable.
    names=[]
    for i,e in enumerate(tip.Shape.Edges,1):
        b=e.BoundBox
        if b.YLength>25 and b.XLength<1e-6 and b.ZLength<1e-6 and abs(abs(b.XMin)-SIDE_INNER_X)<1e-5 and abs(b.ZMin-SIDE_Z1)<1e-5:
            names.append('Edge%d'%i)
    if names:
        f=body.newObject('PartDesign::Fillet','PouchRailEdgeRounds');f.Base=(tip,names);f.Radius=EDGE_R
        doc.recompute();assert f.Shape.isValid() and len(f.Shape.Solids)==1
        tip.Visibility=False;tip=f
    body.Tip=tip
    doc.recompute();body.ViewObject.ShapeColor=COLOR;tip.ViewObject.ShapeColor=COLOR
    path=MECH+'/'+NAME+'.FCStd';doc.saveAs(path)
    import ImportGui
    ImportGui.export([body],MECH+'/'+NAME+'.step')
    # Derived print mesh in build/: native and STEP remain the source.
    import MeshPart
    print_dir=BUILD+'/cradle-print';os.makedirs(print_dir,exist_ok=True)
    msh=MeshPart.meshFromShape(Shape=body.Shape,LinearDeflection=0.025,AngularDeflection=0.2,Relative=False)
    assert msh.isSolid() and not msh.hasNonManifolds() and msh.countComponents()==1
    msh.write(print_dir+'/'+NAME+'.stl')
    open(print_dir+'/'+NAME+'-mesh.json','w').write(json.dumps({'source':MECH+'/'+NAME+'.FCStd','watertight':True,'components':1,'triangles':msh.CountFacets,'linear_deflection_mm':0.025,'physical_print_verified':False},indent=2)+'\n')
    # Derive every manufacturing feature from the finished solid.
    sh=body.Shape;assert sh.isValid() and len(sh.Solids)==1
    b=sh.BoundBox;size=sorted([b.XLength,b.YLength,b.ZLength],reverse=True)
    fab={'kind':'3dp','name':'Internal battery / cable / motor cradle','source':NAME+'.step','qty':3,'order':False,
         'options':{'process':'mjf','material':'pa12','color':'black'},
         'features':dict(volume_cm3=round(sh.Volume/1000,4),area_cm2=round(sh.Area/100,3),size_x_mm=round(size[0],3),size_y_mm=round(size[1],3),size_z_mm=round(size[2],3))}
    open(MECH+'/'+NAME+'.fab.json','w').write(json.dumps(fab,indent=2)+'\n')
    # Saved-native and STEP readback validation and canonical metal interference.
    saved=App.openDocument(path);native=saved.getObject(NAME).Shape
    out=Part.Shape();out.read(MECH+'/'+NAME+'.step')
    assert native.isValid() and out.isValid() and len(out.Solids)==1
    assert abs(out.Volume-native.Volume)<0.01
    checks=[]
    for n in ['MetalBody','MotorThermistorCap']:
        hard=Part.Shape();hard.read(MECH+'/'+n+'.step')
        v=sh.common(hard).Volume;gap=sh.distToShape(hard)[0]
        checks.append({'part':n,'overlap_mm3':round(v,6),'gap_mm':round(gap,6)})
        assert v<0.001,n+' overlap'
    pack=Part.makeBox(*PACK_SIZE,App.Vector(*PACK_MIN))
    motor=Part.makeCylinder(MOTOR_R,MOTOR_STOP_Y-MOTOR_REAR_Y,App.Vector(0,MOTOR_REAR_Y,0),App.Vector(0,1,0))
    for n,p in [('Pack maximum',pack),('Motor',motor)]:
        v=sh.common(p).Volume;gap=sh.distToShape(p)[0]
        checks.append({'part':n,'overlap_mm3':round(v,6),'gap_mm':round(gap,6)})
        assert v<0.001,n+' overlap'
    report={'status':'candidate, nominal CAD checks only','source_native':path,'single_valid_solid':True,
            'saved_step_volume_delta_mm3':round(out.Volume-native.Volume,6),'checks':checks,
            'dimensions':{'pack_mm':PACK_SIZE,'side_gap_mm':0.3,'pack_rear_gap_mm':0.25,'pack_front_gap_mm':0.3,
                          'under_pack_mm':1.2,'above_pack_to_track_mm':1.35,'motor_rear_gap_mm':0.25,
                          'cable_track_clear_width_mm':2*(TRACK_HALF_X-TRACK_WALL),'wall_min_design_mm':1.0},
            'source_sha256':{n:hashlib.sha256(open(MECH+'/'+n,'rb').read()).hexdigest() for n in ['MetalBody.step','MotorThermistorCap.step','internal_cradle.py']},
            'open':['Soft band and cushioning material, tension and swelling response unqualified','Motor terminal envelope and seating tolerances need received parts','Removable guide uses four provisional M1.4 x 5 screws; pilot/engagement require print trial','Guided wire routing and cap installation checks follow in the assembly','No mechanical strength, vibration, creep, heat, sealing or physical assembly result']}
    open(MECH+'/cradle-fit.json','w').write(json.dumps(report,indent=2)+'\n')
    log(NAME,json.dumps(report));log(NAME,'OK')
    for f in os.listdir(MECH):
        if f.endswith('.FCBak'):os.replace(MECH+'/'+f,BUILD+'/'+f)
    exit_code=0
except Exception:
    import traceback
    log(NAME,'ERROR',traceback.format_exc())
finally:
    os._exit(exit_code)
