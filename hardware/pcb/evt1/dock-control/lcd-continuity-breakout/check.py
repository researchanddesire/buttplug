"""Audit the continuity PCB and native fabrication exports."""

from collections import defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile

from build import CANDIDATE, HERE, LID_SHA256, NAME, j302_footprint, pad_decimal_signature, sexp


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(folder):
    board_path = HERE / f"{NAME}.kicad_pcb"
    source = CANDIDATE / "dock-lid-jst-candidate.kicad_pcb"
    assert digest(source) == LID_SHA256
    source_socket = j302_footprint(sexp.parse(source.read_text()))
    board = sexp.parse(board_path.read_text())
    socket, probes = sexp.children(board, "footprint")
    sockets = sexp.children(socket, "pad")
    assert list(map(pad_decimal_signature, sockets)) == list(
        map(pad_decimal_signature, sexp.children(source_socket, "pad"))
    )
    socket_nets = {pad[1].value: sexp.child(pad, "net")[2].value for pad in sockets if pad[1].value != "MP"}
    probe_nets = {
        pad[1].value: sexp.child(pad, "net")[2].value for pad in sexp.children(probes, "pad")
    }
    assert socket_nets == probe_nets == {str(pin): f"PIN_{pin:02d}" for pin in range(1, 28)}
    assert all(sexp.child(pad, "net") is None for pad in sockets if pad[1].value == "MP")

    drc = json.loads((folder / "drc.json").read_text())
    assert drc["kicad_version"] == "10.0.8"
    assert not any(drc[key] for key in ("violations", "unconnected_items", "ignored_checks"))
    project_path = HERE / f"{NAME}.kicad_pro"
    project = json.loads(project_path.read_text())
    assert not project["board"]["design_settings"]["drc_exclusions"]

    netlist = defaultdict(list)
    for line in (folder / f"{NAME}.d356").read_text().splitlines():
        if line.startswith(("317", "327")):
            net = line[3:17].strip()
            reference = line[20:26].strip()
            pin = line[27:31].strip()
            netlist[net].append((reference, pin))
    expected_netlist = {f"PIN_{pin:02d}": [("J302", str(pin)), ("TP1", str(pin))] for pin in range(1, 28)}
    expected_netlist["N/C"] = [("J302", "MP"), ("J302", "MP")]
    assert dict(netlist) == expected_netlist, netlist

    fab = folder / f"{NAME}-fab.zip"
    with ZipFile(fab) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {
            f"{NAME}-{suffix}"
            for suffix in ("F_Cu.gtl", "B_Cu.gbl", "F_Mask.gts", "B_Mask.gbs",
                           "F_Silkscreen.gto", "F_Paste.gtp", "Edge_Cuts.gm1", "PTH.drl")
        }
        drill = archive.read(f"{NAME}-PTH.drl").decode("ascii")
        assert "METRIC" in drill
        assert re.findall(r"(?m)^T\d+C([\d.]+)", drill) == ["1.000"]
        hits = re.findall(r"(?m)^X(-?[\d.]+)Y(-?[\d.]+)$", drill)
        assert sorted(round(float(x), 2) for x, _ in hits) == [
            round(100 + (pin - 14) * 2.54, 2) for pin in range(1, 28)
        ]
        assert {abs(float(y)) for _, y in hits} == {13.0}
        fab_members = {
            name: hashlib.sha256(archive.read(name)).hexdigest() for name in sorted(archive.namelist())
        }

    report = {
        "scope": "Passive JST socket continuity and isolation breakout",
        "source_J302_lid_board_sha256": digest(source),
        "source_J302_exact_pad_shapes_and_positions": len(sockets),
        "breakout_board_sha256": digest(board_path),
        "breakout_project_sha256": digest(project_path),
        "KiCad_version": drc["kicad_version"],
        "DRC_violations": 0,
        "DRC_unconnected": 0,
        "DRC_exclusions_or_ignored": 0,
        "unique_two_endpoint_nets": len(socket_nets),
        "plated_drill_hits_1mm": len(hits),
        "isolated_mechanical_socket_pads": 2,
        "files": {
            path.name: digest(path)
            for path in (folder / "drc.json", folder / f"{NAME}.d356", fab, HERE / "build.py", HERE / "check.py")
        },
        "fabrication_zip_members_sha256": fab_members,
        "received_numbering_and_continuity_verified": False,
    }
    (folder / "review.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"{len(socket_nets)} independent paths, {len(hits)} native plated drill hits and DRC pass")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
