"""Final native pad/netlist, critical-copper, geometry and source-conservation audit."""
from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as ET
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;ROOT=H.parents[3];S=H.parent/'single-flange-study';P=H/'single-flange.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sys.path.insert(0,str(ROOT/'tools'));import kicad_sexp as s
state=json.loads((H/'pcb-state.json').read_text());before=sha(P);assert before==state['board_sha256']
# Run the independently authored retained-circuit and token-geometry checks.
exec(compile((H/'check_schematic.py').read_text(),str(H/'check_schematic.py'),'exec'),{'__file__':str(H/'check_schematic.py')})
exec(compile((H/'check_geometry.py').read_text(),str(H/'check_geometry.py'),'exec'),{'__file__':str(H/'check_geometry.py')})
geom=json.loads((H/'geometry-parity.json').read_text());assert geom['routed_candidate_board_sha256']==before
independent=json.loads((H/'single-flange-independent-terminal-review.json').read_text());assert independent['pass']and independent['retained_endpoints_compared_including_pintype_and_pinfunction']==376
for p,v in independent['inputs_SHA256'].items():assert sha(Path(p))==v,('independent terminal review source drift',p)
pro=json.loads((H/'single-flange.kicad_pro').read_text());severities=pro['board']['design_settings']['rule_severities'];assert not[k for k,v in severities.items()if v=='ignore'];assert not pro['board']['design_settings']['drc_exclusions']
drc=json.loads((H/'drc.json').read_text());assert not drc['violations']and not drc['unconnected_items']and not drc.get('ignored_checks')
r=ET.parse(H/'single-flange-native.xml').getroot();comps={c.get('ref'):c for c in r.findall('./components/comp')};pins={(n.get('ref'),n.get('pin')):net.get('name')for net in r.findall('./nets/net')for n in net.findall('node')};assert len(comps)==39 and len(pins)==155
b=k.LoadBoard(str(P));fps={f.GetReference():f for f in b.GetFootprints()};assert set(fps)==set(comps)|{'MH1','MH2','MH3','MH4'}
rows=[];mechanical_hold_down_pads=0
for ref,f in fps.items():
 if ref.startswith('MH'):
  assert len(list(f.Pads()))==1
  p=list(f.Pads())[0];assert p.GetAttribute()==k.PAD_ATTRIB_NPTH and p.GetDrillSize().x==1600000;continue
 assert f.GetValue()==comps[ref].findtext('value');assert f.GetFPID().GetLibNickname()=='Selected'
 for p in f.Pads():
  num=p.GetNumber()
  if not num:assert not p.GetNetCode();continue
  if num=='MP':assert ref in('J4','J7')and not p.GetNetCode();mechanical_hold_down_pads+=1;continue
  assert pins[ref,num]==p.GetNetname(),(ref,num,p.GetNetname(),pins.get((ref,num)))
  rows.append({'ref':ref,'pad':num,'net':p.GetNetname(),'native_XY_mm':[k.ToMM(p.GetPosition().x),k.ToMM(p.GetPosition().y)],'product_XZ_mm':[round(k.ToMM(p.GetPosition().x)-100,9),round(100-k.ToMM(p.GetPosition().y),9)],'side':k.LayerName(p.GetLayer()),'uuid':p.m_Uuid.AsString()})
assert len(rows)==163 and mechanical_hold_down_pads==4
tracks={t.m_Uuid.AsString():t for t in b.GetTracks()};critical=json.loads((H/'critical-copper.json').read_text());assert len(critical['objects'])==157
for q in critical['objects']:
 t=tracks[q['uuid']];assert t.IsLocked()and t.GetNetname()==q['net']
 def point(v):return k.VECTOR2I(round((100+v[0])*1e6),round((100-v[1])*1e6))
 if q['kind']=='via':assert isinstance(t,k.PCB_VIA)and t.GetPosition()==point(q['product_XZ_mm'])and t.GetWidth()==round(q['diameter_mm']*1e6)and t.GetDrillValue()==round(q['drill_mm']*1e6)
 else:assert not isinstance(t,k.PCB_VIA)and t.GetLayer()==b.GetLayerID(q['layer'])and t.GetStart()==point(q['start'])and t.GetEnd()==point(q['end'])and t.GetWidth()==round(q['width_mm']*1e6)
assert all(isinstance(t,k.PCB_VIA)or(t.GetLayer()!=k.In1_Cu and t.GetWidth()>=150000)for t in tracks.values())
assert all(t.GetDrillValue()>=200000 and t.GetWidth()>=500000 for t in tracks.values()if isinstance(t,k.PCB_VIA))
assert b.GetDesignSettings().GetBoardThickness()==1000000
original=json.loads((S/'native-checks.json').read_text());assert sha(S/'native-checks.json')==state['frozen_study_checks_sha256']
for p,v in original['all_local_source_sha256'].items():assert sha(S/p)==v,('frozen study modified',p)
for p,v in original['source_invariant_sha256'].items():assert sha(H.parent/p)==v,('original device source/artwork modified',p)
repair=json.loads((H/'connector-clearance-repair.json').read_text());proof=ROOT/repair['mechanical_proof_path'];assert sha(proof)==repair['mechanical_proof_sha256'];assert sha(proof.parent/'CombinedClearanceTrial.FCStd')==repair['mechanical_native_sha256']
mcad=json.loads((H/'mcad.json').read_text());assert mcad['board_sha256']==before
for c in mcad['components']:assert sha(ROOT/c['model'])==c['model_sha256']
pose=json.loads((H/'native-step-pose-checks.json').read_text());assert pose['status']=='pass'and pose['native_board_sha256']==before and pose['package_references']==39
for key,field in [('mechanical_native','mechanical_native_sha256'),('mechanical_STEP','mechanical_STEP_sha256'),('native_KiCad_STEP','native_KiCad_STEP_sha256'),('finished_board_local_STEP','finished_board_local_STEP_sha256')]:assert sha(ROOT/mcad[key])==mcad[field]
assert sha(P)==before
report={'status':'pass: native merged39-part routed candidate, not a fabrication or powered release','board_sha256':before,'native_KiCad_DRC_version':drc['kicad_version'],'DRC_violations':0,'unconnected_items':0,'ignored_checks':drc.get('ignored_checks',[]),'DRC_exclusions':[],'native_refs':39,'mechanical_NPTH':4,'logical_terminal_contracts':155,'physical_pad_instances':len(rows),'mechanical_hold_down_pads':mechanical_hold_down_pads,'native_pad_contracts':rows,'tracks':sum(not isinstance(t,k.PCB_VIA)for t in tracks.values()),'vias':sum(isinstance(t,k.PCB_VIA)for t in tracks.values()),'locked_critical_objects':len(critical['objects']),'PCB_layers':4,'nominal_finished_mm':1,'In1_signal_tracks':0,'nominal_minimum_trace_clearance_mm':[.15,.15],'minimum_via_diameter_drill_mm':[.5,.2],'geometry_exceptions':geom['authorized_position_exceptions'],'frozen_geometry_parity_sha256':sha(H/'geometry-parity.json'),'original_body69_source_and_artwork_unchanged':True,'frozen_study_unchanged':True,'J7_numeric_interface_preserved':True,'independent_retained_endpoint_net_type_function_checks':376,'full_device_ERC_errors':0,'full_device_ERC_warnings':0,'body_PCBA_or_factory_artwork_replacement':False,'fabrication_supplier_acceptance':False,'USB_RF_magnetic_thermal_molding_physical_qualification':False,'reports_sha256':{p:sha(H/p)for p in('drc.json','schematic-checks.json','geometry-parity.json','system-native.xml','single-flange-native.xml','system-erc.json','connector-clearance-repair.json','critical-copper.json','mcad.json','native-step-pose-checks.json','single-flange-independent-terminal-review.json')},'source_invariant_sha256':original['source_invariant_sha256']}
report['all_local_source_sha256']={str(p.relative_to(H)):sha(p)for p in sorted(H.rglob('*'))if p.is_file()and p.name not in('native-checks.json',)and'__pycache__'not in p.parts and not p.name.endswith(('.pyc','.FCStd1'))}
(H/'native-checks.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:report[k]for k in('status','board_sha256','DRC_violations','unconnected_items','native_refs','physical_pad_instances','tracks','vias','locked_critical_objects')}))
