"""Recalculate the proposed 1.5 A dock budget from the saved radio schematic."""

import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree


HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "dock-safety" / "power-budget.json"
RADIO = HERE / "case-radio"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def current_ma(volts, ohms):
    return 1000 * volts / ohms


def main():
    binding = json.loads((RADIO / "source-bindings.json").read_text())
    check = json.loads((RADIO / "native-checks.json").read_text())
    netlist_path = RADIO / "case-radio-system-native.xml"
    assert sha256(netlist_path) == check["native_netlist_sha256"]
    assert sha256(RADIO / "source-bindings.json") == check["source_bindings_sha256"]
    for name, digest in binding["outputs_sha256"].items():
        assert sha256(RADIO / name) == digest, name
    native = ElementTree.parse(netlist_path)
    values = {part.get("ref"): part.findtext("value") for part in native.findall("./components/comp")}
    nets = {
        (pin.get("ref"), pin.get("pin")): net.get("name")
        for net in native.findall("./nets/net")
        for pin in net.findall("node")
    }
    expected_values = {
        "R107": "39.2k0.1%25ppm", "R401": "4.22ohm1%100ppm", "R501": "4.22ohm1%100ppm",
        "R150": "19k1", "R151": "100R", "R152": "100k", "R153": "10k", "R154": "100k",
        "R216": "4k7 ohm", "R217": "4k7 ohm", "R905": "1k", "R906": "4k7", "R907": "4k7",
        "U150": "TPS22950YBHR", "U151": "SN74LVC1G97DCKR", "U602": "TPS22919DCKR",
    }
    assert all(values[ref] == value for ref, value in expected_values.items())
    assert nets["U150", "B1"] == nets["U602", "5"] == "LOOP_5V"
    assert nets["U150", "A1"] == nets["U903", "11"] == "RADIO_ACTIVE_EN"
    assert nets["R153", "2"] == nets["U903", "9"] == "RADIO_IRQn"
    assert nets["R905", "2"] == nets["U903", "10"] == nets["U902", "11"] == "SC16_IRQn"

    base = json.loads(BASE.read_text())
    base_uv = base["UV_normal_design"]
    supply_resistance = base["UV_path_resistance"]
    device = base["device_qualified_allocation_mA"]
    ui = base["dock_UI_overhead_allocation_mA"]
    loop = base["contact_loops"]
    loops = loop["qualified_total_max_mA"]
    host_rail_max = 3.4
    # Worst simultaneous DC states. Existing I2C pulls are counted here as well
    # because the previous 10 mA allocation did not itemize bus pull-up current.
    general_resistor_margin = 0.01 + 100e-6 * 100
    host_items = {
        "R152_and_R154_high": 2 * current_ma(host_rail_max, 100_000 * (1 - general_resistor_margin)),
        "R153_IRQ_low": current_ma(host_rail_max, 10_000 * (1 - general_resistor_margin)),
        "R216_R217_I2C_low": 2 * current_ma(host_rail_max, 4_700 * (1 - general_resistor_margin)),
        "SN74LVC1G97_Icc_max": 0.010,
        "SN74LVC1G97_input_level_current_allowance": 1.0,
        "TPS22950_Iq_at_up_to_85C": 0.060,
        "TMUX_enable_input_and_power_off_leakage_allowance": 0.020,
    }
    # TI specifies the 34–66 mA interval at exactly 19.2 kΩ and a 0.5 V
    # switch drop. Inverse scaling is a small-tolerance screening estimate.
    precision_resistor_margin = 0.001 + 25e-6 * 100
    radio_limit_min = 34 / (1 + precision_resistor_margin)
    radio_limit_max = 66 / (1 - precision_resistor_margin)
    host_extra = sum(host_items.values())
    radio_allocation = 70.0

    # Preserve the inherited UV boost assumptions and substitute only R107
    # and the two emitter current set resistors from the native netlist.
    uv_limit_min = 25230 / (39.2 * (1 + precision_resistor_margin)) ** 1.016
    uv_limit_max = 22980 / (39.2 * (1 - precision_resistor_margin)) ** 0.94
    led_nominal = current_ma(0.2, 4.22)
    led_upper = current_ma(0.204, 4.22 * (1 - general_resistor_margin))
    uv_led_w = 2 * led_upper / 1000 * base_uv["Vout_ceiling_V"]
    uv_input = 1000 * (uv_led_w + base_uv["bleeder_and_divider_power_total_W"]) / (
        base_uv["efficiency_floor_assumption"] * base_uv["VIN_floor_V"]
    ) + base_uv["driver_Iq_total_mA"]
    normal_total = device + ui + loops + radio_allocation + uv_input
    worst_total = device + ui + loops + radio_allocation + uv_limit_max
    shared_drop = normal_total / 1000 * supply_resistance["common_PCB_supply_plus_return_max_ohm"]
    driver_floor = 4.5 - shared_drop - uv_input / 1000 * (
        supply_resistance["common_switch_Rmax_ohm"]
        + supply_resistance["each_branch_supply_plus_return_max_ohm"] / 2
    )
    # The radio and both wetting loops now share U602. Use the conservative
    # full 70 mA radio reservation as if it all passed through U602.
    loop_switch_drop = (loops + radio_allocation) / 1000 * 0.250
    loop_wetting_min = current_ma(
        4.5 - shared_drop - loop_switch_drop,
        loop["series_pull_ohm"] * (1 + loop["tolerance"]),
    )
    loop_external_resistance_budget = (
        (4.5 - shared_drop - loop_switch_drop) / 0.010
        - loop["series_pull_ohm"] * (1 + loop["tolerance"])
    )
    assert radio_limit_max + host_extra < radio_allocation
    assert uv_input < uv_limit_min and worst_total < 1500
    assert driver_floor >= base_uv["VIN_floor_V"] and loop_wetting_min >= 10

    report = {
        "scope": "Steady-state screening of the radio schematic and coupled UV resistor values",
        "input_hashes": {
            "calculator": sha256(Path(__file__)),
            "native_netlist": sha256(netlist_path),
            "radio_source_bindings": sha256(RADIO / "source-bindings.json"),
            "frozen_safety_budget": sha256(BASE),
        },
        "radio": {
            "combined_allocation_mA": radio_allocation,
            "host_items_mA": host_items,
            "host_items_sum_mA": host_extra,
            "switch_output_limit_at_resistor_corners_mA": [radio_limit_min, radio_limit_max],
            "arithmetic_margin_to_allocation_mA": radio_allocation - radio_limit_max - host_extra,
            "local_normal_load_acceptance_mA": 30.0,
        },
        "UV": {
            "all_four_emitters_retained": True,
            "limiter_mA": [uv_limit_min, uv_limit_max],
            "normal_input_mA": uv_input,
            "normal_margin_to_limiter_min_mA": uv_limit_min - uv_input,
            "each_LED_nominal_mA": led_nominal,
            "each_LED_upper_mA": led_upper,
            "normal_driver_input_floor_V": driver_floor,
        },
        "source": {
            "minimum_dock_input_V": 4.5,
            "qualified_current_mA": 1500,
            "normal_max_sum_mA": normal_total,
            "steady_limiter_sum_mA": worst_total,
            "margin_to_1p5A_mA": 1500 - worst_total,
            "loop_floor_each_mA_before_wiring_and_contact_loss": loop_wetting_min,
            "loop_remaining_ohms_for_10mA": loop_external_resistance_budget,
            "shared_board_drop_V": shared_drop,
            "shared_U602_drop_V": loop_switch_drop,
        },
        "primary_sources": {
            "TPS22950 current limit and IQ": "https://www.ti.com/lit/ds/symlink/tps22950.pdf",
            "TPS22919 worst on resistance at 3.6 V": "https://www.ti.com/lit/ds/symlink/tps22919.pdf",
            "TPS2553 ILIM equations": "https://www.ti.com/lit/ds/symlink/tps2553.pdf",
            "SN74LVC1G97 static ICC and ΔICC": "https://www.ti.com/lit/ds/symlink/sn74lvc1g97.pdf",
            "TMUX1511 powered-off leakage": "https://www.ti.com/lit/ds/symlink/tmux1511.pdf",
        },
        "assumptions": [
            "3.4 V host rail ceiling is a project bound to verify.",
            "The 1 mA transition allowance covers two SN74LVC1G97 inputs at the datasheet's individual ΔICC test point. It is an engineering allowance for the actual waveforms.",
            "The inverse resistor correction is a screening estimate near the TPS22950 19.2 kΩ test point.",
            "The 0.25 Ω U602 bound uses the lower 3.6 V test rail through 125°C. Harness and contact drops remain to measure.",
            "Existing 10 mA UI allocation and UV driver assumptions retain their original qualification conditions.",
        ],
        "bench_checks": [
            "Measure TPS22950 current limit, startup and short response with the actual C901/C902, harness and module.",
            "Confirm local radio current at or below 30 mA over supported modes and operating conditions.",
            "Measure aggregate source current with both UV branches and radio under normal load, inrush and faults.",
            "Measure wetting current through each complete switch loop while the radio starts and operates.",
            "Confirm the assumed common path resistance, boost efficiency, UV driver VIN and optical/thermal performance.",
            "Measure source-drop isolation, default USB current and suspend with the revised circuitry.",
        ],
        "physical_validation": False,
        "full_product_order_ready": False,
    }
    (RADIO / "power-screen.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"radio": report["radio"], "UV": report["UV"], "source": report["source"]}, indent=2))


if __name__ == "__main__":
    main()
