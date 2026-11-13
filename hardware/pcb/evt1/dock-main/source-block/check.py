"""Independent saved-native pad/copper/connectivity audit; never saves a PCB."""
from pathlib import Path
import collections,hashlib,json,math,xml.etree.ElementTree as ET
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;EVT=H.parents[1];SRC=EVT/'dock-ui'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
mm=lambda n:round(k.ToMM(n),6)
def xy(p):return [round(k.ToMM(p.x)-100,6),round(200-k.ToMM(p.y),6)]
def pair(p):return [mm(p.x),mm(p.y)]
def geometry(p,angle=0):
 return [p.GetNumber(),int(p.GetShape()),pair(p.GetPos0()),pair(p.GetSize()),
         pair(p.GetDrillSize()),round((p.GetOrientationDegrees()-angle)%360,6),
         [int(p.IsOnLayer(x))for x in (k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu)]]
def main():
 path=H/'source-block.kicad_pcb';before=sha(path);m=json.loads((H/'placement.json').read_text())
 assert before==m['board_sha256']
 for rel,d in m['source_sha256_relative_evt1'].items():assert sha(EVT/rel)==d,('stale source',rel)
 b=k.LoadBoard(str(path));assert b;b.BuildConnectivity();con=b.GetConnectivity()
 assert b.GetCopperLayerCount()==4 and abs(mm(b.GetDesignSettings().GetBoardThickness())-1)<1e-8
 xml=ET.parse(SRC/'source-native.xml').getroot();nets={}
 for n in xml.findall('./nets/net'):
  for p in n.findall('node'):nets[p.get('ref'),p.get('pin')]=n.get('name')
 expected={c.get('ref'):c for c in xml.findall('./components/comp')}
 fps={f.GetReference():f for f in b.GetFootprints()}
 assert set(fps)==set(expected)|set(m['mechanical_hole_refs'])
 assert len(expected)==48;out=[];padmap={};pad_identity={}
 for r,c in sorted(expected.items()):
  fp=fps[r];assert fp.IsLocked();lib=c.findtext('footprint')
  assert str(fp.GetFPID().GetLibNickname())+':'+str(fp.GetFPID().GetLibItemName())==lib
  assert fp.GetValue()==c.findtext('value')
  got=xy(fp.GetPosition())+[round(fp.GetOrientationDegrees(),6)]
  assert got==m['footprint_placements_dock_xy_native_angle'][r],(r,got)
  # Compare every pad/drill against the untouched source library, including
  # duplicate USB pad numbers and locating holes. Cosmetic graphics may differ.
  original=k.FootprintLoad(str(SRC/'DockUI.pretty'),lib.split(':')[1]);assert original
  actual_geo=sorted([geometry(p,fp.GetOrientationDegrees())for p in fp.Pads()])
  source_geo=sorted([geometry(p)for p in original.Pads()])
  assert actual_geo==source_geo,('pad geometry changed',r,actual_geo,source_geo)
  pads=[]
  for p in fp.Pads():
   number=p.GetNumber();assert p.GetNetname()==nets.get((r,number),''),(r,number,p.GetNetname())
   if number:padmap[r,number]=p
   pad_identity[p.m_Uuid.AsString()]=(r,number)
   pads.append({'number':number,'net':p.GetNetname(),'dock_xy_mm':xy(p.GetPosition()),'geometry':geometry(p,fp.GetOrientationDegrees())})
  out.append({'ref':r,'value':fp.GetValue(),'selected_source_footprint':lib,'dock_xy_native_angle':got,'pads':pads})
 mounts=[]
 for r,want in zip(m['mechanical_hole_refs'],m['existing_shell_mounts']['dock_xy_mm']):
  f=fps[r];assert xy(f.GetPosition())==want and f.IsLocked();p=list(f.Pads())[0]
  assert p.GetAttribute()==k.PAD_ATTRIB_NPTH and pair(p.GetDrillSize())==[2.3,2.3]
  assert p.IsOnLayer(k.F_Mask) and p.IsOnLayer(k.B_Mask)
  mounts.append({'ref':r,'dock_xy_mm':want,'NPTH_mm':2.3,'hardware_radius_mm':3})
 def canonical(rec):
  if rec['kind']=='via':return ('via',rec['net'],tuple(round(x,6)for x in rec['position']),round(rec['diameter'],6),round(rec['drill'],6))
  points=sorted([tuple(round(x,6)for x in rec['start']),tuple(round(x,6)for x in rec['end'])])
  return ('track',rec['net'],rec['layer'],tuple(points),round(rec['width'],6))
 copper=[]
 for t in b.GetTracks():
  assert t.IsLocked(),('unlocked critical copper',t.m_Uuid.AsString())
  if isinstance(t,k.PCB_VIA):rec={'kind':'via','net':t.GetNetname(),'position':xy(t.GetPosition()),'diameter':mm(t.GetWidth()),'drill':mm(t.GetDrillValue())}
  else:rec={'kind':'track','net':t.GetNetname(),'layer':k.LayerName(t.GetLayer()),'start':xy(t.GetStart()),'end':xy(t.GetEnd()),'width':mm(t.GetWidth())}
  copper.append(rec)
 got=collections.Counter(map(canonical,copper));want=collections.Counter(map(canonical,m['critical_copper']))
 assert got==want,('critical copper mismatch',list((got-want).items())[:5],list((want-got).items())[:5])
 # Traverse actual native copper contacts. A matching net label alone does
 # not establish that its terminals have a physical routed connection.
 def cluster(seed):
  todo=[seed];seen=set();pads=set()
  while todo:
   t=todo.pop();ident=t.m_Uuid.AsString()
   if ident in seen:continue
   seen.add(ident)
   if isinstance(t,k.PAD):pads.add(pad_identity[ident])
   todo.extend(con.GetConnectedTracks(t));todo.extend(con.GetConnectedPads(t))
  return pads
 groups={
 'USB_DP':[('J101','A6'),('J101','B6'),('U121','3'),('U121','4'),('J102','3')],
 'USB_DM':[('J101','A7'),('J101','B7'),('U121','1'),('U121','6'),('J102','2')],
 'CC1':[('J101','A5'),('U103','1')], 'CC2':[('J101','B5'),('U103','2')],
 'HOST critical path':[('J101','A4'),('J101','A9'),('J101','B4'),('J101','B9'),('U104','A1'),('U104','B1'),('C102','1'),('U105','1'),('C103','1')],
 'CONTACT_5V':[('U104','B2'),('C106','1'),('J102','4')],
 'UV_5V_LIMITED':[('U105','6'),('C107','1'),('J103','2')],
 'DEVICE_ILIM':[('U104','C2'),('R105','1'),('R106','1')],
 'DEVICE_FAULTn':[('U104','A2'),('R123','2')],
 'CC local3V3':[('U103','12'),('C108','1')],
 'LDO local input':[('U102','1'),('U102','3'),('C101','1')],
 'LDO local output':[('U102','5'),('C105','1')],
 }
 physical=[]
 for name,terminals in groups.items():
  reached=cluster(padmap[terminals[0]]);assert set(terminals)<=reached,('physical open',name,set(terminals)-reached)
  physical.append({'name':name,'terminals':[list(t)for t in terminals],'native_physical_copper_connected':True})
 # A true continuous reference is present, but refill on the final merged
 # board is mandatory. Keepouts and NPTHs clip the actual saved plane.
 planes=[z for z in b.Zones()if not z.GetIsRuleArea()]
 assert len(planes)==1 and planes[0].IsOnLayer(k.In1_Cu) and planes[0].GetNetname()=='GND'
 assert not any(planes[0].IsOnLayer(x)for x in (k.F_Cu,k.In2_Cu,k.B_Cu))
 drc=json.loads((H/'drc.json').read_text());assert not drc['violations']
 pro=json.loads((H/'source-block.kicad_pro').read_text());assert not pro['board']['design_settings']['drc_exclusions']
 assert before==sha(path),'Read-only checker changed board'
 result={'status':'PASS: native saved source-block pad geometry/net parity and critical copper connectivity',
 'KiCad_Python':k.Version(),'board_sha256':before,'source_xml_sha256':sha(SRC/'source-native.xml'),
 'source_refs':48,'mechanical_refs':4,'source_pad_instances':sum(len(x['pads'])for x in out),
 'critical_track_via_count':len(copper),'all_critical_copper_locked':True,'native_physical_connections':physical,
 'DRC_native_version':drc['kicad_version'],'DRC_geometry_violations':0,'DRC_unconnected_groups':len(drc['unconnected_items']),
 'DRC_exclusions':0,'pad_records':out,'mechanical_mounts':mounts,
 'drawing_only_derivations':{'J101':'two outside-board silk ends shortened3.25→2.475mm; pads/drills/fab unchanged',
 'J102':'manual copper-land courtyard reduced to1.0mm boundary; pads/drills/fab unchanged'},
 'open':'73 remaining connectivity groups include internal control/supply and intersheet endpoints; merged routing required, not fabrication',
 'source_sha256_relative_evt1':m['source_sha256_relative_evt1'],
 'local_input_sha256':{p.name:sha(p)for p in [H/'build.py',H/'fill.py',H/'check.py',H/'placement.json',H/'source-block.kicad_pro',H/'fp-lib-table',H/'drc.json']},
 'derived_library_sha256':{p.name:sha(p)for p in sorted((H/'SourceBlock.pretty').glob('*.kicad_mod'))},
 'flashed_or_powered':False,'physical_fit_qualified':False,'full_product_order_ready':False}
 (H/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({k:result[k]for k in ['status','source_refs','mechanical_refs','source_pad_instances','critical_track_via_count','DRC_geometry_violations','DRC_unconnected_groups']}))
if __name__=='__main__':main()
