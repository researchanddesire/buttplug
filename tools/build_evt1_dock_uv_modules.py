"""Isolated, source-bound UV thermal module trial; frozen ECAD stays untouched.

Dimensions below are in the dock base frame. The lid uses a proper Ry180
rigid transform, preservingY. Stock sensors are dimension reconstructions;
their drawings and the unresolved received/thermal acceptance are recorded.
"""
from pathlib import Path
import hashlib,json,math,sys
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part
import MeshPart

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/cad/evt1-assembly/uv-module-trial'
UV=ROOT/'hardware/pcb/evt1/dock-uv'
V=App.Vector
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
HOLES=[(-45,89),(45,89),(-45,132),(45,132)]
NTC_X=-42.8
NTC_Y=108.5
NTC_Z=9.3-1.5*math.sqrt(2)
THERM_X=42
THERM_Y=97
THERM_Z=10.5
SOURCES={
 'thermostat':{'mpn':'67L045','manufacturer':'Sensata','primary':'https://www.sensata.com/sites/default/files/a/sensata-6700-series-subminiature-bimetal-disc-thermostats-datasheet.pdf',
  'manufacturer_PDF_mirror':'https://datasheet.lcsc.com/datasheet/pdf/4c88ade08706f1af20a35c2091fb47f8.pdf',
  'download_sha256':'9594546e47a02682a491c0b8a2c05b8813faf6692b89db2f9228240dfe06f548',
  'model_basis':'Manufacturerp3 dimensions; nominal15.24mm top-to-bodybottom derivedfrom29.59totalminus14.35REF leads. No guaranteed body-height tolerance inferred.',
  'width_mm':[10.16,.13],'depth_mm':[4.70,.25],'tab_mm':[.76,.03],'tab_extension_mm':[6.35,.51],
  'hole_from_top_mm':[2.79,.13],'hole_diameter_mm':[3.64,.089],
  'hole_source_discrepancy':'Inch0.145 equals3.683mm, not printed3.64mm; receivedholegoverns.',
  'lead_pitch_mm':[5.08,.25],'lead_width_mm':[.76,.08],'lead_shoulder_width_mm':[1.27,.10],
  'lead_thickness_mm':[.33,.013],'lead_plane_from_bracket_back_mm':[2.79,.13],
  'low_level4p5to5p25V_qualification':False},
 'NTC':{'mpn':'NTCLE413E2103F524A','manufacturer':'Vishay','primary':'https://www.vishay.com/docs/29078/ntcle413.pdf',
  'download_sha256':'6606fa831adab4119fb59af4123b9902ce193ee36d193b9da8d85028174f7312',
  'revision':'15-Oct-2026','head_max_diameter_mm':3,'head_max_length_mm':10,'total_length_mm':[52,5],
  'wire_insulation_diameter_for_information_mm':1,'twin_width_for_information_mm':2,'stripped_end_mm':[3,1],
  'model_basis':'Primarymaximum3x10mm lacquered head reconstructed as a capsule; not OEMCAD or a supplied profile tolerance.',
  'mounting':'Dry V saddle plus removable soft-backed clip; no potting, overmolding or fluidcontact.',
  'minimum_body_dielectric_Vrms':500},
 'pad':{'manufacturer':'Henkel/Bergquist','material':'GAP PAD TGP1500','sheet_order_code_candidate':'GP1500-0.020-02-0404',
  'primary':'https://dm.henkel-dam.com/is/content/henkel/lt-8116-brochure-thermal-interface-materials-selection-guide-1',
  'download_sha256':'f9dd0ac838e9e608763c086b0f5d97ff4d0e518b6d62a2f71f63445609185b03',
  'manufacturer_training_order_code':'https://www.digikey.com/en/ptm/h/bergquist/thermal-interface-materials-tim-gap-pad',
  'free_thickness_mm':.508,'LED_cut_mm':[12,3],'installed_LED_gap_mm':.4,
  'thermal_conductivity_W_mK_typ':1.5,'Youngs_modulus_kPa_typ':310,'dielectric_breakdown_Vac_typ':6000,
  'printed_electrical_data_are_test_typicals_not_product_insulation_qualification':True,
  'received_thickness_tolerance_not_assumed':True,'sheet_identity_thickness_quote_required':True},
 'metal':{'material':'6061-T6 aluminium','process':'CNC machine from6mm stock; integral1mm arms/steppedbridge/raisedcontactislands',
  'finish':'Deburr and roundcontactislandedgesR0.2; targetRa<=1.6um, no burrs. Anodize is not credited as insulation.'},
 'M2x3':{'manufacturer':'NBK','mpn':'SNSS-M2-3','primary':'https://www.nbk1560.com/images/en-US/product/miniaturescrew/SNSS/SNSS_1.pdf',
  'diameter_mm':2,'length_mm':3,'head_diameter_mm':3.8,'head_height_mm':2,'hex_AF_mm':1.5},
 'M2x4CS':{'manufacturer':'Accu','mpn':'SIK-M2-4-A2','primary':'https://www.accu.co.uk/phillips-countersunk-screws/65896-SIK-M2-4-A2',
  'diameter_mm':2,'length_mm':4,'head_diameter_mm':3.8,'head_height_mm':1.2,'head_angle_deg':90},
 'wire_sleeve':{'manufacturer':'TE Connectivity','mpn':'RNF-100-1/16-0-SP',
  'primary':'https://www.te.com/content/dam/te-com/documents/energy/global/productdocuments/Miscellaneous%20Locations/energy-epp0500-SoluzioniPerLindustia-italian.pdf',
  'expanded_ID_mm':1.6,'recovered_ID_mm':.8,'recovered_wall_mm':.43,'assembly_outer_diameter_limit_mm':2.4},
 'lacing':{'manufacturer':'Panduit','mpn':'PLT.6SM-C','primary':'https://www.panduit.com/content/dam/panduit/en/products/media/0/00/200/8200/111598200.pdf',
  'length_mm':71,'width_mm':1.8,'thickness_mm':.76,'head_approx_mm':[3.1,2.4,3.2],
  'installed_lacing_and_tail_pose_not_yet_modelled':True}
}

def box(x1,y1,z1,x2,y2,z2):return Part.makeBox(x2-x1,y2-y1,z2-z1,V(x1,y1,z1))
def fuse(shapes):
    s=shapes[0]
    for t in shapes[1:]:s=s.fuse(t)
    return s.removeSplitter()
def cut(s,tools):
    for t in tools:s=s.cut(t)
    return s.removeSplitter()
def feature(body,name,shape,note=''):
    assert shape.isValid(),name
    o=body.newObject('PartDesign::Feature',name);o.Shape=shape;body.Tip=o
    if note:o.addProperty('App::PropertyString','EngineeringNote');o.EngineeringNote=note
    return o
def body(doc,name,shape,color=(.7,.72,.75),note=''):
    b=doc.addObject('PartDesign::Body',name);feature(b,name+'Geometry',shape,note)
    if b.ViewObject:b.ViewObject.ShapeColor=color
    assert len(shape.Solids)==1,(name,len(shape.Solids))
    return b
def rectangle(w,h,z,x,y):return box(x-w/2,y-h/2,z,x+w/2,y+h/2,z+.01)
def side_transform(side):
    assert side in('Base','Lid')
    return App.Placement()if side=='Base'else App.Placement(V(0,0,68.5),App.Rotation(V(0,1,0),180))
def apply_pose(sh,placement):
    r=sh.copy();r.Placement=placement.multiply(r.Placement);return r

def spreader(doc,name):
    b=doc.addObject('PartDesign::Body',name)
    arms=[box(-49,86,8,-36.6,135,9),box(36.6,86,8,49,135,9),
          box(-49,128,6.5,49,135,7.5),box(-49,128,7.49,-36.6,135,8.01),box(36.6,128,7.49,49,135,8.01)]
    s=fuse(arms);feature(b,name+'SteppedUBlank',s,'Onecommonmetalpart; loweredrearbridgeclearstheactualGHcaseand4.35mmmatedheightbudget.')
    adds=[box(x-5,93,9,x+5,95,11.8)for x in(-42,42)]
    # Dry thermistor saddle rib stays below actual boost-driver components.
    adds.append(box(NTC_X-3,103.2,9,NTC_X+3,113.8,9.6))
    # Raised thermostat ledge: bracket backplane10.5, body extendsoutward.
    adds.extend([box(36.6,95.8,9,49,96.8,11.8),box(36.6,96.7,10.5,49,102.7,11.8)])
    s=fuse([s]+adds);feature(b,name+'LEDIslandsAndSensorLedges',s)
    cuts=[Part.makeCylinder(2.9,10,V(x,y,4))for x,y in HOLES]
    # The boardholes areonly3mm fromanedge. OpenopposingU-notches remove
    # theotherwise0.1mm metal ligaments around5.8mm postclearances.
    for x,y in HOLES:
        ya,yb=(85.9,89)if y==89 else(132,135.1)
        cuts.append(box(x-2.9,ya,4,x+2.9,yb,12))
    # Body/pressurebar window opens towardtheUvoid and preserves1.4mmouterrail.
    cuts.extend([box(36.5,102.3,4.5,47.6,113.6,10.6),box(37.5,96.9,7.9,46.5,102.6,9.8)])
    # Straight terminal/sleeve channels, well clearof neighboringmetal.
    for x in(THERM_X-2.54,THERM_X+2.54):cuts.append(box(x-1.9,112.7,5,x+1.9,122.5,9.6))
    # 90degreeVgroove: nominal3mmhead touchesbothfaces, free of hardpotting.
    pts=[V(NTC_X-2.2,103.2,7.1),V(NTC_X,103.2,9.3),V(NTC_X+2.2,103.2,7.1)]
    cuts.append(Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,10.6,0)))
    # Sensor clampclearances/countersinks aremachinedbeforeboardinstallation.
    for x,y in[(NTC_X,100),(NTC_X,117),(42,124.5)]:
        cuts.extend([Part.makeCylinder(1.1,5,V(x,y,5)),Part.makeCylinder(1.9,.3,V(x,y,9),V(0,0,-1)),
                     Part.makeCone(1.9,1.1,.8,V(x,y,8.7),V(0,0,-1))])
    cuts.append(Part.makeCylinder(.8,3,V(42,THERM_Y+2.79,10)))
    cuts.append(Part.makeCylinder(.8,3,V(48,115,7)))
    s=cut(s,cuts);feature(b,name+'MachinedSensorBaysAndMounts',s)
    assert len(s.Solids)==1,len(s.Solids)
    b.addProperty('App::PropertyString','Material');b.Material='6061-T6; machining/finishqualificationpending'
    if b.ViewObject:b.ViewObject.ShapeColor=(.73,.75,.78)
    return b

def thermostat(doc,name):
    # Coordinates followprimaryfrontview: localYtop->leads; localZbackface0,
    # packageandpins toward-Z. Reference-derivedcaseheightisnotamaxrating.
    tab=box(-5.08,0,-.76,5.08,6.4,0)
    tab=tab.cut(Part.makeCylinder(3.64/2,1,V(0,2.79,.1),V(0,0,-1)))
    case=box(-5.08,6.35,-4.7,5.08,15.24,0)
    package=fuse([tab,case])
    b=body(doc,name,package,(.17,.18,.19),SOURCES['thermostat']['model_basis'])
    # Actualtwoleadshoulders andnarrowtails; cut after6mm fromcasetoenable
    # solderedwireextensionswithretainedsleeves. No bent factorypins areassumed.
    leads=[]
    for x in(-2.54,2.54):
        leads.append(box(x-.635,15.24,-2.955,x+.635,20.73,-2.625))
        leads.append(box(x-.38,20.72,-2.955,x+.38,21.24,-2.625))
    feature(b,name+'CutSixMillimetreTerminals',fuse([package]+leads),'Cutlengthcandidate6mmaftercase; supplierminimumsolder/leadhandlingandreceivedoutlinegovern.')
    b.Placement.Base=V(THERM_X,THERM_Y,THERM_Z)
    return b

def ntc(doc,name):
    # Maximumhead capsule, dimensions fromVishay; not a generic box.
    sh=Part.makeCylinder(1.5,7,V(NTC_X,NTC_Y-3.5,NTC_Z),V(0,1,0))
    sh=fuse([sh,Part.makeSphere(1.5,V(NTC_X,NTC_Y-3.5,NTC_Z)),Part.makeSphere(1.5,V(NTC_X,NTC_Y+3.5,NTC_Z))])
    return body(doc,name,sh,(.09,.09,.10),SOURCES['NTC']['model_basis'])

def ntc_clip(doc,name):
    s=box(NTC_X-3,98,5,NTC_X+3,119,8)
    # Saddle clearance is free aroundthehead; a separate softpad pushes it
    # lightly into theV. The actualpreload isameasured acceptance, not E-basedproof.
    cavity=Part.makeCylinder(1.65,11,V(NTC_X,103,NTC_Z),V(0,1,0))
    s=cut(s,[cavity,box(NTC_X-1.6,106.5,5.3,NTC_X+1.6,110.5,NTC_Z-1.5),
             Part.makeCylinder(.8,4,V(NTC_X,100,4.9)),Part.makeCylinder(.8,4,V(NTC_X,117,4.9))])
    s=cut(s,[Part.makeCylinder(1.3,.4,V(NTC_X,y,7.7))for y in(100,117)])
    # Leadexitandlacinganchors lie beyondthehead, not across thebead.
    s=cut(s,[box(NTC_X-1.4,113,6.7,NTC_X+1.4,119.1,8.1),
             box(NTC_X-2.5,115,4.9,NTC_X-1.6,117.2,6.0),box(NTC_X+1.6,115,4.9,NTC_X+2.5,117.2,6.0)])
    return body(doc,name,s,(.30,.31,.33),'MJFPA12dryretainer; taps/force/creepandlacingqualificationpending. Do not hardpotNTC.')

def guard(doc,name):
    s=box(36.8,114.0,5.5,48.8,126.5,6.0)
    adds=[]
    for x in(THERM_X-2.54,THERM_X+2.54):
        tube=Part.makeCylinder(1.8,7.8,V(x,114.2,7.71),V(0,1,0))
        # Bottomwebjoinsbothsplitguardhalves; innerboresaccept<=2.4mmsleeves.
        adds.append(tube);adds.append(box(x-1.0,114.2,5.9,x+1.0,122,7.2))
    adds.extend([Part.makeCylinder(2.3,2.1,V(42,124.5,5.9)),Part.makeCylinder(.7,3.1,V(48,115,6))])
    s=fuse([s]+adds)
    tools=[Part.makeCylinder(1.4,9,V(x,114,7.71),V(0,1,0))for x in(39.46,44.54)]
    tools.append(Part.makeCylinder(.8,4,V(42,124.5,5.4)))
    tools.append(Part.makeCylinder(1.3,.4,V(42,124.5,7.7)))
    for x in(38.3,45.7):tools.append(box(x-.45,115,5.4,x+.45,117.2,9.6))
    s=cut(s,tools)
    return body(doc,name,s,(.3,.31,.33),'Retainedterminal/sleeveguard, onerearM2tap+frontlocator; lacingthroughmatchedslots, actualsleeves/tieposeandpulltestremainopen.')

def screw_shape(length,cs=False):
    if cs:
        rim=1.2-(1.9-1)
        return fuse([Part.makeCylinder(1,length-1.2,V(0,0,-length)),
                     Part.makeCone(1.9,1,.9,V(0,0,-rim),V(0,0,-1)),Part.makeCylinder(1.9,rim,V(0,0,-rim))])
    s=fuse([Part.makeCylinder(1,length,V(0,0,-length)),Part.makeCylinder(1.9,2)])
    pts=[V(.75/math.cos(math.pi/6)*math.cos(i*math.pi/3),.75/math.cos(math.pi/6)*math.sin(i*math.pi/3),1)for i in range(6)]
    return s.cut(Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(V(0,0,1.1)))

def shell_shoulders(side='Base'):
    pose=side_transform(side);out=[]
    for x,y in HOLES:
        z=8 if y==89 else 6.5
        s=Part.makeCylinder(3.8,1,V(x,y,z-1)).cut(Part.makeCylinder(.5,1.2,V(x,y,z-1.1)))
        out.append(apply_pose(s,pose))
    return out

def build_components(doc,side='Base',prefix=None,include_board=False):
    """No saves ormastermutations. Returnthermalparts + exactshellshoulderadds.

    Frozenboardsalreadyintheparentmustnotbeduplicated; include_board isfor
    the isolatedtrialonly. Parentappliesreturnedshoulders tocorrespondingshell.
    """
    prefix=prefix or 'UV'+side;pose=side_transform(side);parts=[]
    metal=spreader(doc,prefix+'Spreader6061');parts.append(metal)
    for i,x in enumerate((-42,42)):
        parts.append(body(doc,prefix+'LEDInsulator'+str(i),box(x-6,92.5,11.8,x+6,95.5,12.2),(.15,.15,.16),
            'SelectedTGP1500cut12x3x0.508;0.4mminstalledclearanceposeonly. Flow/pressure/dielectricqualificationpending.'))
    sensor=thermostat(doc,prefix+'Sensata67L045');parts.append(sensor)
    pressure=box(38,THERM_Y+.29,8.74,46,THERM_Y+5.29,9.74)
    pressure=pressure.cut(Part.makeCylinder(1.1,1.2,V(42,THERM_Y+2.79,8.6)))
    parts.append(body(doc,prefix+'ThermostatPressureBar6061',pressure,(.73,.75,.78)))
    parts.extend([ntc(doc,prefix+'VishayNTC'),ntc_clip(doc,prefix+'DryNTCClip'),guard(doc,prefix+'TerminalGuard')])
    parts.append(body(doc,prefix+'NTCSoftSupport',box(NTC_X-1.5,106.5,5.3,NTC_X+1.5,110.5,NTC_Z-1.5),(.15,.15,.16),
        'TGP1500free0.508mm;receivedhead/supportpreload0.05..0.20Nmustbemeasured. Not adhesive or potting.'))
    for i,(x,y)in enumerate([(NTC_X,100),(NTC_X,117),(42,124.5)]):
        sh=screw_shape(4,True);sh.translate(V(x,y,9));parts.append(body(doc,prefix+'AccuCS4_'+str(i),sh))
    sh=screw_shape(3);sh.rotate(V(),V(0,1,0),180);sh.translate(V(42,THERM_Y+2.79,8.74))
    parts.append(body(doc,prefix+'NBKThermostatM2x3',sh))
    for b in parts:b.Placement=pose.multiply(b.Placement)
    board=None
    if include_board:
        path=UV/side.lower()/'pcb'/('dock-uv-'+side.lower()+'.step')
        manifest=json.loads((path.parent/'mcad.json').read_text());assert sha(path)==manifest['STEP_sha256']
        raw=Part.Shape();raw.read(str(path));assert raw.isValid()and len(raw.Solids)==41
        p=App.Placement(V(0,0,12.27),App.Rotation())if side=='Base'else App.Placement(V(0,0,56.23),App.Rotation(V(0,1,0),180))
        board=doc.addObject('App::Part',prefix+'FrozenPCBA')
        for i,s in enumerate(raw.Solids):
            b=body(doc,prefix+'SourceSolid'+str(i),apply_pose(s,p),(.4,.48,.35),'ExactfrozenSTEPsolid; originalboardgeometry/routesunchanged.')
            board.addObject(b)
    doc.recompute()
    return {'parts':parts,'spreader':metal,'NTC':parts[5],'thermostat':sensor,'board':board,
            'shell_shoulder_adds':shell_shoulders(side),'side':side}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    doc=App.newDocument('UVModuleThermalTrial')
    modules=[build_components(doc,s,include_board=True)for s in('Base','Lid')]
    checks=[]
    for m in modules:
        board_shapes=[b.Shape for b in m['board'].Group]
        for p in m['parts']:
            assert p.Shape.isValid()and len(p.Shape.Solids)==1,p.Name
            for i,s in enumerate(board_shapes):
                bb1,bb2=p.Shape.BoundBox,s.BoundBox
                if not bb1.intersect(bb2):continue
                vol=p.Shape.common(s).Volume
                checks.append({'component':p.Name,'source_solid':i,'intersection_mm3':vol})
                assert vol<1e-5,(p.Name,i,vol)
        # Additionalhardware/substrateBplaneclearanceisnotinCLI STEP'score.
        assert m['spreader'].Shape.isValid()
    native=OUT/'UVModuleThermalTrial.FCStd';doc.recompute();doc.saveAs(str(native))
    for m in modules:
        m['spreader'].Shape.exportStep(str(OUT/(m['side']+'Spreader6061.step')))
        doc.getObject('UV'+m['side']+'ThermostatPressureBar6061').Shape.exportStep(str(OUT/(m['side']+'ThermostatPressureBar6061.step')))
        for suffix in('DryNTCClip','TerminalGuard'):
            b=doc.getObject('UV'+m['side']+suffix)
            mesh=MeshPart.meshFromShape(Shape=b.Shape,LinearDeflection=.04,AngularDeflection=.2,Relative=False)
            assert mesh.isSolid();mesh.write(str(OUT/(b.Name+'.stl')))
    (OUT/'source-manifest.json').write_text(json.dumps(SOURCES,indent=2)+'\n')
    report={'status':'native thermal/sensor mounting candidate; not physically qualified',
      'builder_sha256':sha(Path(__file__)),'native_sha256':sha(native),
      'frozen_sources':{s:json.loads((UV/s/'pcb'/'mcad.json').read_text())for s in('base','lid')},
      'actual_source_solid_checks':checks,'selected_parts':SOURCES,
      'metal_body_count':2,'UVsource_solids_each':41,'source_boards_modified':False,
      'geometry':{'main_plate_Z_base_mm':[8,9],'rear_bridge_Z_base_mm':[6.5,7.5],
        'rear_bridge_Y_mm':[128,135],'metal_inner_arm_X_abs_min_mm':36.6,'LED_contact_island_top_Z_base_mm':11.8,
        'LEDpad_copperplane_gap_mm':.4,'spreader_post_opposed_endnotch_width_mm':5.8,'shell_post_mm':5.2,'shell_shoulder_radius_mm':3.8,
        'NTC_head_center_base_mm':[NTC_X,NTC_Y,NTC_Z],'thermostat_bracket_origin_base_mm':[THERM_X,THERM_Y,THERM_Z]},
      'required_acceptance':['receivedsensor/PCB/padstackandmatedGH/wireclearance','actualcontactforce/flatness/padflowanddielectricaftercycles',
        'sensorleadextensions/sleeving/lacingand1Nstrainrelieftrial','sensorlag/hottestLEDanddriverselection/thermalcutoffwithfaults',
        'FR4/vias/islands/closedcasejunctiontemperature','UVleakage/dose/efficacy/materialaging/finishedcontainment'],
      'physical_validation':False,'full_product_release':False}
    (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'native':str(native),'actual_board_pairs':len(checks),'native_sha256':sha(native)}))
    App.closeDocument(doc.Name)

if __name__=='__main__':main()
