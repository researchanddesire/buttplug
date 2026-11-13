"""Source-bound EVT1 PCB assembly quotes: exact parts and native positions.

No upload/order or complete-product release. Retains native coordinates and
identifies copper-only assembly operations separately from purchased parts.
"""
from pathlib import Path
from collections import defaultdict
import argparse
import csv
import hashlib
import json
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/pcb/evt1'
DOMAINS=('body','flange','sensor','dock','pins')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--kicad-cli',required=True);a=ap.parse_args()
    parts_path=BASE/'parts-selection.json';parts=json.loads(parts_path.read_text())
    native=json.loads((BASE/'native-checks.json').read_text())
    for name,digest in {**parts['source_netlist_sha256'],**native['source_sha256'],**native['netlist_sha256']}.items():
        assert sha(ROOT/name)==digest,('Source changed after review',name)
    fitted=json.loads((ROOT/'hardware/cad/manufacturing-layout/evt1-integration/review.json').read_text())
    assert fitted['parts_selection_sha256']==sha(parts_path) and fitted['geometry_checks']['hard_intersections']==0,'Actual selected-part CAD stale'
    for domain in DOMAINS:
        folder=BASE/domain/'assembly-quote';folder.mkdir(exist_ok=True)
        board=BASE/domain/(domain+'-evt1.kicad_pcb');before=sha(board)
        rows=[p for p in parts['components'] if p['domain']==domain]
        bought={p['ref']:p for p in rows if p['purchase']}
        raw=folder/(domain+'-native-all-positions.csv')
        result=subprocess.run([a.kicad_cli,'pcb','export','pos','--format','csv','--units','mm','--side','both','-o',str(raw),str(board)],capture_output=True,text=True)
        assert result.returncode==0,(domain,result.stdout,result.stderr)
        with raw.open(newline='') as f:
            reader=csv.DictReader(f);columns=reader.fieldnames;placed={r['Ref']:r for r in reader}
        assert set(bought)<=set(placed),(domain,'Purchased references missing from native position export',set(bought)-set(placed))
        positions=folder/(domain+'-purchased-positions.csv')
        with positions.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
            for ref in sorted(bought):writer.writerow(placed[ref])
        grouped=defaultdict(list)
        for p in bought.values():grouped[(p['manufacturer'],p['mpn'])].append(p)
        order=folder/(domain+'-assembly-parts.csv')
        with order.open('w',newline='') as f:
            writer=csv.writer(f);writer.writerow(['Manufacturer','MPN','Quantity_per_board','References','Schematic_value','Footprint','Assembly_note','Manufacturer_source'])
            for (maker,mpn),group in sorted(grouped.items()):
                writer.writerow([maker,mpn,len(group),' '.join(sorted(p['ref'] for p in group)),'; '.join(sorted({p['schematic_value'] for p in group})),'; '.join(sorted({p['footprint'] for p in group})),'; '.join(sorted({p.get('assembly_note','') for p in group if p.get('assembly_note')})),group[0]['manufacturer_source']])
        notes=folder/'README.md'
        operations='\n'.join('- '+p['ref']+': '+p['assembly_note'] for p in rows if not p['purchase']) or '- None on this board.'
        notes.write_text('# '+domain.title()+' EVT1 PCB assembly quote\n\n'
            'Exact parts, native KiCad positions, saved native board and the matching fabrication quote are included. This is an EVT assembly quote, not a complete device release or an order. Supplier acceptance and physical commissioning remain pending.\n\n'
            'Use the purchased-positions file with the assembly-parts worksheet. Units are mm, rotation and side are exported by KiCad. Preserve native coordinates; do not independently recenter/mirror a file. Reconcile package zero angles and pin1/cathode markings with the native Fab drawing before programming placement. Review paste/stencil and reflow, including module/IC exposed pads.\n\n'
            'Copper features and manual assembly operations are not bought parts:\n\n'+operations+'\n\n'
            'D1 on the flange has custom logical numbering: physical cathode stripe at pad2/CAD cathode bar. Keep body JP1 open until the independent charge-guard tests pass. Solder the four pogo pins square to the1mm pin board in the carrier fixture; inspect pitch/height and the rear J94 wires before fitting its retainer. No connector or header is fitted to a hand-solder loom land.\n\n'
            'C83 selection is22uF/25V X5R; the generic schematic10V marking is a minimum rating. Its lot/process acceptance is at least10uF effective at3.3V over the intended temperature/age. Verify regulator effective capacitance and electrical/thermal behavior in commissioning. Manufacturer reference curves do not guarantee the installed result.\n')
        fab=BASE/domain/'fabrication-quote'/(domain+'-evt1-fabrication-quote.zip')
        fabmanifest=json.loads((fab.parent/'manifest.json').read_text())
        assert fabmanifest['board_sha256']==before and fabmanifest['quote_zip_sha256']==sha(fab)
        files={order.name:order,positions.name:positions,'README.md':notes,board.name:board,fab.name:fab}
        manifest={'scope':'EVT PCB assembly quote; full device build package incomplete','board_sha256':before,
            'parts_selection_sha256':sha(parts_path),'native_checks_sha256':sha(BASE/'native-checks.json'),
            'purchased_positions':len(bought),'nonpurchased_operations':len(rows)-len(bought),
            'files':{n:sha(p) for n,p in files.items()},'exporter_sha256':sha(Path(__file__)),
            'supplier_acceptance':False,'physical_validation':False}
        (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        archive=folder/(domain+'-evt1-assembly-quote.zip')
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for name,path in files.items():z.write(path,name)
            z.write(folder/'manifest.json','manifest.json')
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            assert all(hashlib.sha256(z.read(n)).hexdigest()==digest for n,digest in manifest['files'].items())
        assert sha(board)==before,'Export changed saved PCB'
        print(json.dumps({'domain':domain,'purchased_positions':len(bought),'archive':str(archive.relative_to(ROOT))}),flush=True)


if __name__=='__main__':main()
