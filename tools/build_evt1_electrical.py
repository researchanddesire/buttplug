"""Build the EVT1 native electrical revision without modifying R35F.

The board files in layout-seeds are deliberately outside the new projects: the
new schematics require placement/routing and DRC before fabrication. All pin
connections are exported by KiCad, not by a second invented netlist generator.
"""
from pathlib import Path
import copy
import hashlib
import json
import shutil

import electronics_r0_generate as g
import kicad_sexp as s

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "hardware/pcb/pack-pigtail-r35/candidate-f"
OUT = ROOT / "hardware/pcb/evt1"
STOCK = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")
SYSTEM_ID = "b0765cff-5edc-5370-a16a-6618602c4cf4"
BODY_ID = "18c56c33-1353-55c8-b980-d4e657b3577d"
FLANGE_ID = "c5f43682-38d7-5030-b699-32aa1712a79c"
BODY_SHEET_ID = "7b0971b8-4aea-59dd-87e7-df9ceba65eb5"
FLANGE_SHEET_ID = "2bb7fabd-f8c8-5413-8135-97a69a66eb42"


def read(path):
    return s.parse(path.read_text())


def walk(tree):
    if isinstance(tree, list):
        yield tree
        for v in tree:
            yield from walk(v)


def set_property(tree, name, value):
    item = next(p for p in s.children(tree, "property") if p[1].value == name)
    item[2] = s.string(value)


def contexts(symbol, domain, leaf_id):
    """Supply standalone-board and full-system annotation contexts."""
    old = s.child(symbol, "instances")
    if old:
        symbol.remove(old)
    if domain in ("body", "flange"):
        root_id, parent = (BODY_ID, BODY_SHEET_ID) if domain == "body" else (FLANGE_ID, FLANGE_SHEET_ID)
        paths = [(domain + "-evt1", f"/{root_id}/{leaf_id}"),
                 ("system-evt1", f"/{SYSTEM_ID}/{parent}/{leaf_id}")]
    elif domain in ("dock", "pins"):
        paths = [(domain + "-evt1", f"/{leaf_id}")]
    else:
        paths = [("system-evt1", f"/{SYSTEM_ID}/{leaf_id}")]
    ref = s.prop(symbol, "Reference")
    symbol.append(s.parse("(instances " + " ".join(
        f'(project {g.q(project)} (path {g.q(path)} (reference {g.q(ref)}) (unit 1)))'
        for project, path in paths) + ")"))


def new_sheet(domain, name, title, leaf_id=None):
    g.OUT = OUT / domain if domain in ("body", "flange", "sensor", "dock", "pins") else OUT
    g.PROJECT = domain + "-evt1" if domain in ("body", "flange", "sensor", "dock", "pins") else "system-evt1"
    sheet = g.Sheet(name, title)
    if leaf_id:
        sheet.id = leaf_id
    return sheet


def finish(sheet, domain):
    sheet.save()
    path = g.OUT / (sheet.name + ".kicad_sch")
    tree = read(path)
    for n in s.children(tree, "symbol"):
        contexts(n, domain, sheet.id)
    s.child(tree, "generator")[1] = s.atom("build_evt1_electrical")
    title = s.child(tree, "title_block")
    s.child(title, "date")[1] = s.string("2026-11-12")
    s.child(title, "rev")[1] = s.string("EVT1 electrical candidate")
    s.child(title, "comment")[2] = s.string("LAYOUT INTEGRATION REQUIRED BEFORE PCB ORDER")
    s.write(path, tree)
    return tree


def append_sheet(root, name, filename, identity, x, y):
    root.append(s.parse(f'''(sheet (at {x} {y}) (size 68.58 15.24)
      (fields_autoplaced) (stroke (width 0.1524) (type default))
      (fill (color 0 0 0 0)) (uuid {identity})
      (property "Sheetname" {g.q(name)} (at {x} {y - 0.508} 0)
        {g.effects(1.27, '(justify left bottom)')})
      (property "Sheetfile" {g.q(filename)} (at {x} {y + 15.748} 0)
        {g.effects(1.016, '(justify left top)')}))'''))


def remove_component(tree, ref):
    """Remove generated standalone pin wires and their labels with the symbol."""
    item = next(n for n in s.children(tree, "symbol") if s.prop(n, "Reference") == ref)
    ends = set()
    for wire in s.children(tree, "wire"):
        if s.value(wire, "uuid") in {g.uid(ref + ".wire." + str(i)) for i in range(1, 60)}:
            pts = s.child(wire, "pts")
            ends.update(tuple(a.value for a in p[1:]) for p in s.children(pts, "xy"))
            tree.remove(wire)
    for n in list(tree):
        if s.tag(n) in ("global_label", "no_connect"):
            at = s.child(n, "at")
            if at and tuple(a.value for a in at[1:3]) in ends:
                tree.remove(n)
    tree.remove(item)


def patch_pin_label(tree, ref, pin, new_net):
    wire = next(n for n in s.children(tree, "wire") if s.value(n, "uuid") == g.uid(ref + ".wire." + str(pin)))
    endpoints = {tuple(float(a.value) for a in p[1:]) for p in s.children(s.child(wire, "pts"), "xy")}
    labels = [n for n in s.children(tree, "global_label")
              if tuple(float(a.value) for a in s.child(n, "at")[1:3]) in endpoints]
    assert len(labels) == 1, (ref, pin, len(labels))
    labels[0][1] = s.string(new_net)


def add_generated(destination, source):
    libs = s.child(destination, "lib_symbols")
    names = {n[1].value for n in s.children(libs, "symbol")}
    for n in s.children(s.child(source, "lib_symbols"), "symbol"):
        if n[1].value not in names:
            libs.append(n)
    for n in source:
        if s.tag(n) in ("symbol", "wire", "global_label", "no_connect", "text", "junction"):
            destination.append(n)


def initialise_symbols():
    for name in ("R", "C"):
        g.passive(name, name)
    g.passive("NTC_TDK", "R")
    g.LIB["NTC_TDK"]["source"] = "https://www.tdk-electronics.tdk.com/inf/50/db/ntc_09/Glass_enc_Sensors__B57540__G540__G1540.pdf"
    g.connector("Conn2", 2)
    g.connector("Conn4", 4)
    g.connector("Conn1", 1)
    # Manufacturer pin numbering, matching KiCad D_SOD-323: K=1, A=2.
    g.passive("BAT54WS", "D")
    diode = g.LIB["BAT54WS"]
    diode["text"] = diode["text"].replace('(number "1"', '(number "swap"').replace('(number "2"', '(number "1"').replace('(number "swap"', '(number "2"')
    diode["pins"][0].update(number="2", name="A")
    diode["pins"][1].update(number="1", name="K")
    diode["source"] = "https://www.vishay.com/docs/86465/bat54ws.pdf"
    g.ic("TPS3422EGDRYR", [(3, "PB1_N", "input"), (5, "TS_7S5_LOW", "input"), (6, "TST", "input")],
         [(1, "RST_N", "open_collector"), (4, "VCC", "power_in"), (2, "GND", "power_in")],
         "https://www.ti.com/lit/ds/symlink/tps3422.pdf", "Single-button 7.5 s timer, fixed 400 ms reset pulse")
    g.ic("ADS1115IDGSR", [(1, "ADDR", "input"), (4, "AIN0_NTC", "input"), (5, "AIN1_EXC_HALF", "input"),
                         (6, "AIN2", "input"), (7, "AIN3", "input")],
         [(8, "VDD", "power_in"), (3, "GND", "power_in"), (9, "SDA", "bidirectional"),
          (10, "SCL", "input"), (2, "ALERT_RDY", "open_collector")],
         "https://www.ti.com/lit/ds/symlink/ads1115.pdf", "0x48, pulsed ratiometric tip thermistor readout")
    g.ic("LSM303AGRTR", [(1, "SCL", "input"), (4, "SDA", "bidirectional"), (2, "CS_XL", "input"),
                        (3, "CS_MAG", "input"), (5, "C1", "passive"), (7, "INT_MAG", "output")],
         [(9, "VDD", "power_in"), (10, "VDDIO", "power_in"), (6, "GND", "power_in"),
          (8, "GND", "power_in"), (11, "INT2_XL", "output"), (12, "INT1_XL", "output")],
         "https://www.st.com/resource/en/datasheet/lsm303agr.pdf", "Flange-fixed compass: accel 0x19, magnetometer 0x1e")
    g.ic("USBLC6_2SC6", [(1, "IO1_IN", "passive"), (2, "GND", "power_in"), (3, "IO2_IN", "passive")],
         [(6, "IO1_OUT", "passive"), (5, "VBUS", "passive"), (4, "IO2_OUT", "passive")],
         "https://www.st.com/resource/en/datasheet/usblc6-2.pdf", "USB data/5V ESD array; short return at contact entry")
    g.ic("TPS2553DBVR", [(1, "IN", "power_in"), (3, "EN", "input"), (5, "ILIM", "passive")],
         [(6, "OUT", "power_out"), (2, "GND", "power_in"), (4, "FAULT_N", "open_collector")],
         "https://www.ti.com/lit/ds/symlink/tps2553.pdf", "Current-limited USB switch; R210k, 110..150mA at exact nominal resistor")
    # External computer is the power source. Other parallel VBUS/GND pins are
    # passive; SBU contacts are deliberately not connected for USB2 operation.
    g.ic("USB4105", [("A1", "GND", "power_out"), ("A4", "VBUS", "power_out"), ("A5", "CC1", "passive"),
                     ("A6", "DP", "bidirectional"), ("A7", "DM", "bidirectional"), ("A8", "SBU1", "passive"),
                     ("A9", "VBUS", "passive"), ("A12", "GND", "passive")],
         [("B1", "GND", "passive"), ("B4", "VBUS", "passive"), ("B5", "CC2", "passive"),
          ("B6", "DP", "bidirectional"), ("B7", "DM", "bidirectional"), ("B8", "SBU2", "passive"),
          ("B9", "VBUS", "passive"), ("B12", "GND", "passive"), ("S1", "SHIELD", "passive")],
         "https://gct.co/files/drawings/usb4105.pdf", "USB4105-GF-A-120 USB-C receptacle, USB2, top mount")
    g.ic("Pogo0906", [(1, "CONTACT", "passive")], [],
         "https://www.mill-max.com/products/spring-loaded/0906", "0906-2-15-20-75-14-11-0 spring pin; through-hole solder tail")


def copy_reference():
    """Copy only editable source, never the reference's old validation claims."""
    for domain in ("", "body", "flange"):
        folder = OUT / domain
        folder.mkdir(parents=True, exist_ok=True)
        for path in (SOURCE / domain).iterdir():
            if path.suffix in (".kicad_sch", ".kicad_pro", ".kicad_sym"):
                target = folder / path.name.replace("-r35", "-evt1")
                if path.suffix == ".kicad_sch":
                    tree = read(path)
                    for n in walk(tree):
                        if s.tag(n) == "project" and n[1].value in ("system-r35", "body-r35", "flange-r35"):
                            n[1] = s.string(n[1].value.replace("-r35", "-evt1"))
                        if s.tag(n) == "property" and n[1].value == "Sheetfile":
                            n[2] = s.string(n[2].value.replace("-r35", "-evt1"))
                        if s.tag(n) == "global_label" and n[1].value == "ACCEL_INT_N":
                            n[1] = s.string("TIP_EXC_EN")
                    tb = s.child(tree, "title_block")
                    if tb:
                        s.child(tb, "rev")[1] = s.string("EVT1 electrical candidate")
                        s.child(tb, "date")[1] = s.string("2026-11-12")
                        s.child(tb, "comment")[2] = s.string("LAYOUT INTEGRATION REQUIRED BEFORE PCB ORDER")
                    s.write(target, tree)
                else:
                    shutil.copy2(path, target)
        # Domain libraries stay local, including different body/flange R0 footprints.
        table = read(SOURCE / domain / "fp-lib-table")
        for lib in s.children(table, "lib"):
            uri = s.value(lib, "uri")
            source = (SOURCE / domain / uri.replace("${KIPRJMOD}/", "")).resolve()
            destination = folder / (s.value(lib, "name") + ".pretty")
            shutil.copytree(source, destination, dirs_exist_ok=True)
            s.child(lib, "uri")[1] = s.string("${KIPRJMOD}/" + destination.name)
        s.write(folder / "fp-lib-table", table)
        shutil.copy2(SOURCE / domain / "sym-lib-table", folder / "sym-lib-table")
    seed = OUT / "layout-seeds"
    seed.mkdir(exist_ok=True)
    hashes = {}
    for domain in ("body", "flange"):
        path = SOURCE / domain / (domain + "-r35.kicad_pcb")
        target = seed / path.name
        shutil.copy2(path, target)
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    (seed / "README.md").write_text("# R35F layout seeds\n\nThese byte-identical reference boards are not synchronized with EVT1. Do not order them as EVT1. New contacts, wake/recovery, thermistor ADC and fixed compass require new layout and native DRC.\n")
    (OUT / "source-hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")


def recovery():
    path = OUT / "flange/03-control.kicad_sch"
    tree = read(path)
    patch_pin_label(tree, "SW1", 1, "POWER_SWITCH_N")
    # EN/BOOT remain available on internal J4 and through the two external
    # buttons. Retire redundant internal switches to make room for recovery.
    remove_component(tree, "SW3")
    remove_component(tree, "SW4")
    s.write(path, tree)
    sheet = new_sheet("flange", "07-recovery", "EVT1 four-contact wake and independent USB recovery")
    sheet.part("TPS3422EGDRYR", "U71", "TPS3422EGDRYR", 76.2, 63.5,
               {"1": "MCU_EN", "2": "GND", "3": "POWER_SWITCH_N", "4": "3V3", "5": "GND", "6": "GND"},
               "EVT1:Texas_USON-6_1x1.45mm_P0.5mm_SMD")
    sheet.part("C", "C71", "100nF", 132.08, 58.42, {"1": "3V3", "2": "GND"}, "EVT1:C_0402_1005Metric")
    sheet.part("R", "R71", "10k", 132.08, 96.52, {"1": "3V3", "2": "POWER_SWITCH_N"}, "EVT1:R_0402_1005Metric")
    for ref, x, net_a, net_k in (("D71", 187.96, "POWER_N", "POWER_SWITCH_N"),
                                  ("D72", 251.46, "POWER_N", "DOCK_PRESENT_N"),
                                  ("D73", 314.96, "BOOT_N", "MODE_N")):
        sheet.part("BAT54WS", ref, "BAT54WS-E3-08", x, 58.42,
                   {"1": net_k, "2": net_a}, "EVT1:D_SOD-323")
    sheet.note("GPIO1 POWER_N is a diode-OR of the physical switch and active-low dock presence.\nWhile docked, firmware must suppress GPIO1 button gestures and deep sleep.\nU71 watches the separate raw physical switch, so docking never starts its timer.", 40.64, 132.08)
    sheet.note("Hold Power >=7.5 s for an independent 400 ms EN reset. Release before retry.\nHold Mode low during that reset for ROM USB download through the four contacts.\nInternal EN/BOOT service pads remain available before molding. No dock reset pin required.", 40.64, 165.1)
    finish(sheet, "flange")
    path = OUT / "flange/flange-evt1.kicad_sch"
    root = read(path)
    append_sheet(root, "Hardware wake and USB recovery", "07-recovery.kicad_sch", sheet.id, 240.03, 139.7)
    s.write(path, root)


def contacts():
    path = OUT / "flange/01-power.kicad_sch"
    tree = read(path)
    remove_component(tree, "J1")
    sheet = new_sheet("flange", "contact-fragment", "Contact fragment", s.value(tree, "uuid"))
    sheet.part("Conn4", "J1", "FIXED CONTACT TARGETS GND DM DP 5V", 55.88, 50.8,
               {"1": "GND", "2": "USB_DM_CONTACT", "3": "USB_DP_CONTACT", "4": "DOCK_5V"},
               "EVT1:Contact_Loom_4Land", note="Four separate wires. Fixed metal posts in device; moving pins and magnets in dock.")
    sheet.part("R", "R75", "22R", 180.34, 43.18,
               {"1": "USB_DM_CONTACT", "2": "USB_DM"}, "EVT1:R_0402_1005Metric")
    sheet.part("R", "R76", "22R", 180.34, 83.82,
               {"1": "USB_DP_CONTACT", "2": "USB_DP"}, "EVT1:R_0402_1005Metric")
    sheet.part("USBLC6_2SC6", "U75", "USBLC6-2SC6", 279.4, 63.5,
               {"1": "USB_DM_CONTACT", "2": "GND", "3": "USB_DP_CONTACT", "4": "USB_DP_CONTACT",
                "5": "DOCK_5V", "6": "USB_DM_CONTACT"}, "EVT1:SOT-23-6")
    sheet.note("Native USB: D- to GPIO18, D+ to GPIO19. Place R75/R76 near MCU.\nContact order from -X: GND / D- / D+ / 5V. Place U75 at contact entry.\nInternal J4 is before series resistors; do not connect two USB hosts simultaneously.", 35.56, 132.08)
    fragment = finish(sheet, "flange")
    add_generated(tree, fragment)
    s.write(path, tree)
    (OUT / "flange/contact-fragment.kicad_sch").unlink()


def thermistor():
    path = OUT / "body/04-sensors.kicad_sch"
    identity = s.value(read(path), "uuid")
    sheet = new_sheet("body", "04-sensors", "EVT1 two-wire tip thermistor / pulsed ratiometric ADC", identity)
    sheet.part("ADS1115IDGSR", "U7", "ADS1115IDGSR /0x48", 88.9, 68.58,
               {"1": "GND", "2": None, "3": "GND", "4": "TIP_NTC", "5": "TIP_EXC_HALF", "6": "GND", "7": "GND",
                "8": "3V3", "9": "I2C_SDA", "10": "I2C_SCL"}, "EVT1:VSSOP-10_3x3mm_P0.5mm")
    sheet.part("R", "R61", "10k 0.1%", 157.48, 40.64,
               {"1": "TIP_EXC_EN", "2": "TIP_NTC"}, "EVT1:R_0402_1005Metric")
    sheet.part("C", "C61", "100nF", 157.48, 78.74,
               {"1": "3V3", "2": "GND"}, "EVT1:C_0402_1005Metric")
    sheet.part("C", "C62", "10nF", 157.48, 116.84,
               {"1": "TIP_NTC", "2": "GND"}, "EVT1:C_0402_1005Metric")
    sheet.part("R", "R62", "10k 0.1%", 218.44, 40.64,
               {"1": "TIP_EXC_EN", "2": "TIP_EXC_HALF"}, "EVT1:R_0402_1005Metric")
    sheet.part("R", "R63", "10k 0.1%", 218.44, 78.74,
               {"1": "TIP_EXC_HALF", "2": "GND"}, "EVT1:R_0402_1005Metric")
    sheet.part("C", "C63", "10nF", 218.44, 116.84,
               {"1": "TIP_EXC_HALF", "2": "GND"}, "EVT1:C_0402_1005Metric")
    sheet.part("Conn2", "J5", "TIP NTC / GND", 292.1, 43.18,
               {"1": "TIP_NTC", "2": "GND"}, "EVT1:JST_SH_BM02B-SRSS-TB_1x02-1MP_P1.00mm_Vertical")
    sheet.part("Conn4", "J81", "FIXED FLANGE SENSOR LOOM", 292.1, 99.06,
               {"1": "3V3", "2": "GND", "3": "I2C_SDA", "4": "I2C_SCL"}, "EVT1:Sensor_Loom_4Land")
    sheet.note("GPIO10 / interboard pin10 becomes TIP_EXC_EN (not accelerometer interrupt).\nPulse high only for settled ADC conversions; force low on error and sleep.\nR_NTC = 10k * AIN0 / (2*AIN1 - AIN0). PGA +/-4.096 V; 128 SPS single shot.\nExternal fixed sensor daughterboard carries both accel and magnetometer; no body-mounted MC3635.", 40.64, 165.1)
    finish(sheet, "body")
    identity = s.value(read(OUT / "external-04-sensors.kicad_sch"), "uuid")
    sheet = new_sheet("external", "external-04-sensors", "Potted two-wire tip NTC", identity)
    sheet.part("NTC_TDK", "TH101", "B57540G1103F000 / 10k 1% / curve8307", 76.2, 63.5,
               {"1": "TIP_NTC", "2": "GND"}, note="Glass bead in cap thermal pocket, two insulated leads to body J5.", domain="REMOTE_TIP")
    sheet.note("The two-wire thermistor replaces the old four-wire TMP117 assembly.\nUse manufacturer curve8307 and calibrate the assembled thermal path.\nElectrical checks do not qualify potting, sealing or temperature response.", 40.64, 111.76)
    finish(sheet, "external")


def usb_power_mode():
    path = OUT / "body/01-power.kicad_sch"
    tree = read(path)
    patch_pin_label(tree, "U1", 6, "GND")
    for n in walk(tree):
        if s.tag(n) == "property" and n[1].value == "ReviewNote":
            n[2] = s.string(n[2].value.replace("EN1=1 EN2=0 USB500", "EN1=0 EN2=0 USB100").replace("fixed USB500", "fixed USB100"))
    s.write(path, tree)


def dock_boards():
    for domain in ("dock", "pins"):
        folder = OUT / domain
        folder.mkdir(exist_ok=True)
        project = {"meta": {"filename": domain + "-evt1.kicad_pro", "version": 1},
                   "erc": {"erc_exclusions": []}, "board": {"design_settings": {"rules": {
                       "min_clearance": .2, "min_hole_clearance": .15, "min_track_width": .15,
                       "min_through_hole_diameter": .3, "min_via_diameter": .6,
                       "min_copper_edge_clearance": .3}}}}
        (folder / (domain + "-evt1.kicad_pro")).write_text(json.dumps(project, indent=2) + "\n")
    sh = new_sheet("dock", "dock-evt1", "EVT USB-C cradle input and protected four-wire output")
    sh.part("USB4105", "J91", "USB4105-GF-A-120", 76.2, 76.2,
            {"A1": "GND", "A4": "HOST_5V", "A5": "CC1", "A6": "DOCK_DP", "A7": "DOCK_DM", "A8": None,
             "A9": "HOST_5V", "A12": "GND", "B1": "GND", "B4": "HOST_5V", "B5": "CC2", "B6": "DOCK_DP",
             "B7": "DOCK_DM", "B8": None, "B9": "HOST_5V", "B12": "GND", "S1": "GND"},
            "EVT1:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal")
    sh.part("TPS2553DBVR", "U92", "TPS2553DBVR", 195.58, 48.26,
            {"1": "HOST_5V", "2": "GND", "3": "HOST_5V", "4": "DOCK_FAULT_N", "5": "DOCK_ILIM", "6": "DOCK_5V"},
            "EVT1:SOT-23-6")
    sh.part("USBLC6_2SC6", "U91", "USBLC6-2SC6", 312.42, 48.26,
            {"1": "DOCK_DM", "2": "GND", "3": "DOCK_DP", "4": "DOCK_DP", "5": "HOST_5V", "6": "DOCK_DM"},
            "EVT1:SOT-23-6")
    for ref, x, y, value, a, b in (("R91", 152.4, 99.06, "5.1k 1%", "CC1", "GND"),
                                   ("R92", 208.28, 99.06, "5.1k 1%", "CC2", "GND"),
                                   ("R93", 264.16, 99.06, "210k 1%", "DOCK_ILIM", "GND"),
                                   ("R94", 320.04, 99.06, "100k", "HOST_5V", "DOCK_FAULT_N")):
        sh.part("R", ref, value, x, y, {"1": a, "2": b}, "EVT1:R_0402_1005Metric")
    sh.part("C", "C91", "1uF 10V", 152.4, 139.7, {"1": "HOST_5V", "2": "GND"}, "EVT1:C_0603_1608Metric")
    sh.part("C", "C92", "100nF", 208.28, 139.7, {"1": "DOCK_5V", "2": "GND"}, "EVT1:C_0402_1005Metric")
    sh.part("Conn4", "J93", "TO PIN BOARD J94", 312.42, 147.32,
            {"1": "GND", "2": "DOCK_DM", "3": "DOCK_DP", "4": "DOCK_5V"}, "EVT1:Contact_Loom_4Land")
    sh.part("Conn1", "TP91", "FAULT TEST", 264.16, 139.7, {"1": "DOCK_FAULT_N"}, "EVT1:TestPoint_Pad_D1.0mm")
    sh.note("USB2 native ESP32-C3 interface, not a USB hub. Independent 5.1k Rd on each CC.\nU92 limits shorts at the spring pins; reverse-voltage protection is not a substitute for keyed mating.\nDevice charger EN1/EN2 are both low: USB100 input mode, not the former fixed500mA.\nFull-system current, enumeration, suspend/resume, inrush and USB waveform still require EVT measurements.", 40.64, 198.12)
    finish(sh, "dock")
    sh = new_sheet("pins", "pins-evt1", "Four spring pins / rigid metal-face stops / contact order")
    for i, net in enumerate(("GND", "DOCK_DM", "DOCK_DP", "DOCK_5V")):
        sh.part("Pogo0906", "P" + str(91+i), "0906-2-15-20-75-14-11-0", 76.2+i*76.2, 63.5,
                {"1": net}, "EVT1:MillMax_0906_2")
    sh.part("Conn4", "J94", "TO USB BOARD J93", 76.2, 121.92,
            {"1": "GND", "2": "DOCK_DM", "3": "DOCK_DP", "4": "DOCK_5V"}, "EVT1:Contact_Loom_4Land")
    sh.note("Board28x10x1mm. Pin centers local(4,6.7),(10,6.7),(16,6.7),(22,6.7).\nLocal(x,y) maps to dock(X=x-42, Y=8.7962, Z=50.2-y) on component face.\nTail drill0.6mm. Stops touch fixed metal target faces; silicone is not the spring-height datum.\nRoute the short D+/D- loom as a pair. Pin fanout and loose-wire USB impedance need physical validation.", 40.64, 170.18)
    finish(sh, "pins")


def compass():
    (OUT / "sensor").mkdir(exist_ok=True)
    sheet = new_sheet("sensor", "sensor-evt1", "Flange-fixed eCompass sensor daughterboard")
    sheet.part("LSM303AGRTR", "U81", "LSM303AGRTR", 88.9, 68.58,
               {"1": "I2C_SCL", "2": "3V3", "3": "3V3", "4": "I2C_SDA", "5": "MAG_C1", "6": "GND", "7": None,
                "8": "GND", "9": "3V3", "10": "3V3", "11": None, "12": None}, "EVT1:LGA-12_2x2mm_P0.5mm")
    sheet.part("C", "C81", "220nF", 160.02, 48.26,
               {"1": "MAG_C1", "2": "GND"}, "EVT1:C_0402_1005Metric")
    sheet.part("C", "C82", "100nF", 160.02, 86.36,
               {"1": "3V3", "2": "GND"}, "EVT1:C_0402_1005Metric")
    sheet.part("C", "C83", "22uF 10V / Ceff>=10uF at3V3", 160.02, 124.46,
               {"1": "3V3", "2": "GND"}, "EVT1:C_0805_2012Metric",
               note="MLCC candidate: qualify >=10uF effective at3V3/temp versus ST p35 bulk recommendation before layout release.")
    sheet.part("C", "C84", "100nF / VDDIO local", 218.44, 124.46,
               {"1": "3V3", "2": "GND"}, "EVT1:C_0402_1005Metric")
    sheet.part("Conn4", "J82", "TO BODY J81 / FIXED IN FLANGE", 236.22, 58.42,
               {"1": "3V3", "2": "GND", "3": "I2C_SDA", "4": "I2C_SCL"}, "EVT1:Sensor_Loom_4Land")
    sheet.note("Both sensor axes are fixed to the flange/back-arrow reference, independent of cap rotation.\nPlace near +X flange end, away from motor, steel keepers and charging magnets.\nNo extra pullups: existing R32/R33 pull up the common 3V3 I2C bus.\nRegister axes to CAD. Calibrate assembled magnetic offsets; suppress heading when docked.\nSensor PCB placement, magnetic survey and final axis transform still require integration.", 40.64, 170.18)
    tree = finish(sheet, "sensor")
    for n in s.children(tree, "symbol"):
        old = s.child(n, "instances")
        ref = s.prop(n, "Reference")
        n.remove(old)
        n.append(s.parse(f'''(instances
          (project "sensor-evt1" (path "/{sheet.id}" (reference {g.q(ref)}) (unit 1)))
          (project "system-evt1" (path "/{SYSTEM_ID}/{sheet.id}" (reference {g.q(ref)}) (unit 1))))'''))
    s.write(OUT / "sensor/sensor-evt1.kicad_sch", tree)
    shutil.copy2(OUT / "body/body-evt1.kicad_pro", OUT / "sensor/sensor-evt1.kicad_pro")
    root_path = OUT / "system-evt1.kicad_sch"
    root = read(root_path)
    append_sheet(root, "Fixed flange compass sensor", "sensor/sensor-evt1.kicad_sch", sheet.id, 243.84, 139.7)
    s.write(root_path, root)


def libraries():
    """Vendor exact symbol/footprint snapshots used by new components."""
    local = OUT / "EVT1.pretty"
    local.mkdir(exist_ok=True)
    # A zero-radius rounded rectangle is exactly a rectangle. Normalize the
    # inherited ESP32 pads so native board/library readers agree on the shape.
    # This changes representation only, never the copper outline or pad nets.
    for folder in (OUT, OUT/"flange"):
        for path in folder.glob("*.pretty/*ESP32*.kicad_mod"):
            fp=read(path)
            for pad in s.children(fp,"pad"):
                radius=s.child(pad,"roundrect_rratio")
                if pad[3].value=="roundrect" and radius and float(radius[1].value)==0:
                    pad[3]=s.atom("rect");pad.remove(radius)
            s.write(path,fp)
    for folder in (OUT, OUT/"body"):
        path=folder/"PackPigtailR35.pretty/Pack_Pigtail_4Net_5Land.kicad_mod"
        fp=read(path)
        for line in list(s.children(fp,"fp_line")):
            if s.value(line,"layer")=="F.CrtYd":fp.remove(line)
        for text in s.children(fp,"fp_text"):
            if text[2].value=="SG":s.child(text,"layer")[1]=s.string("F.Fab")
        corners=[(-2.8,-3.545),(2.8,-3.545),(2.8,-2.045),(-2.8,-2.045)]
        for a,b in zip(corners,corners[1:]+corners[:1]):
            fp.append(s.parse(f'(fp_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (layer "F.CrtYd") (width .05))'))
        s.write(path,fp)
    footprints = {
        "Package_SON": ["Texas_USON-6_1x1.45mm_P0.5mm_SMD"],
        "Package_SO": ["VSSOP-10_3x3mm_P0.5mm"],
        "Package_LGA": ["LGA-12_2x2mm_P0.5mm"],
        "Package_TO_SOT_SMD": ["SOT-23-6"],
        "Diode_SMD": ["D_SOD-323"],
        "Resistor_SMD": ["R_0402_1005Metric"],
        "Capacitor_SMD": ["C_0402_1005Metric"],
        "TestPoint": ["TestPoint_Pad_D1.0mm"],
        "Connector_USB": ["USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal"],
        "Connector_JST": ["JST_SH_BM02B-SRSS-TB_1x02-1MP_P1.00mm_Vertical"],
    }
    for library, names in footprints.items():
        for name in names:
            shutil.copy2(STOCK / (library + ".pretty") / (name + ".kicad_mod"), local / (name + ".kicad_mod"))
            if library == "Connector_USB":
                path=local/(name+".kicad_mod")
                fp=read(path)
                # Cosmetic only: remove two silk strokes at the PCB overhang.
                # OEM-derived copper, holes and body/courtyard are unchanged.
                for line in s.children(fp,"fp_line"):
                    if s.value(line,"layer")=="F.SilkS" and s.child(line,"end")[2].value=="3.25":fp.remove(line)
                s.write(path,fp)
    for name in ("C_0603_1608Metric","C_0805_2012Metric"):
        shutil.copy2(STOCK / ("Capacitor_SMD.pretty/"+name+".kicad_mod"), local / (name+".kicad_mod"))
    (local / "MillMax_0906_2.kicad_mod").write_text('''(footprint "MillMax_0906_2" (version 20221018) (generator build_evt1_electrical)
      (layer "F.Cu") (attr through_hole)
      (descr "0906-2 tail0.4318mm, barrel1.8288mm; verify against manufacturer drawing")
      (fp_text reference "REF**" (at 0 -1.8) (layer "F.SilkS") (effects (font (size .7 .7) (thickness .12))))
      (fp_text value "0906-2" (at 0 1.8) (layer "F.Fab") (effects (font (size .7 .7) (thickness .12))))
      (fp_circle (center 0 0) (end .9144 0) (stroke (width .1) (type solid)) (fill none) (layer "F.Fab"))
      (fp_circle (center 0 0) (end 1.2 0) (stroke (width .05) (type solid)) (fill none) (layer "F.CrtYd"))
      (pad "1" thru_hole circle (at 0 0) (size 1.5 1.5) (drill .6) (layers "*.Cu" "*.Mask")))\n''')
    for name, pitch, diameter in (("Contact_Loom_4Land", 2.5, 1.8), ("Sensor_Loom_4Land", 1.5, 1.0)):
        pads = "\n".join(f'(pad "{i+1}" smd circle (at {i*pitch} 0) (size {diameter} {diameter}) (layers "F.Cu" "F.Paste" "F.Mask"))' for i in range(4))
        (local / (name + ".kicad_mod")).write_text(f'''(footprint "{name}" (version 20221018) (generator build_evt1_electrical)
          (layer "F.Cu") (attr smd)
          (fp_text reference "REF**" (at 0 -2) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))
          (fp_text value "{name}" (at 0 2) (layer "F.Fab") (effects (font (size 0.8 0.8) (thickness 0.12))))
          {pads})\n''')
    for domain in ("", "body", "flange", "sensor", "dock", "pins"):
        folder = OUT / domain
        library_path = folder / "PrototypeR0.kicad_sym"
        tree = read(library_path) if library_path.exists() else [s.atom("kicad_symbol_lib"), s.parse("(version 20220914)"), s.parse("(generator build_evt1_electrical)")]
        existing = {n[1].value for n in s.children(tree, "symbol")}
        for name, spec in g.LIB.items():
            if name not in existing:
                tree.append(s.parse(spec["text"]))
        s.write(library_path, tree)
        table_path = folder / "fp-lib-table"
        table = read(table_path) if table_path.exists() else [s.atom("fp_lib_table")]
        uri = "${KIPRJMOD}/" + ("../" if domain else "") + "EVT1.pretty"
        table.append(s.parse(f'(lib (name "EVT1") (type "KiCad") (uri {g.q(uri)}) (options "") (descr "EVT1 new component footprint snapshots"))'))
        s.write(table_path, table)
        if not (folder / "sym-lib-table").exists():
            shutil.copy2(OUT / "sym-lib-table", folder / "sym-lib-table")
        # KiCad 10's library-table reader requires the explicit table version.
        for filename in ("sym-lib-table", "fp-lib-table"):
            table_path = folder / filename
            table = read(table_path)
            if s.child(table, "version") is None:
                table.insert(1, s.parse("(version 7)"))
            s.write(table_path, table)
    (OUT / "new-components.json").write_text(json.dumps(g.PARTS, indent=2, ensure_ascii=False) + "\n")


def main():
    g.PARTS.clear()
    initialise_symbols()
    copy_reference()
    recovery()
    contacts()
    thermistor()
    usb_power_mode()
    compass()
    dock_boards()
    libraries()
    print("EVT1 native electrical sources generated; no fabrication release or PCB route implied.")


if __name__ == "__main__":
    main()
