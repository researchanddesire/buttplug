"""Fixed UV-C hardware and blind interlock pockets for the compact dock."""

from hashlib import sha256
import json

import FreeCAD as App
import Part

from compass_datums import box_xyz

V = App.Vector
LED_SOURCE_SUBPATH = "base/pcb/dock-uv-base.step"
LED_MPN = "VLMU35CB20-275-120"
RAIL_X = (29.0, 30.5)
RAIL_Y = (43.0, 115.0)
RAIL_Z = (12.0, 47.0)
PCB_X = (27.8, 28.8)
PCB_Z = (17.0, 45.0)
THERMOSTAT_MPN = "67L045"
NTC_MPN = "NTCLE413E2103F524A"
HALL_STATIONS = ((-31.0, -9.2), (31.0, -9.2))
# Sensor is 5.5 mm toward the short end of the existing 16 mm Hall board.
HALL_BOARD_CHIP_OFFSET = 5.5
HALL_ROOF_BOTTOM_Z = 32.9
TARGET_Z = 34.18
TARGET_R = 1.0
RAIL_FASTENER_Y = (49.0, 109.0)
RAIL_FASTENER_Z = 14.65
BAY_TOP_Z = 6.6
FEED_X, FEED_Y = 33.1, 59.0
FEED_R = 1.8

ALUMINUM = (0.69, 0.73, 0.76)
PCB_GREEN = (0.10, 0.31, 0.27)
INSULATOR = (0.45, 0.48, 0.52)
CERAMIC = (0.92, 0.89, 0.79)
SENSOR = (0.30, 0.33, 0.38)
SEAL = (0.16, 0.17, 0.20)


def side_box(side, x, y, z):
    return box_xyz(side * x[0], side * x[1], *y, *z)


def hall_target_x(board_x):
    return board_x + HALL_BOARD_CHIP_OFFSET * (1 if board_x > 0 else -1)


def rail_fastener_cylinder(side, y, x, radius, length):
    return Part.makeCylinder(radius, length, V(side * x, y, RAIL_FASTENER_Z), V(side, 0, 0))


def add_uv_mounts(base, lid, floor, rim):
    """Cut service cavities from below and integrate the mounts into the base and lid."""
    bay = box_xyz(-35.3, 35.3, -13, 119, 2.0, BAY_TOP_Z)
    # Cable feedthroughs are the only new openings into the optical chamber.
    feed_bores = [Part.makeCylinder(FEED_R, floor - BAY_TOP_Z + 1.0,
                                    V(side * FEED_X, FEED_Y, BAY_TOP_Z - 0.5))
                  for side in (-1, 1)]
    wells = [box_xyz(x - 8.3, x + 8.3, y - 4.65, y + 4.65, 2.25, HALL_ROOF_BOTTOM_Z)
             for x, y in HALL_STATIONS]
    base = base.cut([bay, *feed_bores, *wells])
    # Fused posts bridge the chamber floor and the outer wall. Seats take modest
    # rail loads. The separate hardware envelopes stop at the seat faces.
    posts = [side_box(side, (RAIL_X[1], 36.25), (y - 3.3, y + 3.3), (floor - 0.15, 17.5))
             for side in (-1, 1) for y in RAIL_FASTENER_Y]
    pilots = [rail_fastener_cylinder(side, y, RAIL_X[1] - 0.1, 0.86, 4.9)
              for side in (-1, 1) for y in RAIL_FASTENER_Y]
    base = base.fuse(posts).cut(pilots).removeSplitter()
    # Targets sit in blind lid tabs over the fixed Hall boards. The tabs are
    # outside the chamber skirt and open only from the lid underside.
    target_sites = [(hall_target_x(x), y) for x, y in HALL_STATIONS]
    tabs = [box_xyz(x - 4.6, x + 4.6, y - 3.3, y + 4.6, rim, rim + 3.1)
            for x, y in target_sites]
    passages = [Part.makeCylinder(TARGET_R + 0.1, TARGET_Z + 1.06 - rim, V(x, y, rim))
                for x, y in target_sites]
    lid = lid.fuse(tabs).cut(passages).removeSplitter()
    return base, lid


def selected_emitter(uv_folder):
    """Extract the ten OEM solids at LED x=-42/Y94 from the matched UV assembly."""
    path = uv_folder / LED_SOURCE_SUBPATH
    digest = sha256(path.read_bytes()).hexdigest()
    mcad = json.loads((path.parent / "mcad.json").read_text())
    assert digest == mcad["STEP_sha256"], "UV STEP changed, refresh the reviewed source"
    solids = []
    for solid in Part.read(str(path)).Solids:
        bounds = solid.BoundBox
        if (bounds.XMin >= -43.75 and bounds.XMax <= -40.25
                and bounds.YMin >= 92.25 and bounds.YMax <= 95.75
                and bounds.ZMin >= 0.979 and bounds.ZMax <= 2.756):
            solids.append(solid)
    assert len(solids) == 10, f"Expected 10 Vishay LED solids, found {len(solids)}"
    emitter = Part.makeCompound(solids)
    emitter.translate(V(42, -94, -0.98))
    assert abs(emitter.BoundBox.ZMax - 1.775) < 0.001
    return emitter, digest


def uv_hardware(uv_folder, floor):
    emitter, digest = selected_emitter(uv_folder)
    fixed = []
    sources = []
    moving = []
    for side, label in ((-1, "Left"), (1, "Right")):
        rail = side_box(side, RAIL_X, RAIL_Y, RAIL_Z)
        clearances = [rail_fastener_cylinder(side, y, RAIL_X[0] - 0.1, 1.1, 1.7)
                      for y in RAIL_FASTENER_Y]
        rail = rail.cut(clearances).removeSplitter()
        fixed.extend([
            (label + "UVRail", label + " aluminum heat rail, 72 × 35 × 1.5 stock",
             rail, ALUMINUM),
            (label + "UVBoard", label + " series emitter PCB envelope",
             side_box(side, PCB_X, RAIL_Y, PCB_Z), PCB_GREEN),
            (label + "UVPad", label + " insulating thermal interface",
             side_box(side, (PCB_X[1], RAIL_X[0]), RAIL_Y, PCB_Z), INSULATOR),
            (label + "UVCutoff", label + " independent " + THERMOSTAT_MPN + " thermostat envelope",
             side_box(side, (RAIL_X[1], 35.2), (72, 87.6), (18, 28.5)), SENSOR),
            (label + "UVNTC", label + " " + NTC_MPN + " thermistor head envelope",
             side_box(side, (RAIL_X[1], 32.6), (92, 96), (36.9, 39.1)), SENSOR),
            (label + "UVFeedSeal", label + " opaque potted wire feedthrough envelope",
             Part.makeCylinder(FEED_R, floor - BAY_TOP_Z, V(side * FEED_X, FEED_Y, BAY_TOP_Z)), SEAL),
        ])
        for i, y in enumerate(RAIL_FASTENER_Y, 1):
            # Nominal fastener core is used inside the thread-forming pilot.
            shaft = rail_fastener_cylinder(side, y, RAIL_X[0], 0.80, 5.7)
            head = rail_fastener_cylinder(side, y, RAIL_X[0] - 1.35, 1.9, 1.35)
            fixed.append((label + f"UVRailScrew{i}", label + f" UV rail fastener {i} envelope",
                          shaft.fuse(head).removeSplitter(), ALUMINUM))
        # High/low sites swap fore to aft across the two walls. The source LED
        # optical +Z points into the chamber after the proper Y rotation.
        for vertical, z in (("High", 42.0), ("Low", 20.0)):
            forward = (side == -1) == (vertical == "High")
            y = 55.0 if forward else 103.0
            led = emitter.copy()
            led.rotate(V(), V(0, 1, 0), -side * 90)
            led.translate(V(side * (PCB_X[0] - 0.05), y, z))
            fixed.append((label + vertical + "UV", label + " " + vertical.lower() + " " + LED_MPN,
                          led, CERAMIC))
            sources.append({"side": label.lower(), "height": vertical.lower(),
                            "optical_center_mm": [side * 25.975, y, z],
                            "optical_normal": [-side, 0, 0]})

    hall_sites = []
    for (x, y), label in zip(HALL_STATIONS, ("Left", "Right")):
        chip_x = hall_target_x(x)
        side = 1 if x > 0 else -1
        perimeter = [(-3.5, -13.5), (3.5, -13.5), (4.4, -12), (4.4, 2.5),
                     (-4.4, 2.5), (-4.4, -12)]
        points = [V(chip_x + side * vy, y - side * vx, 30) for vx, vy in perimeter]
        board = Part.Face(Part.makePolygon(points + points[:1])).extrude(V(0, 0, 0.8))
        components = box_xyz(x - 7.8, x + 7.8, y - 4.2, y + 4.2, 30.8, 32.3)
        fixed.append((label + "Hall", label + " wired Hall receiver envelope, 8.8 × 16 mm",
                      Part.makeCompound([board, components]), PCB_GREEN))
        target = Part.makeCylinder(TARGET_R, 1.0, V(chip_x, y, TARGET_Z))
        moving.append((label + "HallTarget", label + " swappable lid target envelope, up to Ø2 × 1 mm",
                       target, ALUMINUM))
        hall_sites.append({"side": label.lower(), "sensor_and_target_xy_mm": [chip_x, y],
                           "closed_target_to_component_envelope_mm": round(TARGET_Z - 32.3, 3)})

    source = {"file": "dock-uv/" + LED_SOURCE_SUBPATH, "sha256": digest, "mpn": LED_MPN,
              "source_optical_plane_mm": 2.755, "emitters": sources,
              "hall_stations": hall_sites}
    return fixed, moving, source
