"""Export source-bound EVT1 PCB fabrication quotes with native KiCad CLI.

No upload/order, full-product fabrication release or supplier acceptance is
implied. Run verify_evt1_electrical.py and the CAD checker before quoting.
"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import zipfile
import kicad_sexp as s

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/pcb/evt1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--kicad-cli',required=True);ap.add_argument('--domains',nargs='+',choices=('body','flange','sensor','dock','pins'),default=['dock','pins']);args=ap.parse_args()
    report=json.loads((BASE/'validation.json').read_text())
    for name,digest in report['source_sha256'].items():assert sha(ROOT/name)==digest,('Electrical validation stale',name)
    assert sha(BASE/'native-checks.json')==report['native_checks_sha256'],'Native checks stale'
    for domain in args.domains:
        board=BASE/domain/(domain+'-evt1.kicad_pcb')
        tree=s.parse(board.read_text())
        copper=[n[1].value for n in s.child(tree,'layers')[1:] if isinstance(n,list) and n[1].value.endswith('.Cu')]
        assert len(copper)=={'body':6,'flange':4,'sensor':2,'dock':2,'pins':2}[domain]
        if domain in ('body','flange','sensor'):
            fitted=json.loads((ROOT/'hardware/cad/manufacturing-layout/evt1-integration/review.json').read_text())
            assert fitted['geometry_checks']['hard_intersections']==0 and fitted['boards'][domain]['sha256']==sha(board),'Actual-board CAD stale'
        layerlist=','.join(copper+['F.Paste','B.Paste','F.SilkS','B.SilkS','F.Mask','B.Mask','Edge.Cuts'])
        rules=json.loads(board.with_suffix('.kicad_pro').read_text())['board']['design_settings']['rules']
        request={'scope':'EVT prototype fabrication quote; no full-product build release, supplier acceptance or order',
                 'layers':len(copper),'copper_layer_order':copper,'thickness_mm':1.0,'material':'FR4','finish':'ENIG',
                 'outer_copper_oz':1,'inner_copper_oz':.5 if len(copper)>2 else None,
                 'copper_clearance_min_mm':rules['min_clearance'],'track_width_min_mm':rules['min_track_width'],
                 'via_drill_min_mm':rules['min_through_hole_diameter'],'via_diameter_min_mm':rules['min_via_diameter'],
                 'copper_to_board_edge_min_mm':rules['min_copper_edge_clearance'],'hole_to_copper_min_mm':rules['min_hole_clearance'],
                 'supplier_review':'Review finished thickness/holes, routed outline, mask webs, paste and the complete actual stackup before accepting a quote. Native stackup is a proposal, not an impedance-qualified fabrication agreement.'}
        if domain in ('dock','pins'):
            request['supplier_review']='USB4105 locating-peg land pattern requires acceptance of0.15mm hole-to-copper clearance on dock board; review routed slots, finished thickness/holes and paste. Pin-board thickness sets spring compression.'
        if domain=='body':request['assembly_note']='J81 sensor-loom ground hand-solder land intentionally includes a through via; it is not a paste-reflow package land.'
        folder=BASE/domain/'fabrication-quote'
        folder.mkdir(exist_ok=True)
        logfile=folder/'export.log'
        with logfile.open('w') as log:
            for command in (
                ['pcb','export','gerbers','--layers',layerlist,'--subtract-soldermask','-o',str(folder)+'/',str(board)],
                ['pcb','export','drill','--format','excellon','--excellon-separate-th','--excellon-oval-format','route','--generate-report','--report-path',str(folder/'drill-report.txt'),'-o',str(folder)+'/',str(board)],
            ):subprocess.run([args.kicad_cli]+command,check=True,stdout=log,stderr=log)
        # Read the native job inventory instead of guessing file extensions:
        # multilayer exports use .g1/.g2/etc for their inner copper.
        jobpath=folder/(domain+'-evt1-job.gbrjob');job=json.loads(jobpath.read_text())
        copperfiles=[v for v in job['FilesAttributes'] if v['FileFunction'].startswith('Copper,')]
        assert len(copperfiles)==len(copper),(domain,'Missing copper layer')
        assert job['GeneralSpecs']['LayerNumber']==len(copper) and job['GeneralSpecs']['BoardThickness']==1
        # The inherited native stackup has an unspecified finish. ENIG is an
        # explicit quote choice, reflected in both output job and request.
        request['native_stackup_finish']=job['GeneralSpecs']['Finish']
        job['GeneralSpecs']['Finish']=request['finish']
        jobpath.write_text(json.dumps(job,indent=2)+'\n')
        (folder/'fabrication-request.json').write_text(json.dumps(request,indent=2)+'\n')
        files=[folder/v['Path'] for v in job['FilesAttributes']]+[jobpath,folder/'fabrication-request.json']+sorted(folder.glob('*.drl'))
        assert all(p.is_file() and p.stat().st_size>0 for p in files)
        assert len(files)==len(set(files)),(domain,'Duplicate export path')
        archive=folder/(domain+'-evt1-fabrication-quote.zip')
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for path in sorted(files):z.write(path,path.name)
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            assert all(hashlib.sha256(z.read(p.name)).hexdigest()==sha(p) for p in files)
        manifest={'scope':'EVT PCB fabrication quote only; no full-product release or order',
                  'board_sha256':sha(board),'quote_zip_sha256':sha(archive),
                  'native_checks_sha256':report['native_checks_sha256'],'electrical_validation_sha256':sha(BASE/'validation.json'),
                  'files':{p.name:sha(p) for p in sorted(files)},
                  'fabrication_request':request}
        (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print(archive)


if __name__=='__main__':main()
