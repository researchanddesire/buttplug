"""Independent native XML-to-pad/geometry audit and fresh KiCad10 DRC."""
from pathlib import Path
import argparse,collections,datetime,hashlib,json,math,subprocess,sys,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent;OUT=HERE/'routed-lid'
sys.path.insert(0,str(HERE.parents[3]/'tools'))
import wx
APP=wx.App(False)
import pcbnew as k
import kicad_sexp as s
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def q(p):return [round(k.ToMM(p.x)-100,6),round(200-k.ToMM(p.y),6)]
def sig(t,b):
 if isinstance(t,k.PCB_VIA):return('via',t.GetNetname(),tuple(q(t.GetPosition())),round(k.ToMM(t.GetWidth()),6),round(k.ToMM(t.GetDrillValue()),6))
 return('track',t.GetNetname(),b.GetLayerName(t.GetLayer()),tuple(sorted([tuple(q(t.GetStart())),tuple(q(t.GetEnd()))])),round(k.ToMM(t.GetWidth()),6))
def row_sig(t):
 if t['kind']=='via':return('via',t['net'],tuple(t['xy']),t['diameter'],t['drill'])
 return('track',t['net'],t['layer'],tuple(sorted([tuple(t['start']),tuple(t['end'])])),t['width'])
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--kicad-cli',required=True);args=ap.parse_args()
 pcb=OUT/'dock-lid-routed.kicad_pcb';before=sha(pcb)
 native=HERE/'dock-lid-ui-native.xml';xml=ET.parse(native).getroot();pins={}
 for net in xml.findall('./nets/net'):
  for node in net.findall('node'):pins[(node.get('ref'),node.get('pin'))]=net.get('name')
 components={c.get('ref'):c for c in xml.findall('./components/comp')if c.findtext('footprint')}
 source=json.loads((HERE/'native-checks.json').read_text())
 for p,want in source['source_sha256'].items():assert sha(HERE/p)==want,('Stale source check',p)
 for p,want in source['reports_sha256'].items():assert sha(HERE/p)==want,('Stale source report',p)
 placement=HERE/'dock-lid-placement.kicad_pcb'
 pr=json.loads((HERE/'dock-lid-placement.json').read_text());assert sha(placement)==pr['native_board_sha256']
 b=k.LoadBoard(str(pcb));assert b.GetCopperLayerCount()==4 and abs(k.ToMM(b.GetDesignSettings().GetBoardThickness())-1)<1e-8
 fps={f.GetReference():f for f in b.GetFootprints()}
 mounts={'H301':[-30,65],'H302':[30,65],'H303':[-32,115],'H304':[32,105]}
 assert set(fps)==set(components)|set(mounts),(set(fps),set(components))
 checks=[];pad_geom={}
 for ref,c in sorted(components.items()):
  fp=fps[ref];fid=str(fp.GetFPID().GetLibNickname())+':'+str(fp.GetFPID().GetLibItemName())
  assert fid==c.findtext('footprint')and fp.GetValue()==c.findtext('value'),ref
  lib=OUT/'DockControl.pretty'/(str(fp.GetFPID().GetLibItemName())+'.kicad_mod')
  tree=s.parse(lib.read_text());want={p[1].value for p in s.children(tree,'pad')if p[1].value}
  actual={p.GetNumber()for p in fp.Pads()if p.GetNumber()};assert actual==want,(ref,actual,want)
  rows=[]
  for p in fp.Pads():
   n=p.GetNumber()
   if not n:continue
   assert p.GetNetname()==(pins.get((ref,n))or''),(ref,n,p.GetNetname(),pins.get((ref,n)))
   side='B.Cu'if p.GetLayerSet().Contains(k.B_Cu)else'F.Cu'
   rows.append({'pin':n,'net':p.GetNetname(),'dock_xy_mm':q(p.GetPosition()),'side':side})
   # All selected SMD pad copper stays outside each actual R3 hardware zone.
   bb=p.GetBoundingBox();a=q(bb.GetOrigin());c2=q(bb.GetEnd());x1,x2=sorted([a[0],c2[0]]);y1,y2=sorted([a[1],c2[1]])
   for h,(x,y)in mounts.items():
    distance=math.hypot(max(x1-x,0,x-x2),max(y1-y,0,y-y2))
    assert distance>=3-1e-8,(ref,n,h,distance)
  checks+=rows;pad_geom[ref]=rows
 for ref in ('S301','S302','S303','J301','J302'):
  fp=fps[ref];want=pr['footprint_placements_dock_xy_and_native_angle'][ref]
  assert q(fp.GetPosition())==want[:2]and abs(fp.GetOrientationDegrees()-want[2])<1e-8,(ref,want,q(fp.GetPosition()))
 for ref,p in mounts.items():
  fp=fps[ref];assert q(fp.GetPosition())==p
  pads=list(fp.Pads());assert len(pads)==1
  hole=pads[0];assert not hole.GetNumber()and hole.GetAttribute()==k.PAD_ATTRIB_NPTH
  assert abs(k.ToMM(hole.GetDrillSize().x)-2.3)<1e-9 and abs(k.ToMM(hole.GetDrillSize().y)-2.3)<1e-9
 # Compare the actual immutable flex keepout polygon and all constraints.
 frozen=s.parse(placement.read_text());routed=s.parse(pcb.read_text())
 model_files={}
 for fp in s.children(routed,'footprint'):
  ref=next(x[2].value for x in s.children(fp,'fp_text')if x[1].value=='reference')
  models=s.children(fp,'model')
  if ref in components:assert models,('Missing selected package model',ref)
  for model in models:
   uri=model[1].value;assert uri.startswith('${KIPRJMOD}/../DockControl.3dshapes/'),(ref,uri)
   path=(OUT/uri.split('${KIPRJMOD}/',1)[1]).resolve();assert path.is_file(),(ref,path)
   model_files[str(path.relative_to(HERE))]=sha(path)
   lib=OUT/'DockControl.pretty'/(fp[1].value.split(':')[1]+'.kicad_mod')
   assert any(s.dump(x)==s.dump(model)for x in s.children(s.parse(lib.read_text()),'model')),(ref,'Board/library model pose mismatch')
 def keepout(tree):
  return[{'polygon':s.child(z,'polygon'),'keepout':s.child(z,'keepout'),'layers':s.child(z,'layers')}for z in s.children(tree,'zone')if s.child(z,'keepout')is not None]
 a=keepout(frozen);c=keepout(routed)
 # Token equality is object-identity based; compare serialized nodes.
 serial=lambda node:s.dump(node)
 for source_keepout in a:
  assert any(serial(x['polygon'])==serial(source_keepout['polygon'])and serial(x['keepout'])==serial(source_keepout['keepout'])for x in c),'FFC corridor changed'
 for t in b.GetTracks():
  if not isinstance(t,k.PCB_VIA):assert t.GetLayer()!=k.In1_Cu,'Inner1 is exclusively the GND reference plane'
 protected=json.loads((OUT/'local-copper.json').read_text())['protected_records']
 got=collections.Counter(sig(t,b)for t in b.GetTracks());want=collections.Counter(row_sig(t)for t in protected);assert not want-got,'Authored local LCD copper changed'
 exchange=json.loads((OUT/'router-exchange.json').read_text());repair=json.loads((OUT/'escape-repair.json').read_text())
 assert sha(pcb.with_suffix('.dsn'))==exchange['dsn_sha256'] and sha(pcb.with_suffix('.ses'))==exchange['session_sha256']
 assert sha(OUT/'first-pass.ses')==repair['initial_offline_session_sha256']
 binding=json.loads((OUT/'lcd-socket-model-binding.json').read_text())
 assert binding['previous_electrical_routing_board_SHA256']==repair['final_board_sha256']
 assert sha(pcb)==binding['board_after_model_binding_SHA256']
 previous=OUT/binding['previous_routed_native_snapshot']
 assert sha(previous)==binding['previous_electrical_routing_board_SHA256']
 cad=HERE.parents[3]/'hardware/cad/evt1-assembly/vendor/lcd-socket'
 sys.path.insert(0,str(cad));import bind_routed_model as binding_tool
 assert binding_tool.without_allowed_metadata(s.parse(previous.read_text()))==binding_tool.without_allowed_metadata(routed)
 assert sha(cad/'bind_routed_model.py')==binding['binder_SHA256']
 assert sha(cad/'source-manifest.json')==binding['source_manifest_SHA256']
 assert sha(cad/'native-checks.json')==binding['CAD_native_checks_SHA256']
 assert sha(HERE/binding['model'])==binding['model_SHA256']
 pose=json.loads((OUT/'lcd-socket-native-pose.json').read_text())
 assert pose['board_SHA256']==sha(pcb)and pose['model_SHA256']==binding['model_SHA256']and pose['actual_KiCad_exported_pose_valid']
 assert sha(HERE.parents[3]/pose['actual_export_file'])==pose['actual_export_SHA256']
 assert sha(HERE.parents[3]/pose['board_datum_export_file'])==pose['board_datum_export_SHA256']
 assert sha(HERE.parents[3]/pose['checker_file'])==pose['checker_SHA256']
 cadchecks=json.loads((cad/'native-checks.json').read_text())
 assert sha(HERE.parents[3]/'tools/build_evt1_dock_lcd_socket.py')==cadchecks['builder_sha256']
 project=json.loads(pcb.with_suffix('.kicad_pro').read_text());assert project['board']['design_settings']['drc_exclusions']==[]
 # Source KiCad10 never writes the input PCB during DRC.
 version=subprocess.check_output([args.kicad_cli,'--version'],text=True).strip();assert version.startswith('10.')
 drc=OUT/'drc.json';r=subprocess.run([args.kicad_cli,'pcb','drc','--format','json','--all-track-errors','--exit-code-violations','-o',str(drc),str(pcb)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (OUT/'drc.log').write_text(r.stdout);d=json.loads(drc.read_text())
 assert d['kicad_version']==version and d['ignored_checks']==[] and d['included_severities']==['error','warning']
 assert r.returncode==0 and not d['violations']and not d['unconnected_items'],(r.returncode,collections.Counter(v['type']for v in d['violations']),len(d['unconnected_items']))
 assert sha(pcb)==before,'Checker modified board'
 def source_files():
  files=[pcb,pcb.with_suffix('.kicad_pro'),pcb.with_suffix('.dsn'),pcb.with_suffix('.ses'),OUT/'first-pass.ses',native,HERE/'native-checks.json',HERE/'route_lid.py',Path(__file__),OUT/'fp-lib-table',OUT/'local-copper.json',OUT/'route-floorplan.json',OUT/'router-exchange.json',OUT/'escape-repair.json',OUT/'native-finalization.json',OUT/'lcd-socket-model-binding.json',OUT/'lcd-socket-native-pose.json',previous]
  files+=list((OUT/'DockControl.pretty').glob('*.kicad_mod'))
  files +=[HERE/p for p in model_files]
  return{str(f.relative_to(HERE)):sha(f)for f in files}
 out={'status':'pass: native routed lid DRC0/unconnected0 and independent XML pad parity','checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kicad_DRC_version':version,'KiCad_Python_version':k.Version(),'source_sha256':source_files(),'reports_sha256':{'drc.json':sha(drc)},'electrical_references':len(components),'mechanical_NPTH_holes':4,'physical_electrical_pad_instances':len(checks),'native_pad_net_checks':pad_geom,'original_control_socket_hinge_XY_preserved':True,'original_FFC_keepout_preserved':True,'manual_source_copper_records_preserved':len(protected),'tracks':sum(not isinstance(t,k.PCB_VIA)for t in b.GetTracks()),'vias':sum(isinstance(t,k.PCB_VIA)for t in b.GetTracks()),'stackup':'4copperlayers/1mm; In1 solidGNDreference; actual dielectric/copper/process supplierapproval open','B_side_max_case_height_mm':1.8,'B_side_planned_mounted_clearance_mm':1.95,'socket_contactheight_and_tail_mating_qualified':False,'native_MCAD_fit_qualified':False,'physical_electrical_or_UV_validation':False,'full_product_order_ready':False}
 (OUT/'native-checks.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({p:out[p]for p in ('status','electrical_references','mechanical_NPTH_holes','physical_electrical_pad_instances','tracks','vias','full_product_order_ready')}))
if __name__=='__main__':main()
