#!/usr/bin/env python3
"""Verify saved EVT artwork and write a source-bound vendor review package."""
import csv
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

import pcbnew as k
from build_trial import BASE, HERE, BOARD, EXPECTED, PLANES, SITES, NTC, FOOT, WINDOW_X, WINDOW_HALF_Y, digest

CLI = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)
STAGING = OUT / "fabrication"
STAGING.mkdir(exist_ok=True)
BASEBOARD = BASE / "single-flange.kicad_pcb"
QUOTE = BASE / "assembly-quote"
NEW = {ref for pair in SITES for ref in pair[:2]}


def run(*args):
    subprocess.run([str(CLI), *map(str,args)], check=True)


def pad_map(b):
    return {(f.GetReference(),p.GetNumber(),p.GetNetname()) for f in b.GetFootprints()
            for p in f.Pads() if p.GetNetname()}


def placements(b):
    return {f.GetReference(): (str(f.GetPosition()), f.GetOrientationDegrees(), f.GetLayer(),
            sorted((p.GetNumber(),str(p.GetPosition()),str(p.GetSize()),str(p.GetDrillSize()),
                    p.GetLayerSet().FmtHex(),p.GetNetname()) for p in f.Pads()))
            for f in b.GetFootprints()}


def read_nets(p):
    return {(n.get("ref"),n.get("pin"),net.get("name"))
            for net in ET.parse(p).findall("nets/net")
            for n in net.findall("node")}


def copper_signature(item):
    return (str(item.GetStart()), str(item.GetEnd()), item.GetLayerName(),
            item.GetNetname(), item.GetWidth())



def crosses_window(item, x_bounds, y_bounds):
    """Conservative window overlap using the trace radius on both axes."""
    radius = k.ToMM(item.GetWidth()) / 2
    start = [k.ToMM(v) for v in item.GetStart()]
    end = [k.ToMM(v) for v in item.GetEnd()]
    entry, exit_ = 0., 1.
    for a, b, (low, high) in zip(start, end, (x_bounds, y_bounds)):
        low -= radius
        high += radius
        if a == b:
            if not low <= a <= high:
                return False
            continue
        lower, upper = sorted(((low-a)/(b-a), (high-a)/(b-a)))
        entry, exit_ = max(entry, lower), min(exit_, upper)
    return entry <= exit_


def drc(board_path,p):
    # KiCad 7's global footprint table cannot be initialized twice in one process.
    code = ("import pcbnew as k,sys; b=k.LoadBoard(sys.argv[1]); "
            "assert k.WriteDRCReport(b,sys.argv[2],k.EDA_UNITS_MILLIMETRES,True)")
    subprocess.run([sys.executable,"-c",code,str(board_path),str(p)],check=True)
    report=p.read_text()
    assert "** Found 0 unconnected pads **" in report
    assert "** Found 0 Footprint errors **" in report
    findings=Counter(re.findall(r"^\[([^\]]+)\]",report,re.M))
    assert not findings.keys()-{"lib_footprint_issues","lib_footprint_mismatch"},p
    return findings


def export_and_verify():
    assert digest(BASEBOARD) == EXPECTED
    b = k.LoadBoard(str(BOARD))
    for path,label in ((BASE/"single-flange.kicad_sch","baseline"),(BOARD.with_suffix(".kicad_sch"),"trial")):
        run("sch","export","netlist","--format","kicadxml","-o",OUT/f"{label}.xml",path)
    native = read_nets(OUT/"trial.xml")
    baseline = read_nets(OUT/"baseline.xml")
    delta = {(r,str(i),net) for ref,j,_,signal,ret,_ in SITES for r in (ref,j)
             for i,net in enumerate((signal,ret),1)}
    assert native == baseline|delta
    assert pad_map(b) == native,(pad_map(b)-native,native-pad_map(b))
    trial_placements = placements(b)
    trial_drc = drc(BOARD,OUT/"trial-drc.rpt")
    trial_copper = Counter(map(copper_signature,b.GetTracks()))

    area_check = {}
    zones = list(b.Zones())
    layer_ids = {"F.Cu":k.F_Cu,"In1.Cu":k.In1_Cu,"In2.Cu":k.In2_Cu,"B.Cu":k.B_Cu}
    for area in zones:
        if "thermal no-pour" not in area.GetZoneName():
            continue
        assert area.GetIsRuleArea() and area.GetDoNotAllowCopperPour()
        assert all(area.IsOnLayer(layer_ids[n]) for n in PLANES)
        result = {}
        for layer,id_ in layer_ids.items():
            total = 0.
            for z in zones:
                if z.GetIsRuleArea() or not z.HasFilledPolysForLayer(id_):
                    continue
                poly = k.SHAPE_POLY_SET()
                poly.BooleanIntersection(area.Outline(),z.GetFilledPolysList(id_),k.SHAPE_POLY_SET.PM_FAST)
                total += abs(poly.Area()) / 1e12
            assert total < 1e-9,(area.GetZoneName(),layer,total)
            result[layer] = total
        area_check[area.GetZoneName()] = result
    assert len(area_check)==2
    for ref,_,y,signal,ret,_ in SITES:
        involved = [t for t in b.GetTracks() if crosses_window(t,WINDOW_X,(y-WINDOW_HALF_Y,y+WINDOW_HALF_Y))]
        assert len(involved)==2, ref
        assert {t.GetNetname() for t in involved} == {signal,ret}, ref
        assert all(t.GetLayer()==k.B_Cu and t.GetWidth()==k.FromMM(.15) for t in involved), ref

    # Reuse the same native runtime for the unmodified board after finishing all
    # operations on b. KiCad 7 can reset project settings when a board is loaded.
    version = k.Version()
    old = k.LoadBoard(str(BASEBOARD))
    assert pad_map(old) == baseline
    assert {r:v for r,v in trial_placements.items() if r not in NEW} == placements(old)
    old_copper = Counter(map(copper_signature,old.GetTracks()))
    retired, added = old_copper-trial_copper, trial_copper-old_copper
    assert sum(retired.values()) == 2 and all(i[2:4]==("In2.Cu","3V3") for i in retired)
    assert sum(added.values()) == 14 and all(i[3] in {"3V3","PACK_NTC","PACK_NTC_RET","PACK_GUARD","PACK_GUARD_RET"} for i in added)
    old_drc = drc(BASEBOARD,OUT/"baseline-drc.rpt")
    assert old_drc == trial_drc,(old_drc,trial_drc)
    assert digest(BASEBOARD) == EXPECTED

    report = {"KiCad":version,"native_drc_trial":dict(trial_drc),"native_drc_baseline":dict(old_drc),
              "unconnected":0,"native_footprint_errors":0,"unchanged_existing_positions":len(placements(old)),
              "native_pcb_schematic_electrical_pads":len(native),
              "retained_electrical_terminals":len(baseline),"new_native_pad_terminals":sorted(delta),
              "removed_copper":list(retired.elements()),"new_copper":list(added.elements()),
              "copper_pour_intersection_in_keepout_mm2":area_check,
              "copper_traces_crossing_each_keepout":"Only two intended 0.15 mm B.Cu sensor traces per window.",
              "source_sha256":digest(BASEBOARD),"variant_sha256":digest(BOARD)}
    (OUT/"verification.json").write_text(json.dumps(report,indent=2)+"\n")

    layers = PLANES+("F.Mask","B.Mask","F.Paste","B.Paste","F.SilkS","B.SilkS","Edge.Cuts")
    run("pcb","export","gerbers","--layers",",".join(layers),"--output",str(STAGING)+"/",BOARD)
    run("pcb","export","drill","--excellon-separate-th","--output",str(STAGING)+"/",BOARD)
    run("pcb","export","pos","--format","csv","--units","mm","--side","both","--smd-only",
        "-o",OUT/"smt-positions.csv",BOARD)
    for kind in ("PTH","NPTH"):
        path = next(STAGING.glob(f"*-{kind}.drl"))
        with ZipFile(QUOTE/"single-flange-evt1-fabrication-quote.zip") as zipf:
            reference = zipf.read(next(n for n in zipf.namelist() if n.endswith(f"-{kind}.drl"))).decode()
        coord = lambda data: sorted(re.findall(r"^X[-\d.]+Y[-\d.]+",data,re.M))
        assert coord(path.read_text())==coord(reference),kind
    with (OUT/"smt-positions.csv").open() as f:
        pos = {row["Ref"]:row for row in csv.DictReader(f)}
    with (QUOTE/"single-flange-smt-positions.csv").open() as f:
        old = {row["Ref"]:row for row in csv.DictReader(f)}
    assert set(pos)==set(old)|{"TH1","TH2"}
    assert set(old) <= set(pos)
    for r in old:
        assert all(pos[r][field]==old[r][field] for field in ("Ref","Val","Package","Side")),r
        for field in ("PosX","PosY"):
            assert abs(float(pos[r][field])-float(old[r][field]))<1e-6,(r,field)
        assert (float(pos[r]["Rot"])-float(old[r]["Rot"]))%360<1e-6,r
    with (QUOTE/"single-flange-smt-parts.csv").open() as f:
        old_parts = list(csv.DictReader(f))
    with (OUT/"smt-parts.csv").open("w",newline="") as f:
        writer = csv.DictWriter(f,fieldnames=list(old_parts[0]))
        writer.writeheader()
        writer.writerows(old_parts)
        writer.writerow(dict(Manufacturer="Vishay", MPN=NTC, Quantity_per_board=2, References="TH1 TH2",
            Schematic_value=NTC,Footprint="ThermalTrial:"+FOOT["TH"],
            Assembly_note="Bottom side. Reflow. No loading force on the sensing chip.",
            Manufacturer_source="https://www.vishay.com/docs/29003/ntcs0402e3t.pdf"))

    sources=[*sorted(STAGING.glob("*")),OUT/"verification.json",OUT/"trial-drc.rpt",OUT/"baseline-drc.rpt",
             OUT/"smt-positions.csv",OUT/"smt-parts.csv", HERE/"README.md",
             QUOTE/"fabrication-request.json", QUOTE/"single-flange-manual-targets.csv"]
    package = OUT/"Compass-EVT-Flange-Thermal-R1-quote.zip"
    with ZipFile(package,"w",ZIP_DEFLATED) as z:
        for path in sources:
            z.write(path, str(path.relative_to(OUT)) if path.is_relative_to(OUT) else path.name)
    with ZipFile(package) as z:
        assert z.testzip() is None


if __name__=="__main__":
    export_and_verify()
