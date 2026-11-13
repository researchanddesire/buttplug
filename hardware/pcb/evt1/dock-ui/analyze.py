"""Recalculate selected dock budgets and exhaust the abstract latch transitions.

This is a circuit design aid, not SPICE, native ERC, USB compliance or safety
certification. It deliberately marks every physical/native result unverified.
"""
from pathlib import Path
from itertools import product
import hashlib
import json

HERE = Path(__file__).resolve().parent
budget = json.loads((HERE / 'power-budget.json').read_text())
lim = budget['UV_branch_limiter']
delta_K = budget['resistor_bound_method']['maximum_abs_film_temperature_departure_K']
lim_error = (lim['resistor_tolerance_fraction']
             + lim['resistor_temperature_coefficient_ppm_per_K'] * 1e-6 * delta_K)
r_min = lim['RILIM_ohm'] / 1000 * (1 - lim_error)
r_max = lim['RILIM_ohm'] / 1000 * (1 + lim_error)
uv_limit_min = 25230 / r_max ** 1.016
uv_limit_max = 22980 / r_min ** 0.94
uv = budget['UV_modules']
rset_error = (uv['RSET_tolerance_fraction']
              + uv['RSET_temperature_coefficient_ppm_per_K'] * 1e-6 * delta_K)
rset_min = uv['RSET_ohm'] * (1 - rset_error)
rset_max = uv['RSET_ohm'] * (1 + rset_error)
i_min = uv['feedback_voltage_V'][0] / rset_max
i_nom = uv['feedback_voltage_V'][1] / uv['RSET_ohm']
i_max = uv['feedback_voltage_V'][2] / rset_min
v_string = (uv['LEDs_per_series_string'] * uv['forward_voltage_design_ceiling_per_LED_V']
            + uv['cathode_FET_drop_design_allowance_V'] + uv['feedback_voltage_V'][2])
uv_output_W = uv['count'] * v_string * i_max
uv_input_mA = (1000 * uv_output_W /
               (uv['minimum_driver_input_V'] * uv['efficiency_design_floor'])
               + uv['driver_quiescent_total_allocation_mA'])
dock = budget['dock_overhead']['allocation_mA']
legacy = budget['device_path']['default_allocation_mA'] + dock
qualified_bound = budget['device_path']['qualified_allocation_mA'] + dock + uv_limit_max
assert sum(x['mA'] for x in budget['dock_overhead']['allocated_items']) <= dock
assert legacy < 100
assert qualified_bound < budget['qualified_source_requirement']['minimum_advertised_current_mA']
assert uv_input_mA < uv_limit_min
assert i_max < .15

# Source sequencing and loaded logic-level design bounds. Leakage terms are
# declared acceptance allocations; these do not replace measured waveforms.
seq = budget['source_sequencing']
vf = seq['SOURCE_OK_filter']
v3_min = seq['LDO_nominal_V'] * (1-seq['LDO_accuracy_fraction'])
v3_max = seq['LDO_nominal_V'] * (1+seq['LDO_accuracy_fraction'])
pull_max = seq['pullup_ohm'] * (1+seq['pullup_tolerance_fraction'])
pg1_high = v3_min - pull_max * seq['pg1_input_current_allocation_A']
pg2_high = v3_min - pull_max * seq['pg2_input_current_allocation_A']
rg = vf['R_ground_ohm'] * (1+vf['R_ground_error_fraction']) + seq['SPDT_Ron_maximum_ohm']
rc = vf['R_charge_ohm'] * (1+vf['R_charge_error_fraction']) + seq['SPDT_Ron_maximum_ohm']
rd = vf['pulldowns_parallel_ohm'] * (1-vf['pulldown_error_fraction'])
source_high = ((v3_min-seq['inverter_VOH_drop_at_100uA_V']
                -rc*vf['load_leakage_allocation_A']) / (1+rc/rd))
source_low = rg * vf['load_leakage_allocation_A']
inverter_load_bound = v3_max/rd + vf['load_leakage_allocation_A']
assert inverter_load_bound < 100e-6, 'VOH VDD-0.1V condition must hold'
assert min(pg1_high, pg2_high) > seq['SPDT_VIH_minimum_V']
assert seq['supervisor_asserted_maximum_VOL_V'] < seq['SPDT_VIL_maximum_V']
assert seq['first_delay_ms_min_nom_max'][0] >= seq['TUSB_initial_EN_low_minimum_ms']
assert seq['second_delay_ms_min_nom_max'][0] > seq['TUSB_enable_to_I2C_available_maximum_ms']
assert seq['supervisor_threshold_nominal_V']*(1-seq['supervisor_threshold_tolerance_fraction']) > seq['TUSB_minimum_VDD_V']
assert source_high > 2.0 and source_low < .05

# State=(release_seen, uv_run, previous_debounced_center_pressed).
# Fault dominates both clock edges. A release edge arms the release latch;
# only a later press captures the independent MCU_ARM input into UV_RUN.
def advance(state, safe, arm, pressed):
    released, run, old_pressed = state
    if not safe:
        return (False, False, pressed)
    release_edge = old_pressed and not pressed
    press_edge = not old_pressed and pressed
    return (released or release_edge,
            (released and arm) if press_edge else run,
            pressed)

transitions = 0
for values in product((False, True), repeat=6):
    release, run, old_button, safe, arm, button = values
    after = advance((release, run, old_button), safe, arm, button)
    assert safe or after[:2] == (False, False)
    if safe and not release and not old_button and button:
        assert not after[1], 'pending press cannot start with release latch clear'
    transitions += 1

fault_sequences = 0
# Include an already held debounced button and a press still pending in the
# hardware debouncer at the time of fault. After recovery, arbitary ARM changes
# and no debounced release cannot start. Then release+freshpress must work.
for old_button, recovery_button in product((False, True), repeat=2):
    state = advance((True, True, old_button), False, True, old_button)
    # During the 180ms minimum UV-reset holdoff, any <=80ms pending hardware
    # debounce edge arrives while clear is still asserted.
    state = advance(state, False, True, recovery_button)
    for arm in (False, True, False, True):
        state = advance(state, True, arm, recovery_button)
        assert state[1] is False
    if not recovery_button:
        # First press cannot start, because no release edge since the fault.
        state = advance(state, True, True, True)
        assert state[1] is False
    state = advance(state, True, True, False)
    assert state[0] and not state[1]
    state = advance(state, True, True, True)
    assert state[1]
    fault_sequences += 1

contract = json.loads((HERE / 'pin-contract.json').read_text())
pins = contract['MCU']['pins']
assert set(pins) == {str(i) for i in range(1, 49)}
assert pins['34']['net'] == 'SWDIO' and pins['37']['net'] == 'SWCLK'
assert pins['1']['gpio'] == 'VDD'
assert len(contract['UI_hinge_link']['pins']) == 20
assert len(contract['lid_UV_hinge_loom']['pins']) == 8
assert contract['lid_UV_hinge_loom']['boost_voltage_crosses_hinge'] is False

result = {
    'schema_version': 1,
    'status': 'pass: arithmetic and abstract logical model only',
    'source_sha256': {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                      for name in ('DESIGN.md', 'parts-selection.json', 'power-budget.json',
                                   'pin-contract.json', 'analyze.py')},
    'calculated': {
        'resistor_initial_tolerance_plus_TCR_bound_fraction': {'UV_limit': lim_error, 'UV_LED_RSET': rset_error},
        'legacy_default_input_allocation_mA': legacy,
        'legacy_margin_to_100mA_mA': 100 - legacy,
        'qualified_UV_limiter_min_mA': uv_limit_min,
        'qualified_UV_limiter_max_mA': uv_limit_max,
        'qualified_sum_of_branch_DC_limit_allocations_mA': qualified_bound,
        'qualified_margin_to_1p5A_mA': 1500 - qualified_bound,
        'LED_current_min_nom_max_mA': [1000 * i_min, 1000 * i_nom, 1000 * i_max],
        'UV_output_power_design_ceiling_W': uv_output_W,
        'UV_input_design_ceiling_mA': uv_input_mA,
        'margin_to_minimum_UV_limiter_mA': uv_limit_min - uv_input_mA,
        'dock_item_allocations_sum_mA': sum(x['mA'] for x in budget['dock_overhead']['allocated_items'])
    },
    'source_control_design_bounds': {
        'PG1_HIGH_min_V': pg1_high, 'PG2_HIGH_min_V': pg2_high,
        'SOURCE_OK_HIGH_min_V': source_high, 'SOURCE_OK_LOW_max_V': source_low,
        'inverter_static_load_max_uA': inverter_load_bound*1e6,
        'TUSB_initial_EN_low_min_ms': seq['first_delay_ms_min_nom_max'][0],
        'status_guard_after_enable_min_ms': seq['second_delay_ms_min_nom_max'][0],
        'basis': 'datasheet timing/logic limits plus explicit leakage allocations; steady-state bounds only',
        'measured_ramp_brownout_or_charge_injection': False,
    },
    'abstract_logic': {'transitions_checked': transitions,
                       'fault_pending_debounce_sequences_checked': fault_sequences,
                       'minimum_UV_release_delay_ms': 180,
                       'maximum_CENTER_debounce_ms': 80,
                       'no_clock_on_fault_recovery': True,
                       'held_button_or_pending_press_cannot_restart_in_model': True},
    'verified_full_dock_native_schematic': False,
    'native_source_sheet_report': 'native-checks.json; independently enforced by check_source.py',
    'verified_native_PCB': False,
    'verified_firmware': False,
    'powered_source_or_safety_measurements': False,
    'UV_optical_or_cleaning_validation': False,
    'full_product_order_ready': False,
    'limits': ['Boolean model assumes ideal gates/flipflops and specified debounce/supervisor timings',
               'No switch/FET single-fault certification or analogue transient simulation',
               '10mA dock overhead and conversion/Vf assumptions remain measured acceptance gates',
               'USB suspend and inrush behavior require implementation and testing',
               'Resistor bounds include initial tolerance and TCR through 100K film-temperature departure, not long-term drift']
}
(HERE / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'pass': True, 'calculated': result['calculated'],
                  'source_control_design_bounds': result['source_control_design_bounds'],
                  'abstract_logic': result['abstract_logic']}, indent=2))
