"""WireViz harness sources for the one-board device, derived from its live netlist.

Exports the native netlist of compass-one-board.kicad_sch, checks the off-board
connector pin contracts and writes four WireViz sources, a wire-stock worksheet
and a source-binding report to hardware/cables/evt1/one-board/. Nominal wire
paths come from the mechanical internals model (mech/internals-fit.json).
Starting blanks are stock planning, not finished cut lengths. With --render the
sources are compiled by WireViz (diagram, PNG and child BOM) outside Git and
their hashes recorded; the human-owned product BOM is untouched.
"""

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import textwrap
import xml.etree.ElementTree as ET

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCHEMATIC = HERE / "compass-one-board.kicad_sch"
PACK_FOOTPRINT = HERE.parent / "EVT1.pretty" / "JST_SH_SM03B-SRSS-TB_1x03-1MP_P1.00mm_Horizontal.kicad_mod"
INTERNALS = HERE / "mech" / "internals-fit.json"
BUILD = HERE / "build" / "cables"
OUT = ROOT / "hardware" / "cables" / "evt1" / "one-board"

# Engineering wire stock carried over from the two-board EVT1 looms: Kapton-insulated
# stranded, amber; (MPN, AWG, maximum insulated OD mm, minimum centreline bend mm).
WIRE = {"28": ("100690", 28, 0.60, 4), "32": ("113094", 32, 0.55, 2)}
SH_CONTACT = "SSH-003T-P0.2-H"
PATH_ALLOWANCE_MM = 20  # dressing, strip and crimp take-up added to the nominal path
NOTE = ("EVT one-board first article. Native numeric pin map; verify mating marks and "
        "continuity. Nominal paths are centreline lengths from the mechanical internals "
        "model, not finished cut lengths; blanks are starting stock. No physical crimp, "
        "current or fit acceptance.")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def netlist_digest(path):
    """Hash of the export with its timestamp removed, so reruns on the same schematic agree."""
    root = ET.parse(path).getroot()
    date = root.find("design/date")
    if date is not None:
        date.text = ""
    return hashlib.sha256(ET.tostring(root)).hexdigest()


def export_netlist(cli, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(cli), "sch", "export", "netlist", "--format", "kicadxml",
                    "-o", str(target), str(SCHEMATIC)], check=True, capture_output=True, text=True)
    return target


def read_netlist(path):
    root = ET.parse(path).getroot()
    components = {}
    for comp in root.findall("components/comp"):
        fields = {f.get("name"): f.text for f in comp.findall("fields/field") if f.text}
        components[comp.get("ref")] = {"value": comp.findtext("value"), "footprint": comp.findtext("footprint"),
                                       "fields": fields}
    pins = {}
    for net in root.findall("nets/net"):
        for node in net.findall("node"):
            pins[(node.get("ref"), node.get("pin"))] = net.get("name")
    return components, pins


def blank_for(path_mm):
    """Starting blank: nominal path plus the allowance, rounded up to 10 mm."""
    return int(math.ceil((path_mm + PATH_ALLOWANCE_MM) / 10.0) * 10)


class Harnesses:
    def __init__(self, pins, paths):
        self.pins = pins
        self.paths = paths
        self.documents = {}
        self.contracts = []
        self.stock = []

    def net(self, ref, pin):
        return self.pins[(ref, str(pin))]

    def contract(self, harness, a, ap, b, bp):
        an, bn = self.net(*a, ap), self.net(*b, bp)
        assert an == bn, (harness, a, ap, an, b, bp, bn)
        self.contracts.append({"harness": harness, "from": [a[0], str(ap)], "to": [b[0], str(bp)], "net": an})
        return an

    def doc(self, name, title, notes=""):
        d = {"metadata": {"title": title, "notes": (NOTE + " " + notes).strip()},
             "options": {"fontname": "Arial", "color_mode": "FULL"},
             "connectors": {}, "cables": {}, "connections": [], "additional_bom_items": []}
        self.documents[name] = d
        return d

    @staticmethod
    def connector(d, name, pins, labels, kind, manufacturer=None, mpn=None, ignore=True, notes=None):
        item = {"type": kind, "pins": list(pins), "pinlabels": list(labels), "ignore_in_bom": ignore}
        if mpn:
            item.update({"manufacturer": manufacturer, "mpn": mpn})
        if notes:
            item["notes"] = notes
        d["connectors"][name] = item

    def wire(self, d, harness, name, a, ap, b, bp, label, gauge="28", path=None, blank=None,
             included=False, color="BN", included_note=None, awg=None):
        mpn, stock_awg, od, radius = WIRE[gauge]
        awg = awg or stock_awg
        if included:
            length = round((path or 0) / 1000, 4)
            notes = included_note or "Included with the component; not a separate wire purchase."
            if path is not None:
                notes += f"\nNominal installed path {path:.1f} mm; the factory lead must cover it with slack."
        else:
            if blank is None:
                blank = blank_for(path) if path is not None else 150
            length = blank / 1000
            notes = (f"{blank} mm starting stock. Maximum insulated OD {od} mm.\n"
                     f"Centreline bend at least {radius} mm.\n"
                     + (f"Nominal installed path {path:.1f} mm from mech/internals-fit.json,\n"
                        f"blank = path + {PATH_ALLOWANCE_MM} mm rounded up to 10 mm.\n"
                        if path is not None else "Installed route not modelled; bench length.\n")
                     + "Do not pre-tin strands before ordinary crimping.\n"
                       "Supplier sets strip/crimp from controlled tooling data.")
        cable = {"category": "bundle", "type": "Included OEM lead" if included else
                 "Individual stranded Kapton wire / trim on first article",
                 "wirecount": 1, "colors": [color], "wirelabels": [label], "gauge": awg, "gauge_unit": "AWG",
                 "length": length, "length_unit": "m", "ignore_in_bom": included, "notes": notes}
        if not included:
            cable.update({"manufacturer": "Accu-Glass", "mpn": mpn})
        d["cables"][name] = cable
        d["connections"].append([{a: [ap]}, {name: [1]}, {b: [bp]}])
        self.stock.append({"harness": harness, "wire": name, "net": label, "from": f"{a}.{ap}", "to": f"{b}.{bp}",
                           "manufacturer": "OEM" if included else "Accu-Glass",
                           "MPN": "included" if included else mpn, "AWG": awg,
                           "stock_blank_mm": 0 if included else blank,
                           "nominal_path_mm": "–" if path is None else round(path, 1),
                           "stock_included": included})

    def build(self):
        # J2: three logical lands for the 3-wire protected pack; land 2 exists twice on the board.
        d = self.doc("pack-one-board", "One-board protected pack / factory JST SH 3P plug into J2",
                     "The pack (3-wire protected 1S LiPo with internal 10 k NTC, 502030 class) is bought with "
                     "its three factory leads already crimped into a JST SH 1.0 mm 3-pin plug (SHR-03V-S); "
                     "nothing here is bought as loose cable and nobody solders the pack. The pack is a "
                     "human-owned BOM/RFQ line. Plug it into J2 after the cap is threaded. There is no "
                     "polarity standard for 3-pin battery plugs: order the pinout below and check it "
                     "with a meter before the first mate.")
        labels = [self.net("J2", p) for p in (1, 2, 3)]
        assert labels == ["PACK_P", "GND", "PACK_NTC"], labels
        self.connector(d, "J2", [1, 2, 3], labels, "JST SH 3-pin side-entry header on the board, SM03B-SRSS-TB",
                       "JST", "SM03B-SRSS-TB(LF)(SN)", ignore=True,
                       notes="Board part (PCB BOM, assembled by the fab), not a cable part. "
                             "Pin 1 PACK_P, 2 GND, 3 PACK_NTC. Rated 1 A per contact.")
        self.connector(d, "PLUG", [1, 2, 3], ["Protected P+", "Protected P-", "NTC"],
                       "Pack's factory JST SH 3P plug", "JST", "SHR-03V-S", ignore=True,
                       notes="Supplied fitted on the pack with three SSH-003T-P0.2-H contacts. "
                             "Specify 1 red P+, 2 black P-, 3 white/yellow NTC.")
        self.connector(d, "PACK", [1, 2, 3], ["Protected P+", "Protected P-", "Internal NTC (to P-)"],
                       "Factory-protected 1S pack with internal NTC", "Pack RFQ", "BC-PACK-EVT1-002",
                       ignore=True,
                       notes="Pack RFQ item (one-board/PACK-RFQ.md), not a cable part. Its own 10 k B 3435 "
                             "NTC is bonded to the cell and returns to P-: the battery temperature sensor "
                             "for the BQ24074 TS cutoff and the AIN2 reading. Leads at least 90 mm.")
        # The pack's internal NTC (TH1 in the schematic) sits between pins 3 and 2.
        self.contract("W-PACK-ONE-BOARD", ("J2",), 3, ("TH1",), 1)
        self.contract("W-PACK-ONE-BOARD", ("J2",), 2, ("TH1",), 2)
        for i, (label, color, key) in enumerate((("PACK_P", "RD", "Pack P"), ("GND", "BK", "Pack N"),
                                                 ("PACK_NTC", "WH", "Pack NTC")), 1):
            self.wire(d, "W-PACK-ONE-BOARD", f"PK{i}", "PLUG", i, "PACK", i, label, "28", path=self.paths[key],
                      included=True, color=color, awg=26,
                      included_note="Factory pack lead crimped into the SH plug; gauge and length per the pack RFQ.")
            d["connections"].append([{"PLUG": [i]}, "-->", {"J2": [i]}])  # mated pins
        d["connectors"]["PACK"]["notes"] += "\nPin 3 lead is white or yellow on typical packs."

        # J3: motor, SH2 side-entry socket, pigtails soldered to the motor's own leads.
        d = self.doc("motor-one-board", "One-board motor / J3 to both bridge outputs",
                     "OEM motor leads are supplied with the motor, not separate wire stock. Solder and insulate "
                     "the pigtail transition, inspect and strain-relieve. MOTOR_N is a bridge output, not ground.")
        labels = [self.net("J3", p) for p in (1, 2)]
        assert labels == ["MOTOR_P", "MOTOR_N"], labels
        self.connector(d, "J3", [1, 2], labels, "JST SH2 socket to the board's SM02B side-entry header",
                       "JST", "SHR-02V-S", ignore=False)
        self.connector(d, "MOTOR", [1, 2], labels, "OEM leaded vibration motor", "NFP", "NFP-E1015 3.7V", ignore=False)
        for i, key in ((1, "Motor P"), (2, "Motor N")):
            self.wire(d, "W-MOTOR-ONE-BOARD", f"M{i}", "J3", i, "MOTOR", i, labels[i - 1], "28", path=self.paths[key])
        d["additional_bom_items"].append({"description": "SH socket crimp contact; crimp the pigtail, then solder "
                                                         "to the OEM lead", "qty": 2, "unit": "pcs",
                                          "manufacturer": "JST", "mpn": SH_CONTACT})

        # J5: tip thermistor, SH2 top-entry socket, 32 AWG pigtails to the glass bead's leads.
        d = self.doc("tip-one-board", "One-board tip thermistor / J5 to the two-wire glass bead",
                     "OEM thermistor leads are supplied with the part. Individually insulate each solder lap; "
                     "do not ordinary-crimp the bead's leads. The bead sits in the cap's thermal pocket.")
        labels = [self.net("J5", p) for p in (1, 2)]
        assert labels == ["TIP_NTC", "GND"], labels
        for i in (1, 2):
            self.contract("W-TIP-ONE-BOARD", ("J5",), i, ("TH101",), i)
        self.connector(d, "J5", [1, 2], labels, "JST SH2 socket to the board's SM02B side-entry header",
                       "JST", "SHR-02V-S", ignore=False)
        self.connector(d, "TIP_NTC", [1, 2], labels, "OEM glass-bead NTC, 10 k 1%", "TDK", "B57540G1103F000", ignore=False)
        for i, key in ((1, "Tip NTC S"), (2, "Tip NTC R")):
            self.wire(d, "W-TIP-ONE-BOARD", f"T{i}", "J5", i, "TIP_NTC", i, labels[i - 1], "32", path=self.paths[key])
        d["additional_bom_items"].append({"description": "SH socket crimp contact; crimp the pigtail, then solder "
                                                         "to the OEM lead", "qty": 2, "unit": "pcs",
                                          "manufacturer": "JST", "mpn": SH_CONTACT})

        # J4: bench service pigtail, not a product harness.
        d = self.doc("service-one-board", "One-board service / J4 to the bench programming fixture",
                     "Bench only; not part of the product. Self-powered interface: the board is powered from its "
                     "pack or dock contacts and no VBUS is supplied here. The fixture end is open (flying leads "
                     "to a USB breakout and EN/BOOT/TX test points); number every lead.")
        labels = [self.net("J4", p) for p in range(1, 7)]
        assert labels == ["GND", "USB_DM", "USB_DP", "MCU_EN", "BOOT_N", "UART_TX"], labels
        self.connector(d, "J4", list(range(1, 7)), labels, "JST SH6 socket to the board's SM06B side-entry header",
                       "JST", "SHR-06V-S", ignore=False)
        self.connector(d, "FIXTURE", list(range(1, 7)), labels, "Bench fixture / numbered flying leads",
                       notes="Keep D-/D+ together with minimal fanout. No 90 ohm or signal-integrity claim.")
        for i in range(1, 7):
            self.wire(d, "W-SERVICE-ONE-BOARD", f"S{i}", "J4", i, "FIXTURE", i, labels[i - 1], "28", blank=150)
        d["additional_bom_items"].append({"description": "SH socket crimp contact", "qty": 6, "unit": "pcs",
                                          "manufacturer": "JST", "mpn": SH_CONTACT})

    def write(self):
        OUT.mkdir(parents=True, exist_ok=True)
        files = []
        for name, d in self.documents.items():
            for c in d["connectors"].values():
                for key, width in (("type", 44), ("notes", 65)):
                    if key in c:
                        c[key] = "\n".join(textwrap.fill(line, width=width, break_long_words=False,
                                                         break_on_hyphens=False) for line in c[key].splitlines())
            path = OUT / f"{name}.yml"
            path.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
            files.append(path)
        with (OUT / "wire-stock.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(self.stock[0]))
            writer.writeheader()
            writer.writerows(self.stock)
        return files


def render(wireviz, files, directory):
    directory.mkdir(parents=True, exist_ok=True)
    command = [*wireviz, "-f", "spt", "-o", str(directory), *map(str, files)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    hashes = {}
    checks = {}
    for file in files:
        expected = yaml.safe_load(file.read_text())
        bom = {}
        for cable in expected["cables"].values():
            if not cable.get("ignore_in_bom"):
                bom[cable["mpn"]] = bom.get(cable["mpn"], 0) + float(cable["length"])
        for connector in expected["connectors"].values():
            if not connector.get("ignore_in_bom"):
                bom[connector["mpn"]] = bom.get(connector["mpn"], 0) + 1
        for item in expected["additional_bom_items"]:
            bom[item["mpn"]] = bom.get(item["mpn"], 0) + item["qty"]
        with (directory / f"{file.stem}.bom.tsv").open(newline="") as f:
            rows = {row["MPN"]: float(row["Qty"]) for row in csv.DictReader(f, delimiter="\t")}
        assert set(rows) == set(bom), (file.stem, rows, bom)
        for mpn, qty in bom.items():
            assert math.isclose(rows[mpn], qty, abs_tol=0.00051), (file.stem, mpn, qty, rows[mpn])
        for suffix in (".svg", ".png", ".bom.tsv"):
            output = directory / f"{file.stem}{suffix}"
            # The pack source buys nothing, so its child BOM is a bare header.
            assert output.is_file() and (suffix == ".bom.tsv" or output.stat().st_size > 100), output
            hashes[output.name] = sha(output)
        checks[file.stem] = {"conductors": len(expected["cables"]), "purchased_MPNs": len(bom),
                             "child_BOM_matches_source": True}
    return {"directory": str(directory), "files_sha256": hashes, "harnesses": checks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", type=Path, default=Path(os.environ.get("BACKPLANE_KICAD_CLI", "kicad-cli")))
    parser.add_argument("--netlist", type=Path, help="use this native XML instead of exporting the schematic")
    parser.add_argument("--render", type=Path, nargs="?", const=BUILD / "export", metavar="DIR",
                        help="compile the sources with WireViz into DIR (default build/cables/export)")
    parser.add_argument("--wireviz", nargs="+", default=[sys.executable, "-m", "wireviz.wv_cli"],
                        help="WireViz command (default: this Python's wireviz.wv_cli module)")
    args = parser.parse_args()

    netlist = args.netlist or export_netlist(args.kicad_cli, BUILD / "compass-one-board-native.xml")
    components, pins = read_netlist(netlist)
    for ref in ("J2", "J3", "J4", "J5", "TH1", "TH101"):
        assert ref in components, ref
    assert "J8" not in components and ("J2", "4") not in pins, "netlist still has the two-wire pack interface"
    assert components["J2"]["footprint"] == "EVT1:JST_SH_SM03B-SRSS-TB_1x03-1MP_P1.00mm_Horizontal", components["J2"]["footprint"]
    assert components["J2"]["fields"].get("Manufacturer Part Number") == "SM03B-SRSS-TB(LF)(SN)"
    pad_numbers = [line.split('"')[1] for line in PACK_FOOTPRINT.read_text().splitlines() if line.strip().startswith("(pad ")]
    assert sorted(pad_numbers) == ["1", "2", "3", "MP", "MP"], pad_numbers
    assert pins[("TH1", "1")] == "PACK_NTC" and pins[("TH1", "2")] == "GND"

    internals = json.loads(INTERNALS.read_text())
    paths = internals["wire_lengths_mm"]
    harnesses = Harnesses(pins, paths)
    harnesses.build()
    files = harnesses.write()

    report = {
        "scope": "Four native-pin-map WireViz sources for the one-board device: pack, motor, tip and bench service. "
                 "Nominal paths come from the mechanical internals model; blanks are starting stock. "
                 "No physical harness, crimp, current or fit result is claimed.",
        "schematic_sha256": {str(p.relative_to(ROOT)): sha(p)
                             for p in (SCHEMATIC, *sorted((HERE / "sheets").glob("*.kicad_sch")))},
        "netlist_export": {"tool": ET.parse(netlist).getroot().findtext("design/tool"),
                           "sha256_without_date": netlist_digest(netlist)},
        "pack_footprint_sha256": sha(PACK_FOOTPRINT),
        "internals_fit_sha256": sha(INTERNALS),
        "nominal_paths_mm": paths,
        "blank_rule": f"path + {PATH_ALLOWANCE_MM} mm rounded up to 10 mm; bench service 150 mm",
        "builder_sha256": sha(Path(__file__)),
        "pin_contracts": harnesses.contracts,
        "connector_pins": {ref: {pin: pins[(ref, pin)] for pin in sorted(
            p for (r, p) in pins if r == ref)} for ref in ("J2", "J3", "J4", "J5", "TH1", "TH101")},
        "files": {f.name: sha(f) for f in files},
        "wire_stock_sha256": sha(OUT / "wire-stock.csv"),
        "render": None,
        "physical_validation": False,
        "full_product_order_ready": False,
    }
    if args.render:
        try:
            report["render"] = render(args.wireviz, files, args.render)
        except (FileNotFoundError, subprocess.CalledProcessError) as error:
            sys.exit(f"WireViz failed ({error}); install wireviz==0.4.1 for this Python or pass --wireviz")
    (OUT / "logical-source.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"harness_sources": len(files), "pin_contracts": len(harnesses.contracts),
                      "wire_stock_rows": len(harnesses.stock), "rendered": bool(args.render)}))


if __name__ == "__main__":
    main()
