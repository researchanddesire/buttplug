"""Removable cable guide for InternalCradle. mm, Z up, front -Y.
Install after loading the pack; four provisional M1.4 x 5 screws.
The guide is a separate editable PartDesign body, with an open four-wire
trough. Pack's three wires occupy the lower neck bore.
"""
import os,sys,json,hashlib
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import FreeCAD as App,Part
from compass_datums import MECH,BUILD,log
NAME='CradleWireGuide'
STATIONS=[(-13.0,1.8),(18.0,1.8),(30.4,3.5),(65.55,3.5)]
HALF_WIDTH,WALL,BASE_T,WALL_H=3.4,1.0,1.2,1.6
MOUNTS=[(-5.0,29.8),(5.0,29.8),(-8.0,66.7),(8.0,66.7)]
MOUNT_BASE_Z,MOUNT_T,EAR_R,CLEAR_D=3.5,1.2,1.8,1.6
COLOR=(0.95,0.69,0.22)
exit_code=1
try:
    doc=App.newDocument(NAME);body=doc.addObject('PartDesign::Body',NAME)
    body.Label='Removable four-wire guide'
    for n,v in [('ClearWidth',4.8),('FloorThickness',BASE_T),('ScrewClearance',CLEAR_D)]:
        body.addProperty('App::PropertyLength',n,'Dimensions');setattr(body,n,v)
    tip=None
    def sketch(n,origin,rot=None):
        s=doc.addObject('Sketcher::SketchObject',n);body.addObject(s)
        s.Placement=App.Placement(App.Vector(*origin),rot or App.Rotation());return s
    def poly(s,pts):
        for a,b in zip(pts,pts[1:]+pts[:1]):
            s.addGeometry(Part.LineSegment(App.Vector(a[0],a[1],0),App.Vector(b[0],b[1],0)),False)
    def rect(s,a,b,c,d):poly(s,[(a,b),(c,b),(c,d),(a,d)])
    def pad(s,n,length):
        global tip
        doc.recompute();f=body.newObject('PartDesign::Pad',n);f.Profile=s;f.Length=length;doc.recompute()
        assert f.Shape.isValid() and len(f.Shape.Solids)==1,n
        s.Visibility=False
        if tip:tip.Visibility=False
        tip=f
    yz=App.Rotation(App.Vector(1,1,1),120)
    for n,x,w,lo,hi in [('TroughFloor',-HALF_WIDTH,2*HALF_WIDTH,0,BASE_T),('LeftLip',-HALF_WIDTH,WALL,BASE_T,BASE_T+WALL_H),('RightLip',HALF_WIDTH-WALL,WALL,BASE_T,BASE_T+WALL_H)]:
        s=sketch(n+'Profile',(x,0,0),yz)
        poly(s,[(y,z+lo) for y,z in STATIONS]+[(y,z+hi) for y,z in reversed(STATIONS)])
        pad(s,n,w)
    for label,hx,y0,y1 in [('Rear',5.0,29.25,31.25),('Nose',8.0,65.05,66.0)]:
        s=sketch(label+'BridgeProfile',(0,0,MOUNT_BASE_Z));rect(s,-hx,y0,hx,y1);pad(s,label+'Bridge',MOUNT_T)
    for i,(x,y) in enumerate(MOUNTS):
        s=sketch('EarProfile'+str(i),(0,0,MOUNT_BASE_Z))
        s.addGeometry(Part.Circle(App.Vector(x,y,0),App.Vector(0,0,1),EAR_R),False);pad(s,'ScrewEar'+str(i),MOUNT_T)
    s=sketch('ScrewClearanceProfile',(0,0,MOUNT_BASE_Z+MOUNT_T))
    for x,y in MOUNTS:s.addGeometry(Part.Circle(App.Vector(x,y,0),App.Vector(0,0,1),CLEAR_D/2),False)
    f=body.newObject('PartDesign::Pocket','ScrewClearances');f.Profile=s;f.Length=MOUNT_T+0.1;doc.recompute()
    s.Visibility=False;tip.Visibility=False;tip=f;body.Tip=f
    assert body.Shape.isValid() and len(body.Shape.Solids)==1
    doc.recompute();body.ViewObject.ShapeColor=COLOR;tip.ViewObject.ShapeColor=COLOR
    doc.saveAs(MECH+'/'+NAME+'.FCStd')
    import ImportGui;ImportGui.export([body],MECH+'/'+NAME+'.step')
    # Derived print mesh in build/: native and STEP remain the source.
    import MeshPart
    print_dir=BUILD+'/cradle-print';os.makedirs(print_dir,exist_ok=True)
    msh=MeshPart.meshFromShape(Shape=body.Shape,LinearDeflection=0.025,AngularDeflection=0.2,Relative=False)
    assert msh.isSolid() and not msh.hasNonManifolds() and msh.countComponents()==1
    msh.write(print_dir+'/'+NAME+'.stl')
    open(print_dir+'/'+NAME+'-mesh.json','w').write(json.dumps({'source':MECH+'/'+NAME+'.FCStd','watertight':True,'components':1,'triangles':msh.CountFacets,'linear_deflection_mm':0.025,'physical_print_verified':False},indent=2)+'\n')
    sh=body.Shape;b=sh.BoundBox;size=sorted([b.XLength,b.YLength,b.ZLength],reverse=True)
    fab={'kind':'3dp','name':'Removable internal wire guide','source':NAME+'.step','qty':3,'order':False,
         'options':{'process':'mjf','material':'pa12','color':'black'},
         'features':dict(volume_cm3=round(sh.Volume/1000,4),area_cm2=round(sh.Area/100,3),size_x_mm=round(size[0],3),size_y_mm=round(size[1],3),size_z_mm=round(size[2],3))}
    open(MECH+'/'+NAME+'.fab.json','w').write(json.dumps(fab,indent=2)+'\n')
    out=Part.Shape();out.read(MECH+'/'+NAME+'.step');assert out.isValid() and len(out.Solids)==1 and abs(sh.Volume-out.Volume)<0.01
    for n in ['InternalCradle','MetalBody','MotorThermistorCap']:
        h=Part.Shape();h.read(MECH+'/'+n+'.step');v=sh.common(h).Volume
        log(NAME,n,'overlap_mm3',v,'gap_mm',sh.distToShape(h)[0]);assert v<0.001,n
    log(NAME,'OK',fab['features'])
    for f in os.listdir(MECH):
        if f.endswith('.FCBak'):os.replace(MECH+'/'+f,BUILD+'/'+f)
    exit_code=0
except Exception:
    import traceback;log(NAME,'ERROR',traceback.format_exc())
finally:os._exit(exit_code)
