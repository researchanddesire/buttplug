"""Compare native project board pads with the product and bench schematics."""

from hashlib import sha256
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / "tools"))
import kicad_sexp as sexp
from build_schematic import BENCH_PARTS, NAME, PRODUCT, PROBES, TERMINAL_UPDATES

PRODUCT_NET = PRODUCT / "compass-one-board-native.xml"
DEV_NET = HERE / f"{NAME}-native.xml"
DEV_PCB = HERE / f"{NAME}.kicad_pcb"


def schematic(path):
    source = ET.parse(path)
    parts = {p.get("ref"): (p.findtext("value"), p.findtext("footprint"))
             for p in source.findall("./components/comp")
             if p.findtext("footprint")}
    pins = {(n.get("ref"), n.get("pin")): net.get("name")
            for net in source.findall("./nets/net") for n in net.findall("node")
            if n.get("ref") in parts}
    return parts, pins


def board_pads():
    tree = sexp.parse(DEV_PCB.read_text())
    footprints = {}
    pads = {}
    for footprint in sexp.children(tree, "footprint"):
        text = next(t for t in sexp.children(footprint, "fp_text") if t[1].value == "reference")
        ref = text[2].value
        footprints[ref] = footprint[1].value
        for pad in sexp.children(footprint, "pad"):
            number = pad[1].value
            if not number:
                continue
            tag = sexp.child(pad, "net")
            value = tag[2].value if tag else None
            existing = pads.setdefault((ref, number), value)
            assert existing == value, (ref, number, existing, value)
    return footprints, pads


def count():
    product, product_pins = schematic(PRODUCT_NET)
    dev, dev_pins = schematic(DEV_NET)
    fp, pads = board_pads()
    removed = {"CT1", "CT2", "CT3", "CT4"}
    expected = {(ref, pin): net for ref, values in TERMINAL_UPDATES.items() for pin, net in values.items()}
    # U2 pins 7 and 8 share a schematic wire. Their native pad records are both checked.
    expected[("U2", "8")] = "DEV_3V3_REG"
    common = product.keys() - removed
    assert product.keys() - dev.keys() == removed
    assert all(product[ref] == dev[ref] for ref in common)
    retained = {p: net for p, net in product_pins.items() if p[0] in common}
    dev_retained = {p: net for p, net in dev_pins.items() if p[0] in common}
    assert set(retained) == set(dev_retained)
    actual_changes = {p: net for p, net in dev_retained.items() if net != retained[p]}
    assert actual_changes == expected, actual_changes
    for ref, _, nets, _, _ in BENCH_PARTS:
        assert tuple(dev_pins[(ref, str(i))] for i in range(1, len(nets) + 1)) == nets
    assert all(dev_pins[(ref, "1")] == net for ref, net in PROBES.items())
    assert fp.keys() - dev.keys() == {"H1", "H2", "H3", "H4"}
    assert all(fp[ref] == footprint for ref, (_, footprint) in dev.items())
    assert set(dev_pins) <= set(pads)
    assert all(net == dev_pins.get(p) for p, net in pads.items())
    return {"retained_product_positions": len(common), "retained_product_terminals": len(retained),
            "deliberate_split_terminal_count": len(expected), "dev_footprint_positions": len(dev),
            "dev_pad_assignments": len(pads), "source_sha256":
            {str(p.relative_to(HERE.parent)): sha256(p.read_bytes()).hexdigest()
             for p in (PRODUCT_NET, DEV_NET, DEV_PCB)}}


if __name__ == "__main__":
    print(json.dumps(count(), indent=2))
