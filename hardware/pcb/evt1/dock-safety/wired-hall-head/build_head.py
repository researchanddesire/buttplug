"""Native remote Hall head for the wired Main staged product schematic."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
from xml.etree import ElementTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import native_helpers
from native_helpers import Project, g, s

TI = 'Texas Instruments'
TI_DOC = 'https://www.ti.com/lit/ds/symlink/'
DIODE_DOC = 'https://www.diodes.com/datasheet/download/DMG1012T.pdf'


def make_head(folder):
    project = Project(folder, 'wired-hall-head', 'Compass wired lid Hall head',
                      '15c9a325-7fe9-4254-9495-c0f310f37681', 'WiredHallHead')
    g.ic('WirePads', [(1, 'HEAD_FEED', 'passive'), (2, 'SIG', 'passive'), (3, 'RETURN', 'passive')],
         [], '', 'Direct soldered head wires, with separate loom strain relief')
    g.ic('DRV5021', [(1, 'VCC', 'power_in'), (3, 'GND', 'power_in')],
         [(2, 'OUT', 'open_collector')], TI_DOC + 'drv5021.pdf', 'Unipolar Hall switch')
    g.ic('TPS3808G01', [(6, 'VDD', 'power_in'), (5, 'SENSE', 'input'), (3, 'MRn', 'input')],
         [(1, 'RESETn', 'open_collector'), (2, 'GND', 'power_in'), (4, 'CT', 'passive')],
         TI_DOC + 'tps3808.pdf', 'Local head supply monitor')
    g.ic('SN74LVC1G58', [(1, 'IN0', 'input'), (3, 'IN1', 'input'), (6, 'IN2', 'input')],
         [(4, 'Y', 'output'), (5, 'VCC', 'power_in'), (2, 'GND', 'power_in')],
         TI_DOC + 'sn74lvc1g58.pdf', 'Local head valid AND Hall low')
    g.ic('DMG1012T', [(1, 'G', 'input'), (2, 'S', 'passive')], [(3, 'D', 'passive')],
         DIODE_DOC, 'Low-voltage N-channel switch, body diode points from local return to drain')
    ec = 'Package_TO_SOT_SMD'
    wire_pads = project.custom('WirePads_3_P1.35mm', [
        (str(i), (i - 2) * 1.35, 0, .80, 1.80, 'rect') for i in range(1, 4)
    ], (3.5, 1.8), (3.5, 1.8), 'Direct soldered wire lands. No connector, pad drill or paste.')
    pad_file = project.fp_dir / 'WirePads_3_P1.35mm.kicad_mod'
    pad_file.write_text(pad_file.read_text().replace('(attr smd)', '(attr smd exclude_from_bom)').replace('"F.Paste" ', ''))
    project.fp_sources['WirePads_3_P1.35mm']['sha256'] = native_helpers.sha(pad_file)
    sot3 = project.stock(ec, 'SOT-23')
    sot6 = project.stock(ec, 'SOT-23-6')
    mosfet = project.stock(ec, 'SOT-523')
    resistor = project.stock('Resistor_SMD', 'R_0603_1608Metric')
    capacitor = project.stock('Capacitor_SMD', 'C_0402_1005Metric')
    project.note('A and B use the same head. Fit one per closure station.', 25.4, 17.78)
    project.note('Keep SIG isolated from local VDD and route through R5 before any head semiconductor.\n'
                 'Product interlock permission requires qualified cutoff/leakage, power, terminals and loom.', 25.4, 27.94)
    project.part('WirePads', 'J1', 'Direct solder', 91.44, 83.82,
                 {1: 'HEAD_FEED', 2: 'SIG', 3: 'GND'}, wire_pads, 'manual copper', 'WirePads_3_P1.35mm')
    project.part('DRV5021', 'U1', 'DRV5021A2QDBZR', 205.74, 83.82,
                 {1: 'HEAD_FEED', 2: 'HALL_OUTn', 3: 'GND'}, sot3, TI, 'DRV5021A2QDBZR',
                 'A2 is an electrical candidate. A3 uses the same DBZ footprint and is the leading modeled magnetic candidate. Do not order by this annotation.')
    project.part('TPS3808G01', 'U2', 'TPS3808G01DBVR', 320.04, 83.82,
                 {6: 'HEAD_FEED', 5: 'HEAD_SENSE', 3: 'HEAD_FEED', 1: 'HEAD_VALID', 2: 'GND', 4: None},
                 sot6, TI, 'TPS3808G01DBVR', 'CT open: published 12–28 ms release')
    project.part('SN74LVC1G58', 'U3', 'SN74LVC1G58DBVR', 434.34, 83.82,
                 {1: 'GND', 3: 'HALL_OUTn', 6: 'HEAD_VALID', 4: 'HEAD_SINK', 5: 'HEAD_FEED', 2: 'GND'},
                 sot6, TI, 'SN74LVC1G58DBVR')
    project.part('DMG1012T', 'Q1', 'DMG1012T-7', 525.78, 83.82,
                 {1: 'HEAD_SINK', 2: 'GND', 3: 'SINK_DRAIN'}, mosfet, 'Diodes Incorporated', 'DMG1012T-7')
    for index, (value, mpn, a, b) in enumerate((
        ('100k 1%', 'RC0603FR-07100KL', 'HEAD_FEED', 'HALL_OUTn'),
        ('100k 1%', 'RC0603FR-07100KL', 'HEAD_FEED', 'HEAD_VALID'),
        ('53.6k 0.1% 25ppm/K', 'RT0603BRD0753K6L', 'HEAD_FEED', 'HEAD_SENSE'),
        ('10k 0.1% 25ppm/K', 'RT0603BRD0710KL', 'HEAD_SENSE', 'GND'),
        ('5.62k 1%', 'RC0603FR-075K62L', 'SIG', 'SINK_DRAIN'),
        ('150k 1%', 'RC0603FR-07150KL', 'HEAD_SINK', 'GND'),
    ), 1):
        project.part('R', f'R{index}', value, 50.8 + 86.36*(index - 1), 149.86,
                     {1: a, 2: b}, resistor, 'Yageo', mpn)
    for ref, value, manufacturer, mpn, note in (
        ('C1', '220nF 35V X7R', 'TDK', 'C1005X7R1V224K050BC',
         'At U1.1. Verify at least 100nF effective at the installed bias and over temperature/age.'),
        ('C2', '100nF 16V X7R', 'Murata', 'GRM155R71C104KA88D', 'At U2.6.'),
        ('C3', '100nF 16V X7R', 'Murata', 'GRM155R71C104KA88D', 'At U3.5.'),
    ):
        project.part('C', ref, value, 50.8 + 86.36*(int(ref[1:]) - 1), 190.5,
                     {1: 'HEAD_FEED', 2: 'GND'}, capacitor, manufacturer, mpn, note)
    project.flag('#FLG01', 'HEAD_FEED', 383.54, 190.5)
    project.flag('#FLG02', 'GND', 472.44, 190.5)
    project.save()
    path = folder / 'wired-hall-head.kicad_sch'
    tree = s.parse(path.read_text())
    s.child(s.child(tree, 'title_block'), 'comment')[2] = s.string('WIRED PRODUCT CANDIDATE — OPERATING RELEASE PENDING')
    j1 = next(symbol for symbol in s.children(tree, 'symbol') if s.prop(symbol, 'Reference') == 'J1')
    s.child(j1, 'in_bom')[1] = s.atom('no')
    s.write(path, tree)
    pro = folder / ('wired-hall-head.kicad_pro')
    settings = json.loads(pro.read_text())
    settings['board'] = {'design_settings': {'rules': {'min_copper_edge_clearance': .30, 'min_track_width': .20}}}
    pro.write_text(json.dumps(settings, indent=2) + '\n')
    return project


def verify(folder, project, cli):
    stem = 'wired-hall-head.kicad_sch'
    for command in (
        ['sch', 'erc', '--format', 'json', '--exit-code-violations', '-o', 'erc.json'],
        ['sch', 'export', 'netlist', '--format', 'kicadxml', '-o', 'native.xml'],
    ):
        subprocess.run([cli, *command, stem], cwd=folder, check=True, capture_output=True, text=True)
    erc = json.loads((folder / 'erc.json').read_text())
    assert not any(sheet['violations'] for sheet in erc['sheets'])
    native = ElementTree.parse(folder / 'native.xml')
    expected = {(row['reference'], str(pin)): net for row in project.rows for pin, net in row['pins'].items()}
    actual = {(node.get('ref'), node.get('pin')): None if net.get('name').startswith('unconnected-') else net.get('name')
              for net in native.findall('./nets/net') for node in net.findall('node') if not node.get('ref').startswith('#')}
    assert actual == expected
    assert {pin for pin, net in actual.items() if net == 'SIG'} == {('J1', '2'), ('R5', '1')}
    assert {pin for pin, net in actual.items() if net == 'SINK_DRAIN'} == {('R5', '2'), ('Q1', '3')}
    print(f'ERC 0/0. {len(project.rows)} refs and {len(actual)} exact device/connector terminals.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default=HERE, type=Path)
    parser.add_argument('--stock-footprints', required=True, type=Path)
    parser.add_argument('--kicad-cli', required=True)
    args = parser.parse_args()
    native_helpers.STOCK = args.stock_footprints
    verify(args.out, make_head(args.out), args.kicad_cli)
