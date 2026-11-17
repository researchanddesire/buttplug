"""Build the native contact adapter schematic and local KiCad libraries."""

from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import electronics_r0_generate as drawing
import kicad_sexp as sexp

NAME = "compass-direct-pc-adapter"
LIBRARY = "ContactAdapter"
TI = "https://www.ti.com/lit/ds/symlink/"
KICAD = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")
BENCH = HERE.parent / "one-board-dev"
USB = "USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal"
PH = "JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical"
R = "R_0603_1608Metric"
C = "C_0603_1608Metric"

# Stock IDs are selections for a quote. Check stock and the exact manufacturer
# line when creating the order.
PARTS = (
    ("J1", "USB4105", "USB4105-GF-A-120", USB, (55.88, 53.34),
     {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND",
      "A4": "PC_5V", "A9": "PC_5V", "B4": "PC_5V", "B9": "PC_5V",
      "A5": "CC1", "B5": "CC2", "A6": "PC_DP", "B6": "PC_DP",
      "A7": "PC_DM", "B7": "PC_DM"}, "GCT", "USB4105-GF-A-120", "C5184243"),
    ("J2", "Contacts", "J94 output", PH, (345.44, 53.34),
     {"1": "GND", "2": "CONTACT_DM", "3": "CONTACT_DP", "4": "CONTACT_5V"},
     "JST", "B4B-PH-K(LF)(SN)", "C265289"),
    ("U1", "TPS2553", "TPS2553QDBVRQ1", "SOT-23-6", (144.78, 55.88),
     {"1": "PC_5V", "2": "GND", "3": "PC_5V", "5": "ILIM", "6": "LIMIT_5V"},
     "Texas Instruments", "TPS2553QDBVRQ1", "C130055"),
    ("U2", "LM66100", "LM66100DCKR", "SOT-363_SC-70-6", (233.68, 55.88),
     {"1": "LIMIT_5V", "2": "GND", "3": "CONTACT_5V", "6": "CONTACT_5V"},
     "Texas Instruments", "LM66100DCKR", "C2869734"),
    ("U3", "TPS7A20", "TPS7A2033PDBVR", "SOT-23-5", (64.77, 139.70),
     {"1": "PC_5V", "2": "GND", "3": "PC_5V", "5": "ADAPTER_3V3"},
     "Texas Instruments", "TPS7A2033PDBVR", "C2862740"),
    ("U4", "TPS3808", "TPS3808G09DBVR", "SOT-23-6", (189.23, 137.16),
     {"1": "VBUS_VALID", "2": "GND", "3": "ADAPTER_3V3", "5": "VBUS_SENSE", "6": "ADAPTER_3V3"},
     "Texas Instruments", "TPS3808G09DBVR", "C24584"),
    ("U5", "PI3USB42", "PI3USB42ZMEX", "UQFN-10_1.4x1.8mm_P0.4mm", (189.23, 226.06),
     {"1": "CONTACT_DP", "2": "CONTACT_DM", "3": "GND", "4": "PC_DM",
      "5": "PC_DP", "8": "DATA_OEn", "9": "ADAPTER_3V3", "10": "GND"},
     "Diodes Incorporated", "PI3USB42ZMEX", "C780880"),
    ("Q1", "2N7002", "2N7002LT1G", "SOT-23", (292.10, 137.16),
     {"1": "VBUS_VALID", "2": "GND", "3": "DATA_OEn"},
     "onsemi", "2N7002LT1G", "C16338"),
    ("D1", "USBESD", "TPD2EUSB30DRTR", "Texas_DRT-3", (67.31, 226.06),
     {"1": "PC_DP", "2": "PC_DM", "3": "GND"},
     "Texas Instruments", "TPD2EUSB30DRTR", "C97502"),
    ("D2", "USBESD", "TPD2EUSB30DRTR", "Texas_DRT-3", (306.07, 226.06),
     {"1": "CONTACT_DP", "2": "CONTACT_DM", "3": "GND"},
     "Texas Instruments", "TPD2EUSB30DRTR", "C97502"),
)
RESISTORS = (
    ("R1", "5.1k", (38.1, 96.52), "CC1", "GND", "RC0603FR-075K1L", "C105580"),
    ("R2", "5.1k", (73.66, 96.52), "CC2", "GND", "RC0603FR-075K1L", "C105580"),
    ("R3", "191k 0.5%", (134.62, 96.52), "ILIM", "GND", "RNCF0603DTC191K", "C2487357"),
    ("R4", "41.2k 1%", (132.08, 172.72), "LIMIT_5V", "VBUS_SENSE", "R0603RXX4122F10LTS", "C267584"),
    ("R5", "10k 0.1%", (171.45, 172.72), "VBUS_SENSE", "GND", "RT0603BRD0710KL", "C95204"),
    ("R6", "47k", (238.76, 172.72), "ADAPTER_3V3", "VBUS_VALID", "RC0603FR-0747KL", "C105579"),
    ("R7", "47k", (276.86, 172.72), "ADAPTER_3V3", "DATA_OEn", "RC0603FR-0747KL", "C105579"),
    ("R8", "10k", (342.90, 172.72), "ADAPTER_3V3", "GND", "RC0603FR-0710KL", "C98220"),
)
CAPACITORS = (
    ("C1", "2.2uF", (184.15, 96.52), "PC_5V", "GRM188R71A225KE15D", "C86018"),
    ("C2", "1uF", (233.68, 96.52), "LIMIT_5V", "GCM188R71C105KA64D", "C161212"),
    ("C3", "1uF", (283.21, 96.52), "CONTACT_5V", "GCM188R71C105KA64D", "C161212"),
    ("C4", "2.2uF", (39.37, 172.72), "ADAPTER_3V3", "GRM188R71A225KE15D", "C86018"),
    ("C5", "100nF", (209.55, 172.72), "ADAPTER_3V3", "GRM188R71H104KA93D", "C77055"),
    ("C6", "100nF", (226.06, 260.35), "ADAPTER_3V3", "GRM188R71H104KA93D", "C77055"),
    ("C7", "1uF", (91.44, 172.72), "PC_5V", "GCM188R71C105KA64D", "C161212"),
)
RESISTOR_MANUFACTURER = {"R3": "Stackpole Electronics", "R4": "EYANG"}
PARTS += tuple((ref, "R", value, R, at, {"1": n1, "2": n2},
                RESISTOR_MANUFACTURER.get(ref, "Yageo"), mpn, stock)
               for ref, value, at, n1, n2, mpn, stock in RESISTORS)
PARTS += tuple((ref, "C", value, C, at, {"1": net, "2": "GND"}, "Murata", mpn, stock)
               for ref, value, at, net, mpn, stock in CAPACITORS)
FOOTPRINTS = {
    USB: BENCH / "DevBench.pretty",
    PH: BENCH / "DevBench.pretty",
    R: KICAD / "Resistor_SMD.pretty",
    C: KICAD / "Capacitor_SMD.pretty",
    "SOT-23-6": KICAD / "Package_TO_SOT_SMD.pretty",
    "SOT-23-5": KICAD / "Package_TO_SOT_SMD.pretty",
    "SOT-23": KICAD / "Package_TO_SOT_SMD.pretty",
    "SOT-363_SC-70-6": KICAD / "Package_TO_SOT_SMD.pretty",
    "Texas_DRT-3": KICAD / "Package_TO_SOT_SMD.pretty",
    "UQFN-10_1.4x1.8mm_P0.4mm": KICAD / "Package_DFN_QFN.pretty",
    "MountingHole_2.2mm_M2": KICAD / "MountingHole.pretty",
}
PIN = "passive"
IN = "input"
PWR_IN = "power_in"
PWR_OUT = "power_out"
OD = "open_collector"
NC = "no_connect"


def prepare_symbols():
    drawing.passive("R", "R")
    drawing.passive("C", "C")
    drawing.ic("USB4105",
               [(pin, pin, PIN) for pin in ("A4", "A5", "A6", "A7", "A8", "A9", "B1", "B4")],
               [(pin, pin, PIN) for pin in ("A1", "A12", "B5", "B6", "B7", "B8", "B9", "B12", "S1")],
               "https://gct.co/files/drawings/usb4105.pdf", "USB 2.0 Type-C sink receptacle")
    drawing.ic("Contacts", [(1, "GND", PIN), (2, "D-", PIN), (3, "D+", PIN), (4, "5 V", PIN)], [],
               "https://www.jst-mfg.com/product/pdf/eng/ePH.pdf", "Keyed harness to J94")
    drawing.ic("TPS2553", [(1, "IN", PWR_IN), (3, "EN", IN), (5, "ILIM", PIN), (2, "GND", PWR_IN)],
               [(6, "OUT", PWR_OUT), (4, "~{FAULT}", OD)], TI + "tps2553-q1.pdf", "USB current limit")
    drawing.ic("LM66100", [(1, "VIN", PWR_IN), (3, "~{CE}", IN), (2, "GND", PWR_IN)],
               [(6, "VOUT", PWR_OUT), (5, "ST", OD), (4, "NC", NC)],
               TI + "lm66100.pdf", "Fast reverse blocking with CE tied to output")
    drawing.ic("TPS7A20", [(1, "IN", PWR_IN), (3, "EN", IN), (2, "GND", PWR_IN)],
               [(5, "OUT", PWR_OUT), (4, "NC", NC)], TI + "tps7a20.pdf", "3.3 V adapter-only regulator")
    drawing.ic("TPS3808", [(6, "VDD", PWR_IN), (5, "SENSE", IN), (3, "~{MR}", IN), (2, "GND", PWR_IN)],
               [(1, "~{RESET}", OD), (4, "CT", PIN)], TI + "tps3808.pdf", "Protected-rail sense and delay")
    drawing.ic("PI3USB42", [(5, "D+A", PIN), (4, "D-A", PIN), (8, "~{OE}", IN), (10, "SEL", IN), (3, "GND", PWR_IN)],
               [(1, "D+", PIN), (2, "D-", PIN), (9, "VDD", PWR_IN), (7, "D+B", PIN), (6, "D-B", PIN)],
               "https://www.diodes.com/datasheet/download/PI3USB42.pdf",
               "USB data gate with power-off isolation and contact-side overvoltage detection")
    drawing.ic("USBESD", [(1, "D+", PIN), (2, "D-", PIN)], [(3, "GND", PIN)],
               TI + "tpd2eusb30.pdf", "Ground-referenced low-capacitance USB ESD clamps")
    drawing.ic("2N7002", [(1, "G", IN)], [(3, "D", PIN), (2, "S", PIN)],
               "https://www.onsemi.com/download/data-sheet/pdf/2n7002l-d.pdf", "Open-drain data-enable inversion")
    drawing.LIB["Source"] = {
        "half": 1.27,
        "source": "",
        "pins": [dict(number="1", name="Source", kind=PWR_OUT, x=0, y=0, angle=90, hide=False)],
        "text": """(symbol "Source" (power) (pin_names hide) (in_bom no) (on_board no)
          (property "Reference" "#FLG" (at 0 5.08 0) (effects (font (size 1.27 1.27)) hide))
          (property "Value" "SOURCE" (at 0 3.81 0) (effects (font (size 1.016 1.016))))
          (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
          (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
          (symbol "Source_0_1"
            (polyline (pts (xy 0 0) (xy 0 1.27) (xy -1.27 1.905) (xy 0 2.54) (xy 1.27 1.905) (xy 0 1.27))
            (stroke (width 0.254) (type default)) (fill (type none))))
          (symbol "Source_1_1" (pin power_out line (at 0 0 90) (length 0)
            (name "P" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))))""",
    }


def source():
    drawing.PROJECT = NAME
    drawing.OUT = HERE
    prepare_symbols()
    sheet = drawing.Sheet(NAME, "Compass EVT1 · direct PC contact adapter")
    sheet.sheet_path = "/" + sheet.id
    sheet.note("USB-C upstream  ·  Protected contact power", 25.40, 13.97)
    sheet.note("USB-C sink: independent Rd on CC1/CC2. J2 mates to the four-contact pin fixture only.",
               25.40, 17.78, 1.016)
    sheet.note("3.3 V logic and protected rail monitor", 25.40, 116.84)
    sheet.note("U4 monitors LIMIT_5V before the reverse blocker. CT open selects 20 ms typical.",
               25.40, 120.65, 1.016)
    sheet.note("USB data gate and ESD", 25.40, 194.31)
    sheet.note("Power absent or LIMIT_5V low → DATA_OEn high or the switch unpowered. SEL low selects A.",
               25.40, 198.12, 1.016)
    sheet.note("Cold mate for first power-on. Attach, break order, inrush and recovery require bench qualification.",
               25.40, 259.08, 1.016)
    for ref, lib, value, footprint, (x, y), nets, _, _, _ in PARTS:
        sheet.part(lib, ref, value, x, y, nets, f"{LIBRARY}:{footprint}", domain="MAIN_T")
    for ref, net, x in [("#FLG1", "PC_5V", 365.76), ("#FLG2", "GND", 365.76)]:
        y = 91.44 if net == "PC_5V" else 111.76
        sheet.part("Source", ref, "SOURCE", x, y, {"1": net}, domain="ANNOTATION")
    sheet.save()

    schematic = HERE / f"{NAME}.kicad_sch"
    tree = sexp.parse(schematic.read_text())
    title = sexp.child(tree, "title_block")
    sexp.child(title, "date")[1] = sexp.string("2026-11-17")
    sexp.child(title, "rev")[1] = sexp.string("EVT1-EA1")
    sexp.child(title, "comment")[2] = sexp.string("BENCH EVALUATION")
    library = sexp.parse("(kicad_symbol_lib (version 20211014) (generator contact_adapter))")
    for embedded in sexp.children(sexp.child(tree, "lib_symbols"), "symbol"):
        name = embedded[1].value.split(":", 1)[1]
        embedded[1] = sexp.string(f"{LIBRARY}:{name}")
        item = deepcopy(embedded)
        item[1] = sexp.string(name)
        library.append(item)
    parts_by_ref = {part[0]: part for part in PARTS}
    for item in sexp.children(tree, "symbol"):
        lib_id = sexp.child(item, "lib_id")
        lib_id[1] = sexp.string(f"{LIBRARY}:{lib_id[1].value.split(':', 1)[1]}")
        ref = sexp.prop(item, "Reference")
        for property_item in list(sexp.children(item, "property")):
            if property_item[1].value in {"DesignStatus", "AssemblyDomain", "ReviewNote"}:
                item.remove(property_item)
        if ref.startswith("#"):
            sexp.child(item, "in_bom")[1] = sexp.atom("no")
            continue
        _, _, _, footprint, _, _, manufacturer, mpn, stock = parts_by_ref[ref]
        field = next(field for field in sexp.children(item, "property") if field[1].value == "Footprint")
        field[2] = sexp.string(f"{LIBRARY}:{footprint}")
        for field, value in (("Manufacturer", manufacturer), ("MPN", mpn), ("LCSC", stock)):
            if not value:
                continue
            item.append(sexp.parse(f'(property "{field}" {drawing.q(value)} (at 0 0 0) '
                                   "(effects (font (size 1 1)) hide))"))
    sexp.write(schematic, tree)
    sexp.write(HERE / f"{LIBRARY}.kicad_sym", library)

    for table, fmt, extension in [("fp", "fp_lib_table", "pretty"), ("sym", "sym_lib_table", "kicad_sym")]:
        (HERE / f"{table}-lib-table").write_text(
            f'({fmt}\n  (version 7)\n  (lib (name "{LIBRARY}") (type "KiCad") '
            f'(uri "${{KIPRJMOD}}/{LIBRARY}.{extension}") (options "") (descr "EVT1 contact adapter"))\n)\n')
    local = HERE / f"{LIBRARY}.pretty"
    local.mkdir(exist_ok=True)
    for name, upstream in FOOTPRINTS.items():
        item = name + ".kicad_mod"
        shutil.copyfile(upstream / item, local / item)
    return tree


def initialize_project():
    path = HERE / f"{NAME}.kicad_pro"
    if path.exists():
        return
    project = json.loads((BENCH / "compass-one-board-dev.kicad_pro").read_text())
    project["meta"]["filename"] = path.name
    project["sheets"] = []
    project["board"]["design_settings"]["drc_exclusions"] = []
    project["erc"]["erc_exclusions"] = []
    project["net_settings"]["classes"] = project["net_settings"]["classes"][:1]
    project["net_settings"]["netclass_patterns"] = []
    project["net_settings"]["netclass_assignments"] = {}
    path.write_text(json.dumps(project, indent=2) + "\n")
    custom = (BENCH / "compass-one-board-dev.kicad_dru").read_text()
    (HERE / f"{NAME}.kicad_dru").write_text(custom.replace("J110", "J1"))


if __name__ == "__main__":
    source()
    initialize_project()
