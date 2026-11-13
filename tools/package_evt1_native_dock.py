"""Package the verified editable dock and relative sources; never a build release."""
from pathlib import Path
import hashlib
import json
import shutil
import zipfile
import ast

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/cad/evt1-assembly'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    native=OUT/'DockAssembly.FCStd';digest=sha(native)
    reports={name:json.loads((OUT/name).read_text())for name in
             ('review.json','native-check.json','loading-check.json','portable-check.json')}
    assert all(r['native_sha256']==digest for r in reports.values())
    assert reports['native-check.json']['nominal_geometry_pass']
    assert reports['loading-check.json']['pass'] and reports['portable-check.json']['pass']
    assert reports['review.json']['builder_sha256']==sha(ROOT/'tools/build_evt1_native_dock.py')
    assert reports['native-check.json']['verifier_sha256']==sha(ROOT/'tools/verify_evt1_native_dock.py')
    assert reports['loading-check.json']['verifier_sha256']==sha(ROOT/'tools/verify_evt1_dock_loading.py')
    for name in ('native-check.json','loading-check.json'):
        assert reports[name]['intersection_helper_sha256']==sha(ROOT/'tools/evt1_brep_checks.py'),name
    assert reports['portable-check.json']['verifier_sha256']==sha(ROOT/'tools/verify_evt1_dock_portability.py')
    for name,digest_helper in reports['review.json']['authoring_helpers_sha256'].items():
        assert sha(ROOT/'tools'/name)==digest_helper,name
    for row in reports['review.json']['external_sources']:
        assert sha(ROOT/row['file'])==row['sha256'],row['file']
    main_folder=ROOT/'hardware/pcb/evt1/dock-main'
    main_board=main_folder/'dock-main.kicad_pcb'
    main_checks=json.loads((main_folder/'native-checks.json').read_text())
    main_parity=json.loads((main_folder/'mcad-geometry-parity.json').read_text())
    imported_main=json.loads((OUT/'pcb/MainPCB-stepup-import.json').read_text())
    assert main_checks['board_sha256']==main_parity['board_sha256']==sha(main_board)
    assert main_parity['snapshot_sha256']==imported_main['board_sha256']
    assert main_parity['electrical_references']==main_checks['electrical_references']==150
    assert main_checks['DRC_violations']==main_checks['DRC_unconnected']==main_checks['DRC_exclusions']==0
    assert main_checks['ignored_rules']==[]
    for relative,digest_source in reports['portable-check.json']['external_files'].items():
        assert sha(OUT/relative)==digest_source,relative
    paths=[OUT/p for p in ('DockAssembly.FCStd','DockAssembly-native.png',
           'DockAssembly-open-native.png','README.md','review.json','native-check.json',
           'loading-check.json','portable-check.json')]
    paths += [p for folder in ('pcb','sources','vendor')for p in (OUT/folder).rglob('*')
              if p.is_file() and p.suffix in ('.FCStd','.png','.STEP','.step','.stp','.json','.md')]
    tool_names=set(reports['review.json']['authoring_helpers_sha256'])|{
        'build_evt1_native_dock.py','import_evt1_stepup.py',
        'import_evt1_functional_dock_pcbs.py','verify_evt1_native_dock.py',
        'verify_evt1_dock_loading.py','verify_evt1_dock_portability.py',
        'package_evt1_native_dock.py'}
    pending=list(tool_names)
    while pending:
        name=pending.pop()
        for node in ast.walk(ast.parse((ROOT/'tools'/name).read_text())):
            modules=[a.name for a in node.names]if isinstance(node,ast.Import)else[node.module]if isinstance(node,ast.ImportFrom)and node.module else[]
            for module in modules:
                dependency=module.split('.')[0]+'.py'
                if (ROOT/'tools'/dependency).is_file()and dependency not in tool_names:
                    tool_names.add(dependency);pending.append(dependency)
    paths += [ROOT/'tools'/name for name in tool_names]
    paths += [main_folder/name for name in ('dock-main.kicad_pcb','dock-main.kicad_pro',
               'dock-main.kicad_dru','native-checks.json','mcad-geometry-parity.json',
               'mcad-model-coverage.json','mcad-model-checks.json')]
    for name in ('UVBase','UVLid','LidUI','MainPCB'):
        imported=json.loads((OUT/'pcb'/(name+'-stepup-import.json')).read_text())
        source=ROOT/imported['board']
        assert sha(source)==imported['board_sha256'],name
        paths.append(source)
        for model in imported['selected_models'].values():
            path=ROOT/model['path'];assert sha(path)==model['sha256'],path
            paths.append(path)
        binding=imported.get('model_coverage_binding')
        if binding:
            path=ROOT/binding['file'];assert sha(path)==binding['sha256'],path
            paths.append(path)
    for domain in ('dock','pins'):
        paths += [ROOT/'hardware/pcb/evt1'/domain/(domain+'-evt1.kicad_pcb'),
                  ROOT/'hardware/pcb/evt1'/domain/'mcad.json']
    paths=sorted(set(paths))
    assert all(p.is_file() for p in paths)
    assert not any(p.suffix.lower()=='.stl' for p in paths)
    archive=OUT/'Native-Dock-Review.zip'
    if archive.exists():
        with zipfile.ZipFile(archive) as previous:
            old_manifest=json.loads(previous.read('review-manifest.json'))
            old_native=old_manifest.get('native_sha256')
            if old_native is None:
                old_native=hashlib.sha256(previous.read('hardware/cad/evt1-assembly/DockAssembly.FCStd')).hexdigest()
        if old_native!=digest:
            prior=OUT/'archive'/('native-review-'+old_native[:12]+'.zip')
            prior.parent.mkdir(exist_ok=True)
            if prior.exists():assert sha(prior)==sha(archive),'Preserve distinct previous bundle'
            else:shutil.copyfile(archive,prior)
    manifest={'scope':'Editable native CAD integration review; no print/order/powered release',
              'native_sha256':digest,'files_sha256':{str(p.relative_to(ROOT)):sha(p)for p in paths},
              'nominal_geometry_pass':True,'sampled_loading_pass':True,'cold_relocation_pass':True,
              'shared_base_PCB':{'routed_board_sha256':main_checks['board_sha256'],
                                'StepUp_snapshot_sha256':main_parity['snapshot_sha256'],
                                'exact_MCAD_geometry_parity':True,'electrical_references':150,
                                'native_DRC_violations':0,'unconnected_items':0},
              'physical_validation':False,'full_product_order_ready':False}
    temporary=archive.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as z:
        for p in paths:z.write(p,str(p.relative_to(ROOT)))
        z.writestr('review-manifest.json',json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(temporary) as z:
        assert z.testzip() is None
        for relative,digest_file in manifest['files_sha256'].items():
            assert hashlib.sha256(z.read(relative)).hexdigest()==digest_file,relative
    temporary.replace(archive)
    print(json.dumps({'archive':str(archive.relative_to(ROOT)),'files':len(paths)+1,
                      'bytes':archive.stat().st_size,'native_sha256':digest},indent=2))


if __name__=='__main__':main()
