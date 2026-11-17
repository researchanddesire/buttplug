"""Capture the wired USB circuit in the frozen six-leaf dock context."""
import argparse
from collections import defaultdict
import json
import math
import os
from pathlib import Path
import sys
import uuid

from contract import CHANGED, DEVICES, EVT, HERE, PASSIVES, ROOT, digest

sys.path.insert(0, str(ROOT / 'tools'))
import electronics_r0_generate as g
import kicad_sexp as sx

PROJECT = 'dock-wired-system'
TRANSPORT = 'dock-wired-transport'
REMOTE_BOARD_SHEETS = {'dock-lid-ui.kicad_sch', 'dock-uv-base.kicad_sch', 'dock-uv-lid.kicad_sch'}
SOURCE = EVT / 'dock-system'
NS = uuid.UUID('bed245d2-3751-4be1-bad6-83e645ea35c1')
VALUES = {
    'R107': ('40.2k 0.1% 25ppm/K', 'RT0603BRD0740K2L', 'Yageo'),
    'R401': ('4.22ohm 1% 100ppm/K', 'CRCW08054R22FKEA', 'Vishay'),
    'R501': ('4.22ohm 1% 100ppm/K', 'CRCW08054R22FKEA', 'Vishay'),
}
TESTPOINTS = {
    'TP151': 'PC_LOCKn', 'TP152': 'GND', 'TP153': 'RP_SWDIO', 'TP154': 'RP_SWCLK',
    'TP155': 'RP_RUN', 'TP156': 'USB_HOST_3V3', 'TP157': 'RP_BOOTSEL_PAD',
}

SERVICE_COPPER = {*TESTPOINTS, *(f'TP{number}' for number in range(601, 608))}


def uid(value):
    return str(uuid.uuid5(NS, value))


def xy(node):
    return tuple(round(float(v.value), 4) for v in node[1:3])


def pin_origin(tree, symbol, number):
    lib = next(lib for lib in sx.children(sx.child(tree, 'lib_symbols'), 'symbol')
               if lib[1].value == sx.value(symbol, 'lib_id'))
    pin = next(pin for unit in sx.children(lib, 'symbol') for pin in sx.children(unit, 'pin')
               if sx.value(pin, 'number') == number)
    at = sx.child(symbol, 'at')
    local = sx.child(pin, 'at')
    assert float(at[3].value) == 0
    return (round(xy(at)[0] + xy(local)[0], 4), round(xy(at)[1] - xy(local)[1], 4)), int(local[3].value)


def change_terminal(tree, symbol, ref, pin, old, new):
    origin, angle = pin_origin(tree, symbol, pin)
    if old is not None:
        wires = [wire for wire in sx.children(tree, 'wire')
                 if origin in [xy(end) for end in sx.children(sx.child(wire, 'pts'), 'xy')]]
        assert len(wires) == 1, (ref, pin)
        end = next(xy(point) for point in sx.children(sx.child(wires[0], 'pts'), 'xy') if xy(point) != origin)
        labels = [lab for lab in sx.children(tree, 'global_label') if xy(sx.child(lab, 'at')) == end]
        assert len(labels) == 1 and labels[0][1].value == old, (ref, pin)
        labels[0][1] = sx.string(new)
        return
    markers = [node for node in sx.children(tree, 'no_connect') if xy(sx.child(node, 'at')) == origin]
    assert len(markers) == 1, (ref, pin)
    tree.remove(markers[0])
    x, y = origin
    ex = round(x - 5.08 * math.cos(math.radians(angle)), 4)
    ey = round(y + 5.08 * math.sin(math.radians(angle)), 4)
    rotation, align = (180, 'right') if angle == 0 else (0, 'left')
    tree.extend([
        sx.parse(f'(wire (pts (xy {x} {y}) (xy {ex} {ey})) (stroke (width 0) (type default)) (uuid {uid(ref + pin + "wire")}))'),
        sx.parse(f'(global_label {g.q(new)} (shape input) (at {ex} {ey} {rotation}) '
                 f'{g.effects(1.016, "(justify " + align + ")")} (uuid {uid(ref + pin + "label")}))'),
    ])


def set_property(symbol, name, val):
    matches = [item for item in sx.children(symbol, 'property') if item[1].value == name]
    if matches:
        assert len(matches) == 1
        matches[0][2] = sx.string(val)
        return
    symbol.append(sx.parse(f'(property {g.q(name)} {g.q(val)} (at 0 0 0) {g.effects(extra="hide")})'))


def add_instances(tree, leaf_name):
    leaf = uid(leaf_name)
    projects = (TRANSPORT,) if leaf_name in REMOTE_BOARD_SHEETS else (PROJECT, TRANSPORT)
    for symbol in sx.children(tree, 'symbol'):
        inst = sx.child(symbol, 'instances')
        assert inst is not None
        ref = sx.prop(symbol, 'Reference')
        unit = sx.value(symbol, 'unit') or '1'
        inst[:] = [node for node in inst if not (isinstance(node, list) and sx.tag(node) == 'project'
                                                and node[1].value in (PROJECT, TRANSPORT))]
        for project in projects:
            inst.append(sx.parse(f'(project {g.q(project)} (path {g.q("/" + uid(PROJECT) + "/" + leaf)} '
                                 f'(reference {g.q(ref)}) (unit {unit})))'))
        if ref in SERVICE_COPPER:
            sx.child(symbol, 'in_bom')[1] = sx.atom('no')


def write_root(project, sheets, title):
    # Both roots share leaf files and keep the existing hierarchy UUIDs.
    top = sx.parse(f'(kicad_sch (version 20230121) (generator wired_main_builder) (uuid {uid(PROJECT)}) '
                   f'(paper "A3") (title_block (title {g.q(title)}) '
                   '(rev "Circuit candidate") (company "Research and Desire")) (lib_symbols) '
                   '(sheet_instances (path "/" (page "1"))))')
    for i, name in enumerate(sheets):
        if project == PROJECT and name in REMOTE_BOARD_SHEETS:
            continue
        x, y = 25.4 + 127 * (i % 3), 50.8 + 63.5 * (i // 3)
        top.append(sx.parse(f'(sheet (at {x} {y}) (size 101.6 25.4) (stroke (width 0.1524) (type default)) '
                            f'(fill (color 0 0 0 0)) (uuid {uid(name)}) '
                            f'(property "Sheetname" {g.q(Path(name).stem)} (at {x} {y - .508} 0) {g.effects()}) '
                            f'(property "Sheetfile" {g.q("sheets/" + name)} (at {x} {y + 25.908} 0) {g.effects()}))'))
    sx.write(HERE / (project + '.kicad_sch'), top)


def capture_context():
    trees = {}
    changes = set()
    values = set()
    for path in sorted((SOURCE / 'sheets').glob('*.kicad_sch')):
        tree = sx.parse(path.read_text())
        for symbol in sx.children(tree, 'symbol'):
            ref = sx.prop(symbol, 'Reference')
            if ref in VALUES:
                values.add(ref)
                for field, val in zip(('Value', 'MPN', 'Manufacturer'), VALUES[ref]):
                    set_property(symbol, field, val)
                if ref == 'R107':
                    set_property(symbol, 'ReviewNote', VALUES[ref][1])
            for terminal, (old, new) in CHANGED.items():
                owner, pin = terminal.split('.')
                if ref == owner:
                    change_terminal(tree, symbol, ref, pin, old, new)
                    changes.add(terminal)
        trees[path.name] = tree
    assert len(trees) == 6 and changes == set(CHANGED) and values == set(VALUES)
    return trees


def passive_footprint(ref, value):
    if ref.startswith('R'):
        return ('Resistor_SMD:R_0603_1608Metric' if '0603' in value else 'Resistor_SMD:R_0402_1005Metric')
    return {
        'C153': 'Capacitor_SMD:C_0603_1608Metric', 'C154': 'Capacitor_SMD:C_0805_2012Metric',
        'C165': 'Capacitor_SMD:C_0603_1608Metric', 'C166': 'Capacitor_SMD:C_0603_1608Metric',
    }.get(ref, 'Capacitor_SMD:C_0402_1005Metric')


def add_new_part(sheet, reference, item, point):
    pins = list(item['pins'].items())
    left, right = [], []
    # Arrange functional inputs and outputs first. Split the large MCU at a
    # predictable package-pin boundary so pin review is straightforward.
    for i, (number, (name, _net, kind)) in enumerate(pins):
        (left if i < (len(pins) + 1) // 2 else right).append((number, name, kind))
    lib = reference + '_' + item['mpn'].replace('-', '_').replace(',', '_')
    g.ic(lib, left, right, item['source'], 'Manufacturer package pin map')
    nets = {str(n): data[1] for n, data in pins}
    fp = 'WiredMain:' + item['footprint'].split(':')[1]
    sheet.part(lib, reference, item['mpn'], *point, nets, fp, domain='MAIN_T')
    return fp


def capture_host():
    g.LIB.clear()
    g.PARTS.clear()
    g.OUT, g.NS, g.PROJECT = HERE / 'sheets', NS, PROJECT
    g.passive('R', 'R')
    g.passive('C', 'C')
    g.ic('ServicePad', [(1, 'Pad', 'passive')], [], '', 'Exposed copper service pad')
    names = {'wired-usb-data': 'USB mux, PC recovery and rail qualification',
             'wired-usb-host': 'RP2040 host, flash, clock and service',
             'wired-usb-passives': 'Local supply decoupling and signal defaults'}
    sheets = {name: g.Sheet(name, title) for name, title in names.items()}
    for sheet in sheets.values():
        sheet.paper = 'A2'
    ctrl, host, passives = sheets.values()
    ctrl.note('PC is the default after Main power qualifies. Short PC LOCK to GND for recovery.\nUSB_HOST_5V is current-limited from HOST_5V; CONTACT_5V remains independent.', 25.4, 12.7, 1.27)
    host.note('Native USB host and separate point-to-point I2C. Keep the XOSC circuit and USB series resistors close to U160.\nService pads require fixture access. Provide each marked capacitor near its specified supply pin.', 25.4, 12.7, 1.27)
    passives.note('The host is off with USB100. Place capacitors by the pin listed in the contract.\nThe PC path remains selected while local power is valid and the host is idle.', 25.4, 12.7, 1.27)
    footprints = {}
    locations = {'U151': (91.44, 60.96), 'U152': (223.52, 60.96), 'U153': (355.6, 60.96),
                 'U154': (487.68, 60.96), 'U155': (91.44, 137.16), 'U156': (223.52, 137.16),
                 'U157': (355.6, 137.16), 'U158': (487.68, 137.16), 'U159': (91.44, 215.9),
                 'U162': (223.52, 215.9), 'U163': (355.6, 215.9)}
    for ref, point in locations.items():
        footprints[ref] = add_new_part(ctrl, ref, DEVICES[ref], point)
    for ref, point in {'U160': (114.3, 165.1), 'U161': (279.4, 93.98), 'Y151': (279.4, 154.94)}.items():
        footprints[ref] = add_new_part(host, ref, DEVICES[ref], point)
    for i, (ref, net) in enumerate(TESTPOINTS.items()):
        footprints[ref] = 'WiredMain:TestPoint_Pad_D1.5mm'
        host.part('ServicePad', ref, net, 431.8, 60.96 + 30.48 * i, {'1': net}, footprints[ref], domain='MAIN_T')
    for i, (ref, spec) in enumerate(PASSIVES.items()):
        value, net1, net2, *placement = spec
        footprint = passive_footprint(ref, value)
        footprints[ref] = 'WiredMain:' + footprint.split(':')[1]
        x, y = 58.42 + 86.36 * (i % 6), 48.26 + 40.64 * (i // 6)
        passives.part(ref[0], ref, value, x, y, {'1': net1, '2': net2}, footprints[ref],
                      note=('Place at ' + placement[0]) if placement else '', domain='MAIN_T')
    for sheet in sheets.values():
        sheet.save()
    lib = sx.parse('(kicad_symbol_lib (version 20220914) (generator wired_main_builder))')
    lib.extend(sx.parse(g.LIB[name]['text']) for name in sorted(g.LIB))
    sx.write(HERE / 'WiredMain.kicad_sym', lib)
    trees = {}
    for name in names:
        path = HERE / 'sheets' / (name + '.kicad_sch')
        tree = sx.parse(path.read_text().replace('PrototypeR0:', 'WiredMain:'))
        for symbol in sx.children(tree, 'symbol'):
            ref = sx.prop(symbol, 'Reference')
            item = DEVICES.get(ref)
            if item:
                set_property(symbol, 'MPN', item['mpn'])
                set_property(symbol, 'Manufacturer', item['manufacturer'])
            elif ref in TESTPOINTS:
                set_property(symbol, 'Manufacturer', 'manual copper')
            else:
                set_property(symbol, 'OrderingStatus', 'Passive MPN selection pending')
        trees[path.name] = tree
    return trees, footprints


def install_libraries(stock):
    copied = {}
    local = HERE / 'WiredMain.pretty'
    local.mkdir(exist_ok=True)
    for library, name in sorted({tuple(item['footprint'].split(':')) for item in DEVICES.values()} |
                                {tuple(passive_footprint(ref, spec[0]).split(':')) for ref, spec in PASSIVES.items()} |
                                {('TestPoint', 'TestPoint_Pad_D1.5mm')}):
        if library == 'WiredMain':
            local_footprint = local / (name + '.kicad_mod')
            copied[local_footprint.name] = {'source_library': library, 'sha256': digest(local_footprint)}
            continue
        source = (EVT / 'case-telemetry-study/case-radio/Radio.pretty' if library == 'Radio'
                  else stock / (library + '.pretty')) / (name + '.kicad_mod')
        destination = local / source.name
        destination.write_bytes(source.read_bytes())
        copied[destination.name] = {'source_library': library, 'sha256': digest(source)}
    for table, alias in (('sym-lib-table', 'WiredMain.kicad_sym'), ('fp-lib-table', 'WiredMain.pretty')):
        if table == 'fp-lib-table' and (HERE / (PROJECT + '.kicad_pcb')).exists():
            continue  # The active layout uses the footprint revisions in its project library table.
        tree = sx.parse((SOURCE / table).read_text())
        for lib in sx.children(tree, 'lib'):
            uri = sx.child(lib, 'uri')
            path = Path(uri[1].value.replace('${KIPRJMOD}', str(SOURCE))).resolve()
            assert path.exists()
            uri[1] = sx.string('${KIPRJMOD}/' + os.path.relpath(path, HERE))
        tree.append(sx.parse(f'(lib (name "WiredMain") (type "KiCad") (uri "${{KIPRJMOD}}/{alias}") '
                             '(options "") (descr "Wired host circuit candidate"))'))
        sx.write(HERE / table, tree)
    return copied


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stock-footprints', type=Path, required=True)
    args = parser.parse_args()
    inputs = [*sorted((SOURCE / 'sheets').glob('*.kicad_sch')), SOURCE / 'native.xml',
              SOURCE / 'sym-lib-table', SOURCE / 'fp-lib-table', SOURCE / 'erc.json',
              SOURCE / (SOURCE.name + '.kicad_pro'), ROOT / 'tools/electronics_r0_generate.py',
              ROOT / 'tools/kicad_sexp.py',
              HERE / 'contract.py', HERE / 'circuit-contract.json',
              *(HERE / 'WiredMain.pretty' / (item['footprint'].split(':')[1] + '.kicad_mod')
                for item in DEVICES.values() if item['footprint'].startswith('WiredMain:'))]
    before = {str(path.relative_to(ROOT)): digest(path) for path in inputs}
    (HERE / 'sheets').mkdir(exist_ok=True)
    context = capture_context()
    host, footprints = capture_host()
    library_sources = install_libraries(args.stock_footprints)
    sheets = context | host
    for name, tree in sheets.items():
        add_instances(tree, name)
        sx.write(HERE / 'sheets' / name, tree)
    write_root(PROJECT, sheets, 'Wired USB dock / Main PCB')
    write_root(TRANSPORT, sheets, 'Wired USB dock / integrated EVT circuit')
    settings = json.loads((SOURCE / (SOURCE.name + '.kicad_pro')).read_text())
    transport_settings = settings | {'meta': settings['meta'] | {'filename': TRANSPORT + '.kicad_pro'}}
    (HERE / (TRANSPORT + '.kicad_pro')).write_text(json.dumps(transport_settings, indent=2) + '\n')
    project_file = HERE / (PROJECT + '.kicad_pro')
    if (HERE / (PROJECT + '.kicad_pcb')).exists():
        # The active PCB and schematic share the project. Preserve its layout rules.
        settings = json.loads(project_file.read_text()) | {'erc': settings['erc']}
    settings['meta']['filename'] = PROJECT + '.kicad_pro'
    project_file.write_text(json.dumps(settings, indent=2) + '\n')
    assert before == {str(path.relative_to(ROOT)): digest(path) for path in inputs}
    manifest = {'inputs_sha256': before, 'builder_sha256': digest(Path(__file__)),
                'local_footprint_sources': library_sources, 'new_reference_footprints': footprints,
                'copied_context_leaves': list(context), 'new_leaves': list(host),
                'main_schematic': PROJECT + '.kicad_sch', 'transport_schematic': TRANSPORT + '.kicad_sch',
                'off_main_board_leaves': sorted(REMOTE_BOARD_SHEETS),
                'declared_terminal_changes': CHANGED, 'declared_resistor_changes': VALUES}
    (HERE / 'source-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'Saved {len(context)} retained leaves and {len(host)} new wired host leaves.')


if __name__ == '__main__':
    main()
