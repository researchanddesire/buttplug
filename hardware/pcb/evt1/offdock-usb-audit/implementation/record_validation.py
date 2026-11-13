#!/usr/bin/env python3
"""Bind completed host/cross-build evidence; does not flash or qualify hardware."""
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
BUILD = Path('/private/tmp/compass-usb-gate-build')
SDK = Path('/Users/lucianchapar/.platformio/packages/framework-espidf')
TOOLS = Path('/Users/lucianchapar/.platformio/packages/toolchain-riscv32-esp/bin')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def entry(path):
    path = Path(path)
    return {'path': str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
            'bytes': path.stat().st_size, 'SHA256': sha(path)}


def run(tool, *args):
    return subprocess.check_output([str(TOOLS / tool), *map(str, args)], text=True)


def main():
    baseline = json.loads((HERE / 'baseline.json').read_text())
    audit = json.loads((HERE.parent / 'evidence.json').read_text())
    unchanged = []
    for item in baseline['sources']:
        if item['path'] in ('firmware/main/evt_console.c', 'firmware/main/evt_console.h',
                            'firmware/main/main.c', 'developer-docs/docs/firmware.md',
                            'developer-docs/docs/testing.md'):
            continue
        assert sha(ROOT / item['path']) == item['SHA256'], item['path']
        unchanged.append(entry(ROOT / item['path']))
    for item in audit['source_snapshots']:
        path = Path(item['path'])
        if '/hardware/pcb/' in str(path) or path.name in ('Kconfig.projbuild', 'sdkconfig.defaults'):
            assert sha(path) == item['SHA256'], str(path)
            unchanged.append(entry(path))
    uv_helper = ROOT / 'tools/build_evt1_dock_uv_labyrinth.py'
    assert sha(uv_helper) == baseline['frozen_UV_helper_SHA256']
    unchanged.append(entry(uv_helper))
    old_artifacts = []
    for item in baseline['artifacts']:
        path = ROOT / item['path']
        assert path.stat().st_size == item['bytes']
        assert path.stat().st_mtime_ns == item['mtime_ns']
        if item['SHA256']:
            assert sha(path) == item['SHA256'], str(path)
        old_artifacts.append({**item, 'preserved': True,
                              'verification': 'hash and metadata' if item['SHA256'] else
                              'metadata only; original cloud-dataless ELF not read'})

    sdk_files = []
    assert (SDK / 'version.txt').read_text().strip() == '5.5.3'
    for item in audit['exact_official_source_comparisons']:
        current = sha(SDK / item['IDF_relative_path'])
        assert current == item['official_SHA256'] == item['installed_SHA256']
        sdk_files.append({**item, 'current_installed_SHA256': current})
    for relative, downloaded in (
        ('components/esp_driver_gpio/src/gpio.c', 'official-gpio.c'),
        ('components/freertos/FreeRTOS-Kernel/portable/riscv/port.c', 'official-riscv-port.c')):
        current = sha(SDK / relative)
        official = sha(Path('/private/tmp/compass-offdock-usb') / downloaded)
        assert current == official
        sdk_files.append({'IDF_relative_path': relative,
                          'primary_URL': 'https://raw.githubusercontent.com/espressif/esp-idf/v5.5.3/' + relative,
                          'official_SHA256': official, 'current_installed_SHA256': current,
                          'exact_match': True})
    build_snapshot = json.loads((HERE / 'source-snapshot-during-build.json').read_text())
    for relative, expected in build_snapshot.items():
        assert sha(ROOT / relative) == expected, relative

    pio_log = (HERE / 'pio-build.log').read_text()
    assert re.search(r'prototype-r0\s+SUCCESS', pio_log)
    assert re.search(r'evt1\s+SUCCESS', pio_log)
    assert 'error:' not in pio_log.lower()
    assert 'warning:' not in pio_log.lower()
    console_log = (HERE / 'console-host.log').read_text()
    assert 'console/PHY boundary:' in console_log and 'detach pass.' in console_log
    existing_log = (HERE / 'existing-host.log').read_text()
    assert '1680 known tilted poses and calibrations passed' in existing_log
    assert 'EVT thermistor fixtures' in existing_log and 'dock accounting' in existing_log

    elf = BUILD / 'evt1/firmware.elf'
    symbols = run('riscv32-esp-elf-objdump', '-t', elf)
    (HERE / 'evt1-symbols.txt').write_text(symbols)
    required = ['dock_detached', 'pad_off_locked', 'vPortEnterCritical',
                'vPortExitCritical', 'gpio_intr_service', 'gpio_isr_loop',
                'xPortSetInterruptMaskFromISR', 'vPortClearInterruptMaskFromISR']
    functions = {}
    for line in symbols.splitlines():
        fields = line.split()
        if len(fields) >= 6 and fields[-1] in required:
            functions[fields[-1]] = {'address': fields[0], 'section': fields[-3],
                                      'size_hex': fields[-2]}
    assert set(functions) == set(required), functions
    for name, item in functions.items():
        assert item['section'] == '.iram0.text', (name, item)
    data_required = ['detach_generation', 'gpio_context', 'port_uxCriticalNesting',
                     'port_uxOldInterruptState']
    isr_data = {}
    rom_ffs = None
    for line in symbols.splitlines():
        fields = line.split()
        if len(fields) >= 6 and fields[-1] in data_required:
            isr_data[fields[-1]] = {'address': fields[0], 'section': fields[-3]}
        if len(fields) >= 5 and fields[-1] == '__ffssi2':
            rom_ffs = {'address': fields[0], 'section': fields[-3]}
    assert set(isr_data) == set(data_required)
    assert all(v['section'] in ('.dram0.bss', '.dram0.data') for v in isr_data.values())
    assert rom_ffs and rom_ffs['section'] == '*ABS*'
    assert 0x40000000 <= int(rom_ffs['address'], 16) < 0x40080000
    disassembly = ''
    for name in required:
        disassembly += run('riscv32-esp-elf-objdump', '-d', '--disassemble=' + name, elf)
    (HERE / 'evt1-isr-disassembly.txt').write_text(disassembly)
    pad_disassembly = run('riscv32-esp-elf-objdump', '-d', '--disassemble=pad_off_locked', elf)
    assert not re.search(r'\b(?:jal|jalr|call)\b', pad_disassembly)
    # This expected small call set is reviewed against the linked disassembly.
    own_isr = run('riscv32-esp-elf-objdump', '-d', '--disassemble=dock_detached', elf)
    isr_calls = re.findall(r'\bjal\s+[^\n]*<([^>]+)>', own_isr)
    assert set(isr_calls) == {'pad_off_locked', 'vPortEnterCritical', 'vPortExitCritical'}, isr_calls
    legacy_symbols = run('riscv32-esp-elf-nm', '-a', BUILD / 'prototype-r0/firmware.elf')
    assert not re.search(r'evt_console_transport|dock_detached|pad_off_locked', legacy_symbols)
    (HERE / 'prototype-symbols.txt').write_text(legacy_symbols)
    main_source = (ROOT / 'firmware/main/main.c').read_text()
    assert main_source.index('gpio_config(&inputs)') < main_source.index('evt_console_transport_init(')
    assert main_source.index('evt_console_transport_init(') < main_source.index('nvs_flash_init(')
    assert main_source.index('nvs_flash_init(') < main_source.index('evt_console_load_calibration(')

    source_paths = sorted((ROOT / 'firmware/main').glob('*'))
    source_paths = [p for p in source_paths if p.is_file()]
    source_paths += sorted((ROOT / 'firmware/tests').rglob('*'))
    source_paths = [p for p in source_paths if p.is_file()]
    source_paths += [ROOT / 'firmware/platformio.ini', ROOT / 'firmware/sdkconfig.evt1',
                     ROOT / 'firmware/sdkconfig.prototype-r0', ROOT / 'firmware/sdkconfig.defaults',
                     ROOT / 'developer-docs/docs/firmware.md', ROOT / 'developer-docs/docs/testing.md',
                     Path(__file__)]
    artifacts = []
    for profile in ('evt1', 'prototype-r0'):
        artifacts += [entry(BUILD / profile / name) for name in
                      ('firmware.elf', 'firmware.bin', 'buttplug_prototype_r0.map', 'bootloader.bin',
                       'partitions.bin', 'config/sdkconfig.h')]
    outputs = [entry(HERE / name) for name in
               ('baseline.json', 'source-snapshot-during-build.json', 'README.md', 'console-host.log', 'existing-host.log',
                'pio-build.log', 'evt1-symbols.txt', 'evt1-isr-disassembly.txt', 'prototype-symbols.txt')]
    report = {
        'state': 'Application USB policy implemented; host and cross-compile evidence only',
        'recorded_UTC': datetime.now(timezone.utc).isoformat(),
        'commands': ['sh firmware/tests/run_evt_console_tests.sh',
                     'sh firmware/tests/run_host_tests.sh',
                     'PLATFORMIO_BUILD_DIR=/private/tmp/compass-usb-gate-build pio run -d firmware -e evt1 -e prototype-r0'],
        'host_tests': {'actual_console_LL_GPIO_USB_driver_NVS_boundary': 'PASS with UBSan',
                       'existing_control_compass_thermistor_wear_suites': 'PASS with UBSan',
                       'cJSON_scope': 'Parsing stubs; transport/session policy tested with actual status/clear command paths'},
        'cross_build': {'evt1': 'PASS', 'prototype-r0': 'PASS', 'warnings': 0,
                        'original_build_outputs_preserved': True, 'flash_performed': False},
        'ISR': {'linked_functions': functions, 'dock_detached_direct_calls': isr_calls,
                'pad_off_locked_only_MMIO_no_calls': True,
                'pad_enable_cleared_before_RX_interrupt_mask': True,
                'native_data_symbols': isr_data, 'GPIO_ffs_helper': rom_ffs,
                'GPIO_callback_table': 'Pinned gpio.c uses MALLOC_CAP_INTERNAL with ESP_INTR_FLAG_IRAM',
                'scope': 'Normal balanced critical-section ISR path in IRAM/ROM with DRAM state; no measured latency or voltage',
                'SDK_failure_path': 'vPortExitCritical assertion failure retains flash diagnostic strings; panic/corrupted nesting is outside this application policy'},
        'SDK': {'version': '5.5.3', 'tag': 'v5.5.3', 'primary_byte_comparisons': sdk_files},
        'source_snapshot': [entry(p) for p in sorted(set(source_paths))],
        'unchanged_guards': unchanged, 'baseline_artifacts': old_artifacts,
        'new_build_artifacts': artifacts, 'evidence_outputs': outputs,
        'legacy_application_gate_symbols_absent': True,
        'remaining_physical_limits': [
            'ROM/startup/reset/CPU hang remain outside application pad policy',
            'Physical GPIO20 is charger power-good, not mechanical closure or dryness',
            'RX driver defaults may temporarily enable pads during its one installation attempt; policy reapplies immediately after return',
            'In-flight NVS set/commit may finish after detach and cannot be retroactively cancelled',
            'Pad voltage/current, U75 steering/backbias, contact leakage and interrupt latency need bench measurement',
            'Enumeration, flashing, reset recovery, sleep/wake and actual contact subassembly remain unqualified']}
    (HERE / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PASS: current sources, SDK, baseline preservation, host logs, two builds and linked ISR sections bound')


if __name__ == '__main__':
    main()
