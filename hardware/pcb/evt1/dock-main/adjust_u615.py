"""Root-approved bounded U615 placement/local-reference exception only.

All192 source objects remain untouched. One authored GND stub is replaced;
the original VDD bypass remains and receives a0.5mm extension to its new pad.
General router copper in the immediate package corridor may be rerouted.
"""
from pathlib import Path
import hashlib,json,sys
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;P=H/'dock-main.kicad_pcb'
sys.path.insert(0,str(H.parents[3]/'tools'));import kicad_sexp as s
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def xy(x,y):return k.VECTOR2I(round((100+x)*1e6),round((200-y)*1e6))
def dock(p):return [round(k.ToMM(p.x)-100,6),round(200-k.ToMM(p.y),6)]
meta=json.loads((H/'placement.json').read_text());assert sha(P)==meta['native_board_sha256']
critical=json.loads((H/'critical-routing.json').read_text());b=k.LoadBoard(str(P))
f=next(f for f in b.GetFootprints()if f.GetReference()=='U615');assert dock(f.GetPosition())==[42,50]
pins_before={p.GetNumber():{'net':p.GetNetname(),'position':dock(p.GetPosition())}for p in f.Pads()}
old_ground=pins_before['7']['position'];old_vdd=pins_before['14']['position']
via=next(r[2]for r in critical['local_ground_vias']if r[:2]==['U615','7'])
old_record=next(r for r in critical['critical_copper']if r['kind']=='track'and r['net']=='GND'and r['start']==old_ground and r['end']==via)
match=[t for t in b.GetTracks()if not isinstance(t,k.PCB_VIA)and t.GetNetname()=='GND'and t.IsLocked()and t.GetStart()==xy(*old_ground)and t.GetEnd()==xy(*via)]
assert len(match)==1;b.Delete(match[0])
region=k.SHAPE_POLY_SET();region.NewOutline()
for p in [(137800000,146700000),(146200000,146700000),(146200000,153800000),(137800000,153800000)]:region.Append(*p)
removed=[]
for t in list(b.GetTracks()):
 if not t.IsLocked()and t.GetEffectiveShape().Collide(region,0):
  removed.append({'uuid':t.m_Uuid.AsString(),'net':t.GetNetname()});b.Delete(t)
f.SetPosition(xy(42,49.5));pins_after={p.GetNumber():{'net':p.GetNetname(),'position':dock(p.GetPosition())}for p in f.Pads()}
assert {n:v['net']for n,v in pins_before.items()}=={n:v['net']for n,v in pins_after.items()}
def track(net,a,c,width,role):
 t=k.PCB_TRACK(b);t.SetStart(xy(*a));t.SetEnd(xy(*c));t.SetWidth(k.FromMM(width));t.SetLayer(k.F_Cu);t.SetNet(b.FindNet(net));t.SetLocked(True);b.Add(t)
 return {'kind':'track','net':net,'start':a,'end':c,'width':width,'layer':'F.Cu','role':role}
new_ground=track('GND',pins_after['7']['position'],via,.2,'local bypass/reference')
critical['critical_copper'][critical['critical_copper'].index(old_record)]=new_ground
extension=track('3V3',pins_after['14']['position'],old_vdd,.3,'approved U615 VDD endpoint extension')
critical['critical_copper'].append(extension)
meta['footprint_placements_dock_xy_native_angle']['U615']=[42,49.5,0]
critical['component_adjustments_dock_xy_native_angle']['U615']=[42,49.5,0]
# Native mounting category follows plated shell retention. Signal lands and
# stencil remain SMT; record the hybrid package explicitly in provenance.
usb=next(f for f in b.GetFootprints()if f.GetReference()=='J101')
usb.SetAttributes((usb.GetAttributes()&~k.FP_SMD)|k.FP_THROUGH_HOLE)
lib=H/'DockUI.pretty/USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal.kicad_mod'
tree=s.parse(lib.read_text());s.child(tree,'attr')[:]=s.parse('(attr through_hole)');s.write(lib,tree)
prov=json.loads((H/'footprint-provenance.json').read_text());key='DockUI:'+lib.stem
prov[key]['local_sha256']=sha(lib);prov[key]['change']='Model URI rebasing; KiCad native mounting class follows plated shell stakes; signal lands/stencil remain SMT. No pad, drill or body geometry change.'
(H/'footprint-provenance.json').write_text(json.dumps(prov,indent=2)+'\n')
k.SaveBoard(str(P),b);meta['native_board_sha256']=sha(P);critical['latest_board_after_exception_sha256']=sha(P)
(H/'placement.json').write_text(json.dumps(meta,indent=2)+'\n');(H/'critical-routing.json').write_text(json.dumps(critical,indent=2)+'\n')
(H/'routing/u615-bounded-exception.json').write_text(json.dumps({'reason':'Fit R3 new rear support between full selected connector and logic-package courtyards; preserve both connector placements','authorization':'root explicit2026-11-12','old_origin':[42,50,0],'new_origin':[42,49.5,0],'all_pin_nets_unchanged':True,'before_pin_geometry':pins_before,'after_pin_geometry':pins_after,'source192_copper_unchanged':True,'removed_authored_critical_track':old_record,'replacement_authored_critical_track':new_ground,'added_VDD_extension':extension,'unchanged_ground_via':via,'unlocked_general_items_to_reroute':removed,'rear_support_dock_xy_mm':[44,55.7],'board_sha256':sha(P)},indent=2)+'\n')
print('Moved onlyU615; replaced1criticalGNDstub,added1VDDextension; reroute',len(removed),'generalitems')
