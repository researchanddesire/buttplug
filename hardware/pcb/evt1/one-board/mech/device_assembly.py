"""Compass EVT1 device assembly: turned metal body and nose cap, thin rear nut,
flange tray, rear cover, the two button plungers, silicone skin reference and the
placed one-board PCB.
Checks hard-part interference and the connector withdrawal space, exports one
coloured STEP and writes mech/device-fit.json.

Run:  QT_QPA_PLATFORM=offscreen /Applications/FreeCAD.app/Contents/MacOS/FreeCAD mech/device_assembly.py
Needs mech/FlangeTray.step, mech/RearCover.step, mech/ButtonPlunger.step, mech/FlangeSkin.step, mech/Internals.step, mech/compass-one-board.step.
"""
import sys, os, json, itertools
sys.path.insert(0, '/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/mech')
import FreeCAD as App, Part
from compass_datums import *

name = 'compass-device'
PARTS = [  # label, file, colour (None keeps the STEP's colours), placement matrix
    ('MetalBody', METAL + '/MetalBody.step', (0.76, 0.77, 0.79), None),
    ('MotorThermistorCap', METAL + '/MotorThermistorCap.step', (0.76, 0.77, 0.79), None),
    ('CapFaceSeal', MECH + '/CapFaceSeal.FCStd', (0.065, 0.070, 0.080), 'seal'),
    ('ThinRearNut', METAL + '/ThinRearNut.step', (0.55, 0.56, 0.58), None),
    ('FlangeTray', MECH + '/FlangeTray.step', (0.16, 0.16, 0.18), None),
    ('RearCover', MECH + '/RearCover.step', (0.16, 0.16, 0.18), None),
    ('FlangeSkin', MECH + '/FlangeSkin.step', (0.42, 0.30, 0.55), None),
    ('ButtonSW1', MECH + '/ButtonPlunger.step', (0.82, 0.82, 0.80), None),
    ('ButtonSW2', MECH + '/ButtonPlunger.step', (0.82, 0.82, 0.80), 'sw2'),   # same part, moved to SW2
    ('PCB', MECH + '/compass-one-board.step', None, 'pcb'),
    ('InternalCradle', MECH + '/InternalCradle.FCStd', (0.90, 0.45, 0.12), 'native'),
    ('CradleWireGuide', MECH + '/CradleWireGuide.FCStd', (0.95, 0.69, 0.22), 'native'),
    ('Internals', MECH + '/Internals.step', None, None),   # pack, NTCs, motor, tip sensor, wires (coloured in the STEP)
]
if os.path.exists(BUILD + '/' + name + '.log'):
    os.remove(BUILD + '/' + name + '.log')
exit_code = 0
try:
    App.ParamGet("User parameter:BaseApp/Preferences/Mod/Import").SetInt("ImportMode", 0)
    import ImportGui
    doc = App.newDocument('CompassDevice')
    roots = []
    shapes = {}
    native_links = []
    for label, path, color, place in PARTS:
        if place in ('seal', 'native'):
            # Keep this new part linked to its editable native sketch/revolution.
            seal_doc = App.openDocument(path)
            App.setActiveDocument(doc.Name)
            source = seal_doc.getObject(label)
            assert source.Shape.isValid() and len(source.Shape.Solids) == 1
            native_links.append((label, source))
            shapes[label] = source.Shape.copy()
            log(name, 'linked', label, path)
            continue
        before = set(o.Name for o in doc.Objects)
        ImportGui.insert(path, doc.Name)
        doc.recompute()
        new = [o for o in doc.Objects if o.Name not in before]
        part_roots = [o for o in new if not o.InList]
        if place == 'pcb':
            m = pcb_matrix()
        elif place == 'sw2':
            m = App.Matrix(); m.move(App.Vector(SWITCHES[1][0] - SWITCHES[0][0], 0, SWITCHES[1][1] - SWITCHES[0][1]))
        else:
            m = App.Matrix()
        for r in part_roots:
            r.Placement = App.Placement(m).multiply(r.Placement)
            r.Label = label if len(part_roots) == 1 else label + '_' + r.Name
        if color is not None:
            for o in new:
                if hasattr(o, 'Shape') and o.ViewObject is not None:
                    o.ViewObject.ShapeColor = color
        roots += part_roots
        sh = Part.Shape(); sh.read(path)
        if place in ('pcb', 'sw2'):
            sh = sh.transformShape(m, True) or sh
        shapes[label] = sh
        log(name, 'inserted', label, 'roots', len(part_roots), 'objects', len(new), 'solids', len(sh.Solids))
    doc.recompute()
    # External links require a saved owner document. Save the complete imported
    # assembly first, then save the linked-seal milestone before exporting.
    doc.saveAs(MECH + '/' + name + '.FCStd')
    for label, source in native_links:
        link = doc.addObject('App::Link', label)
        link.setLink(source)
        link.Label = label
        roots.append(link)
    doc.recompute()
    doc.save()

    # PCB board solid and parts after placement
    pcb = shapes['PCB']
    board = max(pcb.Solids, key=lambda s: s.BoundBox.XLength * s.BoundBox.ZLength)
    bb = board.BoundBox
    log(name, 'placed board bbox', [round(v, 2) for v in (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)])

    def common_volume(a, b):
        """Common volume with a bounding-box prefilter over b's solids."""
        total = 0.0
        ab = a.BoundBox
        for s in (b.Solids or [b]):
            if not ab.intersect(s.BoundBox):
                continue
            try:
                total += a.common(s).Volume
            except Exception as e:
                log(name, 'common failed', str(e))
        return total

    rigid = ['MetalBody', 'ThinRearNut', 'FlangeTray', 'RearCover', 'MotorThermistorCap', 'ButtonSW1', 'ButtonSW2', 'InternalCradle', 'CradleWireGuide']
    hits = []
    pairs = list(itertools.combinations(rigid, 2)) + [(r, 'PCB') for r in rigid]
    for a, b in pairs:
        v = common_volume(shapes[a], shapes[b])
        log(name, 'overlap', a, b, round(v, 4))
        if v > 1e-3:
            hits.append({'a': a, 'b': b, 'mm3': round(v, 3)})

    # Connector withdrawal: the mating plug slides +Z out of each B.Cu housing.
    withdraw = []
    for ref, ((x, z), w, d, h) in CONNECTORS.items():
        box = box_xyz(x - w / 2, x + w / 2, BOARD_B_Y, BOARD_B_Y + h, z + d / 2, z + d / 2 + CONNECTOR_WITHDRAW)
        v_tray = common_volume(shapes['FlangeTray'], box)
        v_nut = common_volume(shapes['ThinRearNut'], box)
        inside = box.BoundBox.ZMax <= FLANGE_Z / 2 - WALL
        withdraw.append({'ref': ref, 'z_top_mm': round(box.BoundBox.ZMax, 2), 'tray_overlap_mm3': round(v_tray, 3), 'nut_overlap_mm3': round(v_nut, 3), 'inside_cavity': inside})

    # Buttons pressed: each plunger moved in by its full travel must still clear the cover and touch
    # only its switch (the nose on the static actuator model; anything else is a collision).
    pressed = []
    for label in ('ButtonSW1', 'ButtonSW2'):
        inst = shapes[label].copy(); inst.translate(App.Vector(0, BUTTON_TRAVEL, 0))
        touched = []
        for sol in pcb.Solids:
            if inst.BoundBox.intersect(sol.BoundBox) and inst.common(sol).Volume > 1e-4:
                sb = sol.BoundBox; touched.append([round(v, 2) for v in (sb.XMin, sb.ZMin, sb.XMax, sb.ZMax)])
        pressed.append({'button': label, 'travel_mm': round(BUTTON_TRAVEL, 2), 'cover_overlap_mm3': round(common_volume(inst, shapes['RearCover']), 4),
                        'board_solids_touched_xz': touched, 'ok': len(touched) == 1})
        log(name, 'pressed', label, pressed[-1])

    # Clearances worth reading off
    clear = {
        'nut_face_to_tallest_B_part_mm': round(NUT_Y[0] - (BOARD_B_Y + B_PART_H), 2),
        'stub_tip_to_board_B_face_mm': round(STUB_TIP_Y - BOARD_B_Y, 2),
        'contact_tip_proud_of_cover_mm': round(COVER_OUT_Y - (BOARD_F_Y - CONTACT_H), 2),
        'contact_tip_below_skin_face_mm': round((BOARD_F_Y - CONTACT_H) - (COVER_OUT_Y - SKIN_T_FACE), 2),
        'antenna_end_to_nut_corner_mm': round(abs(ANTENNA_END_X) - 13.86, 2),
        'flange_depth_mm': round(SHOULDER_Y - COVER_OUT_Y, 2),
        'button_pretravel_mm': BUTTON_PRETRAVEL,
        'button_total_travel_mm': round(BUTTON_TRAVEL, 2),
        'button_head_proud_of_cover_mm': BUTTON_PROUD,
        'silicone_over_button_head_mm': round(BUTTON_HEAD_TOP_Y - (COVER_OUT_Y - SKIN_T_FACE), 2),
        'button_flange_to_switch_body_pressed_mm': round((BOARD_F_Y - SWITCH_BODY_H) - (COVER_IN_Y + BUTTON_TRAVEL), 2),
        'button_boss_underside_above_fcu_mm': round(BOARD_F_Y - (COVER_IN_Y + BUTTON_BOSS_H), 2),
        'button_radial_clearance_mm': round((BUTTON_BORE_D - BUTTON_HEAD_D) / 2, 2),
        'device_length_mm': round(shapes['MotorThermistorCap'].BoundBox.YMax - (COVER_OUT_Y - SKIN_T_FACE), 2),
    }
    internals_fit = json.load(open(MECH + '/internals-fit.json')) if os.path.exists(MECH + '/internals-fit.json') else None
    seal_fit = json.load(open(MECH + '/cap-seal-fit.json'))
    seal_fit['assembly_checks'] = []
    for other in ('MetalBody', 'MotorThermistorCap', 'Internals'):
        overlap = common_volume(shapes['CapFaceSeal'], shapes[other])
        gap = shapes['CapFaceSeal'].distToShape(shapes[other])[0]
        seal_fit['assembly_checks'].append({'other': other, 'overlap_mm3': round(overlap, 6), 'gap_mm': round(gap, 6)})
        assert overlap < 1e-3, 'nose seal intersects ' + other
        if other != 'Internals':
            assert gap < 1e-4, 'nose seal misses ' + other
    log(name, 'nose_seal', json.dumps(seal_fit))
    ImportGui.export(roots, MECH + '/' + name + '.step')
    # Same assembly with the skin and cover left off, to see the board seated in the tray.
    open_roots = [r for r in roots if r.Label not in ('FlangeSkin', 'RearCover')]
    ImportGui.export(open_roots, MECH + '/' + name + '-open.step')
    # Cutaway: the enclosure parts halved at Z = 0 (the +Z half removed), the board and internals whole.
    halfspace = box_xyz(-200, 200, -200, 200, 0, 200)
    cut_objs = []
    for label, path, color, place in PARTS:
        if label in ('PCB', 'Internals', 'InternalCradle', 'CradleWireGuide'):
            continue
        half = shapes[label].cut(halfspace)
        o = doc.addObject('Part::Feature', label + '_cut')
        o.Label = label + ' (cutaway)'; o.Shape = half
        doc.recompute()
        if o.ViewObject is not None:
            o.ViewObject.ShapeColor = color
        cut_objs.append(o)
    whole = [r for r in roots if r.Label in ('PCB', 'Internals', 'InternalCradle', 'CradleWireGuide')]
    ImportGui.export(cut_objs + whole, MECH + '/' + name + '-cutaway.step')
    for o in cut_objs:
        o.ViewObject.Visibility = False
    module_roots = [r for r in roots if r.Label in ('Internals','InternalCradle','CradleWireGuide')]
    ImportGui.export(module_roots, MECH + '/compass-internal-module.step')
    # Exploded inspection view: guide lifted +Z to expose battery loading and band slots.
    exploded=[]
    for label in ('InternalCradle','CradleWireGuide','Internals'):
        o=doc.addObject('Part::Feature',label+'_exploded');o.Shape=shapes[label].copy()
        if label=='CradleWireGuide':o.Placement.Base=App.Vector(0,0,20)
        o.ViewObject.ShapeColor=(0.90,0.45,0.12) if label=='InternalCradle' else (0.95,0.69,0.22) if label=='CradleWireGuide' else (0.62,0.66,0.72)
        exploded.append(o)
    doc.recompute();ImportGui.export(exploded, BUILD + '/cradle-exploded.step')
    for o in exploded:o.ViewObject.Visibility=False
    # Focused section of the existing joint: metal cut at Z=0, installed seal
    # shown whole so the ring is easy to inspect in the viewer.
    joint_objs = []
    joint_box = box_xyz(-40, 40, 61, 67, -40, 0)
    for label in ('MetalBody', 'MotorThermistorCap', 'CapFaceSeal'):
        section = shapes[label] if label == 'CapFaceSeal' else shapes[label].common(joint_box)
        assert section.isValid()
        o = doc.addObject('Part::Feature', label + '_joint_section')
        o.Label = label + ' (joint section)'; o.Shape = section
        o.ViewObject.ShapeColor = (0.065, 0.070, 0.080) if label == 'CapFaceSeal' else (0.76, 0.77, 0.79)
        joint_objs.append(o)
    doc.recompute()
    ImportGui.export(joint_objs, BUILD + '/cap-seal-joint-section.step')
    for o in joint_objs:
        o.ViewObject.Visibility = False
    doc.saveAs(MECH + '/' + name + '.FCStd')
    for f in os.listdir(MECH):
        if f.endswith('.FCBak'):
            os.replace(MECH + '/' + f, BUILD + '/' + f)
    report = {
        'pcb_step': 'compass-one-board.step', 'pcb_placement': 'X = kx - 100, Z = 100 - ky, F.Cu face at Y %.2f' % BOARD_F_Y,
        'flange_outline_mm': [FLANGE_X, FLANGE_Z], 'board_mm': [BOARD_X, BOARD_Z, BOARD_T],
        'hard_part_overlaps': hits, 'connector_withdrawal': withdraw, 'buttons_pressed': pressed, 'clearances': clear,
        'internals': internals_fit,
        'nose_seal': seal_fit,
        'cradle': json.load(open(MECH + '/cradle-fit.json')),
        'scope': 'Nominal rigid geometry only. Wire dressing, tolerances, nut torque access, screw engagement, skin tooling and the dock mate are not checked here.',
    }
    with open(MECH + '/device-fit.json', 'w') as f:
        f.write(json.dumps(report, indent=2) + '\n')
    log(name, json.dumps(report))
    log(name, 'OK')
except Exception:
    import traceback
    log(name, 'ERROR', traceback.format_exc())
    exit_code = 1
finally:
    os._exit(exit_code)
