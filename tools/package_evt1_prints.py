"""Package checked dock prints and the separate device-board fit checkpoint.

No slicer/printer dispatch, supplier submission, purchasing or full-product
release. Working routing seeds and private references are never included.
"""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parents[1]
CAD=ROOT/'hardware/cad/manufacturing-layout'
PCB=ROOT/'hardware/pcb/evt1'
IMAGES=ROOT/'developer-docs/docs/assets'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def quote(domain):
    folder=PCB/domain/'fabrication-quote';manifest=json.loads((folder/'manifest.json').read_text())
    path=folder/(domain+'-evt1-fabrication-quote.zip')
    assert sha(PCB/domain/(domain+'-evt1.kicad_pcb'))==manifest['board_sha256']
    assert sha(PCB/'validation.json')==manifest['electrical_validation_sha256']
    assert sha(PCB/'native-checks.json')==manifest['native_checks_sha256']
    assert sha(path)==manifest['quote_zip_sha256']
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        for name,digest in manifest['files'].items():assert hashlib.sha256(archive.read(name)).hexdigest()==digest
        job=json.loads(archive.read(domain+'-evt1-job.gbrjob'))
        copper=[v for v in job['FilesAttributes'] if v['FileFunction'].startswith('Copper,')]
        assert len(copper)==manifest['fabrication_request']['layers']
        assert all(v['Path'] in archive.namelist() for v in job['FilesAttributes'])
    return path


def assembly(domain):
    folder=PCB/domain/'assembly-quote';manifest=json.loads((folder/'manifest.json').read_text())
    path=folder/(domain+'-evt1-assembly-quote.zip')
    assert sha(PCB/domain/(domain+'-evt1.kicad_pcb'))==manifest['board_sha256']
    assert sha(PCB/'parts-selection.json')==manifest['parts_selection_sha256']
    assert sha(PCB/'native-checks.json')==manifest['native_checks_sha256']
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        for name,digest in manifest['files'].items():assert hashlib.sha256(archive.read(name)).hexdigest()==digest
    return path


def package(folder,name,files,scope):
    data={name:path.read_bytes() for name,path in files.items()}
    manifest={'scope':scope,'files':{n:hashlib.sha256(b).hexdigest() for n,b in data.items()},'packager_sha256':sha(Path(__file__)),'physical_validation':False,'full_product_order_ready':False}
    data['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    path=folder/name
    with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        for n,blob in data.items():archive.writestr(n,blob)
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None and set(archive.namelist())==set(data)
        assert all(archive.read(n)==blob for n,blob in data.items())
    path.with_suffix('.sha256').write_text(sha(path)+'  '+path.name+'\n')
    try:display=str(path.relative_to(ROOT))
    except ValueError:display=str(path)
    print(json.dumps({'archive':display,'members':len(data),'bytes':path.stat().st_size,'sha256':sha(path)}))


def loom_files():
    cable=ROOT/'hardware/cables/evt1';folder=CAD/'evt1-integration/loom'
    logical=json.loads((cable/'logical-source.json').read_text())
    review=json.loads((cable/'logical-review.json').read_text())
    assert review['pass']
    assert sha(cable/'logical-source.json')==review['logical_source_sha256']
    assert sha(ROOT/'tools/verify_evt1_looms.py')==review['verifier_sha256']
    files={name:cable/name for name in ('README.md','requirements.txt','source-review.json','wire-stock.csv','logical-source.json','logical-review.json')}
    for name,digest in logical['files'].items():
        assert sha(cable/name)==digest;files[name]=cable/name
    if logical['interboard_spans_verified']:
        geometry=json.loads((folder/'review.json').read_text())
        assert geometry['geometry_checks']['pass']
        assert sha(folder/'EVT1Loom.FCStd')==logical['loom_native_sha256']==geometry['native_sha256']
        assert sha(folder/'review.json')==logical['loom_review_sha256']
        assert sha(ROOT/'tools/verify_evt1_loom_cad.py')==geometry['geometry_checks']['verifier_sha256']
        assert sha(ROOT/'tools/build_evt1_loom_cad.py')==geometry['builder_sha256']
        assert sha(ROOT/'tools/evt1_loom_paths.py')==geometry['path_builder_sha256']
        assert sha(CAD/'evt1-integration/EVT1Product.FCStd')==geometry['source_product_native_sha256']
        files['routing-plan.json']=cable/'routing-plan.json'
        files['cad/EVT1Loom.FCStd']=folder/'EVT1Loom.FCStd'
        files['cad/README.md']=folder/'README.md'
        files['reports/wire-form-review.json']=folder/'review.json'
        picture=json.loads((IMAGES/'evt1-loom.json').read_text())
        assert picture['native_sha256']==geometry['native_sha256']
        assert picture['loom_review_sha256']==sha(folder/'review.json')
        assert picture['renderer_sha256']==sha(ROOT/'tools/render_evt1_loom.py')
        files['images/evt1-loom.png']=IMAGES/'evt1-loom.png'
    return files,review


def main():
    validation=json.loads((PCB/'validation.json').read_text())
    for n,h in validation['source_sha256'].items():assert sha(ROOT/n)==h,('Electrical source stale',n)
    dock=CAD/'charging-dock';r=json.loads((dock/'review.json').read_text())
    assert sha(dock/'ChargingDock.FCStd')==r['native_sha256'] and 'geometry_checks' in r
    assert 'contact_face_seal_conditional_tolerance_arithmetic' in r['geometry_checks']
    assert sha(ROOT/'tools/verify_charging_dock.py')==r['verifier_sha256']
    assert sha(dock/'contact-seal-spec.json')==r['contact_seal_spec_sha256']
    trial_folder=dock/'contact-seal-trial';trial_report=json.loads((trial_folder/'review.json').read_text())
    assert sha(trial_folder/'ContactSealTrial.FCStd')==trial_report['native_sha256'] and 'geometry_checks' in trial_report
    assert sha(ROOT/'tools/verify_contact_seal_trial.py')==trial_report['verifier_sha256']
    assert trial_report['source_dock_native_sha256']==r['native_sha256']
    assert trial_report['contact_seal_spec_sha256']==r['contact_seal_spec_sha256']
    meta=json.loads((IMAGES/'contact-seal-trial.json').read_text());assert meta['native_sha256']==trial_report['native_sha256']
    trial_files={'README.md':trial_folder/'README.md','CONTACT-POST-INERT-RFQ.md':trial_folder/'CONTACT-POST-INERT-RFQ.md',
        'cad/ContactSealTrial.FCStd':trial_folder/'ContactSealTrial.FCStd','reports/review.json':trial_folder/'review.json',
        'contact-seal-spec.json':dock/'contact-seal-spec.json','images/contact-seal-trial.png':IMAGES/'contact-seal-trial.png',
        'exchange/ContactPost.step':trial_folder/'ContactPost.step'}
    for n in trial_report['print_parts']:
        assert sha(trial_folder/(n+'.stl'))==trial_report['exports'][n]['print_STL_sha256']
        trial_files['print/'+n+'.stl']=trial_folder/(n+'.stl')
    trial_archive='Contact-Seal-Trial-Kit.zip'
    package(trial_folder,trial_archive,trial_files,'Inert single-contact hydrostatic fixture; two fit prints and316L post trial RFQ; no physical seal/casting/electrical qualification')
    for source in r['pcb_sources'].values():assert sha(ROOT/source['board_file'])==source['board_sha256']
    first=('DockBase','DockLid','DockNest','PogoCarrier','PogoRetainer','DockDeviceGauge','PinPCBBlank','MagnetBackSpacer0','MagnetBackSpacer1')
    trial=('FourContactRearHalf','ContactFaceMask','ContactMoldHalfA','ContactMoldHalfB')
    files={'README.md':dock/'PRINT-KIT.md','cad/ChargingDock.FCStd':dock/'ChargingDock.FCStd'}
    files['seal-trial/'+trial_archive]=trial_folder/trial_archive
    files['engineering/contact-seal-spec.json']=dock/'contact-seal-spec.json'
    for n in first+trial:
        expected=next(v['print_STL_sha256'] for v in r['exports'].values() if v['label']==n)
        assert sha(dock/(n+'.stl'))==expected
        files['print/'+('dock/' if n in first else 'interface-trial/')+n+'.stl']=dock/(n+'.stl')
    for n in ('charging-dock','charging-interface','charging-dock-electronics'):
        meta=json.loads((IMAGES/(n+'.json')).read_text());assert meta['native_sha256']==r['native_sha256']
        files['images/'+n+'.png']=IMAGES/(n+'.png')
    for n in ('dock','pins'):files['pcb-quotes/'+n+'-evt1-fabrication-quote.zip']=quote(n)
    for n in ('dock','pins'):files['pcb-assembly-quotes/'+n+'-evt1-assembly-quote.zip']=assembly(n)
    files.update({'reports/charging-dock-review.json':dock/'review.json','reports/electrical-validation.json':PCB/'validation.json'})
    package(dock,'Dock-Interface-Print-Kit.zip',files,'Unpowered dock/contact prints and two cradle PCB quotes; complete device build not released')

    folder=CAD/'evt1-integration';r=json.loads((folder/'review.json').read_text())
    assert sha(folder/'EVT1Product.FCStd')==r['native_sha256'] and r['geometry_checks']['hard_intersections']==0
    assert sha(ROOT/'tools/verify_evt1_product.py')==r['geometry_checks']['verifier_sha256']
    for source in r['boards'].values():assert sha(ROOT/source['source'])==source['sha256']
    files={'README.md':folder/'README.md','cad/EVT1Product.FCStd':folder/'EVT1Product.FCStd',
           'reports/product-review.json':folder/'review.json','reports/electrical-validation.json':PCB/'validation.json',
           'images/evt1-product.png':IMAGES/'evt1-product.png'}
    meta=json.loads((IMAGES/'evt1-product.json').read_text());assert meta['native_sha256']==r['native_sha256']
    assert r['parts_selection_sha256']==sha(PCB/'parts-selection.json')
    assert r['pack_spec_sha256']==sha(PCB/'pack-spec.json')
    for name in ('pack-spec.json','PACK-RFQ.md','pcb-ordering.csv','parts-selection.json','parts-validation.json'):
        files['engineering-parts/'+name]=PCB/name
    if (IMAGES/'evt1-pack.png').exists():
        meta=json.loads((IMAGES/'evt1-pack.json').read_text());assert meta['native_sha256']==r['native_sha256']
        files['images/evt1-pack.png']=IMAGES/'evt1-pack.png'
    for n in ('FlangeTray','RearHalf'):
        assert sha(folder/(n+'.stl'))==r['exports'][n]['print_STL_sha256']
        files['print/'+n+'.stl']=folder/(n+'.stl')
    for n in r['main_custom_rigid_parts']:
        assert sha(folder/(n+'.step'))==r['exports'][n]['STEP_sha256']
        files['exchange/'+n+'.step']=folder/(n+'.step')
    for n in ('body','flange','sensor','dock','pins'):files['pcb-quotes/'+n+'-evt1-fabrication-quote.zip']=quote(n)
    for n in ('body','flange','sensor','dock','pins'):files['pcb-assembly-quotes/'+n+'-evt1-assembly-quote.zip']=assembly(n)
    wiring,wire_review=loom_files()
    files.update({'wiring/'+name:path for name,path in wiring.items()})
    package(folder,'EVT1-Board-Fit-Kit.zip',files,'Actual-board nominal device fit checkpoint, two unpowered plastic prints and five PCB quotes; pack/loom/seal/lock work remains')

    files={name:PCB/name for name in ('README.md','pcb-ordering.csv','parts-selection.json','parts-validation.json','pack-spec.json','PACK-RFQ.md','native-checks.json','validation.json')}
    for n in ('body','flange','sensor','dock','pins'):files['assembly-quotes/'+n+'-evt1-assembly-quote.zip']=assembly(n)
    package(PCB,'EVT1-Electronics-Quote-Kit.zip',files,'Exact parts/native positions and fabrication files for five PCB assembly quotes plus protected-pack RFQ; supplier acceptance, stock and full-product design remain pending')

    # Generated cable diagrams/child BOMs are deliberately packaged outside
    # the repository. Unqualified reference wire STEPs are excluded entirely.
    files=wiring.copy();exports=Path(wire_review['export_directory'])
    for name,digest in wire_review['generated_files_sha256'].items():
        assert sha(exports/name)==digest;files['generated/'+name]=exports/name
    package(exports.parent,'EVT1-Loom-Review-Kit.zip',files,'Seven logical/native-pin-map harness sources and child BOMs; installed spans only when interboard_spans_verified in logical-source.json; all other lengths starting stock. No finished-cut/crimp/physical qualification')


if __name__=='__main__':main()
