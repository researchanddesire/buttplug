"""Check the bench host-key pinout and allowed closures against the native XML."""

from hashlib import sha256
from itertools import combinations
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from build_schematic import HOST_KEY_NETS, NAME
from check_contract import board_pads

HERE = Path(__file__).resolve().parent
NETLIST = HERE / f"{NAME}-native.xml"
BOARD = HERE / f"{NAME}.kicad_pcb"

KEYS = {
    "OFF": (),
    "PC": ((1, 2), (3, 4), (7, 10)),
    "DOCK": ((2, 6), (4, 8), (9, 10)),
}
HOSTS = {
    "PC": ("DEV_USB_DM", "DEV_USB_DP", "DEV_USB_5V"),
    "DOCK": ("DEV_DOCK_DM", "DEV_DOCK_DP", "DEV_DOCK_5V"),
}
DEVICE = ("USB_DM_CONTACT", "USB_DP_CONTACT", "DOCK_5V")
PROFILES = {
    "battery_or_simulator_only": "OFF",
    "direct_pc_at_j110": "PC",
    "local_dock_host_at_j111": "DOCK",
    "pc_via_dock_at_j111": "DOCK",
}


def check():
    root = ET.parse(NETLIST)
    nets = {(node.get("ref"), node.get("pin")): net.get("name")
            for net in root.findall("./nets/net") for node in net.findall("node")}
    pinout = dict(enumerate(HOST_KEY_NETS, 1))
    footprints, pads = board_pads()
    assert "J113" not in footprints and "J114" not in footprints
    assert {int(p): net for (ref, p), net in pads.items() if ref == "J112"} == pinout
    assert all(nets[("J112", str(pin))] == net for pin, net in pinout.items())
    assert tuple(nets[("J111", str(pin))] for pin in range(1, 5)) == ("GND", *HOSTS["DOCK"])
    for a_pin, b_pin, pc_net in zip(("A7", "A6", "A4"), ("B7", "B6", "B4"), HOSTS["PC"]):
        assert nets[("J110", a_pin)] == nets[("J110", b_pin)] == pc_net

    equivalents = {}
    for key, links in KEYS.items():
        used = [pin for pair in links for pin in pair]
        assert len(used) == len(set(used)) and 5 not in used
        connected = {frozenset((pinout[a], pinout[b])) for a, b in links}
        target = {frozenset(pair) for pair in zip(HOSTS[key], DEVICE)} if key != "OFF" else set()
        assert connected == target
        for pc, dock in combinations(HOSTS.values(), 2):
            assert not any(frozenset((a, b)) in connected for a in pc for b in dock)
        equivalents[key] = {
            "closures": links,
            "empty_cavities": sorted(pinout.keys() - set(used)),
            "net_pairs": [sorted(pair) for pair in sorted(connected, key=lambda pair: sorted(pair))],
        }

    return {
        "board_sha256": sha256(BOARD.read_bytes()).hexdigest(),
        "netlist_sha256": sha256(NETLIST.read_bytes()).hexdigest(),
        "pinout": pinout,
        "keys": equivalents,
        "profiles": PROFILES,
        "scope": "PCB and crimp-key connectivity. In the two DOCK profiles the external dock selects the USB host.",
    }


if __name__ == "__main__":
    print(json.dumps(check(), indent=2))
