"""Bounded, owner-reviewed B-side packing refinement; no circuit/pad changes."""
from pathlib import Path
import hashlib,json,math
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;P=H/'single-flange-placement.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(P)=='2fb80d3a8396e52e0cf803d7fc3310dcb7451fa89e745e8af303a663ca98c2fd'
project=H/'single-flange-placement.kicad_pro';project_bytes=project.read_bytes();b=k.LoadBoard(str(P));fps={f.GetReference():f for f in b.GetFootprints()};old={r:[f.GetPosition().x/1e6-100,100-f.GetPosition().y/1e6,f.GetOrientationDegrees()]for r,f in fps.items()}
changes={'R75':[-18.8,3.5,180],'R76':[-18.8,6.5,180],'D71':[7,-6,0],'C31':[-32.4,9,90],'C32':[-29.9,9,90]}
for ref,(x,z,angle)in changes.items():
 f=fps[ref];assert f.GetLayer()==k.B_Cu;f.SetOrientationDegrees(angle);f.SetPosition(k.VECTOR2I(round((100+x)*1e6),round((100-z)*1e6)))
for ref,f in fps.items():
 if ref not in changes:assert old[ref]==[f.GetPosition().x/1e6-100,100-f.GetPosition().y/1e6,f.GetOrientationDegrees()]
def pin(ref,n):
 q=next(q for q in fps[ref].Pads()if q.GetNumber()==n);return[q.GetPosition().x/1e6-100,100-q.GetPosition().y/1e6]
vdd=pin('U6','3');dist=lambda p:math.hypot(p[0]-vdd[0],p[1]-vdd[1]);power=[{'ref':r,'VDD_pad_productXZ':pin(r,'1'),'straight_distance_to_U6_3_mm':dist(pin(r,'1')),'GND_pad_productXZ':pin(r,'2')}for r in('C31','C32')]
k.SaveBoard(str(P),b);project.write_bytes(project_bytes)
m=json.loads((H/'placement.json').read_text());m['board_sha256']=sha(P)
for r in m['electrical_positions']:
 if r['ref']in changes:r['product_XZ_mm']=changes[r['ref']][:2];r['native_angle_deg']=changes[r['ref']][2]
(H/'placement.json').write_text(json.dumps(m,indent=2)+'\n')
r={'before_sha256':'2fb80d3a8396e52e0cf803d7fc3310dcb7451fa89e745e8af303a663ca98c2fd','after_sha256':sha(P),'bounded_positions':{r:{'before':old[r],'after':p}for r,p in changes.items()},'all_other_positions_exact':True,'source_circuit_changed':False,'actual_U6_VDD_pad3_productXZ':vdd,'near_VDD_decoupling_lands':power,'remaining_routing_requirements':'short3V3 neck fromU6pad3 throughC31/C32, adjacentGNDvias/directreturn to moduleground; no routed loop is implied','RF_tradeoff':'C31/C32 remain near the module VDD edge and inside15mm general antenna guidance; other avoidable small-signal/metal positions moved beyond15mm. Keep actual housing/RF qualification open.'}
(H/'rf-refinement.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'board_sha256':sha(P),'VDD':vdd,'caps':power}))
