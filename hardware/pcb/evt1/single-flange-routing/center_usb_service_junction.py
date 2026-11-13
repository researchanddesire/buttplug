"""Center exactly two authored F USB segments on their existing J4 branch via."""
from pathlib import Path
import hashlib,json
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;P=H/'single-flange.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=json.loads((H/'pcb-state.json').read_text());before=sha(P);assert before==m['board_sha256']=='d344f42357925f58d8d2a9048c8f8701878e92476a291d085fdffc5dda7b3c49'
pro=H/'single-flange.kicad_pro';pb=pro.read_bytes();b=k.LoadBoard(str(P));tracks={t.m_Uuid.AsString():t for t in b.GetTracks()};via=tracks['2df51ba1-fb02-49d5-aa5e-6bf426223908'];assert isinstance(via,k.PCB_VIA)and via.GetNetname()=='USB_DM'and via.GetPosition()==k.VECTOR2I(73200000,105000000)
ids={'42384b31-44ce-4bc9-b64f-03a1347081af','4af73313-580f-4875-a2d5-23459a532752'};old=k.VECTOR2I(73200000,104800000);changes=[]
for u in ids:
 t=tracks[u];assert t.IsLocked()and t.GetLayer()==k.F_Cu and t.GetNetname()=='USB_DM'and t.GetWidth()==150000
 if t.GetStart()==old:changes.append({'uuid':u,'endpoint':'start','old_product_XZ_mm':[-26.8,-4.8],'new_product_XZ_mm':[-26.8,-5]});t.SetStart(via.GetPosition())
 else:assert t.GetEnd()==old;changes.append({'uuid':u,'endpoint':'end','old_product_XZ_mm':[-26.8,-4.8],'new_product_XZ_mm':[-26.8,-5]});t.SetEnd(via.GetPosition())
for z in b.Zones():
 if not z.GetIsRuleArea():z.UnFill()
k.SaveBoard(str(P),b);pro.write_bytes(pb);m['board_sha256']=sha(P);(H/'pcb-state.json').write_text(json.dumps(m,indent=2)+'\n');p=H/'critical-copper.json';r=json.loads(p.read_text())
for q in r['objects']:
 if q['uuid']in ids:
  for endpoint in('start','end'):
   if q[endpoint]==[-26.8,-4.8]:q[endpoint]=[-26.8,-5]
r['board_sha256']=sha(P);p.write_text(json.dumps(r,indent=2)+'\n');(H/'routing/usb-service-via-centering.json').write_text(json.dumps({'input_board_sha256':before,'board_sha256':sha(P),'reason':'Explicitly enabled KiCad10 endpoint-centering diagnostic found the former joint0.2mm from an existing mid-track branch via. Center this joint on that via; preserve every terminal, branch and via.','changes':changes,'existing_via_preserved':'2df51ba1-fb02-49d5-aa5e-6bf426223908','component_or_outline_geometry_changed':False,'native_full_DRC_required':True},indent=2)+'\n');print('Centered exact two segment ends; branch via and all other objects preserved')
