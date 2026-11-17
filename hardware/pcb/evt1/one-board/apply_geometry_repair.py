"""Apply the five verified footprint pose changes to a new KiCad PCB file."""

import argparse
import json
from pathlib import Path

import pcbnew as pcb

HERE = Path(__file__).resolve().parent


def xz(point):
    return pcb.ToMM(point.x) - 100, 100 - pcb.ToMM(point.y)


def xy(position):
    x, z = position
    return pcb.VECTOR2I(pcb.FromMM(100 + x), pcb.FromMM(100 - z))


def repair(board, moves):
    footprints = {footprint.GetReference(): footprint for footprint in board.GetFootprints()}
    for ref, pose in moves.items():
        footprint = footprints[ref]
        old = pose["old"]
        center = xz(footprint.GetPosition())
        angle = footprint.GetOrientationDegrees() % 360
        if any(abs(value - expected) > .00001 for value, expected in zip(center, old["native_xz"])):
            raise ValueError(f"{ref} existing pose differs from repair input: {center}")
        if abs(angle - old["angle"] % 360) > .00001:
            raise ValueError(f"{ref} existing angle differs from repair input: {angle}")
        assert footprint.GetLayer() == pcb.B_Cu, ref
    for ref, pose in moves.items():
        footprint = footprints[ref]
        footprint.SetOrientationDegrees(pose["angle"])
        footprint.SetPosition(xy(pose["native_xz"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"output already exists: {args.output}")
    report = json.loads((HERE / "geometry-repair.json").read_text())
    board = pcb.LoadBoard(str(args.source.resolve()))
    repair(board, report["moves"])
    pcb.SaveBoard(str(args.output.resolve()), board)
    print("Applied five B-side mechanical pose changes on a separate board copy.")


if __name__ == "__main__":
    main()
