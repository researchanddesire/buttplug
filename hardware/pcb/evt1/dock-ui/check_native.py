"""Check only the new dock source sheet with native KiCad 10 or newer.

This does not refresh the existing five-PCB baseline or claim that the complete
dock UI, interlock and UV driver circuits have been implemented.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import subprocess

HERE = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def sources():
    return {str(p.relative_to(HERE)): sha(p) for p in sorted(HERE.rglob('*'))
            if p.is_file() and
            (p.suffix in ('.kicad_sch', '.kicad_sym', '.kicad_pro', '.kicad_mod')
             or p.name in ('fp-lib-table', 'sym-lib-table', 'build_source.py',
                           'check_source.py', 'check_native.py',
                           'source-circuit-parts.json'))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kicad-cli', required=True)
    args = ap.parse_args()
    version = subprocess.check_output([args.kicad_cli, '--version'], text=True).strip()
    assert int(version.split('.')[0]) >= 10, 'Native ERC requires KiCad 10 or newer'
    before = sources()
    project = json.loads((HERE / 'dock-ui-source.kicad_pro').read_text())
    assert project['erc']['erc_exclusions'] == [], 'Do not conceal source-sheet findings'
    schematic = HERE / 'dock-ui-source.kicad_sch'
    commands = [
        ['sch', 'export', 'netlist', '--format', 'kicadxml', '-o',
         str(HERE / 'source-native.xml'), str(schematic)],
        ['sch', 'erc', '--format', 'json', '--exit-code-violations', '-o',
         str(HERE / 'erc.json'), str(schematic)],
    ]
    for command in commands:
        run = subprocess.run([args.kicad_cli] + command, text=True,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if run.returncode:
            raise AssertionError((command, run.returncode, run.stdout))
    erc = json.loads((HERE / 'erc.json').read_text())
    findings = [v for sheet in erc['sheets'] for v in sheet['violations']]
    assert not findings, findings
    assert erc['kicad_version'] == version
    assert erc['included_severities'] == ['error', 'warning']
    expected_ignored = {'single_global_label', 'four_way_junction',
                        'simulation_model_issue', 'footprint_filter'}
    assert {v['key'] for v in erc['ignored_checks']} == expected_ignored
    assert sources() == before, 'Saved source changed during native checks; rerun'
    report = {
        'status': 'pass: source-bound native KiCad ERC',
        'scope': 'USB/source-current sheet only; full UI/safety/UV sheets are absent',
        'checked_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'kicad_version': version,
        'source_sha256': before,
        'reports_sha256': {name: sha(HERE / name)
                           for name in ('source-native.xml', 'erc.json')},
        'ERC_error_count': 0,
        'ERC_warning_count': 0,
        'ERC_exclusions': [],
        'standard_ignored_checks': sorted(expected_ignored),
        'off_sheet_context_findings': [],
        'PCB_created_or_routed': False,
        'powered_validation': False,
        'full_product_order_ready': False,
    }
    (HERE / 'native-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('status', 'scope', 'kicad_version',
                     'ERC_error_count', 'ERC_warning_count', 'full_product_order_ready')}, indent=2))


if __name__ == '__main__':
    main()
