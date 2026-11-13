"""Independent saved-native source/pad/packing audit, not route qualification."""
from pathlib import Path
import hashlib,json,math,sys,xml.etree.ElementTree as ET
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;E=H.parent;ROOT=H.parents[3]
sys.path.insert(0,str(ROOT/'tools'));import kicad_sexp as s
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
pt=lambda v:[v.x/1e6-100,100-v.y/1e6]
def signature(p):
 return[p.GetNumber(),int(p.GetAttribute()),int(p.GetShape()),[p.GetPosition().x,p.GetPosition().y],[p.GetSize().x,p.GetSize().y],[p.GetDrillSize().x,p.GetDrillSize().y],round(p.GetOrientationDegrees()%360,5),[p.IsOnLayer(i)for i in(k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu)],p.GetNetname()]
def without(t):
 return [q for q in t if not(isinstance(q,list)and q and(q[0].value=='model'or(q[0].value in('fp_line','fp_rect','fp_circle','fp_arc','fp_poly','fp_text')and s.value(q,'layer')in('F.SilkS','B.SilkS'))))]
def main():
 inv=json.loads((H/'source-inventory.json').read_text());meta=json.loads((H/'placement.json').read_text());prov=json.loads((H/'footprint-provenance.json').read_text())
 for p,h in inv['source_sha256'].items():assert sha(E/p)==h,('source altered',p)
 before=sha(H/'single-flange-placement.kicad_pcb');assert before==meta['board_sha256']
 b=k.LoadBoard(str(H/'single-flange-placement.kicad_pcb'));fps={f.GetReference():f for f in b.GetFootprints()};assert len(fps)==43 and not list(b.GetTracks())
 assert b.GetCopperLayerCount()==4 and b.GetDesignSettings().GetBoardThickness()==1000000
 xml=ET.parse(E/'system-native.xml').getroot();nets={(q.get('ref'),q.get('pin')):n.get('name')for n in xml.findall('./nets/net')for q in n.findall('node')}
 contracts=[];rows=[];coverage=[];packing=[]
 sourceparts={r['ref']:r for r in inv['selected_positions']if r['domain']in('flange','sensor')};actual_source_instances=0
 for ref,rec in prov['selected_source_footprints'].items():
  original=s.parse((ROOT/rec['source_footprint']).read_text());local=s.parse((H/rec['local']).read_text())
  assert sha(ROOT/rec['source_footprint'])==rec['source_sha256']
  # Exact semantic comparison allows only 3D model additions/path rebasing and
  # deferred assembly silk; every original pad/drill/Fab/courtyard/zone remains.
  assert s.dump(without(original))==s.dump(without(local)),('source footprint geometry differs',ref)
  f=fps[ref];assert f.IsLocked();numbered=[q for q in f.Pads()if q.GetNumber()and q.GetNumber()!='MP']
  for q in numbered:
   assert q.GetNetname()==nets[ref,q.GetNumber()],(ref,q.GetNumber(),q.GetNetname(),nets.get((ref,q.GetNumber())))
   contracts.append({'ref':ref,'pad':q.GetNumber(),'net':q.GetNetname(),'product_XZ_mm':pt(q.GetPosition())})
  actual_source_instances+=len(numbered)
  models=list(f.Models());assert len(models)==1,('missing/ambiguous package model',ref)
  model=Path(models[0].m_Filename.replace('${KIPRJMOD}',str(H)));assert model.is_file()
  coverage.append({'ref':ref,'model':str(model.relative_to(H)),'sha256':sha(model),'model_class':'OEM selected module'if ref=='U6'else'KiCad nominal selected package family; selected maximum dimensions separately retained'})
  part=sourceparts[ref];q=next(a for a in meta['electrical_positions']if a['ref']==ref);assert [round(a,6)for a in pt(f.GetPosition())]==q['product_XZ_mm']
  assert f.GetLayer()==(k.F_Cu if q['side']=='F'else k.B_Cu)
  assert abs((f.GetOrientationDegrees()-q['native_angle_deg'])%360)<1e-6
  # Independently transform selected local pads without mutating the native
  # BOARD, avoiding invalidated borrowed SWIG handles in KiCad7.
  proto=k.FootprintLoad(str(H/'Selected.pretty'),Path(rec['local']).stem);assert proto
  assert proto.GetOrientationDegrees()==0
  expected=[];angle=math.radians(q['native_angle_deg']);co=round(math.cos(angle),12);si=round(math.sin(angle),12);back=q['side']=='B'
  layer_map={k.F_Cu:k.B_Cu,k.B_Cu:k.F_Cu,k.In1_Cu:k.In2_Cu,k.In2_Cu:k.In1_Cu}
  for pp in proto.Pads():
   local=pp.GetPos0();x=local.x;y=-local.y if back else local.y
   position=[f.GetPosition().x+round(co*x+si*y),f.GetPosition().y+round(-si*x+co*y)]
   rotation=(q['native_angle_deg']+(-1 if back else 1)*pp.GetOrientationDegrees())%360
   copper=[pp.IsOnLayer(layer_map[i]if back else i)for i in(k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu)]
   expected.append([pp.GetNumber(),int(pp.GetAttribute()),int(pp.GetShape()),position,[pp.GetSize().x,pp.GetSize().y],[pp.GetDrillSize().x,pp.GetDrillSize().y],round(rotation,5),copper,nets.get((ref,pp.GetNumber()),'')])
  assert sorted(signature(p)for p in f.Pads())==sorted(expected),('saved selected pad geometry changed',ref)
  h=max(part.get('maximum_height_mm',0),part['native_geometry'].get('height_budget_mm',0));bounds=[]
  gs=[g.GetBoundingBox()for g in f.GraphicalItems()if isinstance(g,k.PCB_SHAPE)and g.GetLayer()in(k.F_Fab,k.B_Fab)]
  assert gs,('Fab geometry missing',ref)
  bounds=[min(z.GetLeft()for z in gs)/1e6-100,100-max(z.GetBottom()for z in gs)/1e6,max(z.GetRight()for z in gs)/1e6-100,100-min(z.GetTop()for z in gs)/1e6]
  shadow=bounds[2]>=6.75 and bounds[0]<=40.25 and bounds[3]>=-10.75 and bounds[1]<=10.75
  gap=3.352-h if q['side']=='B'and shadow else None
  if gap is not None:assert gap>=.5,(ref,'insufficient pack growth gap',gap)
  packing.append({'ref':ref,'side':q['side'],'Fab_bounds_productXZ_mm':bounds,'conservative_height_mm':h,'over_requested_pack_growth_projection':shadow,'gap_to_growth_mm':gap})
 assert len(prov['selected_source_footprints'])==35 and actual_source_instances==159
 for ref,net in [('CT1','GND'),('CT2','USB_DM_CONTACT'),('CT3','USB_DP_CONTACT'),('CT4','DOCK_5V')]:
  f=fps[ref];q=list(f.Pads())[0];assert q.GetNetname()==net and q.GetDrillSize().x==863600 and q.GetSize().x==3200000
  assert q.GetAttribute()==k.PAD_ATTRIB_PTH and len(list(f.Models()))==1
  contracts.append({'ref':ref,'pad':'1','net':net,'product_XZ_mm':pt(q.GetPosition())})
  models=list(f.Models());model=Path(models[0].m_Filename.replace('${KIPRJMOD}',str(H)));coverage.append({'ref':ref,'model':str(model.relative_to(H)),'sha256':sha(model),'model_class':'primary drawing reconstruction; undimensioned chamfer omitted'})
 assert len(contracts)==163 and len(coverage)==39
 assert {r for r in fps if not r.startswith('MH')and fps[r].GetLayer()==k.F_Cu}=={'SW1','SW2','CT1','CT2','CT3','CT4'}
 # Check actual native copper extents for avoidable non-module objects.
 quiet=[]
 for ref,f in fps.items():
  if ref.startswith('MH')or ref in('U6','C31','C32'):continue
  for q in f.Pads():
   box=q.GetBoundingBox();gap=box.GetLeft()/1e6-100-(-35.6)
   quiet.append({'ref':ref,'pad':q.GetNumber(),'horizontal_gap_from_antenna_edge_mm':gap})
 assert min(q['horizontal_gap_from_antenna_edge_mm']for q in quiet)>=15

 drc=json.loads((H/'placement-drc.json').read_text());assert not drc['violations'],[(r['type'],r['description'])for r in drc['violations']]
 assert drc['unconnected_items'],'Unrouted candidate must not masquerade as routed0/0'
 pro=json.loads((H/'single-flange-placement.kicad_pro').read_text());assert not pro['board']['design_settings']['drc_exclusions'];assert not any(v=='ignore'for v in pro['board']['design_settings']['rule_severities'].values())
 step=json.loads((H/'native-step-pose-checks.json').read_text());assert step['status']=='pass'and step['native_board_sha256']==before and step['normalized_STEP_sha256']==sha(H/'SingleFlangePlacement.step')and step['raw_native_STEP_sha256']==sha(H/'NativeKiCadPlacement.step')
 assert step['FreeCAD_sha256']==sha(H/'SingleFlangePlacement.FCStd')
 assert {q['ref']:q['model_sha256']for q in step['parts']}=={q['ref']:q['sha256']for q in coverage}
 oem=json.loads((H/'OEM-module-pose-checks.json').read_text());assert not oem['failures']and len(oem['physical_pad_instance_registration_checks'])==61
 assert sha(H/'single-flange-placement.kicad_pcb')==before
 r={'status':'pass: source/native pad parity and unrouted placement DRC; NOT routed or build release','board_sha256':before,'KiCad_Python_version':k.Version(),'native_DRC_version':drc['kicad_version'],'source_positions':35,'new_targets':4,'models':39,'physical_source_pad_instances':159,'new_contact_pad_instances':4,'unmodified_body_positions':69,'native_pad_contracts':contracts,'model_coverage':coverage,'component_pack_growth_checks':packing,'placement_DRC_violations':0,'expected_unconnected_items':len(drc['unconnected_items']),'source_invariant_sha256':inv['source_sha256'],'reports_sha256':{'placement-drc.json':sha(H/'placement-drc.json'),'placement.json':sha(H/'placement.json'),'footprint-provenance.json':sha(H/'footprint-provenance.json'),'native-step-pose-checks.json':sha(H/'native-step-pose-checks.json'),'mcad.json':sha(H/'mcad.json'),'OEM-module-pose-checks.json':sha(H/'OEM-module-pose-checks.json')},'RF_avoidable_native_copper_checks':quiet,'near_pin_RF_exceptions':['C31','C32'],'RF_mounting_hardware_and_housing_acceptance':False,'source_board_or_schematic_modified':False,'RF_magnetic_mechanical_or_process_qualification':False,'fabrication_ready':False}
 r['all_local_source_sha256']={str(p.relative_to(H)):sha(p)for p in sorted(H.rglob('*'))if p.is_file()and p.name!='native-checks.json'and p.suffix in('.py','.md','.json','.step','.png','.kicad_pcb','.kicad_pro','.kicad_mod','.FCStd')and '__pycache__'not in str(p)}
 (H/'native-checks.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k]for k in('status','source_positions','new_targets','models','physical_source_pad_instances','placement_DRC_violations','expected_unconnected_items')}))
if __name__=='__main__':main()
