"""Assemble the off-axis body-pack and provisional tail routes in FreeCAD."""

from itertools import combinations
from math import hypot

import FreeCAD as App
import Part


V = App.Vector
PACK_MIN = (-10.5, 31.75, -4.15)
PACK_SIZE = (21.0, 33.0, 6.3)
GROWTH_MIN = (-10.75, 31.5, -4.7)
GROWTH_SIZE = (21.5, 33.5, 7.4)
TAIL_END_Y = -14.6


def _annotate(obj, note):
    obj.addProperty('App::PropertyString', 'DesignBasis', 'Design basis')
    obj.DesignBasis = note


def _style(obj, color, transparency=0, visible=True):
    if obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.Transparency = transparency
        obj.ViewObject.Visibility = visible


def _box(doc, group, name, label, start, size, note, color, transparency=0, visible=True):
    obj = doc.addObject('Part::Box', name)
    obj.Label = label
    obj.Length, obj.Width, obj.Height = size
    obj.Placement.Base = V(*start)
    group.addObject(obj)
    _annotate(obj, note)
    _style(obj, color, transparency, visible)
    return obj


def _cylinder(doc, group, name, label, start, radius, length, note, color, transparency=0, visible=True):
    obj = doc.addObject('Part::Cylinder', name)
    obj.Label = label
    obj.Radius = radius
    obj.Height = length
    obj.Placement = App.Placement(V(*start), App.Rotation(V(0, 0, 1), V(0, 1, 0)))
    group.addObject(obj)
    _annotate(obj, note)
    _style(obj, color, transparency, visible)
    return obj


def _wire(doc, group, name, label, nodes, od, color, note, visible=True):
    edges = []
    min_radius = float('inf')
    for start, end in zip(nodes, nodes[1:]):
        dx, dz = end[0] - start[0], end[2] - start[2]
        dy = end[1] - start[1]
        transverse = hypot(dx, dz)
        if transverse == 0:
            edges.append(Part.makeLine(V(*start), V(*end)))
            continue
        spline = Part.BezierCurve()
        spline.setPoles((V(*start), V(start[0], start[1] + dy / 3, start[2]),
                         V(end[0], end[1] - dy / 3, end[2]), V(*end)))
        edges.append(spline.toShape())
        min_radius = min(min_radius, dy * dy / (6 * transverse))
    path = Part.Wire(edges)
    section = Part.Wire([Part.makeCircle(od / 2, V(*nodes[0]), V(0, -1, 0))])
    obj = doc.addObject('Part::Feature', name)
    obj.Label = label
    obj.Shape = path.makePipeShell([section], True, False)
    obj.addProperty('App::PropertyLength', 'OutsideDiameter', 'Path').OutsideDiameter = od
    obj.addProperty('App::PropertyVectorList', 'PathStations', 'Path').PathStations = [V(*p) for p in nodes]
    if min_radius < float('inf'):
        obj.addProperty('App::PropertyLength', 'MinimumBendRadius', 'Path').MinimumBendRadius = min_radius
    group.addObject(obj)
    _annotate(obj, note)
    _style(obj, color, visible=visible)
    return obj


def add_body_pack_trial(doc, group=None, name='BodyPackTrial'):
    trial = doc.addObject('App::DocumentObjectGroup', name)
    trial.Label = 'Body pack | 1 mm off-axis feasibility trial'
    if group is not None:
        group.addObject(trial)
    _annotate(trial, 'Protected-pack mechanical envelope and nominal, unverified wire paths. '
              'The pack and growth envelope are centered at Z=-1 mm. Contacts, insulation, '
              'mount/retention and installation sequence require further work.')

    pack_color = (0.46, 0.27, 0.72)
    pack = _box(doc, trial, name + 'Pack', 'BC-PACK-EVT1-001 | requested maximum', PACK_MIN, PACK_SIZE,
                'Source hardware/pcb/evt1/pack-spec.json. Relocated maximum pack envelope, '
                '33 × 21 × 6.3 mm, with supplier acceptance pending.', pack_color)
    growth = _box(doc, trial, name + 'Growth', 'Pack growth allowance | toggle to inspect', GROWTH_MIN, GROWTH_SIZE,
                  'Current engineering growth allowance reoriented around the trial center. '
                  '33.5 × 21.5 × 7.4 mm. Actual swelling distribution and restraint are open.',
                  (0.71, 0.56, 0.88), 78, False)
    motor = _cylinder(doc, trial, name + 'Motor', 'NFP-E1015 can | published maximum', (0, 67, 0), 5.55, 26.3,
                      'Existing EVT1 body assembly geometry. Motor rear face Y67, metal stop Y93.3.',
                      (0.85, 0.51, 0.21))
    old = _cylinder(doc, trial, name + 'PreviousMotorLeadEnvelope', 'Previous full-diameter motor lead allowance',
                    (0, 61, 0), 5.55, 6.0, 'Preserved as a hidden comparison. The proposal requires the '
                    'actual lead exit and insulation to fit in a side corridor.', (0.91, 0.57, 0.26), 75, False)
    centered_wires = []
    for i, x in enumerate((-0.4, 0.4), start=1):
        centered_wires.append(_cylinder(doc, trial, f'{name}CenteredLead{i}',
                                         f'Illustrated centered motor lead {i} | comparison',
                                         (x, 60, 0), 0.30, 4.0,
                                         'Centered wire continuation witness inferred from the supplier sketch. '
                                         'Diameter and near-axis segment are illustrative, not OEM dimensions.',
                                         (0.86, 0.44, 0.17), 45, False))

    sensors, growth_sensors = [], []
    for i, x in enumerate((-3.8, 3.8), start=1):
        label = f'Pack NTC {i} | Ø3 × 10 mm head budget'
        basis = 'Vishay NTCLE413E2103F524A head/transition envelope per pack spec. Tape contact, '
        sensors.append(_cylinder(doc, trial, f'{name}PackNTC{i}', label, (x, 39.0, 3.65), 1.5, 10,
                                 basis + 'bias and dry strain relief await bench qualification.', (0.21, 0.72, 0.67)))
        growth_sensors.append(_cylinder(doc, trial, f'{name}PackNTC{i}AtGrowth', label + ' at growth limit',
                                         (x, 39.0, 4.2), 1.5, 10, basis + 'witness shifted with the broad face.',
                                         (0.21, 0.72, 0.67), 68, False))

    routes = doc.addObject('App::DocumentObjectGroup', name + 'Tails')
    routes.Label = 'Ten provisional tails to rear neck opening'
    trial.addObject(routes)
    _annotate(routes, 'Nominal closed-pose sweeps only. Tails end in free space near the rear neck. '
              'No connector, fastening, thread-closing sweep or powered validation is included.')
    wires = []
    motor_note = '29 AWG Cooner CZ 1104 route budget OD≤0.6 mm. Assumed motor lead clocking starts '
    motor_note += 'at Z4.2 on the motor rear face. Actual OEM lead exit, trim and insulated splice are open.'
    for polarity, x, color in (('P', -0.52, (0.89, 0.40, 0.12)), ('N', 0.52, (0.77, 0.25, 0.09))):
        nodes = [(x, 67, 4.2), (x, 36, 4.2), (x, 20, 2.35), (x, TAIL_END_Y, 2.35)]
        wires.append(_wire(doc, routes, name + 'Motor' + polarity, 'Motor ' + polarity + ' | provisional',
                           nodes, 0.60, color, motor_note))

    tip_note = 'Assumed two 0.46 mm insulated tails from the existing offset tip thermistor bore. '
    tip_note += 'The final potting exit and factory leads must be checked.'
    for suffix, x, neck_x in (('S', 7.43, 2.85), ('R', 8.17, 3.75)):
        nodes = [(x, 89.1, 0), (x, 78, 0), (x, 66, 5.4), (x, 43, 5.4),
                 (neck_x, 24, 3.9), (neck_x, TAIL_END_Y, 3.9)]
        wires.append(_wire(doc, routes, name + 'Tip' + suffix, 'Tip NTC ' + suffix + ' | provisional', nodes,
                           0.46, (0.12, 0.56, 0.75), tip_note))

    sensor_note = 'Nominal 0.46 mm insulated pack sensor extension. Sensor positions follow the pack '
    sensor_note += 'face; check slack for movement, attachment and finish the separate returns at the flange.'
    growth_wires = {}
    for i, center_x, neck_z in ((1, -3.8, 1.40), (2, 3.8, 0.45)):
        for suffix, dx in (('S', -0.375), ('R', 0.375)):
            x = center_x + dx
            nodes = [(x, 39, 3.65), (x, 31.3, 3.65), (x, 20, neck_z), (x, TAIL_END_Y, neck_z)]
            wire = _wire(doc, routes, f'{name}NTC{i}{suffix}', f'Pack NTC {i} {suffix} | provisional',
                         nodes, 0.46, (0.22, 0.67, 0.49), sensor_note)
            wires.append(wire)
            growth_wires[wire.Name] = _wire(doc, routes, f'{name}NTC{i}{suffix}AtGrowth',
                                            f'Pack NTC {i} {suffix} | growth witness',
                                            [(x, 39, 4.2), *nodes[1:]], 0.46, (0.22, 0.67, 0.49),
                                            sensor_note, visible=False)

    pack_note = 'Factory-protected power lead OD≤0.63 mm. Short-end PCM positions are illustrative '
    pack_note += 'and require revised factory exit/strain relief and pigtail length.'
    for polarity, x, color in (('P', -0.54, (0.80, 0.17, 0.18)), ('N', 0.54, (0.28, 0.31, 0.35))):
        nodes = [(x, 31.75, -1), (x, TAIL_END_Y, -1)]
        wires.append(_wire(doc, routes, name + 'Pack' + polarity, 'Protected pack ' + polarity + ' | provisional',
                           nodes, 0.63, color, pack_note))
    doc.recompute()
    return {'group': trial, 'pack': pack, 'growth': growth, 'motor_can': motor, 'retired_motor_keepout': old,
            'wires': wires, 'sensor_heads': sensors, 'growth_sensor_heads': growth_sensors,
            'centered_wires': centered_wires, 'growth_wires': growth_wires}


def check_body_pack_trial(trial, metal_body_shape, motor_cap_shape):
    """Check assembled-pose solids and explicitly report separately modeled allowances."""
    part_shapes = (('Metal body', metal_body_shape), ('Motor cap', motor_cap_shape))
    checked_shapes = tuple((obj.Label, obj.Shape) for obj in (
        trial['pack'], trial['growth'], trial['motor_can'], *trial['sensor_heads'],
        *trial['growth_sensor_heads'], *trial['wires'], *trial['growth_wires'].values()))
    for label, shape in checked_shapes + part_shapes:
        assert shape.isValid() and len(shape.Solids) == 1, label

    def pair(label_a, a, label_b, b):
        return {'a': label_a, 'b': label_b, 'common_mm3': a.common(b).Volume,
                'distance_mm': a.distToShape(b)[0]}

    closed_geometry = [pair(a_label, a, b_label, b) for a_label, a in checked_shapes for b_label, b in part_shapes]
    pack = (trial['pack'].Label, trial['pack'].Shape)
    growth = (trial['growth'].Label, trial['growth'].Shape)
    motor = (trial['motor_can'].Label, trial['motor_can'].Shape)
    old = (trial['retired_motor_keepout'].Label, trial['retired_motor_keepout'].Shape)
    hard_pairs = [pair(*pack, *motor), pair(*growth, *motor)]
    wire_shapes = tuple((wire.Label, wire.Shape) for wire in trial['wires'])
    growth_wire_shapes = tuple((wire.Label, wire.Shape) for wire in (
        trial['growth_wires'].get(wire.Name, wire) for wire in trial['wires']))
    sensor_shapes = tuple((obj.Label, obj.Shape) for obj in trial['sensor_heads'])
    growth_sensor_shapes = tuple((obj.Label, obj.Shape) for obj in trial['growth_sensor_heads'])
    wire_pairs = [pair(*a, *b) for a, b in combinations(wire_shapes, 2)]
    wire_pairs.extend(pair(*wire, *item) for wire in wire_shapes for item in (pack, motor, *sensor_shapes))
    growth_wire_pairs = [pair(*a, *b) for a, b in combinations(growth_wire_shapes, 2)]
    growth_wire_pairs.extend(pair(*wire, *item) for wire in growth_wire_shapes for item in growth_sensor_shapes)
    growth_route_pairs = [pair(*wire, *growth) for wire in growth_wire_shapes]
    return {'closed_metal_pairs': closed_geometry, 'pack_motor_pairs': hard_pairs, 'wire_pairs': wire_pairs,
            'lead_replacement_comparison': pair(*growth, *old), 'growth_wire_intersections': growth_route_pairs,
            'growth_wire_pairs': growth_wire_pairs,
            'centered_lead_witness_intersections': [pair(*growth, wire.Label, wire.Shape)
                                                     for wire in trial['centered_wires']],
            'scope': 'Closed-pose nominal checks. Motor and sensor lead exits are assumed. The thermistor tails '
                     'can follow pack growth; the power leads originate within the pack growth allowance. '
                     'Bend radius is from the nominal centered cable path; no torsion or installation sweep.'}
