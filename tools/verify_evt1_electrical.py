"""Independent EVT1 pin-contract, source-integrity and PCB/netlist checks.

Run native KiCad ERC/DRC first. This supplements those checks: an electrically
valid but wrongly named I2C bus must still fail the functional pin contract.
No hardware, USB waveform, charging or fabrication result is inferred.
"""
from pathlib import Path
import hashlib
import json
import xml.etree.ElementTree as ET
import kicad_sexp as s

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/pcb/evt1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def netlist(path):
    tree=ET.parse(path).getroot()
    components={c.get('ref'):c for c in tree.findall('./components/comp')}
    assert len(components)==len(tree.findall('./components/comp')),'Duplicate references'
    pins={}
    for net in tree.findall('./nets/net'):
        for node in net:
            key=(node.get('ref'),node.get('pin'))
            assert key not in pins,('Pin on multiple nets',key)
            pins[key]=net.get('name')
    return components,pins


def same(pins,*nodes):
    values=[pins[n] for n in nodes]
    assert len(set(values))==1,(nodes,values)
    return values[0]


def no_violations(path,board=False):
    r=json.loads(path.read_text())
    violations=r.get('violations',[])+r.get('unconnected_items',[]) if board else [v for sheet in r['sheets'] for v in sheet['violations']]
    assert not violations,(path,violations)
    return {'tool':r['kicad_version'],'report_sha256':sha(path),'violations':0}


def pcb_pad_parity(domain):
    folder=BASE/domain
    components,pins=netlist(folder/(domain+'-native.xml'))
    board=s.parse((folder/(domain+'-evt1.kicad_pcb')).read_text())
    seen={}
    for fp in s.children(board,'footprint'):
        ref=next(t[2].value for t in s.children(fp,'fp_text') if t[1].value=='reference')
        if ref.startswith('H'):
            assert (domain=='dock' and ref in ('H1','H2','H3','H4')) or (domain in ('flange','sensor') and ref in ('H1','H2'))
            continue
        assert ref in components and ref not in seen,ref
        seen[ref]=True
        expected_fp=components[ref].findtext('footprint')
        # KiCad7 stores the loaded native library path as a full id or name.
        assert fp[1].value.split(':')[-1]==expected_fp.split(':')[-1],ref
        for pad in s.children(fp,'pad'):
            number=pad[1].value
            if not number:continue
            actual=s.child(pad,'net')
            actual=actual[2].value if actual else None
            expected=pins.get((ref,number))
            assert actual==expected,(domain,ref,number,actual,expected)
    assert set(seen)==set(components),(domain,set(components)-set(seen))
    return {'components':len(components),'all_native_pad_nets_match':True}


def pcb_parity(domain):
    folder=BASE/domain
    parity=pcb_pad_parity(domain)
    mcad=json.loads((folder/'mcad.json').read_text())
    assert mcad['board_sha256']==sha(folder/(domain+'-evt1.kicad_pcb'))
    return {**parity,'mcad_source_current':True,
            'ERC':no_violations(folder/'erc.json'),'DRC':no_violations(folder/'drc.json',True)}


def main():
    native=json.loads((BASE/'native-checks.json').read_text())
    for name,digest in {**native['source_sha256'],**native['netlist_sha256']}.items():
        assert sha(ROOT/name)==digest,('Native checks stale',name)
    for rows in native['checks'].values():
        for row in rows:assert sha(ROOT/row['report'])==row['sha256'],('Native report changed',row['report'])
    parts=json.loads((BASE/'parts-validation.json').read_text())
    assert parts['parts_selection_sha256']==sha(BASE/'parts-selection.json'),'Selected parts changed after checks'
    assert parts['pcb_ordering_sha256']==sha(BASE/'pcb-ordering.csv'),'Ordering worksheet changed after checks'
    for name,digest in parts['source_native_netlist_sha256'].items():assert sha(ROOT/name)==digest,('Parts/netlist checks stale',name)
    c,p=netlist(BASE/'system-native.xml')
    for nodes in (
        (('U6','18'),('U7','9'),('U81','4'),('J6','8'),('J7','8')),
        (('U6','19'),('U7','10'),('U81','1'),('J6','9'),('J7','9')),
        (('U6','16'),('J6','10'),('J7','10'),('R61','1'),('R62','1')),
        (('U7','4'),('R61','2'),('J5','1'),('TH101','1'),('C62','1')),
        (('U7','5'),('R62','2'),('R63','1'),('C63','1')),
        (('U7','8'),('U6','3'),('U81','9'),('U81','10'),('U71','4')),
        (('U7','1'),('U7','3'),('U7','6'),('U7','7'),('J5','2'),('TH101','2'),('U81','6'),('U81','8'),('U71','2'),('U71','5'),('U71','6')),
        (('J1','2'),('R75','1'),('U75','1'),('U75','6')),
        (('R75','2'),('U6','26'),('J4','2')),
        (('J1','3'),('R76','1'),('U75','3'),('U75','4')),
        (('R76','2'),('U6','27'),('J4','3')),
        (('J1','4'),('F1','1'),('U75','5')),
        (('J1','1'),('U75','2'),('U6','1'),('U1','5'),('U1','6')),
        (('SW1','1'),('U71','3'),('R71','2'),('D71','1')),
        (('U6','13'),('D71','2'),('D72','2'),('R35','2')),
        (('D72','1'),('U1','7'),('U6','30'),('U4','6')),
        (('D73','1'),('SW2','1'),('U6','6')),
        (('D73','2'),('U6','23'),('R34','2'),('J4','5')),
        (('U71','1'),('U6','8'),('C33','1'),('R31','2'),('J4','4')),
    ):same(p,*nodes)
    assert p[('SW1','1')]!=p[('U6','13')],'Raw switch must be separate from dock-wake OR'
    assert p[('D73','1')]!=p[('D73','2')],'Mode/boot need diode isolation'
    assert not {'U101','J101','C101'}&set(c),'Old TMP117 module must be absent'
    assert c['U7'].findtext('value').startswith('ADS1115')
    assert 'B57540G1103F000' in c['TH101'].findtext('value')
    assert c['U81'].findtext('value')=='LSM303AGRTR'
    _,dock=netlist(BASE/'dock/dock-native.xml')
    for nodes in (
        (('J91','A6'),('J91','B6'),('U91','3'),('U91','4'),('J93','3')),
        (('J91','A7'),('J91','B7'),('U91','1'),('U91','6'),('J93','2')),
        (('J91','A4'),('J91','A9'),('J91','B4'),('J91','B9'),('U92','1'),('U92','3'),('U91','5')),
        (('J93','4'),('U92','6'),('C92','1')),
        (('J93','1'),('U92','2'),('U91','2'),('J91','A1'),('J91','S1'),('R91','2'),('R92','2')),
        (('J91','A5'),('R91','1')),(('J91','B5'),('R92','1')),
        (('U92','5'),('R93','1')),
    ):same(dock,*nodes)
    assert dock[('J91','A5')]!=dock[('J91','B5')],'CC resistors must be independent'
    _,pins=netlist(BASE/'pins/pins-native.xml')
    for i,net in enumerate(('GND','DOCK_DM','DOCK_DP','DOCK_5V')):
        assert same(pins,('P'+str(91+i),'1'),('J94',str(1+i)))==net
    m=json.loads((BASE/'pins/mcad.json').read_text())
    for i in range(4):
        pad=next(p for p in m['pads'] if p['ref']=='P'+str(91+i))
        assert pad['xy_mm']==[4+6*i,6.7]
    wire=[p for p in m['pads'] if p['ref']=='J94']
    assert len(wire)==4 and all(p['back'] and not p['front'] and p['xy_mm'][1]==8.5 for p in wire)
    for filename,digest in json.loads((BASE/'source-hashes.json').read_text()).items():
        assert sha(ROOT/filename)==digest,('R35F source changed',filename)
        assert sha(BASE/'layout-seeds'/Path(filename).name)==digest
    boards={d:pcb_parity(d) for d in ('dock','pins')}
    candidates={}
    for d in ('body','flange','sensor'):
        folder=BASE/d;path=folder/(d+'-evt1.kicad_pcb')
        if not path.exists():continue
        parity=pcb_pad_parity(d);r=json.loads((folder/'drc.json').read_text())
        assert not r['violations'] and not r['unconnected_items'],(d,'Native DRC must pass')
        mcad=json.loads((folder/'mcad.json').read_text());assert mcad['board_sha256']==sha(path),(d,'MCAD stale')
        candidates[d]={**parity,'board_sha256':sha(path),'DRC_report_sha256':sha(folder/'drc.json'),
                       'DRC_violations':len(r['violations']),'unconnected_items':len(r['unconnected_items']),
                       'fabrication_release':False,
                       'mcad_source_current':True,
                       'scope':'Routed native board; source-bound DRC and pad/netlist parity pass. Product/package qualification remains open.'}
    report={'scope':'EVT1 electrical candidate and five routed PCBs; full product not released',
            'full_system_components':len(c),'functional_pin_contract':'pass','R35F_sources_preserved':True,
            'full_system_ERC':no_violations(BASE/'erc.json'),'body_ERC':no_violations(BASE/'body/erc.json'),
            'cradle_boards':boards,
            'device_layout_candidates':candidates,
            'standalone_flange_sensor_ERC':'External 3V3/GND supply is modeled by the body in the full-system ERC; standalone pages report undriven supply pins.',
            'full_product_order_ready':False,
            'native_checks_sha256':sha(BASE/'native-checks.json'),
            'selected_PCB_parts':{'validation_sha256':sha(BASE/'parts-validation.json'),'purchased_positions':parts['purchased_positions'],'unique_order_lines':parts['unique_order_lines'],'scope':'Exact PCB part selections and native/order parity pass; stock, supplier acceptance and physical qualification pending'},
            'remaining_before_complete_EVT_build_package':['Complete actual device mechanics, assembly paths and factory axes workflow','Protected pack RFQ acceptance, non-PCB purchased parts and pack retention',
                         'Rear-nut lock and machining drawings','Closed-assembly button/contact seals, overmold process and loom',
                         'Factory magnetic registration/calibration procedure and full compass behavior'],
            'physical_validation_after_build':['USB/charging/fault/fit/thermal tests','Machining, print and casting acceptance',
                                                'Magnetic survey and heading accuracy','Materials, sealing, loads and endurance'],
            'source_sha256':{str(p.relative_to(ROOT)):sha(p) for p in sorted(BASE.rglob('*'))
                             if p.suffix in ('.kicad_sch','.kicad_sym','.kicad_pcb','.kicad_pro','.kicad_mod')},
            'verifier_sha256':sha(Path(__file__))}
    (BASE/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'functional_pin_contract':'pass','system_ERC':0,'body_ERC':0,'dock_ERC_DRC':0,'pins_ERC_DRC':0,'full_product_order_ready':False}))


if __name__=='__main__':main()
