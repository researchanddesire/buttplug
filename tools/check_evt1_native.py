"""Run native KiCad checks and bind their reports to the exact saved sources.

This is digital electrical verification only. No supplier, hardware or full
product release follows from ERC/DRC passing.
"""
from pathlib import Path
import argparse
import concurrent.futures
import datetime
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/pcb/evt1'
DOMAINS=('body','flange','sensor','dock','pins')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def sources():
    return {str(p.relative_to(ROOT)):sha(p) for p in sorted(BASE.rglob('*'))
            if p.is_file() and (p.suffix in ('.kicad_sch','.kicad_sym','.kicad_pcb','.kicad_pro','.kicad_mod','.kicad_dru')
                                or p.name in ('fp-lib-table','sym-lib-table'))}


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--kicad-cli',required=True);a=ap.parse_args()
    version=subprocess.check_output([a.kicad_cli,'--version'],text=True).strip()
    before=sources()
    def check(domain):
        folder=BASE/domain if domain else BASE
        stem=domain+'-evt1' if domain else 'system-evt1'
        rows=[]
        commands=[(['sch','export','netlist','--format','kicadxml','-o',str(folder/((domain or 'system')+'-native.xml')),str(folder/(stem+'.kicad_sch'))],None),
                  (['sch','erc','--format','json','--exit-code-violations','-o',str(folder/'erc.json'),str(folder/(stem+'.kicad_sch'))],'erc')]
        if domain:commands.append((['pcb','drc','--format','json','--exit-code-violations','-o',str(folder/'drc.json'),str(folder/(stem+'.kicad_pcb'))],'drc'))
        for args,kind in commands:
            result=subprocess.run([a.kicad_cli]+args,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
            if kind:
                path=folder/(kind+'.json');r=json.loads(path.read_text())
                issues=(r['violations']+r['unconnected_items']) if kind=='drc' else [v for sheet in r['sheets'] for v in sheet['violations']]
                if kind=='erc' and domain in ('flange','sensor'):
                    assert len(issues)==2 and all(v['type']=='power_pin_not_driven' for v in issues),(domain,issues)
                    assert result.returncode==5,(domain,result.stdout)
                    scope='Two external supply inputs; connected body supply passes full-system ERC'
                else:
                    assert result.returncode==0 and not issues,(domain,kind,result.stdout,issues)
                    scope='pass'
                rows.append({'kind':kind,'report':str(path.relative_to(ROOT)),'sha256':sha(path),'issue_count':len(issues),'scope':scope})
            else:assert result.returncode==0,(domain,result.stdout)
        return domain or 'system',rows
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        checks=dict(executor.map(check,('',)+DOMAINS))
    assert sources()==before,'Native source changed during checks; rerun on the saved source'
    netlists={str((BASE/d/((d or 'system')+'-native.xml')).relative_to(ROOT)):sha(BASE/d/((d or 'system')+'-native.xml')) for d in ('',)+DOMAINS}
    report={'scope':'Source-bound native ERC/DRC; digital verification only','kicad_version':version,
            'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_sha256':before,'netlist_sha256':netlists,'checks':checks,'runner_sha256':sha(Path(__file__)),
            'full_product_order_ready':False}
    (BASE/'native-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'version':version,'system_ERC':0,'body_ERC':0,'all_five_PCB_DRC':0,'unconnected_items':0,'source_bound':True}))


if __name__=='__main__':main()
