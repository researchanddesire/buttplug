"""Analytical candidate corners, not component/safety qualification.

The equations intentionally preserve the original BQ24074 RISET, CE pullup,
TS bias and independent charge guard. No original source is rewritten.
"""
from pathlib import Path
import hashlib
import itertools
import json
import math

H = Path(__file__).resolve().parent
ROOT = H.parents[3]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def evaluate():
    # One of two series 10M taps shorted AND a buffer rail fault: conservative
    # combined case. 1% resistors; parasitic leakage is separately unqualified.
    tap_resistor_error = .01 + 100e-6 * 100 + .01  # initial +100K TCR +1% drift reserve
    tap_min = 10e6 * (1-tap_resistor_error)
    ts_corners = []
    for bias, threshold, fault in itertools.product((72e-6, 78e-6), (.270, .330, 2., 2.2), (0., 5.5)):
        ntc = threshold / bias
        disturbed = (bias + fault / tap_min) / (1 / ntc + 1 / tap_min)
        ts_corners.append(dict(bias_A=bias, threshold_V=threshold, ntc_ohm=ntc,
                               fault_rail_V=fault, disturbed_V=disturbed,
                               perturbation_mV=1000 * (disturbed - threshold)))
    max_ts_shift = max(abs(x['perturbation_mV']) for x in ts_corners)
    # At an open TS, even a fault to GND sinks at most ~0.56uA at5.5V;
    # this cannot balance the BQ's >=72uA source inside its valid TS window.
    open_ts_sink_at_cold_max = 2.2 / tap_min
    assert open_ts_sink_at_cold_max < 72e-6
    r_iset = 8870.
    parallel = r_iset * tap_min / (r_iset + tap_min)
    # CE isolation: SN74LVC1G14DCKR Schmitt input through22k, not a direct
    # TCA port or high-leakage MOSFET gate. Including CE input sink10uA,
    # R3 tolerance1%, tap tolerance1%. Use3.8V input as a candidate lower
    # observation bound; BQ PGOOD itself does not imply this voltage.
    r_pull_max, r_ce_min, r_ce_max = 10100., 22000. * .99, 22000. * 1.01
    ce_source_min = 3.8
    ce_disabled_fault = (ce_source_min - 10e-6 * r_pull_max) / (1 + r_pull_max / r_ce_min)
    ce_high_observed_min = ce_source_min - (10e-6 + 5e-6) * r_pull_max - 5e-6 * r_ce_max
    ce_low_observed_max = .4 + 5e-6 * r_ce_max
    assert ce_disabled_fault > 1.4
    # Conservative table envelope across2.3..5.5V exceeds our3.3V range:
    # VT+<=3.33V; VT->=0.58V forDCK. Slow CE edges are allowed.
    assert ce_high_observed_min > 3.33
    assert ce_low_observed_max < .58
    # TCA CHG input: initial pullup is ON. Its100uA max plus4.7k drop
    # still reads low against the BQ's specified0.4V at5mA.
    vdd_min, vdd_max = 3.3 * .98, 3.3 * 1.02
    r_chg_max, r_chg_min = 4700. * 1.01, 4700. * .99
    chg_low_max = .4 + 100e-6 * r_chg_max
    chg_sink_fault = vdd_max / r_chg_min + vdd_max / 9900. + 100e-6
    assert chg_low_max < .3 * vdd_min and chg_sink_fault < .005
    # Input bias bound30pA includes OPA391DCK -40..125C; two10M1%
    # resistors. Conservative offset envelope750uV +6uV/K*100K.
    bias_error = 30e-12 * 20e6 * (1+tap_resistor_error)
    offset_envelope = 750e-6 + 6e-6 * 100
    buffer_error = bias_error + offset_envelope
    # 1nF C0G at the buffer input; ±5%C, +1%R. Wait >=8tau after
    # power/config transitions before valid readings. BQ nodes see the RC
    # through20M, not a large direct added TS capacitance.
    tau_max = 20e6 * (1+tap_resistor_error) * 1e-9 * 1.05
    current_factor = 400. / r_iset
    termination = {'ISET_factor_Aohm_min': 797., 'ISET_factor_Aohm_max': 975.,
                   'USB100_fraction_min': .027, 'USB100_fraction_typ': .033, 'USB100_fraction_max': .040,
                   'programmed_current_nominal_mA': 890. / r_iset * 1000,
                   'termination_nominal_mA': .033 * 890. / r_iset * 1000,
                   'meaning': 'Comparator threshold, not a software Done threshold; actual input/thermal/DPPM and battery detection matter.'}
    tolerance = .001 + 25e-6 * 100
    limiter = lambda r: (25230 / (r * (1 + tolerance))**1.016,
                          22980 / (r * (1 - tolerance))**.94)
    other = 630. + 10. + 2 * 5.25 / (430. * .99) * 1000
    cases = []
    for name, rlim, rset, radio in [('frozen_no_radio', 34.8, 3.65, 0.),
                                    ('radio_only_unsafe', 34.8, 3.65, 70.),
                                    ('coupled_candidate', 39.2, 4.22, 70.)]:
        imin, imax = limiter(rlim)
        led = .204 / (rset * .98)
        vout = 16.204
        power = 2 * led * vout + 2 * vout**2 * (1 / 99000 + 1 / (1068000 * .99))
        iuv = power / (.7 * 4.10) * 1000 + 4.6
        total_normal = other + radio + iuv
        vin = 4.5 - total_normal / 1000 * .050 - iuv / 1000 * .165 - iuv / 2000 * .290
        hard_total = other + radio + imax
        cases.append(dict(name=name, U105_Rlim_kohm=rlim, UV_Rset_ohm=rset,
                          radio_allocation_mA=radio, UV_limit_min_mA=imin, UV_limit_max_mA=imax,
                          UV_normal_mA=iuv, UV_min_limit_margin_mA=imin-iuv,
                          hard_source_total_mA=hard_total, hard_source_margin_mA=1500-hard_total,
                          full_normal_source_mA=total_normal, driver_voltage_DC_V=vin,
                          LED_nominal_mA=.2/rset*1000,
                          passes_DC_candidate=hard_total < 1500 and iuv < imin and vin >= 4.10))
    assert cases[0]['passes_DC_candidate'] and not cases[1]['passes_DC_candidate'] and cases[2]['passes_DC_candidate']
    return {'status': 'Analytical candidate corners; no bench, supplier or fabrication acceptance',
        'builder_sha256': sha(Path(__file__)),
        'source_inputs_sha256': {str(p.relative_to(ROOT)): sha(p) for p in (
            ROOT/'hardware/pcb/evt1/body/body-native.xml', ROOT/'hardware/pcb/evt1/parts-selection.json',
            ROOT/'hardware/pcb/evt1/dock-safety/power-budget.json')},
        'TS': {'two_series_tap_resistors_ohm': [10e6,10e6], 'fault_tap_min_ohm':tap_min,
               'fault_corners':ts_corners, 'max_threshold_perturbation_mV':max_ts_shift,
               'open_NTC_fault_sink_A_at2p2V':open_ts_sink_at_cold_max,
               'minimum_TS_bias_A':72e-6, 'short_NTC_V':0.,
               'conclusion':'Open/short cannot be hidden by this bounded resistive fault; near-boundary trip shifts remain and require qualification. Independent guard remains unchanged.'},
        'ISET': {'selected_original_R1_ohm':r_iset, 'selected_R1_initial_tolerance_percent':.1,
                 'minimum_fault_parallel_R_ohm':parallel,
                 'resistance_reduction_percent':100*(1-parallel/r_iset),
                 'max_fault_injection_A':5.5/tap_min,
                 'mirror_accuracy_percent':10.,
                 'buffer_voltage_error_envelope_mV':1000*buffer_error,
                 'buffer_only_current_error_mA':1000*buffer_error*current_factor,
                 'RISET_unchanged':True, 'EN1_EN2_USB100_unchanged':True},
        'CE': {'candidate_input_isolator':'SN74LVC1G14DCKR', 'tap_ohm':22000.,
               'assumed_observation_input_min_V':ce_source_min,
               'input_Imax_A':5e-6, 'off_Imax_A':10e-6,
               'disabled_CE_min_with_monitor_input_short_GND_V':ce_disabled_fault,
               'BQ_CE_VIH_V':1.4, 'buffer_VTplus_conservative_max_V':3.33, 'buffer_VTminus_conservative_min_V':.58,
               'buffer_high_input_min_V':ce_high_observed_min,
               'buffer_low_input_max_V':ce_low_observed_max,
               'meaning':'Inverting read-only path; monitoring faults cannot pull CE into enable under stated bounds. No firmware CE control.'},
        'CHG': {'tap_ohm':4700., 'initial_TCA_pullup_max_A':100e-6,
                'TCA_low_input_max_V':chg_low_max, 'TCA_VIL_min_supply_V':.3*vdd_min,
                'max_BQ_sink_A_with_wrong_TCA_high_output':chg_sink_fault,
                'BQ_VOL_test_current_A':.005},
        'ADC': {'input_filter_C_F':1e-9, 'input_tau_max_s':tau_max,
                'input_valid_delay_min_s':8*tau_max,
                'output_filter':{'R_ohm':1000.,'C_F':100e-9},
                'input_bias_error_max_mV':1000*bias_error,
                'TS_above_buffer_supply':'Saturation/invalid, not valid temperature; bounded injection through two taps still requires power-sequence/leakage acceptance.',
                'ADC_rails_unchanged':True, 'tip_pulsed_excitation_and_differential_MUX_preserved':True},
        'termination':termination, 'source_budget_candidates':cases,
        'radio_branch':{'limiter_setting_ohm':19200., 'drift_bound':tolerance,
                        'minimum_limit_mA':34/(1+tolerance), 'maximum_limit_mA':66/(1-tolerance),
                        'hard_allocation_mA':70., 'normal_target_max_mA':30.,
                        'response_max_us':5., 'FLT_not_current_limit_indicator':True},
        'unqualified':['resistor leakage/PCB contamination and isolation spacing','buffer overload/recovery and unpowered injection',
                       'actual trip shifts over received NTC and guard tolerances','ADC filter/MUX settling and estimator error',
                       '3.8V CE observation bound and all power sequences','radio startup/branch inrush/currentlimit transient',
                       '70% UV efficiency, maxIq and hot drops','changed UV optical/thermal dose'],
        'original_circuit_or_artwork_mutation':False, 'physical_validation':False}


if __name__ == '__main__':
    report = evaluate()
    (H/'fault-loading.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('CE','CHG','termination','source_budget_candidates')},indent=2))
