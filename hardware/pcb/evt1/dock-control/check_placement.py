"""Read one native candidate per KiCad7 Python process; never mutate its board."""
from pathlib import Path
import argparse,hashlib,json,sys,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[3]/'tools'))
import wx
APP=wx.App(False)
import pcbnew as k
import kicad_sexp as s

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser();ap.add_argument('domain',choices=['controller','lid'])
 ap.add_argument('--refresh-schematic-binding',action='store_true',help='After a fresh native export, rebind only if every saved PCB terminal still matches')
 args=ap.parse_args()
 name='dock-'+args.domain+'-placement';path=HERE/(name+'.kicad_pcb')
 before=sha(path);placement=json.loads((HERE/(name+'.json')).read_text())
 assert before==placement['native_board_sha256']
 native=HERE/placement['native_schematic_xml']
 if sha(native)!=placement['native_schematic_xml_sha256']:
  assert args.refresh_schematic_binding,'Fresh export differs; complete native pad parity before explicitly rebinding'
 xml=ET.parse(native).getroot();pins={};expected={}
 for net in xml.findall('./nets/net'):
  for node in net.findall('node'):pins[(node.get('ref'),node.get('pin'))]=net.get('name')
 for c in xml.findall('./components/comp'):
  if c.findtext('footprint'):expected[c.get('ref')]=c
 board=k.LoadBoard(str(path));assert board and not list(board.GetTracks())
 assert board.GetCopperLayerCount()==2
 assert abs(k.ToMM(board.GetDesignSettings().GetBoardThickness())-1)<1e-9
 footprints={fp.GetReference():fp for fp in board.GetFootprints()}
 assert set(footprints)==set(expected)
 manifest=json.loads((HERE/'circuit-parts.json').read_text())
 items={p['ref']:p for p in manifest['generated_pin_manifest']}
 result=[];models={}
 for ref,fp in sorted(footprints.items()):
  c=expected[ref];want=c.findtext('footprint')
  assert str(fp.GetFPID().GetLibNickname())+':'+str(fp.GetFPID().GetLibItemName())==want
  assert fp.GetValue()==c.findtext('value')
  numbers={p.GetNumber()for p in fp.Pads()if p.GetNumber()}
  assert numbers==set(items[ref]['pins']),(ref,numbers,items[ref]['pins'])
  actual=[]
  for p in fp.Pads():
   n=p.GetNumber()
   if not n:continue
   net=pins.get((ref,n));actual_net=p.GetNetname()
   assert actual_net==(net or ''),(ref,n,actual_net,net)
   actual.append({'pad':n,'net':actual_net,'dock_xy_mm':[round(k.ToMM(p.GetPosition().x)-100,6),round(200-k.ToMM(p.GetPosition().y),6)]})
  pos=placement['footprint_placements_dock_xy_and_native_angle'][ref]
  got=[k.ToMM(fp.GetPosition().x)-100,200-k.ToMM(fp.GetPosition().y),fp.GetOrientationDegrees()]
  assert all(abs(a-b)<1e-8 for a,b in zip(pos,got)),(ref,pos,got)
  result.append({'reference':ref,'footprint':want,'dock_xy_native_angle':got,'pads':actual})
  tree=s.parse((HERE/'DockControl.pretty'/(want.split(':')[1]+'.kicad_mod')).read_text())
  m=s.child(tree,'model')
  if m:
   local=HERE/m[1].value.split('${KIPRJMOD}/',1)[1];assert local.exists(),local
   models[ref]={'local_file':str(local.relative_to(HERE)),'sha256':sha(local)}
 # J302 is direct, and native180deg hinge sockets put their pin1 atdock+X.
 for ref in ('J201','J301','J302'):
  if ref not in footprints:continue
  fp=footprints[ref];one=next(p for p in fp.Pads()if p.GetNumber()=='1')
  dx=k.ToMM(one.GetPosition().x-fp.GetPosition().x)
  assert abs(dx-(-6.5 if ref=='J302' else 4.75))<1e-8,(ref,dx)
 if args.domain=='lid':
  for ref,x in (('S301',-22),('S302',0),('S303',22)):
   p=footprints[ref].GetPosition();assert abs(k.ToMM(p.x)-100-x)<1e-9 and abs(200-k.ToMM(p.y)-54)<1e-9
 assert sha(path)==before,'Read-only checker modified board'
 # No byte of the PCB changes. Rebinding occurs ONLY after all component,
 # physical-pad, net, placement, model and connector-direction checks pass.
 if args.refresh_schematic_binding:
  placement['native_schematic_xml_sha256']=sha(native)
  (HERE/(name+'.json')).write_text(json.dumps(placement,indent=2)+'\n')
 out={'status':'pass: native saved-board selected-footprint and pad/net parity',
      'board_sha256':before,'schematic_xml_sha256':sha(native),'KiCad_Python':k.Version(),
      'footprint_count':len(result),'native_pad_instances':sum(len(r['pads'])for r in result),
      'native_pads':result,'local_3D_sources':models,
      'missing_3D_references':[r for r in footprints if r not in models and r not in ('J202','TP201')],
      'routing_present':False,'physical_mating_qualified':False,'full_product_order_ready':False}
 (HERE/(name+'-checks.json')).write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({a:out[a]for a in ('status','footprint_count','native_pad_instances','missing_3D_references','full_product_order_ready')}))
if __name__=='__main__':main()
