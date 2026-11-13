"""Native editable finished PCB with39 linked actual selected packages.

Copy the frozen verified native assembly, then apply only the two approved link
translations and new source bindings. The original native stays byte-identical.
"""
from pathlib import Path
import hashlib,json,shutil
import FreeCAD as A
H=Path(__file__).resolve().parent;ROOT=H.parents[3];S=H.parent/'single-flange-study';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();data=json.loads((H/'mcad.json').read_text());assert sha(ROOT/data['native_board'])==data['board_sha256']
frozen=S/'SingleFlangePlacement.FCStd';oldsha=sha(frozen);dest=H/'SingleFlangeRouting.FCStd';shutil.copyfile(frozen,dest);d=A.openDocument(str(dest));d.Label='Single flange / routed candidate /39 selected packages';root=d.getObject('SingleFlange');board=d.getObject('PCB');assert root and board
matrix=lambda m:A.Matrix(*[v for row in m for v in row]);changed=[]
for r in data['components']:
 link=d.getObject(r['ref']);assert link and link.TypeId=='App::Link';old=link.LinkPlacement.toMatrix();new=matrix(r['model_to_product_matrix4'])
 if max(abs(a-b)for a,b in zip(old.A,new.A))>1e-9:changed.append(r['ref'])
 link.LinkPlacement=A.Placement(new)
assert set(changed)=={'U75','U71'}
for o in d.Objects:
 if 'RelativeSourceSTEP'in o.PropertiesList:
  o.RelativeSourceSTEP=o.RelativeSourceSTEP.replace('single-flange-study/','single-flange-routing/');assert sha(ROOT/o.RelativeSourceSTEP)==o.SourceSHA256
board.SourceKiCad=data['native_board'];board.SourceSHA256=data['board_sha256'];root.SourceBoardSHA256=data['board_sha256'];root.StudyStatus='Routed candidate; native ERC/DRC and source parity are digital checks. Received dimensions, solder seating, USB/RF/magnetic/material/molding and powered qualification remain open.'
d.recompute();assert d.getObject('BoardOutlineAndHoles').FullyConstrained and d.getObject('FinishedPCB').Length==1 and len(root.Shape.Solids)==142 and root.Shape.isValid()
d.saveAs(str(dest));step=H/'SingleFlangeRouting.step';root.Shape.exportStep(str(step));assert sha(frozen)==oldsha
r={'status':'saved editable native1mm PCB with39 actual source-model links; not physical acceptance','board_sha256':data['board_sha256'],'native_sha256':sha(dest),'normalized_STEP_sha256':sha(step),'frozen_source_native_sha256':oldsha,'frozen_source_unchanged':True,'exact_link_translation_exceptions':changed,'component_links':39,'total_solids':142,'unique_source_models':17,'component_proxy_boxes':False,'PCB_fully_constrained':True,'PCB_finished_Pad_mm':1,'proper_model_poses':True,'solder_stand_off_assumption_mm':0,'physical_fit_or_process_acceptance':False};(H/'component-assembly-checks.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));A.closeDocument(d.Name)
