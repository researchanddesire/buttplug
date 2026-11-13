"""Independently inspect native KiCad XML and assigned footprint pin sets.

The input XML must be freshly exported by KiCad. This catches pin/net mistakes;
it does not stand in for ERC, routing or current measurements.
"""
from pathlib import Path
import hashlib
import json
import sys
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import kicad_sexp as s
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
t=ET.parse(HERE/'source-native.xml').getroot()
net={}
nets={}
for n in t.findall('./nets/net'):
    name=n.get('name');nodes={(e.get('ref'),e.get('pin')) for e in n.findall('node')}
    nets[name]=nodes
    for node in nodes:net[node]=name
expected={
 ('U103','1'):'CC1',('U103','2'):'CC2',('U103','3'):'GND',
 ('U103','4'):'VBUS_DET',('U103','7'):'CC_OUT1',('U103','8'):'CC_OUT2',
 ('U103','10'):'GND',('U103','11'):'CC_ENABLE',('U103','12'):'3V3',
 ('U114','1'):'CC_OUT1',('U114','6'):'SOURCE_REQUEST',('U114','5'):'3V3',('U114','2'):'GND',
 ('U114','3'):'BTN_CENTERn_DEBOUNCED',('U114','4'):'BTN_CENTER_PRESSED',
 ('R127','1'):'3V3',('R127','2'):'BTN_CENTERn_DEBOUNCED',
 ('J104','8'):'BTN_CENTERn_DEBOUNCED',('J104','9'):'BTN_CENTER_PRESSED',
 ('U104','A1'):'HOST_5V',('U104','A2'):'DEVICE_FAULTn',('U104','B1'):'HOST_5V',
 ('U104','B2'):'CONTACT_5V',('U104','C1'):'GND',('U104','C2'):'DEVICE_ILIM',
 ('R105','1'):'DEVICE_ILIM',('R105','2'):'DEVICE_ILIM_LOW_RETURN',
 ('R108','1'):'DEVICE_ILIM_LOW_RETURN',('R108','2'):'GND',
 ('R106','1'):'DEVICE_ILIM',('R106','2'):'DEVICE_ILIM_HIGH_RETURN',
 ('Q103','1'):'SOURCE_OK',('Q103','2'):'GND',('Q103','3'):'DEVICE_ILIM_HIGH_RETURN',
 ('U105','1'):'HOST_5V',('U105','2'):'GND',('U105','3'):'SOURCE_OK',
 ('U105','4'):'UV_LIMIT_FAULTn',('U105','5'):'UV_ILIM',('U105','6'):'UV_5V_LIMITED',
 ('U102','1'):'HOST_5V',('U102','2'):'GND',('U102','3'):'HOST_5V',('U102','5'):'3V3',
 ('J102','1'):'GND',('J102','2'):'USB_DM',('J102','3'):'USB_DP',('J102','4'):'CONTACT_5V',
 ('R101','1'):'HOST_5V',('R101','2'):'VBUS_DET',
 ('U120','1'):'CC_ENABLE',('U120','2'):'GND',('U120','3'):'HOST_5V',
 ('U120','4'):'CC_ENABLE_CT',('U120','5'):'3V3',('U120','6'):'HOST_5V',
 ('U123','1'):'CC_STATUS_READY',('U123','2'):'GND',('U123','3'):'CC_STATUS_MRn',
 ('U123','4'):'CC_STATUS_CT',('U123','5'):'3V3',('U123','6'):'HOST_5V',
 ('U122','1'):'SOURCE_DRIVE',('U122','2'):'GND',('U122','3'):'SOURCE_OFF_RETURN',
 ('U122','4'):'SOURCE_OK',('U122','5'):'HOST_5V',('U122','6'):'CC_STATUS_READY',
 ('U124','1'):'HOST_5V',('U124','2'):'GND',('U124','3'):'GND',
 ('U124','4'):'CC_STATUS_MRn',('U124','5'):'HOST_5V',('U124','6'):'CC_ENABLE',
 ('R128','1'):'3V3',('R128','2'):'CC_ENABLE',
 ('R129','1'):'3V3',('R129','2'):'CC_STATUS_READY',
 ('R130','1'):'HOST_5V',('R130','2'):'CC_ENABLE_CT',
 ('R131','1'):'HOST_5V',('R131','2'):'CC_STATUS_CT',
 ('R132','1'):'SOURCE_REQUEST',('R132','2'):'SOURCE_DRIVE',
 ('R133','1'):'SOURCE_OFF_RETURN',('R133','2'):'GND',
 ('C114','1'):'SOURCE_OK',('C114','2'):'GND',
}
for terminal,name in expected.items():assert net.get(terminal)==name,(terminal,name,net.get(terminal))
for pin in ('5','9'):assert net[('U103',pin)].startswith('unconnected-')
for label,portpins,esdpins in [('USB_DM',('A7','B7'),('1','6')),('USB_DP',('A6','B6'),('3','4'))]:
    expected_nodes={('J101',x) for x in portpins}|{('U121',x) for x in esdpins}|{('J102','2' if label=='USB_DM' else '3')}
    assert nets[label]==expected_nodes,(label,nets[label])
assert nets['CC1']=={('J101','A5'),('U103','1')}
assert nets['CC2']=={('J101','B5'),('U103','2')}
# Distinct returnnode ensures no permanent high-mode resistor path bypasses Q103.
assert nets['DEVICE_ILIM_HIGH_RETURN']=={('R106','2'),('Q103','3')}
assert nets['DEVICE_ILIM_LOW_RETURN']=={('R105','2'),('R108','1')}
parts=json.loads((HERE/'source-circuit-parts.json').read_text())['parts']
comps={e.get('ref'):e for e in t.findall('./components/comp')}
assert set(comps)=={x['reference'] for x in parts}
footprint_checks=[]
for row in parts:
    c=comps[row['reference']]
    assert c.findtext('footprint')==row['footprint']
    props={x.get('name'):x.get('value') for x in c.findall('property')}
    assert props['MPN']==row['mpn'] and props['Manufacturer']==row['manufacturer']
    fp=HERE/'DockUI.pretty'/(row['footprint'].split(':',1)[1]+'.kicad_mod')
    f=s.parse(fp.read_text());padnums={x[1].value for x in s.children(f,'pad') if x[1].value}
    sympins={pin for ref,pin in net if ref==row['reference']}
    assert padnums==sympins,(row['reference'],padnums,sympins)
    footprint_checks.append({'reference':row['reference'],'pad_numbers':sorted(padnums),'footprint_sha256':sha(fp)})
values={r:c.findtext('value') for r,c in comps.items()}
assert values['R105']=='19.1k 0.1%' and values['R108']=='100R 0.1%'
assert values['R106']=='2.52k 0.1%' and values['R107']=='34.8k 0.1%'
assert values['R101']=='887k 1%'
assert values['R127']=='10k 1%'
assert values['U103']=='TUSB320HAIRWBR'
assert values['U120']==values['U123']=='TPS3808G33DBVR'
assert values['U122']==values['U124']=='TS5A3159DBVR'
assert values['R128']==values['R129']=='10k 1%'
assert values['R130']==values['R131']=='100k 1%'
assert values['R132']=='2.52k 0.1%' and values['R133']=='100R 0.1%'
assert values['C114']=='100nF16V'
assert nets['SOURCE_REQUEST']=={('U114','6'),('R132','1')}
assert nets['SOURCE_DRIVE']=={('R132','2'),('U122','1')}
assert nets['SOURCE_OFF_RETURN']=={('U122','3'),('R133','1')}
assert nets['CC_STATUS_MRn']=={('U124','4'),('U123','3')}
assert ('U114','6') not in nets['SOURCE_OK']
assert values['U114']=='SN74LVC2G14DCKR', 'Slow open-drain edge requires Schmitt input'
assert nets['BTN_CENTERn_DEBOUNCED']=={('U114','3'),('J104','8'),('R127','2')}
native_path=HERE/'native-checks.json'
native=None
if native_path.exists():
    native=json.loads(native_path.read_text())
    for filename,expected_hash in native['source_sha256'].items():
        assert sha(HERE/filename)==expected_hash,('stale native source binding',filename)
    for filename,expected_hash in native['reports_sha256'].items():
        assert sha(HERE/filename)==expected_hash,('stale native report binding',filename)
    assert native['ERC_error_count']==0 and native['ERC_warning_count']==0
report={'status':'pass: actual KiCad native XML/footprint pin contracts',
        'kicad_native_exporter':t.findtext('./design/tool'),
        'component_count':len(comps),'purchased_positions':sum(r['manufacturer']!='manual copper' for r in parts),
        'manual_copper_features':sum(r['manufacturer']=='manual copper' for r in parts),
        'unique_purchased_MPNs':len({r['mpn'] for r in parts if r['manufacturer']!='manual copper'}),
        'explicit_terminal_checks':len(expected),
        'USB_data_path_has_only_receptacle_ESD_and_device_contact_port':True,
        'no_parallel_CC_Rd':True,'low_current_path_cannot_be_bypassed_without_qualified_Q103':True,
        'SOURCE_OK_is_actively_grounded_until_two_stage_power_qualification':True,
        'TUSB_enable_has_independent_powergood_delay':True,
        'slow_CC_edge_has_Schmitt_inverter':True,'absent_UI_harness_defaults_CENTER_released':True,
        'footprint_pin_checks':footprint_checks,
        'source_sha256':{str(p.relative_to(HERE)):sha(p) for p in sorted(HERE.glob('*'))
                         if p.is_file() and (p.suffix in ('.kicad_sch','.kicad_sym','.kicad_pro','.xml')
                                             or p.name in ('fp-lib-table','sym-lib-table','build_source.py','check_source.py',
                                                           'check_native.py','source-circuit-parts.json'))},
        'native_ERC_run':native is not None,
        'native_ERC_scope':native['scope'] if native else 'not checked',
        'native_ERC_binding_sha256':sha(native_path) if native else None,
        'PCB_created_or_routed':False,'powered_validation':False,'full_product_order_ready':False}
(HERE/'source-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256','footprint_pin_checks')},indent=2))
