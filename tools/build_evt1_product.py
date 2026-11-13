"""Integrate actual EVT1 device PCBs with the selected four-part mechanics.

FreeCAD Python. Original manufacturing/dock sources remain read-only. This
checkpoint checks nominal board/component space, not materials or physical fit.
"""
from pathlib import Path
import hashlib
import itertools
import json
import math
import sys
import xml.etree.ElementTree as ET
import zipfile
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
import MeshPart

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hardware/cad/manufacturing-layout'
OUT=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else SOURCE/'evt1-integration'
OUT.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_report=json.loads((SOURCE/'review.json').read_text())
dock_report=json.loads((SOURCE/'charging-dock/review.json').read_text())
assert sha(SOURCE/'ManufacturingLayout.FCStd')==source_report['native_sha256']
assert sha(SOURCE/'charging-dock/ChargingDock.FCStd')==dock_report['native_sha256']
S=A.openDocument(str(SOURCE/'ManufacturingLayout.FCStd'))
C=A.openDocument(str(SOURCE/'charging-dock/ChargingDock.FCStd'))
D=A.newDocument('EVT1Product');D.Label='EVT1 board and four-part product integration / engineering prototype'
groups={n:D.addObject('App::DocumentObjectGroup',n) for n in ('Construction','ProductParts','Electronics','Contacts','SoftGoods','References','MatingAllowances')}
roles={};boards={};components={};mates={};mounts={}
parts_path=ROOT/'hardware/pcb/evt1/parts-selection.json'
parts_sha=sha(parts_path) if parts_path.exists() else None
pack_path=ROOT/'hardware/pcb/evt1/pack-spec.json'
pack_spec=json.loads(pack_path.read_text()) if pack_path.exists() else None


def feat(name,shape,group):
    o=D.addObject('PartDesign::Feature',name);o.Shape=shape;groups[group].addObject(o);roles[name]=o
    assert shape.isValid(),name
    return o


def copy_label(doc,label,name,group):
    found=doc.getObjectsByLabel(label);assert len(found)==1,(label,len(found))
    return feat(name,found[0].Shape.copy(),group)


def box(name,bounds,group):
    x,y,z,a,b,c=bounds
    assert min(a-x,b-y,c-z)>0,(name,bounds)
    o=D.addObject('Part::Box',name);o.Length=a-x;o.Width=b-y;o.Height=c-z;o.Placement.Base=A.Vector(x,y,z);groups[group].addObject(o);roles[name]=o
    return o


def cyl(name,r,point,length,direction,group):
    o=D.addObject('Part::Cylinder',name);o.Radius=r;o.Height=length
    o.Placement=A.Placement(A.Vector(*point),A.Rotation(A.Vector(0,0,1),A.Vector(*direction)))
    groups[group].addObject(o);roles[name]=o;return o


def bounds(shape):
    b=shape.BoundBox;return [getattr(b,n) for n in ('XMin','YMin','ZMin','XMax','YMax','ZMax')]


def transform(domain,x,y,z):
    if domain=='body':return A.Vector(x,y+5,z-.5)
    if domain=='flange':return A.Vector(x+1.5,-18.8125-z,y+17.5125)
    return A.Vector(x+28,-11.3-z,5-y)


def pcb_box(domain,xy,zlo,zhi):
    x0,y0,x1,y1=xy
    points=[transform(domain,x,y,z) for x in (x0,x1) for y in (y0,y1) for z in (zlo,zhi)]
    return [min(getattr(p,c) for p in points) for c in ('x','y','z')]+[max(getattr(p,c) for p in points) for c in ('x','y','z')]


body=copy_label(S,'MetalBody','MetalBody','ProductParts')
cap=copy_label(S,'MotorThermistorCap','MotorThermistorCap','ProductParts')
traybase=copy_label(S,'FlangeTray','TraySource','Construction')
rear=copy_label(C,'FourContactRearHalf','RearHalf','ProductParts')
nut=copy_label(S,'ThinRearNut','RearNutReference','References')
pack_heads=[]
if pack_spec:
    copy_label(S,'UnselectedPackReference','PriorPackGauge','Construction')
    pack=box('PackSizeReference',pack_spec['product_maximum_body_bounds_mm'],'References')
    pack.Label=pack_spec['part_number']+' / requested supplier maximum envelope'
    growth=box('PackGrowthAllowance',pack_spec['product_growth_keepout_bounds_mm'],'Construction')
    power_connector=box('BatteryPowerConnector',pack_spec['lead_exit']['product_mated_connector_bounds_mm'],'References')
    power_connector.Label='JST ACH wire-to-wire battery disconnect / mated envelope allowance'
    for i,(start,end) in enumerate(pack_spec['external_thermistors']['product_head_axis_segments_mm']):
        direction=A.Vector(*end)-A.Vector(*start)
        head=cyl('PackNTC'+str(i),pack_spec['external_thermistors']['head_transition_OD_budget_mm']/2,start,direction.Length,(direction.x,direction.y,direction.z),'References')
        head.Label='Pack NTC'+str(i+1)+' / maximum head-transition envelope'
        pack_heads.append(head)
else:
    pack=copy_label(S,'UnselectedPackReference','PackSizeReference','References')
copy_label(S,'MotorReferenceFitTBD','PriorMotorGauge','Construction')
# Maximum published case26.3x11.1, seated on the actual metal stopY93.3.
# Full-diameter rear allowance conservatively reserves the6mm lead-exit
# projection in the manufacturer's drawing, without guessing terminal angles.
motor=cyl('MotorReference',5.55,(0,67,0),26.3,(0,1,0),'References')
motor_boot=cyl('MotorLeadExitAllowance',5.55,(0,61,0),6,(0,1,0),'References')
motor_boot.Label='Motor rear lead exit / requested full-diameter6mm allowance'
copy_label(S,'TipThermistorHeadReference','TipThermistor','References')
copy_label(S,'TipPottingProcessSpace','TipPottingSpace','SoftGoods')
copy_label(S,'CapFaceSealProcessSpace','CapFaceSealSpace','SoftGoods')
copy_label(C,'FourContactSkin','ContinuousSkin','SoftGoods')
for i in (0,1):copy_label(C,'BuriedSteelKeeper'+str(i),'SteelKeeper'+str(i),'Contacts')
for net in ('GND','USB_DM','USB_DP','DOCK_5V'):
    copy_label(C,'Target_'+net,'Contact_'+net,'Contacts')
    copy_label(C,'TargetNut_'+net,'ContactNut_'+net,'Contacts')
    copy_label(C,'TargetSeal_'+net,'ContactSeal_'+net,'SoftGoods')

# The two nonmagnetic micro screws retain the sensor on integral tray bosses.
# Pre-tap M1.4x0.3; pilots are not final thread surfaces. Board back Y=-10.8.
bosses=[];cores=[]
for i,x in enumerate((29.5,38.5)):
    bosses.append(cyl('SensorBoss'+str(i),2,(x,-9.55,3.5),1.25,(0,-1,0),'Construction'))
    cores.append(cyl('SensorPilot'+str(i),.55,(x,-10.85,3.5),2.25,(0,1,0),'Construction'))
    shaft=cyl('SensorScrewShaft'+str(i),.7,(x,-11.8,3.5),2.5,(0,1,0),'References')
    head=cyl('SensorScrewHead'+str(i),1.3,(x,-12.65,3.5),.85,(0,1,0),'References')
    mounts['SensorScrew'+str(i)]=[shaft.Name,head.Name]
blank=D.addObject('Part::MultiFuse','TrayWithSensorBosses');blank.Shapes=[traybase]+bosses;blank.Refine=True;groups['Construction'].addObject(blank)
holes=D.addObject('Part::MultiFuse','SensorPilotTools');holes.Shapes=cores;holes.Refine=True;groups['Construction'].addObject(holes)
tray=D.addObject('Part::Cut','FlangeTray');tray.Base=blank;tray.Tool=holes;tray.Refine=True;groups['ProductParts'].addObject(tray);roles['FlangeTray']=tray
D.recompute()

for domain in ('body','flange','sensor'):
    folder=ROOT/'hardware/pcb/evt1'/domain
    data=json.loads((folder/'mcad.json').read_text());assert sha(ROOT/data['board_file'])==data['board_sha256']
    if parts_sha:assert data['parts_selection_sha256']==parts_sha,(domain,'Parts selection changed after MCAD extraction')
    drc=json.loads((folder/'drc.json').read_text());assert not drc['violations'] and not drc['unconnected_items'],domain
    thickness=data['thickness_mm'];assert abs(thickness-1)<1e-8
    points=[transform(domain,x,y,-.5) for x,y in data['outline_xy_mm']]
    direction=transform(domain,0,0,.5)-transform(domain,0,0,-.5)
    shape=Part.Face(Part.makePolygon(points+points[:1])).extrude(direction)
    for hole in data['holes']:
        dx,dy=hole['drill_xy_mm'];assert abs(dx-dy)<1e-8,'Model noncircular hole explicitly'
        x,y=hole['xy_mm'];p=transform(domain,x,y,-.6)
        shape=shape.cut(Part.makeCylinder(dx/2,1.2,p,direction))
    board=feat(domain.title()+'PCB',shape,'Electronics');boards[domain]={'role':board.Name,'source':data['board_file'],'sha256':data['board_sha256']}
    for item in data['components']:
        h=item['height_budget_mm']
        if h<=0:continue
        zlo,zhi=(-.5-h,-.5) if item['back'] else (.5,.5+h)
        o=box(domain.title()+'_'+item['ref'],pcb_box(domain,item['fab_bounds_xy_mm'],zlo,zhi),'Electronics')
        components[o.Name]={'domain':domain,'ref':item['ref'],'height_budget_mm':h,'scope':item['scope']}
    # Nominal SH plug projection is separate from the selected component body.
    for ref in (('J3','J6') if domain=='body' else ('J7','J4') if domain=='flange' else ()):
        item=next(c for c in data['components'] if c['ref']==ref)
        sig=[p['xy_mm'] for p in data['pads'] if p['ref']==ref and p['number'] not in ('','MP')]
        mp=[p['xy_mm'] for p in data['pads'] if p['ref']==ref and p['number']=='MP']
        v=[sum(p[i] for p in mp)/len(mp)-sum(p[i] for p in sig)/len(sig) for i in (0,1)]
        ll=math.hypot(*v);v=[round(q/ll) for q in v];u=[-v[1],v[0]]
        bb=item['fab_bounds_xy_mm'];front=max(x*v[0]+y*v[1] for x in (bb[0],bb[2]) for y in (bb[1],bb[3]))
        center=sum((p[0]*u[0]+p[1]*u[1]) for p in sig)/len(sig);width=len(sig)+1
        pts=[[(front+lead)*v[j]+(center+side*width/2)*u[j] for j in (0,1)] for lead in (0,2.25) for side in (-1,1)]
        rect=[min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts)]
        h=item['height_budget_mm'];zlo,zhi=(-.5-h,-.5) if item['back'] else (.5,.5+h)
        o=box(domain.title()+'_'+ref+'_Mate',pcb_box(domain,rect,zlo,zhi),'MatingAllowances');mates[o.Name]={'domain':domain,'ref':ref,'scope':'2.25mm plug projection from JST6.25mm side-entry mated length minus4mm header length; not OEM whole plug/lead geometry','source':'https://www.jst-mfg.com/product/pdf/eng/eSH.pdf'}
    for item in data['mating_allowances']:
        c=next(c for c in data['components'] if c['ref']==item['ref'])
        o=box(domain.title()+'_'+item['ref']+'_Mate',pcb_box(domain,c['fab_bounds_xy_mm'],.5+c['height_budget_mm'],.5+item['height_from_F_surface_mm']),'MatingAllowances')
        mates[o.Name]={'domain':domain,'ref':item['ref'],'scope':item['scope']}

D.recompute()
# Insulating sleeve and two standard foam pads, without a rigid scaffold.
module=[roles['BodyPCB']]+[roles[n] for n,v in components.items() if v['domain']=='body']+[roles[n] for n,v in mates.items() if v['domain']=='body']
bb=[bounds(o.Shape) for o in module];b=[min(q[i] for q in bb) for i in range(3)]+[max(q[i] for q in bb) for i in range(3,6)]
outer=Part.makeBox(b[3]-b[0]+.5,b[4]-b[1]+.5,b[5]-b[2]+.5,A.Vector(b[0]-.25,b[1],b[2]-.25))
inside=Part.makeBox(b[3]-b[0],b[4]-b[1]+.7,b[5]-b[2],A.Vector(b[0],b[1]-.1,b[2]))
sleeve=outer.cut(inside)
# The enclosing rectangle otherwise extends empty upper corners into the
# narrowing bore at the rear edge. Relieve only the first1mm aboveZ4.5 and
# outsideX+/-9; the PCB edge and the lower J6 housing remain wrapped.
for x0 in (b[0]-.35,9):
    width=(-9-x0) if x0<0 else b[3]+.35-x0
    sleeve=sleeve.cut(Part.makeBox(width,1,10,A.Vector(x0,b[1],4.5)))
# Top-entry J5 leads leave through an actual window in the insulating wrap;
# a closed box around the mated header would trap the two wires.
j5=roles['Body_J5_Mate'].Shape.BoundBox
window=Part.makeBox(j5.XLength+.8,j5.YLength+.8,2,A.Vector(j5.XMin-.4,j5.YMin-.4,j5.ZMax-.1))
sleeve=sleeve.cut(window)
feat('BodyInsulatingSleeve',sleeve,'SoftGoods')
for sign in (-1,1):
    x0,x1=(b[3]+.25,12.25) if sign==1 else (-12.25,b[0]-.25)
    shape=Part.makeBox(x1-x0,10,3,A.Vector(x0,54,-1.5)).common(Part.makeCylinder(12.25,12,A.Vector(0,53,0),A.Vector(0,1,0)))
    feat('BodyFoam'+('R' if sign==1 else 'L'),shape,'SoftGoods')

def overlap(a,b):
    aa=a.BoundBox;bb=b.BoundBox
    if any(min(getattr(aa,c+'Max'),getattr(bb,c+'Max'))<=max(getattr(aa,c+'Min'),getattr(bb,c+'Min'))+1e-7 for c in 'XYZ'):return 0
    return a.common(b).Volume

hard=list(groups['ProductParts'].Group)+list(groups['Electronics'].Group)+list(groups['Contacts'].Group)+[nut,pack,motor,motor_boot,roles['TipThermistor']]+pack_heads+([power_connector] if pack_spec else [])
hits=[]
for a,b in itertools.combinations(hard,2):
    amount=overlap(a.Shape,b.Shape)
    if amount>1e-4:hits.append({'a':a.Name,'b':b.Name,'intersection_mm3':amount})
mate_hits=[]
for name,item in mates.items():
    for o in hard:
        if o.Name==item['domain'].title()+'_'+item['ref']:continue
        amount=overlap(roles[name].Shape,o.Shape)
        if amount>1e-4:mate_hits.append({'mate':name,'target':o.Name,'intersection_mm3':amount})
native=OUT/'EVT1Product.FCStd';D.saveAs(str(native))
# Save an uncluttered initial view without changing document geometry. The
# FreeCAD headless runtime does not provide ViewObjects.
with zipfile.ZipFile(native) as archive:
    payload=[(i,archive.read(i)) for i in archive.infolist()]
    xml=ET.fromstring(archive.read('Document.xml'))
names=[o.get('name') for o in xml.findall('Objects/Object')]
visible={'ProductParts'}|{o.Name for o in groups['ProductParts'].Group}
gui=ET.Element('Document',SchemaVersion='1',HasExpansion='1')
ET.SubElement(gui,'Expand',count='0')
providers=ET.SubElement(gui,'ViewProviderData',Count=str(len(names)))
for rank,name in enumerate(names):
    provider=ET.SubElement(providers,'ViewProvider',name=name,expanded='0',treeRank=str(rank))
    props=ET.SubElement(provider,'Properties',Count='1',TransientCount='0')
    prop=ET.SubElement(props,'Property',name='Visibility',type='App::PropertyBool',status='1')
    ET.SubElement(prop,'Bool',value='true' if name in visible else 'false')
pending=native.with_suffix('.view-tmp')
with zipfile.ZipFile(pending,'w',compression=zipfile.ZIP_DEFLATED) as archive:
    for info,blob in payload:
        if info.filename!='GuiDocument.xml':archive.writestr(info,blob)
    archive.writestr('GuiDocument.xml',ET.tostring(gui,encoding='utf-8',xml_declaration=True))
with zipfile.ZipFile(pending) as archive:
    assert all(archive.read(i.filename)==blob for i,blob in payload if i.filename!='GuiDocument.xml')
pending.replace(native)
exports={}
for o in list(groups['ProductParts'].Group)+list(groups['Electronics'].Group)+list(groups['Contacts'].Group)+list(groups['SoftGoods'].Group)+list(groups['References'].Group)+list(groups['MatingAllowances'].Group):
    if not hasattr(o,'Shape') or o.Shape.isNull():continue
    view=OUT/(o.Name+'-view.stl')
    mesh=MeshPart.meshFromShape(Shape=o.Shape,LinearDeflection=.06,AngularDeflection=.2,Relative=False)
    assert mesh.isSolid(),o.Name
    mesh.write(str(view));exports[o.Name]={'view_STL_sha256':sha(view)}
for o in groups['ProductParts'].Group:
    assert o.Shape.isValid() and len(o.Shape.Solids)==1,o.Name
    step=OUT/(o.Name+'.step');o.Shape.exportStep(str(step));exports[o.Name]['STEP_sha256']=sha(step)
    if o.Name in ('FlangeTray','RearHalf'):
        shape=o.Shape.copy()
        shape.rotate(A.Vector(),A.Vector(1,0,0),-90 if o.Name=='FlangeTray' else 90)
        bb=shape.BoundBox;shape.translate(A.Vector(-bb.XMin,-bb.YMin,-bb.ZMin))
        path=OUT/(o.Name+'.stl')
        mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.04,AngularDeflection=.2,Relative=False)
        assert mesh.isSolid();mesh.write(str(path));exports[o.Name]['print_STL_sha256']=sha(path)
result={'scope':'Nominal actual-board integration; material/process/physical validation pending','native_sha256':sha(native),'builder_sha256':sha(Path(__file__)),
        'parts_selection_sha256':parts_sha,
        'pack_spec_sha256':sha(pack_path) if pack_spec else None,
        'battery_interface':{'part':pack_spec['part_number'],'status':pack_spec['status'],'growth_role':'PackGrowthAllowance','thermistor_roles':[o.Name for o in pack_heads],'power_connector_role':power_connector.Name,'scope':'Requested protected-pack/NTC and mated ACH power-disconnect envelopes; no supplied or validated battery assembly'} if pack_spec else None,
        'source_manufacturing_sha256':source_report['native_sha256'],'source_dock_sha256':dock_report['native_sha256'],
        'board_frames':{'body':'(x,y,z)_PCB to product(x,y+5,z-0.5)','flange':'(x+1.5,-18.8125-z,y+17.5125)','sensor':'(x+28,-11.3-z,5-y)'},
        'motor_interface':{'case_maximum_OD_length_mm':[11.1,26.3],'case_front_stop_Y_mm':93.3,'lead_exit_allowance_role':motor_boot.Name,'lead_exit_allowance_OD_length_mm':[11.1,6],
            'source':'https://nfpshop.com/wp-content/uploads/2022/04/Encapsulated-Vibration-Motor-NFP-E1015-3.7V.pdf',
            'scope':'Case/drawing6MAX lead projection reserved. Lead bundle width/angle/gauge are supplier/received-part acceptance; full-diameter allowance is a proposed conservative bound. Actual bore/retention/fit remains unqualified.'},
        'boards':boards,'components':components,'mating_allowances':mates,'sensor_screw_refs':mounts,
        'sensor_mount':{'PCB_back_Y_mm':-10.8,'PCB_F_Y_mm':-11.8,'pilot_diameter_mm':1.1,'pilot_depth_mm':2.2,'front_web_mm':.6,'tap':'M1.4x0.3, full thread >=1.5mm','screw':'NBK SPA-M1.4-2.5-MC3 RENY; head envelope2.6x0.85mm','manufacturer_nominal':{'thread':'M1.4x0.3','length_mm':2.5,'head_diameter_mm':2.5,'head_height_mm':.8,'bit':'SKCHB-M1.4','source':'https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/highintensity/SPA-MC3/SPA-M1.4-MC3/SPA-M1.4-2.5-MC3/'},'qualification':'Pilot/tap process, strip/torque and received screw dimensions need trial; manufacturer screw torsional strength is not a boss torque allowance'},
        'exports':exports,'native_roles':{n:o.Name for n,o in roles.items()},
        'main_custom_rigid_parts':[o.Name for o in groups['ProductParts'].Group],
        'bounds':{n:bounds(o.Shape) for n,o in roles.items() if hasattr(o,'Shape') and not o.Shape.isNull()},
        'hard_part_intersections':hits,'mating_intersections':mate_hits,'full_product_order_ready':False}
(OUT/'review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'native':str(native),'hard_intersections':hits,'mate_intersections':mate_hits},indent=2),flush=True)
