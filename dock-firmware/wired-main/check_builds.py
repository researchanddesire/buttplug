"""Bind the two compiled wired dock images to firmware and schematic sources."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
DOCK = HERE.parent
ROOT = DOCK.parent
WIRED = ROOT / 'hardware/pcb/evt1/case-telemetry-study/wired-main'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def linked(cross, elf, required, forbidden):
    output = subprocess.check_output([cross + 'nm', '--defined-only', elf], text=True)
    symbols = {line.split()[-1] for line in output.splitlines()}
    assert set(required) <= symbols and not set(forbidden) & symbols
    sizes = subprocess.check_output([cross + 'size', elf], text=True).splitlines()[1].split()
    return dict(zip(('text', 'data', 'bss'), map(int, sizes[:3])))


def pins_and_parts():
    xml = WIRED / 'native.xml'
    checked = json.loads((WIRED / 'native-checks.json').read_text())
    assert digest(xml) == checked['native_report_hashes']['native.xml']
    source = ET.parse(xml)
    pins = {(node.get('ref'), node.get('pin')): net.get('name')
            for net in source.findall('./nets/net') for node in net.findall('node')}
    expected = {
        'U201.5': 'USB_HOST_SCL', 'U201.6': 'USB_HOST_SDA',
        'U162.2': 'USB_HOST_SDA', 'U162.3': 'RP_SDA',
        'U162.5': 'USB_HOST_SCL', 'U162.6': 'RP_SCL',
        'U160.2': 'RP_SDA', 'U160.3': 'RP_SCL',
        'U160.4': 'RP_LOCAL_READY', 'U160.5': 'RP_USB_BREAK',
        'U160.6': 'RP_CONTACT_OK', 'U160.7': 'RP_LIMIT_FAULTn',
    }
    assert {key: pins[tuple(key.split('.'))] for key in expected} == expected
    resistor_mpns = {'R107': 'RT0603BRD0740K2L',
                     'R401': 'CRCW08054R22FKEA', 'R501': 'CRCW08054R22FKEA'}
    for ref, mpn in resistor_mpns.items():
        assert source.find(f"./components/comp[@ref='{ref}']/property[@name='MPN']").get('value') == mpn
    return {'native_xml_sha256': digest(xml), 'terminals': expected, 'matched_MPNs': resistor_mpns}


def artifacts(folder, stem):
    return {path.name: digest(path)
            for path in (folder / (stem + '.' + suffix) for suffix in ('bin', 'hex', 'elf'))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cross', required=True)
    parser.add_argument('--stm32-build', type=Path, required=True)
    parser.add_argument('--rp2040-build', type=Path, required=True)
    parser.add_argument('--direct-build', type=Path, required=True)
    parser.add_argument('--framed-build', type=Path, required=True)
    parser.add_argument('--smoke-build', type=Path, required=True)
    args = parser.parse_args()
    subprocess.run(['make', '-C', DOCK, 'test'], check=True)
    subprocess.run(['make', '-C', DOCK / 'case-link-candidate', '-f', 'wired-cdc.mk',
                    'wired-cdc-test'], check=True)
    rp_path = HERE / 'build-validation.json'
    rp = json.loads(rp_path.read_text())
    required = [*rp['required_symbols_linked'], 'watchdog_enable', 'set_sys_clock_48mhz',
                'tuh_cdc_read_clear', 'tuh_cdc_write_clear', 'case_link_new_session',
                'wired_cdc_next_request']
    required = list(dict.fromkeys(required))
    rp['required_symbols_linked'] = required
    rp['scope'] = 'Compiled wired dock firmware on both processors. Installed and powered tests pending.'
    rp['arm_size_bytes'] = linked(args.cross, args.rp2040_build / 'compass_wired_host.elf',
                                  required, rp['absent_symbols_verified'])
    rp['artifacts_sha256'] = artifacts(args.rp2040_build, 'compass_wired_host')
    rp['sources_sha256'] = {name: digest(ROOT / name) for name in rp['sources_sha256']}
    replay_sources = [DOCK / 'case-link-candidate' / name for name in ('test_wired_cdc.c', 'wired-cdc.mk')]
    replay_sources.extend(ROOT / 'firmware/main' / name for name in ('case_telemetry.c', 'thermal_history.c'))
    rp['retained_event_replay'] = {
        'host_actual_sender_roundtrip': True,
        'tested': ['long-gap reconnect', 'invalid attempt followed by valid reading',
                   'rapid redock', 'different retained event rejected', 'plug reboot'],
        'source_sha256': {str(path.relative_to(ROOT)): digest(path) for path in replay_sources},
    }
    stm_required = ['board_host_bus_init', 'board_host_bus_transfer', 'host_client_step',
                    'lcd_render_host', 'dock_step', 'board_watchdog_heartbeat']
    stm_size = linked(args.cross, args.stm32_build / 'dock-evt1.elf', stm_required, [])
    assert stm_size['text'] + stm_size['data'] < 131072
    assert stm_size['bss'] + stm_size['data'] < 20480 - 2048
    binary = (args.stm32_build / 'dock-evt1.bin').read_bytes()
    sp, reset = struct.unpack_from('<II', binary)
    assert sp == 0x20005000 and reset & 1 and 0x08000000 < reset < 0x08000000 + len(binary)
    assert 'PROFILE=wired' in subprocess.check_output(
        ['make', '-C', DOCK, '-pn', 'PROFILE=wired'], text=True)
    assert '-DDOCK_UV_SENSE_MILLIOHM=4220u' in subprocess.check_output(
        ['make', '-C', DOCK, '-Bn', 'PROFILE=wired'], text=True)
    baseline = json.loads((DOCK / 'validation.json').read_text())
    direct = artifacts(args.direct_build, 'dock-evt1')
    assert direct['dock-evt1.bin'] == baseline['artifacts']['dock-evt1.bin']
    rp['stm32'] = {
        'profile': 'wired', 'sense_milliohm': 4220, 'arm_size_bytes': stm_size,
        'required_symbols_linked': stm_required,
        'artifacts_sha256': artifacts(args.stm32_build, 'dock-evt1'),
        'source_sha256': {
            str(path.relative_to(ROOT)): digest(path)
            for path in sorted([DOCK / 'Makefile', DOCK / 'stm32l071cb.ld',
                                *DOCK.glob('include/*.h'), *DOCK.glob('src/*.c'),
                                *DOCK.glob('tests/*.c'), DOCK / 'tests/run.sh',
                                *HERE.glob('host_client.*'), HERE / 'test_host_client.c',
                                Path(__file__)])},
        'default_direct_image_bin_unchanged': True,
    }
    bench_file = DOCK / 'wired-host-bench/build-validation.json'
    bench = json.loads(bench_file.read_text())
    bench['sources_sha256'] = {name: digest(ROOT / name) for name in bench['sources_sha256']}
    for mode, path in [('host', args.framed_build), ('smoke', args.smoke_build)]:
        saved = bench['variants'][mode]['artifacts_sha256']
        now = artifacts(path, 'compass_wired_host')
        for suffix in ('bin', 'hex'):
            name = 'compass_wired_host.' + suffix
            assert now[name] == saved[name], (mode, name)
        saved.update(now)
    rp['schematic_binding'] = pins_and_parts()
    bench_file.write_text(json.dumps(bench, indent=2) + '\n')
    rp_path.write_text(json.dumps(rp, indent=2) + '\n')
    print('Both wired targets and both stock Pico variants verified. Default STM32 BIN is unchanged.')


if __name__ == '__main__':
    main()
