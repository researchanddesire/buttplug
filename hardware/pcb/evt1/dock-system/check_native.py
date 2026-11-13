"""Independent full-system ERC, leaf conservation and terminal/net comparison."""
from pathlib import Path
import argparse
import collections
import datetime
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import kicad_sexp as s
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def read_xml(path):
    tree=ET.parse(path).getroot()
    components={c.get('ref'):c for c in tree.findall('./components/comp')}
    pins={}
    for net in tree.findall('./nets/net'):
        for node in net.findall('node'):
            pins[(node.get('ref'),node.get('pin'))]=(net.get('name'),node.attrib)
    return components,pins


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--kicad-cli',required=True)
    cli=ap.parse_args().kicad_cli
    manifest=json.loads((HERE/'source-manifest.json').read_text())
    inputs=manifest['inputs_sha256']
    for path,digest in inputs.items():
        assert sha(ROOT/path)==digest,('Regenerate snapshots after source edit',path)
    assert sha(HERE/'build_source.py')==manifest['builder_sha256']
    source_files={str(p.relative_to(HERE)):sha(p)for p in sorted(HERE.rglob('*'))
                  if p.is_file() and (p.suffix in ('.kicad_sch','.kicad_pro')
                  or p.name in ('source-manifest.json','sym-lib-table','fp-lib-table','build_source.py','check_native.py'))}
    expected_components={};expected_pins={};leaf_reports={}
    for item in manifest['sheets']:
        original=ROOT/item['source'];snapshot=HERE/item['snapshot']
        assert sha(snapshot)==item['snapshot_sha256']
        a=s.parse(original.read_text());b=s.parse(snapshot.read_text())
        removed=item.get('standalone_context_flags_removed',[])
        removed_ids=set(item.get('standalone_context_node_uuids_removed',[]))
        assert len(removed_ids)==3*len(removed)
        for node in list(a):
            if isinstance(node,list) and s.value(node,'uuid') in removed_ids:
                assert s.tag(node) in ('symbol','wire','global_label')
                if s.tag(node)=='symbol':
                    assert s.prop(node,'Reference') in removed and s.prop(node,'Footprint') in ('',None)
                a.remove(node)
        for symbol in s.children(b,'symbol'):
            inst=s.child(symbol,'instances')
            inst[:]=[x for x in inst if not(isinstance(x,list) and s.tag(x)=='project' and x[1].value=='dock-system')]
        assert s.dump(a)==s.dump(b),('Electrical leaf content changed',original)
        if original.parent.name=='dock-ui':
            xml=original.parent/'source-native.xml'
        elif original.parent.name=='dock-control':
            xml=original.with_name(original.stem+'-native.xml')
        else:
            xml=original.parent/'native.xml'
        binding_file=original.parent/'native-checks.json'
        binding=json.loads(binding_file.read_text())
        assert binding['source_sha256'][original.name]==sha(original),('Leaf native binding stale',original)
        assert binding['reports_sha256'][xml.name]==sha(xml),('Leaf XML binding stale',xml)
        components,pins=read_xml(xml)
        assert not set(components)&set(expected_components),('Duplicate reference',original)
        expected_components.update(components);expected_pins.update(pins)
        leaf_reports[str(xml.relative_to(ROOT))]=sha(xml)
        leaf_reports[str(binding_file.relative_to(ROOT))]=sha(binding_file)
    project=json.loads((HERE/'dock-system.kicad_pro').read_text())
    assert project['erc']['erc_exclusions']==[]
    version=subprocess.check_output([cli,'--version'],text=True).strip()
    assert int(version.split('.')[0])>=10
    runs=[]
    for name,args in [
        ('xml',['sch','export','netlist','--format','kicadxml','-o',str(HERE/'native.xml'),str(HERE/'dock-system.kicad_sch')]),
        ('erc',['sch','erc','--format','json','--exit-code-violations','-o',str(HERE/'erc.json'),str(HERE/'dock-system.kicad_sch')])]:
        result=subprocess.run([cli]+args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,cwd=HERE)
        (HERE/(name+'.log')).write_text(result.stdout)
        runs.append({'phase':name,'returncode':result.returncode})
    erc=json.loads((HERE/'erc.json').read_text())
    findings=[v for sheet in erc['sheets']for v in sheet['violations']]
    components,pins=read_xml(HERE/'native.xml')
    assert set(components)==set(expected_components),('Component inventory changed',set(components)^set(expected_components))
    checks=[]
    for ref,source in expected_components.items():
        actual=components[ref]
        for field in ('value','footprint'):
            assert actual.findtext(field)==source.findtext(field),(ref,field)
        fields=lambda node:{f.get('name'):f.text for f in node.findall('./fields/field')}
        for field in ('Manufacturer','MPN'):
            assert fields(actual).get(field)==fields(source).get(field),(ref,field)
    assert set(pins)==set(expected_pins),('Terminal inventory changed',set(pins)^set(expected_pins))
    for terminal,(net,source) in expected_pins.items():
        actual,details=pins[terminal]
        if net.startswith('unconnected-'):
            assert actual.startswith('unconnected-'),(terminal,net,actual)
        else:
            assert actual==net,(terminal,net,actual)
        assert details.get('pintype')==source.get('pintype'),terminal
        checks.append({'ref':terminal[0],'pin':terminal[1],'leaf_net':net,'system_net':actual,'pintype':details.get('pintype')})
    required={
        'BTN_CENTERn_RAW':[('S302','1'),('U608','2')],
        'BTN_CENTERn_DEBOUNCED':[('U608','3'),('U114','3'),('U201','26')],
        'BTN_CENTER_PRESSED':[('U114','4'),('U614','3')],
        'SOURCE_OK':[('U122','4'),('U201','4'),('U612','4')],
        'UV_RUN':[('U609','9'),('U201','31')],
        'MCU_NRSTn':[('R606','2'),('U201','7'),('J202','3')],
        'BASE_FB':[('U202','4'),('J621','4')],
        'LID_FB':[('U202','5'),('J622','4')],
        'NTC_BASE':[('R218','2'),('R220','1'),('J621','6')],
        'NTC_LID':[('R219','2'),('R221','1'),('J622','6')],
    }
    interfaces=[]
    for net,terminals in required.items():
        for terminal in terminals:
            assert pins[terminal][0]==net,(net,terminal,pins[terminal])
        interfaces.append({'net':net,'required_terminals':terminals})
    for path,digest in inputs.items():assert sha(ROOT/path)==digest,('Sources changed while checking',path)
    for path,digest in leaf_reports.items():assert sha(ROOT/path)==digest,('Leaf native reports changed while checking',path)
    for path,digest in source_files.items():assert sha(HERE/path)==digest,('System changed while checking',path)
    report={'status':'pass'if not findings and all(r['returncode']==0 for r in runs)else'fail',
            'scope':'Combined dock schematic; preserved leaf terminals and explicit cross-sheet interfaces',
            'checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'kicad_version':version,'runs':runs,'ERC_findings':findings,
            'ERC_errors':sum(v['severity']=='error'for v in findings),
            'ERC_warnings':sum(v['severity']=='warning'for v in findings),
            'ERC_exclusions':[],'native_component_count':len(components),
            'native_terminal_count':len(checks),'terminal_checks':checks,
            'cross_sheet_interfaces':interfaces,'leaf_native_reports_sha256':leaf_reports,
            'source_sha256':source_files,'inputs_sha256':inputs,
            'reports_sha256':{n:sha(HERE/n)for n in ('native.xml','erc.json')},
            'functional_terminal_conservation':True,
            'standalone_context_flags_removed':{i['source']:i.get('standalone_context_flags_removed',[])for i in manifest['sheets']},
            'PCB_routed':False,
            'powered_validation':False,'optical_validation':False,'full_product_order_ready':False}
    (HERE/'native-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    summary={k:report[k]for k in ('status','kicad_version','native_component_count','native_terminal_count','ERC_errors','ERC_warnings')}
    summary['finding_types']=dict(collections.Counter(v['type']for v in findings))
    summary['first_findings']=[{'type':v['type'],'description':v['description']}for v in findings[:6]]
    print(json.dumps(summary,indent=2))
    assert report['status']=='pass','Native full-system ERC failed; inspect report'


if __name__=='__main__':main()
