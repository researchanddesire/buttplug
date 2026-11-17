"""Check WireViz connections and BOM against the native radio pin contract."""

import argparse
from collections import Counter
import csv
from hashlib import sha256
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

from wireviz.wireviz import parse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
RADIO = ROOT / 'hardware/pcb/evt1/case-telemetry-study/case-radio'
SIGNALS = ['RADIO_5V', 'GND', 'MON_I2C_SDA', 'MON_I2C_SCL', 'RADIO_IRQn', 'RADIO_ACTIVE_EN']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exports', required=True, type=Path)
    parser.add_argument('--check', action='store_true', help='Compare with the saved source audit')
    args = parser.parse_args()
    xml = RADIO / 'case-radio-system-native.xml'
    recipe = HERE / 'main-to-radio.yml'
    check_path = RADIO / 'native-checks.json'
    netlist_bytes = xml.read_bytes()
    netlist_hash = sha256(netlist_bytes).hexdigest()
    schematic_check = json.loads(check_path.read_text())
    assert schematic_check['native_netlist_sha256'] == netlist_hash and not schematic_check['erc_violations']
    native = ET.fromstring(netlist_bytes)
    expected = list(zip(map(str, range(1, 7)), SIGNALS))
    for ref in ('J150', 'J901'):
        component = native.find(f"./components/comp[@ref='{ref}']")
        assert component.findtext("./fields/field[@name='MPN']") == 'SM06B-GHS-TB(LF)(SN)'
        terminals = [(node.get('pin'), net.get('name')) for net in native.findall('./nets/net')
                     for node in net.findall('node') if node.get('ref') == ref]
        assert Counter(terminals) == Counter(expected), ref
    diagram = parse(recipe, return_types='harness')
    assert set(diagram.connectors) == {'J150', 'J901'} and set(diagram.cables) == {'Radio'}
    for connector in diagram.connectors.values():
        assert connector.mpn == 'GHR-06V-S' and connector.pinlabels == SIGNALS
    bundle = diagram.cables['Radio']
    connections = [(c.from_name, c.from_pin, c.via_port, c.to_name, c.to_pin) for c in bundle.connections]
    assert connections == [('J150', pin, pin, 'J901', pin) for pin in range(1, 7)]
    assert bundle.mpn == '1371-26-7' and bundle.gauge == 26 and bundle.gauge_unit == 'AWG'
    assert bundle.length_unit == 'm' and bundle.length == .175 and bundle.wirelabels == SIGNALS
    with (args.exports / 'main-to-radio.bom.tsv').open(newline='') as source:
        rows = list(csv.DictReader(source, delimiter='\t'))
    parts = {(row['Manufacturer'], row['MPN'], row['Unit']): float(row['Qty']) for row in rows}
    assert len(parts) == len(rows) == 3
    assert parts.pop(('JST', 'GHR-06V-S', '')) == 2
    assert parts.pop(('JST', 'SSHL-002T-P0.2', '')) == 12
    assert math.isclose(parts.pop(('Allied Wire and Cable', '1371-26-7', 'm')), 1.05)
    evidence = {
        'scope': 'Schematic and WireViz bench harness only. Installed route and physical continuity open.',
        'source_sha256': {str(path.relative_to(ROOT)): sha256(path.read_bytes()).hexdigest()
                          for path in (xml, recipe, check_path, Path(__file__))},
        'connector_pins': {'J150': dict(expected), 'J901': dict(expected)},
        'bench_stock': {'GHR-06V-S': 2, 'SSHL-002T-P0.2': 12, '1371-26-7_m': 1.05},
    }
    payload = json.dumps(evidence, indent=2) + '\n'
    report = HERE / 'native-checks.json'
    if args.check:
        assert report.read_text() == payload
    else:
        report.write_text(payload)
    print('12 native terminals, six straight-through conductors and three stock rows match.')


if __name__ == '__main__':
    main()
