"""Native-export terminal conservation; no invented replacement netlist."""
from pathlib import Path
import hashlib,json,xml.etree.ElementTree as E

H=Path(__file__).resolve().parent
ROOT=H.parents[3]
O=H/'body-instrumentation'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def terminal_map(path):
    root=E.parse(path).getroot()
    refs={x.get('ref'):x.findtext('value')for x in root.findall('./components/comp')}
    result={}
    for net in root.findall('./nets/net'):
        for node in net.findall('node'):
            key=(node.get('ref'),node.get('pin'))
            assert key not in result,key
            result[key]=(net.get('name'),node.get('pintype'),node.get('pinfunction'))
    return refs,result


def main():
    source=ROOT/'hardware/pcb/evt1/single-flange-routing/system-native.xml'
    before,old=terminal_map(source)
    after,new=terminal_map(O/'native.xml')
    bindings=json.loads((O/'source-bindings.json').read_text())
    assert bindings['builder_sha256']==sha(H/'build_body_candidate.py')
    added={p['ref']for p in bindings['new_parts']}
    assert len(added)==21 and set(after)==set(before)|added
    assert all(after[r]==before[r]for r in before)
    differences=[]
    for key,value in old.items():
        expected=value
        if key in [('U7','6'),('U7','7')]:
            expected=('CHARGE_CURRENT_ADC' if key[1]=='6' else 'CHARGE_TS_ADC',value[1],value[2])
        assert new.get(key)==expected,(key,value,new.get(key),expected)
        if new[key]!=value:differences.append({'ref':key[0],'pin':key[1],'from':list(value),'to':list(new[key])})
    assert len(differences)==2
    for p in bindings['new_parts']:
        for pin,net in p['pins'].items():
            if net is None:continue
            assert new[(p['ref'],pin)][0]==net,(p['ref'],pin,net,new.get((p['ref'],pin)))
    erc=json.loads((O/'erc.json').read_text())
    issues=[v for sh in erc['sheets']for v in sh['violations']]
    assert not issues,[(v['type'],v['description'])for v in issues]
    assert not erc.get('ignored_tests',[])
    project=json.loads((O/'instrumented-device.kicad_pro').read_text())
    assert not project['erc'].get('erc_exclusions',[])
    disabled={k:v for k,v in project['erc']['rule_severities'].items()if v=='ignore'}
    assert not disabled,disabled
    for p,v in bindings['source_inputs_sha256'].items():
        assert sha(ROOT/p)==v,('retained source changed',p)
    report={'status':'Native KiCad circuit conservation and ERC pass; no PCB routing/mechanical acceptance',
            'checker_sha256':sha(Path(__file__)),'native_tool_version':erc.get('kicad_version'),
            'retained_refs':len(before),'added_refs':len(added),'total_refs':len(after),
            'retained_endpoints_checked_net_type_function':len(old),'only_existing_terminal_changes':differences,
            'new_connected_endpoints':sum(1 for r,p in new if r in added),
            'source_XML_sha256':sha(source),'candidate_XML_sha256':sha(O/'native.xml'),
            'ERC_sha256':sha(O/'erc.json'),'ERC_violations':0,'ERC_ignored_tests':[], 'ERC_exclusions':[],
            'original_body69_artwork_sha256':sha(ROOT/'hardware/pcb/evt1/body/body-evt1.kicad_pcb'),
            'frozen_flange_artwork_sha256':sha(ROOT/'hardware/pcb/evt1/single-flange-routing/single-flange.kicad_pcb'),
            'source_bindings_sha256':sha(O/'source-bindings.json'),
            'local_source_sha256':{str(p.relative_to(O)):sha(p)for p in sorted(O.rglob('*'))if p.is_file()and (p.suffix in('.kicad_sch','.kicad_sym','.kicad_mod','.kicad_pro')or p.name in('fp-lib-table','sym-lib-table'))},
            'physical_validation':False,'source_promotion':False}
    (O/'native-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in('retained_refs','added_refs','retained_endpoints_checked_net_type_function','ERC_violations')}))


if __name__=='__main__':main()
