"""Selected Molex52437-2771 OEM geometry and adjustable PCB trial shims.

Run in FreeCAD GUI/Python. No main assembly or electrical source is modified.
The OEM download contains two exact solids in its OPEN position. An optional
rigid closed-envelope pose moves the latch1.6mm; spring deflection is omitted.
Neither pose establishes a qualified loaded FPC copper-contact plane.
"""
from pathlib import Path
import hashlib,json,math
import FreeCAD as App
import Part,Sketcher

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/cad/evt1-assembly/vendor/lcd-socket'
SOURCE=OUT/'524372771.stp'
SOURCE_SHA256='d5672a336735ddad3354496a4e732e10df378164f574a02ad6431cc5a0de58a4'
MOUNTS=((-30,65),(30,65),(-32,115),(32,105))
LAND_ROW_REAR_HOUSING_OFFSET=.6
LATCH_STROKE=1.6

def _bounds(shape):
    bb=shape.optimalBoundingBox(False,False)
    return [getattr(bb,k)for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax')]

def _source():
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA256
    shape=Part.read(str(SOURCE))
    assert shape.isValid() and len(shape.Solids)==2 and len(shape.Faces)==1001
    return shape

def _board_matrix():
    # OEM+Y is height and+Z is the mouth. Rx90 gives a right-handed board
    # frame with pin1-X and mouth-Y. RevF p2 places housing rear0.6mm ahead
    # of the land-row centre: half0.8mm land +0.2mm reference gap.
    m=App.Matrix()
    m.A11=1;m.A12=0;m.A13=0;m.A14=0
    m.A21=0;m.A22=0;m.A23=-1;m.A24=-LAND_ROW_REAR_HOUSING_OFFSET
    m.A31=0;m.A32=1;m.A33=0;m.A34=0
    return m

def _property(obj,kind,name,value,group='Source'):
    obj.addProperty(kind,name,group);setattr(obj,name,value)

def _body(doc,part,name,label,shape):
    body=doc.addObject('PartDesign::Body',name);part.addObject(body);body.Label=label
    feature=body.newObject('PartDesign::Feature',name+'OEMGeometry')
    feature.Label='Exact OEM STEP BRep / new native features may follow'
    feature.Shape=shape
    _property(feature,'App::PropertyString','OEMSourceSHA256',SOURCE_SHA256)
    _property(feature,'App::PropertyString','GeometryKind','Rigidly transformed OEM BRep; no envelope replacement')
    body.Tip=feature
    return body

def build(doc,name='DockLCDSocket',pose='oem_open'):
    """Return App::Part in the J302 land-row frame: X pin row,+Z height,mouth-Y.

    Source H-plane is localZ0; actual OEM solder tails reachZ-0.04. Parent
    assembly must account for solder/copolanarity and the unqualified FPC mate.
    """
    assert pose in ('oem_open','closed_envelope')
    original=_source();part=doc.addObject('App::Part',name)
    part.Label='Molex52437-2771 / selected OEM geometry'
    params=doc.addObject('App::FeaturePython',name+'Parameters')
    params.Label='Socket latch pose / loaded contact height UNSPECIFIED'
    _property(params,'App::PropertyLength','ActuatorSlide',0 if pose=='oem_open' else LATCH_STROKE,'Pose')
    _property(params,'App::PropertyLength','PublishedSlideStroke',LATCH_STROKE,'Pose')
    _property(params,'App::PropertyString','LoadedCopperContactHeight','UNSPECIFIED: open OEM CAD is not a loaded FPC mating specification','Qualification')
    _property(part,'App::PropertyLinkGlobal','Parameters',params,'Pose')
    _property(part,'App::PropertyString','PartNumber','52437-2771')
    _property(part,'App::PropertyString','SourceFile','524372771.stp')
    _property(part,'App::PropertyString','SourceSHA256',SOURCE_SHA256)
    _property(part,'App::PropertyString','SourceCADDate','2013-08-20')
    _property(part,'App::PropertyString','PoseAtCreation',pose,'Pose')
    _property(part,'App::PropertyString','SourceToBoardFrame','X=sX;Y=-sZ-0.6;Z=sY. Source housing rearZ0 and source H planeY0.')
    _property(part,'App::PropertyString','PinConvention','27 actual terminals on0.5pitch; pin1-X; mouth-Y; LCDpinp→socketpadp')
    _property(part,'App::PropertyBool','LoadedContactPlaneQualified',False,'Qualification')
    _property(part,'App::PropertyBool','ReceivedTailMatingQualified',False,'Qualification')
    _property(part,'App::PropertyString','ClosedPoseLimit','Rigid latch translation only. Contact deflection omitted; small internal common volume is not a hardware-fit result.','Qualification')
    for i,shape in enumerate(original.Solids):
        transformed=shape.copy();transformed.transformShape(_board_matrix())
        body=_body(doc,part,name+('HousingContacts' if i==0 else 'Actuator'),
                   'OEM housing +27 actual contact profiles' if i==0 else 'OEM slider / editable rigid pose',transformed)
        if i==1:body.setExpression('Placement.Base.y',params.Name+'.ActuatorSlide')
        if App.GuiUp:
            body.ViewObject.ShapeColor=(.82,.79,.67) if i==0 else(.37,.23,.13)
    # Construction only: land-row centres, not substitute solder pads or springs.
    sketch=doc.addObject('Sketcher::SketchObject',name+'TerminalCentres');part.addObject(sketch)
    sketch.Label='Construction:27 electrical terminal centres / PCB land-row datum'
    for i in range(27):
        x=-6.5+.5*i;n=sketch.addGeometry(Part.Circle(App.Vector(x,0,0),App.Vector(0,0,1),.1),True)
        sketch.addConstraint(Sketcher.Constraint('Radius',n,.1))
        sketch.addConstraint(Sketcher.Constraint('PointOnObject',n,3,-1))
        if abs(x)<1e-9:sketch.addConstraint(Sketcher.Constraint('PointOnObject',n,3,-2))
        else:sketch.addConstraint(Sketcher.Constraint('DistanceX',n,3,x))
    doc.recompute();assert sketch.FullyConstrained
    if App.GuiUp:sketch.Visibility=False
    validate(part)
    return part

def validate(part):
    doc=part.Document;doc.recompute();original=_source()
    bodies=[o for o in part.Group if o.TypeId=='PartDesign::Body'];assert len(bodies)==2
    slide=float(part.Parameters.ActuatorSlide)
    assert -.000001<=slide<=LATCH_STROKE+.000001
    expected=[[-9.75,-4.85,-.04,9.75,.1,2],[-10.05,-6.7+slide,.05,10.05,-2.55+slide,1.95]]
    rows=[];shapes=[]
    for i,b in enumerate(bodies):
        # Tip.Shape is local to its body; use only the relative body pose here.
        shape=b.Tip.Shape.copy();shape.transformShape(b.Placement.toMatrix())
        assert shape.isValid() and len(shape.Solids)==1
        assert abs(shape.Volume-original.Solids[i].Volume)<1e-8
        bounds=_bounds(shape);assert all(abs(a-c)<1e-7 for a,c in zip(bounds,expected[i])),(b.Name,bounds,expected[i])
        shape.tessellate(.5);assert all(abs(a-c)<1e-7 for a,c in zip(_bounds(shape),bounds))
        rows.append({'body':b.Name,'native_type':b.TypeId,'features':[b.Tip.TypeId],
                     'faces':len(shape.Faces),'valid':True,'volume_mm3':shape.Volume,'exact_bounds_mm':bounds})
        shapes.append(shape)
    contacts=[]
    for f in original.Solids[0].Faces:
        surface=f.Surface;bb=f.optimalBoundingBox(False,False)
        if isinstance(surface,Part.Plane)and abs(surface.Axis.y)>.999 and abs(surface.Position.y-.14)<1e-7:
            if abs((bb.XMax-bb.XMin)-.2)<1e-7 and abs(bb.ZMin+.7)<1e-7 and abs(bb.ZMax+.2)<1e-7:
                contacts.append((bb.XMin+bb.XMax)/2)
    assert len(contacts)==27
    assert all(abs(x-(-6.5+.5*i))<1e-7 for i,x in enumerate(sorted(contacts)))
    common=shapes[0].common(shapes[1]).Volume
    if abs(slide)<1e-7:assert common<1e-9
    if abs(slide-LATCH_STROKE)<1e-7:assert abs(common-.00407)<1e-8
    return {'source_sha256':SOURCE_SHA256,'OEM_source_solids':2,'OEM_source_faces':1001,
            'native_bodies':rows,'actual_terminal_count':27,'terminal_pitch_mm':.5,
            'actuator_rigid_slide_mm':slide,'internal_common_volume_mm3':common,
            'nominal_solder_tail_below_H_datum_mm':.04,'loaded_copper_contact_height_qualified':False,
            'note':'Closed-envelope common volume comes from omitted spring deformation; no loaded-contact or received-fit claim.'}

def build_trial_shims(doc,name='LCDSocketTrialShims',stack_mm=1.0,roof_seat_z_mm=61.5):
    """Four editable equal annular shim stacks at the existing PCB mounting holes.

    The proposed fixed roof seat61.5 and stack0.5..1.5 yield PCBtop61.0..60.0.
    This is an adjustable fixture range, not a claimed contact-height datum.
    """
    assert .5<=stack_mm<=1.5
    params=doc.addObject('App::FeaturePython',name+'Parameters')
    _property(params,'App::PropertyLength','Stack',stack_mm,'Trial')
    _property(params,'App::PropertyLength','RoofSeatZ',roof_seat_z_mm,'Trial')
    _property(params,'App::PropertyLength','PCBTopZ',roof_seat_z_mm-stack_mm,'Trial')
    params.setExpression('PCBTopZ',params.Name+'.RoofSeatZ - '+params.Name+'.Stack')
    _property(params,'App::PropertyString','Qualification','Proposed equal-stack trial fixture; no selected loaded copper plane or final shell release','Trial')
    part=doc.addObject('App::Part',name);part.Label='Four equal PCB trial shim stacks / actual annular geometry'
    _property(part,'App::PropertyLinkGlobal','Parameters',params,'Trial')
    part.setExpression('Placement.Base.z',params.Name+'.PCBTopZ')
    for i,(x,y)in enumerate(MOUNTS,301):
        body=doc.addObject('PartDesign::Body',name+str(i));part.addObject(body)
        body.Label='Shim at H'+str(i)+' / OD5.2 ID2.3';body.Placement.Base=App.Vector(x,y,0)
        sketch=body.newObject('Sketcher::SketchObject','ShimProfile'+str(i))
        for radius in (2.6,1.15):
            n=sketch.addGeometry(Part.Circle(App.Vector(0,0,0),App.Vector(0,0,1),radius),False)
            sketch.addConstraint(Sketcher.Constraint('Coincident',n,3,-1,1))
            sketch.addConstraint(Sketcher.Constraint('Radius',n,radius))
        doc.recompute();assert sketch.FullyConstrained
        pad=body.newObject('PartDesign::Pad','ShimStack'+str(i));pad.Profile=sketch
        pad.setExpression('Length',params.Name+'.Stack');body.Tip=pad
        if App.GuiUp:sketch.Visibility=False;body.ViewObject.ShapeColor=(.72,.83,.88)
    doc.recompute()
    for body in [b for b in part.Group if b.TypeId=='PartDesign::Body']:
        assert body.Shape.isValid()and len(body.Shape.Solids)==1
        assert abs(body.Shape.Volume-math.pi*(2.6**2-1.15**2)*stack_mm)<1e-8
    return part

def validate_shims(part):
    """Check saved native sketches, expressions and global annular extents."""
    part.Document.recompute();stack=float(part.Parameters.Stack)
    top=float(part.Parameters.PCBTopZ);roof=float(part.Parameters.RoofSeatZ)
    assert .5<=stack<=1.5 and abs(top+stack-roof)<1e-8
    bodies=[b for b in part.Group if b.TypeId=='PartDesign::Body']
    assert len(bodies)==4
    for body,(x,y)in zip(bodies,MOUNTS):
        assert body.Tip.TypeId=='PartDesign::Pad'and body.Tip.Profile[0].FullyConstrained
        shape=body.Shape.copy();shape.transformShape(part.Placement.toMatrix())
        assert shape.isValid()and len(shape.Solids)==1
        assert abs(shape.Volume-math.pi*(2.6**2-1.15**2)*stack)<1e-8
        assert all(abs(a-b)<1e-7 for a,b in zip(_bounds(shape),[x-2.6,y-2.6,top,x+2.6,y+2.6,roof]))
    return {'native_bodies':[b.Name for b in bodies],'stack_mm':stack,'PCB_top_Z_mm':top,
            'roof_seat_Z_mm':roof,'fully_constrained_profiles':4,'native_pad_geometry_valid':True}

def measured_datums():
    """Measure actual OEM surfaces; none is promoted to a loaded contact datum."""
    source=_source();housing,latch=source.Solids
    lower=[];upper=[];stops=[]
    for i,f in enumerate(housing.Faces,1):
        t=f.Surface;b=_bounds(f)
        if isinstance(t,Part.Cylinder):
            # Match actual terminal arc face extents, not a fitted proxy.
            if abs(b[1]-.590696)<1e-5 and abs(b[2]-2.900856)<1e-5:lower.append(b)
            if abs(b[1]-1.487)<1e-7 and abs(b[2]-3.2475)<1e-7:upper.append(b)
        if isinstance(t,Part.Plane)and abs(t.Position.z-.5)<1e-7 and f.normalAt(0,0).z>.999:
            if abs(b[1]-.725)<1e-7 and abs(b[4]-1.475)<1e-7:stops.append({'face':i,'bounds':b,'normal':[0,0,1]})
    assert len(lower)==27 and len(upper)==27 and len(stops)>=26
    def row(faces):
        return {'count':len(faces),'source_height_Y_mm':[min(b[1]for b in faces),max(b[4]for b in faces)],
                'source_axial_Z_mm':[min(b[2]for b in faces),max(b[5]for b in faces)]}
    tip_global_y=112.575222039;land_global_y=114.0
    tip=land_global_y-LAND_ROW_REAR_HOUSING_OFFSET-tip_global_y
    rows={'lower_terminal_arcs':row(lower),'upper_terminal_arcs':row(upper)}
    for r in rows.values():
        a,b=r['source_axial_Z_mm'];assert tip<a<b<tip+2.8
        r['fixed_FPC_tip_margin_mm']=a-tip
        r['minimum_2_8mm_land_coverlay_margin_mm']=tip+2.8-b
    underside=latch.Faces[61];upface=latch.Faces[83]
    assert underside.normalAt(0,0).y<-.999 and upface.normalAt(0,0).y>.999
    return {'source_SHA256':SOURCE_SHA256,'coordinate_frame':'Unchanged manufacturer STEP axes: X terminal row,Y height,Z toward mouth',
            'actual_contact_reference_rows':rows,'rear_intercontact_walls':stops,
            'actuator_underside_face62':{'bounds':_bounds(underside),'normal':list(underside.normalAt(0,0)),'is_cable_support_floor':False},
            'actuator_upface84':{'bounds':_bounds(upface),'normal':list(upface.normalAt(0,0))},
            'fixed_FPC':{'tip_global_Y_mm':tip_global_y,'copper_face_global_Z_mm':61.7,'copper_face_normal':[0,0,-1],
                         'tip_OEM_Z_mm':tip,'exposed_land_OEM_Z_nominal_mm':[tip,tip+3.0],
                         'exposed_land_OEM_Z_minimum_mm':[tip,tip+2.8],'closed_front_global_Y_mm':108.9,
                         'depth_from_closed_front_mm':tip_global_y-108.9,'drawing_reference_depth_mm':3.0,
                         'deeper_than_drawing_reference_mm':tip_global_y-108.9-3,
                         'distance_before_modeled_rear_walls_mm':tip-.5,'loaded_copper_height_qualified':False,
                         'limitation':'Axial overlap only.2013 open-model arcs/stop walls are not a2018 loaded contact-height or insertion-stop specification.'}}

def export_board_model(part,path):
    """Export exact closed OEM solids in physical board XYZ, for identity model pose."""
    part.Document.recompute();shapes=[]
    for body in part.Group:
        if body.TypeId=='PartDesign::Body':
            shape=body.Tip.Shape.copy();shape.transformShape(body.Placement.toMatrix());shapes.append(shape)
    assert len(shapes)==2 and abs(float(part.Parameters.ActuatorSlide)-LATCH_STROKE)<1e-8
    compound=Part.makeCompound(shapes);compound.exportStep(str(path))
    readback=Part.read(str(path));assert readback.isValid()and len(readback.Solids)==2
    assert len(readback.Faces)==1001 and abs(readback.Volume-compound.Volume)<1e-7
    assert all(abs(a-b)<1e-7 for a,b in zip(_bounds(readback),[-10.05,-5.1,-.04,10.05,.1,2]))
    return {'file':path.name,'SHA256':hashlib.sha256(path.read_bytes()).hexdigest(),
            'valid':True,'solids':2,'faces':1001,'volume_mm3':readback.Volume,
            'exact_board_frame_bounds_mm':_bounds(readback),'KiCad_model_offset_mm':[0,0,0],
            'KiCad_model_rotation_deg':[0,0,0],'scale':[1,1,1],
            'loaded_copper_plane_qualified':False}

def main():
    OUT.mkdir(exist_ok=True);checks={}
    for pose,suffix in (('oem_open','OEMOpen'),('closed_envelope','ClosedEnvelope')):
        d=App.newDocument('Socket'+suffix);part=build(d,pose=pose)
        checks[pose]=validate(part);path=OUT/('Molex524372771'+suffix+'.FCStd')
        d.saveAs(str(path));App.closeDocument(d.Name)
        reopened=App.openDocument(str(path));checks[pose]['saved_readback']=validate(reopened.getObject('DockLCDSocket'))
        if pose=='closed_envelope':
            checks['board_model_export']=export_board_model(reopened.getObject('DockLCDSocket'),OUT/'Molex524372771ClosedBoardFrame.step')
        App.closeDocument(reopened.Name)
    d=App.newDocument('SocketShimTrial');shims=build_trial_shims(d)
    params=shims.Parameters
    for value in (.5,1.5,1.0):
        params.Stack=value;d.recompute()
        for b in shims.Group:
            if b.TypeId=='PartDesign::Body':assert b.Shape.isValid()and len(b.Shape.Solids)==1
        assert abs(float(params.PCBTopZ)-(61.5-value))<1e-8
    shimcheck=validate_shims(shims)
    d.saveAs(str(OUT/'LCDSocketTrialShims.FCStd'));App.closeDocument(d.Name)
    d=App.openDocument(str(OUT/'LCDSocketTrialShims.FCStd'))
    shimreadback=validate_shims(d.getObject('LCDSocketTrialShims'));App.closeDocument(d.Name)
    checks['shim_trial']={'native_bodies':4,'fully_constrained_annular_profiles':4,'mount_XY_mm':MOUNTS,
                          'OD_mm':5.2,'ID_mm':2.3,'stack_range_mm':[.5,1.5],'proposed_roof_seat_Z_mm':61.5,
                          'resulting_PCB_top_range_mm':[60,61],'edit_range_checks_pass':True,
                          'native_validation':shimcheck,'saved_readback':shimreadback,'physical_mating_qualified':False}
    (OUT/'geometry-datums.json').write_text(json.dumps(measured_datums(),indent=2)+'\n')
    checks['outputs_sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest()for f in OUT.glob('*.FCStd')}
    checks['outputs_sha256']['geometry-datums.json']=hashlib.sha256((OUT/'geometry-datums.json').read_bytes()).hexdigest()
    checks['FreeCAD_version']=App.Version();checks['builder_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (OUT/'native-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    print(json.dumps({'OEM_solids':2,'actual_contacts':27,'native_open_closed_saved_readback':'pass','shim_edit_range':'pass','loaded_contact_plane_qualified':False}))

if __name__=='__main__':main()
