"""Selected B3FS-1002P tactile switch as native component with actual source CAD.

Call build(doc,name='DockSwitch'). Origin is the PCB seating plane beneath the
centre of the released actuator; +Z is outward. The native component retains
four gull-wing terminals, detailed stepped case, lid and actual Ø3 plunger.
KiCad source geometry is attributed and checked against the manufacturer drawing.
"""
from pathlib import Path
import hashlib
import json

import FreeCAD as App
import Part
import Sketcher

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'hardware/cad/evt1-assembly/vendor/buttons/SW_SPST_Omron_B3FS-100xP.step'
SOURCE_SHA256 = 'b329c059bd0fc4def23f1dbf3a8ab42d79451e42368166bfa454033e4741fdc1'


def _bounds(shape):
    b = shape.optimalBoundingBox(False, False)
    return [b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]


def validate(part):
    body = next(o for o in part.Group if o.TypeId == 'PartDesign::Body')
    shape = body.Shape
    expected = [-4,-3.15,0,4,3.15,3.1]
    assert shape.isValid() and len(shape.Solids) == 1
    assert all(abs(a-b)<1e-6 for a,b in zip(_bounds(shape),expected))
    # Positive metal volume must exist at each of the four real gull-wing feet.
    feet=[]
    for x in (-3.9,3.3):
        for y in (-2.5,2.0):
            clip = Part.makeBox(.6,.5,.25,App.Vector(x,y,0))
            volume = shape.common(clip).Volume
            assert volume>1e-4, (x,y,volume)
            feet.append({'clip_base_mm':[x,y,0],'actual_source_material_mm3':volume})
    return {'part':part.Name,'selected_MPN':part.ManufacturerPartNumber,
            'native_valid':True,'native_solid_count':len(shape.Solids),
            'source_face_count':len(shape.Faces),'nominal_bounds_mm':_bounds(shape),
            'four_terminal_material_checks':feet,
            'free_actuator_face_Z_mm':3.1,'actuation_face_nominal_Z_mm':2.85,
            'pretravel_is_not_allowed_total_stroke':True,'physical_fit_qualified':False}


def build(doc,name='DockSwitch'):
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_SHA256
    source = Part.Shape()
    source.read(str(SOURCE))
    part=doc.addObject('App::Part',name)
    part.Label='B3FS-1002P / selected 1.47N tactile switch'
    for label,value in (
        ('ManufacturerPartNumber','B3FS-1002P'),
        ('SourceSHA256',SOURCE_SHA256),
        ('GeometrySource','Official KiCad library SW_SPST_Omron_B3FS-100xP; manufacturer drawing checked; not OEM CAD'),
        ('ManufacturerDrawingURL','https://omronfs.omron.com/en_US/ecb/products/pdf/en-b3fs.pdf'),
        ('Limitations','Released geometry only; actuator internals and allowed total overtravel are not published/modelled. Supplier/received switch and cap tolerance validation required. IP00 dry chamber.')):
        part.addProperty('App::PropertyString',label,'Source')
        setattr(part,label,value)
    for label,value in (('FreeHeight',3.1),('FreeHeightTolerance',.2),
                        ('PlungerDiameter',3),('PretravelNominal',.25),
                        ('PretravelMinimum',.15),('PretravelMaximum',.45),
                        ('NominalClickFaceZ',2.85),('MinimumClickFaceZ',2.45),
                        ('MaximumClickFaceZ',3.15)):
        part.addProperty('App::PropertyLength',label,'Actuation')
        setattr(part,label,value)
    for label,value in (('OperatingForceNominalN',1.47),('OperatingForceToleranceN',.49),('ReleaseForceMinimumN',.49)):
        part.addProperty('App::PropertyFloat',label,'Actuation')
        setattr(part,label,value)
    body=doc.addObject('PartDesign::Body',name+'Body')
    part.addObject(body)
    body.Label='Detailed selected switch geometry / KiCad source'
    solid=body.newObject('PartDesign::Feature',name+'SourceGeometry')
    solid.Label='Source case, gull-wing terminals and released actuator'
    solid.Shape=source
    body.Tip=solid
    if solid.ViewObject:
        colours=[]
        for f in solid.Shape.Faces:
            b=f.BoundBox
            plunger=b.ZMin>=2.59999 and b.ZMax>2.60001 and b.XMin>=-1.50001 and b.XMax<=1.50001 and b.YMin>=-1.50001 and b.YMax<=1.50001
            metal=b.ZMin>2.1 or b.XMin<-3.01 or b.XMax>3.01
            colours.append((.93,.91,.80) if plunger else ((.65,.67,.68) if metal else (.12,.13,.13)))
        solid.ViewObject.DiffuseColor=colours
        body.ViewObject.ShapeColor=(.25,.26,.26)
    datum=doc.addObject('Sketcher::SketchObject',name+'ActuatorFaceDatum')
    part.addObject(datum)
    datum.Label='Released actuator contact face / Ø3 at Z3.1'
    datum.Placement.Base=App.Vector(0,0,3.1)
    datum.addGeometry(Part.Circle(App.Vector(0,0,0),App.Vector(0,0,1),1.5),False)
    datum.addConstraint(Sketcher.Constraint('Coincident',0,3,-1,1))
    i=datum.addConstraint(Sketcher.Constraint('Radius',0,1.5))
    datum.renameConstraint(i,'PlungerRadius')
    doc.recompute()
    assert datum.FullyConstrained
    datum.Visibility=False
    body.Visibility=True
    solid.Visibility=True
    result=validate(part)
    part.addProperty('App::PropertyString','GeometryChecks','Source')
    part.GeometryChecks=json.dumps(result,separators=(',',':'))
    return part
