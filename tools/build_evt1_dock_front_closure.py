"""Captured D31 magnetic front catch: native coupon and shell integration API.

All dimensions use the dock's closed global frame. The visible cream grip
keeps17x9mm atY-7.8/Z35.5..44.5. Two axial magnet pairs close across the seam;
side-loading channels and screwed rear plugs mechanically retain every magnet.
No adhesive, snap flexure, catalog pull force or qualified UV closure is credited.
"""
from pathlib import Path
import hashlib,json,math,zipfile,xml.etree.ElementTree as ET
import FreeCAD as App
import Part,Sketcher

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/cad/evt1-assembly/front-closure-trial'
MASTER=ROOT/'hardware/cad/evt1-assembly/DockAssembly.FCStd'
MAGNET_URL='https://www.kjmagnetics.com/d31-neodymium-disc-magnet'
SCREW_URL='https://www.nbk1560.com/en/products/specialscrew/nedzicom/miniaturescrew/SNSS/SNSS-M2/SNSS-M2-8/'
MAG_D=25.4*3/16;MAG_T=25.4/16;MAG_TOL=.004*25.4
MAG_X=(-4.8,4.8);MAG_Y=-3
SIDES={'upper':dict(z0=40.3,z1=44.5,slot0=41.1,slot1=42.9,screw_z=42.0,bearing_y=6.,pilot=3.6,length=8),
       'lower':dict(z0=35.5,z1=40,slot0=37.4,slot1=39.2,screw_z=34.8,bearing_y=4.3,pilot=3.3,length=6)}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def bounds(shape):
    b=shape.optimalBoundingBox(False,False)
    return [getattr(b,k)for k in('XMin','YMin','ZMin','XMax','YMax','ZMax')]

def prop(obj,kind,name,value,group='Engineering'):
    obj.addProperty(kind,name,group);setattr(obj,name,value)

def profile(body,name,points,position=(0,0,0),rotation=None):
    sketch=body.newObject('Sketcher::SketchObject',name)
    sketch.Placement=App.Placement(App.Vector(*position),rotation or App.Rotation())
    for a,b in zip(points,points[1:]+points[:1]):
        i=sketch.addGeometry(Part.LineSegment(App.Vector(*a,0),App.Vector(*b,0)),False)
        sketch.addConstraint(Sketcher.Constraint('Block',i))
    return sketch

def rect(body,name,x0,y0,x1,y1,z):
    return profile(body,name,[(x0,y0),(x1,y0),(x1,y1),(x0,y1)],(0,0,z))

def rr(body,name,w,h,r,position,rotation=None):
    sketch=body.newObject('Sketcher::SketchObject',name)
    sketch.Placement=App.Placement(App.Vector(*position),rotation or App.Rotation())
    x,y=w/2,h/2;q=math.sqrt(.5);v=lambda a:App.Vector(*a,0)
    segments=[((-x+r,-y),(x-r,-y),None),((x-r,-y),(x,-y+r),(x-r+r*q,-y+r-r*q)),
              ((x,-y+r),(x,y-r),None),((x,y-r),(x-r,y),(x-r+r*q,y-r+r*q)),
              ((x-r,y),(-x+r,y),None),((-x+r,y),(-x,y-r),(-x+r-r*q,y-r+r*q)),
              ((-x,y-r),(-x,-y+r),None),((-x,-y+r),(-x+r,-y),(-x+r-r*q,-y+r-r*q))]
    for a,b,c in segments:
        i=sketch.addGeometry(Part.LineSegment(v(a),v(b))if c is None else Part.Arc(v(a),v(c),v(b)),False)
        sketch.addConstraint(Sketcher.Constraint('Block',i))
    return sketch

def circles(body,name,centres,r,z):
    sketch=body.newObject('Sketcher::SketchObject',name);sketch.Placement.Base.z=z
    for x,y in centres:
        i=sketch.addGeometry(Part.Circle(App.Vector(x,y,0),App.Vector(0,0,1),r),False)
        sketch.addConstraint(Sketcher.Constraint('Block',i))
    return sketch

def feature(body,name,kind,sketch,length,reversed=False):
    body.Document.recompute();assert sketch.FullyConstrained,name
    obj=body.newObject('PartDesign::'+kind,name);obj.Profile=sketch;obj.Length=length
    if kind=='Pocket':obj.Reversed=reversed
    body.Tip=obj;body.Document.recompute()
    assert obj.Shape.isValid()and len(obj.Shape.Solids)==1,(name,len(obj.Shape.Solids))
    if App.GuiUp:
        sketch.Visibility=False
        for previous in body.Group:
            if previous!=obj and hasattr(previous,'Shape'):previous.Visibility=False
    return obj

def add_catch(body,side,prefix=None):
    """Append actual native pads/pockets to an existing identity-placed shell Body.

    Caller owns removal of decorative LatchCover and its obsolete seat.
    Returns a named feature dictionary. No master file is opened or modified.
    """
    assert side in SIDES
    prefix=prefix or ('FrontClosure'+side.title());s=SIDES[side];made={}
    made['cup']=feature(body,prefix+'Cup','Pad',rr(body,prefix+'CupProfile',17,6.8,.7,(0,-3,s['z0'])),s['z1']-s['z0'])
    if side=='lower':
        made['blind_thread_boss']=feature(body,prefix+'BlindThreadBoss','Pad',rect(body,prefix+'BlindThreadBossProfile',-3,-4,3,.4,33.2),2.3)
    if side=='upper':
        made['grip']=feature(body,prefix+'CreamGrip','Pad',rr(body,prefix+'GripProfile',17,9,3,(0,-5.2,40),App.Rotation(App.Vector(1,0,0),90)),2.6)
        relief=profile(body,prefix+'LowerGripReliefProfile',[(-10,30),(10,30),(10,40.3),(-10,40.3)],(0,-6.6,0),App.Rotation(App.Vector(1,0,0),90))
        made['grip_back_relief']=feature(body,prefix+'LowerGripBackRelief','Pocket',relief,1.5)
    made['magnet_pockets']=feature(body,prefix+'MagnetPockets','Pocket',circles(body,prefix+'MagnetPocketProfiles',[(x,MAG_Y)for x in MAG_X],2.525,s['slot1']),1.8)
    tunnel=body.newObject('Sketcher::SketchObject',prefix+'SideLoadingProfiles');tunnel.Placement.Base.z=s['slot1']
    for x in MAG_X:
        pts=[(x-2.525,-3),(x+2.525,-3),(x+2.525,1),(x-2.525,1)]
        for a,b in zip(pts,pts[1:]+pts[:1]):
            i=tunnel.addGeometry(Part.LineSegment(App.Vector(*a,0),App.Vector(*b,0)),False);tunnel.addConstraint(Sketcher.Constraint('Block',i))
    made['loading_channels']=feature(body,prefix+'SideLoadingChannels','Pocket',tunnel,1.8)
    hole=circles(body,prefix+'RearTapPilotProfile',[(0,s['screw_z'])],.8,0)
    hole.Placement=App.Placement(App.Vector(0,.4,0),App.Rotation(App.Vector(1,0,0),90))
    made['tap_pilot']=feature(body,prefix+'RearM2TapPilot','Pocket',hole,s['pilot'],True)
    return made

def add_liner_clearance(body,side,prefix='FrontClosureLiner'):
    """Full-depth loading slot before installing rear plugs; upper final-seat bay."""
    feature(body,prefix+side.title()+'ThroughSlot','Pocket',rect(body,prefix+side.title()+'ThroughSlotProfile',-8.9,-2.5,8.9,.8,58),48)
    if side=='upper':
        feature(body,prefix+'UpperFinalSeatBay','Pocket',rect(body,prefix+'UpperFinalSeatProfile',-8.9,-2.5,8.9,6.4,44.9),4.6)

def new_body(doc,group,name,label):
    body=doc.addObject('PartDesign::Body',name);group.addObject(body);body.Label=label
    return body

def build_retainer(doc,group,side,name):
    s=SIDES[side];body=new_body(doc,group,name,'Captured magnet rear plug / '+side)
    feature(body,name+'Plate','Pad',rr(body,name+'PlateProfile',17,1,.3,(0,.9,s['z0'])),s['z1']-s['z0'])
    sketch=body.newObject('Sketcher::SketchObject',name+'FingerProfiles');sketch.Placement.Base.z=s['slot0']+.15
    for x in MAG_X:
        pts=[(x-2.425,-3),(x+2.425,-3),(x+2.425,.4),(x-2.425,.4)]
        for a,b in zip(pts,pts[1:]+pts[:1]):
            i=sketch.addGeometry(Part.LineSegment(App.Vector(*a,0),App.Vector(*b,0)),False);sketch.addConstraint(Sketcher.Constraint('Block',i))
    feature(body,name+'LocatorFingers','Pad',sketch,1.5)
    feature(body,name+'ConcaveSeats','Pocket',circles(body,name+'SeatProfiles',[(x,-3)for x in MAG_X],2.6,s['slot1']),1.8)
    feature(body,name+'BaffleBridge','Pad',rect(body,name+'BridgeProfile',-8.5,1.4,8.5,s['bearing_y'],s['z0']),s['z1']-s['z0'])
    if side=='lower':
        feature(body,name+'OffsetBaffleWall','Pad',rect(body,name+'BaffleWallProfile',-12,2.3,12,4.3,13.2),26.8)
        toe=[(-12,.5),(-8.7,.5),(-8.7,-1.7),(8.7,-1.7),(8.7,.5),(12,.5),(12,4.3),(-12,4.3)]
        feature(body,name+'FloorOverlapToe','Pad',profile(body,name+'ToeProfile',toe,(0,0,13.2)),1.2)
    else:
        top_front=2.3+(51.5-40.6)*6.7/16.9
        a=rect(body,name+'BaffleWallBottom',-12,2.3,12,4.3,40.6)
        b=rect(body,name+'BaffleWallTop',-12,top_front,12,top_front+2,51.5)
        doc.recompute();loft=body.newObject('PartDesign::AdditiveLoft',name+'SlopingOffsetBaffle');loft.Profile=a;loft.Sections=[b];loft.Ruled=True;body.Tip=loft;doc.recompute()
        assert loft.Shape.isValid()and len(loft.Shape.Solids)==1
        if App.GuiUp:a.Visibility=False;b.Visibility=False
        feature(body,name+'RearSeamOverlapLip','Pad',rect(body,name+'RearLipProfile',-12,4.5,12,5.7,37),3.6)
    hole=circles(body,name+'ScrewClearanceProfile',[(0,s['screw_z'])],1.1,0)
    hole.Placement=App.Placement(App.Vector(0,s['bearing_y'],0),App.Rotation(App.Vector(1,0,0),90))
    feature(body,name+'ScrewClearance','Pocket',hole,s['bearing_y']-.35,True)
    prop(body,'App::PropertyString','MaterialProcess','Same qualified MJFPA12 or engineeringSLA process as cup; no flexible detent or adhesive.','Source')
    if App.GuiUp:body.ViewObject.ShapeColor=(.9,.86,.76)if side=='upper'else(.19,.20,.22)
    return body

def build_magnet(doc,group,side,index,name):
    s=SIDES[side];z=s['slot0']if side=='upper'else s['slot1']-MAG_T
    body=new_body(doc,group,name,'K&J D31 / '+side+' pair'+str(index+1))
    feature(body,name+'Disc','Pad',circles(body,name+'DiscProfile',[(MAG_X[index],-3)],MAG_D/2,z),MAG_T)
    prop(body,'App::PropertyString','MPN','D31','Source');prop(body,'App::PropertyString','SourceURL',MAGNET_URL,'Source')
    prop(body,'App::PropertyString','SelectedData','Axially magnetized N42 NdFeB; Ni-Cu-Ni;3/16x1/16in;±.004in tolerance. North+Z on allfourdiscs gives attracting pairs.','Source')
    prop(body,'App::PropertyString','ForceLimit','No installedholding force is inferred from the steel-plate catalog pull. Actualplasticgap/lidmoment/cycle trial required.','Qualification')
    if App.GuiUp:body.ViewObject.ShapeColor=(.72,.74,.76)
    return body

def build_screw(doc,group,side,name):
    s=SIDES[side];body=new_body(doc,group,name,'NBK SNSS-M2-'+str(s['length'])+' rear-plug/baffle screw')
    sketch=profile(body,name+'Section',[(0,2),(1.9,2),(1.9,0),(1,0),(1,-s['length']),(0,-s['length'])],rotation=App.Rotation(App.Vector(1,0,0),90))
    doc.recompute();assert sketch.FullyConstrained
    rev=body.newObject('PartDesign::Revolution',name+'Revolution');rev.Profile=sketch;rev.ReferenceAxis=(sketch,['V_Axis']);rev.Angle=360
    body.Tip=rev;body.Placement=App.Placement(App.Vector(0,s['bearing_y'],s['screw_z']),App.Rotation(App.Vector(1,0,0),-90))
    prop(body,'App::PropertyString','MPN','SNSS-M2-'+str(s['length']),'Source');prop(body,'App::PropertyString','SourceURL',SCREW_URL if s['length']==8 else 'https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/miniaturescrew/SNSS/','Source')
    prop(body,'App::PropertyString','ProfileLimit','PublishedheadD3.8/H2 andM2major, selectedunderheadL'+str(s['length'])+'; pitch.4;1.5hexbit. Drive recess/threadhelix omitted. Nominal externalprofile, not OEMCAD.','Source')
    if App.GuiUp:sketch.Visibility=False;body.ViewObject.ShapeColor=(.22,.23,.24)
    return body

def source_wall(master,side):
    object_name='UpperShell'if side=='upper'else'LowerShell'
    with zipfile.ZipFile(master)as archive:
        tree=ET.fromstring(archive.read('Document.xml'))
        obj=next(o for o in tree.findall('.//Object[@name="'+object_name+'"]')if o.find('./Properties/Property[@name="Shape"]')is not None)
        member=obj.find('./Properties/Property[@name="Shape"]/Part').get('file');data=archive.read(member)
    shape=Part.Shape();shape.importBrepFromString(data.decode('ascii'))
    low=40.3 if side=='upper'else 31;high=47 if side=='upper'else 40
    crop=shape.common(Part.makeBox(28,15,high-low,App.Vector(-14,-12,low)))
    assert crop.isValid()and len(crop.Solids)==1
    return crop,{'master_native':str(master.relative_to(ROOT)),'master_SHA256':sha(master),'source_body':object_name,
                 'source_BRep_member':member,'source_BRep_SHA256':hashlib.sha256(data).hexdigest(),
                 'crop_box_bounds_mm':[-14,-12,low,14,3,high],'geometry_kind':'Exact source shell cut to a printable testcoupon; clippingbox is not a fit model.'}

def source_liner(master,side):
    name='UpperChamber'if side=='upper'else'LowerChamber'
    with zipfile.ZipFile(master)as archive:
        tree=ET.fromstring(archive.read('Document.xml'))
        obj=next(o for o in tree.findall('.//Object[@name="'+name+'"]')if o.find('./Properties/Property[@name="Shape"]')is not None)
        member=obj.find('./Properties/Property[@name="Shape"]/Part').get('file');data=archive.read(member)
    shape=Part.Shape();shape.importBrepFromString(data.decode('ascii'))
    low,high=(40.6,54)if side=='upper'else(10,37)
    crop=shape.common(Part.makeBox(28,17,high-low,App.Vector(-14,-5,low)))
    assert crop.isValid()and len(crop.Solids)==1
    return crop

def build(doc,name='FrontClosure',master_path=MASTER):
    """Return coupon root with Upper/Lower groups; all localgeometry usesdockXYZ.

    For productintegration call add_catch(existingShellBody,side) and build the
    selected cap/magnets/screw into its correct moving module. Do not import
    the cropped shell coupon into the complete product.
    """
    root=doc.addObject('App::Part',name);root.Label='Functional captured-magnet front closure / unqualified trial'
    params=doc.addObject('App::FeaturePython',name+'Parameters');prop(params,'App::PropertyAngle','OpeningAngle',0,'Pose')
    prop(root,'App::PropertyLinkGlobal','Parameters',params,'Pose');prop(root,'App::PropertyBool','HoldingAndUVClosureQualified',False,'Qualification')
    source=[]
    for side in('lower','upper'):
        group=doc.addObject('App::Part',name+side.title());root.addObject(group)
        prop(root,'App::PropertyLink','Upper'if side=='upper'else'Lower',group,'Modules')
        body=new_body(doc,group,name+side.title()+'Housing','Exact source wall coupon + integral '+side+' catch')
        shape,info=source_wall(Path(master_path),side);source.append(info)
        seed=body.newObject('PartDesign::Feature',name+side.title()+'MasterWallCrop');seed.Shape=shape;body.Tip=seed
        prop(seed,'App::PropertyString','SourceSHA256',info['master_SHA256'],'Source')
        add_catch(body,side,prefix=name+side.title())
        if App.GuiUp:body.ViewObject.ShapeColor=(.9,.86,.76)if side=='upper'else(.19,.20,.22)
        build_retainer(doc,group,side,name+side.title()+'Retainer')
        for i in range(2):build_magnet(doc,group,side,i,name+side.title()+'Magnet'+str(i+1))
        build_screw(doc,group,side,name+side.title()+'RetainerScrew')
        liner=new_body(doc,group,name+side.title()+'Liner','Exact cream liner front coupon / full-depth loading relief')
        seed=liner.newObject('PartDesign::Feature',name+side.title()+'MasterLinerCrop');seed.Shape=source_liner(Path(master_path),side);liner.Tip=seed
        add_liner_clearance(liner,side,name+'Liner')
    root.Upper.setExpression('Placement','create(<<placement>>;create(<<vector>>;0;0;0);create(<<rotation>>;create(<<vector>>;1;0;0);-'+params.Name+'.OpeningAngle);create(<<vector>>;0;164.4;40.15))')
    prop(root,'App::PropertyString','MasterReadOnlySources',json.dumps(source),'Source')
    doc.recompute();return root

def placed(group,body):
    shape=body.Tip.Shape.copy();shape.transformShape(group.Placement.multiply(body.Placement).toMatrix());return shape

def validate(root):
    root.Document.recompute();rows=[]
    for group in(root.Lower,root.Upper):
        for b in group.Group:
            if b.TypeId!='PartDesign::Body':continue
            shape=placed(group,b);assert shape.isValid()and len(shape.Solids)==1,b.Name
            for obj in b.Group:
                if obj.TypeId=='Sketcher::SketchObject':assert obj.FullyConstrained,obj.Name
            bb=bounds(shape);shape.tessellate(.5);assert all(abs(a-c)<1e-7 for a,c in zip(bounds(shape),bb))
            rows.append({'body':b.Name,'valid':True,'native_features':[o.TypeId for o in b.Group],'exact_bounds_mm':bb,'volume_mm3':shape.Volume})
    assert len(rows)==12
    lower=[(b.Name,placed(root.Lower,b))for b in root.Lower.Group if b.TypeId=='PartDesign::Body']
    upper=[(b.Name,placed(root.Upper,b))for b in root.Upper.Group if b.TypeId=='PartDesign::Body']
    collisions=[]
    for an,a in lower:
        for bn,b in upper:
            if a.optimalBoundingBox(False,False).intersect(b.optimalBoundingBox(False,False)):
                v=a.common(b).Volume
                if v>1e-7:collisions.append([an,bn,v])
    assert not collisions,collisions
    return {'native_bodies':rows,'cross_module_pairs':len(lower)*len(upper),'cross_module_overlap_findings':collisions,
            'opening_angle_degrees':float(root.Parameters.OpeningAngle),'loaded_holding_force_qualified':False}

def validate_loading(root):
    """Nominal process-independent geometry checks using the actual OEM maxsize."""
    assert abs(float(root.Parameters.OpeningAngle))<1e-8
    report=[];internal=[]
    for side,group in(('lower',root.Lower),('upper',root.Upper)):
        spec=SIDES[side];bodies={b.Name:b for b in group.Group if b.TypeId=='PartDesign::Body'}
        housing=next(b for n,b in bodies.items()if n.endswith('Housing'))
        retainer=next(b for n,b in bodies.items()if n.endswith('Retainer'))
        screw=next(b for n,b in bodies.items()if n.endswith('RetainerScrew'))
        liner=next(b for n,b in bodies.items()if n.endswith('Liner'));lshape=placed(group,liner)
        hshape=placed(group,housing);rshape=placed(group,retainer)
        items=[(n,placed(group,b))for n,b in bodies.items()]
        for i,(an,a)in enumerate(items):
            for bn,b in items[i+1:]:
                common=a.common(b);volume=common.Volume
                allowed=an in(housing.Name,screw.Name)and bn in(housing.Name,screw.Name)
                if allowed:
                    engagement=spec['length']-(spec['bearing_y']-.4)
                    major=Part.makeCylinder(1,engagement,App.Vector(0,.4,spec['screw_z']),App.Vector(0,-1,0))
                    assert common.cut(major).Volume<1e-7
                    assert abs(volume-math.pi*(1-.8**2)*engagement)<1e-7,(side,volume)
                else:assert volume<1e-7,(side,an,bn,volume)
                internal.append({'a':an,'b':bn,'common_mm3':volume,'allowed_nominal_tapped_thread_major_only':allowed})
        maximum=[]
        for x in MAG_X:
            z=spec['slot0']if side=='upper'else spec['slot1']-MAG_T-MAG_TOL
            gauge=Part.makeCylinder((MAG_D+MAG_TOL)/2,MAG_T+MAG_TOL,App.Vector(x,-3,z))
            assert gauge.common(rshape).Volume<1e-7
            for i in range(19):
                # Assemblycaps are absent; moveeachmaximummagnet from+Y6 to-3.
                trial=gauge.copy();trial.translate(App.Vector(0,9-.5*i,0))
                assert trial.common(hshape).Volume<1e-7,(side,x,i)
                assert trial.common(lshape).Volume<1e-7,(side,'magnet/liner',x,i)
            maximum.append(gauge)
        for i in range(17):
            trial=rshape.copy();trial.translate(App.Vector(0,8-.5*i,0))
            assert trial.common(hshape).Volume<1e-7,(side,'rearplug',i)
            assert trial.common(lshape).Volume<1e-7,(side,'rearplug/liner',i)
            for gauge in maximum:assert trial.common(gauge).Volume<1e-7,(side,'rearplug/maxmagnet',i)
        head_rear=spec['bearing_y']+2
        driver=Part.makeCylinder(2.3,18,App.Vector(0,head_rear,spec['screw_z']),App.Vector(0,1,0))
        for n,b in items:
            if n!=screw.Name:assert driver.common(b).Volume<1e-7,(side,'driver',n)
        report.append({'side':side,'OEM_max_D_mm':MAG_D+MAG_TOL,'OEM_max_T_mm':MAG_T+MAG_TOL,
                       'magnet_loading_poses':38,'rear_plug_loading_poses':17,'rear_driver_corridor_diameter_mm':4.6,
                       'driver_corridor_Y_mm':[head_rear,head_rear+18],'driver_Z_mm':spec['screw_z'],
                       'selected_driver_tip':'1.5mm hex; actual complete tool-shank/handle fit unqualified',
                       'nominal_M2_thread_engagement_mm':spec['length']-(spec['bearing_y']-.4),
                       'holding_force_or_print_process_qualified':False})
    return {'intra_module_pairs':internal,'loading_and_driver':report,
            'closed_floor_seated_magnet_face_gap_mm':41.1-39.2,'minimum_nominal_plastic_face_wall_mm':.8,
            'OEM_max_mag_vs_nominal_pocket_radial_clearance_mm':(5.05-MAG_D-MAG_TOL)/2,
            'OEM_max_mag_vs_nominal_channel_height_clearance_mm':1.8-MAG_T-MAG_TOL,
            'print_or_received_fit_qualified':False}

def validate_liner_loading(root):
    result=[]
    for side,group in(('lower',root.Lower),('upper',root.Upper)):
        housing=next(b for b in group.Group if b.Name.endswith('Housing'))
        liner=next(b for b in group.Group if b.Name.endswith('Liner'))
        a=placed(group,housing);b=placed(group,liner)
        for i in range(31):
            trial=b.copy();trial.translate(App.Vector(0,0,(1 if side=='lower'else -1)*(30-i)))
            assert trial.common(a).Volume<1e-7,(side,'vertical_liner_loading',i)
        result.append({'side':side,'nominal_vertical_loading_poses':31,'plugs_installed_after_liner':True,'slot_X_mm':[-8.9,8.9],'full_depth_slot_Y_mm':[-2.5,.8],
                       'upper_additional_final_seat_clearance_Y_mm':[-2.5,6.4]if side=='upper'else None})
    return result

def main():
    OUT.mkdir(parents=True,exist_ok=True);before=sha(MASTER)
    doc=App.newDocument('FrontClosureTrial');root=build(doc);report={'closed':validate(root),'loading':validate_loading(root),'liner_loading':validate_liner_loading(root),
                                                                'master_front_context':json.loads(root.MasterReadOnlySources)}
    poses=[]
    for a in(.1,.5,1,1.5,2,3,5,10,30,60,110):
        root.Parameters.OpeningAngle=a;doc.recompute();poses.append(validate(root))
    root.Parameters.OpeningAngle=0;doc.recompute();path=OUT/'FrontClosureTrial.FCStd';doc.saveAs(str(path))
    exports={}
    for side,group in(('lower',root.Lower),('upper',root.Upper)):
        for suffix in('Housing','Retainer','Liner'):
            body=next(b for b in group.Group if b.Name.endswith(suffix));shape=placed(group,body)
            export=OUT/(side+'-'+suffix.lower()+'.step');shape.exportStep(str(export));readback=Part.read(str(export))
            delta=readback.Volume-shape.Volume
            assert readback.isValid()and len(readback.Solids)==1 and abs(delta)<1e-6*max(1,shape.Volume)
            assert all(abs(a-b)<1e-5 for a,b in zip(bounds(shape),bounds(readback)))
            errors=[]
            for a,b in((shape,readback),(readback,shape)):
                for edge in a.Edges:
                    for i in range(5):errors.append(Part.Vertex(edge.valueAt(edge.FirstParameter+(edge.LastParameter-edge.FirstParameter)*i/4)).distToShape(b)[0])
            assert max(errors)<1e-5
            exports[export.name]={'SHA256':sha(export),'exact_bounds_mm':bounds(readback),'solid_volume_mm3':readback.Volume,
                                  'volume_delta_mm3':delta,'bidirectional_edge_samples':len(errors),'max_edge_sample_distance_mm':max(errors),
                                  'relative_volume_tolerance':1e-6,'linear_exchange_tolerance_mm':1e-5}
    root.Parameters.OpeningAngle=2;doc.recompute();released=OUT/'FrontClosureReleased.FCStd';doc.saveAs(str(released));App.closeDocument(doc.Name)
    doc=App.openDocument(str(path));report['saved_readback']=validate(doc.FrontClosure);App.closeDocument(doc.Name)
    doc=App.openDocument(str(released));report['released_saved_readback']=validate(doc.FrontClosure);App.closeDocument(doc.Name)
    report['opening_pose_checks']=poses;report['native_SHA256']=sha(path);report['released_native_SHA256']=sha(released)
    report['single_part_STEP_exports']=exports;report['builder_SHA256']=sha(Path(__file__))
    report['master_SHA256_before']=before;report['master_SHA256_after']=sha(MASTER);assert report['master_SHA256_after']==before
    report['FreeCAD_version']=App.Version();report['full_product_order_ready']=False
    report['source_manifest_SHA256']=sha(OUT/'source-manifest.json')
    (OUT/'native-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'native_bodies':12,'saved_readback':'pass','closed_and_opening_pairs':36*(len(poses)+3),'master_unchanged':True,'holding_and_UV_qualified':False}))

if __name__=='__main__':main()
