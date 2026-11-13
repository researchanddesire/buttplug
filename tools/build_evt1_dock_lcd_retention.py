"""Isolated compliant LCD mounting coupon; never edits the master dock.

Two printed carriers share the four existing bezel screws. Ears occupy roof
pockets aboveZ66, preserving the orange roof bearing below the unchangedZ64
underhead datum. Paired face pads avoid active/COG areas and edge squeezing.
"""
from pathlib import Path
import hashlib,json,math,sys
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part
import MeshPart

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/cad/evt1-assembly/lcd-retention-trial'
sys.path.insert(0,str(ROOT/'tools'))
import build_evt1_dock_display as display
V=App.Vector
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
MOUNTS=[(-34.5,69),(34.5,69),(-13,105),(13,105)]
SOURCES={
 'LCD':{'manufacturer':'Newhaven','mpn':'NHD-C12864B2Z-RN-FBW',
   'primary':'https://newhavendisplay.com/content/specs/NHD-C12864B2Z-RN-FBW.pdf',
   'OEM_STEP':str(display.MODEL.relative_to(ROOT)),'OEM_STEP_sha256':display.SOURCE_SHA256,
   'handling':'https://newhavendisplay.com/lcd-displays/cog-lcd-displays/',
   'handling_basis':'Support glass evenly, pressure off glass edges and exposed controller. No numeric allowable mounting load is published here.',
   'front_datum_mm':[0,87,68.8],'maximum_published_depth_mm':2.1,
   'OEM_internal_visual_solids_are_not_a_material_stack':True},
 'foam':{'manufacturer':'Rogers','mpn':'4790-92-09030-04 P','product_identifier':'3036884',
   'primary':'https://www.rogerscorp.com/-/media/project/rogerscorp/documents/elastomeric-material-solutions/poron/english/product-availability/17-082-poron-polyurethanes-product-availability-brochure.pdf',
   'family_primary':'https://www.rogerscorp.com/elastomeric-material-solutions/poron-industrial-polyurethanes/poron-4790-92',
   'nominal_thickness_mm':.75,'family_thickness_tolerance_fraction':.10,'density_kg_m3':144,
   'carrier':'2mil PET support; whether nominal0.75includesPET is not explicit in retrieved primarytext. Measure total stack.',
   'CFD_at25percent_kPa_typ':1.70,'CFD_is_not_a_guaranteed_load':True,
   'cut_dimensions_mm':[1.2,22],'cut_quantity':4,'adhesive_credited':False,
   'availability_or_supplier_quote_verified':False},
 'shim':{'manufacturer':'CS Hyde','mpn':'48-2F-1-100','material':'Mylar TypeA PET, plain nonadhesive film',
   'primary':'https://cshyde.com/viewitems/films/mylar-polyester-pet-film',
   'nominal_thickness_in':.002,'nominal_thickness_mm':.0508,'stock_width_in':1,'stock_length_ft':100,
   'thickness_tolerance_not_assumed':True,'shape':'One-piece pad shim with tail and rear screw registration hole, die cut from plainfilm. No loose rectangular shims.'},
 'fasteners':{'reuse':'ExistingfourNBK SNSS-M2-6 bezel screws',
   'primary':'https://www.nbk1560.com/images/en-US/product/miniaturescrew/SNSS/SNSS_1.pdf',
   'underhead_Z_mm':64,'shaft_tip_Z_mm':70,'bezel_pilot_top_Z_mm':70.1,
   'nominal_bezel_engagement_mm':2.3,'front_heads':False},
 'printed':{'material':'MJFPA12 or toughSLA','frame_min_main_thickness_mm':1.7,
   'shim_channel_roof_mm':.7,'rear_platform_mm':1.6,'material_torque_creep_and_drop_qualification':False}
}

def box(x1,y1,z1,x2,y2,z2):return Part.makeBox(x2-x1,y2-y1,z2-z1,V(x1,y1,z1))
def fuse(shapes):
    out=shapes[0]
    for s in shapes[1:]:out=out.fuse(s)
    return out.removeSplitter()
def minus(shape,tools):
    for t in tools:shape=shape.cut(t)
    return shape.removeSplitter()
def capsule(a,b,width,z,height):
    p,q=V(*a,z),V(*b,z);d=q-p;length=d.Length
    r=width/2;normal=V(-d.y,d.x,0).normalize()*r
    pts=[p+normal,q+normal,q-normal,p-normal]
    return fuse([Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,0,height)),
                 Part.makeCylinder(r,height,p),Part.makeCylinder(r,height,q)])
def mirror(s,side):
    return s.copy()if side=='Right'else s.mirror(V(),V(1,0,0))
def feature(b,name,shape,note=''):
    assert shape.isValid(),name
    o=b.newObject('PartDesign::Feature',name);o.Shape=shape;b.Tip=o
    if note:o.addProperty('App::PropertyString','EngineeringNote');o.EngineeringNote=note
    return o
def body(doc,name,shape,color=(.75,.73,.67),note=''):
    assert shape.isValid()and len(shape.Solids)==1,(name,len(shape.Solids))
    b=doc.addObject('PartDesign::Body',name);feature(b,name+'Geometry',shape,note)
    if b.ViewObject:b.ViewObject.ShapeColor=color
    return b

def shim_shape(z,height,clearance=False):
    w=2.2 if clearance else 1.6
    s=fuse([box(22.5,76,z,27.1,98,z+height),
            capsule((26.5,97),(27.5,103.5),w,z,height),
            capsule((27.5,103.5),(13,105),w,z,height),
            Part.makeCylinder(2.7 if clearance else 2.6,height,V(13,105,z))])
    return s.cut(Part.makeCylinder(1.2,height+.02,V(13,105,z-.01))).removeSplitter()

def carrier(doc,name,side):
    b=doc.addObject('PartDesign::Body',name)
    segments=[((34.5,69),(27.5,77)),((27.5,77),(27.5,103.5)),((27.5,103.5),(13,105))]
    s=fuse([capsule(a,c,4,66,1.7)for a,c in segments]+[
       Part.makeCylinder(3,1.7,V(34.5,69,66)),Part.makeCylinder(3.5,1.7,V(13,105,66))])
    s=mirror(s,side);feature(b,name+'RigidSpineAndSharedScrewEars',s,
        'Earbottom66/top67.7 is the hardjointstack; existinghead64stillbears2mmorange roof beloweachscrew.')
    platform=mirror(box(22.5,76,64.4,29.5,98,66),side)
    s=fuse([s,platform]);feature(b,name+'MatchedRearFacePlatform',s,
        'Onlysoftpadstransmitnormalglassload; raisedframe staysoutsideglassedges. NoCOGoractivearea hard contact.')
    # PET stack has a tail registered on the existing rear screw. This retains
    # every individual layer without an adhesive or an unrestrained rectangle.
    pockets=[box(24.4,75.9,66,27.3,98.1,67),
             capsule((26.5,97),(27.5,103.5),2.2,66,1),
             capsule((27.5,103.5),(13,105),2.2,66,1),
             Part.makeCylinder(2.7,1,V(13,105,66))]
    tools=[mirror(t,side)for t in pockets]
    sign=1 if side=='Right'else-1
    tools.extend(Part.makeCylinder(1.15,4,V(sign*x,y,64))for x,y in[(34.5,69),(13,105)])
    s=minus(s,tools);feature(b,name+'RegisteredShimChannelAndBores',s,
       'PETtailhole iscapturedbyrearM2screw.1.0mmpocketheight accommodatesreceivedlocalglassfaces, notanadhesivejoint.')
    assert len(s.Solids)==1,(name,len(s.Solids))
    if b.ViewObject:b.ViewObject.ShapeColor=(.22,.26,.30)
    return b

def fixed_features(foam_total=.75,compression=.25,front_z=68.8):
    floor=max(69.1,front_z+foam_total*(1-compression));gap=floor-front_z;roof=[];bezel=[]
    path=[((34.5,69),(27.5,77)),((27.5,77),(27.5,103.5)),((27.5,103.5),(13,105))]
    for side in('Left','Right'):
        for a,b in path:roof.append(mirror(capsule(a,b,4.6,66,2.2),side))
        roof.extend(mirror(t,side)for t in[
            Part.makeCylinder(3.3,2.2,V(34.5,69,66)),Part.makeCylinder(3.8,2.2,V(13,105,66)),
            box(22.2,75.7,63.8,29.8,98.3,66.1),box(22.4,75.8,66,27.3,98.2,68.2)])
        bezel.append(mirror(box(22.4,75.8,69.0,23.8,98.2,floor),side))
    return {'roof_cuts':roof,'bezel_gasket_cuts':bezel,'bezel_adds':[],
      'dimensions':{'shared_mounts':MOUNTS,'ear_floor_Z_mm':66,'ear_top_Z_mm':67.7,'unchanged_head_Z_mm':64,
          'rear_pad_platform_Z_mm':66,'front_pad_pocket_floor_Z_mm':front_z+gap,'nominal_pad_gap_mm':gap,
          'face_pad_X_abs_mm':[22.5,23.7],'face_pad_Y_mm':[76,98],
          'no_edge_preload':True,'no_adhesive_credit':True}}

def build_components(doc,measured_depth=1.8,foam_total=.75,film_layer=.0508,compression=.25,prefix='LCDRetention',front_local_z=68.8):
    """Add two carriers/four captured facepads/two registered PET stacks.

    No LCD duplication, master changes or saves. Values are received local-face
    measurements, not an assumed physical meaning of overlapping OEM graphics.
    Apply returned roof/bezel cuts in the master and reuse its four screws.
    """
    assert 1.4<=measured_depth<=2.1 and .675<=foam_total<=.90 and .04<=film_layer<=.06 and 68.5<=front_local_z<=68.8
    assert 68.8-front_local_z+measured_depth<=2.1+1e-9,'Receivedlocalfacesmustalsomeetpublishedmaximumoverallrearprojection'
    floor=max(69.1,front_local_z+foam_total*(1-compression));gap=floor-front_local_z;rear=front_local_z-measured_depth
    layers=max(0,round((rear-gap-66)/film_layer));shim=layers*film_layer
    assert 0<=shim<=.94
    rear_gap=rear-(66+shim)
    assert .10<1-rear_gap/foam_total<.45
    parts=[]
    for side in('Left','Right'):
        parts.append(carrier(doc,prefix+side+'Carrier',side))
        if layers:
            b=body(doc,prefix+side+'RegisteredPETStack',mirror(shim_shape(66,shim),side),(.78,.82,.80),
               'PlainCSHyde48-2F-1-100: individuallycut0.0508mmlayers, screwregisteredtail; layerinterfacesomittedfromstacksolid.')
            b.addProperty('App::PropertyInteger','LayerCount');b.LayerCount=layers
            b.addProperty('App::PropertyLength','MeasuredSingleLayer');b.MeasuredSingleLayer=film_layer
            parts.append(b)
        for face,z,h in[('Front',front_local_z,gap),('Rear',66+shim,rear_gap)]:
            parts.append(body(doc,prefix+side+face+'PORON',mirror(box(22.5,76,z,23.7,98,z+h),side),(.12,.12,.14),
               'Rogers4790-92-09030-04P product3036884, plainPETsupportedfoam; installedpose, notmaterialsimulation. Measurelocalfacesandforce.'))
    doc.recompute()
    return {'parts':parts,'fixed_features':fixed_features(foam_total,compression,front_local_z),
      'received_stack':{'measured_local_LCD_depth_mm':measured_depth,'measured_free_total_foam_mm':foam_total,
        'measured_PET_layer_mm':film_layer,'PET_layers_each':layers,'PET_stack_mm':shim,
        'local_front_face_Z_mm':front_local_z,'front_gap_mm':gap,'rear_gap_mm':rear_gap,'front_compression_fraction':1-gap/foam_total,
        'rear_compression_fraction':1-rear_gap/foam_total,
        'equal_spring_linear_float_estimate_mm':(gap-rear_gap)/2,
        'CFD25percent_nominal_reference_force_N':1.70e3*(2*1.2*22)*1e-6,
        'force_or_glass_stress_not_validated':True}}

def fixture(doc,fixed):
    stock=fuse([box(-44,55,64,44,113,67.4)]+[Part.makeCylinder(2,3.7,V(x,y,64))for x,y in MOUNTS])
    r=body(doc,'RoofCoupon',stock,(.94,.39,.10),'Actualprintablebenchreceiver;67.4bezelrecessandfour67.7supportseatsmatchmasterdatums;notaproductfitproxy.')
    s=r.Tip.Shape
    tools=[box(-24.3,64.7,63.8,24.3,101.3,69),box(-7.6,57,61.4,7.6,65.6,68.3)]
    tools.extend(Part.makeCylinder(1.1,5,V(x,y,63.8))for x,y in MOUNTS)
    tools+=fixed['roof_cuts'];s=minus(s,tools);feature(r,'ActualRoofReceiverPockets',s)
    b=body(doc,'BezelCoupon',box(-44,55,67.7,44,113,70.5),(.91,.87,.76),'Printedreceiverwithactualglassseat/viewdatums.')
    tools=[box(-24.3,64.7,67.6,24.3,101.3,69.1),box(-22.2,74.8,67.6,22.2,99.2,70.6),
           box(-7.6,57,67.6,7.6,65.6,68.3)]
    tools.extend(Part.makeCylinder(.5,2.5,V(x,y,67.6))for x,y in MOUNTS)
    tools+=fixed['bezel_gasket_cuts'];s=minus(b.Tip.Shape,tools);feature(b,'ActualBezelSeatAndCapturedFrontPads',s)
    doc.recompute();return r,b

def screw(doc,name,x,y):
    sh=fuse([Part.makeCylinder(1,6,V(x,y,64)),Part.makeCylinder(1.9,2,V(x,y,62))])
    return body(doc,name,sh,(.65,.67,.70),'ExistingNBKSNSS-M2-6 externalprofile; threadmajoroverlapwithprintedpilotintentional. Noheadorlengthchange.')

def main():
    OUT.mkdir(parents=True,exist_ok=True);doc=App.newDocument('LCDRetentionTrial')
    result=build_components(doc)
    roof,bezel=fixture(doc,result['fixed_features'])
    lcd=display.build(doc,name='SelectedLCD',ffc_pose='installed');lcd.Placement.Base=V(0,87,68.8)
    for i,(x,y)in enumerate(MOUNTS):screw(doc,'ExistingBezelM2x6_'+str(i),x,y)
    doc.recompute()
    assert lcd.Shape.isValid()
    for p in result['parts']:
        assert p.Shape.isValid()and len(p.Shape.Solids)==1,p.Name
        if p.Name.endswith('Carrier'):assert p.Shape.common(lcd.Shape).Volume<1e-5,p.Name
        p.Shape.exportStep(str(OUT/(p.Name+'.step')))
    for b in[roof,bezel]+[p for p in result['parts']if p.Name.endswith('Carrier')]:
        mesh=MeshPart.meshFromShape(Shape=b.Shape,LinearDeflection=.04,AngularDeflection=.2,Relative=False)
        assert mesh.isSolid();mesh.write(str(OUT/(b.Name+'.stl')))
    native=OUT/'LCDRetentionTrial.FCStd';doc.saveAs(str(native))
    (OUT/'source-manifest.json').write_text(json.dumps(SOURCES,indent=2)+'\n')
    (OUT/'review.json').write_text(json.dumps({'native_sha256':sha(native),'builder_sha256':sha(Path(__file__)),
      'status':'firstcompliantLCDcoupon; physicalqualificationpending','received_stack':result['received_stack'],
      'feature_dimensions':result['fixed_features']['dimensions'],'selected_LCD_SHA256':display.SOURCE_SHA256,
      'display_builder_sha256':sha(Path(display.__file__)),'display_source_manifest_sha256':sha(display.SOURCES/'source-manifest.json'),
      'printed_bodies':[b.Name for b in[roof,bezel]+[p for p in result['parts']if p.Name.endswith('Carrier')]],
      'master_edited':False,'adhesive_credited':False,'glass_force_or_mura_validated':False,
      'published_LCD_minimum_depth_assumed':False,'physical_validation':False},indent=2)+'\n')
    print(json.dumps({'native':str(native),'received_stack':result['received_stack']}))
    App.closeDocument(doc.Name)

if __name__=='__main__':main()
