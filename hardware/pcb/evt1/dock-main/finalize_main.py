"""Keep all copper while adding explicit mechanical courtyards/rule severities."""
from pathlib import Path
import hashlib,json
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;P=H/'dock-main.kicad_pcb'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads((H/'placement.json').read_text());assert sha(P)==meta['native_board_sha256']
b=k.LoadBoard(str(P));assert meta.get('general_routing_imported')
before=[t.m_Uuid.AsString()for t in b.GetTracks()]
for f in b.GetFootprints():
 if not f.GetReference().startswith('H70'):continue
 f.SetAttributes(k.FP_EXCLUDE_FROM_POS_FILES|k.FP_EXCLUDE_FROM_BOM)
 if not any(g.GetLayer()==k.F_CrtYd for g in f.GraphicalItems()):
  c=k.FP_SHAPE(f);c.SetShape(k.SHAPE_T_CIRCLE);c.SetLayer(k.F_CrtYd)
  c.SetStart0(k.VECTOR2I(0,0));c.SetEnd0(k.VECTOR2I(k.FromMM(3),0));c.SetDrawCoord()
  c.SetWidth(k.FromMM(.05));f.Add(c)
assert before==[t.m_Uuid.AsString()for t in b.GetTracks()]
k.SaveBoard(str(P),b)
pro=json.loads((H/'dock-main.kicad_pro').read_text())
severities=pro['board']['design_settings']['rule_severities']
restored=[]
for name,value in severities.items():
 if value=='ignore':severities[name]='warning';restored.append(name)
assert not pro['board']['design_settings']['drc_exclusions']
base=pro['net_settings']['classes'][0];base.update(clearance=.15,track_width=.2,via_diameter=.5,via_drill=.2)
pro['net_settings']['classes']=[base];assign={}
for name,nets,width in [('HOST_POWER',['HOST_5V'],.6),('UI_POWER',['3V3','3V3_ANALOG'],.3),
 ('LOOP_POWER',['LOOP_5V','BASE_THERM_SEND','LID_THERM_SEND'],.3),
 ('UV_POWER',['UV_5V_LIMITED','UV_5V_MID','UV_5V_SW','CONTACT_5V'],.6)]:
 c=dict(base);c.update(name=name,track_width=width);pro['net_settings']['classes'].append(c)
 for net in nets:assign[net]=name
pro['net_settings']['netclass_assignments']=assign
(H/'dock-main.kicad_pro').write_text(json.dumps(pro,indent=2)+'\n')
meta['native_board_sha256']=sha(P);meta['all_DRC_rules_enabled']=True
(H/'placement.json').write_text(json.dumps(meta,indent=2)+'\n')
(H/'finalization.json').write_text(json.dumps({'board_sha256':sha(P),'native_copper_UUIDs_preserved':len(before),'rules_restored_from_ignore':restored,'mechanical_holes_excluded_from_BOM_and_position':True,'DRC_exclusions':0},indent=2)+'\n')
print('Preserved copper; enabled all DRC rules and added mechanical courtyards',restored)
