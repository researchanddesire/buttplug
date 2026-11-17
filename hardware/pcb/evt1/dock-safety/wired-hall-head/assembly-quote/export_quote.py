"""Export and independently reconcile the native Hall-head PCB supplier quote."""
import argparse
from collections import Counter, defaultdict
import csv
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile

OUT = Path(__file__).resolve().parent
HEAD = OUT.parent
sys.path.insert(0, str(HEAD.parents[4] / 'tools'))
from kicad_sexp import child, children, parse, prop, value

STEM = 'wired-hall-head'
BOARD = HEAD / f'{STEM}.kicad_pcb'
VERSION = '10.0.8'
QUANTITY = 2
LAYERS = 'F.Cu,B.Cu,F.Mask,B.Mask,F.Paste,F.SilkS,Edge.Cuts'
GERBERS = ('F_Cu.gtl', 'B_Cu.gbl', 'F_Mask.gts', 'B_Mask.gbs', 'F_Paste.gtp',
           'F_Silkscreen.gto', 'Edge_Cuts.gm1')
FAB = [f'{STEM}-{suffix}' for suffix in (*GERBERS, 'job.gbrjob', 'PTH.drl', 'NPTH.drl')]
FAB += [f'{STEM}.d356', 'drill-report.txt', 'fabrication-request.json']
RAW_POSITIONS = f'{STEM}-native-all-positions.csv'
POSITIONS = f'{STEM}-purchased-positions.csv'
BOM = f'{STEM}-assembly-parts.csv'
COPPER = f'{STEM}-copper-only.csv'


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text())


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def write_csv(path, columns, rows):
    with path.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(rows)


def export(cli, work):
    def run(*args):
        subprocess.run([cli, *map(str, args)], cwd=HEAD, check=True, capture_output=True, text=True)

    assert subprocess.check_output([cli, '--version'], text=True).strip() == VERSION
    run('pcb', 'drc', '--schematic-parity', '--severity-all', '--exit-code-violations',
        '--format', 'json', '-o', work / 'drc.json', BOARD)
    run('sch', 'erc', '--severity-all', '--exit-code-violations', '--format', 'json',
        '-o', work / 'erc.json', BOARD.with_suffix('.kicad_sch'))
    run('pcb', 'export', 'gerbers', '--check-zones', '-o', f'{work}/', '--layers', LAYERS, BOARD)
    run('pcb', 'export', 'drill', '-o', f'{work}/', '--excellon-separate-th',
        '--generate-report', '--report-path', work / 'drill-report.txt', BOARD)
    run('pcb', 'export', 'ipcd356', '-o', work / f'{STEM}.d356', BOARD)
    run('pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both',
        '-o', work / RAW_POSITIONS, BOARD)
    run('pcb', 'export', 'svg', '--mode-single', '--fit-page-to-board', '--exclude-drawing-sheet',
        '--layers', 'F.Fab,Edge.Cuts', '-o', work / 'assembly-front.svg', BOARD)


def verify_fabrication(work, tree, parts, footprints):
    drc = read_json(work / 'drc.json')
    erc = read_json(work / 'erc.json')
    assert drc['kicad_version'] == erc['kicad_version'] == VERSION
    assert not any(drc[key] for key in ('violations', 'unconnected_items', 'schematic_parity'))
    assert not any(sheet['violations'] for sheet in erc['sheets'])

    ipc = (work / f'{STEM}.d356').read_text().splitlines()
    aliases = {line[8:14].strip(): line[14:].strip() for line in ipc if line.startswith('P  NNAME')}
    nets = {}
    for line in ipc:
        if line[:3] not in ('317', '327', '367'):
            continue
        ref, pin, net = line[20:26].strip(), line[27:31].strip(), line[3:17].strip()
        if ref in parts:
            assert (ref, pin) not in nets
            nets[ref, pin] = aliases.get(net, net).upper()
    net_pads = {}
    for ref, fp in footprints.items():
        for pad in children(fp, 'pad'):
            pin, net = pad[1].value, value(pad, 'net')
            expected = parts[ref]['pins'][pin]
            assert net == expected or (expected is None and net.startswith('unconnected-'))
            net_pads[ref, pin] = net.upper()
    assert len(net_pads) == 39 and net_pads == nets

    pth = (work / f'{STEM}-PTH.drl').read_text()
    npth = (work / f'{STEM}-NPTH.drl').read_text()
    assert re.findall(r'^T\d+C([.\d]+)$', pth, re.M) == ['0.300']
    hits = Counter((float(x), float(y)) for x, y in re.findall(r'^X([-\d.]+)Y([-\d.]+)$', pth, re.M))
    vias = children(tree, 'via')
    assert len(vias) == 21
    expected_hits = Counter()
    for via in vias:
        x, y = (float(a.value) for a in child(via, 'at')[1:3])
        assert float(value(via, 'drill')) == .30 and float(value(via, 'size')) == .60
        expected_hits[x, -y] += 1
    assert hits == expected_hits and not re.search(r'^X', npth, re.M)

    job = read_json(work / f'{STEM}-job.gbrjob')['GeneralSpecs']
    assert job['LayerNumber'] == 2 and job['BoardThickness'] == .8
    assert job['Size'] == {'X': 8.85, 'Y': 16.05}  # Includes the 0.05 mm artwork stroke.
    profile = (work / f'{STEM}-Edge_Cuts.gm1').read_text()
    points = {(int(x) / 10**6, -int(y) / 10**6)
              for x, y in re.findall(r'^X(-?\d+)Y(-?\d+)D0[12]\*$', profile, re.M)}
    board_points = {tuple(float(a.value) for a in child(edge, end)[1:3])
                    for edge in children(tree, 'gr_line') for end in ('start', 'end')}
    assert len(points) == 6 and points == board_points
    paste_refs = set(re.findall(r'%TO\.C,([^*]+)\*%', (work / f'{STEM}-F_Paste.gtp').read_text()))
    assert paste_refs == parts.keys() - {'J1'}


def prepare_parts(work, parts, footprints):
    assert {ref for ref, fp in footprints.items()
            if 'exclude_from_bom' in {token.value for token in child(fp, 'attr')[1:]}} == {'J1'}
    assert parts['U1']['mpn'] == 'DRV5021A2QDBZR'
    assert parts['C1']['mpn'] == 'C1005X7R1V224K050BC'
    with (work / RAW_POSITIONS).open(newline='') as stream:
        reader = csv.DictReader(stream)
        native = {row['Ref']: row for row in reader}
        columns = reader.fieldnames
    assert native.keys() == parts.keys() and len(native) == 14
    groups = defaultdict(list)
    positions = []
    for ref in sorted(native.keys() - {'J1'}):
        row, part, fp = native[ref], parts[ref], footprints[ref]
        assert row['Val'] == prop(fp, 'Value') == part['value']
        assert part['mpn'] == prop(fp, 'MPN') and part['manufacturer'] == prop(fp, 'Manufacturer')
        assert row['Package'] == part['footprint'].split(':')[1] and row['Side'] == 'top'
        position = [float(axis.value) for axis in child(fp, 'at')[1:]]
        x, y = position[:2]
        rotation = position[2] if len(position) == 3 else 0
        assert abs(float(row['PosX']) - x) < 1e-5 and abs(float(row['PosY']) + y) < 1e-5
        assert abs((float(row['Rot']) - rotation + 180) % 360 - 180) < 1e-5
        positions.append([row[key] for key in columns])
        groups[part['manufacturer'], part['mpn']].append(ref)
    assert len(positions) == 13 and len(groups) == 11
    write_csv(work / POSITIONS, columns, positions)
    rows = []
    for (manufacturer, mpn), refs in sorted(groups.items()):
        part = parts[refs[0]]
        rows.append((manufacturer, mpn, len(refs), QUANTITY * len(refs), ' '.join(refs),
                     part['value'], part['footprint'], 'SMT', part['primary_source']))
    write_csv(work / BOM, ('Manufacturer', 'MPN', 'Quantity_per_board', 'Quantity_for_two_boards',
                          'References', 'Schematic_value', 'Footprint', 'Assembly_process', 'Manufacturer_source'), rows)
    assert sum(row[3] for row in rows) == 26
    write_csv(work / COPPER, ('Reference', 'Operations', 'Purchased_quantity'),
              [('J1', 'Leave all three wire lands bare for later manual wiring. No connector, paste or machine placement.', 0)])


def package(work, name, entries, details):
    manifest = {'board_sha256': digest(BOARD), 'source': BOARD.name, 'kicad_version': VERSION,
                'quote_only': True, 'physical_validation': False, 'details': details,
                'files': {entry: digest(work / entry) for entry in entries}}
    archive = work / name
    with ZipFile(archive, 'w', compression=ZIP_DEFLATED) as bundle:
        for entry in entries:
            bundle.write(work / entry, entry)
        bundle.writestr('manifest.json', json.dumps(manifest, indent=2) + '\n')
    with ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert set(bundle.namelist()) == set(entries) | {'manifest.json'}
        assert all(sha256(bundle.read(entry)).hexdigest() == hashed for entry, hashed in manifest['files'].items())
    return manifest


def main(cli):
    source = read_json(HEAD / 'native-checks.json')
    assert source['terminals'] == 39 and not any(source[key] for key in ('drc', 'opens', 'erc', 'schematic_parity'))
    assert all(digest(HEAD / name) == hashed for name, hashed in source['source_sha256'].items())
    board_hash = digest(BOARD)
    rules = read_json(BOARD.with_suffix('.kicad_pro'))['board']['design_settings']
    assert rules['rules']['min_track_width'] == .20 and rules['rules']['min_copper_edge_clearance'] == .30
    assert not rules.get('drc_exclusions') and 'ignore' not in rules.get('rule_severities', {}).values()
    tree = parse(BOARD.read_text())
    parts = {p['reference']: p for p in read_json(HEAD / 'parts-selection.json')['parts']}
    footprints = {prop(fp, 'Reference'): fp for fp in children(tree, 'footprint')}
    assert footprints.keys() == parts.keys()
    fab_zip = f'{STEM}-evt1-fabrication-quote.zip'
    smt_zip = f'{STEM}-evt1-assembly-quote.zip'
    fabrication = {'units_requested': QUANTITY, 'material_requested': 'FR-4',
                   'copper_layers': 2, 'finished_thickness_mm': .8, 'routed_size_mm': [8.8, 16.0],
                   'finish_requested': 'ENIG', 'outer_copper_per_side_oz_requested': 1,
                   'minimum_track_mm': .20, 'minimum_copper_to_edge_mm': .30,
                   'plated_vias': 21, 'via_finished_drill_mm': .30, 'via_pad_diameter_mm': .60, 'npth': 0}
    assembly = {'assemblies_requested': QUANTITY, 'smt_positions_per_board': 13, 'unique_purchased_lines': 11,
                'total_placements': 26, 'default_hall': 'DRV5021A2QDBZR',
                'quote_only_alternate': 'DRV5021A3QDBZR', 'manual_land_references': ['J1'],
                'native_checks_sha256': digest(HEAD / 'native-checks.json')}
    with TemporaryDirectory(prefix='compass-hall-rfq-') as tmp:
        work = Path(tmp)
        export(cli, work)
        verify_fabrication(work, tree, parts, footprints)
        prepare_parts(work, parts, footprints)
        for file in (OUT / 'README.md', BOARD):
            (work / file.name).write_bytes(file.read_bytes())
        write_json(work / 'fabrication-request.json', fabrication)
        package(work, fab_zip, FAB, fabrication)
        entries = [fab_zip, 'README.md', BOARD.name, BOM, POSITIONS, COPPER, 'assembly-front.svg']
        manifest = package(work, smt_zip, entries, assembly)
        write_json(work / 'manifest.json', {**manifest, 'assembly_zip_sha256': digest(work / smt_zip)})
        for name in ('manifest.json', 'fabrication-request.json', BOM, POSITIONS, COPPER, 'assembly-front.svg', fab_zip, smt_zip):
            (OUT / name).write_bytes((work / name).read_bytes())
        assert digest(BOARD) == board_hash


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kicad-cli', default='kicad-cli')
    main(parser.parse_args().kicad_cli)
