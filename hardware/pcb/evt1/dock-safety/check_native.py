"""Native ERC and pin/pad parity for one new dock safety or UV project."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT/'tools'))
import kicad_sexp as s
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--folder',required=True)
    ap.add_argument('--stem',required=True); ap.add_argument('--kicad-cli',required=True)
    a=ap.parse_args(); folder=Path(a.folder).resolve()
    def sources():
        return {str(f.relative_to(folder)):sha(f) for f in sorted(folder.rglob('*'))
                if f.is_file() and f.relative_to(folder).parts[0]!='pcb' and (f.suffix in ('.kicad_sch','.kicad_sym','.kicad_pro','.kicad_mod')
                                   or f.name in ('sym-lib-table','fp-lib-table','parts-selection.json'))}
    before=sources()
    shared={str(f.relative_to(ROOT)):sha(f) for f in (HERE/'native_helpers.py',Path(__file__))}
    builder=(folder.parent/'build_uv.py') if a.stem.startswith('dock-uv-') else (folder/'build_safety.py')
    shared[str(builder.relative_to(ROOT))]=sha(builder)
    pro=json.loads((folder/(a.stem+'.kicad_pro')).read_text())
    assert pro['erc']['erc_exclusions']==[]
    ver=subprocess.check_output([a.kicad_cli,'--version'],text=True).strip()
    assert int(ver.split('.')[0])>=10
    for command in [
        ['sch','export','netlist','--format','kicadxml','-o',str(folder/'native.xml'),str(folder/(a.stem+'.kicad_sch'))],
        ['sch','erc','--format','json','--exit-code-violations','-o',str(folder/'erc.json'),str(folder/(a.stem+'.kicad_sch'))]]:
        r=subprocess.run([a.kicad_cli]+command,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        if r.returncode: print(r.stdout); raise AssertionError((r.returncode,command))
    erc=json.loads((folder/'erc.json').read_text())
    findings=[v for sheet in erc['sheets'] for v in sheet['violations']]
    assert not findings,findings
    assert erc['included_severities']==['error','warning']
    assert {i['key'] for i in erc['ignored_checks']}=={'single_global_label','four_way_junction','simulation_model_issue','footprint_filter'}
    t=ET.parse(folder/'native.xml').getroot()
    comps={c.get('ref'):c for c in t.findall('./components/comp')}
    nets={}; pinmap={}
    for net in t.findall('./nets/net'):
        ns={(n.get('ref'),n.get('pin')) for n in net.findall('node')}; nets[net.get('name')]=ns
        for pin in ns: pinmap[pin]=net.get('name')
    manifest=json.loads((folder/'parts-selection.json').read_text())
    parts=manifest['parts']; assert set(comps)=={p['reference'] for p in parts},(set(comps),{p['reference'] for p in parts})
    pin_checks=0; fp_checks=0
    for p in parts:
        ref=p['reference']; c=comps[ref]
        assert c.findtext('value')==p['value'],ref
        props={x.get('name'):x.get('value') for x in c.findall('property')}
        assert props.get('MPN')==p['mpn'] and props.get('Manufacturer')==p['manufacturer'],ref
        for pin,net in p['pins'].items():
            actual=pinmap[(ref,pin)]
            assert actual==net if net else actual.startswith('unconnected-'),(ref,pin,net,actual)
            pin_checks+=1
        if p['footprint']:
            lib,name=p['footprint'].split(':')
            fp=folder/(lib+'.pretty')/(name+'.kicad_mod')
            pads={x[1].value for x in s.children(s.parse(fp.read_text()),'pad') if x[1].value}
            assert pads==set(p['pins']),(ref,pads,set(p['pins']))
            fp_checks+=1
        else: assert p['offboard'],ref
    assert sources()==before,'Saved source changed during native checks'
    report={'status':'pass: native ERC and complete declared pin/pad parity','scope':a.stem,
            'kicad_version':ver,'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'source_sha256':before,'shared_source_sha256':shared,
            'reports_sha256':{n:sha(folder/n) for n in ('native.xml','erc.json')},
            'component_count':len(parts),'pin_checks':pin_checks,'footprint_checks':fp_checks,
            'offboard_components':sum(p['offboard'] for p in parts),
            'ERC_errors':0,'ERC_warnings':0,'ERC_exclusions':[],
            'PCB_created_or_routed':False,'powered_validation':False,'full_product_order_ready':False}
    (folder/'native-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('scope','kicad_version','component_count','pin_checks','footprint_checks','offboard_components','ERC_errors','ERC_warnings')},indent=2))


if __name__=='__main__': main()
