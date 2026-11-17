"""Derive a single-PCB schematic from the active EVT1 plug sources."""

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import uuid

HERE = Path(__file__).resolve().parent
EVT = HERE.parent
ROOT = HERE.parents[3]
FLANGE = EVT / "single-flange-routing"
PROJECT = "compass-one-board"
NAMESPACE = uuid.UUID("1893dfec-ce07-494c-8f40-fd22461b345a")
sys.path.insert(0, str(ROOT / "tools"))

import electronics_r0_generate as g
import kicad_sexp as s
from build_evt1_electrical import append_sheet, patch_pin_label, remove_component

Q = json.dumps
SOURCES = (
    ("Power path and 3V3", EVT / "body/01-power.kicad_sch", "01-power"),
    ("Motor and hardware inhibit", EVT / "body/02-motor.kicad_sch", "02-motor"),
    ("Radio, MCU and controls", FLANGE / "sheets/03-control.kicad_sch", "03-control"),
    ("Tip and pack temperature ADC", EVT / "body/04-sensors.kicad_sch", "04-analog-sensors"),
    ("Independent hardware charge guard", EVT / "body/05-charge-guard.kicad_sch", "05-charge-guard"),
    ("USB and contact protection", FLANGE / "sheets/01-power.kicad_sch", "06-contact-protection"),
    ("Hard reset and ROM recovery", FLANGE / "sheets/07-recovery.kicad_sch", "07-recovery"),
    ("Compass and local decoupling", FLANGE / "sheets/08-compass.kicad_sch", "08-compass"),
    ("Four fixed targets", FLANGE / "sheets/04-targets.kicad_sch", "09-fixed-targets"),
    ("Tip thermistor / off PCB", EVT / "external-04-sensors.kicad_sch", "10-remote-tip"),
    ("Pack hardware thermistors / off PCB", EVT / "external-05-charge-guard.kicad_sch", "11-remote-pack-guards"),
)
PACK_MON = "PACK_MON_NTC"
R88 = {"mpn": "TNPW040210K0BEED", "value": "10k 0.1%", "footprint": "EVT1:R_0402_1005Metric",
       "source": "https://www.vishay.com/docs/28758/tnpw_e3.pdf"}
C88 = {"mpn": "GRM155R71H103KA88D", "value": "10nF 50V X7R", "footprint": "EVT1:C_0402_1005Metric",
       "source": "https://www.murata.com/en-global/api/pdfdownloadapi?cate=luCeramicCapacitorsSMD&partno=GRM155R71H103KA88%23"}
J8 = {"mpn": "SM02B-SRSS-TB(LF)(SN)", "value": "PACK MONITOR NTC / GND",
      "footprint": "PrototypeR0:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal",
      "source": "https://www.jst-mfg.com/product/pdf/eng/eSH.pdf"}
TH3 = {"mpn": "NTCLE413E2103F524A", "value": "NTCLE413E2103F524A", "footprint": "",
       "source": "https://www.vishay.com/docs/29078/ntcle413.pdf"}
SELECTION = {"R88": R88, "C88": C88, "J8": J8, "TH3": TH3}
OPTIONAL_SYS_BULK = {
    "C12": "Leave empty on the first article. Footprint retained for U2 SYS bulk tuning.",
    "C22": "Leave empty on the first article. Footprint retained for U3 SYS bulk tuning.",
}
SOURCE_SUBSTITUTIONS = {
    "C1": {
        "replaces": "4.7uF 10V X7R",
        "value": "4.7uF 16V X7R",
        "mpn": "GRM21BR71C475KE51L",
        "jlc": "C408144",
        "source": "https://ds.murata.com/simsurfing/mlcc.html?partnumbers=%5B%22GRM21BR71C475KE51%22%5D",
        "note": "0805 X7R 4.7uF +/-10%, 16V. Confirm 1.40mm maximum installed height. Verify C1 biased input bypass and contact inrush, and C2 BAT bias and battery simulator transients with JP1 open.",
    },
    "C2": {
        "replaces": "4.7uF 10V",
        "value": "4.7uF 16V X7R",
        "mpn": "GRM21BR71C475KE51L",
        "jlc": "C408144",
        "source": "https://ds.murata.com/simsurfing/mlcc.html?partnumbers=%5B%22GRM21BR71C475KE51%22%5D",
        "note": "0805 X7R 4.7uF +/-10%, 16V. Confirm 1.40mm maximum installed height. Verify C1 biased input bypass and contact inrush, and C2 BAT bias and battery simulator transients with JP1 open.",
    },
    "C3": {
        "replaces": "10uF 10V",
        "value": "4.7uF 16V X7R",
        "mpn": "GRM21BR71C475KE51L",
        "jlc": "C408144",
        "source": "https://ds.murata.com/simsurfing/mlcc.html?partnumbers=%5B%22GRM21BR71C475KE51%22%5D",
        "note": "Local BQ24074 OUT bypass. With C12 and C22 empty the shared SYS bank is 44.7uF nominal. Verify SYS at USB100 startup and during converter load steps.",
    },
    "C51": {
        "replaces": "10uF 10V X5R 0603 HF",
        "value": "10uF 10V X5R 0603 HF",
        "mpn": "CL10A106KP8NNNC",
        "jlc": "C19702",
        "source": "https://weblib.samsungsem.com/mlcc/mlcc-ec-data-sheet.do?partNumber=CL10A106KP8NNN",
        "note": "0603 X5R 10uF +/-10%, 10V, 0.90mm maximum. Local HF bypass beside the regulator and PGND. At 25C, typical after bias is 4.43uF at 3.3V, 3.97uF at 3.68V and 3.28uF at 4.4V. Verify installed bulk plus HF capacitance, startup and load-step behavior.",
    },
    "C52": {
        "replaces": "10uF 10V X5R 0603 HF",
        "value": "10uF 10V X5R 0603 HF",
        "mpn": "CL10A106KP8NNNC",
        "jlc": "C19702",
        "source": "https://weblib.samsungsem.com/mlcc/mlcc-ec-data-sheet.do?partNumber=CL10A106KP8NNN",
        "note": "0603 X5R 10uF +/-10%, 10V, 0.90mm maximum. Local HF bypass beside the regulator and PGND. At 25C, typical after bias is 4.43uF at 3.3V, 3.97uF at 3.68V and 3.28uF at 4.4V. Verify installed bulk plus HF capacitance, startup and load-step behavior.",
    },
    "C53": {
        "replaces": "10uF 10V X5R 0603 HF",
        "value": "10uF 10V X5R 0603 HF",
        "mpn": "CL10A106KP8NNNC",
        "jlc": "C19702",
        "source": "https://weblib.samsungsem.com/mlcc/mlcc-ec-data-sheet.do?partNumber=CL10A106KP8NNN",
        "note": "0603 X5R 10uF +/-10%, 10V, 0.90mm maximum. Local HF bypass beside the regulator and PGND. At 25C, typical after bias is 4.43uF at 3.3V, 3.97uF at 3.68V and 3.28uF at 4.4V. Verify installed bulk plus HF capacitance, startup and load-step behavior.",
    },
    "C54": {
        "replaces": "10uF 10V X5R 0603 HF",
        "value": "10uF 10V X5R 0603 HF",
        "mpn": "CL10A106KP8NNNC",
        "jlc": "C19702",
        "source": "https://weblib.samsungsem.com/mlcc/mlcc-ec-data-sheet.do?partNumber=CL10A106KP8NNN",
        "note": "0603 X5R 10uF +/-10%, 10V, 0.90mm maximum. Local HF bypass beside the regulator and PGND. At 25C, typical after bias is 4.43uF at 3.3V, 3.97uF at 3.68V and 3.28uF at 4.4V. Verify installed bulk plus HF capacitance, startup and load-step behavior.",
    },
    "C33": {
        "replaces": "1uF",
        "value": "1uF",
        "mpn": "CGA3E1X7R1V105KT000N",
        "jlc": "C342956",
        "source": "https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=CGA3E1X7R1V105KT000N",
        "note": "TDK 0603 X7R 1uF +/-10%, 35V and 0.90mm maximum. Verify biased capacitance, MCU_EN reset pulse and ROM recovery timing on the assembled board.",
    },
    "R1": {
        "replaces": "8.87k 1% / ~100mA",
        "value": "8.87k 1% / ~100mA",
        "mpn": "TC0210B8871TCC",
        "jlc": "C517790",
        "source": "https://datasheet.lcsc.com/datasheet/pdf/d0d02de47642fe4f4639912f1a5cccad.pdf?productCode=C517790",
        "note": "Fit the 0402 +/-0.1%, +/-10 ppm/K selection to preserve ISET resistance margin. The schematic value is the inherited circuit label; use the exact MPN for assembly.",
    },
    "R2": {
        "replaces": "3.24k 1%",
        "value": "3.24k 1%",
        "mpn": "RT0402BRD073K24L",
        "jlc": "C852760",
        "source": "https://yageogroup.com/component-documentation/download/specsheet/RT0402BRD073K24L",
        "note": "0402 thin film, +/-0.1%, +/-25 ppm/K. Preserve the current-limit resistor value and USB100 straps.",
    },
    "R75": {
        "replaces": "22R",
        "value": "22R",
        "mpn": "RC0402FR-0722RL",
        "jlc": "C114765",
        "source": "https://yageogroup.com/component-documentation/download/specsheet/RC0402FR-0722RL",
        "note": "Fit both USB series positions with the same Yageo 0402 22ohm +/-1% part. Verify USB enumeration, ROM recovery and transfers through assembled dock contacts.",
    },
    "R76": {
        "replaces": "22R",
        "value": "22R",
        "mpn": "RC0402FR-0722RL",
        "jlc": "C114765",
        "source": "https://yageogroup.com/component-documentation/download/specsheet/RC0402FR-0722RL",
        "note": "Fit both USB series positions with the same Yageo 0402 22ohm +/-1% part. Verify USB enumeration, ROM recovery and transfers through assembled dock contacts.",
    },
    "R11": {
        "replaces": "312k 0.1%",
        "value": "312k 0.1%",
        "mpn": "RT0603BRD07312KL",
        "jlc": "C861315",
        "source": "https://www.digikey.ca/en/products/detail/yageo/RT0603BRD07312KL/5927923",
        "note": "Exact 312k ratio preserved with 0603 thin film +/-0.1%, +/-25ppm/K, 0.55mm maximum. Verify cold-start and regulated 3V3 under the normal power sources.",
    },
    "R43": {
        "replaces": "715k 0.1%",
        "value": "715k 0.1%",
        "mpn": "PTFR0805B715KP9",
        "jlc": "C2849329",
        "source": "https://s.resistor.today/shop/products/epdf/PTFR.pdf",
        "footprint": "Selected:RESI_PTFR0805_C16003",
        "note": "Exact 715k hot guard resistor, 0805 +/-0.1%, +/-25 ppm/K. Verify both thermal guard trips before closing JP1.",
    },
    "R21": {
        "replaces": "362k 0.1%",
        "value": "360k 0.1%",
        "mpn": "PTFR0805B360KN9",
        "jlc": "C351576",
        "source": "https://s.resistor.today/shop/products/epdf/PTFR.pdf",
        "footprint": "Selected:RESI_PTFR0805_C16003",
        "note": "0805 thin film 360k +/-0.1%, +/-10 ppm/K. With R22 at 100k, nominal MOTOR_3V7 is 3.680V. Check loaded motor voltage and first-pulse behavior.",
    },
    "R45": {
        "replaces": "200k 0.1%",
        "value": "200k 0.1%",
        "mpn": "ERA3AEB204V",
        "jlc": "C473261",
        "source": "https://industrial.panasonic.com/ww/products/pt/high-precision-chip-resistors/models/ERA3AEB204V",
        "note": "0603 thin film 200k +/-0.1%, +/-25 ppm/K. Verify both thermal guard trips before closing JP1.",
    },
    "R46": {
        "replaces": "11k 1%",
        "value": "11k 1%",
        "mpn": "RT0402BRD0711KL",
        "jlc": "C705064",
        "source": "https://yageogroup.com/component-documentation/download/specsheet/RT0402BRD0711KL",
        "note": "0402 thin film 11k +/-0.1%, +/-25 ppm/K. The dock-powered pull-up stays above 10k; no change to the guard permission logic.",
    },
    "C83": {
        "replaces": "22uF 10V / Ceff>=10uF at3V3",
        "value": "47uF 10V / Ceff>=10uF at3V3",
        "mpn": "MSASL21GBB5476MTNA01", "jlc": "C386058",
        "source": "https://ds.yuden.co.jp/TYCOMPAS/or/detail?pn=MSASL21GBB5476MTNA01&u=M",
        "note": "Same 0805 footprint and maximum package envelope. Accept at least 10uF effective at 3.3V over operating temperature and aging. Measure startup and 3V3 stability through the retained TPS63070/USB100 power path.",
    },
    "U6": {
        "replaces": "ESP32-C3-MINI-1-N4X candidate",
        "mpn": "ESP32-C3-MINI-1-H4X", "jlc": "C41349510",
        "source": "https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.html",
        "note": "Same 4 MB flash, silicon v1.1, module dimensions and recommended 53-pad land pattern. H4X extends the module ambient upper range to 105°C.",
    },
    "U9": {
        "replaces": "TPS3808G33DBVR",
        "mpn": "TPS3808G33QDBVRQ1", "jlc": "C414616",
        "source": "https://www.ti.com/lit/ds/symlink/tps3808-q1.pdf",
        "note": "Same DBV pin map, 3.07 V threshold and open-CT delay. VDD is VBUS_CHG, SENSE is 3V3. The automotive VDD operating floor is 1.8 V, below the BQ24074 input UVLO. JP1 ships open. Qualify CE isolation on VBUS/3V3 startup and brownout before closing JP1.",
    },
}


def identity(name):
    return str(uuid.uuid5(NAMESPACE, name))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add_property(symbol, name, value):
    x, y = [atom.value for atom in s.child(symbol, "at")[1:3]]
    symbol.append(s.parse(f'(property {Q(name)} {Q(value)} (at {x} {y} 0) '
                          '(effects (font (size 1.27 1.27)) hide))'))


def set_property(symbol, name, value):
    prop = next(field for field in s.children(symbol, "property") if field[1].value == name)
    prop[2] = s.string(value)


def schematic_additions():
    """Generate the new two-wire input and its off-board thermistor."""
    g.LIB.clear()
    g.PARTS.clear()
    g.PROJECT = PROJECT
    g.passive("R", "R")
    g.passive("C", "C")
    g.connector("Conn2", 2)
    g.passive("NTC", "R")
    # The cached NTC symbol comes from the matching hardware pack sensor sheet.
    g.LIB["NTC"]["source"] = TH3["source"]
    with tempfile.TemporaryDirectory(prefix="compass-one-board-") as temporary:
        g.OUT = Path(temporary)
        readout = g.Sheet("pack-input-fragment", "Pack temperature input")
        readout.part("R", "R88", R88["value"], 157.48, 154.94,
                     {"1": "TIP_EXC_EN", "2": PACK_MON}, R88["footprint"],
                     note="Pack monitor excitation from the existing GPIO10 pulse")
        readout.part("C", "C88", C88["value"], 218.44, 154.94,
                     {"1": PACK_MON, "2": "GND"}, C88["footprint"])
        readout.part("Conn2", "J8", J8["value"], 292.1, 99.06,
                     {"1": PACK_MON, "2": "GND"}, J8["footprint"],
                     note="Two-wire dry pack monitor. JST SH2 horizontal. Sensor return separate from power wiring.")
        readout.note("GPIO10 drives tip and diagnostic pack dividers; pulse only for settled conversions.\n"
                     "AIN0 = tip, AIN1 = half excitation, AIN2 = pack monitor, AIN3 = GND.\n"
                     "R = 10 kΩ × input / (2 × AIN1 − input), using bracketing reference reads.\n"
                     "Hardware charge limits stay on the independent BQ24074 TS and comparator sensor pairs.\n"
                     "Open/short/unavailable readings are invalid. Pack monitor grants no charge permission.",
                     40.64, 205.74)
        readout.save()
        readout_tree = s.parse((g.OUT / "pack-input-fragment.kicad_sch").read_text())
        remote = g.Sheet("12-remote-pack-monitor", "Battery temperature monitor / off PCB")
        remote.part("NTC", "TH3", TH3["value"], 76.2, 63.5,
                    {"1": PACK_MON, "2": "GND"}, note="Dry cell-coupled thermistor to J8. Diagnostic only.",
                    domain="REMOTE_PACK_MON")
        remote.note("Dedicated battery thermistor. Both existing hardware charge sensors remain separate.\n"
                    "Keep TH3 against the protected pack in the dry cavity; qualify mounting and thermal bias.",
                    25.4, 111.76)
        remote.save()
        remote_tree = s.parse((g.OUT / "12-remote-pack-monitor.kicad_sch").read_text())
    for tree in (readout_tree, remote_tree):
        for symbol in s.children(tree, "symbol"):
            details = SELECTION[s.prop(symbol, "Reference")]
            set_property(symbol, "Datasheet", details["source"])
            add_property(symbol, "Manufacturer Part Number", details["mpn"])
    return readout_tree, remote_tree


def mark_project(tree, instance, project=PROJECT):
    for symbol in s.children(tree, "symbol"):
        ref = s.prop(symbol, "Reference")
        unit = s.value(symbol, "unit") or "1"
        previous = s.child(symbol, "instances")
        if previous is not None:
            symbol.remove(previous)
        symbol.append(s.parse(
            f'(instances (project {Q(project)} (path {Q(instance)} (reference {Q(ref)}) (unit {unit}))))'))


def root_schematic(entries):
    identity_root = identity(PROJECT)
    root = s.parse(f'''(kicad_sch (version 20230121) (generator compass_one_board) (uuid {identity_root})
        (paper "A3") (title_block (title "Compass / single flange PCB") (date "2026-11-16")
        (rev "EVT one-board candidate") (company "Research and Desire")
        (comment 1 "ENGINEERING CANDIDATE - BENCH QUALIFICATION REQUIRED"))
        (lib_symbols) (sheet_instances (path "/" (page "1"))))''')
    for i, (label, basename, sheet_id) in enumerate(entries):
        append_sheet(root, label, f"sheets/{basename}.kicad_sch", sheet_id,
                     25.4 + 172.72 * (i % 2), 35.56 + 38.1 * (i // 2))
        sheet = s.children(root, "sheet")[-1]
        size = s.child(sheet, "size")
        size[1] = s.atom("129.54")
    return root


def write_libraries(trees):
    definitions = {}
    for tree in trees.values():
        for source_symbol in s.children(s.child(tree, "lib_symbols"), "symbol"):
            name = source_symbol[1].value
            assert name.startswith("PrototypeR0:"), name
            key = name.split(":", 1)[1]
            symbol = deepcopy(source_symbol)
            symbol[1] = s.string(key)
            if key in definitions:
                assert s.dump(definitions[key]) == s.dump(symbol), key
            definitions[key] = symbol
    library = s.parse("(kicad_symbol_lib (version 20220914) (generator compass_one_board))")
    library.extend(definitions[key] for key in sorted(definitions))
    s.write(HERE / "PrototypeR0.kicad_sym", library)
    (HERE / "sym-lib-table").write_text((FLANGE / "sym-lib-table").read_text())
    footprint_table = (FLANGE / "fp-lib-table").read_text().replace(
        '${KIPRJMOD}/Selected.pretty', '${KIPRJMOD}/../single-flange-routing/Selected.pretty')
    (HERE / "fp-lib-table").write_text(footprint_table)


def write_project():
    destination = HERE / f"{PROJECT}.kicad_pro"
    if destination.exists():
        return
    settings = json.loads((FLANGE / "single-flange-system.kicad_pro").read_text())
    settings["meta"]["filename"] = destination.name
    (destination).write_text(json.dumps(settings, indent=2) + "\n")


def build():
    readout, remote = schematic_additions()
    trees = {}
    bindings = {}
    entries = []
    for label, source, basename in SOURCES:
        tree = s.parse(source.read_text())
        bindings[str(source.relative_to(ROOT))] = sha(source)
        if basename == "04-analog-sensors":
            remove_component(tree, "J81")
            patch_pin_label(tree, "U7", 6, PACK_MON)
            for note in s.children(tree, "text"):
                if "interboard pin10" in note[1].value:
                    tree.remove(note)
            # Existing symbols keep exact definitions and pin IDs; new parts are
            # standard source-matched R/C/Conn2 symbols already on this sheet.
            existing = {node[1].value for node in s.children(s.child(tree, "lib_symbols"), "symbol")}
            assert {node[1].value for node in s.children(s.child(readout, "lib_symbols"), "symbol")} <= existing
            tree.extend(node for node in readout if s.tag(node) in {"symbol", "wire", "global_label", "text"})
        for symbol in s.children(tree, "symbol"):
            ref = s.prop(symbol, "Reference")
            if ref == "JP1":
                # The open solder jumper is copper artwork and consumes no BOM part.
                s.child(symbol, "in_bom")[1] = s.atom("no")
            if ref in OPTIONAL_SYS_BULK:
                s.child(symbol, "in_bom")[1] = s.atom("no")
                add_property(symbol, "AssemblyPopulation", OPTIONAL_SYS_BULK[ref])
            if ref in SOURCE_SUBSTITUTIONS:
                selection = SOURCE_SUBSTITUTIONS[ref]
                assert s.prop(symbol, "Value") == selection["replaces"], ref
                set_property(symbol, "Value", selection.get("value", selection["mpn"]))
                set_property(symbol, "Datasheet", selection["source"])
                set_property(symbol, "ReviewNote", selection["note"])
                if "footprint" in selection:
                    set_property(symbol, "Footprint", selection["footprint"])
                add_property(symbol, "Manufacturer Part Number", selection["mpn"])
                add_property(symbol, "LCSC Part Number", selection["jlc"])
        trees[basename] = tree
        entries.append((label, basename, identity(basename)))
    basename = "12-remote-pack-monitor"
    # Same Vishay part and cached symbol as the existing hardware guard pair.
    original_ntc = next(node for node in s.children(s.child(trees["11-remote-pack-guards"], "lib_symbols"), "symbol")
                        if node[1].value == "PrototypeR0:NTC")
    cached = s.child(remote, "lib_symbols")
    cached[1] = deepcopy(original_ntc)
    trees[basename] = remote
    entries.append(("Pack diagnostic thermistor / off PCB", basename, identity(basename)))
    (HERE / "sheets").mkdir(exist_ok=True)
    for _, basename, sheet_id in entries:
        tree = trees[basename]
        mark_project(tree, f"/{identity(PROJECT)}/{sheet_id}")
        s.write(HERE / "sheets" / f"{basename}.kicad_sch", tree)
    s.write(HERE / f"{PROJECT}.kicad_sch", root_schematic(entries))
    write_libraries(trees)
    write_project()
    for name in ("body/06-interboard.kicad_sch", "single-flange-routing/sheets/06-interboard.kicad_sch"):
        bindings[str((EVT / name).relative_to(ROOT))] = sha(EVT / name)
    manifest = {
        "scope": "Single device PCB candidate. Read-only source masters.",
        "source_sha256": bindings,
        "removed": {"J6": "body interboard", "J7": "flange interboard", "J81": "retired discrete compass harness"},
        "selected_additions": SELECTION,
        "source_substitutions": SOURCE_SUBSTITUTIONS,
        "source_metadata_changes": {
            "JP1": "exclude from BOM; retain open copper jumper on PCB",
            **OPTIONAL_SYS_BULK,
        },
        "telemetry": {"adc": "U7 ADS1115 / 0x48 / AIN2 pin 6 / MUX 110",
                      "reference": "U7 AIN1 pin 5 / TIP_EXC_HALF",
                      "unused": "U7 AIN3 pin 7 remains grounded",
                      "excitation": "U6 GPIO10 module pin 16 / TIP_EXC_EN high only for conversions",
                      "sense_net": PACK_MON, "J8": {"1": PACK_MON, "2": "GND"},
                      "dnp": [], "hardware_charge_permission": "independent existing circuits"},
    }
    (HERE / "schematic-source-bindings.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    build()
