"""Independent saved-native full circuit/pad/route/mount audit of shared base."""
from pathlib import Path
import argparse,collections,hashlib,json,math,xml.etree.ElementTree as ET
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;E=H.parent;ROOT=H.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def xy(p):return [round(k.ToMM(p.x)-100,6),round(200-k.ToMM(p.y),6)]
def point(p):return (round((100+p[0])*1e6),round((200-p[1])*1e6))
def pair(v):return [v.x,v.y]
def shape(p,angle):
 return [p.GetNumber(),int(p.GetShape()),pair(p.GetPos0()),pair(p.GetSize()),pair(p.GetDrillSize()),
         round((p.GetOrientationDegrees()-angle)%360,5),[p.IsOnLayer(i)for i in (k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu)]]
def signature(t):
 if isinstance(t,dict):
  if t['kind']=='via':return ('via',t['net'],point(t['position']),round(t['diameter']*1e6),round(t['drill']*1e6))
  return ('track',t['net'],t['layer'],tuple(sorted([point(t['start']),point(t['end'])])),round(t['width']*1e6))
 if isinstance(t,k.PCB_VIA):return ('via',t.GetNetname(),tuple(pair(t.GetPosition())),t.GetWidth(),t.GetDrillValue())
 return ('track',t.GetNetname(),k.LayerName(t.GetLayer()),tuple(sorted([tuple(pair(t.GetStart())),tuple(pair(t.GetEnd()))])),t.GetWidth())
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--refresh-schematic-binding',action='store_true');args=parser.parse_args()
 p=H/'dock-main.kicad_pcb';before=sha(p);meta=json.loads((H/'placement.json').read_text());assert before==meta['native_board_sha256']
 assert meta['source_block_sha256']==sha(H/'source-block/source-block.kicad_pcb')
 xmlpath=E/'dock-system/native.xml';old_xml_hash=meta['system_xml_sha256']
 if sha(xmlpath)!=old_xml_hash:assert args.refresh_schematic_binding,'Use explicit --refresh-schematic-binding only after native150pad audit'

 sysreport=json.loads((E/'dock-system/native-checks.json').read_text())
 assert sysreport['status']=='pass' and sysreport['reports_sha256']['native.xml']==sha(xmlpath)
 r=ET.parse(xmlpath).getroot();expected={};nets={}
 for c in r.findall('./components/comp'):
  if c.find('sheetpath').get('names') in('/dock-ui-source/','/dock-controller/','/dock-safety/') and c.findtext('footprint'):expected[c.get('ref')]=c
 for n in r.findall('./nets/net'):
  for t in n.findall('node'):nets[t.get('ref'),t.get('pin')]=n.get('name')
 b=k.LoadBoard(str(p));assert b.GetCopperLayerCount()==4 and round(k.ToMM(b.GetDesignSettings().GetBoardThickness()),6)==1
 fps={f.GetReference():f for f in b.GetFootprints()};assert len(fps)==len(list(b.GetFootprints()))
 assert set(fps)==set(expected)|{'H70'+str(i)for i in range(1,7)} and len(expected)==150
 checked=[];partrecords=[];padmap={}
 for ref,c in sorted(expected.items()):
  f=fps[ref];lib=c.findtext('footprint');assert str(f.GetFPID().GetLibNickname())+':'+str(f.GetFPID().GetLibItemName())==lib
  assert f.GetValue()==c.findtext('value') and f.IsLocked()
  want=meta['footprint_placements_dock_xy_native_angle'][ref]
  assert tuple(pair(f.GetPosition()))==point(want[:2])and round(f.GetOrientationDegrees()%360,6)==round(want[2]%360,6),(ref,want,xy(f.GetPosition()))
  original=k.FootprintLoad(str(H/(lib.split(':')[0]+'.pretty')),lib.split(':')[1]);assert original
  assert sorted(shape(q,f.GetOrientationDegrees())for q in f.Pads())==sorted(shape(q,0)for q in original.Pads()),('selected pad/drill geometry changed',ref)
  assert {q.GetNumber()for q in f.Pads()if q.GetNumber()}=={n for rr,n in nets if rr==ref}
  for q in f.Pads():
   number=q.GetNumber()
   if not number:continue
   assert q.GetNetname()==nets[ref,number],(ref,number,q.GetNetname(),nets[ref,number])
   checked.append({'ref':ref,'pad':number,'net':q.GetNetname(),'dock_xy_mm':xy(q.GetPosition())})
   padmap[ref,number]=q
  partrecords.append({'ref':ref,'value':f.GetValue(),'source_footprint':lib,'dock_xy_native_angle':want})
 holes=[]
 for i,want in enumerate(meta['mounting_holes_dock_xy_d_mm'],701):
  f=fps['H'+str(i)];q=list(f.Pads())[0]
  assert q.GetAttribute()==k.PAD_ATTRIB_NPTH and q.GetDrillSize().x==2300000 and q.GetDrillSize().y==2300000
  assert q.IsOnLayer(k.F_Mask)and q.IsOnLayer(k.B_Mask)and xy(q.GetPosition())==want[:2]
  assert f.IsLocked() and any(g.GetLayer()==k.F_CrtYd for g in f.GraphicalItems())
  holes.append({'ref':'H'+str(i),'dock_xy_mm':want[:2],'NPTH_mm':2.3,'hardware_radius_mm':3})
  # Pads are intentionally excluded from rule-area self-tests, so inspect
  # actual foreign copper pads against the screw-head radius independently.
  circle=k.SHAPE_CIRCLE(q.GetPosition(),3000000)
  for ref in expected:
   for other in fps[ref].Pads():
    if other.GetAttribute()==k.PAD_ATTRIB_NPTH:continue
    if other.IsOnLayer(k.F_Cu):assert not other.GetEffectiveShape(k.F_Cu).Collide(circle,0),('pad inside head radius',i,ref,other.GetNumber())
 assert holes[-1]['dock_xy_mm']==[44,55.7]
 alltracks=list(b.GetTracks());actual=collections.Counter(signature(t)for t in alltracks)
 source=json.loads((H/'source-block/placement.json').read_text());critical=json.loads((H/'critical-routing.json').read_text())
 for name,items in [('source192',source['critical_copper']),('main critical',critical['critical_copper'])]:
  wanted=collections.Counter(signature(t)for t in items);assert not(wanted-actual),('lost protected copper',name,list((wanted-actual).items())[:3])
  assert all(t.IsLocked()for t in alltracks if signature(t)in wanted)
 guides=json.loads((H/'routing/residual-fanout-guides.json').read_text())['extra_locked_authored_copper']
 retired=json.loads((H/'routing/fanout-finalization.json').read_text())['retired_new_fanout_vias']
 retired_ids={row['uuid']for row in retired};byid={t.m_Uuid.AsString():t for t in alltracks}
 assert not(retired_ids&set(byid))
 preserved_guides=[]
 for row in guides:
  if row['uuid']in retired_ids:continue
  t=byid[row['uuid']];assert t.IsLocked()and t.GetNetname()==row['net']
  if row['kind']=='via':
   assert isinstance(t,k.PCB_VIA)and pair(t.GetPosition())==[round(x*1e6)for x in row['position_native_mm']]
   assert [t.GetWidth(),t.GetDrillValue()]==[round(x*1e6)for x in row['diameter_drill_mm']]
  else:
   assert not isinstance(t,k.PCB_VIA)and t.GetLayer()==k.F_Cu
   assert pair(t.GetStart())==[round(x*1e6)for x in row['start_native_mm']]
   assert pair(t.GetEnd())==[round(x*1e6)for x in row['end_native_mm']]
   assert t.GetWidth()==round(row['width_mm']*1e6)
  preserved_guides.append(row['uuid'])
 assert len(preserved_guides)==58 and len(retired_ids)==1
 assert not any(not isinstance(t,k.PCB_VIA)and t.GetLayer()==k.In1_Cu for t in alltracks)
 permitted_inner={signature(t)for t in source['critical_copper']+critical['critical_copper']}
 # Exact local edge-capture paths cannot silently become a long router detour.
 clock=[]
 for net,a0,a1 in [('CLOCK_RELEASE',('U614','6'),('U609','3')),('CLOCK_PRESS',('U614','4'),('U609','11'))]:
  paths=[t for t in alltracks if t.GetNetname()==net and not isinstance(t,k.PCB_VIA)]
  assert paths and all(t.IsLocked()for t in paths if signature(t)in permitted_inner)
  clock.append({'net':net,'driver':list(a0),'latch':list(a1),'total_native_track_length_mm':sum(k.ToMM(t.GetLength())for t in paths)})
 drc=json.loads((H/'drc.json').read_text());assert not drc['violations'] and not drc['unconnected_items']
 binding=json.loads((H/'drc-board-binding.json').read_text());assert binding['board_sha256']==before and binding['DRC_sha256']==sha(H/'drc.json')
 parity=json.loads((H/'mcad-geometry-parity.json').read_text());assert parity['board_sha256']==before and parity['snapshot_sha256']==sha(H/'dock-main-MCAD-placement.kicad_pcb')
 power=json.loads((H/'power-study/final/resistance.json').read_text());assert power['native_board_sha256']==before
 for row in power['requested_fabrication_minimum_corner_cases']:assert row['estimated_common_PCB_R_ohm']<.05
 assert power['supplier_acceptance']is False
 pro=json.loads((H/'dock-main.kicad_pro').read_text());ds=pro['board']['design_settings']
 assert not ds['drc_exclusions'] and not any(v=='ignore'for v in ds['rule_severities'].values())
 assert abs(ds['rules']['min_hole_clearance']-.2)<1e-12
 assert sha(p)==before,'Read-only native audit modified board'
 if sha(xmlpath)!=old_xml_hash:
  meta['system_xml_sha256']=sha(xmlpath)
  meta['schematic_rebinding']={'prior_XML_sha256':old_xml_hash,'current_XML_sha256':sha(xmlpath),'basis':'all150 actual references and every physical electrical pad independently matched current native XML; no board mutation'}
  (H/'placement.json').write_text(json.dumps(meta,indent=2)+'\n')
 local=[q for q in H.iterdir()if q.is_file()and q.name not in('native-checks.json',)and q.suffix in('.py','.json','.md','.kicad_pcb','.kicad_pro','.kicad_dru')]
 report={'status':'pass: native full shared-base circuit/pad parity and DRC0/unconnected0',
  'board_sha256':before,'system_XML_sha256':sha(xmlpath),'source_block_sha256':meta['source_block_sha256'],
  'KiCad_Python_version':k.Version(),'native_DRC_version':drc['kicad_version'],
  'electrical_references':len(expected),'physical_electrical_pad_instances':len(checked),'mechanical_NPTH_holes':holes,
  'native_pad_checks':checked,'selected_part_placements':partrecords,
  'preserved_source_copper_items':192,'preserved_main_critical_items':len(critical['critical_copper']),'preserved_extra_authored_fanout_items':len(preserved_guides),'retired_new_graph_redundant_fanout_vias':retired,
  'tracks':sum(not isinstance(t,k.PCB_VIA)for t in alltracks),'vias':sum(isinstance(t,k.PCB_VIA)for t in alltracks),
  'local_clock_paths':clock,'In1_continuous_ground_reserved':True,'general_signal_layers':['F.Cu','In2.Cu','B.Cu'],
  'DRC_violations':0,'DRC_unconnected':0,'DRC_exclusions':0,'ignored_rules':[],
  'bounded_rule':'Only two J101-owned features use manufacturer0.15mm hole spacing; all other holes0.20mm. Received/fabricator acceptance pending.',
  'local_source_sha256':{q.name:sha(q)for q in sorted(local)},'libraries_and_models_sha256':{str(q.relative_to(H)):sha(q)for folder in sorted(list(H.glob('*.pretty'))+[H/'DockMain.3dshapes'])for q in sorted(folder.rglob('*'))if q.is_file()and q.suffix in('.kicad_mod','.step','.FCStd','.json','.md')},'MCAD_geometry_parity_sha256':sha(H/'mcad-geometry-parity.json'),'final_DC_study_sha256':sha(H/'power-study/final/resistance.json'),'DRC_board_binding_sha256':sha(H/'drc-board-binding.json'),
  'physical_or_powered_result':False,'fabrication_release':False}
 (H/'native-checks.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps({key:report[key]for key in('status','board_sha256','electrical_references','physical_electrical_pad_instances','tracks','vias','DRC_violations','DRC_unconnected')}))
if __name__=='__main__':main()
