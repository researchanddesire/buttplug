"""Repair only explicitly reported preflight items, preserving locked copper."""
from pathlib import Path
import hashlib,json,sys
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parents[3]/'tools'))
import kicad_sexp as s
P=H/'dock-main.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads((H/'placement.json').read_text());assert sha(P)==meta['native_board_sha256']
b=k.LoadBoard(str(P));drc=json.loads((H/'drc.json').read_text())
remove={i['uuid']for v in drc['violations']if v['type']=='copper_edge_clearance'for i in v['items']if i['description'].startswith('Track ')}
found=[]
for t in list(b.GetTracks()):
 if t.m_Uuid.AsString()in remove:
  assert not t.IsLocked();found.append({'uuid':t.m_Uuid.AsString(),'net':t.GetNetname()});b.Delete(t)
assert len(found)==len(remove)
fp={f.GetReference():f for f in b.GetFootprints()}
f=fp['H706'];old=f.GetPosition();target=k.VECTOR2I(144000000,144300000)
assert old==k.VECTOR2I(144000000,143800000)
f.SetPosition(target);moved=0
for z in b.Zones():
 if z.GetIsRuleArea()and z.GetBoundingBox().GetCenter()==old:z.Move(target-old);moved+=1
assert moved==2
for row in meta['mounting_holes_dock_xy_d_mm']:
 if row[:2]==[44,56.2]:row[1]=55.7
# Selected receptacle genuinely has SMT signal lands AND plated shell stakes.
# Retain both native mounting attributes rather than suppressing its check.
f=fp['J101'];f.SetAttributes(f.GetAttributes()|k.FP_THROUGH_HOLE|k.FP_SMD)
lib=H/'DockUI.pretty/USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal.kicad_mod'
tree=s.parse(lib.read_text());a=s.child(tree,'attr');a[:]=s.parse('(attr through_hole smd)');s.write(lib,tree)
pr=json.loads((H/'footprint-provenance.json').read_text());key='DockUI:'+lib.stem
pr[key]['local_sha256']=sha(lib);pr[key]['change']='3D URI rebasing plus hybrid SMT signal/plated-shell mounting metadata; selected copper, drills and body unchanged'
(H/'footprint-provenance.json').write_text(json.dumps(pr,indent=2)+'\n')
k.SaveBoard(str(P),b);meta['native_board_sha256']=sha(P)
(H/'placement.json').write_text(json.dumps(meta,indent=2)+'\n')
(H/'routing/preflight-repairs.json').write_text(json.dumps({'board_sha256':sha(P),'removed_only_native_reported_unlocked_tracks':found,'rear_support_dock_xy_mm':[44,55.7],'connector_positions_preserved':True,'USB_mount_attributes':'hybrid SMT+throughhole; no geometry change'},indent=2)+'\n')
print('Removed explicit edge violations',len(found),'preserved all locked copper; rear support44,55.7')
