"""Repackage unchanged 4.22-ohm UV artwork against the wired Main netlist."""

import argparse
import importlib.util
import io
import json
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

HERE = Path(__file__).resolve().parent
WIRED = HERE.parent
ARCHIVED = WIRED.parents[1] / 'case-radio-uv'
ROOT = WIRED.parents[4]
SOURCE = ARCHIVED / 'build_quotes.py'
spec = importlib.util.spec_from_file_location('uv_quote_common', SOURCE)
uv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(uv)

SENSE_VALUE = '4.22ohm1%100ppm'
NATIVE_SENSE_VALUE = '4.22ohm 1% 100ppm/K'
SENSE_MPN = 'CRCW08054R22FKEA'
MAIN_MPN = 'RT0603BRD0740K2L'
MAIN_VALUE = '40.2k 0.1% 25ppm/K'


def field(part, name):
    return part.findtext(f"./fields/field[@name='{name}']")


def firmware_contract(firmware):
    args = ['make', '-C', str(firmware), '--no-print-directory', '-Bn', 'all']
    profiles = {'wired': ['-DDOCK_WIRED_MAIN', '-DDOCK_UV_SENSE_MILLIOHM=4220u'],
                'direct': []}
    for profile, expected in profiles.items():
        make = subprocess.run([*args, f'PROFILE={profile}'], text=True, check=True, capture_output=True)
        commands = [line.split() for line in make.stdout.splitlines() if ' -c src/dock_app.c ' in line]
        assert len(commands) == 1, (profile, commands)
        assert [word for word in commands[0] if word.startswith(('-DDOCK_WIRED_MAIN', '-DDOCK_UV_SENSE_MILLIOHM'))] == expected
    header = (firmware / 'include/dock_app.h').read_text()
    source = (firmware / 'src/dock_app.c').read_text()
    assert re.search(r'#define DOCK_UV_SENSE_MILLIOHM 3650u\b', header)
    assert re.search(r'\badc\s*\*\s*15625u\s*/\s*DOCK_UV_SENSE_MILLIOHM\b', source)
    return {'command': 'make -C dock-firmware PROFILE=wired', 'sense_milliohm': 4220,
            'fallback_direct_profile_milliohm': 3650, 'compile_flags_replayed': True}


def quote_readme(side, ref):
    return f"""# Wired Main UV {side} board engineering quote

Fit **{ref} = 4.22 Ω**, Vishay **{SENSE_MPN}**, 0805, ±1%, ±100 ppm/K.
This assembly pairs with wired Main **R107 = 40.2 kΩ**, Yageo
**{MAIN_MPN}**, and the STM32 build from
`make -C dock-firmware PROFILE=wired` using **4220 mΩ**.
Confirm the population on Main, base and lid together before applying power.

Quote a 1.00 mm two-layer copper-plus-core board with 0.86 mm FR4, 70 µm
finished outer copper each side, ENIG and nominal 10 µm solder mask per face.
Preserve the Ø2.2 mm nonplated mounts, 1 mm minimum inside milling radius,
0.20 mm trace/clearance and Ø0.60/0.30 mm vias. Confirm stack and process.

Use the 20-position purchase and placement tables. The four test points are
copper-only. Quote the two remote thermal parts separately from PCB placement.
LED pad 1 is cathode. Confirm the bottom-side rotations with the assembler.

The fabrication files are identical to the previously routed UV artwork.
Supplier review and pricing are the scope of this packet. Installed source,
current limits, thermal cutoff, optical leakage and cleaning checks are pending.
""".encode()


def build_side(side, cli, native, bindings, check):
    ref = {'base': 'R401', 'lid': 'R501'}[side]
    archived = ARCHIVED / side
    package = archived / f'case-radio-uv-{side}-supplier-quote.zip'
    board = archived / 'pcb' / f'dock-uv-{side}.kicad_pcb'
    project = board.with_suffix('.kicad_pro')
    archive_bytes = bindings(package)
    with ZipFile(io.BytesIO(archive_bytes)) as archive:
        source_manifest = json.loads(archive.read('manifest.json'))
        files = {name: archive.read(name) for name in source_manifest['files_sha256']}
        assert set(archive.namelist()) == set(files) | {'manifest.json'} and archive.testzip() is None
    assert all(uv.sha(data) == source_manifest['files_sha256'][name] for name, data in files.items())
    pcb_data = bindings(board)
    assert uv.sha(pcb_data) == source_manifest['board_sha256']
    assert not json.loads(bindings(project))['board']['design_settings']['drc_exclusions']
    original = uv.ORIGINAL / side / 'pcb' / 'fabrication-review' / f'uv-{side}-supplier-review.zip'
    with ZipFile(io.BytesIO(bindings(original))) as archive:
        fab_names = source_manifest['fabrication_files_identical']
        assert len(fab_names) == 13
        assert all(files[name] == archive.read(name) for name in fab_names)

    native_part = native.find(f"./components/comp[@ref='{ref}']")
    assert native_part.findtext('value') == NATIVE_SENSE_VALUE and field(native_part, 'MPN') == SENSE_MPN
    # Keep the compact stored PCB/position value while retaining the exact ordered part.
    native_part.find('value').text = SENSE_VALUE
    files['onboard-selected-parts.csv'] = uv.update_csv(files['onboard-selected-parts.csv'], ref, 'Reference', {
        'AssemblyNote': 'Wired Main UV population, 4.22 ohm sense resistor.'})
    purchased = uv.csv_rows(files['purchased-positions.csv'])
    all_positions = uv.csv_rows(files['native-all-positions.csv'])
    part_rows = uv.csv_rows(files['onboard-selected-parts.csv'])
    for rows in (purchased, all_positions):
        assert len([row for row in rows if row['Ref'] == ref and row['Val'] == SENSE_VALUE]) == 1
    assert len(purchased) == len(part_rows) == 20
    assert {row['Ref'] for row in purchased} == {row['Reference'] for row in part_rows}
    assert {row['Ref']: row for row in all_positions} == {row['Ref']: row for row in purchased}
    remote = uv.csv_rows(files['remote-thermal-parts.csv'])
    parity = uv.audit_radio_parity(uv.sx.parse(pcb_data.decode()), part_rows, remote, native)
    assert sum(map(len, parity.values())) == 61

    drc_path = archived / 'pcb' / 'native-drc.json'
    saved = json.loads(bindings(drc_path))
    assert files['checks/native-drc.json'] == drc_path.read_bytes()
    with TemporaryDirectory(prefix='wired-uv-drc-') as tmp:
        fresh = uv.drc(cli, board, Path(tmp) / 'result.json')
    assert {k: v for k, v in fresh.items() if k != 'date'} == {k: v for k, v in saved.items() if k != 'date'}
    files.pop('checks/radio-pad-net-parity.json')
    files['checks/wired-pad-net-parity.json'] = uv.json_bytes(parity)
    files['README.md'] = quote_readme(side, ref)
    assert all(b'radio' not in data.lower() for name, data in files.items() if name.endswith(('.md', '.csv')))

    report = {
        'scope': f'Wired Main UV {side} engineering quote', 'board_sha256': uv.sha(pcb_data),
        'wired_native_netlist_sha256': uv.sha((WIRED / 'native.xml').read_bytes()),
        'coupled_configuration': {
            'Main_R107': {'resistance_ohm': 40200, 'mpn': MAIN_MPN},
            'UV_R401_R501': {'resistance_ohm': 4.22, 'mpn': SENSE_MPN},
            'firmware_profile': 'wired', 'sense_milliohm': 4220},
        'populated_sense_reference': ref, 'purchased_placements': len(purchased), 'remote_parts': len(remote),
        'physical_pads_checked': 61, 'native_drc_errors': len(fresh['violations']),
        'native_drc_unconnected': len(fresh['unconnected_items']),
        'inherited_DRC_ignored_checks': [rule['key'] for rule in fresh['ignored_checks']],
        'identical_fabrication_files': fab_names, 'files_sha256': {name: uv.sha(data) for name, data in sorted(files.items())},
        'supplier_acceptance': False, 'powered_validation': False,
    }
    files['manifest.json'] = uv.json_bytes(report)
    buffer = io.BytesIO()
    with ZipFile(buffer, 'w') as archive:
        for name, data in sorted(files.items()):
            archive.writestr(ZipInfo(name), data, compress_type=ZIP_DEFLATED)
    zip_data = buffer.getvalue()
    with ZipFile(io.BytesIO(zip_data)) as archive:
        assert archive.testzip() is None and all(archive.read(name) == data for name, data in files.items())
    target = HERE / f'wired-main-uv-{side}-supplier-quote.zip'
    uv.write_or_check(target, zip_data, check)
    return {**report, 'quote_sha256': uv.sha(zip_data)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kicad-cli', required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    version = subprocess.check_output([args.kicad_cli, 'version'], text=True).strip()
    assert version == '10.0.8', version
    hashes = {}

    def bind(path):
        data = path.read_bytes()
        hashes[path.relative_to(ROOT).as_posix()] = uv.sha(data)
        return data

    native_data = bind(WIRED / 'native.xml')
    native_check = json.loads(bind(WIRED / 'native-checks.json'))
    power = json.loads(bind(WIRED / 'circuit-contract.json'))['power']['wired_coexistence']
    assert native_check['native_report_hashes']['native.xml'] == uv.sha(native_data)
    assert native_check['ERC_errors'] == native_check['ERC_warnings'] == 0
    assert (power['R107_kohm'], power['R107_mpn'], power['R401_R501_ohm_each'],
            power['R401_R501_mpn']) == (40.2, MAIN_MPN, 4.22, SENSE_MPN)
    native = ET.fromstring(native_data)
    main_part = native.find("./components/comp[@ref='R107']")
    assert main_part.findtext('value') == MAIN_VALUE and field(main_part, 'MPN') == MAIN_MPN
    firmware = ROOT / 'dock-firmware'
    for source in (SOURCE, Path(__file__), firmware / 'Makefile', firmware / 'include/dock_app.h', firmware / 'src/dock_app.c'):
        bind(source)
    runtime = firmware_contract(firmware)
    boards = {side: build_side(side, args.kicad_cli, native, bind, args.check) for side in ('base', 'lid')}
    report = {'native_KiCad': version, 'sources_sha256': dict(sorted(hashes.items())),
              'runtime': runtime, 'boards': boards, 'full_product_order_ready': False}
    uv.write_or_check(HERE / 'native-checks.json', uv.json_bytes(report), args.check)
    print('Two wired UV quote archives verified: 61 pads per board, DRC 0/0, all 13 fabrication files identical per board.')


if __name__ == '__main__':
    main()
