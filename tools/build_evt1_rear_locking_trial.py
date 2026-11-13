"""Separate keyed tabwasher trial; no frozen product/joint source mutation.

Native profiles/Pads/Pockets express nominal geometry, not sheet-metal
springback, preload, torque capacity or received-material acceptance.
"""
from pathlib import Path
import sys,math,json,hashlib
lib=Path('/Applications/FreeCAD.app/Contents/Resources/lib')
if lib.is_dir():sys.path.insert(0,str(lib))
import FreeCAD as A
import Part,Sketcher
V=A.Vector
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/cad/manufacturing-layout/evt1-integration/rear-locking-trial'
LOOM=ROOT/'hardware/cad/manufacturing-layout/evt1-integration/contact-module-trial/pack-loom-trial/LocalTrayReliefLoomTrial.FCStd'
LOOM_SHA='93f79a0a3c46d9976f756f89f3c6d730208946d13c89078248d9545dc0e254be'
REAR=OUT.parent/'rear-joint-trial'
THICK=.25
INNER_R=.25
LEG_LENGTH=1.
OVERBEND_DEG=11.3
EAR_WIDTH=1.5
EAR_START=11.65
OUTER_BEND_START=12.
NEUTRAL_K=.5 # Geometric neutral-axis assumption for the inert flat coupon.
EAR_END=OUTER_BEND_START+(INNER_R+NEUTRAL_K*THICK)*math.radians(90+OVERBEND_DEG)+LEG_LENGTH
KEY_NEUTRAL_LENGTH=(INNER_R+NEUTRAL_K*THICK)*math.pi/2+.85
KEY_BLANK_INNER=9.75-KEY_NEUTRAL_LENGTH
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def bounds(s):
    b=s.optimalBoundingBox(False,False)
    return[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax]

def polygon(points):
    return[Part.LineSegment(V(*a,0),V(*b,0))for a,b in zip(points,points[1:]+points[:1])]

def rectangle(x0,y0,x1,y1):return polygon([(x0,y0),(x1,y0),(x1,y1),(x0,y1)])

def capsule(x0,y0,x1,y1):
    # Vertical narrow slot; two explicit semicircles.
    r=(x1-x0)/2;cx=(x0+x1)/2
    return[Part.LineSegment(V(x0,y0+r),V(x0,y1-r)),
       Part.Arc(V(x0,y1-r),V(cx,y1),V(x1,y1-r)),
       Part.LineSegment(V(x1,y1-r),V(x1,y0+r)),
       Part.Arc(V(x1,y0+r),V(cx,y0),V(x0,y0+r))]

def locked_sketch(body,name,geometries,placement):
    sk=body.newObject('Sketcher::SketchObject',name+'Profile');sk.Placement=placement
    for g in geometries:
        i=sk.addGeometry(g,False);sk.addConstraint(Sketcher.Constraint('Block',i))
    body.Document.recompute();assert sk.FullyConstrained,name
    return sk

def extrude(body,name,geometries,placement,length,pocket=False,reverse=False):
    sk=locked_sketch(body,name,geometries,placement)
    f=body.newObject('PartDesign::Pocket'if pocket else'PartDesign::Pad',name)
    f.Profile=sk;f.Length=length;f.Reversed=reverse
    body.Document.recompute();sk.Visibility=False
    assert f.Shape.isValid()and len(f.Shape.Solids)==1,(name,len(f.Shape.Solids))
    return f

def xz(y):return A.Placement(V(0,y,0),A.Rotation(V(1,0,0),90))

def xy(z):return A.Placement(V(0,0,z),A.Rotation())

def yz(x):return A.Placement(V(x,0,0),A.Rotation(V(1,1,1),120))

def stamp(o,name,text):
    o.addProperty('App::PropertyString',name,'Engineering');setattr(o,name,text)

def source_body(d,name,shape,source,source_sha):
    b=d.addObject('PartDesign::Body',name);f=b.newObject('PartDesign::Feature',name+'Snapshot');f.Shape=shape.copy()
    stamp(b,'SourceFile',source);stamp(b,'SourceSHA256',source_sha)
    return b

def ring_and_ears(d,name):
    b=d.addObject('PartDesign::Body',name)
    circles=[Part.Circle(V(),V(0,0,1),r)for r in(11.8,9.2)]
    extrude(b,name+'AnnularSeat',circles,xz(-10.25),THICK,reverse=True)
    ears=[]
    for k in range(12):
        t=math.radians(k*30);co,si=math.cos(t),math.sin(t)
        pts=[(r*co-w*si,r*si+w*co)for r,w in[(EAR_START,-EAR_WIDTH/2),(EAR_END,-EAR_WIDTH/2),(EAR_END,EAR_WIDTH/2),(EAR_START,EAR_WIDTH/2)]]
        ears.extend(polygon(pts))
    extrude(b,name+'TwelveRadialEars',ears,xz(-10.25),THICK,reverse=True)
    stamp(b,'MaterialCandidate','Goodfellow334-806-15 / SigmaGF33480615; annealed316L,50x50x0.25mm. Received thickness/COA, cut edge and bend properties unqualified.')
    stamp(b,'GeometryScope','One mutually exclusive sheet state. Neutral K=0.5 is geometric development only; no forming, preload or strength result.')
    return b

def key_relief_slots(body,name):
    slots=[]
    for sign in(-1,1):
        for side in(-1,1):
            xa,xb=(1.1,1.25)if side>0 else(-1.25,-1.1)
            za,zb=(KEY_BLANK_INNER-.15,10.05)if sign>0 else(-10.05,-KEY_BLANK_INNER+.15)
            slots+=capsule(xa,za,xb,zb)
    extrude(body,name,slots,xz(-10.3),.35,pocket=True)

def inner_key_profile(sign):
    p=lambda y,z:V(y,sign*z)
    outer0=p(-10.25,9.75);outer1=p(-9.75,9.25)
    inner0=p(-10.,9.75);inner1=p(-9.75,9.5)
    return[Part.Arc(outer0,p(-9.75-.5/math.sqrt(2),9.75-.5/math.sqrt(2)),outer1),
        Part.LineSegment(outer1,p(-8.9,9.25)),Part.LineSegment(p(-8.9,9.25),p(-8.9,9.5)),
        Part.LineSegment(p(-8.9,9.5),inner1),
        Part.Arc(inner1,p(-9.75-.25/math.sqrt(2),9.75-.25/math.sqrt(2)),inner0),
        Part.LineSegment(inner0,outer0)]

def make_flat_blank(d):
    b=ring_and_ears(d,'FlatWasherBlank')
    tongues=rectangle(-1.1,KEY_BLANK_INNER,1.1,10.05)+rectangle(-1.1,-10.05,1.1,-KEY_BLANK_INNER)
    extrude(b,'TwoFlatInnerTongues',tongues,xz(-10.25),THICK,reverse=True)
    key_relief_slots(b,'FlatTongueReliefSlots')
    return b

def make_prelock(d):
    b=ring_and_ears(d,'PrelockWasher')
    extrude(b,'VacatedInnerTongueLanes',rectangle(-1.1,-9.75,1.1,9.75),xz(-10.3),.35,pocket=True)
    key_relief_slots(b,'FormedInnerKeySideSlots')
    for sign in(-1,1):extrude(b,'BentInnerKey'+('Positive'if sign>0 else'Negative'),inner_key_profile(sign),yz(-1.1),2.2)
    return b

def outer_profile(start=OUTER_BEND_START,overbend=OVERBEND_DEG,leg=LEG_LENGTH):
    cy=-10.5;t0=math.pi/2;t1=-math.radians(overbend);tm=(t0+t1)/2
    p=lambda r,t:V(start+r*math.cos(t),cy+r*math.sin(t))
    d=V(math.sin(t1),-math.cos(t1));i0,i1=p(.25,t0),p(.25,t1);o0,o1=p(.5,t0),p(.5,t1)
    it=i1+d*leg;ot=o1+d*leg
    return[Part.Arc(i0,p(.25,tm),i1),Part.LineSegment(i1,it),Part.LineSegment(it,ot),
        Part.LineSegment(ot,o1),Part.Arc(o1,p(.5,tm),o0),Part.LineSegment(o0,i0)]

def make_locked(d,prelock):
    b=source_body(d,'LockedWasher',prelock.Shape,'Native PrelockWasher state','same document')
    extrude(b,'VacatedOuterEarLane',rectangle(OUTER_BEND_START,-EAR_WIDTH/2,14.,EAR_WIDTH/2),xz(-10.3),.35,pocket=True)
    extrude(b,'CornerClearOuterTab',outer_profile(),xy(-EAR_WIDTH/2),EAR_WIDTH)
    return b

def make_nut(d):
    b=d.addObject('PartDesign::Body','IFME10028QuarterMMRearward')
    r=24/math.sqrt(3);pts=[(r*math.cos(math.radians(30+60*k)),r*math.sin(math.radians(30+60*k)))for k in range(6)]
    extrude(b,'Published24AFNut',polygon(pts),xz(-14.25),4.,reverse=True)
    extrude(b,'Saved17mmThreadPilot',[Part.Circle(V(),V(0,0,1),8.5)],xz(-14.26),4.02,pocket=True)
    stamp(b,'ManufacturerPart','ifm E10028,316Ti/1.4571; source drawing24AF x4 /M18x1. Sharp regular hex conservatively exceeds the drawing27mm corner span; no undocumented chamfer credit.')
    return b

def tray_relief(d,shape,out_z,name):
    b=source_body(d,name,shape,str(LOOM.relative_to(ROOT)),LOOM_SHA)
    gg=rectangle(-1.2,9.15,1.2,out_z)+rectangle(-1.2,-out_z,1.2,-9.15)
    extrude(b,name+'InnerKeyPockets',gg,xz(-10.4),1.55,pocket=True)
    return b

def main():
    assert sha(LOOM)==LOOM_SHA
    OUT.mkdir(parents=True,exist_ok=True)
    source=A.openDocument(str(LOOM))
    context_shapes={name:source.getObject('Context_'+name).Shape.copy()for name in('MetalBody','ProposedFlangeTray','PackGrowthAllowance','PackSizeReference')}
    A.closeDocument(source.Name)
    d=A.newDocument('RearLockingTrial');parts=d.addObject('App::Part','SelectedTrialState');refs=d.addObject('App::Part','SourceContext');compare=d.addObject('App::Part','MutuallyExclusiveSheetStates')
    ctx={}
    for name,s in context_shapes.items():
        ctx[name]=source_body(d,'Source'+name,s,str(LOOM.relative_to(ROOT)),LOOM_SHA);refs.addObject(ctx[name])
    blank=make_flat_blank(d);compare.addObject(blank);print('FLAT_BLANK_READY',blank.Shape.Volume,flush=True)
    pre=make_prelock(d);compare.addObject(pre);print('PRELOCK_READY',pre.Shape.Volume,flush=True)
    locked=make_locked(d,pre);parts.addObject(locked)
    nut=make_nut(d);parts.addObject(nut)
    suggested=d.addObject('PartDesign::Body','SuggestedOuterBendNegative');compare.addObject(suggested)
    extrude(suggested,'SuggestedVerticalTab',outer_profile(11.8,0,1.3),xy(-EAR_WIDTH/2),EAR_WIDTH)
    t1=tray_relief(d,context_shapes['ProposedFlangeTray'],9.6,'SuggestedKeyReliefTray');compare.addObject(t1)
    suggested_tray_common=pre.Shape.common(t1.Shape).Volume
    chosen_z=9.6 if suggested_tray_common<1e-7 else 9.8
    tray=tray_relief(d,context_shapes['ProposedFlangeTray'],chosen_z,'LockingKeyReliefTray');parts.addObject(tray)
    driver_shape=Part.Shape();driver_shape.read(str(REAR/'TwoJawDriver.step'));assert driver_shape.isValid()and len(driver_shape.Solids)==1
    driver=source_body(d,'TwoJawDriver',driver_shape,str((REAR/'TwoJawDriver.step').relative_to(ROOT)),sha(REAR/'TwoJawDriver.step'));refs.addObject(driver)
    d.recompute();out=OUT/'RearLockingTrial.FCStd';d.saveAs(str(out));print('LOCKING_NATIVE_CHECKPOINT_SAVED',flush=True)
    tests={'suggested_outer_tab_nut_common_mm3':suggested.Shape.common(nut.Shape).Volume,
           'selected_outer_tab_nut_common_mm3':locked.Shape.common(nut.Shape).Volume,
           'selected_washer_body_common_mm3':locked.Shape.common(ctx['MetalBody'].Shape).Volume,
           'selected_washer_Tray_common_mm3':locked.Shape.common(tray.Shape).Volume,
           'suggested_9p6_Tray_common_mm3':suggested_tray_common,'selected_Tray_relief_max_absZ_mm':chosen_z,
           'actual_nut_body_common_mm3':nut.Shape.common(ctx['MetalBody'].Shape).Volume,
           'actual_nut_Tray_common_mm3':nut.Shape.common(tray.Shape).Volume}
    report={'status':'Native nominal keyed-tabwasher study; assembly, material and load gates open',
      'native_sha256':sha(out),'builder_sha256':sha(__file__),'source_native_sha256':LOOM_SHA,
      'stock':{'manufacturer':'Goodfellow','part':'334-806-15','supplier_SKU':'GF33480615','material':'annealed316L foil','size_mm':[50,50,.25],
        'primary_URL':'https://www.sigmaaldrich.com/US/en/product/aldrich/gf33480615','availability_and_received_COA_thickness_bend_properties_qualified':False},
      'dimensions':{'thickness_mm':THICK,'ring_ID_mm':18.4,'ring_OD_mm':23.6,'ear_count':12,'ear_width_mm':EAR_WIDTH,
        'flat_ear_end_radial_coordinate_mm':EAR_END,'flat_pattern_max_radius_mm':math.hypot(EAR_END,EAR_WIDTH/2),
        'inner_key_width_mm':2.2,'inner_key_inner_outer_absZ_mm':[9.25,9.5],'inner_key_leg_Y_mm':[-9.75,-8.9],
        'inner_key_bend_inner_outer_R_mm':[.25,.5],'outer_selected_bend_start_X_mm':OUTER_BEND_START,'outer_selected_overbend_deg':OVERBEND_DEG,
        'outer_selected_straight_leg_mm':LEG_LENGTH,'neutral_K_is_unqualified_geometric_assumption':NEUTRAL_K,
        'inner_blank_tongue_min_absZ_mm':KEY_BLANK_INNER,'formed_before_thread_installation_required':True,
        'nut_source_Y_mm':[-14,-10],'selected_nut_Y_mm':[-14.25,-10.25],'unselected_locking_stack_mm':.25},
      'nominal_part_checks':tests,'flat_volume_mm3':blank.Shape.Volume,'prelock_volume_mm3':pre.Shape.Volume,'locked_volume_mm3':locked.Shape.Volume,
      'flat_to_prelock_volume_delta_mm3':pre.Shape.Volume-blank.Shape.Volume,
      'selected_nut_bounds_mm':bounds(nut.Shape),'selected_washer_bounds_mm':bounds(locked.Shape),'source_body_fixed':True,
      'master_or_product_source_edited':False,'physical_validation':False,'nut_lock_strength_or_preload_credited':False,
      'assembly_loading_checked':False,'actual_angular_forming_checked':False}
    (OUT/'initial-review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(tests,indent=2),flush=True)

if __name__=='__main__':main()
