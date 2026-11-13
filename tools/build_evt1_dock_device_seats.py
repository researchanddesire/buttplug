"""Source-derived device seats and an inert, editable liner coupon.

The dock/device sources are immutable. Thin captured sheet pads and measured
PET shims set the existing device pose; no silicone modulus is assumed.
"""
from pathlib import Path
import hashlib,json,math,sys
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part,Sketcher,MeshPart
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/cad/evt1-assembly/device-seating-trial'
HOST=ROOT/'hardware/cad/evt1-assembly/DockAssembly.FCStd'
PRODUCT=ROOT/'hardware/cad/evt1-assembly/sources/ReadableEVT1Product.FCStd'
HOST_SHA='688c072ac989355187df894464c211c0e026bd0f2808f03d6ede89bcbbc055cd'
PRODUCT_SHA='63da08fb57ef4bd5c0af9bbb872e5ec13d2163aa234433ed3da78c525ebb3833'
V=App.Vector
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
ROLES=('MetalBody','MotorThermistorCap','ContinuousSkin','Contact_GND','Contact_USB_DM','Contact_USB_DP','Contact_DOCK_5V','SteelKeeper0','SteelKeeper1')
PADS=((-28,30),(28,30),(0,40))
BODY_Y=(104.5,108.5)
BODY_R=18.669085398110735
SILICONE_LOADED=.2484
PET=.0508
SOURCES={
 'device':{'native':str(PRODUCT.relative_to(ROOT)),'sha256':PRODUCT_SHA,'host_native':str(HOST.relative_to(ROOT)),'host_sha256':HOST_SHA,'placement_mm':[0,50,32],'contacts_Y_mm':23.2,'contact_center_Z_mm':43.5,'actual_outer_skin_bottom_Z_mm':13.0,'actual_body_max_outer_radius_mm':BODY_R,'inner_skin_surface_is_not_the_outer_support_surface':True},
 'soft_sheet':{'manufacturer':'Rogers','grade':'BISCO HT-6240','ordering_definition':'HT-6240 transparent solid silicone, plain/nonadhesive,0.010in; converter cut per supplied profiles; no invented stock SKU',
 'primary':'https://rogerscorp.com/-/media/project/rogerscorp/documents/elastomeric-material-solutions/bisco/english/data-sheets/180-093-bisco-ht-6240-transparent-solid-silicone-data-sheet.pdf',
 'availability_primary':'https://www.rogerscorp.com/-/media/project/rogerscorp/documents/elastomeric-material-solutions/bisco/english/product-availability/180-464-bisco-silicones-general-industrial-product-availability.pdf',
 'nominal_thickness_mm':.254,'published_thickness_tolerance_mm':[-.051,.051],'durometer_Shore_A':[35,45],
 'published_UV_resistance_is_not_a_275nm_aging_or_transmission_guarantee':True,'loaded_thickness_is_measured_not_predicted':True,'adhesive_credited':False,'quote_stock_and_received_identity_verified':False},
 'shim':{'manufacturer':'CS Hyde','mpn':'48-2F-1-100','material':'Plain Mylar TypeA PET','primary':'https://cshyde.com/viewitems/films/mylar-polyester-pet-film','nominal_thickness_mm':PET,'stock':'0.002in,1in x100ft','thickness_tolerance_not_assumed':True,'each_layer_has_integral_tail_and_slit_registration_hole':True,'film_retention_requires_closed_hole_silicone_cover':True},
 'print':{'material':'MJF PA12 or tough SLA','liner_min_nominal_floor_mm':1.5,'snap_catch_material_strength_and_soft_tail_tear_qualification':False},
 'fasteners':{'new_purchased_fasteners':0,'retention':'Integral liner mushroom catches; stretch sheet/film holes over received heads during inert trial. No adhesive.'}}

def box(a,b):return Part.makeBox(b[0]-a[0],b[1]-a[1],b[2]-a[2],V(*a))
def fuse(shapes):
 s=shapes[0]
 for x in shapes[1:]:s=s.fuse(x)
 return s.removeSplitter()
def cut(s,tools):
 for t in tools:s=s.cut(t)
 return s.removeSplitter()
def rr(x,y,w,h,r,z,d):
 # Actual rounded feature contour, not a selected-part fit substitute.
 s=fuse([box((x-w/2+r,y-h/2,z),(x+w/2-r,y+h/2,z+d)),box((x-w/2,y-h/2+r,z),(x+w/2,y+h/2-r,z+d))]+[Part.makeCylinder(r,d,V(x+sx*(w/2-r),y+sy*(h/2-r),z))for sx in(-1,1)for sy in(-1,1)])
 return s

def feature(b,name,s,note=''):
 assert s.isValid()and len(s.Solids)==1,(name,len(s.Solids))
 o=b.newObject('PartDesign::Feature',name);o.Shape=s;b.Tip=o
 if note:o.addProperty('App::PropertyString','EngineeringNote');o.EngineeringNote=note
 return o

def body(doc,name,s,color,note=''):
 b=doc.addObject('PartDesign::Body',name);feature(b,name+'Geometry',s,note)
 if b.ViewObject:b.ViewObject.ShapeColor=color
 return b

def sources():
 assert sha(HOST)==HOST_SHA,'Host changed: seating requires explicit revalidation'
 assert sha(PRODUCT)==PRODUCT_SHA,'Product source changed: do not silently regenerate seats'
 return next((d for d in App.listDocuments().values()if d.FileName==str(PRODUCT)),None)or App.openDocument(str(PRODUCT))

def actual_device(doc,prefix='ActualDevice'):
 source=sources();p=doc.addObject('App::Part',prefix)
 for role in ROLES:
  o=source.getObject(role);assert o and o.Shape.isValid(),role
  l=doc.addObject('App::Link',prefix+role);l.setLink(o);l.LinkPlacement=App.Placement(V(0,50,32),App.Rotation());p.addObject(l)
 return p

def native_extrusions(b,name,tools,subtract=False):
 """Create editable Sketch/Pocket/Pad from line/circle planar contours."""
 z=tools[0].BoundBox.ZMax if subtract else tools[0].BoundBox.ZMin
 d=tools[0].BoundBox.ZLength
 assert all(abs(t.BoundBox.ZLength-d)<1e-6 and abs((t.BoundBox.ZMax if subtract else t.BoundBox.ZMin)-z)<1e-6 for t in tools)
 s=b.newObject('Sketcher::SketchObject',name+'Profile');s.Placement.Base.z=z
 joined=fuse(tools)
 for solid in joined.Solids:
  low=solid.BoundBox.ZMin
  faces=[f for f in solid.Faces if f.BoundBox.ZLength<1e-7 and abs(f.BoundBox.ZMin-low)<1e-7]
  assert len(faces)==1,(name,len(faces))
  for wire in faces[0].Wires:
   for edge in wire.Edges:
    a,c=edge.FirstParameter,edge.LastParameter;p=lambda t:V(edge.valueAt(t).x,edge.valueAt(t).y,0)
    if isinstance(edge.Curve,Part.Line):g=Part.LineSegment(p(a),p(c))
    elif isinstance(edge.Curve,Part.Circle):
     g=Part.Circle(V(edge.Curve.Center.x,edge.Curve.Center.y,0),V(0,0,1),edge.Curve.Radius)if abs(c-a-2*math.pi)<1e-7 else Part.Arc(p(a),p((a+c)/2),p(c))
    else:raise TypeError((name,type(edge.Curve)))
    n=s.addGeometry(g,False);s.addConstraint(Sketcher.Constraint('Block',n))
 b.Document.recompute();assert s.FullyConstrained
 o=b.newObject('PartDesign::Pocket'if subtract else'PartDesign::Pad',name);o.Profile=s;o.Length=d
 b.Document.recompute();assert o.Shape.isValid()and len(o.Shape.Solids)==1,(name,len(o.Shape.Solids));s.Visibility=False
 return o

def fixed_features():
 catches=[(x,54)for x,y in PADS]+[(-24,106.5),(24,106.5)]
 return {'liner_flange_relief_cuts':[rr(0,37.25,92,28.5,2,12.6,.5)],
 'liner_shimland_adds':[rr(x,y,6,4,.6,12.5,.15)for x,y in PADS],
 'liner_body_relief_cuts':[box((-3.7,BODY_Y[0]-.2,12.5),(3.7,BODY_Y[1]+.2,13.5))],
 'liner_catch_stems':[Part.makeCylinder(1,.9,V(x,y,13))for x,y in catches],
 'liner_catch_heads':[Part.makeCylinder(1.7,.6,V(x,y,13.9))for x,y in catches],
 'dimensions':{'flange_relief_Z_mm':12.6,'flange_relief_X_mm':[-46,46],'flange_relief_Y_mm':[23,51.5],
 'shimland_top_Z_mm':12.65,'flange_pad_centres_mm':[list(p)for p in PADS],'flange_pad_face_mm':[6,4],
 'saddle_X_mm':[-3.5,3.5],'saddle_Y_mm':list(BODY_Y),'saddle_floor_Z_mm':12.5,
 'catch_centres_mm':[list(p)for p in catches],'catch_stem_diameter_mm':2,'catch_head_diameter_mm':3.4,
 'catch_underhead_Z_mm':13.9,'catch_top_Z_mm':14.5,'liner_min_floor_mm':1.5}}

def apply_liner_reliefs(b,prefix='DeviceSeat'):
 """Mutate only the supplied liner Body via named native features."""
 f=fixed_features()
 native_extrusions(b,prefix+'FlangeRelief',f['liner_flange_relief_cuts'],True)
 native_extrusions(b,prefix+'ThreeShimLands',f['liner_shimland_adds'])
 native_extrusions(b,prefix+'BodyPadRelief',f['liner_body_relief_cuts'],True)
 native_extrusions(b,prefix+'SheetCatchStems',f['liner_catch_stems'])
 native_extrusions(b,prefix+'SheetCatchHeads',f['liner_catch_heads'])
 return f

def apply_liner_saddle(b,loaded_silicone=SILICONE_LOADED,pet_stack=2*PET,prefix='DeviceSeat'):
 """Native XZ circular-arc sketch, extruded along+Y; identity dock frame."""
 assert .18<=loaded_silicone<=.31 and 0<=pet_stack<=.21
 radius=BODY_R+loaded_silicone+pet_stack;edge=32-math.sqrt(radius*radius-3.5**2);low=32-radius
 assert low>12.5
 s=b.newObject('Sketcher::SketchObject',prefix+'SaddleXZProfile')
 s.Placement=App.Placement(V(0,BODY_Y[0],0),App.Rotation(V(1,0,0),90))
 pts=[V(-3.5,12.5,0),V(3.5,12.5,0),V(3.5,edge,0),V(-3.5,edge,0)]
 gs=[Part.LineSegment(pts[0],pts[1]),Part.LineSegment(pts[1],pts[2]),Part.Arc(pts[2],V(0,low,0),pts[3]),Part.LineSegment(pts[3],pts[0])]
 for g in gs:n=s.addGeometry(g,False);s.addConstraint(Sketcher.Constraint('Block',n))
 b.Document.recompute();assert s.FullyConstrained
 o=b.newObject('PartDesign::Pad',prefix+'ActualRadiusSaddle');o.Profile=s;o.Length=4;o.Reversed=True
 b.Document.recompute();assert o.Shape.isValid()and len(o.Shape.Solids)==1;s.Visibility=False
 return {'feature':o,'radius_mm':radius,'minimum_face_Z_mm':low,'profile_source':'Maximum rotational exterior of actual MetalBody; constant maximum-radius envelope clears all+3Y sampled shifts.'}

def slab_y(x,w,yz):
 pts=[V(x,y,z)for y,z in yz];return Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(w,0,0))
def slab_x(y,w,xz):
 pts=[V(x,y,z)for x,z in xz];return Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,w,0))
def flange_sheet(x,y,h,layer_bottom,assembly_slit=False):
 # Lower tail stays below the skin; it rises outside the+3Y flange envelope.
 head=rr(x,y,6,4,.6,12.65+layer_bottom,h)
 z0=12.65+layer_bottom;z1=12.6+layer_bottom;z2=13+layer_bottom
 tail=slab_y(x-1,2,[(y+2,z0),(y+4,z1),(50,z1),(51.4,z2),(54,z2),(54,z2+h),(51.4,z2+h),(50,z1+h),(y+4,z1+h),(y+2,z0+h)])
 end=Part.makeCylinder(2.4,h,V(x,54,z2));s=fuse([head,tail,end]);s=s.cut(Part.makeCylinder(1.1,h+.02,V(x,54,z2-.01)))
 if assembly_slit:s=s.cut(box((x-.04,55,z2-.01),(x+.04,56.5,z2+h+.01)))
 return s.removeSplitter()

def body_sheet(h,inner_radius,flat,assembly_slit=False):
 # Annular central strap has the received sheet's radial thickness.
 y0,y1=BODY_Y;outer=inner_radius+h
 ann=Part.makeCylinder(outer,4,V(0,y0,32),V(0,1,0)).cut(Part.makeCylinder(inner_radius,4.02,V(0,y0-.01,32),V(0,1,0)))
 centre=ann.common(box((-3.5,y0,12),(3.5,y1,16)))
 a=32-math.sqrt(outer*outer-3.5**2);c=32-math.sqrt(inner_radius*inner_radius-3.5**2)
 # Flat tails lie on the actual liner/PET stack.
 sides=[]
 for sign in(-1,1):
  pts=[(3.5,a),(7,flat),(24,flat),(24,flat+h),(7,flat+h),(3.5,c)]
  pts=[(sign*x,z)for x,z in pts];tail=slab_x(y0,4,pts)
  end=Part.makeCylinder(2.4,h,V(sign*24,106.5,flat));end=end.cut(Part.makeCylinder(1.1,h+.02,V(sign*24,106.5,flat-.01)))
  if assembly_slit:
   xx=sign*24;slice_=box((xx+1 if sign>0 else xx-2.5,106.46,flat-.01),(xx+2.5 if sign>0 else xx-1,106.54,flat+h+.01));end=end.cut(slice_)
  sides.extend([tail,end])
 result=fuse([centre]+sides)
 for sign in(-1,1):result=result.cut(Part.makeCylinder(1.1,h+.02,V(sign*24,106.5,flat-.01)))
 return result.removeSplitter()

def build_components(doc,flange_loaded=SILICONE_LOADED,flange_layers=(2,2,2),body_loaded=SILICONE_LOADED,body_layers=2,film_layer=PET,prefix='DeviceSeat'):
 """Add retained softgoods/shim bodies. Apply liner helpers separately.

 At default settings flange contact is exactlyZ13.000. Thickness inputs are
 received measurements under representative load, not elastic predictions.
 """
 assert sha(PRODUCT)==PRODUCT_SHA,'Selecteddevicesourcechanged'
 assert len(flange_layers)==3 and all(0<=n<=4 for n in flange_layers)and 0<=body_layers<=4
 assert .18<=flange_loaded<=.31 and .18<=body_loaded<=.31 and abs(film_layer-PET)<1e-8
 parts=[];heights=[]
 for i,((x,y),n)in enumerate(zip(PADS,flange_layers)):
  stack=n*film_layer
  if stack:
   p=body(doc,prefix+'FlangePET'+str(i),flange_sheet(x,y,stack,0,True),(.70,.78,.82),'CSHyde48-2F-1-100 plainPETstack; everycutlayer hasintegraltail/hole. Internalstackinterfacesnotmodeled.');p.addProperty('App::PropertyInteger','LayerCount');p.LayerCount=n;parts.append(p)
  silicone=flange_sheet(x,y,stack+flange_loaded,0)
  if stack:silicone=silicone.cut(flange_sheet(x,y,stack,0)).removeSplitter()
  p=body(doc,prefix+'FlangeSilicone'+str(i),silicone,(.20,.66,.64),'RogersBISCOHT-6240 .010in, receivedloadedthickness; noassumedmodulus/adhesive/UVtransmission.');parts.append(p)
  heights.append(12.65+stack+flange_loaded)
 if body_layers:parts.append(body(doc,prefix+'BodyPET',body_sheet(body_layers*PET,BODY_R+body_loaded,13,True),(.70,.78,.82),'FormedPETlayers withassemblyslitsunderclosedholesiliconeretainer; radialinstalledposeisnotformingstrainvalidation.'))
 silicone=body_sheet(body_loaded+body_layers*PET,BODY_R,13)
 if body_layers:silicone=silicone.cut(body_sheet(body_layers*PET,BODY_R+body_loaded,13)).removeSplitter()
 parts.append(body(doc,prefix+'BodySilicone',silicone,(.20,.66,.64),'Onepiece0.010inHT-6240strap; central7x4mmradialband, softtailsoutboardofactualmetalbody.'))
 doc.recompute()
 return {'parts':parts,'fixed_features':fixed_features(),'received_stack':{'flange_pad_top_Z_mm':heights,'flange_loaded_sheet_mm':flange_loaded,'flange_PET_layers':list(flange_layers),'body_loaded_sheet_mm':body_loaded,'body_PET_layers':body_layers,'sheet_free_nominal_mm':.254,'load_deflection_measured':False},
 'shadow_limits':{'flange_face_contact_max_mm2':72,'body_band_contact_envelope_max_mm2':28,'total_contact_envelope_max_mm2':100,'tails_catches_and_geometry_also_block_rays':True,'275nm_transmission_credited':False,'contact_surface_cleaning_claim':False}}

def coupon(doc):
 b=doc.addObject('PartDesign::Body','SeatLinerCoupon')
 stock=fuse([rr(0,40,96,36,2,11,2),box((-5,56,11),(5,110,13)),rr(0,106.5,56,10,2,11,2)])
 feature(b,'PrintedCouponFloor',stock,'InertfunctionalreceiverwithactualfloorZ11..13; notafitproxyforselectedparts.')
 apply_liner_reliefs(b);apply_liner_saddle(b)
 if b.ViewObject:b.ViewObject.ShapeColor=(.91,.87,.76)
 return b

def main():
 OUT.mkdir(parents=True,exist_ok=True);source=sources();doc=App.newDocument('DeviceSeatingTrial')
 result=build_components(doc);liner=coupon(doc)
 doc.saveAs(str(OUT/'DeviceSeatingTrial.FCStd'));device=actual_device(doc)
 doc.recompute();assert device.Shape.isValid()
 for b in[liner]+result['parts']:
  assert b.Shape.isValid()and len(b.Shape.Solids)==1,b.Name
  b.Shape.exportStep(str(OUT/(b.Name+'.step')))
 mesh=MeshPart.meshFromShape(Shape=liner.Shape,LinearDeflection=.035,AngularDeflection=.15,Relative=False);assert mesh.isSolid();mesh.write(str(OUT/'SeatLinerCoupon.stl'))
 native=OUT/'DeviceSeatingTrial.FCStd';doc.saveAs(str(native))
 (OUT/'source-manifest.json').write_text(json.dumps(SOURCES,indent=2)+'\n')
 (OUT/'review.json').write_text(json.dumps({'native_sha256':sha(native),'builder_sha256':sha(Path(__file__)),'source_host_sha256':HOST_SHA,'source_device_sha256':PRODUCT_SHA,'received_stack':result['received_stack'],'shadow_limits':result['shadow_limits'],'fixed_feature_dimensions':result['fixed_features']['dimensions'],'physical_validation':False,'silicone_modulus_assumed':False,'full_product_release':False},indent=2)+'\n')
 print(json.dumps({'native':str(native),'parts':len(result['parts']),'received_stack':result['received_stack']}))
 App.closeDocument(doc.Name)
if __name__=='__main__':main()
