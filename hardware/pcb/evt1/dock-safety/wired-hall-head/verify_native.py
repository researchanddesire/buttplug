"""Run native KiCad 10.0.8 electrical and source-parity checks on the Hall head."""
import argparse
from collections import Counter, defaultdict
import hashlib
import heapq
import json
import math
from pathlib import Path
import subprocess
import tempfile
from xml.etree import ElementTree

import pcbnew

HERE = Path(__file__).resolve().parent
STEM = 'wired-hall-head'


def front_track_dist(board, net, start, stop):
    graph = defaultdict(list)
    for item in board.GetTracks():
        if isinstance(item, pcbnew.PCB_VIA) or item.GetLayer() != pcbnew.F_Cu or item.GetNetname() != net:
            continue
        left, right = item.GetStart(), item.GetEnd()
        a, b = (left.x, left.y), (right.x, right.y)
        length = math.dist(a, b)
        graph[a].append((length, b))
        graph[b].append((length, a))
    queue = [(0, (start.x, start.y))]
    seen = set()
    target = (stop.x, stop.y)
    while queue:
        total, point = heapq.heappop(queue)
        if point == target:
            return round(total / pcbnew.FromMM(1), 3)
        if point not in seen:
            seen.add(point)
            for length, destination in graph[point]:
                heapq.heappush(queue, (total + length, destination))
    raise AssertionError(f'No front copper path between the Hall and bypass capacitor on {net}')


def inspect(cli, output):
    assert pcbnew.GetBuildVersion() == '10.0.8'
    assert subprocess.check_output([cli, '--version'], text=True).strip() == '10.0.8'
    with tempfile.TemporaryDirectory() as scratch:
        paths = {name: Path(scratch, name) for name in ('erc.json', 'drc.json', 'native.xml')}
        for args, result, kind in (
            (['sch', 'erc', '--format', 'json'], 'erc.json', 'sch'),
            (['sch', 'export', 'netlist', '--format', 'kicadxml'], 'native.xml', 'sch'),
            (['pcb', 'drc', '--schematic-parity', '--format', 'json'], 'drc.json', 'pcb'),
        ):
            subprocess.run([cli, *args, '-o', str(paths[result]), f'{STEM}.kicad_{kind}'],
                           cwd=HERE, check=True, capture_output=True, text=True)
        erc = json.loads(paths['erc.json'].read_text())
        drc = json.loads(paths['drc.json'].read_text())
        xml = ElementTree.parse(paths['native.xml'])
        if output:
            for name, path in paths.items():
                (HERE / name).write_bytes(path.read_bytes())

    parts = json.loads((HERE / 'parts-selection.json').read_text())['parts']
    expected = {(part['reference'], pin): net for part in parts for pin, net in part['pins'].items()}
    native = {(node.get('ref'), node.get('pin')): net.get('name')
              for net in xml.findall('./nets/net') for node in net.findall('node') if not node.get('ref').startswith('#')}
    board = pcbnew.LoadBoard(str(HERE / f'{STEM}.kicad_pcb'))
    actual = {}
    positions = {}
    footprints = {}
    for footprint in board.GetFootprints():
        footprints[footprint.GetReference()] = footprint
        for pad in footprint.Pads():
            key = (footprint.GetReference(), pad.GetNumber())
            assert key not in actual, key
            actual[key] = pad.GetNetname()
            positions[key] = pad.GetPosition()
    assert len(expected) == 39
    assert actual == native
    assert {k: (None if v.startswith('unconnected-') else v) for k, v in native.items()} == expected
    assert {p for p, n in actual.items() if n == 'SIG'} == {('J1', '2'), ('R5', '1')}
    assert {p for p, n in actual.items() if n == 'SINK_DRAIN'} == {('R5', '2'), ('Q1', '3')}
    for part in parts:
        ref = part['reference']
        component = xml.find(f'./components/comp[@ref="{ref}"]')
        native_value = component.findtext('value')
        native_mpn = component.find('./fields/field[@name="MPN"]').text
        assert (native_value, native_mpn) == (part['value'], part['mpn']), ref
        footprint = footprints[ref]
        assert footprint.GetValue() == part['value'], ref
        assert footprint.GetField('MPN').GetText() == part['mpn'], ref
    assert not any(sheet['violations'] for sheet in erc['sheets'])
    assert not drc['schematic_parity']
    bypass_mm = {
        'supply': front_track_dist(board, 'HEAD_FEED', positions['U1', '1'], positions['C1', '1']),
        'return': front_track_dist(board, 'GND', positions['U1', '3'], positions['C1', '2']),
    }
    source_files = [HERE / f'{STEM}.kicad_{extension}' for extension in ('sch', 'pcb', 'pro')]
    source_files.extend(HERE / name for name in (
        'parts-selection.json', 'routing.json', 'WiredHallHead.kicad_sym', 'fp-lib-table', 'sym-lib-table',
        'build_board.py', 'build_head.py',
    ))
    source_files.extend(sorted((HERE / 'WiredHallHead.pretty').glob('*.kicad_mod')))
    result = {'tool': 'KiCad 10.0.8', 'terminals': len(actual), 'erc': 0, 'schematic_parity': 0,
              'opens': len(drc['unconnected_items']),
              'drc': dict(Counter(item['type'] for item in drc['violations'])),
              'hall_front_copper_bypass_mm': bypass_mm,
              'source_sha256': {p.relative_to(HERE).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                for p in source_files}}
    if output:
        (HERE / 'native-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kicad-cli', default='kicad-cli')
    parser.add_argument('--save', action='store_true')
    parser.add_argument('--require-clean', action='store_true')
    args = parser.parse_args()
    summary = inspect(args.kicad_cli, args.save)
    if args.require_clean and (summary['opens'] or summary['drc']):
        raise SystemExit(1)
