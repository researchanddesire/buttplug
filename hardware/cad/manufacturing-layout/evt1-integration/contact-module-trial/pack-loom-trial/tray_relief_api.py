"""Rear-open notches in the old reference-pack ribs; no source mutation."""
import math
import FreeCAD as A
import Part, Sketcher
V=A.Vector
GEOMETRY={'X_mm':[29.,32.],'Z_centres_mm':[-9.3,9.3],'Z_width_mm':2.3,
          'corner_radius_mm':.65,'tool_start_Y_mm':-14.6,'pocket_depth_mm':1.2,
          'new_rear_rib_face_Y_mm':-13.4,'original_rib_rear_Y_mm':-14.5,
          'original_rib_front_Y_mm':-9.6,'original_rib_rear_width_mm':.62}

def ribs():
    result=[]
    for z in (-9.2,9.2):
        a=Part.makePolygon([V(12,-9.6,z-.4),V(40.5,-9.6,z-.4),V(40.5,-9.6,z+.4),V(12,-9.6,z+.4),V(12,-9.6,z-.4)])
        b=Part.makePolygon([V(12.09,-14.5,z-.31),V(40.41,-14.5,z-.31),V(40.41,-14.5,z+.31),V(12.09,-14.5,z+.31),V(12.09,-14.5,z-.31)])
        result.append(Part.makeLoft([a,b],True,False))
    return result

def rounded_profile(sk,x0,y0,x1,y1,r):
    k=1-math.sqrt(.5)
    def line(a,b):return Part.LineSegment(V(*a,0),V(*b,0))
    def arc(a,b,d):return Part.Arc(V(*a,0),V(*b,0),V(*d,0))
    gg=[line((x0+r,y0),(x1-r,y0)),arc((x1-r,y0),(x1-r*k,y0+r*k),(x1,y0+r)),
        line((x1,y0+r),(x1,y1-r)),arc((x1,y1-r),(x1-r*k,y1-r*k),(x1-r,y1)),
        line((x1-r,y1),(x0+r,y1)),arc((x0+r,y1),(x0+r*k,y1-r*k),(x0,y1-r)),
        line((x0,y1-r),(x0,y0+r)),arc((x0,y0+r),(x0+r*k,y0+r*k),(x0+r,y0))]
    for g in gg:
        i=sk.addGeometry(g,False);sk.addConstraint(Sketcher.Constraint('Block',i))

def apply_tray_wire_reliefs(body,prefix='NTCReturnCrossing'):
    """Body has the exact original Tray Tip; add one editable native Pocket.

    Global product frame. Draw is +Y from the open rear cavity. No save,
    parameter change, or product-document lookup occurs in this function.
    """
    sk=body.newObject('Sketcher::SketchObject',prefix+'Profile')
    sk.Placement=A.Placement(V(0,GEOMETRY['tool_start_Y_mm'],0),A.Rotation(V(1,0,0),90))
    for z in GEOMETRY['Z_centres_mm']:
        rounded_profile(sk,29,z-1.15,32,z+1.15,.65)
    body.Document.recompute();assert sk.FullyConstrained
    f=body.newObject('PartDesign::Pocket',prefix+'Reliefs');f.Profile=sk;f.Length=1.2
    body.Document.recompute();sk.Visibility=False
    assert f.Shape.isValid()and len(f.Shape.Solids)==1
    return {'pocket':f,'profile':sk,'dimensions':GEOMETRY.copy()}
