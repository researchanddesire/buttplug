"""Independent native-to-ordering checks for selected EVT1 PCB components.

Decodes passive manufacturer part numbers and compares their case, nominal
value, rating and tolerance with the saved native netlist. It does not replace
manufacturer curves, supplier sourcing, paste/reflow or physical acceptance.
"""
from pathlib import Path
from collections import Counter
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/pcb/evt1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def resistance(value):
    m=re.match(r'([\d.]+)([kKM]?)',value);assert m,value
    return float(m[1])*{'':1,'k':1000,'K':1000,'M':1e6}[m[2]]


def main():
    source=BASE/'parts-selection.json';r=json.loads(source.read_text())
    parts={(p['domain'],p['ref']):p for p in r['components']};assert len(parts)==len(r['components'])
    seen=set();nativefiles={};passives=0
    for domain in ('body','flange','sensor','dock','pins'):
        path=BASE/domain/(domain+'-native.xml');assert sha(path)==r['source_netlist_sha256'][str(path.relative_to(ROOT))]
        nativefiles[str(path.relative_to(ROOT))]=sha(path)
        for comp in E.parse(path).getroot().findall('./components/comp'):
            key=(domain,comp.get('ref'));p=parts[key];seen.add(key)
            value=comp.findtext('value');fp=comp.findtext('footprint')
            assert p['schematic_value']==value and p['footprint']==fp,key
            if not p['purchase']:
                assert p['mpn'] is None and p['assembly_note'],key;continue
            mpn=p['mpn'];assert mpn and p['manufacturer_source'].startswith('https://'),key
            if key[1].startswith('R'):
                m=re.fullmatch(r'(TNPW|CRCW)(0402|0603|0805)([0-9RKM]+)([A-Z]+)',mpn);assert m,(key,mpn)
                series,size,code,suffix=m.groups();assert size in fp,(key,'Case mismatch')
                mark=next(c for c in code if c in 'RKM');ohms=float(code.replace(mark,'.'))*{'R':1,'K':1000,'M':1e6}[mark]
                assert abs(ohms/resistance(value)-1)<1e-9,(key,'MPN resistance',mpn,value)
                assert ohms==p['resistance_ohm'],key
                if series=='TNPW':
                    assert suffix[0]=='B' and p['tolerance_percent']==.1,(key,'Tolerance code')
                    assert 10<=ohms<={'0402':100000,'0603':332000,'0805':1e6}[size],(key,'Family range')
                else:assert suffix[0]=='F' and p['tolerance_percent']==1,key
                required=re.search(r'([\d.]+)%',value)
                if required:assert p['tolerance_percent']<=float(required[1]),key
                passives+=1
            elif key[1].startswith('C'):
                if mpn.startswith('GRM'):
                    size={'15':'0402','18':'0603','21':'0805','31':'1206','32':'1210'}[mpn[3:5]]
                    voltage={'1A':10,'1C':16,'1E':25,'1H':50}[mpn[8:10]]
                    dielectric={'R6':'X5R','R7':'X7R'}[mpn[6:8]]
                else:
                    assert mpn.startswith('C'),(key,mpn)
                    size={'1005':'0402','1608':'0603','2012':'0805'}[mpn[1:5]]
                    dielectric=mpn[5:8];voltage={'1A':10,'1C':16,'1E':25,'1H':50}[mpn[8:10]]
                code=mpn[10:13];tol={'J':5,'K':10,'M':20}[mpn[13]]
                farads=int(code[:2])*10**int(code[2])*1e-12
                m=re.match(r'([\d.]+)([unp])F',value);assert m,key
                expected=float(m[1])*{'u':1e-6,'n':1e-9,'p':1e-12}[m[2]]
                assert abs(farads/expected-1)<1e-9 and abs(farads/p['capacitance_F']-1)<1e-9,(key,'MPN capacitance')
                assert size in fp and voltage==p['rated_voltage_V'] and dielectric==p['dielectric'] and tol==p['tolerance_percent'],key
                rating=re.search(r'([\d.]+)V',value)
                if rating:assert voltage>=float(rating[1]),(key,'Underrated voltage')
                for required in ('X7R','X5R'):
                    if required in value:assert dielectric==required,(key,'Dielectric mismatch')
                passives+=1
    assert seen==set(parts),'Native/selection coverage differs'
    ordered=Counter()
    with (BASE/'pcb-ordering.csv').open(newline='') as f:
        for line in csv.DictReader(f):
            refs=line['References'].split();assert len(refs)==int(line['Qty_per_complete_device_and_dock'])
            for ref in refs:
                domain,refname=ref.split(':');p=parts[(domain,refname)]
                assert p['purchase'] and p['mpn']==line['MPN'] and p['manufacturer']==line['Manufacturer'],ref
                ordered[(domain,refname)]+=1
    assert ordered==Counter({k:1 for k,p in parts.items() if p['purchase']}),'Ordering quantity/coverage mismatch'
    result={'scope':'Native component/order worksheet parity and passive MPN decoding; no stock or physical validation',
            'parts_selection_sha256':sha(source),'pcb_ordering_sha256':sha(BASE/'pcb-ordering.csv'),
            'source_native_netlist_sha256':nativefiles,'native_positions':len(parts),'purchased_positions':len(ordered),
            'nonpurchased_features':len(parts)-len(ordered),'passive_MPN_case_value_rating_tolerance_checks':passives,
            'unique_order_lines':len({p['mpn'] for p in parts.values() if p['purchase']}),
            'verifier_sha256':sha(Path(__file__)),'C83_effective_capacitance':'Incoming/process acceptance required; nominal MPN decoding does not verify installed capacitance',
            'stock_and_supplier_acceptance':False,'physical_validation':False,'full_product_order_ready':False}
    (BASE/'parts-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('native_positions','purchased_positions','nonpurchased_features','passive_MPN_case_value_rating_tolerance_checks','unique_order_lines')}))


if __name__=='__main__':main()
