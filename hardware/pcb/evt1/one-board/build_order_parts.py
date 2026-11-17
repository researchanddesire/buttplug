"""Reconcile the single-board part list against the existing exact selections."""

import argparse
import csv
from pathlib import Path
import xml.etree.ElementTree as ET

from build_schematic import OPTIONAL_SYS_BULK

HERE = Path(__file__).resolve().parent
EVT = HERE.parent
MANUAL = {
    "J2": "Hand-solder five pack and thermistor lands. Follow J2 pinout and fit a detached harness.",
    "JP1": "Copper-only charge permission jumper. Leave open for first power.",
    **{f"CT{i}": "Mill-Max 1946-0-00-15-00-00-03-0, install manually after checking finished plated diameter."
       for i in range(1, 5)},
    **OPTIONAL_SYS_BULK,
}


def selections():
    result = {}
    with (EVT / "pcb-ordering.csv").open() as stream:
        for row in csv.DictReader(stream):
            for designator in row["References"].split():
                if designator.startswith("body:"):
                    result[designator.removeprefix("body:")] = row
    with (EVT / "single-flange-routing/assembly-quote/single-flange-smt-parts.csv").open() as stream:
        for row in csv.DictReader(stream):
            for designator in row["References"].split():
                if designator in result:
                    raise ValueError(f"Duplicate baseline designator {designator}")
                result[designator] = row
    return result


def write_rows(path, headers, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_netlist", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    baseline = selections()
    smt, manual = [], []
    for comp in ET.parse(args.native_netlist).findall("./components/comp"):
        reference = comp.get("ref")
        footprint = comp.findtext("footprint")
        if not footprint:
            continue
        if reference in MANUAL:
            manual.append({"Reference":reference, "Treatment":MANUAL[reference]})
            continue
        mpn = comp.findtext("fields/field[@name='Manufacturer Part Number']")
        previous = baseline.get(reference, {})
        exact = mpn or previous.get("MPN")
        if not exact:
            raise ValueError(f"No exact MPN for {reference}: {footprint}")
        smt.append({
            "Comment":comp.findtext("value"),
            "Designator":reference,
            "Footprint":footprint.split(":",1)[1],
            "Manufacturer Part Number":exact,
            "Baseline MPN":previous.get("MPN",""),
        })
    assert set(item["Reference"] for item in manual) == set(MANUAL)
    assert len(smt) == len({row["Designator"] for row in smt})
    write_rows(args.output / "assembly-parts-candidate.csv", list(smt[0]), smt)
    write_rows(args.output / "manual-positions.csv", list(manual[0]), manual)
    print(f"{len(smt)} exact SMT selections and {len(manual)} manual, copper-only or unloaded positions.")


if __name__ == "__main__":
    main()
