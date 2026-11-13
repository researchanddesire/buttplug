"""Source-bound UV-only fabrication/assembly review artifacts; never orders."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import subprocess
import zipfile
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main(cli):
    for side in('base','lid'):
        leaf=HERE/side;folder=leaf/'pcb';board=folder/('dock-uv-'+side+'.kicad_pcb');before=sha(board)
        checked=json.loads((folder/'pcb-checks.json').read_text());assert checked['board_sha256']==before
        assert not json.loads((folder/'native-drc.json').read_text())['violations']
        parts=json.loads((leaf/'parts-selection.json').read_text())
        out=folder/'fabrication-review';out.mkdir(exist_ok=True)
        commands=[
            ['pcb','export','gerbers','--layers','F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,B.Paste,F.SilkS,B.SilkS,Edge.Cuts','--subtract-soldermask','-o',str(out)+'/',str(board)],
            ['pcb','export','drill','--format','excellon','--excellon-separate-th','--excellon-oval-format','route','--generate-report','--report-path',str(out/'drill-report.txt'),'-o',str(out)+'/',str(board)],
            ['pcb','export','pos','--format','csv','--units','mm','--side','both','--use-drill-file-origin','-o',str(out/'native-all-positions.csv'),str(board)]]
        for command in commands:
            result=subprocess.run([cli]+command,capture_output=True,text=True)
            assert result.returncode==0,(command,result.stdout,result.stderr)
        with (out/'native-all-positions.csv').open()as file:
            reader=csv.DictReader(file);fields=reader.fieldnames;positions={r['Ref']:r for r in reader}
        bought=[p for p in parts['parts']if not p['offboard']and p['manufacturer']!='manual copper']
        assert len(bought)==20 and all(p['reference']in positions for p in bought)
        with(out/'purchased-positions.csv').open('w',newline='')as file:
            writer=csv.DictWriter(file,fieldnames=fields);writer.writeheader()
            for p in bought:writer.writerow(positions[p['reference']])
        for name,rows in [('onboard-selected-parts.csv',bought),('remote-thermal-parts.csv',[p for p in parts['parts']if p['offboard']])]:
            with(out/name).open('w',newline='')as file:
                writer=csv.writer(file);writer.writerow(['Reference','Manufacturer','MPN','Value','Footprint','PrimarySource','AssemblyNote'])
                for p in rows:writer.writerow([p['reference'],p['manufacturer'],p['mpn'],p['value'],p['footprint']or'offboard',p['primary_source'],p['note']])
        (out/'README.md').write_text('# UV PCB supplier review only\n\n'
            'This package covers this UV board only. It is not an order or a complete-product fabrication release. Actual stackup, stencil/reflow, UV/thermal qualification, received tolerances, opacity and final clamshell fit remain open.\n\n'
            'Request nominal1mm copper-plus-FR4,2layers,70um outer copper each,FR4core0.86mm,ENIG,mask10um each. Coatings are additional to nominal laminate/copper thickness. Require minimum finished conductor cross-sections consistent with the resistance acceptance; supplier stackup/process acceptance is pending. Minimum trace/clearance0.2/0.2mm,via0.6/0.3mm,4NPTH2.2mm mounting holes and1mm internal milling radii. Tenting/plugging and backing-pad surface finish require process review. No soldermask electrical isolation to a common Al backing is credited.\n\n'
            'Twenty onboard purchased positions use the exact selected MPNs. Four TP copper solder lands and four holes are not purchased parts. The two remote thermal parts are separately listed and MUST NOT be placed as PCB components. Provide strain relief and actual hottest-region thermal attachment. Do not substitute a ground thermal pad for either LED terminal. Match the marked cathode to pad1; the physical package and selected OEM model agree on positive localX. Reconcile bottom placement rotations with the native board before programming assembly.\n\n'
            'The power budget requires each complete hot UV PCB supply/return loop<=20mOhm as an acceptance target; actual resistance is not yet measured. The separate full branch allowance includes connectors,crimps and wire; see ../../../../dock-safety/power-budget.json in the source tree. Input/output effective capacitance>=1uF, loop stability, source changes/inrush, optical cutoff/leakage/dose/efficacy and thermal/material aging require measurement.\n')
        files={p.name:sha(p)for p in sorted(out.iterdir())if p.is_file()and p.name not in('manifest.json','uv-'+side+'-supplier-review.zip')}
        manifest={'scope':'UV-only supplier review; no order or full-product release','board_sha256':before,'PCB_check_sha256':sha(folder/'pcb-checks.json'),
            'parts_selection_sha256':sha(leaf/'parts-selection.json'),'exporter_sha256':sha(Path(__file__)),
            'purchased_onboard_positions':20,'remote_thermal_positions':2,'manual_copper_lands':4,'mounting_holes':4,'files_sha256':files,
            'supplier_acceptance':False,'physical_validation':False,'full_product_order_ready':False}
        (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        with zipfile.ZipFile(out/('uv-'+side+'-supplier-review.zip'),'w',zipfile.ZIP_DEFLATED)as archive:
            for name in files:archive.write(out/name,name)
            archive.write(out/'manifest.json','manifest.json')
        assert sha(board)==before,'Exporter changed PCB'
        print(side,'20purchased positions; supplier-review archive written')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--kicad-cli',required=True);main(ap.parse_args().kicad_cli)
