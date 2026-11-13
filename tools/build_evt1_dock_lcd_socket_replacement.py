"""JST public-drawing datums and a real equal-shim received-fit fixture.

The public catalog has no loaded contact section. Socket geometry is therefore
native dimensioned sketches, NOT a fictitious housing/cavity or fit-test solid.
The separate fixture has editable Pads/Pockets and four actual annular shims.
Run with FreeCAD Python or call build/build_fixture from the GUI.
"""
from pathlib import Path
import argparse,hashlib,json,math
import FreeCAD as App
import Part,Sketcher
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/cad/evt1-assembly/vendor/lcd-socket-replacement'
RETENTION=ROOT/'hardware/cad/evt1-assembly/lcd-retention-trial/LCDRetentionTrial.FCStd'
RETENTION_SHA='324c1bf695388c44b33b2b04952df54d929efc825d6596fece1c9ee4e81cffe6'
MOUNTS=[(-30,65),(30,65),(-32,115),(32,105)]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def prop(o,t,n,v):o.addProperty(t,n,'Trial');setattr(o,n,v)
def wire(sk,points,closed=True,construction=False):
    pairs=list(zip(points,points[1:]+points[:1]if closed else points[1:]))
    for a,b in pairs:
        i=sk.addGeometry(Part.LineSegment(App.Vector(*a,0),App.Vector(*b,0)),construction)
        sk.addConstraint(Sketcher.Constraint('Block',i))
def rect(sk,x1,y1,x2,y2,construction=False):wire(sk,[(x1,y1),(x2,y1),(x2,y2),(x1,y2)],construction=construction)
def circles(sk,xy,r):
    for x,y in xy:
        i=sk.addGeometry(Part.Circle(App.Vector(x,y,0),App.Vector(0,0,1),r),False)
        sk.addConstraint(Sketcher.Constraint('DistanceX',i,3,x))
        sk.addConstraint(Sketcher.Constraint('DistanceY',i,3,y))
        sk.addConstraint(Sketcher.Constraint('Radius',i,r))
def sketch(doc,owner,name,z=0):
    s=doc.addObject('Sketcher::SketchObject',name);owner.addObject(s)
    s.Placement.Base.z=z;return s
def pad(body,s,name,length,reverse=False):
    d=body.Document;d.recompute();assert s.FullyConstrained
    p=body.newObject('PartDesign::Pad',name);p.Profile=s;p.Length=length;p.Reversed=reverse
    body.Tip=p;d.recompute();assert p.Shape.isValid()and len(p.Shape.Solids)==1,name
    if App.GuiUp:s.Visibility=False
    return p
def pocket(body,s,name,length):
    d=body.Document;d.recompute();assert s.FullyConstrained
    p=body.newObject('PartDesign::Pocket',name);p.Profile=s;p.Length=length
    body.Tip=p;d.recompute();assert p.Shape.isValid()and len(p.Shape.Solids)==1,name
    if App.GuiUp:s.Visibility=False
    return p

def build(doc,name='JST27FLZDrawingDatums'):
    """Native primary-drawing reconstruction; intentionally no socket solids.

    Frame: native KiCad x/y, board F=0; origin signal-row centre; mouth +Y.
    Dock frame +x=+X,+y=−Y,+z=+Z at J302(0,114,F).
    """
    p=doc.addObject('App::Part',name);p.Label='JST 27FLZ-RSM2-TB / documented datums / loaded geometry unknown'
    prop(p,'App::PropertyString','MPN','27FLZ-RSM2-TB')
    prop(p,'App::PropertyString','PrimarySource','https://www.jst.com/wp-content/uploads/2025/06/eFLZ.pdf pp2–3')
    prop(p,'App::PropertyBool','LoadedGeometryKnown',False)
    prop(p,'App::PropertyBool','PhysicalFitQualified',False)
    prop(p,'App::PropertyString','Scope','Dimensioned mounting pattern and external projection datums only. Not a package fit proxy. No invented contact plane, cable cavity, terminal shape or internal guides.')
    prop(p,'App::PropertyString','NumberingEvidence','Marked-end convention: pin1 at -X, mouth+Y; catalog triangle has no explicit numeral1 legend. Verify received terminal continuity before power.')
    for n,v in [('ContactPitch',.5),('OverallWidth',19.4),('ClosedDepth',4.6),('OpenDepthReference',6.4),('MountingHeight',2),('FPCThicknessNominal',.3),('FPCThicknessTolerance',.03)]:prop(p,'App::PropertyLength',n,v)
    lands=sketch(doc,p,name+'RecommendedMountingPattern')
    for i in range(27):rect(lands,-6.5+.5*i-.175,-.55,-6.5+.5*i+.175,.55)
    for x in (-8.75,8.75):rect(lands,x-1.05,.2,x+1.05,2.3)
    prop(lands,'App::PropertyString','Evidence','Catalog p2 left column, mounting-surface view. Signal .35×1.1; mounting2.1×2.1. Pattern is reference, not guaranteed manufacturing tolerance.')
    plan=sketch(doc,p,name+'ClosedAndOpenProjectionDatums')
    # Construction dimensions only: these deliberately do not create a
    # filled rectangle that could be mistaken for an actual housing model.
    wire(plan,[(-9.7,.4),(-9.7,5)],False,True)
    wire(plan,[(9.7,.4),(9.7,5)],False,True)
    wire(plan,[(-9.7,.4),(9.7,.4)],False,True)
    wire(plan,[(-9.7,5),(9.7,5)],False,True)
    wire(plan,[(-9.7,6.8),(9.7,6.8)],False,True)
    prop(plan,'App::PropertyString','Evidence','Catalog p3 B19.4/closed4.6/open(6.4). RearY+.4 derives from p2 parenthesized(.15) outline datum, nominal reference only; no guaranteed insertion stop.')
    elevation=sketch(doc,p,name+'SideHeightAndEntryDatums')
    elevation.Placement=App.Placement(App.Vector(0,.4,0),App.Rotation(App.Vector(1,0,0),90))
    wire(elevation,[(-9.7,0),(-9.7,2)],False,True)
    wire(elevation,[(9.7,0),(9.7,2)],False,True)
    wire(elevation,[(-9.7,2),(9.7,2)],False,True)
    prop(elevation,'App::PropertyString','Evidence','Catalog p3 mounting height2.0. Cable/contact height is NOT dimensioned; none is modeled.')
    doc.recompute()
    assert all(s.FullyConstrained for s in [lands,plan,elevation])
    return p

def build_fixture(doc,name='JSTSocketReceivedFit',stack_mm=1.0,include_lcd_retention=True):
    """Open roof fixture, matching actual four seats; measurement interval only.

    Hardware uses the parent's M2x6 underside access/tapped plastic trial scheme.
    The fixture does not select a loaded contact height or clamp the LCD glass.
    """
    assert .10<=stack_mm<=1.50
    p=doc.addObject('App::Part',name)
    params=doc.addObject('App::FeaturePython',name+'Parameters')
    for n,v in [('Stack',stack_mm),('RoofSeatZ',61.5),('PCBFrontZ',61.5-stack_mm),('LCDFrontDatumZ',68.8),('FixedCopperFaceZ',61.7)]:prop(params,'App::PropertyLength',n,v)
    params.setExpression('PCBFrontZ',params.Name+'.RoofSeatZ - '+params.Name+'.Stack')
    prop(p,'App::PropertyLinkGlobal','Parameters',params)
    prop(p,'App::PropertyBool','RangePhysicallyQualified',False)
    prop(p,'App::PropertyString','Use','Measurement fixture only: use approved LCD retention coupon at frontZ68.8; no bare glass/COG clamp. M2 pilots/taps/received screw access need inert trial.')
    assert sha(RETENTION)==RETENTION_SHA
    source=App.openDocument(str(RETENTION))
    prop(p,'App::PropertyString','LCDRetentionSourceSHA256',RETENTION_SHA)
    body=doc.addObject('PartDesign::Body',name+'RoofFrame');p.addObject(body)
    base=body.newObject('PartDesign::Feature',name+'SourceLCDRoofCoupon')
    base.Shape=source.RoofCoupon.Shape.copy()
    prop(base,'App::PropertyString','ImmutableSource','LCDRetentionTrial.FCStd:RoofCoupon; frozen source copied exactly, then native additive/Pocket trial features')
    body.Tip=base
    # Extend only the existing coupon rear to support the two rear UI holes.
    s=sketch(doc,body,name+'RearSeatRoofExtension',64);rect(s,-44,112,44,124)
    pad(body,s,name+'RearSeatRoofExtensionPad',3.4)
    s=sketch(doc,body,name+'FourSeatProfiles',64);circles(s,MOUNTS,2.6)
    pad(body,s,name+'FourDownwardSeats',2.5,True)
    s=sketch(doc,body,name+'FourM2PilotProfiles',67.4);circles(s,MOUNTS,.8)
    pocket(body,s,name+'FourM2TapPilots',5.9)
    if include_lcd_retention:
        assert doc.FileName,'Save the owning fixture document before adding external source links'
        names=['BezelCoupon','SelectedLCD']+['LCDRetention'+side+suffix for side in ['Left','Right']for suffix in ['Carrier','RegisteredPETStack','FrontPORON','RearPORON']]+['ExistingBezelM2x6_'+str(i)for i in range(4)]
        for n in names:
            link=doc.addObject('App::Link',name+'Actual'+n);link.setLink(source.getObject(n));p.addObject(link)
    # Separate real equal shims; OD5.2/ID2.3. They carry no force/creep claim.
    for i,(x,y)in enumerate(MOUNTS):
        b=doc.addObject('PartDesign::Body',name+'Shim'+str(i));p.addObject(b)
        s=sketch(doc,b,name+'ShimProfile'+str(i),61.5-stack_mm)
        circles(s,[(x,y)],2.6);circles(s,[(x,y)],1.15)
        pp=pad(b,s,name+'ShimPad'+str(i),stack_mm)
        s.setExpression('Placement.Base.z',params.Name+'.PCBFrontZ')
        pp.setExpression('Length',params.Name+'.Stack')
    doc.recompute()
    if App.GuiUp:
        for b in p.Group:
            if b.TypeId=='PartDesign::Body':b.ViewObject.ShapeColor=(.82,.83,.75)
    return p

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stack',type=float,default=1);a=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    d=App.newDocument('JSTSocketReceivedFit');path=OUT/'JSTSocketReceivedFit.FCStd';d.saveAs(str(path))
    datums=build(d);fixture=build_fixture(d,stack_mm=a.stack)
    d.recompute();d.save()
    rows=[]
    for b in fixture.Group:
        if b.TypeId!='PartDesign::Body':continue
        shape=b.Shape;assert shape.isValid()and len(shape.Solids)==1
        assert not shape.check(True),b.Name
        bb=shape.optimalBoundingBox(False,False)
        rows.append({'name':b.Name,'volume_mm3':shape.Volume,'bounds':[bb.XMin,bb.YMin,bb.ZMin,bb.XMax,bb.YMax,bb.ZMax]})
    assert len(rows)==5 and all(s.FullyConstrained for s in d.Objects if s.TypeId=='Sketcher::SketchObject')
    links=[o for o in fixture.Group if o.TypeId=='App::Link'];assert len(links)==14
    for o in links:assert o.LinkedObject and o.Shape.isValid()and len(o.Shape.Solids)>0,o.Name
    source_roof=next(o for o in d.Objects if o.Name.endswith('SourceLCDRoofCoupon')).Shape
    additions=fixture.Group[0].Shape.cut(source_roof) if fixture.Group[0].TypeId=='PartDesign::Body' else d.getObject('JSTSocketReceivedFitRoofFrame').Shape.cut(source_roof)
    added_checks=[]
    for o in links:
        vol=additions.common(o.Shape).Volume
        assert vol<1e-7,(o.Name,'new fixture additions intersect retained LCD coupon',vol)
        added_checks.append({'link':o.Name,'added_fixture_common_mm3':vol})
    params=fixture.Parameters
    for thickness in (.1,1.5,a.stack):
        params.Stack=thickness;d.recompute()
        for i in range(4):
            b=d.getObject('JSTSocketReceivedFitShim'+str(i));bb=b.Shape.optimalBoundingBox(False,False)
            assert abs(bb.ZMax-61.5)<1e-7 and abs(bb.ZMin-(61.5-thickness))<1e-7
    d.save()
    report={'scope':'Native dimensioned JST datum sketches and real received-fit fixture only; not a loaded socket geometry/fit pass','builder_sha256':sha(__file__),'native_sha256':sha(path),'frozen_LCD_retention_source':str(RETENTION.relative_to(ROOT)),'frozen_LCD_retention_source_sha256':RETENTION_SHA,'actual_LCD_retention_links':14,'new_fixture_addition_checks_against_actual_LCD_retention':added_checks,'equal_shim_geometric_interval_checked':True,'fixture_bodies':rows,'socket_solid_count':0,'unknown_internals_not_fabricated':True,'fully_constrained_sketches':True,'measurement_stack_interval_mm':[.1,1.5],'measurement_PCB_front_interval_Z_mm':[60,61.4],'physical_range_or_contactplane_qualified':False,'primary_loaded_contact_height_known':False,'full_product_order_ready':False}
    (OUT/'native-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
