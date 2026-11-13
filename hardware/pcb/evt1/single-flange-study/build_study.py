"""Native, unrouted single-flange study; immutable routed device sources."""
from pathlib import Path
import hashlib,json,math,sys,xml.etree.ElementTree as ET,shutil
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;E=H.parent;ROOT=H.parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import kicad_sexp as s
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def xy(x,z):return k.VECTOR2I(round((100+x)*1e6),round((100-z)*1e6))
# Final native angles are measured AFTER the explicit B-side flip.
P={
'U6':[-30,0,90,'B'],'SW1':[-17,0,0,'F'],'SW2':[-9,0,0,'F'],
'J7':[-7,0,90,'B'],'J4':[-15.5,-8,180,'B'],
'C31':[-32.4,9,-90,'B'],'C32':[-29.9,9,-90,'B'],'C33':[-18,-4,0,'B'],'C34':[12,-4,90,'B'],
'R31':[-18,5,0,'B'],'R32':[-15,5,0,'B'],'R33':[-12,5,0,'B'],
'R34':[-18,2,0,'B'],'R35':[-15,2,0,'B'],'R36':[-12,2,0,'B'],
'R37':[-18,-1,0,'B'],'R38':[-15,-1,0,'B'],'R39':[13,5,0,'B'],'R40':[13,2,0,'B'],
'R75':[-18.8,3.5,-180,'B'],'R76':[-18.8,6.5,-180,'B'],
'U75':[-1,4,0,'B'],'F1':[4,5,0,'B'],'D1':[9,5,0,'B'],
'D71':[7,-6,0,'B'],'D72':[4,0,0,'B'],'D73':[4,-3,0,'B'],
'R71':[2,-7,0,'B'],'U71':[-1,-6,0,'B'],'C71':[-1,-9,0,'B'],
'U81':[33,0,0,'B'],'C81':[33,3,0,'B'],'C82':[36,0,0,'B'],
'C83':[30,0,90,'B'],'C84':[36,-3,0,'B']}
CONTACTS={'CT1':(-16,10,'GND'),'CT2':(-10,10,'USB_DM_CONTACT'),'CT3':(-4,10,'USB_DP_CONTACT'),'CT4':(2,10,'DOCK_5V')}

def libraries():
 out={};prov={};models={};(H/'Selected.pretty').mkdir(exist_ok=True);(H/'Selected.3dshapes').mkdir(exist_ok=True)
 parts=json.loads((E/'parts-selection.json').read_text())['components']
 for domain in ('flange','sensor'):
  owner=E/domain;table=s.parse((owner/'fp-lib-table').read_text());libs={s.value(a,'name'):Path(s.value(a,'uri').replace('${KIPRJMOD}',str(owner))).resolve()for a in s.children(table,'lib')}
  for part in parts:
   ref=part['ref']
   if part['domain']!=domain or ref not in P:continue
   alias,name=part['footprint'].split(':');source=libs[alias]/(name+'.kicad_mod');t=s.parse(source.read_text())
   # No assembly silk is claimed in this placement-only study; keep all Fab,
   # courtyard, pad/drill and keepout geometry unchanged.
   t[:]=[v for v in t if not(isinstance(v,list)and v and getattr(v[0],'value',None)in('fp_line','fp_rect','fp_circle','fp_arc','fp_poly','fp_text')and s.value(v,'layer')in('F.SilkS','B.SilkS'))]
   if not s.children(t,'model')and ref[0]in('R','C'):
    size='0805_2012'if '0805'in name or 'GRM21'in name else'0603_1608'
    folder='Resistor_SMD'if ref[0]=='R'else'Capacitor_SMD';fname=ref[0]+'_'+size+'Metric.step'
    t.append(s.parse('(model "${KICAD6_3DMODEL_DIR}/'+folder+'.3dshapes/'+fname+'"(offset(xyz 0 0 0))(scale(xyz 1 1 1))(rotate(xyz 0 0 0)))'))
   for model in s.children(t,'model'):
    uri=model[1].value
    if '${KICAD6_3DMODEL_DIR}'in uri:
     src=Path(uri.replace('${KICAD6_3DMODEL_DIR}','/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels')).with_suffix('.step')
     dst=H/'Selected.3dshapes'/src.name
     if src.exists():shutil.copyfile(src,dst)
     else:
      downloads=json.loads((H/'downloaded-models.json').read_text());assert dst.exists()and sha(dst)==downloads[src.name]['sha256'],src
     model[1]=s.string('${KIPRJMOD}/Selected.3dshapes/'+dst.name)
     models[dst.name]={'source':str(src)if src.exists()else downloads[src.name]['source'],'sha256':sha(dst),'classification':'KiCad selected package-family nominal STEP; not OEM exact-MPN or received-part qualification'}
   if ref=='U6':
    src=Path('/private/tmp/ESP32-C3-MINI-1-OEM.STEP');assert sha(src)=='a4ed075447476cb39cbee4f5889f163ff8abae111efcf27c3559b8dafa1085aa'
    dst=H/'Selected.3dshapes/ESP32-C3-MINI-1-OEM.step';shutil.copyfile(src,dst)
    t.append(s.parse('(model "${KIPRJMOD}/Selected.3dshapes/ESP32-C3-MINI-1-OEM.step"(offset(xyz -6.6 -5.6 0))(scale(xyz 1 1 1))(rotate(xyz 0 0 0)))'))
    models[dst.name]={'source':'https://www.espressif.com/sites/default/files/3dmodel/ESP32-C3-MINI-1%203D%20Model.STEP','primary_landing_page':'https://www.espressif.com/en/module/esp32-c3-mini-1-en','sha256':sha(src),'classification':'manufacturer OEM selected MINI-1 geometry; received N4X tolerance verification remains open','footprint_model_offset_xyz_mm':[-6.6,-5.6,0]}
   dest=H/'Selected.pretty'/(name+'.kicad_mod');s.write(dest,t)
   prov[ref]={'domain':domain,'source_footprint':str(source.relative_to(ROOT)),'source_sha256':sha(source),'local':str(dest.relative_to(H)),'local_sha256':sha(dest),'part':part}
   out[ref]=(name,part)
 # New selected TH fixed target. Drill from exact-part manufacturer sheet;
 # annulus is a study choice, NOT an OEM recommended land-pattern claim.
 target='''(footprint "MillMax_1946_0_PTH_Study"(version 20221018)(generator pcbnew)(layer "F.Cu")(descr "1946-0-00-15-00-00-03-0; OEM .034in recommended mounting hole; 3.2mm pad is engineering trial choice, no accepted annulus")(attr through_hole)
(fp_text reference "CT?"(at 0 -2.5)(layer "F.SilkS")(effects(font(size .7 .7)(thickness .12))))
(fp_text value "1946-0-00-15-00-00-03-0"(at 0 2.5)(layer "F.Fab")(effects(font(size .5 .5)(thickness .1))))
(fp_circle(center 0 0)(end 1.5875 0)(layer "F.Fab")(width .05)(fill none))
(fp_circle(center 0 0)(end 1.85 0)(layer "F.CrtYd")(width .05)(fill none))(fp_circle(center 0 0)(end 2 0)(layer "B.CrtYd")(width .05)(fill none))
(pad "1" thru_hole circle(at 0 0)(size 3.2 3.2)(drill .8636)(layers "*.Cu" "*.Mask"))(model "${KIPRJMOD}/Selected.3dshapes/MillMax1946.step"(offset(xyz 0 0 0))(scale(xyz 1 1 1))(rotate(xyz 0 0 0))))'''
 contact=ROOT/'hardware/cad/manufacturing-layout/evt1-integration/contact-module-trial/single-board/models/MillMax1946.step'
 shutil.copyfile(contact,H/'Selected.3dshapes/MillMax1946.step')
 (H/'Selected.pretty/MillMax_1946_0_PTH_Study.kicad_mod').write_text(target+'\n')
 s.write(H/'fp-lib-table',s.parse('(fp_lib_table (version 7) (lib (name "Selected") (type "KiCad") (uri "${KIPRJMOD}/Selected.pretty") (options "") (descr "Source-bound selected device footprints and explicit new fixed-contact trial")))'))
 existing=json.loads((H/'footprint-provenance.json').read_text())if(H/'footprint-provenance.json').exists()else{}
 target_proof=existing.get('new_fixed_target',{});target_proof.update({'MPN':'1946-0-00-15-00-00-03-0','model_sha256':sha(contact),'actual_model_source':str(contact.relative_to(ROOT))})
 (H/'footprint-provenance.json').write_text(json.dumps({'selected_source_footprints':prov,'local_nominal_models':models,'new_fixed_target':target_proof,'no_source_board_changes':True},indent=2)+'\n')
 return out

def edge(b,a,c):
 e=k.PCB_SHAPE(b);e.SetShape(k.SHAPE_T_SEGMENT);e.SetStart(xy(*a));e.SetEnd(xy(*c));e.SetWidth(k.FromMM(.05));e.SetLayer(k.Edge_Cuts);b.Add(e)
def loop(b,points):
 for a,c in zip(points,points[1:]+points[:1]):edge(b,a,c)
def outline():
 #82x26 R3 outer perimeter, with an OPEN left-edge antenna notch.
 # Polyline arcs sampled5deg; this is editable study artwork, no fab export.
 pts=[]
 for cx,cz,start in [(38,-10,-90),(38,10,0),(-38,10,90),(-38,-10,180)]:
  for i in range(19):
   t=math.radians(start+5*i);pts.append([round(cx+3*math.cos(t),6),round(cz+3*math.sin(t),6)])
 # Replace the left-edge straight span with the open RF-board cutout.
 # Current clockwise path traverses(-41,+10)→(-41,-10).
 i=next(i for i,a in enumerate(pts)if a==[-41.0,10.0])
 j=next(j for j,a in enumerate(pts)if a==[-41.0,-10.0])
 pts=pts[:i+1]+[[-41,7.2],[-35.6,7.2],[-35.6,-7.2],[-41,-7.2]]+pts[j:]
 # Preserve the existing two case-closure screw axes with open R2 reliefs.
 top=next(i for i,a in enumerate(pts)if a==[38.0,13.0])
 relief=lambda z,angles:[[round(12+2*math.cos(math.radians(a)),6),round(z+2*math.sin(math.radians(a)),6)]for a in angles]
 pts=pts[:top+1]+relief(13,range(0,-181,-5))+pts[top+1:]
 pts+=relief(-13,range(180,-1,-5))
 return pts

def main():
 source=json.loads((H/'source-inventory.json').read_text())
 for path,h in source['source_sha256'].items():assert sha(E/path)==h,('immutable source changed',path)
 data=libraries();r=ET.parse(E/'system-native.xml').getroot();comps={c.get('ref'):c for c in r.findall('./components/comp')}
 b=k.BOARD();b.SetFileName(str(H/'single-flange-placement.kicad_pcb'));b.SetCopperLayerCount(4);ds=b.GetDesignSettings();ds.SetBoardThickness(k.FromMM(1));ds.m_MinClearance=k.FromMM(.15);ds.m_CopperEdgeClearance=k.FromMM(.3);ds.m_NetSettings.m_DefaultNetClass.SetClearance(k.FromMM(.15))
 nets={};padmap={}
 for n in r.findall('./nets/net'):
  name=n.get('name');b.Add(k.NETINFO_ITEM(b,name))
  for q in n.findall('node'):nets[q.get('ref'),q.get('pin')]=name
 placed=[]
 for ref,pos in P.items():
  print('Placing',ref,flush=True)
  name,part=data[ref];f=k.FootprintLoad(str(H/'Selected.pretty'),name);assert f;f.SetFPID(k.LIB_ID('Selected',name));f.SetReference(ref);f.SetValue(comps[ref].findtext('value'));f.SetPosition(xy(*pos[:2]));f.SetOrientationDegrees(pos[2]);b.Add(f)
  if pos[3]=='B':f.Flip(f.GetPosition(),False)
  f.SetLocked(True);f.Reference().SetVisible(False);f.Value().SetVisible(False)
  for p in f.Pads():
   if p.GetNumber():
    net=nets.get((ref,p.GetNumber()))
    if net:p.SetNet(b.FindNet(net));padmap[ref,p.GetNumber()]=p.GetNetname()
    else:assert p.GetNumber()=='MP',(ref,p.GetNumber());p.SetNetCode(0)
  placed.append({'ref':ref,'domain':part['domain'],'product_XZ_mm':pos[:2],'side':pos[3],'native_angle_deg':f.GetOrientationDegrees(),'selected_max_height_mm':part.get('maximum_height_mm'),'MPN':part.get('mpn')})
 for ref,(x,z,net)in CONTACTS.items():
  f=k.FootprintLoad(str(H/'Selected.pretty'),'MillMax_1946_0_PTH_Study');f.SetFPID(k.LIB_ID('Selected','MillMax_1946_0_PTH_Study'));f.SetReference(ref);f.SetValue('1946-0-00-15-00-00-03-0');f.SetPosition(xy(x,z));f.SetLocked(True);f.Reference().SetVisible(False);f.Value().SetVisible(False)
  list(f.Pads())[0].SetNet(b.FindNet(net));b.Add(f)
  placed.append({'ref':ref,'product_XZ_mm':[x,z],'side':'F','MPN':'1946-0-00-15-00-00-03-0','net':net,'selected_height_above_board_mm':3.048})
 for i,(x,z)in enumerate([(-30,-10),(-38,10),(38,-10),(38,10)],1):
  f=k.FOOTPRINT(b);f.SetReference('MH'+str(i));f.SetValue('PROVISIONAL M1.4 support');f.SetPosition(xy(x,z));f.SetLocked(True);f.Reference().SetVisible(False);f.Value().SetVisible(False)
  q=k.PAD(f);q.SetAttribute(k.PAD_ATTRIB_NPTH);q.SetShape(k.PAD_SHAPE_CIRCLE);q.SetSize(k.VECTOR2I(1600000,1600000));q.SetDrillSize(k.VECTOR2I(1600000,1600000));layers=k.LSET.AllCuMask();layers.AddLayer(k.F_Mask);layers.AddLayer(k.B_Mask);q.SetLayerSet(layers);q.SetPosition(f.GetPosition());f.Add(q)
  for layer in(k.F_CrtYd,k.B_CrtYd):
   c=k.PCB_SHAPE(f);c.SetShape(k.SHAPE_T_CIRCLE);c.SetCenter(f.GetPosition());c.SetEnd(xy(x+1.75,z));c.SetWidth(50000);c.SetLayer(layer);f.Add(c)
  b.Add(f)
 pts=outline();loop(b,pts)
 k.SaveBoard(str(H/'single-flange-placement.kicad_pcb'),b)
 project=H/'single-flange-placement.kicad_pro';settings=json.loads(project.read_text())
 for key,value in settings['board']['design_settings']['rule_severities'].items():
  if value=='ignore':settings['board']['design_settings']['rule_severities'][key]='error'
 settings['board']['design_settings']['drc_exclusions']=[];project.write_text(json.dumps(settings,indent=2)+'\n')
 report={'status':'unrouted source-bound placement STUDY; no physical fit/RF/seal/fabrication qualification','board_sha256':sha(H/'single-flange-placement.kicad_pcb'),'frame':'nativePCB(x,y)=(100+productX,100-productZ); Fnormal=-productY; FsurfaceY=-26.952; BsurfaceY=-25.952','board_thickness_mm':1,'board_F_productY_mm':-26.952,'board_B_productY_mm':-25.952,'outer_envelope_XZ_mm':[82,26],'outline_product_XZ_mm':pts,'electrical_positions':placed,'physical_source_pad_instances':sum(bool(q.GetNumber())and q.GetNumber()!='MP'for f in b.GetFootprints()if f.GetReference()in P for q in f.Pads()),'unique_logical_source_pad_numbers':len(padmap),'source_reference_count':len(P),'new_contact_count':4,'removed_from_merged_layout':{'J1':'four handwire contact lands replaced by four selected TH targets, same nets/order','J82':'sensor-only interboard lands redundant after direct I2C/3V3/GND merge; existing bodyJ81 artwork unchanged'},'retained_body_interface':'J7 physical numeric1:1 to existing unmodified bodyJ6','body_PCB_unchanged':True,'source_inventory_sha256':sha(H/'source-inventory.json'),'no_tracks_or_vias':True,'assembly_or_RF_acceptance':False}
 (H/'placement.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in ('status','source_reference_count','new_contact_count','physical_source_pad_instances','board_sha256')}))
if __name__=='__main__':main()
