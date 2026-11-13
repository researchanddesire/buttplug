"""Bind local selected-part models and a supplier-reviewable stackup."""
from pathlib import Path
import json
import shutil
import sys
import build_pcbs as m
from route_pcbs import ctx
k=m.k
sys.path.insert(0,str(m.ROOT/'tools'))
import kicad_sexp as s

def main(side):
    folder,path,b=ctx(side);before=m.sha(path)
    models=json.loads((m.HERE/'models/source-manifest.json').read_text())
    local=folder/'DockUV.pretty';local.mkdir(exist_ok=True)
    assignments={}
    for source in(m.HERE/side/'DockUV.pretty').glob('*.kicad_mod'):
        name=source.stem;tree=s.parse(source.read_text())
        tree[:]=[n for n in tree if s.tag(n)!='model']
        if name in models['parts']:
            row=models['parts'][name];target=m.HERE/'models'/row['local_step']
            assert m.sha(target)==row['local_step_sha256']
            offset=row.get('KiCad_model_offset_XYZ_mm',[0,0,0]);rot=row.get('KiCad_model_rotation_XYZ_deg',[0,0,0])
            modelpath='$'+'{KIPRJMOD}/../../models/'+row['local_step']
            tree.append(s.parse('(model '+json.dumps(modelpath)+' (offset(xyz '+' '.join(map(str,offset))+')) (scale(xyz 1 1 1)) (rotate(xyz '+' '.join(map(str,rot))+')))'))
            assignments[name]=(modelpath,offset,rot)
        s.write(local/source.name,tree)
    (folder/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "DockUV") (type "KiCad") (uri "'+'$'+'{KIPRJMOD}/DockUV.pretty") (options "") (descr "Derived frozen UV footprints with local selected-part models")))\n')
    for f in b.GetFootprints():
        name=str(f.GetFPID().GetLibItemName());f.Models().clear()
        if name in assignments:
            fn,offset,rot=assignments[name];model=k.FP_3DMODEL();model.m_Filename=fn
            model.m_Offset.x,model.m_Offset.y,model.m_Offset.z=offset
            model.m_Rotation.x,model.m_Rotation.y,model.m_Rotation.z=rot
            f.Models().push_back(model)
    m.save(b,path)
    tree=s.parse(path.read_text());setup=s.child(tree,'setup')
    setup[:]=[n for n in setup if s.tag(n)!='stackup']
    setup.insert(1,s.parse('''(stackup
      (layer "F.SilkS"(type "Top Silk Screen"))
      (layer "F.Paste"(type "Top Solder Paste"))
      (layer "F.Mask"(type "Top Solder Mask")(thickness 0.01))
      (layer "F.Cu"(type "copper")(thickness 0.07))
      (layer "dielectric 1"(type "core")(thickness 0.86)(material "FR4")(epsilon_r 4.5)(loss_tangent 0.02))
      (layer "B.Cu"(type "copper")(thickness 0.07))
      (layer "B.Mask"(type "Bottom Solder Mask")(thickness 0.01))
      (layer "B.Paste"(type "Bottom Solder Paste"))
      (layer "B.SilkS"(type "Bottom Silk Screen"))
      (copper_finish "ENIG")(dielectric_constraints no))'''))
    s.write(path,tree)
    data={'status':'routed native candidate; supplier stackup and powered/thermal acceptance pending',
          'before_models_sha256':before,'native_board_sha256':m.sha(path),'models_manifest_sha256':m.sha(m.HERE/'models/source-manifest.json'),
          'finalizer_sha256':m.sha(Path(__file__)),'derived_footprints':{str(p.relative_to(folder)):m.sha(p)for p in local.glob('*.kicad_mod')},
          'stackup':{'nominal_copper_plus_FR4_mm':1,'FR4_core_mm':.86,'outer_copper_um_each':70,'mask_um_each':10,'coatings_not_in_nominal_thickness':True,'finish':'ENIG','minimum_track_clearance_mm':.2,'minimum_drill_mm':.3,'minimum_annulus_mm':.15,'supplier_acceptance':False},
          'models':{n:{'relative_path':a[0],'offset_mm':a[1],'rotation_deg':a[2]}for n,a in assignments.items()},
          'thermal_attachment':{'B_contact_region_near_each_LED_planar_mm':{'left':[-47.8,92.5,-36.2,95.5],'right':[36.2,92.5,47.8,95.5]},
            'electrical_isolation_required':'Each LED terminal copper/via array is a different electrical net. Any common metal backing requires a qualified insulating thermal interface; soldermask is not credited.',
            'local_sensors':'Remote NTC/67L045 wire solder lands on right arm; place sensors on actual hottest heatspreader/driver region and qualify lag. Mechanical retention and exact backing/pad remain open.',
            'not_credited':'FR4 thermal path does not inherit Vishay24.4K/W Al-MCPCB rating; no predicted optical output/dose or measured temperature claim'},
          'physical_fit':False,'thermal_validation':False,'full_product_order_ready':False}
    (folder/'assembly-models.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({'board':str(path),'selected_models':len(assignments),'stackup_mm':1}))

if __name__=='__main__':main(sys.argv[1])
