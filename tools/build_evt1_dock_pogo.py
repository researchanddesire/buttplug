"""Mill-Max 0906-2 external MCAD from the selected manufacturer's drawing.

Run/import within FreeCAD.  ``build(doc, compression_mm=.6)`` returns an
App::Part with two editable PartDesign bodies.  PCB seating face is local Z=0;
the contact points along +Z and the solder tail points along -Z.  Compression
changes the visible projection of the plunger; undisclosed internal spring,
clearances and stops are intentionally not invented.

This is a dimensional reconstruction, not manufacturer-supplied CAD. See
hardware/cad/evt1-assembly/vendor/pogo/source.json for dimensions and limits.
"""
import math


MPN = "0906-2-15-20-75-14-11-0"
INCH = 25.4
FREE_HEIGHT = .197 * INCH
MAX_STROKE = .055 * INCH
MID_STROKE = .0275 * INCH
BARREL_HEIGHT = .106 * INCH
TAIL_LENGTH = .069 * INCH
TIP_DIAMETER = .042 * INCH
UPPER_BARREL_DIAMETER = .059 * INCH
LOWER_BARREL_DIAMETER = .064 * INCH
FLANGE_DIAMETER = .072 * INCH
TAIL_DIAMETER = .017 * INCH
FLANGE_THICKNESS = .016 * INCH
LOWER_BARREL_LENGTH = .028 * INCH


def build(doc, compression_mm=.6, name="Pogo0906_2"):
    """Return selected-part assembly. Dimensions mm; native FreeCAD API only."""
    import FreeCAD as App
    import Part
    import Sketcher

    compression_mm = float(compression_mm)
    if not 0 <= compression_mm <= MAX_STROKE:
        raise ValueError("Compression exceeds selected 0906-2 nominal stroke")
    # Parameter holder must remain outside the App::Part. An App::Part depends
    # on contained bodies; a child expression referring back to that parent
    # creates a cyclic dependency in FreeCAD.
    parameters = doc.addObject("App::FeaturePython", name + "Parameters")
    parameters.Label = name + " / editable compression and drawing dimensions"
    part = doc.addObject("App::Part", name)
    part.Label = "Mill-Max " + MPN
    part.addProperty("App::PropertyLink", "Parameters", "Assembly")
    part.Parameters = parameters
    part.addProperty("App::PropertyString", "ManufacturerPartNumber", "Source")
    part.ManufacturerPartNumber = MPN
    part.addProperty("App::PropertyString", "ModelBasis", "Source")
    part.ModelBasis = "Manufacturer-dimensioned external reconstruction; internals omitted"
    part.addProperty("App::PropertyString", "SourceURL", "Source")
    part.SourceURL = "https://www.mill-max.com/sites/default/files/external/catalog/2021-02/023-028.pdf"
    for key, value in (("FreeHeight", FREE_HEIGHT), ("MaxStroke", MAX_STROKE),
                       ("MidStroke", MID_STROKE), ("BarrelHeight", BARREL_HEIGHT),
                       ("TailLength", TAIL_LENGTH), ("TipRadius", TIP_DIAMETER/2)):
        parameters.addProperty("App::PropertyLength", key, "Manufacturer dimensions")
        setattr(parameters, key, value)
        parameters.setEditorMode(key, 1)
        # The part exposes read-only mirrors for convenient inspection. Its
        # children depend directly on the independent parameter object.
        part.addProperty("App::PropertyLength", key, "Manufacturer dimensions")
        part.setExpression(key, parameters.Name + "." + key)
        part.setEditorMode(key, 1)
    parameters.addProperty("App::PropertyLength", "Compression", "Assembly")
    parameters.Compression = compression_mm
    part.addProperty("App::PropertyLength", "Compression", "Assembly")
    part.setExpression("Compression", parameters.Name + ".Compression")
    part.setEditorMode("Compression", 1)
    part.addProperty("App::PropertyString", "Datum", "Assembly")
    part.Datum = "PCB seating underside of flange Z=0; contact direction +Z"
    part.setEditorMode("Datum", 1)
    part.addProperty("App::PropertyString", "Limitations", "Source")
    part.Limitations = ("Tip/tail hemispheres inferred from rounded drawing, radii not separately "
                        "dimensioned. Undimensioned edge breaks omitted. External surfaces only; "
                        "no internal spring, force, material deformation or received-tolerance proof.")

    def body(suffix):
        b = doc.addObject("PartDesign::Body", name + suffix)
        part.addObject(b)
        if b.ViewObject is not None:
            b.ViewObject.ShapeColor = (.86, .65, .18)
            b.ViewObject.LineColor = (.22, .17, .05)
        return b

    def section(b, suffix, geometries, z=0):
        s = b.newObject("Sketcher::SketchObject", name + suffix)
        # Sketch X/Y are radial/axial. V_Axis becomes the global contact axis Z.
        s.Placement = App.Placement(App.Vector(0, 0, z),
                                    App.Rotation(App.Vector(1, 0, 0), 90))
        for geometry in geometries:
            i = s.addGeometry(geometry, False)
            s.addConstraint(Sketcher.Constraint("Block", i))
        doc.recompute()
        if not s.FullyConstrained:
            raise RuntimeError("Pogo external section is underconstrained")
        return s

    def revolve(b, suffix, s):
        f = b.newObject("PartDesign::Revolution", name + suffix)
        f.Profile = s
        f.ReferenceAxis = (s, ["V_Axis"])
        f.Angle = 360
        doc.recompute()
        if f.Shape.isNull() or not f.Shape.isValid() or len(f.Shape.Solids) != 1:
            raise RuntimeError("Pogo native revolution failed: " + f.Name)
        s.Visibility = False
        return f

    v = lambda r, z: App.Vector(r, z, 0)
    rt = TAIL_DIAMETER/2
    rf = FLANGE_DIAMETER/2
    rl = LOWER_BARREL_DIAMETER/2
    ru = UPPER_BARREL_DIAMETER/2
    q = math.sqrt(.5)
    fixed = body("ShellAndTail")
    # Nominal visible sleeve and tail. Internal cavities are not disclosed and
    # are not represented as fictitious mechanical or electrical geometry.
    points = [(rt, -TAIL_LENGTH+rt), (rt, 0), (rf, 0),
              (rf, FLANGE_THICKNESS), (rl, FLANGE_THICKNESS),
              (rl, FLANGE_THICKNESS+LOWER_BARREL_LENGTH),
              (ru, FLANGE_THICKNESS+LOWER_BARREL_LENGTH),
              (ru, BARREL_HEIGHT), (0, BARREL_HEIGHT), (0, -TAIL_LENGTH)]
    fixed_geometry = [Part.Arc(v(0, -TAIL_LENGTH),
                              v(rt*q, -TAIL_LENGTH+rt-rt*q),
                              v(rt, -TAIL_LENGTH+rt))]
    fixed_geometry += [Part.LineSegment(v(*a), v(*b))
                       for a, b in zip(points, points[1:])]
    fs = section(fixed, "ShellSection", fixed_geometry)
    revolve(fixed, "TurnedShell", fs)

    plunger = body("VisiblePlunger")
    r = TIP_DIAMETER/2
    stem = plunger.newObject("Sketcher::SketchObject", name + "PlungerDiameter")
    stem.Placement.Base = App.Vector(0, 0, BARREL_HEIGHT)
    stem.addGeometry(Part.Circle(App.Vector(), App.Vector(0, 0, 1), r), False)
    stem.addConstraint(Sketcher.Constraint("Coincident", 0, 3, -1, 1))
    stem.addConstraint(Sketcher.Constraint("Radius", 0, r))
    doc.recompute()
    assert stem.FullyConstrained
    projection = plunger.newObject("PartDesign::Pad", name + "PlungerProjection")
    projection.Profile = stem
    projection.Length = FREE_HEIGHT - compression_mm - BARREL_HEIGHT - r
    expression = "{p}.FreeHeight - {p}.Compression - {p}.BarrelHeight - {p}.TipRadius".format(p=parameters.Name)
    projection.setExpression("Length", expression)
    doc.recompute()
    stem.Visibility = False
    dome = section(plunger, "RoundedTipSection", [
        Part.LineSegment(v(0, 0), v(r, 0)),
        Part.Arc(v(r, 0), v(r*q, r*q), v(0, r)),
        Part.LineSegment(v(0, r), v(0, 0)),
    ], FREE_HEIGHT-compression_mm-r)
    dome.setExpression("Placement.Base.z", "{p}.FreeHeight - {p}.Compression - {p}.TipRadius".format(p=parameters.Name))
    doc.recompute()
    revolve(plunger, "RoundedTip", dome)
    projection.Visibility = False
    for b in (fixed, plunger):
        b.Tip.Visibility = True
        b.Visibility = True
        if b.Shape.isNull() or not b.Shape.isValid() or len(b.Shape.Solids) != 1:
            raise RuntimeError("Pogo selected-part body is invalid")
    doc.recompute()
    return part


def validate(part):
    """Check exact BRep extents, independent of GUI display triangulation."""
    bodies = [o for o in part.Group if o.TypeId == "PartDesign::Body"]
    assert len(bodies) == 2
    fixed, plunger = bodies
    for b in bodies:
        assert b.Shape.isValid() and len(b.Shape.Solids) == 1
    compression = part.Parameters.Compression.Value
    assert 0 <= compression <= MAX_STROKE
    tol = 1e-6
    # Shape.BoundBox can use the coarse triangulation cached by the GUI. Its
    # polygon vertices need not reach cylinder/sphere extrema. Disable both
    # triangulation and shape-tolerance enlargement for analytic BRep bounds.
    fb = fixed.Shape.optimalBoundingBox(False, False)
    pb = plunger.Shape.optimalBoundingBox(False, False)
    assert abs(fb.ZMin + TAIL_LENGTH) < tol
    assert abs(fb.ZMax - BARREL_HEIGHT) < tol
    assert abs(fb.XLength - FLANGE_DIAMETER) < tol
    assert abs(fb.YLength - FLANGE_DIAMETER) < tol
    assert abs(pb.ZMin - BARREL_HEIGHT) < tol
    assert abs(pb.ZMax - (FREE_HEIGHT-compression)) < tol
    assert abs(pb.XLength - TIP_DIAMETER) < tol
    assert abs(pb.YLength - TIP_DIAMETER) < tol
    assert fixed.Shape.common(plunger.Shape).Volume < 1e-9
    return {"mpn": MPN, "compression_mm": compression,
            "PCB_seating_Z_mm": 0, "contact_Z_mm": FREE_HEIGHT-compression,
            "tail_end_Z_mm": -TAIL_LENGTH,
            "bounds_method": "Shape.optimalBoundingBox(False, False); analytic BRep extrema",
            "native_bodies": 2, "body_validity": [b.Shape.isValid() for b in bodies],
            "nominal_max_stroke_mm": MAX_STROKE,
            "not_physical_qualification": True}
