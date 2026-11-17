"""Read back and adopt a checked routing checkpoint into the EVT Main project."""

import argparse
from collections import Counter
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
from uuid import NAMESPACE_URL, uuid5
from xml.etree import ElementTree as ET

HERE = Path(__file__).resolve().parent
LAYOUT = HERE / 'layout-candidate'
CHECKPOINT_NAME = 'dock-main-wired'
PROJECT = 'dock-wired-system'


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def load_helper():
    spec = importlib.util.spec_from_file_location('clock', LAYOUT/'host-clock-detours/replay.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return helper


def sync_board_metadata(board, k, transport_xml):
    """Copy published symbol fields without changing tracks, pads or placement."""
    components = {comp.get('ref'): comp for comp in ET.parse(transport_xml).findall('components/comp')}
    mechanical_holes = {f'H{number}' for number in range(701, 707)}
    for footprint in board.GetFootprints():
        ref = footprint.GetReference()
        if ref in mechanical_holes:
            assert ref not in components and all(not pad.GetNumber() for pad in footprint.Pads())
            footprint.SetBoardOnly()
            continue
        component = components[ref]
        assert component.findtext('footprint'), ref
        assert footprint.IsExcludedFromBOM() == (component.find("property[@name='exclude_from_bom']") is not None), ref
        for item in component.findall('fields/field'):
            name = item.get('name')
            if name in {'Footprint', 'Description', 'Reference', 'Value'}:
                continue
            if footprint.HasField(name):
                field = footprint.GetField(name)
            else:
                field = k.PCB_FIELD(footprint, k.FIELD_T_USER, name)
                field.SetUuid(k.KIID(str(uuid5(NAMESPACE_URL, f'compass/wired-main/{ref}/{name}'))))
                field.SetLayer(k.B_Fab if footprint.IsFlipped() else k.F_Fab)
                field.SetPosition(footprint.GetPosition())
                field.SetTextSize(k.VECTOR2I(k.FromMM(1), k.FromMM(1)))
                field.SetTextThickness(k.FromMM(.15))
                field.SetVisible(False)
                footprint.Add(field)
            field.SetText(item.text or '')


def verify_and_write(checkpoint, output, cli, overlay_path=None):
    helper = load_helper()
    remote, combined, k = helper.remote, helper.combined, helper.k
    assert k.GetBuildVersion() == subprocess.check_output([cli, 'version'], text=True).strip() == '10.0.8'
    inputs = json.loads((checkpoint/'native-checks.json').read_text())
    origin = checkpoint / f'{CHECKPOINT_NAME}.kicad_pcb'
    assert digest(origin) == inputs['trial_board_sha256']
    drc_origin = checkpoint/'drc.json'
    assert digest(drc_origin) == inputs['trial_DRC_sha256']
    recorded_drc = json.loads(drc_origin.read_text())
    assert not recorded_drc['violations']

    output.mkdir(parents=True, exist_ok=True)
    path = output / f'{PROJECT}.kicad_pcb'
    assert not path.exists(), 'Use an empty staging directory'
    rules = (checkpoint/f'{CHECKPOINT_NAME}.kicad_dru').read_bytes()
    (output/f'{PROJECT}.kicad_dru').write_bytes(rules)
    settings = json.loads((checkpoint/f'{CHECKPOINT_NAME}.kicad_pro').read_text())
    schematic_settings = json.loads((HERE/f'{PROJECT}.kicad_pro').read_text())
    settings['meta']['filename'] = PROJECT + '.kicad_pro'
    settings['erc'] = schematic_settings['erc']
    (output/f'{PROJECT}.kicad_pro').write_text(json.dumps(settings, indent=2)+'\n')
    def footprint_uri(match):
        source = (checkpoint/match[1]).resolve()
        assert source.is_dir(), source
        if source.name == 'DockControl.pretty':
            source = HERE/'DockControl.pretty'
            assert source.is_dir(), source
        return '${KIPRJMOD}/' + os.path.relpath(source, output)

    libraries = (checkpoint/'fp-lib-table').read_text()
    libraries = re.sub(r'\$\{KIPRJMOD\}/([^\"]+)', footprint_uri, libraries)
    uv_path = os.path.relpath(HERE.parents[1]/'dock-uv/base/DockUV.pretty', output)
    uv_row = f' (lib (name "DockUV") (type "KiCad") (uri "${{KIPRJMOD}}/{uv_path}") (options "") (descr "UV board footprint library"))'
    (output/'fp-lib-table').write_text(libraries.rstrip()[:-1] + uv_row + '\n)\n')

    source_board = k.LoadBoard(str(origin))
    source_pads, source_routes = combined.flash.snapshot(source_board)
    source_plane = helper.study.plane(source_board)
    placements = combined.placement(source_board)
    zone_options = combined.zone_options(source_board)
    outline = remote.outline(source_board)
    removed = {}
    added_rows = []
    expected_opens = helper.study.ground.limiter.open_nets(recorded_drc)
    if overlay_path:
        overlay = json.loads(overlay_path.read_text())
        assert overlay['source_board_sha256'] == digest(origin)
        removed = overlay['remove']
        for track in list(source_board.GetTracks()):
            key = remote.track_key(track)
            if key in removed:
                assert track.GetNetname() == removed[key] and not track.IsLocked()
                source_board.Delete(track)
        assert set(removed) <= set(source_routes)
        added_rows = overlay['routes']
        audited_inner = overlay.get('audited_In1_signal_routes', [])
        assert [row for row in added_rows if row.get('layer') == 'In1.Cu'] == audited_inner
        for row in added_rows:
            remote.add_route(source_board, row)
        expected_opens.subtract(overlay['closed_opens_by_net'])
        expected_opens = +expected_opens
    netlist_path = HERE / 'native.xml'
    sync_board_metadata(source_board, k, netlist_path)
    for footprint in source_board.GetFootprints():
        remote.rebase_models(footprint, checkpoint, output)
    assert k.SaveBoard(str(path), source_board, True)
    report_file = output/'active-routing-drc.json'
    if overlay_path:
        subprocess.run([cli, 'pcb', 'drc', '--refill-zones', '--save-board', '--format', 'json',
                        '-o', str(report_file), str(path)], check=True)
    board_hash = digest(path)
    subprocess.run([cli, 'pcb', 'drc', '--format', 'json', '-o', str(report_file), str(path)], check=True)
    assert digest(path) == board_hash
    report = json.loads(report_file.read_text())
    open_nets = helper.study.ground.limiter.open_nets
    assert not report['violations'] and open_nets(report) == expected_opens
    assert len(report['unconnected_items']) == sum(expected_opens.values())

    board = k.LoadBoard(str(path))
    board_pads, board_routes = combined.flash.snapshot(board)
    assert board_pads == source_pads
    kept = {key: row for key, row in source_routes.items() if key not in removed}
    assert {key: board_routes[key] for key in kept} == kept
    assert not set(removed) & set(board_routes)
    new_routes = [track for track in board.GetTracks() if remote.track_key(track) not in kept]
    assert Counter(map(combined.copper_shape, new_routes)) == combined.copper_rows(added_rows)
    assert combined.placement(board) == placements and remote.outline(board) == outline
    assert combined.zone_options(board) == zone_options
    plane = helper.study.plane(board)  # Also verifies a continuous single ground outline.
    if not overlay_path:
        assert plane == source_plane

    nets = {(node.get('ref'), node.get('pin')): net.get('name').lstrip('/')
            for net in ET.parse(netlist_path).findall('nets/net') for node in net.iterfind('node')}
    terminals = set()
    physical_pads = 0
    models = 0
    for footprint in board.GetFootprints():
        for model in footprint.Models():
            uri = model.m_Filename
            assert uri.startswith('${KIPRJMOD}/') and (output/uri.split('/',1)[1]).is_file(), uri
            models += 1
        for pad in footprint.Pads():
            if not pad.GetNumber():
                continue
            key = (footprint.GetReference(), pad.GetNumber())
            pcb_net = pad.GetNetname().lstrip('/')
            assert nets.get(key) == pcb_net, (key, nets.get(key), pcb_net)
            terminals.add(key)
            physical_pads += 1
    assert len(terminals) == len(source_pads) == 799 and models == 200
    summary = {'board_sha256': digest(path), 'checkpoint_board_sha256': digest(origin),
               'checkpoint': checkpoint.relative_to(HERE).as_posix(),
               'native_KiCad': k.GetBuildVersion(), 'native_xml_sha256': digest(netlist_path),
               'drc_sha256': digest(report_file), 'violations': 0,
               'remaining_opens': len(report['unconnected_items']),
               'open_counts_by_net': dict(sorted(open_nets(report).items())),
               'unchanged_copper_objects': len(kept), 'added_copper_objects': len(new_routes),
               'removed_copper_objects': len(removed), 'native_terminal_net_checks': len(terminals),
               'native_physical_numbered_pads': physical_pads,
               'resolved_relative_models': models, 'In1_GND_fill_sha256': plane,
               'fabrication_ready': False}
    if overlay_path:
        summary['route_overlay_sha256'] = digest(overlay_path)
    (output/'active-routing.json').write_text(json.dumps(summary, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkpoint', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--kicad-cli', required=True)
    parser.add_argument('--overlay', type=Path)
    args = parser.parse_args()
    verify_and_write(args.checkpoint.resolve(), args.out.resolve(), args.kicad_cli, args.overlay)
