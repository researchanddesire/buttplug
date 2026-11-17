"""Bind selected wired Main footprints to local STEP files and height limits."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRep import BRep_Builder
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepCheck import BRepCheck_Analyzer
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakePrism
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
from OCC.Core.gp import gp_Pnt, gp_Vec
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Reader, STEPControl_Writer
from OCC.Core.TopAbs import TopAbs_SOLID
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopoDS import TopoDS_Compound

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[4] / 'tools'))
import kicad_sexp as kicad

MODELS = HERE / 'WiredMain.3dshapes'
FOOTPRINTS = HERE / 'WiredMain.pretty'
CONTRACT = HERE / 'circuit-contract.json'
DOCK_SPACE = HERE.parents[3] / 'cad/evt1-assembly/dock-harness-trial/wired-main-space-review/space-check.json'

# Package outline dimensions include terminal tips when the drawing specifies them.
PACKAGE_LIMITS = {
    'U151': ('846AP', (4.90, 3.10, 1.10), 'https://www.onsemi.com/download/package-drawing/pdf/846ap.pdf'),
    'U152': ('DRT', (1.00, 1.00, 0.45), 'https://www.ti.com/packaging/docs/searchtipackages.tsp?packageName=SO'),
    'U153': ('DBV0006A', (3.00, 3.05, 1.45), 'https://www.ti.com/lit/ds/symlink/tps2553-q1.pdf'),
    'U154': ('DBV0005A', (3.00, 3.05, 1.45), 'https://www.ti.com/lit/ds/symlink/tps7a20.pdf'),
    'U155': ('DSE0006A', (1.55, 1.55, 0.80), 'https://www.ti.com/lit/ds/symlink/tps3890.pdf'),
    'U156': ('DBV0006A', (3.00, 3.05, 1.45), 'https://www.ti.com/lit/ds/symlink/tps3808.pdf'),
    'U157': ('PW0014A', (6.60, 5.10, 1.20), 'https://www.ti.com/lit/ds/symlink/sn74hcs21.pdf'),
    'U158': ('PW0014A', (6.60, 5.10, 1.20), 'https://www.ti.com/lit/ds/symlink/sn74hcs00.pdf'),
    'U159': ('DCK0006A', (2.40, 2.15, 1.10), 'https://www.ti.com/lit/ds/symlink/sn74lvc2g17.pdf'),
    'U160': ('QFN-56 reduced EP', (7.00, 7.00, 0.90), 'https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf#page=608'),
    'U161': ('UX', (3.10, 2.10, 0.60), 'https://static.datasheets.com/doc/3906047-winbond-w25q16jvssiq-ds.pdf#page=67'),
    'U162': ('RSV0016A', (1.85, 2.65, 0.55), 'https://www.ti.com/lit/ds/symlink/tmux1511.pdf'),
    'U163': ('DCK0006A', (2.40, 2.15, 1.10), 'https://www.ti.com/lit/ds/symlink/sn74lvc2g17.pdf'),
    'Y151': ('ABM8-272-T3', (3.40, 2.70, 0.80), 'https://abracon.com/datasheets/ABM8-272-T3.pdf'),
}
ALTERNATE_MODELS = {
    'Onsemi_846AP_MSOP10': 'Package_SO.3dshapes/MSOP-10_3x3mm_P0.5mm.step',
    'TI_DSE0006A': 'Package_SON.3dshapes/WSON-6_1.5x1.5mm_P0.5mm.step',
    'Winbond_USON-8_2x3mm_P0.5mm_UX': 'Package_SON.3dshapes/Winbond_USON-8-1EP_3x2mm_P0.5mm_EP0.2x1.6mm.step',
}
PASSIVE_LIBRARIES = {
    'C_0402_1005Metric': 'Capacitor_SMD',
    'C_0603_1608Metric': 'Capacitor_SMD',
    'C_0805_2012Metric': 'Capacitor_SMD',
    'R_0402_1005Metric': 'Resistor_SMD',
    'R_0603_1608Metric': 'Resistor_SMD',
}


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def make_rsv_step(path):
    # TI 4220314/C nominal package, not the wider PCB solder-land geometry.
    # STEP Y is opposite to KiCad's top-view pad coordinates.
    builder = BRep_Builder()
    package = TopoDS_Compound()
    builder.MakeCompound(package)
    outline = BRepBuilderAPI_MakePolygon()
    for x, y in [(-0.9, 1.2), (-0.8, 1.3), (0.9, 1.3), (0.9, -1.3), (-0.9, -1.3)]:
        outline.Add(gp_Pnt(x, y, 0.025))
    outline.Close()
    face = BRepBuilderAPI_MakeFace(outline.Wire()).Face()
    builder.Add(package, BRepPrimAPI_MakePrism(face, gp_Vec(0, 0, 0.475)).Shape())

    for pin in range(1, 17):
        side, station = divmod(pin - 1, 4)
        span = (-0.6, -0.2, 0.2, 0.6)[station]
        length = 0.50 if pin == 16 else 0.40
        if side == 0:
            x, y, w, h = -0.9, -span - 0.1, length, 0.2
        elif side == 1:
            x, y, w, h = span - 0.1, -1.3, 0.2, length
        elif side == 2:
            x, y, w, h = 0.9 - length, span - 0.1, length, 0.2
        else:
            x, y, w, h = -span - 0.1, 1.3 - length, 0.2, length
        builder.Add(package, BRepPrimAPI_MakeBox(gp_Pnt(x, y, 0), w, h, 0.025).Shape())
    writer = STEPControl_Writer()
    assert writer.Transfer(package, STEPControl_AsIs) == IFSelect_RetDone
    assert writer.Write(str(path)) == IFSelect_RetDone


def measure(path):
    reader = STEPControl_Reader()
    assert reader.ReadFile(str(path)) == IFSelect_RetDone
    assert reader.TransferRoots() > 0
    shape = reader.OneShape()
    assert BRepCheck_Analyzer(shape).IsValid(), path
    solids = TopExp_Explorer(shape, TopAbs_SOLID)
    count = 0
    while solids.More():
        count += 1
        solids.Next()
    bounds = Bnd_Box()
    brepbndlib.AddOptimal(shape, bounds, False, False)
    x0, y0, z0, x1, y1, z1 = bounds.Get()
    assert abs(z0) < 0.005 and count > 0, (path, bounds.Get())
    return {'sha256': digest(path), 'valid_solids': count,
            'bounds_xyzxyz_mm': [round(v, 6) for v in bounds.Get()],
            'size_xyz_mm': [round(x1 - x0, 6), round(y1 - y0, 6), round(z1 - z0, 6)]}


def numbered_pads(name):
    path = FOOTPRINTS / (name + '.kicad_mod')
    tree = kicad.parse(path.read_text())
    return path, {pad[1].value: pad for pad in kicad.children(tree, 'pad') if pad[1].value}


def pad_dimension(pad, field):
    return tuple(float(atom.value) for atom in kicad.child(pad, field)[1:3])


def assert_critical_lands():
    _, mux = numbered_pads('Onsemi_846AP_MSOP10')
    for number, pad in mux.items():
        assert pad_dimension(pad, 'size') == (1.40, 0.30)
        assert abs(pad_dimension(pad, 'at')[0]) == 2.20
    _, dse = numbered_pads('TI_DSE0006A')
    for number, pad in dse.items():
        assert pad_dimension(pad, 'size') == (0.8 if number == '1' else 0.7, 0.25)
        assert abs(pad_dimension(pad, 'at')[0]) == 0.60
    _, flash = numbered_pads('Winbond_USON-8_2x3mm_P0.5mm_UX')
    assert pad_dimension(flash['9'], 'at') == (0, 0)
    assert pad_dimension(flash['9'], 'size') == (0.20, 1.60)
    _, rp = numbered_pads('QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm')
    assert pad_dimension(rp['57'], 'size') == (3.20, 3.20)
    assert pad_dimension(rp['1'], 'size') == (0.875, 0.20)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stock-models', type=Path, help='optional KiCad 10 3dmodels folder for byte parity')
    parser.add_argument('--install', action='store_true', help='populate or refresh local STEP files')
    args = parser.parse_args()
    if args.install and args.stock_models is None:
        parser.error('--install requires --stock-models')
    devices = json.loads(CONTRACT.read_text())['devices']
    host = json.loads(DOCK_SPACE.read_text())['windows']['host_bottom']
    nearest = host['nearest_rigid']
    assert nearest['limiting_shape'] == 'LowerShell' and not host['rigid_intersections_mm3']
    clearance = round(host['size_xyz_mm'][2] + nearest['distance_mm'], 6)
    assert set(devices) == set(PACKAGE_LIMITS)
    assert_critical_lands()
    MODELS.mkdir(exist_ok=True)
    rows, models = {}, {}

    def bind_model(name, source):
        original = args.stock_models / source if source and args.stock_models else None
        destination = MODELS / (name + '.step')
        if args.install and original:
            shutil.copyfile(original, destination)
        if source is None:
            if args.install and not destination.exists():
                make_rsv_step(destination)
        elif original:
            assert digest(original) == digest(destination), (name, original)
        models[name] = {'model_uri': '${KIPRJMOD}/WiredMain.3dshapes/' + destination.name,
                        'stock_model': source,
                        'classification': 'manufacturer drawing reconstruction' if source is None else 'KiCad package-family geometry',
                        **measure(destination)}
        return models[name]

    for ref, device in devices.items():
        library, name = device['footprint'].split(':')
        package, limit, drawing = PACKAGE_LIMITS[ref]
        footprint, pads = numbered_pads(name)
        assert set(pads) == set(device['pins']), (ref, name)
        default_source = library + '.3dshapes/' + name + '.step'
        source = None if ref == 'U162' else ALTERNATE_MODELS.get(name, default_source)
        model = models[name] if name in models else bind_model(name, source)
        model_height = model['size_xyz_mm'][2]
        package_allowance = limit[2] + 0.05
        model_allowance = max(limit[2], model_height) + 0.05
        rows[ref] = {'mpn': device['mpn'], 'package': package, 'manufacturer_drawing': drawing,
                     'outline_limit_xyz_mm': limit,
                     'height_authority': 'TI DRT-3 package table; product data sheet reports 1 mm by 1 mm footprint' if ref == 'U152' else 'manufacturer package drawing',
                     'footprint': 'WiredMain:' + name, 'footprint_sha256': digest(footprint),
                     'package_limit_plus_solder_mm': round(package_allowance, 3),
                     'floor_clearance_at_package_limit_mm': round(clearance - package_allowance, 3),
                     'package_or_step_plus_solder_mm': round(model_allowance, 3),
                     'floor_clearance_including_step_mm': round(clearance - model_allowance, 3)}
    for name, library in PASSIVE_LIBRARIES.items():
        bind_model(name, library + '.3dshapes/' + name + '.step')
    report = {'scope': 'Native footprint pad parity and STEP readback; no placed-board, routing, tolerance or solder qualification',
              'solder_height_screen_mm': 0.05,
              'host_window_mm': host['size_xyz_mm'],
              'host_window_center_dock_xyz_mm': [*host['center_xy_mm'], host['bounds_xyz_mm'][-1]],
              'host_window_nominal_floor_distance_mm': clearance,
              'source_sha256': {p.name: digest(p) for p in (CONTRACT, DOCK_SPACE, Path(__file__))},
              'selected_devices': rows, 'models': models,
              'passive_models': 'Package-family STEP for layout; exact passive MPN selection is pending.'}
    (HERE / 'package-models.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'{len(rows)} selected devices have pad parity, {len(models)} local STEP models pass geometric readback.')


if __name__ == '__main__':
    main()
