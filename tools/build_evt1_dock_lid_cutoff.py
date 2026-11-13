"""D2F-01L drawing-based native component; manufacturer CAD is login-gated.

Published mounting, case, terminal and blade dimensions are native features.
The blade's hinge/bend details are not dimensioned: its movable straight-blade
pose is an explicitly derived reference, not OEM geometry or a received OP/RP.
The mounting-hole centreline isZ0; length+X points fromCOM/hinge towardNC.
"""
from pathlib import Path
import hashlib,json,math
import FreeCAD as App
import Part,Sketcher

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/cad/evt1-assembly/vendor/lid-cutoff'
PDF_SHA256='d3f2ed08101cf7ec6f57577643225f73faa5475026dda0072bcddf2d99fb04db'
DATASHEET='https://omronfs.omron.com/en_US/ecb/products/pdf/en-d2f.pdf'
LENGTH=12.8;WIDTH=5.8;BLADE_LENGTH=12.8;BLADE_WIDTH=3;BLADE_T=.3
PIVOT_Z=4.7

def _angle(height):
    return math.asin((height-PIVOT_Z)/math.hypot(BLADE_LENGTH,BLADE_T))-math.atan2(BLADE_T,BLADE_LENGTH)

# At the drawing's nominal operating reference, A is10.8 past firstmountX-3.25.
# This solves a straight-blade reference root. It is NOT an OEM hinge datum.
PIVOT_X=7.55-(BLADE_LENGTH*math.cos(_angle(6.8))-BLADE_T*math.sin(_angle(6.8)))

def _bounds(shape):
    b=shape.optimalBoundingBox(False,False)
    return [getattr(b,k)for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax')]

def _property(obj,kind,name,value,group='Source'):
    obj.addProperty(kind,name,group);setattr(obj,name,value)

def _profile(body,name,points,z):
    sketch=body.newObject('Sketcher::SketchObject',name);sketch.Placement.Base.z=z
    for p,q in zip(points,points[1:]+points[:1]):
        i=sketch.addGeometry(Part.LineSegment(App.Vector(*p,0),App.Vector(*q,0)),False)
        sketch.addConstraint(Sketcher.Constraint('Block',i))
    return sketch

def _rectangle(body,name,x1,y1,x2,y2,z):
    return _profile(body,name,[(x1,y1),(x2,y1),(x2,y2),(x1,y2)],z)

def _pad(body,name,profile,length):
    body.Document.recompute();assert profile.FullyConstrained
    pad=body.newObject('PartDesign::Pad',name);pad.Profile=profile;pad.Length=length
    body.Tip=pad;body.Document.recompute()
    if App.GuiUp:profile.Visibility=False
    return pad

def _body(doc,part,name,label):
    body=doc.addObject('PartDesign::Body',name);part.addObject(body);body.Label=label
    return body

def build(doc,name='DockLidCutoff',pose='operating_reference'):
    """Return a native App::Part in the actual case/mounting-hole datum frame.

    'free_limit_reference' puts the derived blade at published FP MAX10mm.
    It must not be called a nominal free position or a travel limit.
    """
    assert pose in('operating_reference','free_limit_reference')
    part=doc.addObject('App::Part',name);part.Label='D2F-01L / drawing-based component and explicit pose limits'
    params=doc.addObject('App::FeaturePython',name+'Parameters')
    _property(part,'App::PropertyLinkGlobal','Parameters',params,'Reference pose')
    _property(part,'App::PropertyString','SelectedMPN','D2F-01L')
    _property(part,'App::PropertyString','ManufacturerSource','Omron B036-E1-12; current product page redirects to Aratas, formerly Omron Components')
    _property(part,'App::PropertyString','DatasheetURL',DATASHEET)
    _property(part,'App::PropertyString','DatasheetSHA256',PDF_SHA256)
    _property(part,'App::PropertyString','GeometryKind','Native dimensional reconstruction; not manufacturer STEP')
    _property(part,'App::PropertyString','LocalFrame','Origin at case centre on mounting-hole line; lengthX fromCOM/hinge toNC; widthY; actuatorupZ')
    _property(part,'App::PropertyString','Pins','X-5.08=COM;X0=NO;X+5.08=NC. These are function labels, not manufacturer pin numbers.')
    _property(part,'App::PropertyString','Limitations','Case outer dimensions/mounting/terminals/blade dimensions followp3/p4. Undimensioned case details, pin retention scallops, hinge, bentroot and internal plunger are omitted. Blade pose is derived, not OEM/received geometry.')
    _property(part,'App::PropertyBool','PhysicalFitQualified',False,'Qualification')
    _property(part,'App::PropertyBool','ReceivedOPRPMeasured',False,'Qualification')
    _property(params,'App::PropertyLength','BladeContactReferenceHeight',6.8 if pose=='operating_reference'else 10,'Reference pose')
    _property(params,'App::PropertyLength','BladeRootReferenceX',PIVOT_X,'Reference pose')
    _property(params,'App::PropertyLength','BladeRootReferenceZ',PIVOT_Z,'Reference pose')
    _property(params,'App::PropertyAngle','BladeReferenceAngle',math.degrees(_angle(float(params.BladeContactReferenceHeight))),'Reference pose')
    params.setExpression('BladeReferenceAngle','asin(('+params.Name+'.BladeContactReferenceHeight - 4.7 mm) / 12.803515142217872 mm) - atan(0.3 / 12.8)')
    for prop,value in(('OperatingPositionNominal',6.8),('OperatingPositionMinimum',5.3),('OperatingPositionMaximum',8.3),
                       ('FreePositionMaximum',10),('OvertravelMinimum',.55),('MovementDifferentialMaximum',.5),('DerivedReleasePositionUpperBound',8.8)):
        _property(params,'App::PropertyLength',prop,value,'Published / derived travel')
    _property(params,'App::PropertyForce','OperatingForceMaximum','0.78 N','Published / derived travel')
    _property(params,'App::PropertyForce','ReleaseForceMinimum','0.05 N','Published / derived travel')
    _property(params,'App::PropertyString','Pretravel','NOT PUBLISHED forhingelever; do not use nearby pin-plungerPT0.5mm','Published / derived travel')
    _property(params,'App::PropertyString','ReleasePosition','AbsoluteRP notpublished. Derived conservativeRP<=OP+MD<=8.8mm; measureeachreceivedunit.','Published / derived travel')
    _property(params,'App::PropertyString','OvertravelMeaning','OT MIN0.55 is minimumavailablepost-OPtravel, notmaximumtotaltravel.','Published / derived travel')

    case=_body(doc,part,name+'Case','Case / native pads and actual mounting-hole profiles')
    base=_rectangle(case,name+'LowerCaseProfile',-6.4,-2.9,6.4,2.9,-1.5)
    _pad(case,name+'LowerCasePad',base,2.9)
    top=_rectangle(case,name+'UpperCaseProfile',-6.35,-2.85,6.35,2.85,1.4)
    _pad(case,name+'UpperCasePad',top,3.6)
    # Front sketch axes(X,Z), pad/pocket normal-Y. The left hole is a2.2dia
    # circle with top/bottom flats2.0apart, as the dual callouts show onp4.
    hole=case.newObject('Sketcher::SketchObject',name+'MountingHoleProfiles')
    hole.Placement=App.Placement(App.Vector(0,2.9,0),App.Rotation(App.Vector(1,0,0),90))
    a=math.sqrt(1.1**2-1);cx=-3.25
    curves=[Part.LineSegment(App.Vector(cx-a,1,0),App.Vector(cx+a,1,0)),
            Part.Arc(App.Vector(cx+a,1,0),App.Vector(cx+1.1,0,0),App.Vector(cx+a,-1,0)),
            Part.LineSegment(App.Vector(cx+a,-1,0),App.Vector(cx-a,-1,0)),
            Part.Arc(App.Vector(cx-a,-1,0),App.Vector(cx-1.1,0,0),App.Vector(cx-a,1,0)),
            Part.Circle(App.Vector(3.25,0,0),App.Vector(0,0,1),1)]
    for curve in curves:
        i=hole.addGeometry(curve,False);hole.addConstraint(Sketcher.Constraint('Block',i))
    doc.recompute();assert hole.FullyConstrained
    pocket=case.newObject('PartDesign::Pocket',name+'MountingHoles');pocket.Profile=hole
    pocket.Length=5.8;pocket.Reversed=True;case.Tip=pocket
    if App.GuiUp:hole.Visibility=False;case.ViewObject.ShapeColor=(.12,.13,.14)

    for function,x in(('COM',-5.08),('NO',0),('NC',5.08)):
        pin=_body(doc,part,name+function,'PCB terminal '+function+' / nominal published straight section')
        _property(pin,'App::PropertyString','ElectricalFunction',function,'Electrical')
        _property(pin,'App::PropertyString','OmittedDetail','Undimensioned insertion-retention scallops are omitted; do not infer retention force.','Qualification')
        profile=_rectangle(pin,name+function+'Profile',x-.45,-.2,x+.45,.2,-5)
        _pad(pin,name+function+'Pad',profile,3.5)
        if App.GuiUp:pin.ViewObject.ShapeColor=(.7,.66,.5)

    blade=_body(doc,part,name+'Lever','3x0.3x12.8 blade / DERIVED hinge-pose reference')
    profile=_rectangle(blade,name+'LeverProfile',0,-1.5,12.8,1.5,0)
    _pad(blade,name+'LeverPad',profile,.3)
    blade.Placement.Base=App.Vector(PIVOT_X,0,PIVOT_Z)
    blade.Placement.Rotation=App.Rotation(App.Vector(0,1,0),-math.degrees(_angle(float(params.BladeContactReferenceHeight))))
    blade.setExpression('Placement.Rotation.Angle','-'+params.Name+'.BladeReferenceAngle')
    _property(blade,'App::PropertyString','PoseCaveat','Straight-blade reference solvesnominalA(X7.55,Z6.8); actualbentroot/pivotareundimensioned. Free-limit pose is not actual FP.','Qualification')
    if App.GuiUp:blade.ViewObject.ShapeColor=(.75,.76,.79)
    doc.recompute();validate(part)
    return part

def validate(part):
    part.Document.recompute();bodies=[b for b in part.Group if b.TypeId=='PartDesign::Body']
    assert abs(part.Parameters.OperatingForceMaximum.getValueAs('N').Value-.78)<1e-10
    assert abs(part.Parameters.ReleaseForceMinimum.getValueAs('N').Value-.05)<1e-10
    assert len(bodies)==5
    rows=[]
    for body in bodies:
        shape=body.Shape
        assert shape.isValid()and len(shape.Solids)==1 and shape.Volume>0,body.Name
        for obj in body.Group:
            if obj.TypeId=='Sketcher::SketchObject':assert obj.FullyConstrained,obj.Name
        bb=_bounds(shape);shape.tessellate(.5)
        assert all(abs(a-b)<1e-7 for a,b in zip(_bounds(shape),bb))
        rows.append({'body':body.Name,'features':[o.TypeId for o in body.Group],'valid':True,'volume_mm3':shape.Volume,'exact_bounds_mm':bb})
    case=next(b for b in bodies if b.Name.endswith('Case'))
    assert len(case.Tip.Shape.Solids)==1
    # Real through-holes, not just a visual marking. Testbothholecentrelines.
    for x in(-3.25,3.25):
        assert not case.Shape.isInside(App.Vector(x,0,0),1e-7,True)
    assert all(abs(a-b)<1e-7 for a,b in zip(_bounds(case.Shape),[-6.4,-2.9,-1.5,6.4,2.9,5]))
    lever=next(b for b in bodies if b.Name.endswith('Lever'))
    tip=lever.Placement.multVec(App.Vector(12.8,0,.3))
    h=float(part.Parameters.BladeContactReferenceHeight)
    assert abs(tip.z-h)<1e-6,(tip,h)
    if abs(h-6.8)<1e-8:assert abs(tip.x-7.55)<1e-7
    return {'native_component_bodies':rows,'native_body_count':5,'actual_case_mounting_holes_open':True,
            'native_blade_tip_reference_mm':list(tip),'blade_reference_height_mm':h,'blade_root_is_derived_not_OEM':True,
            'published_terminal_function_X_mm':{'COM':-5.08,'NO':0,'NC':5.08},
            'published_OP_interval_mm':[5.3,8.3],'published_OT_minimum_mm':.55,'published_MD_maximum_mm':.5,
            'absolute_RP_published':False,'PT_published_for_hinge_lever':False,'physical_fit_and_received_OPRP_qualified':False}

def main():
    OUT.mkdir(parents=True,exist_ok=True);report={}
    for pose,suffix in(('operating_reference','OperatingReference'),('free_limit_reference','FreeLimitReference')):
        doc=App.newDocument('D2F'+suffix);part=build(doc,pose=pose)
        path=OUT/('D2F01L'+suffix+'.FCStd');doc.saveAs(str(path));report[pose]=validate(part)
        App.closeDocument(doc.Name);doc=App.openDocument(str(path))
        reopened=doc.getObject('DockLidCutoff');report[pose]['saved_readback']=validate(reopened)
        if pose=='operating_reference':
            edits=[]
            for height in(5.3,8.3,10,6.8):
                reopened.Parameters.BladeContactReferenceHeight=height;doc.recompute();checked=validate(reopened)
                edits.append({'input_reference_height_mm':height,'actual_tip_mm':checked['native_blade_tip_reference_mm']})
            report['native_parameter_edit_checks']=edits
        App.closeDocument(doc.Name)
        report[pose]['native_SHA256']=hashlib.sha256(path.read_bytes()).hexdigest()
    report['builder_SHA256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report['FreeCAD_version']=App.Version();report['datasheet_SHA256']=PDF_SHA256
    report['source_manifest_SHA256']=hashlib.sha256((OUT/'source-manifest.json').read_bytes()).hexdigest()
    (OUT/'native-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'native_body_count':5,'saved_operating_free_reference_readbacks':'pass','received_OP_RP_qualified':False}))

if __name__=='__main__':main()
