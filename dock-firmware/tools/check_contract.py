#!/usr/bin/env python3
"""Verify firmware package/GPIO assignments against hardware's pin contract."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def check():
    local=json.loads((ROOT/'pin-map.json').read_text())
    source=ROOT.parent/local['hardware_source']
    hw=json.loads(source.read_text())['MCU']
    assert hw['mpn']==local['mpn'] and hw['package'].startswith(local['package'])
    import hashlib,xml.etree.ElementTree as ET
    folder=source.parent
    bound=json.loads((folder/'native-checks.json').read_text())
    for rel,value in bound['source_sha256'].items():
        assert hashlib.sha256((folder/rel).read_bytes()).hexdigest()==value,('stale controller source',rel)
    xml=folder/'dock-control-native.xml'
    assert hashlib.sha256(xml.read_bytes()).hexdigest()==bound['reports_sha256'][xml.name]
    graph={}
    for net in ET.parse(xml).getroot().findall('./nets/net'):
        for node in net.findall('node'):graph[(node.get('ref'),node.get('pin'))]=net.get('name')
    native=local['pins']
    aliases={'NTC_BASE':'NTC_BASE_ADC','NTC_LID':'NTC_LID_ADC','DEVICE_LIMIT_FAULTn':'DEVICE_FAULTn'}
    for signal,point in native.items():
        physical=hw['physical48pins'][str(point['physical_pin'])]
        want=aliases.get(signal,signal)
        if signal.startswith('LCD_'):want+='_MCU'
        assert physical['name']==point['gpio'] and physical['net']==want,(signal,point,physical)
        assert graph[('U201',str(point['physical_pin']))]==want,(signal,want)
    # Explicit chains preserve logical firmware names while verifying the
    # filtered/series-resistor aliases on the actual MCU terminals.
    for n,net in enumerate([f'LCD_DB{j}'for j in range(8)]+['LCD_A0','LCD_WRn','LCD_CSn','LCD_RESETn'],201):
        assert graph[('R'+str(n),'1')]==net+'_MCU' and graph[('R'+str(n),'2')]==net
    for ref,net in [('R220','NTC_BASE'),('R221','NTC_LID')]:
        assert graph[(ref,'1')]==net and graph[(ref,'2')]==net+'_ADC'
    header=(ROOT/'include/board_pins.h').read_text()
    for signal,point in native.items():
        port,pin=re.fullmatch(r'P([ABCH])([0-9]+)',point['gpio']).groups()
        assert re.search(r'^#define '+re.escape(signal)+r'_PORT GPIO'+port+r'$',header,re.M)
        assert re.search(r'^#define '+re.escape(signal)+r'_PIN '+pin+r'u$',header,re.M)
    for n in range(8): assert native[f'LCD_DB{n}']['gpio']==f'PA{n}'
    assert native['NTC_BASE']['gpio']=='PB0' and native['NTC_LID']['gpio']=='PB1'
    assert native['MON_I2C_SCL']['gpio']=='PB10' and native['MON_I2C_SDA']['gpio']=='PB11'
    assert native['SWDIO']['gpio']=='PA13' and native['SWCLK']['gpio']=='PA14'
    manifest=json.loads((ROOT/'vendor/sources.json').read_text())
    for f in manifest['files']:
        assert hashlib.sha256((ROOT/'vendor'/f['file']).read_bytes()).hexdigest()==f['sha256'],f
    return {'GPIOs_checked':len(native),'vendor_files_checked':len(manifest['files']),
            'hardware_source':str(source.relative_to(ROOT.parent)),
            'native_netlist':str(xml.relative_to(ROOT.parent)),
            'native_netlist_sha256':hashlib.sha256(xml.read_bytes()).hexdigest(),
            'explicit_series_filter_aliases':True,'pass':True}

if __name__=='__main__': print(json.dumps(check(),indent=2))
