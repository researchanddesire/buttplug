"""Apply the checked USB pair to a disposable product PCB copy with pcbnew 7."""

import argparse
from pathlib import Path
import shutil

import pcbnew as pcb


TOP_ROUTES = {
    "USB_DP": [
        (72.4, 105.0), (72.4, 104.7), (74.0, 103.1), (76.2, 103.1),
        (77.5, 101.8), (77.5, 95.9), (79.9, 93.5),
    ],
    "USB_DM": [
        (73.2, 105.0), (73.2, 104.395), (74.145, 103.45), (76.345, 103.45),
        (77.85, 101.945), (77.85, 101.5), (78.05, 101.3), (79.55, 101.3),
        (79.75, 101.1), (79.75, 99.9), (79.55, 99.7), (78.05, 99.7),
        (77.85, 99.5), (77.85, 98.55), (79.9, 96.5),
    ],
}
OLD_MODULE_VIAS = {(72.4, 107.1), (73.2, 107.1)}
OLD_DP_SERVICE_JUNCTION = (72.4, 104.9)
NEW_DP_SERVICE_JUNCTION = TOP_ROUTES["USB_DP"][0]
GROUND_STITCH = (72.9, 103.4)


def mm(point):
    return pcb.VECTOR2I(*(pcb.FromMM(coordinate) for coordinate in point))


def xy(vector):
    return round(pcb.ToMM(vector.x), 5), round(pcb.ToMM(vector.y), 5)


def add_track(board, net, layer, start, end):
    track = pcb.PCB_TRACK(board)
    track.SetLayer(layer)
    track.SetStart(mm(start))
    track.SetEnd(mm(end))
    track.SetWidth(pcb.FromMM(0.15))
    track.SetNetCode(board.FindNet(net).GetNetCode())
    track.SetLocked(True)
    board.Add(track)


def apply_usb_pair(source, output):
    if output.exists() or output.with_suffix(".kicad_pro").exists():
        raise ValueError(f"Use a new output basename for this copper pass: {output}")

    project = source.with_suffix(".kicad_pro")
    project.read_bytes()
    board = pcb.LoadBoard(str(source))
    obsolete_tracks = []
    moved = []
    for item in list(board.GetTracks()):
        net = item.GetNetname()
        if net not in TOP_ROUTES:
            continue

        if isinstance(item, pcb.PCB_VIA):
            center = xy(item.GetPosition())
            if center in OLD_MODULE_VIAS:
                obsolete_tracks.append(item)
            elif net == "USB_DP" and center == OLD_DP_SERVICE_JUNCTION:
                item.SetPosition(mm(NEW_DP_SERVICE_JUNCTION))
                moved.append(item)
            continue

        ends = {xy(item.GetStart()), xy(item.GetEnd())}
        if item.GetLayer() == pcb.F_Cu or (item.GetLayer() == pcb.B_Cu and ends & OLD_MODULE_VIAS):
            obsolete_tracks.append(item)
        elif net == "USB_DP" and item.GetLayer() == pcb.In2_Cu and OLD_DP_SERVICE_JUNCTION in ends:
            if xy(item.GetStart()) == OLD_DP_SERVICE_JUNCTION:
                item.SetStart(mm(NEW_DP_SERVICE_JUNCTION))
            else:
                item.SetEnd(mm(NEW_DP_SERVICE_JUNCTION))
            moved.append(item)

    if len(obsolete_tracks) != 17 or len(moved) != 2:
        raise ValueError("Unexpected baseline USB copper. Compare it to usb-pair-review.json before applying.")

    for item in obsolete_tracks:
        board.Remove(item)

    for net, points in TOP_ROUTES.items():
        for start, end in zip(points, points[1:]):
            add_track(board, net, pcb.F_Cu, start, end)
        x, y = points[0]
        add_track(board, net, pcb.B_Cu, (x, 105.9), (x, y))

    stitch = pcb.PCB_VIA(board)
    stitch.SetPosition(mm(GROUND_STITCH))
    stitch.SetViaType(pcb.VIATYPE_THROUGH)
    stitch.SetLayerPair(pcb.F_Cu, pcb.B_Cu)
    stitch.SetWidth(pcb.FromMM(0.5))
    stitch.SetDrill(pcb.FromMM(0.2))
    stitch.SetNetCode(board.FindNet("GND").GetNetCode())
    stitch.SetLocked(True)
    board.Add(stitch)
    pcb.SaveBoard(str(output), board)
    shutil.copyfile(project, output.with_suffix(".kicad_pro"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    apply_usb_pair(args.source, args.output)


if __name__ == "__main__":
    main()
