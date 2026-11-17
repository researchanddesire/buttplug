#!/usr/bin/env python3
"""Replay the Hall receiver's proposed passive feed and static electrical corners."""

import json
from itertools import product
from pathlib import Path


LINE_V = (4.40, 5.25)
FEED_OHM = 124.0
FEED_ERROR = .006
R107_KOHM = 41.7
R107_ERROR = .00451
FEED_SHUNT = (9.7, 10.3)
RETURN_SHUNT = (1.455, 1.545)
HEAD_CURRENT_A = .00410
SIGNATURE_RETURN_MAX_A = .00030
SIGNATURE_LEAKAGE_A = 20.05e-6
DIVIDER_ERROR = .0035
HEAD_QUOTED_DIVIDER_ERROR = .00851
PRECISION_DIVIDER_ERROR = .00451
POWER_WITNESS_TOP_OHM = 57_600
POWER_WITNESS_BOTTOM_OHM = 9760
HEAD_DIVIDER_TOP_OHM = 54_900
HEAD_DIVIDER_BOTTOM_OHM = 10_200
RECEIVER_ALLOCATION_MA = 2.0
CONTACT_LIMIT_ERROR = .00451
USB100_MAX_MA = 100.0


def tolerance(nominal, error):
    return nominal * (1 - error), nominal * (1 + error)


def limits(values):
    values = list(values)
    return min(values), max(values)


def voltage_divider_limits(top, bottom, reference, ratio_error, bias_a):
    return limits(
        ref * (1 + r_top / r_bottom) + bias * r_top
        for ref, r_top, r_bottom, bias in product(
            reference, tolerance(top, ratio_error), tolerance(bottom, ratio_error), (-bias_a, bias_a)
        )
    )


def current_amplifier_limits(shunt, current):
    return limits(
        gain * (resistance * amps + offset)
        for gain, resistance, amps, offset in product(
            tolerance(500, .005), shunt, current, (-40e-6, 40e-6)
        )
    )


def main_current_limits(divider_top):
    return limits(
        line * down / (top + down) + offset
        for line, top, down, offset in product(
            LINE_V, tolerance(divider_top, DIVIDER_ERROR),
            tolerance(1000, DIVIDER_ERROR), (-.006, .006)
        )
    )


def signature_limits():
    closed_v = []
    open_v = []
    signature_a = []
    open_sink_limit_a = []
    return_hi_v = (RETURN_SHUNT[1] + 2) * (HEAD_CURRENT_A + SIGNATURE_RETURN_MAX_A)
    resistor_corners = [tolerance(value, .02) for value in (10_000, 10_000, 10_000, 41_200, 10_000)]
    signature_ohm = (5620 * .98, 5620 * 1.02 + 7)
    # Round the calculated high threshold up before bounding a false valid code.
    conservative_sig_high_v = 2.133
    for line, bias, lt, lb, ht, hb, rs, ground, leakage in product(
        LINE_V, *resistor_corners, signature_ohm, (0, return_hi_v),
        (-SIGNATURE_LEAKAGE_A, SIGNATURE_LEAKAGE_A),
    ):
        conductance = 1 / bias + 1 / (lt + lb) + 1 / (ht + hb)
        drive = line / bias + leakage
        closed = (drive + ground / rs) / (conductance + 1 / rs)
        closed_v.append(closed)
        open_v.append(drive / conductance)
        signature_a.append((closed - ground) / rs)
        open_sink_limit_a.append(line / bias - conductance * conservative_sig_high_v)
    return limits(closed_v), limits(open_v), limits(signature_a), min(open_sink_limit_a)


def receiver_short_screen_mA(current_divider_scale):
    """Estimate receiver load for two shorted feeds with both thermal branches enabled."""
    high_line = LINE_V[1]
    # INA190 x2, TLV9022 x2 sections, TPS3710, TLV6700, TPS3701,
    # TPS3808 x2, INA300, TPS22918, and three rail-driven logic devices.
    active_a = (130 + 70 + 13 + 13 + 11 + 12 + 150 + 17 + 30) * 1e-6
    passive_a = high_line / (98_700 * .99)  # Thermal supervisor sense.
    for span in (40_200 * current_divider_scale, 11_700 * current_divider_scale, 100_900):
        passive_a += high_line / (span * (1 - PRECISION_DIVIDER_ERROR))
    pulls_a = 2 * high_line / (24_900 * .99)  # Hall window and RESET pullups.
    pulls_a += high_line / 70_000  # Hall supervisor MR internal pull-up.
    pulls_a += high_line / (157_300 * .99)  # Thermal enable network released.
    stage_input_leakage_a = 5e-6  # Per-channel allowance outside the divider model.
    return 2000 * (active_a + passive_a + pulls_a + stage_input_leakage_a)


def contact_limit_bounds(rlim_kohm):
    rlow, rhigh = tolerance(rlim_kohm, CONTACT_LIMIT_ERROR)
    return 25230 / rhigh ** 1.016, 22980 / rlow ** .94


def contact_limiter_screen(active_margin_mA, candidate_margin_mA, device_allocation_mA, contact_rise_v):
    """Screen a second TPS2553-Q1 in series with the existing U104 plug path."""
    # C1/C44 on the plug body and C106 on Main, with +10% initial and +15% X7R.
    # This excludes unmodeled distributed capacitance and input capacitance at U104.
    contact_caps_uF = (4.7 + .1 + .1) * 1.10 * 1.15
    full_slew_charge_uC = contact_caps_uF * LINE_V[1]
    added_drop_mV = .135 * USB100_MAX_MA
    remaining_drop_mV = 1000 * (4.50 - contact_rise_v) - added_drop_mV
    alternatives = {}
    for name, rlim_kohm, allocation_mA in (
        ('124_kohm', 124, 250.0), ('191_kohm', 191, 170.0), ('110_kohm_split', 110, 280.0),
    ):
        minimum_mA, maximum_mA = contact_limit_bounds(rlim_kohm)
        # Reserve 0.5 mA for contact-side loads outside the BQ24074.
        inrush_headroom_mA = minimum_mA - USB100_MAX_MA - .5
        recovered_mA = device_allocation_mA - allocation_mA
        alternatives[name] = {
            'current_limit_min_max_mA': (minimum_mA, maximum_mA),
            'allocation_mA': allocation_mA,
            'headroom_inside_allocation_mA': allocation_mA - maximum_mA,
            'inrush_headroom_under_DC_threshold_mA': inrush_headroom_mA,
            'full_slew_charge_over_headroom_ms': full_slew_charge_uC / inrush_headroom_mA,
            'active_R107_two_head_short_static_margin_mA': active_margin_mA + recovered_mA,
            'candidate_R107_two_head_short_static_margin_mA': candidate_margin_mA + recovered_mA,
            'pre_thermal_shutdown_at_hard_short_power_W': LINE_V[1] * maximum_mA / 1000,
        }
    # Two equal parallel strings, each two 110 kΩ resistors in series.
    one_resistor_shorted_mA = contact_limit_bounds(2 * 110 / 3)
    one_resistor_open_mA = contact_limit_bounds(2 * 110)
    short_allocation_mA = 410.0
    alternatives['110_kohm_split']['single_program_resistor_faults'] = {
        'one_short_limit_min_max_mA': one_resistor_shorted_mA,
        'one_open_limit_min_max_mA': one_resistor_open_mA,
        'one_short_allocation_mA': short_allocation_mA,
        'one_short_active_R107_static_margin_mA': active_margin_mA + device_allocation_mA - short_allocation_mA,
    }
    return {'original_device_allocation_mA': device_allocation_mA,
            'added_drop_max_mV_at_100mA': added_drop_mV,
            'remaining_drop_to_contact_release_at_4p5V_mV': remaining_drop_mV,
            'contact_side_capacitor_charge_screen_uC': full_slew_charge_uC,
            'startup_and_suspended_USB_verified': False,
            'alternatives': alternatives}


def check_corners():
    evt1 = Path(__file__).resolve().parents[2]
    source = evt1 / "case-telemetry-study/wired-main/circuit-contract.json"
    main_power = json.loads(source.read_text())["power"]
    baseline = main_power["wired_coexistence"]
    safety_budget = json.loads((evt1 / "dock-safety/power-budget.json").read_text())
    thermal_near_trip_increment_mA = 2 * (15.6109469697 - 12.3326286117 + .40)
    uv_max_mA = 22980 / (R107_KOHM * (1 - R107_ERROR)) ** .94
    uv_min_mA = 25230 / (R107_KOHM * (1 + R107_ERROR)) ** 1.016
    receiver_short_mA = receiver_short_screen_mA(1)
    receiver_short_scaled_mA = receiver_short_screen_mA(2)
    other_mA = (
        baseline["hard_source_total_mA"] - baseline["UV_limiter_max_mA"]
        + thermal_near_trip_increment_mA + RECEIVER_ALLOCATION_MA
    )
    feed_low, feed_high = tolerance(FEED_OHM, FEED_ERROR)
    bias_mA = 1000 * LINE_V[1] / 9800
    hard_short_a = LINE_V[1] / (3 * feed_low + FEED_SHUNT[0])
    stacked_short_a = LINE_V[1] / (2 * feed_low + FEED_SHUNT[0])
    shunt_short_a = LINE_V[1] / (3 * feed_low)
    two_short_margin_mA = 1500 - other_mA - uv_max_mA - 2000 * hard_short_a - 2 * bias_mA
    full_receiver_margin_mA = two_short_margin_mA + RECEIVER_ALLOCATION_MA - receiver_short_mA
    scaled_receiver_margin_mA = two_short_margin_mA + RECEIVER_ALLOCATION_MA - receiver_short_scaled_mA
    active_uv_max_increment_mA = baseline["UV_limiter_max_mA"] - uv_max_mA
    one_shunt_short_margin_mA = (
        1500 - other_mA - uv_max_mA - 1000 * (shunt_short_a + hard_short_a) - 2 * bias_mA
    )
    one_stacked_short_margin_mA = (
        1500 - other_mA - uv_max_mA - 1000 * (stacked_short_a + HEAD_CURRENT_A) - 2 * bias_mA
    )
    head_ref_fall = tolerance(.405, .02)
    head_ref_rise = (head_ref_fall[0] * 1.015, head_ref_fall[1] * 1.03)
    quoted_head_fall_v = voltage_divider_limits(
        53_600, 10_000, head_ref_fall, HEAD_QUOTED_DIVIDER_ERROR, 25e-9
    )
    head_release_max_v = voltage_divider_limits(
        HEAD_DIVIDER_TOP_OHM, HEAD_DIVIDER_BOTTOM_OHM, head_ref_rise, PRECISION_DIVIDER_ERROR, 25e-9
    )[1]
    head_drop_min_v = voltage_divider_limits(
        HEAD_DIVIDER_TOP_OHM, HEAD_DIVIDER_BOTTOM_OHM, head_ref_fall, PRECISION_DIVIDER_ERROR, 25e-9
    )[0]
    return_path_ohm = RETURN_SHUNT[1] + 2
    divider_budget_a = LINE_V[0] / (
        (POWER_WITNESS_TOP_OHM + POWER_WITNESS_BOTTOM_OHM) * (1 - PRECISION_DIVIDER_ERROR)
    ) + 25e-9
    startup_tap_v = LINE_V[0] - 3 * feed_high * (HEAD_CURRENT_A + divider_budget_a)
    loaded_head_v = (
        startup_tap_v - (FEED_SHUNT[1] + 3) * HEAD_CURRENT_A
        - return_path_ohm * (HEAD_CURRENT_A + SIGNATURE_RETURN_MAX_A)
    )
    feed_monitor_rising_max_v = voltage_divider_limits(
        POWER_WITNESS_TOP_OHM, POWER_WITNESS_BOTTOM_OHM, (.396, .404), PRECISION_DIVIDER_ERROR, 25e-9
    )[1]
    feed_monitor_min_v = voltage_divider_limits(
        POWER_WITNESS_TOP_OHM, POWER_WITNESS_BOTTOM_OHM, (.387, .400), PRECISION_DIVIDER_ERROR, 25e-9
    )[0]
    sig_ceiling_v = voltage_divider_limits(41_200, 10_000, (.397, .403), .02, 25e-9)[1]
    bridged_feed_max_v = sig_ceiling_v + stacked_short_a * FEED_SHUNT[1] + .020
    max_head_divider_ohm = max(
        63_600 * (1 + HEAD_QUOTED_DIVIDER_ERROR),
        (HEAD_DIVIDER_TOP_OHM + HEAD_DIVIDER_BOTTOM_OHM) * (1 + PRECISION_DIVIDER_ERROR),
    )
    min_head_bleed_a = (2.50 - .002) / max_head_divider_ohm - 25e-9
    intact_feed_min_v = current_amplifier_limits(FEED_SHUNT, (min_head_bleed_a,) * 2)[0]
    open_feed_max_v = current_amplifier_limits(FEED_SHUNT, (0, 10e-6 + 3e-9))[1]
    feed_trip = main_current_limits(39_200)
    sig_closed, sig_open, sig_current, sig_open_sink_limit_a = signature_limits()
    # The normal loaded SIG branch and divider establish the minimum without
    # a minimum ICC guarantee from the Hall switch or the logic device.
    return_min_a = sig_current[0] + min_head_bleed_a
    return_max_a = HEAD_CURRENT_A + SIGNATURE_RETURN_MAX_A
    closed_return = current_amplifier_limits(RETURN_SHUNT, (return_min_a, return_max_a))
    return_trip = main_current_limits(39_200)
    open_return_max_v = current_amplifier_limits(RETURN_SHUNT, (0, 10e-6 + 3e-9))[1]
    return_high_min_v = voltage_divider_limits(
        90_900, 10_000, (.387, .400), PRECISION_DIVIDER_ERROR, 25e-9
    )[0]
    return_high_max_v = voltage_divider_limits(
        90_900, 10_000, (.396, .404), PRECISION_DIVIDER_ERROR, 25e-9
    )[1]
    return_limit_a = (return_high_max_v / (500 * .995) + 40e-6) / RETURN_SHUNT[0]
    feed_drop_ohm = FEED_SHUNT[1] + 3
    remote_witness_drop_v = feed_monitor_min_v - (feed_drop_ohm + return_path_ohm) * return_limit_a
    # Independent of the high-return amplifier if the only extra power at
    # the head is the maximum possible SIG pull-up current.
    sig_fault_a = LINE_V[1] / 9800
    feed_at_sensor_floor_a = (
        LINE_V[1] - 2.50 - return_path_ohm * sig_fault_a
    ) / (3 * feed_low + feed_drop_ohm + return_path_ohm)
    tap_at_sensor_floor_v = LINE_V[1] - 3 * feed_low * feed_at_sensor_floor_a
    passive_witness_floor_v = (
        feed_monitor_min_v
        - (feed_drop_ohm + return_path_ohm) * (LINE_V[1] - feed_monitor_min_v) / (3 * feed_low)
        - return_path_ohm * sig_fault_a
    )
    bypassed_limiter_witness_floor_v = (
        feed_monitor_min_v
        - (feed_drop_ohm + return_path_ohm) * (LINE_V[1] - feed_monitor_min_v) / (2 * feed_low)
        - return_path_ohm * sig_fault_a
    )

    return {
        "model_only": True,
        "low_line_head_max_assumed_load_mA": 1000 * HEAD_CURRENT_A,
        "low_line_min_head_V": loaded_head_v,
        "aged_head_release_max_V": head_release_max_v,
        "aged_head_drop_min_V": head_drop_min_v,
        "quoted_head_aged_drop_min_V": quoted_head_fall_v[0],
        "head_start_DC_margin_mV": 1000 * (loaded_head_v - head_release_max_v),
        "main_witness_start_DC_margin_mV": 1000 * (startup_tap_v - feed_monitor_rising_max_v),
        "main_witness_falling_min_V": feed_monitor_min_v,
        "main_witness_remote_floor_with_passive_feed_only_V": passive_witness_floor_v,
        "main_witness_remote_floor_with_one_limiter_bypassed_V": bypassed_limiter_witness_floor_v,
        "main_witness_remote_floor_with_return_guard_V": remote_witness_drop_v,
        "main_witness_remote_cutoff_margin_with_passive_feed_only_mV": (
            1000 * (feed_monitor_min_v - tap_at_sensor_floor_v)
        ),
        "UV_min_margin_mA": uv_min_mA - baseline["UV_input_required_mA"],
        "active_R107_provisional_two_head_short_margin_mA": two_short_margin_mA - active_uv_max_increment_mA,
        "two_head_short_source_margin_mA": two_short_margin_mA,
        "receiver_two_head_short_static_screen_mA": receiver_short_mA,
        "two_head_short_margin_with_receiver_screen_mA": full_receiver_margin_mA,
        "receiver_two_head_short_double_divider_impedance_screen_mA": receiver_short_scaled_mA,
        "two_head_short_margin_with_double_divider_impedance_screen_mA": scaled_receiver_margin_mA,
        "contact_limiter_screen": contact_limiter_screen(
            full_receiver_margin_mA - active_uv_max_increment_mA,
            full_receiver_margin_mA,
            safety_budget["device_qualified_allocation_mA"],
            main_power["contact_voltage_monitor"]["rising_estimated_upper_V"],
        ),
        "one_shunt_short_plus_two_head_shorts_source_margin_mA": one_shunt_short_margin_mA,
        "one_limiter_short_plus_one_head_short_source_margin_mA": one_stacked_short_margin_mA,
        "one_limiter_short_plus_two_head_shorts_source_margin_mA": (
            two_short_margin_mA - 1000 * (stacked_short_a - hard_short_a)
        ),
        "maximum_feed_short_mA": 1000 * hard_short_a,
        "maximum_stacked_feed_short_mA": 1000 * stacked_short_a,
        "maximum_surviving_limiter_power_mW": 1000 * stacked_short_a ** 2 * feed_high,
        "feed_to_SIG_short_guard_mV": 1000 * (feed_monitor_min_v - bridged_feed_max_v),
        "intact_closed_SIG_V": sig_closed,
        "open_SIG_V": sig_open,
        "minimum_sink_to_reach_open_SIG_high_cut_uA": 1e6 * sig_open_sink_limit_a,
        "minimum_additional_sink_to_reach_open_SIG_high_cut_uA": (
            1e6 * (sig_open_sink_limit_a - SIGNATURE_LEAKAGE_A)
        ),
        "closed_signature_current_mA": tuple(value * 1000 for value in sig_current),
        "minimum_intact_feed_guard_mV": 1000 * (intact_feed_min_v - feed_trip[1]),
        "maximum_open_feed_guard_mV": 1000 * (feed_trip[0] - open_feed_max_v),
        "minimum_closed_return_guard_mV": 1000 * (closed_return[0] - return_trip[1]),
        "maximum_open_return_guard_mV": 1000 * (return_trip[0] - open_return_max_v),
        "maximum_normal_return_guard_mV": 1000 * (return_high_min_v - closed_return[1]),
    }


if __name__ == "__main__":
    print(json.dumps(check_corners(), indent=2))
