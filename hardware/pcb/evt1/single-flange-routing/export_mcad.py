"""Read-only exact native footprint/model pose handoff in the product frame."""
from pathlib import Path
import hashlib,json,math,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sys.path.insert(0,str(ROOT/'tools'));import kicad_sexp as s
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
mm=lambda a,b:[[sum(a[i][k]*b[k][j]for k in range(3))for j in range(3)]for i in range(3)]
mv=lambda a,v:[sum(a[i][k]*v[k]for k in range(3))for i in range(3)]
Rprod=[[1,0,0],[0,0,-1],[0,1,0]]
tree=s.parse((H/'single-flange.kicad_pcb').read_text());meta=json.loads((H/'pcb-state.json').read_text());assert sha(H/'single-flange.kicad_pcb')==meta['board_sha256'];parts=[];holes=[]
for fp in s.children(tree,'footprint'):
 ref=next(a[2].value for a in s.children(fp,'fp_text')if a[1].value=='reference');at=s.child(fp,'at');x=float(at[1].value)-100;z=100-float(at[2].value);theta=float(at[3].value)if len(at)>3 else 0;back=s.value(fp,'layer')=='B.Cu'
 if ref.startswith('MH'):holes.append({'ref':ref,'product_XZ_mm':[x,z],'drill_mm':1.6});continue
 models=s.children(fp,'model');assert len(models)==1;model=models[0];p=Path(model[1].value.replace('${KIPRJMOD}',str(H)));assert p.is_file()
 vectors={a:[float(n.value)for n in s.child(s.child(model,a),'xyz')[1:]]for a in('offset','rotate','scale')};assert vectors['rotate']==[0,0,0]and vectors['scale']==[1,1,1]
 a=math.radians(theta);c=math.cos(a);d=math.sin(a);rz=[[c,-d,0],[d,c,0],[0,0,1]];flip=[[1,0,0],[0,-1,0],[0,0,-1]]if back else[[1,0,0],[0,1,0],[0,0,1]]
 rot=mm(Rprod,mm(rz,flip));delta=mv(rot,vectors['offset']);base=[x,-25.952-(0 if back else 1),z];trans=[base[i]+delta[i]for i in range(3)];matrix=[[round(rot[i][j],12)for j in range(3)]+[round(trans[i],9)]for i in range(3)]+[[0,0,0,1]]
 parts.append({'ref':ref,'value':next(a[2].value for a in s.children(fp,'fp_text')if a[1].value=='value'),'side':'B'if back else'F','footprint_product_XZ_mm':[x,z],'native_angle_deg':theta,'model':str(p.relative_to(ROOT)),'model_sha256':sha(p),'model_vectors_native':vectors,'model_to_product_matrix4':matrix,'rigid_transform_determinant':1})
assert len(parts)==39
r={'status':'exact native model pose handoff; no nominal package models substitute for received maximum qualification','native_board':str((H/'single-flange.kicad_pcb').relative_to(ROOT)),'board_sha256':meta['board_sha256'],'native_KiCad_STEP':str((H/'NativeKiCadRouted.step').relative_to(ROOT)),'native_KiCad_STEP_sha256':sha(H/'NativeKiCadRouted.step'),'board_thickness_mm':1,'board_F_productY_mm':-26.952,'board_B_productY_mm':-25.952,'native_xy_to_product_XZ':'productX=nativeX−100;productZ=100−nativeY','raw_native_STEP_axis_mapping_only_matrix4':[[1,0,0,0],[0,0,-1,-25.952],[0,1,0,0],[0,0,0,1]],'whole_STEP_frame':'Raw KiCad --user-origin100x100mm; STEP+Yup maps product+Z. This axis mapping alone DOES NOT correct native solder/mask seating offsets; use per-ref matrices or SingleFlangeRouting.FCStd for physical datums','raw_KiCad_export_seating_z_mm':{'F':.995,'B':-.085,'FR4_bottom':0,'FR4_top':.91},'physical_model_mounting_assumption':'Models are located at the agreed finished1mmPCB F/B planes; solder stand-off and received seating are not qualified or silently credited','mechanical_native':'hardware/pcb/evt1/single-flange-routing/SingleFlangeRouting.FCStd','mechanical_STEP':'hardware/pcb/evt1/single-flange-routing/SingleFlangeRouting.step','outline_product_XZ_mm':meta['outline_product_XZ_mm'],'holes':holes,'components':parts,'battery_growth_bounds_product_mm':[6.75,-22.6,-10.75,40.25,-15.2,10.75],'permanent_F_barrier_keepout_XZ_mm':[-20.7,-3.15,4.7,12.65],'F_barrier_exceptions':['SW1','SW2','CT1','CT2','CT3','CT4'],'B_contact_bearing_posts':{'centres_product_XZ_mm':[[-16,10],[-10,10],[-4,10],[2,10]],'OD_mm':4,'ID_mm':1.2,'Yspan_mm':[-25.952,-22.6]},'RF_antenna_region_product_XZ_mm':[-41,-6.6,-35.6,6.6],'RF_copper_keepout':'all4Cu layers of antenna region plus actual open board edge notch;15mm full housing guidance and final range testing remain qualification requirements','body_PCB_altered':False,'physical_fit_or_RF_acceptance':False}
frozen=H.parent/'single-flange-study';g=json.loads((H/'geometry-parity.json').read_text());assert g['routed_candidate_board_sha256']==r['board_sha256']
old=json.loads((frozen/'mcad.json').read_text());assert sha(frozen/'SingleFlangePlacement.FCStd')==old['finished_board_native_sha256']
for key in('finished_board_local_STEP','finished_board_local_STEP_sha256','finished_board_native','finished_board_native_sha256','finished_board_binding_sha256'):r[key]=old[key]
r['finished_board_geometry_proof_sha256']=sha(H/'geometry-parity.json');r['finished_board_binding_uses_frozen_geometry']=True;r['frozen_study_MCAD_sha256']=sha(frozen/'mcad.json');r['authorized_clearance_repair_sha256']=sha(H/'connector-clearance-repair.json')
if(H/'SingleFlangeRouting.FCStd').exists():r['mechanical_native_sha256']=sha(H/'SingleFlangeRouting.FCStd')
if(H/'SingleFlangeRouting.step').exists():r['mechanical_STEP_sha256']=sha(H/'SingleFlangeRouting.step')
(H/'mcad.json').write_text(json.dumps(r,indent=2)+'\n');print('39 proper model transforms, native board/STEP hashes bound')
