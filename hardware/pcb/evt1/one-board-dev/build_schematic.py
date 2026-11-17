"""Regenerate the bench derivative from the product one-board KiCad source."""

from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PRODUCT = HERE.parent / "one-board"
NAME = "compass-one-board-dev"
sys.path.insert(0, str(ROOT / "tools"))
import electronics_r0_generate as graphics
import kicad_sexp as sexp
from build_evt1_electrical import append_sheet, patch_pin_label

TERMINAL_UPDATES = {
    "U2": {"7": "DEV_3V3_REG"},
    "C13": {"1": "DEV_3V3_REG"},
    "C14": {"1": "DEV_3V3_REG"},
    "C15": {"1": "DEV_3V3_REG"},
    "C52": {"1": "DEV_3V3_REG"},
    "R11": {"1": "DEV_3V3_REG"},
    "U5": {"1": "DEV_MOTOR_VM"},
    "C28": {"1": "DEV_MOTOR_VM"},
    "C30": {"1": "DEV_MOTOR_VM"},
    "J2": {"1": "DEV_PACK_POS"},
}

PAD1 = "DevBench:TestPoint_THTPad_D1.5mm_Drill0.7mm"
PINHEADER = "DevBench:PinHeader_1x{count:02d}_P2.54mm_Vertical"
USB_FOOTPRINT = "USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal"
USB = f"DevBench:{USB_FOOTPRINT}"
HOST_KEY_FOOTPRINT = "JST_PHD_B10B-PHDSS_2x05_P2.00mm_Vertical"
HOST_KEY_NETS = (
    "DEV_USB_DM", "USB_DM_CONTACT", "DEV_USB_DP", "USB_DP_CONTACT", "GND",
    "DEV_DOCK_DM", "DEV_USB_5V", "DEV_DOCK_DP", "DEV_DOCK_5V", "DOCK_5V",
)
BENCH_ORDER_PARTS = {
    "J110": ("USB4105-GF-A-120", "https://gct.co/files/drawings/usb4105.pdf"),
    "J111": ("B4B-PH-K(LF)(SN)", "https://www.jst-mfg.com/product/index.php?lang=2&series=199"),
    "J112": ("B10B-PHDSS(LF)(SN)", "https://www.jst-mfg.com/product/index.php?lang=2&series=201"),
    "J120": ("TSW-102-07-G-S", "https://www.samtec.com/products/tsw-102-07-g-s"),
    "J121": ("TSW-102-07-G-S", "https://www.samtec.com/products/tsw-102-07-g-s"),
    "J122": ("TSW-102-07-G-S", "https://www.samtec.com/products/tsw-102-07-g-s"),
    "J124": ("TSW-104-07-G-S", "https://www.samtec.com/products/tsw-104-07-g-s"),
    "J125": ("TSW-106-07-G-S", "https://www.samtec.com/products/tsw-106-07-g-s"),
    "R101": ("RC0603FR-075K1L", "https://www.yageo.com/en/Product/Index/rchip"),
    "R102": ("RC0603FR-075K1L", "https://www.yageo.com/en/Product/Index/rchip"),
}
BENCH_PARTS = [
    ("J111", "DOCK HOST", ("GND", "DEV_DOCK_DM", "DEV_DOCK_DP", "DEV_DOCK_5V"), "DevBench:JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical", (250.19, 36.83)),
    ("J112", "PC / DOCK HOST KEY", HOST_KEY_NETS, f"DevBench:{HOST_KEY_FOOTPRINT}", (175.26, 90.17)),
    ("J120", "3V3 isolate", ("DEV_3V3_REG", "3V3"), PINHEADER.format(count=2), (58.42, 149.86)),
    ("J121", "MOTOR VM isolate", ("MOTOR_3V7", "DEV_MOTOR_VM"), PINHEADER.format(count=2), (127, 149.86)),
    ("J122", "PACK+ isolate", ("DEV_PACK_POS", "PACK_P"), PINHEADER.format(count=2), (195.58, 149.86)),
    ("J124", "Dual pack NTC simulator", ("PACK_NTC", "GND", "PACK_GUARD", "GND"), PINHEADER.format(count=4), (269.24, 149.86)),
    ("J125", "Recovery and I2C", ("GND", "3V3", "MCU_EN", "BOOT_N", "I2C_SCL", "I2C_SDA"), PINHEADER.format(count=6), (342.9, 149.86)),
]
PROBES = {
    "TP101": "GND", "TP102": "DOCK_5V", "TP103": "VBUS_CHG", "TP104": "SYS",
    "TP105": "PACK_P", "TP106": "3V3", "TP107": "MOTOR_3V7", "TP108": "DEV_MOTOR_VM",
    "TP109": "DOCK_PRESENT_N", "TP110": "TIP_EXC_EN", "TP111": "TIP_NTC",
    "TP112": "TIP_EXC_HALF", "TP113": "PACK_NTC", "TP114": "PACK_GUARD",
    "TP115": "PACK_MON_NTC", "TP116": "MOTOR_ARM", "TP117": "MOTOR_PWM", "TP118": "MOTOR_IN1",
    "TP119": "MOTOR_P", "TP120": "MOTOR_N", "TP121": "GND",
}
FOOTPRINT_STOCK = (
    ("Resistor_SMD", "R_0603_1608Metric"),
    ("MountingHole", "MountingHole_3.2mm_M3"),
    ("TestPoint", "TestPoint_THTPad_D1.5mm_Drill0.7mm"),
    ("Connector_JST", "JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical"),
    ("Connector_JST", HOST_KEY_FOOTPRINT),
    *(( "Connector_PinHeader_2.54mm", f"PinHeader_1x{count:02d}_P2.54mm_Vertical") for count in (2, 4, 6)),
)


def read(path):
    return sexp.parse(path.read_text())


def set_string(node, tag, value):
    sexp.child(node, tag)[1] = sexp.string(value)


def annotate_symbols(tree, root_id, sheet_id):
    for symbol in sexp.children(tree, "symbol"):
        old = sexp.child(symbol, "instances")
        if old:
            symbol.remove(old)
        ref = sexp.prop(symbol, "Reference")
        unit = sexp.value(symbol, "unit")
        path = f"/{root_id}/{sheet_id}"
        symbol.append(sexp.parse(f'(instances (project "{NAME}" (path "{path}" (reference {graphics.q(ref)}) (unit {unit}))))'))


def prepare_library_tables():
    destination = HERE / "DevBench.pretty"
    destination.mkdir(exist_ok=True)
    stock = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")
    for family, footprint in FOOTPRINT_STOCK:
        path = destination / f"{footprint}.kicad_mod"
        if not path.exists():
            shutil.copyfile(stock / f"{family}.pretty" / path.name, path)
    hybrid = destination / f"{USB_FOOTPRINT}.kicad_mod"
    if not hybrid.exists():
        source = (HERE.parent / "EVT1.pretty" / hybrid.name).read_text()
        assert source.count("(attr smd)") == 1
        hybrid.write_text(source.replace("(attr smd)", "(attr through_hole)", 1))
    for filename, library_name in (("fp-lib-table", "DevBench"), ("sym-lib-table", None)):
        tree = read(PRODUCT / filename)
        for item in sexp.children(tree, "lib"):
            uri = sexp.value(item, "uri")
            if uri.startswith("${KIPRJMOD}/"):
                path = (PRODUCT / uri.removeprefix("${KIPRJMOD}/")).resolve()
                relative_path = path.relative_to(HERE.parent)
                set_string(item, "uri", "${KIPRJMOD}/../" + relative_path.as_posix())
        if library_name:
            tree.append(sexp.parse(f'(lib (name "{library_name}") (type "KiCad") '
                                   '(uri "${KIPRJMOD}/DevBench.pretty") (options "") '
                                   '(descr "Local KiCad 7 bench footprint snapshots"))'))
        else:
            tree.append(sexp.parse('(lib (name "DevBench") (type "KiCad") '
                                   '(uri "${KIPRJMOD}/DevBench.kicad_sym") (options "") '
                                   '(descr "Bench connector and external source symbols"))'))
        sexp.write(HERE / filename, tree)


def bench_sheet(root_id, sheet_id):
    graphics.PROJECT = NAME
    graphics.OUT = HERE / "sheets"
    graphics.passive("R", "R")
    for count in (1, 2, 4, 6):
        graphics.connector(f"Conn{count}", count)
    graphics.ic("HostKey",
                [(pin, label, "passive") for pin, label in (
                    (1, "PC D-"), (3, "PC D+"), (5, "GND"), (7, "PC 5V"), (9, "DOCK 5V"))],
                [(pin, label, "passive") for pin, label in (
                    (2, "Common D-"), (4, "Common D+"), (6, "DOCK D-"), (8, "DOCK D+"), (10, "Common 5V"))],
                BENCH_ORDER_PARTS["J112"][1], "Polarized PHD socket for one terminated PC or DOCK loopback key")
    graphics.ic("USB4105",
                [(pin, pin, "passive") for pin in ("A4", "A5", "A6", "A7", "A8", "A9", "B1", "B4")],
                [(pin, pin, "passive") for pin in ("A1", "A12", "B5", "B6", "B7", "B8", "B9", "B12", "S1")],
                "https://gct.co/files/drawings/usb4105.pdf", "USB-C 16-pin USB 2.0 UFP")
    graphics.LIB["DEV_LINK_POWER"] = dict(
        half=1.27, source="", pins=[dict(number="1", name="P", kind="power_out", x=0, y=0, angle=90, hide=False)],
        text='''(symbol "DEV_LINK_POWER" (power) (pin_names hide) (in_bom no) (on_board no)
          (property "Reference" "#FLG" (at 0 5.08 0) (effects (font (size 1.27 1.27)) hide))
          (property "Value" "BENCH_LINK_SOURCE" (at 0 3.81 0) (effects (font (size 1.27 1.27))))
          (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
          (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))
          (symbol "DEV_LINK_POWER_0_1"
            (polyline (pts (xy 0 0) (xy 0 1.27) (xy -1.27 1.905) (xy 0 2.54) (xy 1.27 1.905) (xy 0 1.27))
            (stroke (width 0.254) (type default)) (fill (type none))))
          (symbol "DEV_LINK_POWER_1_1" (pin power_out line (at 0 0 90) (length 0)
            (name "P" (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27)))))))''',
    )
    sheet = graphics.Sheet("09-bench", "Compass bench derivative | supplies, USB and instruments")
    sheet.id = sheet_id
    sheet.note("Remove both power sources before changing the J112 host key. Connect one USB host. "
               "Ship with the host key and rail shunts removed.", 20.32, 15.24, 1.27)
    usb_nets = {"A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND",
                "A4": "DEV_USB_5V", "A9": "DEV_USB_5V", "B4": "DEV_USB_5V", "B9": "DEV_USB_5V",
                "A5": "DEV_CC1", "B5": "DEV_CC2", "A6": "DEV_USB_DP", "B6": "DEV_USB_DP",
                "A7": "DEV_USB_DM", "B7": "DEV_USB_DM"}
    sheet.part("USB4105", "J110", "USB4105-GF-A-120", 106.68, 45.72, usb_nets, USB, domain="MAIN_T")
    for ref, net, x in (("R101", "DEV_CC1", 177.8), ("R102", "DEV_CC2", 210.82)):
        sheet.part("R", ref, "5.1k 1%", x, 46.99, {"1": net, "2": "GND"}, "DevBench:R_0603_1608Metric", domain="MAIN_T")
    for ref, value, nets, footprint, (x, y) in BENCH_PARTS:
        symbol = "HostKey" if ref == "J112" else f"Conn{len(nets)}"
        sheet.part(symbol, ref, value, x, y, dict(zip(map(str, range(1, len(nets) + 1)), nets)),
                   footprint, domain="MAIN_T")
    sheet.note("PC key: 1-2, 3-4, 7-10. DOCK key: 2-6, 4-8, 9-10. "
               "Cavity 5 is board ground and unused by both keys.", 231.14, 83.82, 1.27)
    sheet.note("J120/J121/J122 are open by default. J124 accepts resistance simulators. Keep the real pack "
               "and sensor harnesses disconnected during fault injection.", 22.86, 116.84, 1.27)
    sheet.note("BENCH_LINK_SOURCE indicates where external conditions drive the retained power pins. "
               "The installed removable link is required.", 22.86, 186.69, 1.27)
    for i, net in enumerate(("3V3", "DEV_MOTOR_VM"), start=1):
        sheet.part("DEV_LINK_POWER", f"#FLG11{i}", "BENCH_LINK_SOURCE", 62.23 + 71.12 * i, 198.12, {"1": net}, domain="ANNOTATION")
    for i, (ref, net) in enumerate(PROBES.items()):
        sheet.part("Conn1", ref, net, 55.88 + 50.8 * (i % 7), 223.52 + 20.32 * (i // 7),
                   {"1": net}, PAD1, domain="MAIN_T")
    sheet.save()
    path = HERE / "sheets" / "09-bench.kicad_sch"
    tree = read(path)
    symbols = sexp.children(sexp.child(tree, "lib_symbols"), "symbol")
    library = sexp.parse('(kicad_symbol_lib (version 20211014) (generator compass_dev_bench))')
    for symbol in symbols:
        name = symbol[1].value.split(":", 1)[1]
        symbol[1] = sexp.string("DevBench:" + name)
        entry = deepcopy(symbol)
        entry[1] = sexp.string(name)
        library.append(entry)
    for item in sexp.children(tree, "symbol"):
        existing = sexp.value(item, "lib_id")
        set_string(item, "lib_id", "DevBench:" + existing.split(":", 1)[1])
        ref = sexp.prop(item, "Reference")
        if ref in PROBES:
            sexp.child(item, "in_bom")[1] = sexp.atom("no")
        if ref in BENCH_ORDER_PARTS:
            mpn, datasheet = BENCH_ORDER_PARTS[ref]
            for name, value in (("MPN", mpn), ("Datasheet", datasheet)):
                property_node = next((node for node in sexp.children(item, "property") if node[1].value == name), None)
                if property_node is None:
                    item.append(sexp.parse(f'(property {graphics.q(name)} {graphics.q(value)} '
                                           '(at 0 0 0) (effects (font (size 1.27 1.27)) hide))'))
                else:
                    property_node[2] = sexp.string(value)
        if ref == "J112":
            note = next(node for node in sexp.children(item, "property") if node[1].value == "ReviewNote")
            note[2] = sexp.string("Use one keyed PC or DOCK plug. Change keys with both USB and battery disconnected.")
    sexp.write(HERE / "DevBench.kicad_sym", library)
    annotate_symbols(tree, root_id, sheet_id)
    sexp.write(path, tree)


def build():
    product_root = read(PRODUCT / "compass-one-board.kicad_sch")
    root_id = graphics.uid(NAME)
    sexp.child(product_root, "uuid")[1] = sexp.atom(root_id)
    set_string(sexp.child(product_root, "title_block"), "title", "Compass EVT1 open bench board")
    set_string(sexp.child(product_root, "title_block"), "rev", "Open bench derivative")
    (HERE / "sheets").mkdir(exist_ok=True)
    found_patches = set()
    for leaf in sexp.children(product_root, "sheet"):
        filename = next(p[2].value for p in sexp.children(leaf, "property") if p[1].value == "Sheetfile")
        path = PRODUCT / filename
        tree = read(path)
        refs = {sexp.prop(s, "Reference") for s in sexp.children(tree, "symbol")}
        # Product pogo contacts are replaced by the selectable bench sheet.
        if {"CT1", "CT2", "CT3", "CT4"} <= refs:
            assert refs <= {"CT1", "CT2", "CT3", "CT4"}, (path, refs)
            product_root.remove(leaf)
            continue
        for ref, updates in TERMINAL_UPDATES.items():
            if ref in refs:
                for pin, net in updates.items():
                    patch_pin_label(tree, ref, pin, net)
                found_patches.add(ref)
        for symbol in sexp.children(tree, "symbol"):
            if sexp.prop(symbol, "Reference") == "JP1":
                sexp.child(symbol, "in_bom")[1] = sexp.atom("no")
        annotate_symbols(tree, root_id, sexp.value(leaf, "uuid"))
        dest = HERE / filename
        dest.parent.mkdir(exist_ok=True)
        sexp.write(dest, tree)
    assert found_patches == set(TERMINAL_UPDATES), set(TERMINAL_UPDATES) - found_patches
    bench_id = graphics.uid(NAME + "-bench")
    append_sheet(product_root, "Bench sources, links and probes", "sheets/09-bench.kicad_sch", bench_id, 203.2, 241.3)
    bench_sheet(root_id, bench_id)
    sexp.write(HERE / f"{NAME}.kicad_sch", product_root)
    prepare_library_tables()
    project_path = HERE / f"{NAME}.kicad_pro"
    if not project_path.exists():
        project = json.loads((PRODUCT / "compass-one-board.kicad_pro").read_text())
        project["meta"]["filename"] = project_path.name
        project_path.write_text(json.dumps(project, indent=2) + "\n")


if __name__ == "__main__":
    build()
