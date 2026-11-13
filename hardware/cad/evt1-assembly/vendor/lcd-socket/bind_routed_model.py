"""Attach the exact closed OEM model to the derived routed J302 metadata only.

Run with ordinary Python after build_evt1_dock_lcd_socket.py. Frozen circuit,
placement candidates, pads, copper and all non-J302 geometry remain unchanged.
"""
from pathlib import Path
import hashlib,json,shutil,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
sys.path.insert(0,str(ROOT/'tools'))
import kicad_sexp as s
CONTROL=ROOT/'hardware/pcb/evt1/dock-control'
OUT=CONTROL/'routed-lid'
PCB=OUT/'dock-lid-routed.kicad_pcb'
MODEL=CONTROL/'DockControl.3dshapes/Molex_52437-2771_ClosedEnvelope.step'
URI='${KIPRJMOD}/../DockControl.3dshapes/'+MODEL.name
REPORT=OUT/'lcd-socket-model-binding.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def reference(f):
    return next(t[2].value for t in s.children(f,'fp_text')if t[1].value=='reference')

def without_allowed_metadata(tree):
    # Parse a fresh clone so the comparison cannot share mutable node objects.
    clone=s.parse(s.dump(tree))
    footprints=s.children(clone,'footprint') if clone[0].value=='kicad_pcb' else [clone]
    for f in footprints:
        if clone[0].value=='kicad_pcb'and reference(f)!='J302':continue
        f[:]=[n for n in f if not(isinstance(n,list)and n and n[0].value=='model')]
        for line in s.children(f,'fp_line'):
            if s.child(line,'layer')[1].value=='F.CrtYd':
                for n in ('start','end'):
                    point=s.child(line,n)
                    if abs(float(point[2].value)-5.35)<1e-8:point[2]=s.atom('5.1')
    return s.dump(clone)

def patch(f):
    old_models=s.children(f,'model');assert not old_models,'Model already attached'
    changed=0
    for line in s.children(f,'fp_line'):
        if s.child(line,'layer')[1].value!='F.CrtYd':continue
        for n in ('start','end'):
            point=s.child(line,n)
            if abs(float(point[2].value)-5.1)<1e-8:
                point[2]=s.atom('5.35');changed+=1
    assert changed==4,('Expected only front courtyard edge changes',changed)
    f.append(s.parse('(model "'+URI+'"(offset(xyz 0 0 0))(scale(xyz 1 1 1))(rotate(xyz 0 0 0)))'))

def main():
    assert not REPORT.exists(),'Already bound; retain the existing source-bound record'
    checks=json.loads((HERE/'native-checks.json').read_text())
    assert checks['builder_sha256']==sha(ROOT/'tools/build_evt1_dock_lcd_socket.py')
    source=HERE/'Molex524372771ClosedBoardFrame.step'
    assert checks['board_model_export']['SHA256']==sha(source)
    assert checks['board_model_export']['solids']==2 and checks['board_model_export']['faces']==1001
    prior=sha(PCB)
    assert prior=='a7f45608992ae84fcc229e2492af9244682d75f991f0f522f98c2046b7ecad08',prior
    tree=s.parse(PCB.read_text());fp=next(f for f in s.children(tree,'footprint')if reference(f)=='J302')
    library=OUT/'DockControl.pretty'/(fp[1].value.split(':')[1]+'.kicad_mod')
    oldlib=sha(library);lib=s.parse(library.read_text())
    baseline=without_allowed_metadata(tree);baseline_lib=without_allowed_metadata(lib)
    patch(fp);patch(lib)
    assert without_allowed_metadata(tree)==baseline,'Unexpected PCB change'
    assert without_allowed_metadata(lib)==baseline_lib,'Unexpected footprint change'
    MODEL.parent.mkdir(exist_ok=True);shutil.copyfile(source,MODEL)
    archive=OUT/'before-socket-model.kicad_pcb';assert not archive.exists()
    shutil.copyfile(PCB,archive)
    library.write_text(s.dump(lib)+'\n');PCB.write_text(s.dump(tree)+'\n')
    record={
        'scope':'J302 OEM model identity attachment and 0.25mm closed-front courtyard margin only',
        'previous_electrical_routing_board_SHA256':prior,'board_after_model_binding_SHA256':sha(PCB),
        'previous_routed_native_snapshot':archive.name,
        'library':str(library.relative_to(CONTROL)),'library_before_SHA256':oldlib,'library_after_SHA256':sha(library),
        'model':str(MODEL.relative_to(CONTROL)),'model_SHA256':sha(MODEL),
        'model_source':str(source.relative_to(ROOT)),'model_source_SHA256':sha(source),
        'CAD_native_checks':str((HERE/'native-checks.json').relative_to(ROOT)),
        'CAD_native_checks_SHA256':sha(HERE/'native-checks.json'),
        'source_manifest_SHA256':sha(HERE/'source-manifest.json'),
        'binder_SHA256':sha(Path(__file__)),
        'OEM_transform_to_physical_board_XYZ':[[1,0,0,0],[0,0,-1,-.6],[0,1,0,0],[0,0,0,1]],
        'OEM_actuator_translation_before_transform_mm':[0,0,-1.6],
        'KiCad_model_offset_mm':[0,0,0],'KiCad_model_rotation_deg':[0,0,0],'KiCad_model_scale':[1,1,1],
        'model_frame':'Physical board X right/Y up/Z component height; model mouth-Y maps native footprint+Y',
        'model_pin1_solder_tail_top_centre_mm':[-6.5,-.15,.14],
        'expected_closed_model_bounds_mm':[-10.05,-5.1,-.04,10.05,.1,2],
        'J302_land_row_dock_XY_mm':[0,114],'closed_front_dock_Y_mm':108.9,
        'courtyard_front_native_Y_mm':5.35,'courtyard_front_dock_Y_mm':108.65,
        'closed_front_courtyard_margin_mm':.25,'open_actuator_front_dock_Y_mm':107.3,
        'unmodeled_opening_access':'Assembly-only slide-lock access must extend beyond the closed courtyard.',
        'pads_tracks_vias_fills_zones_other_footprints_unchanged':True,
        'frozen_circuit_and_placement_sources_modified':False,
        'native_KiCad_STEP_import_check':'Pending separate actual exporter check',
        'loaded_contact_height_and_received_mating_qualified':False}
    REPORT.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({'board_SHA256':sha(PCB),'model_SHA256':sha(MODEL),'non_metadata_native_tokens_unchanged':True}))

if __name__=='__main__':main()
