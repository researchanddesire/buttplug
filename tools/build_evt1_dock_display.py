"""Selected LCD as editable native FreeCAD bodies, reconstructed from OEM STEP.

Call ``build(doc)`` from FreeCAD. The returned App::Part uses the centre of the
44 x 24 viewing area as XY origin and the front face as Z=0. FFC runs toward -Y.
The imported STEP remains the dimensional reference. Optional installed mode
poses the factory FFC with an unqualified native ribbon fold; no retainer is designed. Current data-sheet active area supersedes the 2018 STEP.
"""
from pathlib import Path
import hashlib
import json
import math

import FreeCAD as App
import Part
import Sketcher

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "hardware/cad/evt1-assembly/vendor/display"
MODEL = SOURCES / "NHD-C12864B2Z-RN.STEP"
SOURCE_SHA256 = "6fd8053ab7961345e04773c4d3113529df448efd5a68a5c6cf82d61366dba662"


def _rectangle(body, name, width, height, x, y, z):
    sketch = body.newObject("Sketcher::SketchObject", name)
    sketch.Placement.Base = App.Vector(x, y, z)
    points = ((0, 0), (width, 0), (width, height), (0, height))
    for i in range(4):
        a, b = points[i], points[(i + 1) % 4]
        sketch.addGeometry(Part.LineSegment(App.Vector(a[0], a[1], 0), App.Vector(b[0], b[1], 0)), False)
    for i in range(4):
        sketch.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % 4, 1))
    for i in (0, 2):
        sketch.addConstraint(Sketcher.Constraint("Horizontal", i))
    for i in (1, 3):
        sketch.addConstraint(Sketcher.Constraint("Vertical", i))
    sketch.addConstraint(Sketcher.Constraint("Coincident", 0, 1, -1, 1))
    for label, constraint in (("Width", Sketcher.Constraint("Distance", 0, width)),
                              ("Height", Sketcher.Constraint("Distance", 1, height))):
        n = sketch.addConstraint(constraint)
        sketch.renameConstraint(n, label)
    body.Document.recompute()
    assert sketch.FullyConstrained, sketch.Name
    return sketch


def _tail_profile(body, name, top_y, z):
    """OEM FFC has two 0.3-radius lower corners and square shoulders."""
    s = body.newObject("Sketcher::SketchObject", name)
    s.Placement.Base.z = z
    q = math.sqrt(0.5)
    v = lambda x, y: App.Vector(x, y, 0)
    edges = (
        Part.LineSegment(v(-7, top_y), v(7, top_y)),
        Part.LineSegment(v(7, top_y), v(7, -82.7)),
        Part.Arc(v(7, -82.7), v(6.7 + .3*q, -82.7 - .3*q), v(6.7, -83)),
        Part.LineSegment(v(6.7, -83), v(-6.7, -83)),
        Part.Arc(v(-6.7, -83), v(-6.7 - .3*q, -82.7 - .3*q), v(-7, -82.7)),
        Part.LineSegment(v(-7, -82.7), v(-7, top_y)),
    )
    for edge in edges:
        i = s.addGeometry(edge, False)
        s.addConstraint(Sketcher.Constraint("Block", i))
    body.Document.recompute()
    assert s.FullyConstrained, name
    return s


def _view_profile(body, name):
    """The OEM view-area sheet has four 1mm-radius corners."""
    s = body.newObject("Sketcher::SketchObject", name)
    s.Placement.Base = App.Vector(0, 4, 1.4)
    q = math.sqrt(.5)
    v = lambda x, y: App.Vector(x, y, 0)
    seq = [((-21, -12), (21, -12), None),
           ((21, -12), (22, -11), (21+q, -11-q)),
           ((22, -11), (22, 11), None),
           ((22, 11), (21, 12), (21+q, 11+q)),
           ((21, 12), (-21, 12), None),
           ((-21, 12), (-22, 11), (-21-q, 11+q)),
           ((-22, 11), (-22, -11), None),
           ((-22, -11), (-21, -12), (-21-q, -11-q))]
    for a, b, m in seq:
        i = s.addGeometry(Part.LineSegment(v(*a), v(*b)) if m is None else Part.Arc(v(*a), v(*m), v(*b)), False)
        s.addConstraint(Sketcher.Constraint("Block", i))
    body.Document.recompute()
    assert s.FullyConstrained, name
    return s


def _pad(body, name, sketch, length):
    doc = body.Document
    pad = body.newObject("PartDesign::Pad", name)
    pad.Profile = sketch
    pad.Length = length
    doc.recompute()
    assert pad.Shape.isValid() and len(pad.Shape.Solids) == 1, name
    sketch.Visibility = False
    for other in body.Group:
        if other != pad and hasattr(other, "Visibility"):
            other.Visibility = False
    pad.Visibility = True
    return pad


def _body(doc, part, name, label, color):
    b = doc.addObject("PartDesign::Body", name)
    part.addObject(b)
    b.Label = label
    if b.ViewObject:
        b.ViewObject.ShapeColor = color
    return b


def _bounds(shape):
    b = shape.optimalBoundingBox(False, False)
    return [b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax]


def _end_placement(sketch, part, z_offset):
    # Body source coordinates are normalised only once at the end of build().
    sketch.setExpression('Placement.Base.y', part.Name+'.FFCConnectorLocalTipY + 4 mm')
    sketch.setExpression('Placement.Base.z', part.Name+'.FFCConnectorLocalCenterZ + 1.6 mm'+('%+g mm' % z_offset))


def _rounded_positive_end(body, name, length):
    s = body.newObject('Sketcher::SketchObject', name)
    q = math.sqrt(.5)
    v = lambda x, y: App.Vector(x,y,0)
    edges = (
        Part.LineSegment(v(-7,-length),v(7,-length)),
        Part.LineSegment(v(7,-length),v(7,-.3)),
        Part.Arc(v(7,-.3),v(6.7+.3*q,-.3+.3*q),v(6.7,0)),
        Part.LineSegment(v(6.7,0),v(-6.7,0)),
        Part.Arc(v(-6.7,0),v(-6.7-.3*q,-.3+.3*q),v(-7,-.3)),
        Part.LineSegment(v(-7,-.3),v(-7,-length)),
    )
    for edge in edges:
        i=s.addGeometry(edge,False)
        s.addConstraint(Sketcher.Constraint('Block',i))
    body.Document.recompute()
    assert s.FullyConstrained
    return s


def _installed_ffc(doc, part, name, bend_radius_mm, straight_before_bend_mm):
    r=float(bend_radius_mm)
    a=float(straight_before_bend_mm)
    runout=65-a-math.pi*r
    assert r>.05 and a>0 and runout>5, 'FFC needs positive bend and 5mm flat stiffened connector end'
    settings=doc.addObject("App::FeaturePython",name+"FFCParameters")
    settings.Label="Installed FFC parameters / bend not qualified"
    settings.addProperty("App::PropertyLength","FFCFreeLength","Installed FFC")
    settings.FFCFreeLength=65
    settings.setEditorMode('FFCFreeLength',1)
    part.addProperty("App::PropertyLinkGlobal","FFCParameters","Installed FFC")
    part.FFCParameters=settings
    for key,value in (('FFCBendCentrelineRadius',r),('FFCLeadInLength',a),
                      ('FFCConnectorLocalTipY',-22+65-2*a-math.pi*r),
                      ('FFCConnectorLocalCenterZ',-.95-2*r),('FFCInnerBendRadius',r-.05)):
        settings.addProperty('App::PropertyLength',key,'Installed FFC')
        setattr(settings,key,value)
        part.addProperty('App::PropertyLength',key,'Installed FFC')
        part.setExpression(key,settings.Name+'.'+key)
    settings.setExpression('FFCConnectorLocalTipY','-22 mm + FFCFreeLength - 2 * FFCLeadInLength - pi * FFCBendCentrelineRadius')
    settings.setExpression('FFCConnectorLocalCenterZ','-0.95 mm - 2 * FFCBendCentrelineRadius')
    settings.setExpression('FFCInnerBendRadius','FFCBendCentrelineRadius - 0.05 mm')
    b=_body(doc,part,name+'InstalledFFC','Installed factory FFC / unqualified R%g fold' % r,(.66,.55,.30))
    spine=b.newObject('Sketcher::SketchObject',name+'FFCInstalledPath')
    spine.Label='65mm FFC centreline / editable tangent line-arc-line'
    spine.Placement=App.Placement(App.Vector(0,-18,.65),App.Rotation(App.Vector(1,1,1),120))
    v=lambda u,w:App.Vector(u,w,0)
    spine.addGeometry(Part.LineSegment(v(0,0),v(-a,0)),False)
    spine.addGeometry(Part.Arc(v(-a,0),v(-a-r,-r),v(-a,-2*r)),False)
    spine.addGeometry(Part.LineSegment(v(-a,-2*r),v(-a+runout,-2*r)),False)
    spine.addConstraint(Sketcher.Constraint('Coincident',0,1,-1,1))
    spine.addConstraint(Sketcher.Constraint('Tangent',0,2,1,1))
    spine.addConstraint(Sketcher.Constraint('Tangent',1,2,2,1))
    spine.addConstraint(Sketcher.Constraint('Horizontal',0))
    spine.addConstraint(Sketcher.Constraint('Horizontal',2))
    for key,con,expr in (
        ('BendRadius',Sketcher.Constraint('Radius',1,r),settings.Name+'.FFCBendCentrelineRadius'),
        ('LeadIn',Sketcher.Constraint('Distance',0,a),settings.Name+'.FFCLeadInLength'),
        ('ReturnRun',Sketcher.Constraint('Distance',2,runout),settings.Name+'.FFCFreeLength - '+settings.Name+'.FFCLeadInLength - pi * '+settings.Name+'.FFCBendCentrelineRadius')):
        i=spine.addConstraint(con)
        spine.renameConstraint(i,key)
        spine.setExpression('Constraints.'+key,expr)
    doc.recompute()
    assert spine.FullyConstrained, spine.Name
    section=_rectangle(b,name+'FFCInstalledSection',14,.1,-7,-.05,0)
    section.Placement=App.Placement(App.Vector(0,-18,.65),App.Rotation(App.Vector(1,0,0),90))
    # Put the rectangle's origin at(-7,-.05) in its own section plane.
    section.Placement.Base=App.Vector(-7,-18,.60)
    pipe=b.newObject('PartDesign::AdditivePipe',name+'FFCInstalledRibbon')
    pipe.Profile=section
    pipe.Spine=(spine,[])
    pipe.Mode='Frenet'
    doc.recompute()
    assert pipe.Shape.isValid() and len(pipe.Shape.Solids)==1, pipe.getStatusString()
    assert abs(spine.Shape.Length-65)<1e-6
    assert abs(pipe.Shape.Volume-91)<1e-5,(pipe.Shape.Volume,_bounds(pipe.Shape))
    spine.Visibility=False
    section.Visibility=False
    # Trim only the two source 0.3mm end corners from the actual ribbon.
    trim=b.newObject('Sketcher::SketchObject',name+'FFCEndCornerTrim')
    q=math.sqrt(.5)
    for sign in (-1,1):
        pts=(v(sign*7,-.3),v(sign*7,0),v(sign*6.7,0))
        edges=(Part.LineSegment(pts[0],pts[1]),Part.LineSegment(pts[1],pts[2]),
               Part.Arc(pts[2],v(sign*(6.7+.3*q),-.3+.3*q),pts[0]))
        for edge in edges:
            i=trim.addGeometry(edge,False)
            trim.addConstraint(Sketcher.Constraint('Block',i))
    _end_placement(trim,settings,.05)
    cut=b.newObject('PartDesign::Pocket',name+'FFCRoundedEnd')
    cut.Profile=trim
    cut.Length=.1001
    doc.recompute()
    assert cut.Shape.isValid() and len(cut.Shape.Solids)==1
    assert abs(cut.Shape.Volume-(91-.1*2*(.3**2-math.pi*.3**2/4)))<1e-5,cut.Shape.Volume
    trim.Visibility=False
    pipe.Visibility=False
    s=_rounded_positive_end(b,name+'FFCInstalledStiffenerProfile',5)
    _end_placement(s,settings,.05)
    _pad(b,name+'FFCInstalledStiffenerPad',s,.1)
    s=b.newObject('Sketcher::SketchObject',name+'FFCInstalledContactsProfile')
    for pin in range(27):
        x=-6.5+pin*.5
        pts=((x-.15,-3),(x+.15,-3),(x+.15,0),(x-.15,0))
        for j in range(4):
            p0,p1=pts[j],pts[(j+1)%4]
            i=s.addGeometry(Part.LineSegment(v(*p0),v(*p1)),False)
            s.addConstraint(Sketcher.Constraint('Block',i))
    _end_placement(s,settings,-.15)
    doc.recompute()
    assert s.FullyConstrained
    _pad(b,name+'FFCInstalledContactsPad',s,.1)
    assert abs(b.Shape.Volume-100.422274333882)<1e-5,b.Shape.Volume
    doc.recompute()
    return b,{
        'scope':'Nominal installed FFC candidate; bend radius and installed strain/connector remain unqualified',
        'native_path':spine.Name,'native_sweep':pipe.Name,
        'centreline_length_mm':spine.Shape.Length,'centreline_radius_mm':r,
        'inner_radius_mm':r-.05,'lead_in_mm':a,'return_run_mm':runout,
        'local_entry_mm':[0,-22,-.95],
        'local_connector_tip_mm':[0,part.FFCConnectorLocalTipY.Value,part.FFCConnectorLocalCenterZ.Value],
        'connector_entry_direction':[0,1,0],'connector_contact_face_normal':[0,0,-1],
        'finished_contact_tail_thickness_mm':.3,'flat_stiffened_end_length_mm':5,
        'contact_land_count':27,'body_valid':b.Shape.isValid(),'body_solids':len(b.Shape.Solids),
        'solid_volume_mm3':b.Shape.Volume,'radius_qualified':False,'installed_fit_qualified':False}


def build(doc, name="DockLCD", current_active_area=True, ffc_pose="flat", bend_radius_mm=3.0, straight_before_bend_mm=4.0):
    """Return one purchased LCD App::Part with editable native component bodies.

    The OEM five solids are graphical/material lumps that overlap internally.
    They are one purchased component, not five independent mechanical mates.
    With ``current_active_area=False`` the native bodies reproduce the 2018
    factory STEP; True updates the optical marking to the current drawing.
    ffc_pose="installed" adds a sixth body with a native constant-length sweep.
    """
    assert ffc_pose in ("flat", "installed")
    actual_sha = hashlib.sha256(MODEL.read_bytes()).hexdigest()
    assert actual_sha == SOURCE_SHA256, "Manufacturer source changed; review conversion"
    source = Part.Shape()
    source.read(str(MODEL))
    assert source.isValid() and len(source.Solids) == 5
    part = doc.addObject("App::Part", name)
    part.Label = "Newhaven NHD-C12864B2Z-RN-FBW / native OEM geometry"
    part.addProperty("App::PropertyString", "ManufacturerPartNumber", "Source")
    part.ManufacturerPartNumber = "NHD-C12864B2Z-RN-FBW"
    part.addProperty("App::PropertyString", "SourceSHA256", "Source")
    part.SourceSHA256 = actual_sha
    part.addProperty("App::PropertyString", "DatasheetURL", "Source")
    part.DatasheetURL = "https://newhavendisplay.com/content/specs/NHD-C12864B2Z-RN-FBW.pdf"
    part.addProperty("App::PropertyString", "Limitations", "Source")
    part.Limitations = "Factory flat FFC; installed fold/strain relief not designed. OEM visual layers overlap. Current allowed thickness 2.1mm exceeds 2018 STEP 1.8mm; seat must reserve current maximum."
    part.addProperty("App::PropertyLength", "CurrentThicknessMaximum", "Drawing")
    part.CurrentThicknessMaximum = 2.1
    part.addProperty("App::PropertyLength", "FFCFreeLength", "Drawing")
    part.FFCFreeLength = 65
    part.addProperty("App::PropertyLength", "FFCContactPitch", "Drawing")
    part.FFCContactPitch = .5
    bodies = []
    b = _body(doc, part, name+"FrontSheet", "OEM front glass sheet", (.67, .75, .69))
    _pad(b, name+"FrontSheetPad", _rectangle(b, name+"FrontSheetProfile", 48, 29, -24, -11, .7), .7)
    bodies.append(b)
    b = _body(doc, part, name+"Border", "OEM border graphic solid", (.045, .05, .045))
    _pad(b, name+"BorderPad", _rectangle(b, name+"BorderProfile", 47, 28, -23.5, -10.5, -.2), 1.8)
    bodies.append(b)
    b = _body(doc, part, name+"ViewSheet", "OEM 44x24 viewing area sheet", (.56, .63, .53))
    _pad(b, name+"ViewSheetPad", _view_profile(b, name+"ViewSheetProfile"), .2)
    bodies.append(b)
    b = _body(doc, part, name+"ActiveArea", "Active area / current 39.64x19.8" if current_active_area else "OEM 2018 active area / 39.64x19.6", (.43, .52, .39))
    _pad(b, name+"ActiveAreaPad", _rectangle(b, name+"ActiveAreaProfile", 39.64, 19.8 if current_active_area else 19.6, -19.82, -5.9 if current_active_area else -5.7, 1.4), .2)
    bodies.append(b)
    b = _body(doc, part, name+"GlassFFC", "OEM rear glass / FFC routed separately" if ffc_pose == "installed" else "OEM rear glass, factory FFC and 27 contacts", (.66, .55, .30))
    _pad(b, name+"RearGlassPad", _rectangle(b, name+"RearGlassProfile", 48, 36, -24, -18, 0), .7)
    if ffc_pose == "flat":
        _pad(b, name+"FFCTailPad", _tail_profile(b, name+"FFCTailProfile", -18, .6), .1)
        _pad(b, name+"FFCStiffenerPad", _tail_profile(b, name+"FFCStiffenerProfile", -78, .5), .1)
        s = b.newObject("Sketcher::SketchObject", name+"FFCContactsProfile")
        s.Placement.Base.z = .7
        for pin in range(27):
            x = -6.5 + pin*.5
            pts = ((x-.15, -83), (x+.15, -83), (x+.15, -80), (x-.15, -80))
            for j in range(4):
                a, c = pts[j], pts[(j+1)%4]
                i = s.addGeometry(Part.LineSegment(App.Vector(a[0], a[1], 0), App.Vector(c[0], c[1], 0)), False)
                s.addConstraint(Sketcher.Constraint("Block", i))
        doc.recompute()
        assert s.FullyConstrained
        _pad(b, name+"FFCContactsPad", s, .1)
    bodies.append(b)
    installed_check = None
    if ffc_pose == "installed":
        b, installed_check = _installed_ffc(doc, part, name, bend_radius_mm, straight_before_bend_mm)
        bodies.append(b)
        part.addProperty("App::PropertyString", "InstalledFFCChecks", "Installed FFC")
        part.InstalledFFCChecks = json.dumps(installed_check, separators=(",", ":"))
        part.Limitations = "Installed FFC has candidate bend only; bend radius, strain relief and received fit unqualified. OEM visual layers overlap. Current2.1mm thickness maximum controls seat."
    part.addProperty("App::PropertyString", "FFCPose", "Source")
    part.FFCPose = ffc_pose
    doc.recompute()
    checks = []
    for i, (body, oem) in enumerate(zip(bodies, source.Solids)):
        if i == 4 and ffc_pose == "installed":
            oem = oem.common(Part.makeBox(48, 36, .7, App.Vector(-24, -18, 0)))
        overlap = body.Shape.common(oem).Volume
        difference = body.Shape.Volume + oem.Volume - 2*overlap
        changed_current_optical_marking = i == 3 and current_active_area
        assert changed_current_optical_marking or abs(difference) < 1e-6, (body.Name, difference)
        checks.append({"body":body.Name,"OEM_solid_index":i,"native_valid":body.Shape.isValid(),"native_solid_count":len(body.Shape.Solids),"symmetric_difference_mm3":difference,"current_optical_marking_update":changed_current_optical_marking})
        if body.ViewObject:
            body.Tip.ViewObject.ShapeColor = body.ViewObject.ShapeColor
            body.Tip.Visibility = True
    part.addProperty("App::PropertyString", "OEMConversionChecks", "Source")
    part.OEMConversionChecks = json.dumps(checks, separators=(",", ":"))
    # Factory coordinates: viewing area centre(0,4), front1.6. Canonical datum
    # allows an assembly link at its window centre without hidden offsets.
    for body in bodies:
        if body.ViewObject:
            body.Tip.ViewObject.ShapeColor = body.ViewObject.ShapeColor
            body.Tip.Visibility = True
        body.Placement = App.Placement(App.Vector(0, -4, -1.6), App.Rotation())
    doc.recompute()
    if ffc_pose == "installed":
        part.InstalledFFCChecks = json.dumps(validate_installed(part), separators=(",", ":"))
    return part


def validate_installed(part):
    """Recheck the current native geometry after a saved parameter edit."""
    assert part.FFCPose == 'installed'
    doc=part.Document
    settings=part.FFCParameters
    b=next(o for o in part.Group if o.TypeId=='PartDesign::Body' and 'InstalledFFC' in o.Name)
    path=next(o for o in b.Group if o.TypeId=='Sketcher::SketchObject' and 'FFCInstalledPath' in o.Name)
    radius=settings.FFCBendCentrelineRadius.Value
    lead=settings.FFCLeadInLength.Value
    total=settings.FFCFreeLength.Value
    runout=total-lead-math.pi*radius
    assert abs(total-65)<1e-9
    assert radius>.05 and lead>0 and runout>=5
    assert path.FullyConstrained and abs(path.Shape.Length-total)<1e-6
    assert b.Shape.isValid() and len(b.Shape.Solids)==1
    assert abs(b.Shape.Volume-100.422274333882)<1e-5
    b.Shape.check(True)
    bb=b.Shape.optimalBoundingBox(False, False)
    end_y=-22+total-2*lead-math.pi*radius
    end_z=-.95-2*radius
    expected=[-7,-22-lead-radius-.05,end_z-.15,7,end_y,-.9]
    assert all(abs(a-c)<1e-6 for a,c in zip(_bounds(b.Shape),expected)),(_bounds(b.Shape),expected)
    return {'scope':'Nominal installed FFC candidate; bend, strain relief, connector and fit require qualification',
            'native_body':b.Name,'native_path':path.Name,'centreline_length_mm':path.Shape.Length,
            'centreline_radius_mm':radius,'inner_radius_mm':radius-.05,
            'lead_in_mm':lead,'return_run_mm':runout,
            'local_entry_mm':[0,-22,-.95],'local_connector_tip_mm':[0,end_y,end_z],
            'connector_entry_direction':[0,1,0],'connector_contact_face_normal':[0,0,-1],
            'finished_contact_tail_thickness_mm':.3,'flat_stiffened_end_length_mm':5,
            'contact_land_count':27,'body_valid':True,'body_solids':1,
            'BOP_check_passed':True,'solid_volume_mm3':b.Shape.Volume,
            'local_bounds_mm':_bounds(b.Shape),'radius_qualified':False,'installed_fit_qualified':False}
