from pathlib import Path
import json,hashlib,shutil
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;p=H/'single-flange-placement.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(p)=='98abc09d3093d83784f05320408d50109c6dcd81a6fa7b2d3453bedad1fa5c37'
shutil.copyfile(H/'placement-drc.json',H/'rf-moves-preflight-drc.json');project=H/'single-flange-placement.kicad_pro';pro=project.read_bytes();b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()};changes={'R75':[-18.8,3.5,180],'R76':[-18.8,6.5,180]}
for ref,(x,z,angle)in changes.items():
 f=fps[ref];assert f.GetLayer()==k.B_Cu;f.SetOrientationDegrees(angle);f.SetPosition(k.VECTOR2I(round((100+x)*1e6),round((100-z)*1e6)))
k.SaveBoard(str(p),b);project.write_bytes(pro);m=json.loads((H/'placement.json').read_text());m['board_sha256']=sha(p)
for r in m['electrical_positions']:
 if r['ref']in changes:r['product_XZ_mm']=changes[r['ref']][:2];r['native_angle_deg']=changes[r['ref']][2]
(H/'placement.json').write_text(json.dumps(m,indent=2)+'\n');r=json.loads((H/'rf-refinement.json').read_text());r['courtyard_resolution']={'intermediate_board_sha256':r['after_sha256'],'native_preflight':'rf-moves-preflight-drc.json','final_two_resistor_poses':changes,'source_geometry_or_net_change':False};r['after_sha256']=sha(p)
for ref,pose in changes.items():r['bounded_positions'][ref]['after']=pose
(H/'rf-refinement.json').write_text(json.dumps(r,indent=2)+'\n');print(sha(p))
