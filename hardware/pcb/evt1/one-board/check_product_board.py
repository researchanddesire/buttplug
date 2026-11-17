"""Audit native pad assignments and the mechanically registered flange interfaces."""

import argparse
import hashlib
import json
from pathlib import Path

import pcbnew as pcb

from place_product_pcb import netlist, xz


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def audit(board_path, xml_path):
    board = pcb.LoadBoard(str(board_path))
    components, expected = netlist(xml_path)
    footprints = {footprint.GetReference(): footprint for footprint in board.GetFootprints()}
    assert set(footprints) == set(components) | {"MH1", "MH2", "MH3", "MH4"}
    logical, physical = {}, []
    mismatches = []
    for ref, component in components.items():
        footprint = footprints[ref]
        if footprint.GetValue() != component.findtext("value"):
            mismatches.append({"reference":ref, "field":"value", "board":footprint.GetValue(),
                               "schematic":component.findtext("value")})
        lib = footprint.GetFPID()
        identifier = f"{lib.GetLibNickname()}:{lib.GetLibItemName()}"
        if identifier != component.findtext("footprint"):
            mismatches.append({"reference":ref,"field":"footprint","board":identifier,
                               "schematic":component.findtext("footprint")})
        for pad in footprint.Pads():
            key = (ref, pad.GetNumber())
            actual = pad.GetNetname()
            assert actual == expected.get(key, ""), (key, actual, expected.get(key))
            if key in expected:
                logical[key] = actual
            physical.append(key)
    assert logical == expected, set(expected) - set(logical)
    for index, center in enumerate((-16, -10, -4, 2), start=1):
        pad, = footprints[f"CT{index}"].Pads()
        assert tuple(pad.GetDrillSize()) == (1020000,1020000)
        assert tuple(pad.GetSize()) == (3200000,3200000)
        point = xz(pad.GetPosition())
        assert abs(point[0]-center)<1e-8 and abs(point[1]-10)<1e-8
    settings = board.GetDesignSettings()
    assert settings.GetBoardThickness() == 1000000
    assert board.GetCopperLayerCount() == 4
    in1_routes = [
        track for track in board.GetTracks()
        if not isinstance(track, pcb.PCB_VIA) and track.GetLayer() == pcb.In1_Cu
    ]
    # Reserve the radio and USB return region on In1. The only signal copper
    # on this layer is the checked SYS crossover beside the right regulator.
    assert len(in1_routes) <= 1
    for route in in1_routes:
        assert route.GetNetname() == "SYS" and route.GetWidth() == pcb.FromMM(.5)
        assert all(120 <= pcb.ToMM(at.x) <= 128 for at in (route.GetStart(), route.GetEnd()))
    return {"board_sha256":sha(board_path), "native_xml_sha256":sha(xml_path),
            "footprints":len(components), "logical_pin_assignments":len(logical),
            "physical_pad_instances":len(physical), "value_or_library_mismatches":mismatches,
            "fixed_contact_datums_and_drills":True, "four_layers_and_1_mm_laminate":True,
            "in1_right_side_sys_crossovers":len(in1_routes)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board",type=Path)
    parser.add_argument("native_netlist",type=Path)
    parser.add_argument("report",type=Path)
    args = parser.parse_args()
    report = audit(args.board, args.native_netlist)
    args.report.write_text(json.dumps(report,indent=2)+"\n")
    print(f"Verified {report['logical_pin_assignments']} pad assignments on {report['footprints']} designators.")
    if report["value_or_library_mismatches"]:
        print("Native metadata differences are in the report.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
