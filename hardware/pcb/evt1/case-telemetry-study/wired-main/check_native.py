"""Replay native ERC and compare all integrated terminals to the two inputs."""
import argparse
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET

from build_source import PROJECT, REMOTE_BOARD_SHEETS, SERVICE_COPPER, SOURCE, TRANSPORT, VALUES, sx
from contract import HERE, ROOT, digest


def read_netlist(path):
    tree = ET.parse(path)
    parts = {}
    pins = {}
    for comp in tree.findall('./components/comp'):
        ref = comp.get('ref')
        assert ref not in parts
        props = {node.get('name'): node.get('value') for node in comp.findall('property')}
        parts[ref] = (comp.findtext('value'), comp.findtext('footprint'), props.get('MPN'), props.get('Manufacturer'))
    for net in tree.findall('./nets/net'):
        name = net.get('name')
        for node in net.findall('node'):
            key = (node.get('ref'), node.get('pin'))
            assert key not in pins, key
            pins[key] = (None if name.startswith('unconnected-') else name,
                         node.get('pinfunction'), node.get('pintype'))
    return parts, pins


def replay(cli, project, netlist, erc):
    jobs = {
        netlist: ['sch', 'export', 'netlist', '--format', 'kicadxml'],
        erc: ['sch', 'erc', '--format', 'json', '--exit-code-violations'],
    }
    for output, command in jobs.items():
        process = subprocess.run([cli, *command, '-o', str(output), project + '.kicad_sch'], cwd=HERE,
                                 capture_output=True, text=True)
        if process.returncode:
            raise RuntimeError(process.stdout + process.stderr)


def verify_erc(path, project, frozen):
    report = json.loads(path.read_text())
    assert report['ignored_checks'] == frozen['ignored_checks']
    assert report['included_severities'] == ['error', 'warning']
    assert not any(sheet['violations'] for sheet in report['sheets'])
    assert json.loads((HERE / (project + '.kicad_pro')).read_text())['erc']['erc_exclusions'] == []
    return report


def verify_main_view(cli, transport):
    # Main is a subset of the transport view. Both use the exact same component sheets.
    with TemporaryDirectory() as directory:
        netlist = Path(directory) / 'main.xml'
        erc = Path(directory) / 'main-erc.json'
        replay(cli, PROJECT, netlist, erc)
        verify_erc(erc, PROJECT, json.loads((SOURCE / 'erc.json').read_text()))
        parts, pins = read_netlist(netlist)
    transport_parts, transport_pins = read_netlist(transport)
    components = ET.parse(transport).findall('./components/comp')
    main_refs = {part.get('ref') for part in components if
                 Path(part.find("property[@name='Sheetfile']").get('value')).name not in REMOTE_BOARD_SHEETS}
    assert parts == {ref: part for ref, part in transport_parts.items() if ref in main_refs}
    assert pins == {ref_pin: pin for ref_pin, pin in transport_pins.items() if ref_pin[0] in main_refs}
    assert SERVICE_COPPER <= main_refs
    by_ref = {part.get('ref'): part for part in components}
    assert all(by_ref[ref].find("property[@name='exclude_from_bom']") is not None for ref in SERVICE_COPPER)
    return {'source': PROJECT + '.kicad_sch', 'ERC_errors': 0, 'ERC_warnings': 0,
            'refs': len(parts), 'terminals': len(pins), 'equal_to_transport_subset': True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kicad-cli', required=True)
    args = parser.parse_args()
    manifest = json.loads((HERE / 'source-manifest.json').read_text())
    contract = json.loads((HERE / 'circuit-contract.json').read_text())
    for path, sha in (manifest['inputs_sha256'] | contract['source_sha256']).items():
        assert digest(ROOT / path) == sha, ('Changed input', path)
    assert digest(HERE / 'build_source.py') == manifest['builder_sha256']
    assert digest(HERE / 'contract.py') == contract['builder_sha256']
    track = [*sorted((HERE / 'sheets').glob('*.kicad_sch')), *sorted((HERE / 'WiredMain.pretty').glob('*.kicad_mod')),
             *(HERE / (project + suffix) for project in (PROJECT, TRANSPORT) for suffix in ('.kicad_sch', '.kicad_pro')),
             HERE / 'WiredMain.kicad_sym',
             HERE / 'fp-lib-table', HERE / 'sym-lib-table', HERE / 'source-manifest.json', HERE / 'circuit-contract.json',
             HERE / 'build_source.py', HERE / 'contract.py', Path(__file__)]
    source_hashes = {str(p.relative_to(HERE)): digest(p) for p in track}
    cli_version = subprocess.check_output([args.kicad_cli, '--version'], text=True).strip()
    assert cli_version == '10.0.8', cli_version
    transport_netlist = HERE / 'native.xml'
    transport_erc = HERE / 'erc.json'
    replay(args.kicad_cli, TRANSPORT, transport_netlist, transport_erc)
    report = verify_erc(transport_erc, TRANSPORT, json.loads((SOURCE / 'erc.json').read_text()))
    main_view = verify_main_view(args.kicad_cli, transport_netlist)

    old_components, old_pins = read_netlist(SOURCE / 'native.xml')
    new_components, new_pins = read_netlist(HERE / 'native.xml')
    old_refs = set(old_components)
    assert old_refs <= set(new_components)
    exact_deltas = {}
    for key, old in old_pins.items():
        new = new_pins[key]
        assert new[1] == old[1], (key, old, new)
        terminal = '.'.join(key)
        wanted = contract['native_baseline_terminal_changes'].get(terminal)
        if wanted is None:
            assert new == old, (key, old, new)
        else:
            assert [old[0], new[0]] == wanted, (key, old, new, wanted)
            assert new[2] == old[2].removesuffix('+no_connect'), (key, old, new)
            exact_deltas[terminal] = wanted
    assert set(exact_deltas) == set(contract['native_baseline_terminal_changes'])
    assert {p for p in new_pins if p[0] in old_refs} == set(old_pins)
    for ref, old in old_components.items():
        expected = old
        if ref in VALUES:
            value, mpn, mfr = VALUES[ref]
            expected = (value, old[1], mpn, mfr)
        assert new_components[ref] == expected, (ref, new_components[ref], expected)

    # Devices and passives come from the saved contract. Service copper is a
    # separate explicit contract here so the verifier does not use generated nets.
    service = {'TP151': 'PC_LOCKn', 'TP152': 'GND', 'TP153': 'RP_SWDIO',
               'TP154': 'RP_SWCLK', 'TP155': 'RP_RUN', 'TP156': 'USB_HOST_3V3', 'TP157': 'RP_BOOTSEL_PAD'}
    expected_new = {}
    for ref, device in contract['devices'].items():
        expected_new[ref] = {number: spec[1] for number, spec in device['pins'].items()}
        actual = new_components[ref]
        assert (actual[0], actual[2], actual[3]) == (device['mpn'], device['mpn'], device['manufacturer']), (ref, actual)
    for ref, (value, net1, net2, *_) in contract['passives'].items():
        expected_new[ref] = {'1': net1, '2': net2}
        assert new_components[ref][0] == value
    expected_new.update({ref: {'1': net} for ref, net in service.items()})
    assert set(new_components) - old_refs == set(expected_new)
    expected_terminals = {(ref, pin): net for ref, pins in expected_new.items() for pin, net in pins.items()}
    assert {key: data[0] for key, data in new_pins.items() if key[0] not in old_refs} == expected_terminals
    footprint_cache = {}
    for ref, expected in expected_new.items():
        name = new_components[ref][1]
        assert name == manifest['new_reference_footprints'][ref]
        library, model = name.split(':')
        assert library == 'WiredMain'
        if model not in footprint_cache:
            fp = sx.parse((HERE / (library + '.pretty') / (model + '.kicad_mod')).read_text())
            footprint_cache[model] = {pad[1].value for pad in sx.children(fp, 'pad') if pad[1].value}
        assert footprint_cache[model] == set(expected), (ref, footprint_cache[model], set(expected))
    assert source_hashes == {str(p.relative_to(HERE)): digest(p) for p in track}
    result = {
        'status': 'Native ERC and terminal/value conservation passed; routed and powered verification pending',
        'kicad_version': cli_version, 'retained_refs': len(old_refs), 'retained_terminals': len(old_pins),
        'exact_declared_terminal_changes': exact_deltas, 'exact_declared_resistor_changes': VALUES,
        'new_refs': len(expected_new), 'new_terminals': len(expected_terminals),
        'new_footprint_pin_checks': len(expected_new), 'total_refs': len(new_components), 'total_terminals': len(new_pins),
        'ERC_errors': 0, 'ERC_warnings': 0, 'ERC_exclusions': [],
        'inherited_ERC_ignored_checks': [v['key'] for v in report['ignored_checks']],
        'source_hashes': source_hashes, 'baseline_and_contract_hashes': manifest['inputs_sha256'] | contract['source_sha256'],
        'native_report_schematic': TRANSPORT + '.kicad_sch', 'main_view': main_view,
        'native_report_hashes': {name: digest(HERE / name) for name in ('native.xml', 'erc.json')},
        'PCB_validated_by_this_check': False, 'powered_validation': False, 'assembly_release': False,
    }
    (HERE / 'native-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f"KiCad {cli_version}: ERC 0/0; {len(old_refs)} original refs and {len(old_pins)} terminals, "
          f"{len(expected_new)} new refs and {len(expected_terminals)} contract terminals verified.")


if __name__ == '__main__':
    main()
