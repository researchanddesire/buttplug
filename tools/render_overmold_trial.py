"""Render the saved mold trial's actual native meshes for phone-sized review."""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from PIL import Image, ImageDraw, PngImagePlugin
import render_mechanical_r2 as draw

ROOT = Path(__file__).resolve().parents[1]
FOLDER = Path(sys.argv[1]).resolve()
OUT = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else ROOT / 'developer-docs/docs/assets/overmold-trial.png'
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
report = json.loads((FOLDER / 'review.json').read_text())
assert sha(FOLDER / 'OvermoldTrial.FCStd') == report['native_sha256']
assert report['geometry_checks']['continuous_skin_valid_single_solid']
meshes = draw.NativeMeshes(FOLDER)
for name, values in report['exports'].items():
    meshes.expected[name + '-view.stl'] = values['view_STL_sha256']
    if 'section_view_STL_sha256' in values:
        meshes.expected[name + '-section-view.stl'] = values['section_view_STL_sha256']


def color(name):
    if name.startswith('TrialContinuousSkin'):
        return (194, 118, 142)
    if name.startswith('ClosedAssemblyDummy'):
        return (110, 158, 150)
    return (145, 167, 191)


draw.part_color = color


def geometry(name, section=False, rotate=False, delta=None):
    triangles = meshes.load(name + ('-section-view' if section else '-view'))
    if rotate:
        # B shown face-up beside A, a display pose only.
        triangles = triangles * np.array([-1, 1, -1])
    if delta:
        triangles = triangles + np.array(delta)
    return (name, triangles, None)


im = Image.new('RGB', (1640, 1540), 'white')
d = ImageDraw.Draw(im)
draw.label(d, (30, 20), 'CAD for the first casting trial', 34, True)
draw.label(d, (30, 70), 'Native CAD geometry. Closed flange + installed root, then ONE continuous skin.', 22, fill=draw.MUTED)
draw.panel(im, (20, 115, 1600, 530), 'TWO MOLD HALVES / CAVITY FACES',
           '116 x 50 x 28 mm each. B rotated for display; tools open along +/-Z.',
           [geometry('MoldHalfA'), geometry('MoldHalfB', rotate=True, delta=(130, 0, 0))],
           camera=(.10, .18, 3))
draw.panel(im, (20, 665, 790, 655), 'CLOSED INSERT + SKIN / SECTION',
           'Green: solid inert dummy. Pink: continuous silicone.',
           [geometry('ClosedAssemblyDummy', section=True), geometry('TrialContinuousSkin', section=True)],
           camera=(0, .05, 3))
draw.panel(im, (830, 665, 790, 655), 'CONTINUOUS SKIN / REAR FACE',
           '90 x 38 mm skin; raised back arrow proposes +X.',
           [geometry('TrialContinuousSkin')],
           camera=(.4, -2.8, 1.8))
d = ImageDraw.Draw(im)
draw.label(d, (32, 1350), 'Print: MoldHalfA.stl, MoldHalfB.stl and ClosedAssemblyDummy.stl.', 24, True)
draw.label(d, (32, 1395), 'Fill network: ~24.2 mL. End skin: 1 mm nominal. Confirm dry fit and material cure before casting.', 22)
draw.label(d, (32, 1440), 'No electronics, battery, working buttons or contact seals in this trial. No pressure or material release.', 22, fill=draw.AMBER)
draw.label(d, (32, 1485), 'Original product CAD unchanged. Geometry checks do not establish filling, bonding, sealing or physical fit.', 21, fill=draw.MUTED)
meshes.verify()
meta = {'native_sha256': report['native_sha256'], 'renderer_sha256': sha(Path(__file__)),
        'review_sha256': sha(FOLDER / 'review.json'), 'meshes_sha256': meshes.used,
        'scope': 'Actual native meshes/sections. B rotated180 aboutY and translated130mmX for display. No generated concept geometry.'}
info = PngImagePlugin.PngInfo()
info.add_text('Source', json.dumps(meta, sort_keys=True))
OUT.parent.mkdir(parents=True, exist_ok=True)
im.save(OUT, pnginfo=info)
OUT.with_suffix('.json').write_text(json.dumps(meta, indent=2) + '\n')
print(OUT)
