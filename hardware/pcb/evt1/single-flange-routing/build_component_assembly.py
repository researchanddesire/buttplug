"""Native editable finished PCB with39 linked actual selected packages.

Copy the frozen verified native assembly, then apply the two approved link
translations, four target drill diameters, and new source bindings.
"""
from pathlib import Path
import hashlib,json,math,shutil
import FreeCAD as A,Part,Sketcher


def assembly_shape(root, board):
    shapes = [board.Shape]
    for link in root.Group:
        if link.TypeId != 'App::Link':
            continue
        source = link.LinkedObject
        transform = link.LinkPlacement * source.Placement.inverse()
        for component in source.Group:
            shape = component.Shape.copy()
            shape.Placement = transform * shape.Placement
            shapes.append(shape)
    return Part.makeCompound(shapes)


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
profile=d.getObject('BoardOutlineAndHoles')
holes={tuple(r['product_XZ_mm']):r['drill_mm'] for r in data['holes'] if r['ref'].startswith('CT')}
target_indices=[i for i,curve in enumerate(profile.Geometry)
                if isinstance(curve,Part.Circle) and (curve.Center.x,curve.Center.y) in holes]
assert len(target_indices)==len(holes)==4
for i in reversed(target_indices):
 curve=profile.Geometry[i];diameter=holes[curve.Center.x,curve.Center.y]
 assert math.isclose(curve.Radius,.4318,abs_tol=1e-8)
 profile.delGeometry(i)
 index=profile.addGeometry(Part.Circle(curve.Center,curve.Axis,diameter/2),False)
 profile.addConstraint(Sketcher.Constraint('Block',index))
board.SourceKiCad=data['native_board'];board.SourceSHA256=data['board_sha256'];root.SourceBoardSHA256=data['board_sha256'];root.StudyStatus='Routed candidate; native ERC/DRC and source parity are digital checks. Received dimensions, solder seating, USB/RF/magnetic/material/molding and powered qualification remain open.'
d.recompute()
assembly=assembly_shape(root,board)
assert profile.FullyConstrained and d.getObject('FinishedPCB').Length==1 and len(assembly.Solids)==142 and assembly.isValid()
d.saveAs(str(dest));step=H/'SingleFlangeRouting.step';assembly.exportStep(str(step));assert sha(frozen)==oldsha
local=board.Shape.copy();local.Placement=board.Placement.inverse()*local.Placement
out=H/'FinishedPCB_local.step';local.exportStep(str(out));cold=Part.read(str(out))
assert cold.isValid() and len(cold.Solids)==1 and abs(cold.Volume-local.Volume)<1e-6
bb=local.optimalBoundingBox(False,False)
binding={'status':'pass: editable 1 mm laminate with four updated target drills',
 'board_sha256':data['board_sha256'],'native_source':str(dest.relative_to(ROOT)),
 'native_source_sha256':sha(dest),'Body':board.Name,'Tip':'FinishedPCB','profile':profile.Name,
 'fully_constrained_profile':True,'Pad_Length_mm':1.0,'STEP':str(out.relative_to(ROOT)),
 'STEP_sha256':sha(out),'STEP_bounds_local_mm':[getattr(bb,n) for n in ('XMin','YMin','ZMin','XMax','YMax','ZMax')],
 'solid_count':1,'volume_mm3':local.Volume,'nominal_target_drill_diameter_mm':1.02,
 'target_holes':[{'ref':r['ref'],'center_product_XZ_mm':r['product_XZ_mm']} for r in data['holes'] if r['ref'].startswith('CT')],
 'laminate_removed_mm3':sum(math.pi*((drill/2)**2-.4318**2) for drill in holes.values()),
 'proper_local_to_product_matrix4':[[1,0,0,0],[0,0,-1,-25.952],[0,1,0,0],[0,0,0,1]],
 'physical_acceptance':False}
(H/'finished-board.json').write_text(json.dumps(binding,indent=2)+'\n')
r={'status':'saved editable native1mm PCB with39 actual source-model links; not physical acceptance','board_sha256':data['board_sha256'],'native_sha256':sha(dest),'normalized_STEP_sha256':sha(step),'frozen_source_native_sha256':oldsha,'frozen_source_unchanged':True,'exact_link_translation_exceptions':changed,'component_links':39,'total_solids':142,'unique_source_models':17,'component_proxy_boxes':False,'PCB_fully_constrained':True,'PCB_finished_Pad_mm':1,'proper_model_poses':True,'solder_stand_off_assumption_mm':0,'physical_fit_or_process_acceptance':False};(H/'component-assembly-checks.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));A.closeDocument(d.Name)
