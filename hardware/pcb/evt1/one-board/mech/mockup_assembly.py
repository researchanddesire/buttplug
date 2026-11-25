"""Editable links to the two mockup bodies and three loose dowels.

Run with FreeCAD console, then use mockup_color_step.py for coloured STEP.
All source product parts stay unchanged.
"""
PIN_CENTERS_XY_MM = [(-15.0, -14.0), (15.0, -14.0), (0.0, 55.0)]
PIN_BASE_Z_MM = -4.0
import sys
sys.path.insert(0, '/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/mech')
from mockup_common import *

def build():
    sources = {name: App.openDocument(str(MECH / (name + '.FCStd')))
               for name in ['MockupHalfA', 'MockupHalfB', 'MockupAlignmentPin']}
    doc = App.newDocument('MockupAssembly')
    doc.Label = 'Compass full-size inert print mockup'
    doc.saveAs(str(MECH / 'MockupAssembly.FCStd'))
    links = []
    for name in ['MockupHalfA', 'MockupHalfB']:
        link = doc.addObject('App::Link', name)
        link.setLink(sources[name].getObject('MockupHalf'))
        links.append(link)
    pin_body = sources['MockupAlignmentPin'].getObject('AlignmentPin')
    for i, (x, y) in enumerate(PIN_CENTERS_XY_MM):
        link = doc.addObject('App::Link', 'Pin' + str(i + 1))
        link.setLink(pin_body)
        link.Placement = App.Placement(App.Vector(x, y, PIN_BASE_Z_MM), App.Rotation())
        links.append(link)
    doc.recompute()
    for link in links:
        assert link.Shape.isValid() and len(link.Shape.Solids) == 1
    assert links[0].Shape.common(links[1].Shape).Volume < 1e-4
    for pin in links[2:]:
        for half in links[:2]:
            assert pin.Shape.common(half.Shape).Volume < 1e-4
    doc.save()
    compound = Part.makeCompound([link.Shape for link in links])
    compound.exportStep(str(MECH / 'MockupAssembly.step'))
    saved = read_shape(MECH / 'MockupAssembly.step')
    assert len(saved.Solids) == 5
    report = {'sources_sha256': source_hashes(), 'assembled_bounds_mm': bounds(compound),
        'parts': {'MockupHalfA': 1, 'MockupHalfB': 1, 'MockupAlignmentPin': 3},
        'valid_saved_step': saved.isValid(), 'saved_step_solids': len(saved.Solids),
        'nominal_pin_diametral_clearance_mm': 0.3,
        'nominal_pin_total_axial_clearance_mm': 0.6,
        'product_sources_modified': False, 'physical_print_verified': False}
    (PACKET / 'validation.json').write_text(json.dumps(report, indent=2) + '\n')
    for backup in MECH.glob('*.FCBak'):
        shutil.move(str(backup), str(BUILD / backup.name))

run_logged('MockupAssembly', build)
