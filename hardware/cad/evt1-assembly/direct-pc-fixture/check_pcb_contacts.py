"""Verify the saved dock P91–P94/J94 map and compact CT footprint parity."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "tools"))
import kicad_sexp as kicad

PCB = REPO / "hardware/pcb/evt1"
TARGETS = ("CT1", "CT2", "CT3", "CT4")
SPRING_PINS = ("P91", "P92", "P93", "P94")


def footprints(path, names):
    result = {}
    tree = kicad.parse(path.read_text())
    for fp in kicad.children(tree, "footprint"):
        ref = kicad.prop(fp, "Reference") or next(
            (item[2].value for item in kicad.children(fp, "fp_text") if item[1].value == "reference"), ""
        )
        if ref not in names:
            continue
        pads = []
        for pad in kicad.children(fp, "pad"):
            net = kicad.child(pad, "net")
            if net:
                pads.append({
                    "number": pad[1].value,
                    "type": pad[2].value,
                    "at_mm_deg": [float(t.value) for t in kicad.child(pad, "at")[1:]],
                    "size_mm": [float(t.value) for t in kicad.child(pad, "size")[1:]],
                    "drill_mm": float(kicad.value(pad, "drill")) if kicad.child(pad, "drill") else None,
                    "net": net[-1].value,
                })
        result[ref] = {
            "library": fp[1].value,
            "at_mm_deg": [float(t.value) for t in kicad.child(fp, "at")[1:]],
            "pads": sorted(pads, key=lambda p: p["number"])
        }
    assert set(result) == set(names), (path, list(result))
    return dict(sorted(result.items()))


def check(extra_board=None):
    layouts = {
        "active compact": PCB / "one-board/compass-one-board.kicad_pcb",
        "approved contact datum reference": PCB / "single-flange-routing/single-flange.kicad_pcb",
    }
    if extra_board:
        layouts["candidate packet"] = extra_board
    contacts = footprints(layouts["active compact"], TARGETS)
    for label, path in layouts.items():
        assert footprints(path, TARGETS) == contacts, (label, path)

    pins_path = PCB / "pins/pins-evt1.kicad_pcb"
    pins = footprints(pins_path, (*SPRING_PINS, "J94"))
    names = (
        ("GND", "GND"),
        ("USB_DM_CONTACT", "DOCK_DM"),
        ("USB_DP_CONTACT", "DOCK_DP"),
        ("DOCK_5V", "DOCK_5V"),
    )
    for i, ((target_net, pin_net), target, pin, pad) in enumerate(
        zip(names, TARGETS, SPRING_PINS, pins["J94"]["pads"], strict=True), 1
    ):
        target_pad, = contacts[target]["pads"]
        pin_pad, = pins[pin]["pads"]
        assert target_pad["net"] == target_net and target_pad["drill_mm"] == 1.02
        assert target_pad["size_mm"] == [3.2, 3.2]
        assert str(i) == pad["number"] and pad["net"] == pin_net == pin_pad["net"]
        assert contacts[target]["at_mm_deg"][:2] == [78 + 6 * i, 90], target
    return {
        "status": "pass",
        "sources": {
            label: {
                "file": str(path.relative_to(REPO)) if path.is_relative_to(REPO) else path.name,
                "sha256": sha256(path.read_bytes()).hexdigest(),
            }
            for label, path in (layouts | {"dock pin PCB": pins_path}).items()
        },
        "target_contacts": contacts,
        "pin_module": pins,
        "scope": "Four artwork contact datums and the pin-board net map. Package-height fit is separate."
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compare-board", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = json.dumps(check(args.compare_board), indent=2) + "\n"
    if args.output:
        args.output.write_text(report)
    print(report)
