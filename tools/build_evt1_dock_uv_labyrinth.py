"""Native dock seam upstand/relief trial; no optical containment qualification.

The integration function appends editable sketch/pad/pocket features to two
identity-placed shell Bodies. This standalone trial reads exact shell, liner
and hinge-pin BReps from the saved master, then uses the frozen front-closure
helper. Source documents and frozen helpers are never saved by this module.
"""
from pathlib import Path
import hashlib,json,math,sys,zipfile,xml.etree.ElementTree as ET
import FreeCAD as App
import Part,Sketcher,Mesh,MeshPart
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/cad/evt1-assembly/uv-seam-trial'
MASTER=ROOT/'hardware/cad/evt1-assembly/DockAssembly.FCStd'
sys.path.insert(0,str(ROOT/'tools'))
import build_evt1_dock_front_closure as closure

ANGLES=(0,.25,.5,1,2,3,5,10,110)
GEOMETRY={
    'center_Y_mm':77.5,
    'base_outer_WH_R_mm':[127.5,162.5,48.75],
    'base_inner_WH_R_mm':[125.5,160.5,47.75],
    'base_Z_mm':[40.,43.],
    'base_front_interruption_X_mm':[-9.5,9.5],
    'base_front_interruption_Y_below_mm':.8,
    'lid_relief_WH_R_mm':[128.1,163.1,49.05],
    'lid_relief_Z_mm':[40.2,43.4],
    'lid_relief_front_exclusion_X_mm':[-9.2,9.2],
    'lid_relief_front_exclusion_Y_below_mm':6.5,
    'closed_nominal_radial_clearance_mm':.3,
    'closed_nominal_axial_clearance_mm':.4,
    'front_baffle_overlap_each_side_mm':2.5,
    'front_return_cheeks_X_mm':[[-13.5,-12.5],[12.5,13.5]],
    'front_return_cheeks_YZ_mm':[-3.75,10,39.6,43],
    'upper_liner_cheek_entry_X_mm':[[-13.8,-12.2],[12.2,13.8]],
    'upper_liner_cheek_entry_YZ_mm':[-4.05,10.3,40.2,43.3],
    'lower_liner_loading_slots_X_mm':[[-13.8,-12.2],[12.2,13.8]],
    'lower_liner_loading_slots_YZ_mm':[-4.05,10.3,10,58],
    'lower_plug_side_wings_X_mm':[[-15.5,-11.8],[11.8,15.5]],
    'lower_plug_side_wings_YZ_mm':[2.3,4.3,13.2,39.8],
    'lower_plug_floor_wings_rear_Y_mm':12.3,
    'lower_plug_cheek_clearance_X_mm':[[-13.8,-12],[12,13.8]],
    'lower_plug_cheek_clearance_YZ_mm':[2,4.6,39.3,40.1],
    'upper_liner_rear_web_loading_notch_WH_R_mm':[27.8,10.6,.4],
    'upper_liner_rear_web_loading_notch_YZ_mm':[159.4,40.4,47.2],
    'hinge_axis_YZ_mm':[164.4,40.15],
}

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def bounds(shape):
    b=shape.optimalBoundingBox(False,False)
    return [getattr(b,k)for k in('XMin','YMin','ZMin','XMax','YMax','ZMax')]
def prop(obj,kind,name,value,group='Engineering'):
    obj.addProperty(kind,name,group);setattr(obj,name,value)

def rr_wire(w,h,r,cy=77.5):
    """Exact analytic rounded-rectangle wire in XY, Z0."""
    x,y=w/2,h/2;q=math.sqrt(.5);v=lambda a:App.Vector(a[0],a[1]+cy,0)
    segments=[((-x+r,-y),(x-r,-y),None),((x-r,-y),(x,-y+r),(x-r+r*q,-y+r-r*q)),
              ((x,-y+r),(x,y-r),None),((x,y-r),(x-r,y),(x-r+r*q,y-r+r*q)),
              ((x-r,y),(-x+r,y),None),((-x+r,y),(-x,y-r),(-x+r-r*q,y-r+r*q)),
              ((-x,y-r),(-x,-y+r),None),((-x,-y+r),(-x+r,-y),(-x+r-r*q,-y+r-r*q))]
    return Part.Wire([Part.makeLine(v(a),v(b))if c is None else Part.Arc(v(a),v(c),v(b)).toShape()for a,b,c in segments])

def base_profile_face():
    ring=Part.Face(rr_wire(*GEOMETRY['base_outer_WH_R_mm'])).cut(Part.Face(rr_wire(*GEOMETRY['base_inner_WH_R_mm'])))
    cut=Part.Face(Part.makePolygon([App.Vector(x,y,0)for x,y in[(-9.5,-20),(9.5,-20),(9.5,.8),(-9.5,.8),(-9.5,-20)]]))
    face=ring.cut(cut)
    assert face.isValid()and len(face.Faces)==1 and len(face.Wires)==1
    return face

def relief_profile_face():
    face=Part.Face(rr_wire(*GEOMETRY['lid_relief_WH_R_mm']))
    cut=Part.Face(Part.makePolygon([App.Vector(x,y,0)for x,y in[(-9.2,-20),(9.2,-20),(9.2,6.5),(-9.2,6.5),(-9.2,-20)]]))
    face=face.cut(cut)
    assert face.isValid()and len(face.Faces)==1 and len(face.Wires)==1
    return face

def sketch_from_face(body,name,face,z):
    """BRep wire only seeds native analytic sketch geometry; no shape proxy."""
    sk=body.newObject('Sketcher::SketchObject',name);sk.Placement.Base.z=z
    for wire in face.Wires:
        for edge in wire.OrderedEdges:
            u0,u1=edge.FirstParameter,edge.LastParameter
            a,b=edge.valueAt(u0),edge.valueAt(u1)
            if isinstance(edge.Curve,Part.Line):geom=Part.LineSegment(a,b)
            elif isinstance(edge.Curve,Part.Circle):geom=Part.Arc(a,edge.valueAt((u0+u1)/2),b)
            else:raise AssertionError(('Nonanalytic profile edge',type(edge.Curve)))
            i=sk.addGeometry(geom,False);sk.addConstraint(Sketcher.Constraint('Block',i))
    body.Document.recompute();assert sk.FullyConstrained,name
    return sk

def add_labyrinth(base_body,lid_body,prefix='UVSeam'):
    """Append native base upstand and lid relief to identity shell Bodies.

    Bodies must use the closed dock XYZ frame, with body Placement identity.
    Parent App::Part hinge placement may be nonidentity. Apply after the frozen
    front catch and before final whole-assembly checks. Returns named features.
    No source/master document is opened or saved by this function.
    """
    assert base_body.Document is lid_body.Document
    for body in(base_body,lid_body):
        assert body.TypeId=='PartDesign::Body'
        assert body.Placement.isIdentity(),body.Name
        assert body.Tip.Shape.isValid()and len(body.Tip.Shape.Solids)==1
    base=closure.feature(base_body,prefix+'BaseUpstand','Pad',sketch_from_face(base_body,prefix+'BaseUpstandProfile',base_profile_face(),40),3)
    cheek_profile=base_body.newObject('Sketcher::SketchObject',prefix+'BaseReturnCheeksProfile');cheek_profile.Placement.Base.z=39.6
    for x0,x1 in GEOMETRY['front_return_cheeks_X_mm']:
        points=[(x0,-3.75),(x1,-3.75),(x1,10),(x0,10)]
        for a,b in zip(points,points[1:]+points[:1]):
            i=cheek_profile.addGeometry(Part.LineSegment(App.Vector(*a,0),App.Vector(*b,0)),False)
            cheek_profile.addConstraint(Sketcher.Constraint('Block',i))
    cheeks=closure.feature(base_body,prefix+'BaseReturnCheeks','Pad',cheek_profile,3.4)
    lid=closure.feature(lid_body,prefix+'LidEntryRelief','Pocket',sketch_from_face(lid_body,prefix+'LidEntryReliefProfile',relief_profile_face(),43.4),3.2)
    for obj in(base,cheeks,lid):
        prop(obj,'App::PropertyString','NominalGeometry',json.dumps(GEOMETRY),'Source')
        prop(obj,'App::PropertyBool','OpticalContainmentQualified',False,'Qualification')
    return {'base_upstand':base,'base_return_cheeks':cheeks,'lid_entry_relief':lid}

def add_liner_entry_relief(upper_liner,prefix='UVSeam'):
    """Explicit0.3mm nominal entry allowance for the two fixed base cheeks.

    Apply to the identity-placed upper cream liner after its front-catch slot.
    No frozen closure feature is modified. Closed and moving clearances still
    require the caller's complete assembly verification.
    """
    assert upper_liner.TypeId=='PartDesign::Body'and upper_liner.Placement.isIdentity()
    profile=upper_liner.newObject('Sketcher::SketchObject',prefix+'UpperLinerEntryProfiles');profile.Placement.Base.z=43.3
    for x0,x1 in GEOMETRY['upper_liner_cheek_entry_X_mm']:
        points=[(x0,-4.05),(x1,-4.05),(x1,10.3),(x0,10.3)]
        for a,b in zip(points,points[1:]+points[:1]):
            i=profile.addGeometry(Part.LineSegment(App.Vector(*a,0),App.Vector(*b,0)),False)
            profile.addConstraint(Sketcher.Constraint('Block',i))
    front=closure.feature(upper_liner,prefix+'UpperLinerEntryRelief','Pocket',profile,3.1)
    # The original rear notch ended at46.2. During vertical installation its
    # taper still intrudes into the web until46.4015;47.2 leaves0.3166mm inY.
    closure.feature(upper_liner,prefix+'UpperLinerWebLoadingRelief','Pocket',
                    closure.rr(upper_liner,prefix+'UpperLinerWebLoadingProfile',27.8,10.6,.4,(0,159.4,47.2)),6.8)
    return front

def add_lower_liner_loading_slots(lower_liner,prefix='UVSeam'):
    """Full-depth slots allow vertical installation past integral return cheeks."""
    assert lower_liner.TypeId=='PartDesign::Body'and lower_liner.Placement.isIdentity()
    profile=lower_liner.newObject('Sketcher::SketchObject',prefix+'LowerLinerLoadingSlotsProfile');profile.Placement.Base.z=58
    for x0,x1 in GEOMETRY['lower_liner_loading_slots_X_mm']:
        points=[(x0,-4.05),(x1,-4.05),(x1,10.3),(x0,10.3)]
        for a,b in zip(points,points[1:]+points[:1]):
            i=profile.addGeometry(Part.LineSegment(App.Vector(*a,0),App.Vector(*b,0)),False)
            profile.addConstraint(Sketcher.Constraint('Block',i))
    return closure.feature(lower_liner,prefix+'LowerLinerLoadingSlots','Pocket',profile,48)

def add_lower_slot_baffles(lower_retainer,prefix='UVSeam'):
    """Append slot-covering wings to the existing captive plug; no new part.

    The frozen closure builder remains unchanged. Install this combined plug
    only after the slotted lower liner. Floor wings overlap the rear of the
    new through-slots by2mm at a nominal0.2mm floor allowance.
    """
    assert lower_retainer.TypeId=='PartDesign::Body'and lower_retainer.Placement.isIdentity()
    profile=lower_retainer.newObject('Sketcher::SketchObject',prefix+'LowerSlotWallWingsProfile');profile.Placement.Base.z=13.2
    for x0,x1 in GEOMETRY['lower_plug_side_wings_X_mm']:
        points=[(x0,2.3),(x1,2.3),(x1,4.3),(x0,4.3)]
        for a,b in zip(points,points[1:]+points[:1]):
            i=profile.addGeometry(Part.LineSegment(App.Vector(*a,0),App.Vector(*b,0)),False)
            profile.addConstraint(Sketcher.Constraint('Block',i))
    wall=closure.feature(lower_retainer,prefix+'LowerSlotWallWings','Pad',profile,26.6)
    profile=lower_retainer.newObject('Sketcher::SketchObject',prefix+'LowerSlotCheekClearanceProfiles');profile.Placement.Base.z=40.1
    for x0,x1 in GEOMETRY['lower_plug_cheek_clearance_X_mm']:
        points=[(x0,2),(x1,2),(x1,4.6),(x0,4.6)]
        for a,b in zip(points,points[1:]+points[:1]):
            i=profile.addGeometry(Part.LineSegment(App.Vector(*a,0),App.Vector(*b,0)),False)
            profile.addConstraint(Sketcher.Constraint('Block',i))
    clearance=closure.feature(lower_retainer,prefix+'LowerSlotCheekClearances','Pocket',profile,.8)
    profile=lower_retainer.newObject('Sketcher::SketchObject',prefix+'LowerSlotFloorWingsProfile');profile.Placement.Base.z=13.2
    right=[(11.8,.5),(12.3,.5),(12.3,-1.7),(13.7,-1.7),(13.7,.5),(15.5,.5),(15.5,12.3),(11.8,12.3)]
    for points in(right,[(-x,y)for x,y in right]):
        for a,b in zip(points,points[1:]+points[:1]):
            i=profile.addGeometry(Part.LineSegment(App.Vector(*a,0),App.Vector(*b,0)),False)
            profile.addConstraint(Sketcher.Constraint('Block',i))
    floor=closure.feature(lower_retainer,prefix+'LowerSlotFloorWings','Pad',profile,1.2)
    return {'wall_wings':wall,'cheek_clearances':clearance,'floor_wings':floor}

def source_brep(path,name):
    with zipfile.ZipFile(path)as archive:
        tree=ET.fromstring(archive.read('Document.xml'))
        node=next(o for o in tree.findall('.//Object[@name="'+name+'"]')if o.find('./Properties/Property[@name="Shape"]')is not None)
        member=node.find('./Properties/Property[@name="Shape"]/Part').get('file');data=archive.read(member)
    shape=Part.Shape();shape.importBrepFromString(data.decode('ascii'))
    assert shape.isValid()and len(shape.Solids)==1,name
    return shape,{'native':str(Path(path).relative_to(ROOT)),'native_SHA256':sha(path),'object':name,'BRep_member':member,
                  'BRep_SHA256':hashlib.sha256(data).hexdigest(),'exact_bounds_mm':bounds(shape),'volume_mm3':shape.Volume}

def build(doc,name='UVSeam',master_path=MASTER):
    root=doc.addObject('App::Part',name);root.Label='Native dock seam labyrinth / unqualified opaque geometry trial'
    parameters=doc.addObject('App::FeaturePython',name+'Parameters')
    prop(parameters,'App::PropertyAngle','OpeningAngle',0,'Pose')
    prop(root,'App::PropertyLinkGlobal','Parameters',parameters,'Pose')
    prop(root,'App::PropertyBool','OpticalContainmentQualified',False,'Qualification')
    source=[]
    for side in('lower','upper'):
        group=doc.addObject('App::Part',name+side.title());root.addObject(group)
        prop(root,'App::PropertyLink',side.title(),group,'Modules')
        body=closure.new_body(doc,group,name+side.title()+'Shell','Exact saved '+side+' shell / front catch and UV seam trial')
        shape,info=source_brep(Path(master_path),'LowerShell'if side=='lower'else'UpperShell');source.append(info)
        seed=body.newObject('PartDesign::Feature',name+side.title()+'SavedShell');seed.Shape=shape;body.Tip=seed
        closure.add_catch(body,side,prefix=name+side.title()+'Catch')
        liner=closure.new_body(doc,group,name+side.title()+'Liner','Exact saved '+side+' cream liner / frozen closure loading slot')
        shape,info=source_brep(Path(master_path),'LowerChamber'if side=='lower'else'UpperChamber');source.append(info)
        seed=liner.newObject('PartDesign::Feature',name+side.title()+'SavedLiner');seed.Shape=shape;liner.Tip=seed
        closure.add_liner_clearance(liner,side,prefix=name+'ClosureLiner')
        closure.build_retainer(doc,group,side,name+side.title()+'Retainer')
        for i in range(2):closure.build_magnet(doc,group,side,i,name+side.title()+'Magnet'+str(i+1))
        closure.build_screw(doc,group,side,name+side.title()+'RetainerScrew')
        if App.GuiUp:
            body.ViewObject.ShapeColor=(.96,.34,.07)if side=='upper'else(.12,.14,.16)
            liner.ViewObject.ShapeColor=(.90,.86,.76)
    base=next(b for b in root.Lower.Group if b.Name.endswith('Shell'))
    lid=next(b for b in root.Upper.Group if b.Name.endswith('Shell'))
    result=add_labyrinth(base,lid,prefix=name)
    prop(root,'App::PropertyLink','BaseUpstand',result['base_upstand'],'Features')
    prop(root,'App::PropertyLink','BaseReturnCheeks',result['base_return_cheeks'],'Features')
    prop(root,'App::PropertyLink','LidEntryRelief',result['lid_entry_relief'],'Features')
    liner=next(b for b in root.Upper.Group if b.Name.endswith('Liner'))
    prop(root,'App::PropertyLink','UpperLinerEntryRelief',add_liner_entry_relief(liner,prefix=name),'Features')
    prop(root,'App::PropertyLink','UpperLinerWebLoadingRelief',liner.Tip,'Features')
    liner=next(b for b in root.Lower.Group if b.Name.endswith('Liner'))
    prop(root,'App::PropertyLink','LowerLinerLoadingSlots',add_lower_liner_loading_slots(liner,prefix=name),'Features')
    retainer=next(b for b in root.Lower.Group if b.Name.endswith('Retainer'))
    wings=add_lower_slot_baffles(retainer,prefix=name)
    prop(root,'App::PropertyLink','LowerSlotWallWings',wings['wall_wings'],'Features')
    prop(root,'App::PropertyLink','LowerSlotCheekClearances',wings['cheek_clearances'],'Features')
    prop(root,'App::PropertyLink','LowerSlotFloorWings',wings['floor_wings'],'Features')
    pin=closure.new_body(doc,root.Lower,name+'HingePin','Exact saved selected hinge pin')
    shape,info=source_brep(Path(master_path),'CustomHingePin');source.append(info)
    seed=pin.newObject('PartDesign::Feature',name+'SavedHingePin');seed.Shape=shape;pin.Tip=seed
    if App.GuiUp:pin.ViewObject.ShapeColor=(.55,.57,.60)
    root.Upper.setExpression('Placement','create(<<placement>>;create(<<vector>>;0;0;0);create(<<rotation>>;create(<<vector>>;1;0;0);-'+parameters.Name+'.OpeningAngle);create(<<vector>>;0;164.4;40.15))')
    prop(root,'App::PropertyString','ReadOnlySourceGeometry',json.dumps(source),'Source')
    doc.recompute();return root

def items(root,side):
    group=getattr(root,side.title())
    return [(b.Name,closure.placed(group,b))for b in group.Group if b.TypeId=='PartDesign::Body']

def validate_pose(root):
    root.Document.recompute();rows=[]
    for side in('lower','upper'):
        group=getattr(root,side.title())
        for body in group.Group:
            if body.TypeId!='PartDesign::Body':continue
            shape=closure.placed(group,body)
            assert shape.isValid()and len(shape.Solids)==1,body.Name
            for obj in body.Group:
                if obj.TypeId=='Sketcher::SketchObject':assert obj.FullyConstrained,obj.Name
            bb=bounds(shape);shape.tessellate(.5)
            assert all(abs(a-b)<1e-7 for a,b in zip(bb,bounds(shape)))
            rows.append({'body':body.Name,'exact_bounds_mm':bb,'volume_mm3':shape.Volume})
    findings=[];lower=items(root,'lower');upper=items(root,'upper')
    for an,a in lower:
        for bn,b in upper:
            if a.optimalBoundingBox(False,False).intersect(b.optimalBoundingBox(False,False)):
                common=a.common(b).Volume
                if common>1e-7:findings.append({'a':an,'b':bn,'common_mm3':common})
    return {'opening_degrees':float(root.Parameters.OpeningAngle),'bodies':rows,'cross_module_pairs':len(lower)*len(upper),'overlap_findings':findings}

def validate_added_geometry(root):
    assert abs(float(root.Parameters.OpeningAngle))<1e-8
    base=root.BaseUpstand;lid=root.LidEntryRelief
    def preceding(feature):
        features=[o for o in feature.getParentGeoFeatureGroup().Group if o.TypeId.startswith('PartDesign::')and hasattr(o,'Shape')]
        return features[features.index(feature)-1]
    oldbase=preceding(base).Shape;oldlid=preceding(lid).Shape
    finalbase=root.BaseReturnCheeks.Shape
    added=finalbase.cut(oldbase);removed=oldlid.cut(lid.Shape)
    ideal=base_profile_face().extrude(App.Vector(0,0,3));ideal.translate(App.Vector(0,0,40))
    for x0,x1 in GEOMETRY['front_return_cheeks_X_mm']:ideal=ideal.fuse(Part.makeBox(x1-x0,13.75,3.4,App.Vector(x0,-3.75,39.6)))
    ideal=ideal.cut(oldbase)
    assert added.isValid()and len(added.Solids)==1
    assert added.cut(ideal).Volume<1e-7 and ideal.cut(added).Volume<1e-7
    assert abs(added.Volume-ideal.Volume)<1e-6
    assert finalbase.isValid()and len(finalbase.Solids)==1
    assert lid.Shape.isValid()and len(lid.Shape.Solids)==1
    assert finalbase.common(lid.Shape).Volume<1e-7
    clearance=added.distToShape(lid.Shape)[0]
    # The interrupted front profile has a shorter approach to the protected cup.
    assert clearance>=.299999
    internal=[]
    for side in('lower','upper'):
        group=getattr(root,side.title());shell=next(b for b in group.Group if b.Name.endswith('Shell'))
        extra=added if side=='lower'else removed
        for name,shape in items(root,side):
            if name==shell.Name:continue
            common=extra.common(shape).Volume
            assert common<1e-7,(side,name,common)
            internal.append({'side':side,'body':name,'changed_volume_intersection_mm3':common,'distance_to_changed_region_mm':extra.distToShape(shape)[0]})
    upperliner=next(s for n,s in items(root,'upper')if n.endswith('Liner'))
    liner_clearance=added.distToShape(upperliner)[0];assert liner_clearance>=.299999
    return {'nominal_geometry':GEOMETRY,'base_added_volume_mm3':added.Volume,'lid_removed_volume_mm3':removed.Volume,
            'closed_minimum_added_upstand_to_lid_mm':clearance,'changed_region_component_checks':internal,
            'closed_minimum_added_upstand_to_upper_liner_mm':liner_clearance,
            'upper_shell_remains_single_valid_solid':True,'minimum_nominal_lid_outer_wall_at_relief_bottom_mm':.95,
            'front_interruption_bridged_by_24mm_upper_and_extended31mm_lower_baffles':True,'opaque_material_or_strength_qualified':False}

def validate_loading(root):
    assert abs(float(root.Parameters.OpeningAngle))<1e-8
    # Required links reject an older native lacking the return-loading solution.
    assert root.LowerLinerLoadingSlots and root.LowerSlotWallWings and root.LowerSlotFloorWings and root.LowerSlotCheekClearances
    assert root.UpperLinerWebLoadingRelief
    result=[]
    for side in('lower','upper'):
        pieces=items(root,side);shell=next(s for n,s in pieces if n.endswith('Shell'))
        liner=next(s for n,s in pieces if n.endswith('Liner'));retainer=next(s for n,s in pieces if n.endswith('Retainer'))
        for i in range(33):
            moved=liner.copy();moved.translate(App.Vector(0,0,(32-i)*(1 if side=='lower'else-1)))
            volume=moved.common(shell).Volume
            assert volume<1e-7,(side,'vertical liner loading',i,volume)
        for i in range(17):
            moved=retainer.copy();moved.translate(App.Vector(0,8-i*.5,0))
            for label,shape in(('shell',shell),('liner',liner)):
                volume=moved.common(shape).Volume
                assert volume<1e-7,(side,'plug loading',label,i,volume)
        spec=closure.SIDES[side];rear=spec['bearing_y']+2
        driver=Part.makeCylinder(2.3,18,App.Vector(0,rear,spec['screw_z']),App.Vector(0,1,0))
        for name,shape in pieces:
            if not name.endswith('RetainerScrew'):assert driver.common(shape).Volume<1e-7,(side,'driver',name)
        result.append({'side':side,'vertical_liner_loading_poses':33,'plug_loading_poses':17,'plug_installed_after_liner':True,
                       'driver_corridor_diameter_mm':4.6,'driver_corridor_Y_mm':[rear,rear+18],'driver_Z_mm':spec['screw_z']})
    old=root.LowerLinerLoadingSlots.getParentGeoFeatureGroup()
    features=[o for o in old.Group if o.TypeId.startswith('PartDesign::')and hasattr(o,'Shape')]
    uncut=features[features.index(root.LowerLinerLoadingSlots)-1].Shape.copy();uncut.translate(App.Vector(0,0,30))
    shell=next(s for n,s in items(root,'lower')if n.endswith('Shell'))
    rejected=uncut.common(shell).Volume;assert rejected>1,'Loading regression must demonstrate real old-liner interference'
    return {'loading':result,'old_lower_liner_without_slots_at_plus30Z_interference_mm3':rejected,
            'additional_printed_parts':0,'full_product_loading_qualified':False,
            'assembly_sequence':'Slotted liners first; magnets then combined rear plugs/baffles; preassembled contact module afterward. Whole master geometry and received parts still require parent checks.'}

def perimeter_samples(steps=12):
    """Closed outer seam XY and outward unit normals, including corners."""
    out=[]
    for i in range(steps):
        t=(i+.5)/steps
        out.extend([((-15+30*t,-5),(0,-1)),((65,45+65*t),(1,0)),((15-30*t,160),(0,1)),((-65,110-65*t),(-1,0))])
    for cx,cy,start in((15,45,-90),(15,110,0),(-15,110,90),(-15,45,180)):
        for i in range(steps*2):
            a=math.radians(start+90*(i+.5)/(steps*2));nx,ny=math.cos(a),math.sin(a)
            out.append(((cx+50*nx,cy+50*ny),(nx,ny)))
    return out

def segment_blockers(a,b,shapes):
    line=Part.makeLine(App.Vector(*a),App.Vector(*b));blocked=[]
    for name,shape in shapes:
        common=line.common(shape)
        if common.Length>1e-6:blocked.append({'body':name,'material_intersection_length_mm':common.Length})
    return blocked

class TriangleBVH:
    """Segment/triangle acceleration over the native derived mesh only."""
    def __init__(self,mesh):
        points,indices=mesh.Topology
        p=np.asarray([[v.x,v.y,v.z]for v in points],dtype=float)
        triangles=p[np.asarray(indices,dtype=int)]
        self.v0=triangles[:,0];self.e1=triangles[:,1]-self.v0;self.e2=triangles[:,2]-self.v0
        low=triangles.min(axis=1);high=triangles.max(axis=1);centers=(low+high)*.5
        self.nodes=[]
        def split(ids):
            index=len(self.nodes);lo=low[ids].min(axis=0);hi=high[ids].max(axis=0);self.nodes.append(None)
            if len(ids)<=20:self.nodes[index]=(tuple(lo),tuple(hi),None,None,ids)
            else:
                axis=int(np.argmax(np.ptp(centers[ids],axis=0)));mid=len(ids)//2
                order=np.argpartition(centers[ids,axis],mid);left=split(ids[order[:mid]]);right=split(ids[order[mid:]])
                self.nodes[index]=(tuple(lo),tuple(hi),left,right,None)
            return index
        split(np.arange(len(triangles),dtype=int))

    def blocked(self,start,end):
        origin=np.asarray(start,dtype=float);direction=np.asarray(end,dtype=float)-origin
        inverse=tuple(1/v if abs(v)>1e-14 else None for v in direction)
        stack=[0]
        while stack:
            lo,hi,left,right,ids=self.nodes[stack.pop()];minimum=0.;maximum=1.;passes=True
            for axis in range(3):
                if inverse[axis]is None:
                    if start[axis]<lo[axis]-1e-9 or start[axis]>hi[axis]+1e-9:passes=False;break
                else:
                    a=(lo[axis]-start[axis])*inverse[axis];b=(hi[axis]-start[axis])*inverse[axis]
                    if a>b:a,b=b,a
                    minimum=max(minimum,a);maximum=min(maximum,b)
                    if maximum<minimum:passes=False;break
            if not passes:continue
            if ids is None:stack.append(left);stack.append(right);continue
            e1,e2=self.e1[ids],self.e2[ids];pv=np.cross(direction,e2)
            determinant=np.einsum('ij,ij->i',e1,pv);valid=np.abs(determinant)>1e-12
            inv=np.divide(1.,determinant,out=np.zeros_like(determinant),where=valid)
            tv=origin-self.v0[ids];u=np.einsum('ij,ij->i',tv,pv)*inv
            qv=np.cross(tv,e1);v=np.einsum('ij,j->i',qv,direction)*inv
            t=np.einsum('ij,ij->i',e2,qv)*inv
            if np.any(valid&(u>=-1e-10)&(v>=-1e-10)&(u+v<=1+1e-10)&(t>1e-8)&(t<1-1e-8)):return True
        return False

def protected_point(p):
    """Limit source samples to nominal cream chamber air, not outer pockets."""
    x,y,z=p
    if not 13.2<z<55.5:return False
    f=max(0,(z-40.5)/15.)
    w,h,r=119.4-13.4*f,154.4-13.4*f,44.7-6.7*f
    dx=max(0,abs(x)-(w/2-r));dy=max(0,abs(y-77.5)-(h/2-r))
    return dx*dx+dy*dy<(r-.05)**2

def validate_ray_controls(root,shapes,bvh):
    # Side-gap control: deleting the ring must expose the original seam.
    oldbody=root.BaseUpstand.getParentGeoFeatureGroup()
    features=[o for o in oldbody.Group if o.TypeId.startswith('PartDesign::')and hasattr(o,'Shape')]
    old=features[features.index(root.BaseUpstand)-1].Shape
    no_upstand=[(n,old if n.endswith('LowerShell')else s)for n,s in shapes]
    side_a,side_b=(0,80,40.15),(77,80,40.15)
    assert not segment_blockers(side_a,side_b,no_upstand)
    assert segment_blockers(side_a,side_b,shapes)and bvh.blocked(side_a,side_b)
    # Exact opposite-side skew rays demonstrated why simple finite-width bars
    # needed the integral return cheeks. Preserve the open reference as a test.
    without_cheeks=[(n,root.BaseUpstand.Shape if n.endswith('LowerShell')else s)for n,s in shapes]
    y=(16.8-math.sqrt(16.8**2+4*5*1484.11))/10
    controls=[]
    for sign in(-1,1):
        for z in(40.05,40.15,40.25):
            a=(sign*53.3,25,z);b=(sign*(2*y+3.3),y,z)
            assert protected_point(a)
            assert not segment_blockers(a,b,without_cheeks),(a,b,'reference should be clear')
            blocks=segment_blockers(a,b,shapes)
            assert blocks and bvh.blocked(a,b),(a,b,'return cheeks must block')
            controls.append({'interior_mm':a,'exterior_mm':b,'without_return_cheeks_exact_clear':True,'with_returns_exact_blockers':blocks})
    shallow=[]
    rejected=OUT/'rejected/UVSeamShallowGapRejected.FCStd'
    reference=json.loads((rejected.parent/'reference.json').read_text())
    assert sha(rejected)==reference['native_SHA256']
    reference_doc=App.openDocument(str(rejected));reference_root=reference_doc.UVSeam
    reference_shapes=items(reference_root,'lower')+items(reference_root,'upper')
    App.closeDocument(reference_doc.Name)
    for sign in(-1,1):
        for slope in(-.0157,-.016):
            a=(sign*53.3,25,40.15+slope*30);b=(sign*(2*y+3.3),y,40.15+slope*(y+5))
            blocks=segment_blockers(a,b,shapes)
            assert blocks and bvh.blocked(a,b),(a,b,'downward cheek overlap must block shallow3D ray')
            assert not segment_blockers(a,b,reference_shapes),(a,b,'rejected variant must reproduce clear ray')
            shallow.append({'interior_mm':a,'exterior_mm':b,'exact_blockers':blocks,'rejected_native_exact_clear':True,'rejected_native_SHA256':sha(rejected)})
    return {'side_original_seam_control':{'without_upstand_exact_clear':True,'with_upstand_exact_blocked':True},'front_adversarial_controls':controls,'shallow_3D_regression_controls':shallow}

def ray_screen(root):
    """Finite opaque-geometry ray screen; candidate misses checked against BRep.

    This is deliberately not an all-rays visibility proof or optical result.
    Source points are in the protected interior, not in the outer lip pocket.
    """
    assert abs(float(root.Parameters.OpeningAngle))<1e-8
    shapes=items(root,'lower')+items(root,'upper')
    mesh=Mesh.Mesh()
    for name,shape in shapes:
        mesh.addMesh(MeshPart.meshFromShape(Shape=shape,LinearDeflection=.02,AngularDeflection=.12,Relative=False))
    print('ray mesh',mesh.CountFacets,'facets',flush=True)
    bvh=TriangleBVH(mesh);controls=validate_ray_controls(root,shapes,bvh)
    sources=[]
    candidates=[(x,y,z)for x in(-35,0,35)for y in(25,80,135)for z in(14.5,25,38,40.15,42,54,55)]
    for (x,y),(nx,ny)in perimeter_samples(3):
        candidates.extend((x-inset*nx,y-inset*ny,z)for inset in(7,15)for z in(38,40.15,42,44.5))
    candidates.extend((x,y,z)for x in(-53.3,-35,-15,0,15,35,53.3)for y in(7,15,25)for z in(39.8,40.05,40.15,40.25,40.4,42,43.15))
    boxes=[s.optimalBoundingBox(False,False)for _,s in shapes]
    for p in candidates:
        point=App.Vector(*p)
        if protected_point(p)and not any(box.isInside(point)and s.isInside(point,.01,True)for box,(_,s)in zip(boxes,shapes)):sources.append(p)
    seam_targets=[(x,y,z)for(x,y),_ in perimeter_samples(6)for z in(40.01,40.15,40.29)]
    hinge_targets=[]
    for x in(-35,-25,-15,15,25,35):
        for i in range(16):
            angle=2*math.pi*(i+.5)/16
            hinge_targets.append((x,164.4+4.4*math.cos(angle),40.15+4.4*math.sin(angle)))
    for x in(-36.1,36.1):
        for i in range(8):
            angle=2*math.pi*(i+.5)/8
            hinge_targets.append((x,164.4+1.6*math.cos(angle),40.15+1.6*math.sin(angle)))
    for p in hinge_targets:
        point=App.Vector(*p)
        if not any(box.isInside(point)and s.isInside(point,.0001,True)for box,(_,s)in zip(boxes,shapes)):seam_targets.append(p)
    def extend_through_seam(a,target):
        # Preserve every source-to-aperture slope. A fixed-height external ring
        # would miss steep rays crossing the0.3mm outer seam at another height.
        length=math.sqrt(sum((target[i]-a[i])**2 for i in range(3)))
        factor=1+500/length
        return tuple(a[i]+factor*(target[i]-a[i])for i in range(3))
    calibration=[]
    for i in range(48):
        a=sources[(i*17)%len(sources)];b=extend_through_seam(a,seam_targets[(i*37)%len(seam_targets)])
        predicted=bvh.blocked(a,b);actual=bool(segment_blockers(a,b,shapes))
        assert predicted==actual,('Mesh/BRep calibration mismatch',a,b)
        calibration.append({'interior_mm':a,'exterior_mm':b,'mesh_blocked':predicted,'exact_BRep_blocked':actual})
    tested=0;misses=[];mesh_misses=0
    for a in sources:
        for target in seam_targets:
            b=extend_through_seam(a,target)
            blocked=bvh.blocked(a,b);tested+=1
            if not blocked:
                mesh_misses+=1;blocks=segment_blockers(a,b,shapes)
                if not blocks:misses.append({'interior_mm':a,'exterior_mm':b})
        if tested%5000< len(seam_targets):print('ray screen',tested,'segments',flush=True)
    return {'method':'Finite opaque-solid mesh ray screen with segment/triangle BVH acceleration, every apparent clear segment rechecked against exact BRep. No all-ray proof, reflections, transmission or measured optical attenuation.',
            'source_count':len(sources),'seam_target_count':len(seam_targets),'sampled_segments':tested,'mesh_facets':mesh.CountFacets,
            'linear_mesh_deflection_mm':.02,'angular_mesh_deflection_radians':.12,'BRep_rechecked_apparent_clear_segments':mesh_misses,
            'direct_clear_segment_findings':misses,'all_source_points_mm':sources,
            'seam_targets':'6samples per straight/12per quadrant,3seamZ at40.01/40.15/40.29; plus free sampled hinge-eye annulusR4.4 and bore-endR1.6. Each interior-to-aperture direction is continued500mm beyond its aperture; endpoint height varies with ray slope.',
            'all_aperture_target_points_mm':seam_targets,
            'exact_BRep_reference_and_regression_controls':controls,
            'exact_BRep_mesh_calibration_segments':calibration,
            'optical_leakage_or_containment_qualified':False}

def frozen_sources():
    checks=ROOT/'hardware/cad/evt1-assembly/front-closure-trial/native-checks.json';data=json.loads(checks.read_text())
    assert sha(Path(closure.__file__))==data['builder_SHA256'],'Frozen closure helper changed'
    path=checks.parent/'FrontClosureTrial.FCStd';assert sha(path)==data['native_SHA256']
    manifest=checks.parent/'source-manifest.json';assert sha(manifest)==data['source_manifest_SHA256']
    rejected=OUT/'rejected/UVSeamShallowGapRejected.FCStd'
    reference=rejected.parent/'reference.json'
    assert sha(rejected)==json.loads(reference.read_text())['native_SHA256']
    return {str(p.relative_to(ROOT)):sha(p)for p in(MASTER,Path(closure.__file__),checks,path,manifest,rejected,reference)}

def export_coupons(root):
    """Exact cutouts are derived print-test sectors, not replacements for shell."""
    cases={'side':(-66,65,34,14,25,14),'front':(-16,-9,31,32,19,24),'hinge':(-40,150,33,80,21,17)}
    records={}
    for label,(x,y,z,w,h,d)in cases.items():
        clip=Part.makeBox(w,h,d,App.Vector(x,y,z));pieces=[]
        for side in('lower','upper'):
            shape=next(s for n,s in items(root,side)if n.endswith('Shell')).common(clip)
            assert shape.isValid()and shape.Volume>0
            path=OUT/(label+'-'+side+'-shell.step');shape.exportStep(str(path));readback=Part.read(str(path))
            assert readback.isValid()and len(readback.Solids)==len(shape.Solids)
            # This cropped spline loft has a1.414ppm GProp volume integration
            # difference despite zero symmetric BRep difference and submicron
            # boundary error. Keep geometry checks independent of that integral.
            delta=readback.Volume-shape.Volume
            assert abs(delta)<2e-6*max(1,shape.Volume),(label,side,delta)
            assert all(abs(a-b)<1e-5 for a,b in zip(bounds(shape),bounds(readback)))
            difference=[shape.cut(readback).Volume,readback.cut(shape).Volume]
            assert max(difference)<1e-7,(label,side,difference)
            errors=[]
            for a,b in((shape,readback),(readback,shape)):
                for edge in a.Edges:
                    for i in range(5):errors.append(Part.Vertex(edge.valueAt(edge.FirstParameter+(edge.LastParameter-edge.FirstParameter)*i/4)).distToShape(b)[0])
            assert max(errors)<1e-5,(label,side,max(errors))
            records[path.name]={'SHA256':sha(path),'clip_bounds_mm':[x,y,z,x+w,y+h,z+d],'solid_count':len(shape.Solids),'volume_mm3':shape.Volume,
                                'exact_bounds_mm':bounds(shape),'STEP_volume_delta_mm3':delta,'relative_volume_tolerance':2e-6,
                                'symmetric_BRep_difference_mm3':difference,'bidirectional_edge_samples':len(errors),'maximum_edge_distance_mm':max(errors),'linear_exchange_tolerance_mm':1e-5,
                                'source':'Exact final native shell cut; testonly. Includes native added/removed seam geometry.'}
    return records

def main():
    OUT.mkdir(parents=True,exist_ok=True);before=frozen_sources()
    if '--check-saved'in sys.argv:
        doc=App.openDocument(str(OUT/'UVSeamTrial.FCStd'));root=doc.UVSeam
        root.Parameters.OpeningAngle=0;doc.recompute();print('checking saved native',flush=True)
    else:
        doc=App.newDocument('UVSeamTrial');root=build(doc);print('native build complete',flush=True)
    closed=OUT/'UVSeamTrial.FCStd';doc.saveAs(str(closed))
    changed=validate_added_geometry(root);loading=validate_loading(root);poses=[]
    for angle in ANGLES:
        root.Parameters.OpeningAngle=angle;doc.recompute();result=validate_pose(root);poses.append(result)
        print('pose',angle,'overlaps',len(result['overlap_findings']),flush=True)
    print('GEOMETRY_API_FROZEN_SHA256',sha(Path(__file__)),flush=True)
    root.Parameters.OpeningAngle=0;doc.recompute();rays=ray_screen(root)
    doc.saveAs(str(closed));exports=export_coupons(root)
    root.Parameters.OpeningAngle=2;doc.recompute();opened=OUT/'UVSeamOpening2deg.FCStd';doc.saveAs(str(opened));App.closeDocument(doc.Name)
    doc=App.openDocument(str(closed));saved=validate_pose(doc.UVSeam);App.closeDocument(doc.Name)
    doc=App.openDocument(str(opened));saved_open=validate_pose(doc.UVSeam);App.closeDocument(doc.Name)
    after=frozen_sources();assert before==after,'Read-only source changed during trial'
    report={'FreeCAD_version':App.Version(),'builder_SHA256':sha(Path(__file__)),'read_only_sources_SHA256':before,'source_hashes_unchanged':True,
            'source_manifest_SHA256':sha(OUT/'source-manifest.json'),'native_SHA256':sha(closed),'opening_native_SHA256':sha(opened),
            'changed_geometry':changed,'loading':loading,'opening_pose_checks':poses,'closed_finite_ray_screen':rays,'saved_closed_readback':saved,'saved_opening_readback':saved_open,
            'STEP_print_test_sectors':exports,'full_product_or_optical_qualification':False}
    (OUT/'native-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'poses':len(poses),'overlap_findings':sum(len(p['overlap_findings'])for p in poses),'finite_ray_clear_findings':len(rays['direct_clear_segment_findings']),
                      'native_saved_readback':True,'frozen_sources_unchanged':True,'UV_qualification':False}),flush=True)

if __name__=='__main__':main()
