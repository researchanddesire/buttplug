"""Pure/native-file mechanical geometry parity; never load two KiCad7 BOARDs."""
from pathlib import Path
import hashlib,json,re,sys,decimal
H=Path(__file__).resolve().parent;S=H.parent/'single-flange-study';ROOT=H.parents[3];sys.path.insert(0,str(ROOT/'tools'));import kicad_sexp as s
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def norm(n):
 if isinstance(n,s.Atom):
  if n.raw.startswith('"'):return n.value
  try:return str(decimal.Decimal(n.value).normalize())
  except decimal.InvalidOperation:return n.value
 return [norm(q)for q in n]
def fps(t,translations=None):
 out={}
 for f in s.children(t,'footprint'):
  ref=next(q[2].value for q in s.children(f,'fp_text')if q[1].value=='reference')
  if translations and ref in translations:
   old,new=translations[ref]['old'],translations[ref]['new'];at=s.child(f,'at')
   assert [float(at[1].value)-100,100-float(at[2].value)]==old
   at[1]=s.Atom(str(100+new[0]));at[2]=s.Atom(str(100-new[1]))
  out[ref]=norm([q for q in f if not(isinstance(q,list)and s.tag(q)in('path','sheetfile','sheetname'))])
 return out
source=S/'single-flange-placement.kicad_pcb';p=H/'single-flange.kicad_pcb';a=s.parse(source.read_text());b=s.parse(p.read_text());exceptions={}
repair=H/'connector-clearance-repair.json'
if repair.exists():
 x=json.loads(repair.read_text());exceptions=x['positions_product_XZ_mm'];assert exceptions=={'U75':{'old':[-1,4],'new':[6.3,9]},'U71':{'old':[-1,-6],'new':[-1,-7]}}
 assert sha(ROOT/x['mechanical_proof_path'])==x['mechanical_proof_sha256']
old=fps(a,exceptions);new=fps(b);assert set(old)==set(new)and len(old)==43
for r in old:assert old[r]==new[r],('mechanical/source footprint changed',r)
edges=lambda t:sorted(json.dumps(norm(q),sort_keys=True)for q in t if isinstance(q,list)and s.tag(q).startswith('gr_')and s.value(q,'layer')=='Edge.Cuts')
assert edges(a)==edges(b);assert s.value(s.child(a,'general'),'thickness')==s.value(s.child(b,'general'),'thickness')=='1';assert norm(s.child(a,'layers'))==norm(s.child(b,'layers'))
models={}
for folder in('Selected.pretty','Selected.3dshapes'):
 for q in(S/folder).glob('*'):
  if q.is_file():assert sha(q)==sha(H/folder/q.name),('selected source library/model changed',q);models[str(q.relative_to(S))]=sha(q)
r={'status':'pass: frozen geometry exact except the authorized U75/U71 translations','frozen_study_board_sha256':sha(source),'routed_candidate_board_sha256':sha(p),'preserved_electrical_positions':39-len(exceptions),'authorized_position_exceptions':exceptions,'authorized_repair_sha256':sha(repair)if exceptions else None,'preserved_mechanical_NPTH':4,'footprint_and_pad_and_model_tokens_exact_except_schematic_path_and_two_authorized_global_positions':True,'outline_edge_UUIDs_and_geometry_exact':True,'nominal_board_mm':1,'Cu_layers':4,'selected_library_and_model_sha256':models,'frozen_study_MCAD_sha256':sha(S/'mcad.json'),'frozen_FreeCAD_sha256':sha(S/'SingleFlangePlacement.FCStd'),'physical_validation':False};(H/'geometry-parity.json').write_text(json.dumps(r,indent=2)+'\n');print(r['status'])
