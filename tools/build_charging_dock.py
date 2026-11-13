"""Four-contact flange + printable clamshell dock integration study.

Run with FreeCAD Python: build_charging_dock.py [manufacturing-folder] [output]
The source product and first inert mold are read-only. No PCB/BOM is changed.
"""
from pathlib import Path
import hashlib
import json
import math
import sys
import zipfile
import xml.etree.ElementTree as ET

sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
import MeshPart

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / 'hardware/cad/manufacturing-layout'
OUT = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else SOURCE / 'charging-dock'
OUT.mkdir(parents=True, exist_ok=True)
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
source_report = json.loads((SOURCE / 'review.json').read_text())
trial_report = json.loads((SOURCE / 'overmold-trial/review.json').read_text())
assert sha(SOURCE / 'ManufacturingLayout.FCStd') == source_report['native_sha256']
assert sha(SOURCE / 'overmold-trial/OvermoldTrial.FCStd') == trial_report['native_sha256']
S = A.openDocument(str(SOURCE / 'ManufacturingLayout.FCStd'))
T = A.openDocument(str(SOURCE / 'overmold-trial/OvermoldTrial.FCStd'))
D = A.newDocument('ChargingDock')
D.Label = 'Four-contact flange / clamshell dock / unpowered prototype study'
pcb_data={}
for domain in ('dock','pins'):
    path=ROOT/'hardware/pcb/evt1'/domain/'mcad.json'
    data=json.loads(path.read_text())
    assert sha(ROOT/data['board_file'])==data['board_sha256'],domain+' PCB MCAD is stale'
    assert abs(data['thickness_mm']-1)<1e-8,domain+' PCB thickness'
    pcb_data[domain]=data
D.Label = 'Four-contact clamshell / EVT1 cradle PCB integration'
groups = {n: D.addObject('App::DocumentObjectGroup', n) for n in
          ('Construction', 'DeviceInterface', 'DockParts', 'ContactTooling', 'References', 'ComponentReferences')}
exports = {}
print_names = []
OFFSET = A.Vector(0, 40, 32)
CONTACT_X = [-38, -32, -26, -20]
CONTACT_Z = 11.5
NETS = ['GND', 'USB_DM', 'USB_DP', 'DOCK_5V']
KEEPERS = [(-38.5, -8), (-21, -10.5)]
FACE_Y = -26.8
seal_spec_path=SOURCE/'charging-dock/contact-seal-spec.json'
seal_spec=json.loads(seal_spec_path.read_text())
gland_spec=seal_spec['gland']
PIN_FREE = .197 * 25.4
PIN_STROKE = .055 * 25.4
PIN_BODY = .106 * 25.4
PIN_PCB_Y = FACE_Y + OFFSET.y - (PIN_FREE - .6)


def feature(name, shape, group='Construction'):
    obj = D.addObject('PartDesign::Feature', name)
    obj.Shape = shape
    groups[group].addObject(obj)
    return obj


def box(name, x, y, z, lx, ly, lz):
    obj = D.addObject('Part::Box', name)
    obj.Length, obj.Width, obj.Height = lx, ly, lz
    obj.Placement.Base = A.Vector(x, y, z)
    groups['Construction'].addObject(obj)
    return obj


def cylinder(name, radius, xyz, length, axis=(0, 1, 0)):
    obj = D.addObject('Part::Cylinder', name)
    obj.Radius, obj.Height = radius, length
    obj.Placement = A.Placement(A.Vector(*xyz), A.Rotation(A.Vector(0, 0, 1), A.Vector(*axis)))
    groups['Construction'].addObject(obj)
    return obj


def boolean(kind, name, base, tool):
    obj = D.addObject('Part::' + kind, name)
    obj.Base, obj.Tool, obj.Refine = base, tool, True
    groups['Construction'].addObject(obj)
    D.recompute()
    return obj


def union(name, objects):
    obj = D.addObject('Part::MultiFuse', name)
    obj.Shapes, obj.Refine = objects, True
    groups['Construction'].addObject(obj)
    D.recompute()
    return obj


def finish(obj, group, printable=False):
    groups['Construction'].removeObject(obj)
    groups[group].addObject(obj)
    D.recompute()
    assert obj.Shape.isValid() and len(obj.Shape.Solids) == 1, (obj.Name, obj.Shape.isValid(), len(obj.Shape.Solids))
    if printable:
        print_names.append(obj.Name)
    exports[obj.Name] = {}
    return obj


def rr_xy(hx, hy, radius, z, cy=77.5):
    q = math.sqrt(.5)
    vec = lambda x, y: A.Vector(x, cy+y, z)
    steps = [((-hx+radius, -hy), (hx-radius, -hy), None),
             ((hx-radius, -hy), (hx, -hy+radius), (hx-radius+radius*q, -hy+radius-radius*q)),
             ((hx, -hy+radius), (hx, hy-radius), None),
             ((hx, hy-radius), (hx-radius, hy), (hx-radius+radius*q, hy-radius+radius*q)),
             ((hx-radius, hy), (-hx+radius, hy), None),
             ((-hx+radius, hy), (-hx, hy-radius), (-hx+radius-radius*q, hy-radius+radius*q)),
             ((-hx, hy-radius), (-hx, -hy+radius), None),
             ((-hx, -hy+radius), (-hx+radius, -hy), (-hx+radius-radius*q, -hy+radius-radius*q))]
    edges = [Part.makeLine(vec(*a), vec(*b)) if m is None else Part.Arc(vec(*a), vec(*m), vec(*b)).toShape()
             for a, b, m in steps]
    return Part.Wire(edges)


def hex_nut(name, x, y, z, af, thickness, bore):
    radius = af / math.sqrt(3)
    # Flats along Z, keeping contact fasteners clear of the PCB edge.
    pts = [A.Vector(x+radius*math.cos(math.radians(i*60)), y, z+radius*math.sin(math.radians(i*60))) for i in range(6)]
    blank = feature(name + 'Blank', Part.Face(Part.makePolygon(pts+pts[:1])).extrude(A.Vector(0, thickness, 0)))
    return boolean('Cut', name, blank, cylinder(name + 'Pilot', bore/2, (x, y-.05, z), thickness+.1))


def moved(shape):
    result = shape.copy()
    result.translate(OFFSET)
    return result


# Revised rear HALF, still closed and fully overmolded with the first half.
# Rebuild from the original plate/hold-down shapes instead of leaving old
# two-target holes or obsolete permanent-magnet pockets in the new design.
cover_parts = [feature('RearPlateSource', S.getObject('CoverPlateBlank').Shape.copy())]
for i in (0, 1):
    cover_parts.append(feature('PCBHoldDownSource' + str(i), S.getObject('PCBHoldDown' + str(i)).Shape.copy()))
for i, (x, z) in enumerate(KEEPERS):
    cover_parts.append(cylinder('KeeperBoss' + str(i), 4.6, (x, -25.5, z), 2.6))
cover = union('RearHalfWithKeeperBosses', cover_parts)
for i, z in enumerate((-13, 13)):
    cover = boolean('Cut', 'RearScrewBore' + str(i), cover, cylinder('RearScrewTool' + str(i), 1.1, (12, -24.6, z), 1.8))
for i, x in enumerate((-21.35, -15.35)):
    cover = boolean('Cut', 'RearButtonOpening' + str(i), cover, cylinder('ButtonOpeningTool' + str(i), 2.5, (x, -24.6, 3.5125), 1.8))
for i, (x, z) in enumerate(KEEPERS):
    cover = boolean('Cut', 'OpenKeeperPocket' + str(i), cover, cylinder('KeeperPocketTool' + str(i), 4.1, (x, -25.1, z), 2.3))
for i, x in enumerate(CONTACT_X):
    cover = boolean('Cut', 'TargetStemBore' + str(i), cover, cylinder('TargetStemTool' + str(i), gland_spec['bore_diameter_mm']/2, (x, -24.6, CONTACT_Z), 1.8))
cover.Label = 'Four-contact rear plastic half / proposal'
cover = finish(cover, 'DeviceInterface', True)
# Give the final object a stable semantic name, not its last cutter's name.
cover.Label = 'FourContactRearHalf'

targets, nuts, keepers, seals, glands = [], [], [], [], []
for i, (x, net) in enumerate(zip(CONTACT_X, NETS)):
    # Turned spool head: rigid plastic bearing, silicone-key groove and a
    # slightly proud, rounded flat contact. Thread is a root/pilot envelope.
    pts = [(0, FACE_Y), (2, FACE_Y), (2, -26.4), (1.65, -26.4),
           (1.65, -25.7), (2, -25.7), (2, -24.5), (.754625, -24.5),
           (.754625, -21.3), (.5, -21.3), (.5, -20.3), (0, -20.3)]
    wire = Part.makePolygon([A.Vector(x+r, y, CONTACT_Z) for r, y in pts+pts[:1]])
    head = Part.Face(wire).revolve(A.Vector(x, 0, CONTACT_Z), A.Vector(0, 1, 0), 360)
    edges = [e for e in head.Edges if abs(e.BoundBox.YMin-FACE_Y) < 1e-6 and e.BoundBox.YLength < 1e-6
             and abs(e.BoundBox.XLength-4) < 1e-6]
    assert len(edges) == 1
    head = head.makeFillet(.15, edges)
    recess=Part.makeCylinder(gland_spec['OD_mm']/2,gland_spec['depth_mm'],A.Vector(x,-24.5-gland_spec['depth_mm'],CONTACT_Z),A.Vector(0,1,0)).cut(
        Part.makeCylinder(gland_spec['ID_mm']/2,gland_spec['depth_mm']+.02,A.Vector(x,-24.51-gland_spec['depth_mm'],CONTACT_Z),A.Vector(0,1,0)))
    glands.append(feature('TargetSealGlandTool_'+net,recess))
    head=head.cut(recess)
    target = finish(feature('Target_' + net, head), 'DeviceInterface')
    target.addProperty('App::PropertyString', 'ThreadCallout')
    target.ThreadCallout = 'M2x0.4 nominal; root envelope ONLY, actual fit/material/torque and retention qualification pending'
    targets.append(target)
    nut = finish(hex_nut('TargetNut_' + net, x, -22.9, CONTACT_Z, 4, 1.6, 1.6), 'ComponentReferences')
    nuts.append(nut)
    # Elliptical section preserves the free nominal ring volume while fitting
    # the installed axial space. It predicts neither strain nor contact force.
    ring=seal_spec['CAD_seal'];rr=ring['major_ring_radius_mm'];a=ring['radial_half_width_mm'];b=ring['axial_half_height_mm'];cy=-24.5-b
    edge=Part.Ellipse(A.Vector(x+rr+a,cy,CONTACT_Z),A.Vector(x+rr,cy+b,CONTACT_Z),A.Vector(x+rr,cy,CONTACT_Z)).toShape()
    ring_shape=Part.Face(Part.Wire([edge])).revolve(A.Vector(x,0,CONTACT_Z),A.Vector(0,1,0),360)
    seals.append(finish(feature('TargetSeal_'+net,ring_shape),'ComponentReferences'))
for i, (x, z) in enumerate(KEEPERS):
    keepers.append(finish(cylinder('BuriedSteelKeeper' + str(i), 4, (x, -25.1, z), 1), 'ComponentReferences'))
    feature('KeeperRearPottingSpace' + str(i), Part.makeCylinder(4.1, 1.2, A.Vector(x, -24.1, z), A.Vector(0, 1, 0)), 'References')

skin = feature('InertTrialSkinSource', T.getObject('TrialContinuousSkin').Shape.copy())
skin_cuts = union('ContactAndKeeperSkinCuts', targets + glands + [D.getObject('KeeperBoss0'), D.getObject('KeeperBoss1')])
skin = finish(boolean('Cut', 'FourContactSkin', skin, skin_cuts), 'DeviceInterface')
feature('OriginalTrayReference', S.getObject(source_report['native_object_names']['FlangeTray']).Shape.copy(), 'References')
feature('LegacyFlangeElectronics', S.getObject('FlangeElectronicsMechanicalProposal').Shape.copy(), 'References')
feature('UnselectedBatteryReference', S.getObject('UnselectedPackReference').Shape.copy(), 'References')
body_actual = feature('BodyReference', S.getObject(source_report['native_object_names']['MetalBody']).Shape.copy(), 'References')
cap_actual = feature('CapReference', S.getObject(source_report['native_object_names']['MotorThermistorCap']).Shape.copy(), 'References')

# Removal mask extends to Z=0: otherwise a proud post would catch the lower
# wall of a closed rectangular window when the main B tool slides +Z.
mask_body = box('MaskStem', -41, -37, 0, 24, 10.5, 16.2)
mask_flange = box('MaskPullFlange', -47, -40, -1, 36, 3, 18.2)
mask = union('MaskBlank', [mask_body, mask_flange])
for i, x in enumerate(CONTACT_X):
    mask = boolean('Cut', 'FaceShutoffRecess' + str(i), mask,
                   cylinder('FaceRecessTool' + str(i), 2.05, (x, FACE_Y, CONTACT_Z), .31))
for i, x in enumerate((-44, -14)):
    mask = boolean('Cut', 'MaskScrewPassage' + str(i), mask, cylinder('MaskScrewTool' + str(i), 1.65, (x, -40.1, 13.2), 3.2))
mask = finish(mask, 'ContactTooling', True)
mask.Label = 'ContactFaceMask'
tool_a = finish(feature('ContactMoldHalfA', T.getObject('MoldHalfA').Shape.copy()), 'ContactTooling', True)
tool_b = feature('MoldBSource', T.getObject('MoldHalfB').Shape.copy())
tool_b = boolean('Cut', 'ContactMaskOpenSlot', tool_b, box('MaskSlotTool', -41.05, -37.1, -.1, 24.1, 10.61, 16.35))
for i, x in enumerate((-44, -14)):
    tool_b = boolean('Cut', 'MaskScrewPilot' + str(i), tool_b,
                     cylinder('MaskPilotTool' + str(i), 1.25, (x, -37.1, 13.2), 7.1))
tool_b = finish(tool_b, 'ContactTooling', True)
tool_b.Label = 'ContactMoldHalfB'

# Whole-device inert outside gauge, in the dock's seated coordinates.
body_outer = S.getObject('TurnedBodyBlank').Shape.fuse(S.getObject('ShortTurnedNoseBlank').Shape).removeSplitter()
closed_flange = T.getObject('ClosedFlangeEnvelope').Shape.copy()
outer = body_outer.fuse(closed_flange).fuse(skin.Shape)
for target in targets:
    outer = outer.fuse(target.Shape)
outer = outer.removeSplitter()
gauge = finish(feature('DockDeviceGauge', moved(outer)), 'References', True)
feature('SeatedMetalBody', moved(body_actual.Shape), 'References')
feature('SeatedMetalCap', moved(cap_actual.Shape), 'References')
feature('SeatedSiliconeSkin', moved(skin.Shape), 'References')
for target in targets:
    feature('Seated' + target.Name, moved(target.Shape), 'References')

# Pocket-toy clamshell, flat opaque outer lid for the first print. A display and
# three buttons are space/style proposals, not holes through the UV chamber.
base_blank = feature('RoundedBaseBlank', Part.Face(rr_xy(57.5, 77.5, 20, 0)).extrude(A.Vector(0, 0, 34)))
base_core = feature('BaseInteriorTool', Part.Face(rr_xy(55, 75, 17.5, 2.5)).extrude(A.Vector(0, 0, 32)))
base = boolean('Cut', 'BaseShell', base_blank, base_core)
lid_blank = feature('RoundedLidBlank', Part.Face(rr_xy(57.5, 77.5, 20, 34.3)).extrude(A.Vector(0, 0, 30.7)))
lid_core = feature('LidInteriorTool', Part.Face(rr_xy(55.5, 75.5, 18, 34.2)).extrude(A.Vector(0, 0, 28.3)))
lid = boolean('Cut', 'LidShell', lid_blank, lid_core)
base_eyes = [cylinder('BaseHingeEye' + str(i), 4, (x, 155, 34.15), 11, (1, 0, 0)) for i, x in enumerate((-25, 14))]
base_links = [box('BaseHingeLink' + str(i), x, 151, 29, 11, 4, 5.15) for i, x in enumerate((-25, 14))]
base = union('BaseWithHinge', [base] + base_eyes + base_links)
lid = union('LidWithHinge', [lid, cylinder('LidHingeEye', 4, (-12, 155, 34.15), 24, (1, 0, 0)),
                            box('LidHingeLink', -12, 151, 34.15, 24, 4, 5.05)])
hinge_bore = cylinder('HingePinBore', 1.65, (-26, 155, 34.15), 52, (1, 0, 0))
base = boolean('Cut', 'BaseHingeBored', base, hinge_bore)
lid = boolean('Cut', 'LidHingeBored', lid, hinge_bore)
base = boolean('Cut', 'CentralEyeRelief', base,
               cylinder('CentralEyeReliefTool',4.2,(-12.3,155,34.15),24.6,(1,0,0)))
for i,x in enumerate((-25.3,13.7)):
    lid = boolean('Cut','OuterEyeRelief'+str(i),lid,
                  cylinder('OuterEyeReliefTool'+str(i),4.2,(x,155,34.15),11.6,(1,0,0)))
base = union('BaseWithPrototypeLatch', [base, box('LatchReceiver', -8, -7, 25, 16, 9.5, 9)])
lid = union('LidWithPrototypeLatch', [lid, box('LatchTab', -8, -7, 34.3, 16, 9.5, 3)])
base = boolean('Cut', 'LatchPilot', base, cylinder('LatchPilotTool', 1.25, (0, -3.5, 26.5), 7.7, (0, 0, 1)))
lid = boolean('Cut', 'LatchPassage', lid, cylinder('LatchPassageTool', 1.65, (0, -3.5, 34.2), 3.2, (0, 0, 1)))
# PCB nose and GCT USB4105 housing pass through this window. Socket face is
# flush at X=-57.5; the old recessed keepout would prevent normal plug mating.
base = boolean('Cut', 'USBCWindow', base, box('USBCWindowTool', -58, 47.5, 5.1, 5, 11, 5.9))
nest_mounts = [(-49, 27), (49, 27), (-49, 118), (49, 118)]
bosses = [cylinder('NestMountBoss' + str(i), 3.5, (x, y, 2.4), 3.1, (0, 0, 1)) for i, (x, y) in enumerate(nest_mounts)]
base = union('BaseWithNestBosses', [base] + bosses)
for i, (x, y) in enumerate(nest_mounts):
    base = boolean('Cut', 'NestMountPilot' + str(i), base, cylinder('NestPilotTool' + str(i), 1.25, (x, y, .5), 5.1, (0, 0, 1)))

# Contact head's two feet bolt down to rigid base bosses independently of nest.
head_mounts = [(-43, 9), (-13, 9)]
base = union('BaseWithContactMounts', [base] + [cylinder('HeadMountBoss' + str(i), 3, (x, y, 2.4), 3.1, (0, 0, 1)) for i, (x, y) in enumerate(head_mounts)])
for i, (x, y) in enumerate(head_mounts):
    base = boolean('Cut', 'HeadMountPilot' + str(i), base, cylinder('HeadPilotTool' + str(i), 1.25, (x, y, .5), 5.1, (0, 0, 1)))
usb_mounts=[(-54+h['xy_mm'][0],42+h['xy_mm'][1]) for h in pcb_data['dock']['holes'] if h['ref'].startswith('H')]
assert len(usb_mounts)==4
base=union('BaseWithUSBBoardMounts',[base]+[cylinder('USBBoardBoss'+str(i),2.4,(x,y,2.4),3,(0,0,1)) for i,(x,y) in enumerate(usb_mounts)])
for i,(x,y) in enumerate(usb_mounts):
    base=boolean('Cut','USBMountPilot'+str(i),base,cylinder('USBMountPilotTool'+str(i),.8,(x,y,1.4),4.1,(0,0,1)))
base = finish(base, 'DockParts', True)
base.Label = 'DockBase'
lid = finish(lid, 'DockParts', True)
lid.Label = 'DockLid'
feature('OptionalDisplayKeepout', Part.makeBox(56, 28, 5, A.Vector(-28, 76, 57)), 'References')
# Mechanical source comes from the actual routed PCB, including its narrow
# front nose and the receptacle/mounting drills. Fab body envelopes are
# conservative height budgets, not claimed OEM STEP models.
points=[A.Vector(-54+x,42+y,5.4) for x,y in pcb_data['dock']['outline_xy_mm']]
usb_shape=Part.Face(Part.makePolygon(points+points[:1])).extrude(A.Vector(0,0,1))
for h in pcb_data['dock']['holes']:
    dx,dy=h['drill_xy_mm'];u,v=h['xy_mm']
    if abs(dx-dy)<1e-7:
        cut=Part.makeCylinder(dx/2,1.2,A.Vector(-54+u,42+v,5.3))
    else:
        a,b=min(dx,dy),max(dx,dy)
        cut=Part.makeBox(a,b-a,1.2,A.Vector(-a/2,-(b-a)/2,0)).fuse(Part.makeCylinder(a/2,1.2,A.Vector(0,-(b-a)/2,0))).fuse(Part.makeCylinder(a/2,1.2,A.Vector(0,(b-a)/2,0)))
        if dx>dy:cut.rotate(A.Vector(),A.Vector(0,0,1),90)
        cut.rotate(A.Vector(),A.Vector(0,0,1),-h['angle_deg'])
        cut.translate(A.Vector(-54+u,42+v,5.3))
    usb_shape=usb_shape.cut(cut)
usb_board=finish(feature('DockUSBPCB',usb_shape.removeSplitter()),'ComponentReferences')
usb_components=[]
for c in pcb_data['dock']['components']:
    if c['ref'].startswith('H'):continue
    a,b,u,v=c['fab_bounds_xy_mm']
    obj=feature('USBComponent_'+c['ref'],Part.makeBox(u-a,v-b,c['height_budget_mm'],A.Vector(-54+a,42+b,6.4)),'ComponentReferences')
    obj.Label=c['ref']+' / PCB fab body and height budget'
    usb_components.append(obj.Name)

# Sparse removable nest. A conservative diameter38.8 cavity clears the
# maximum diameter37.34 metal throughout the 3mm slide, independent of taper.
# Fit soft liners to the measured local gap; they are not selected components.
body_clearance = cylinder('BodyNestLoadClearance', 19.4, (0, 60, 32), 90)
rails = [box('NestRail' + str(i), x, 20, 5.5, 4, 108, 2) for i, x in enumerate((-51, 47))]
cross = [box('NestCrossbar' + str(i), -51, y, 5.5, 102, 6, 2) for i, y in enumerate((24, 81, 108, 115))]
saddles = [box('BodySaddleBlank' + str(i), -23, y, 7.4, 46, 6, 24.6) for i, y in enumerate((81, 108))]
flange_supports = [box('FlangeRest' + str(i), x, 20, 7.4, 8, 12, 5.6) for i, x in enumerate((-34, 26))]
guides = [box('FlangeSideGuide' + str(i), x, 12.7, 12.9, 2.3, 8, 38.5) for i, x in enumerate((-47.5, 45.2))]
# Links join the front alignment guides to the support frame outside the flange.
links = [box('FrontGuideLink' + str(i), x, 20, 7.4, 13.5, 4, 5.5) for i, x in enumerate((-47.5, 34))]
feet = [cylinder('NestScrewFoot' + str(i), 4.2, (x, y, 5.5), 3, (0, 0, 1)) for i, (x, y) in enumerate(nest_mounts)]
nest = union('NestBlank', rails + cross + saddles + flange_supports + guides + links + feet)
nest = boolean('Cut', 'NestMetalClearance', nest, body_clearance)
nest = boolean('Cut','NestUSBBayClearance',nest,box('NestUSBBayTool',-54.5,41.5,2.5,29,23,9))
for i, (x, y) in enumerate(nest_mounts):
    nest = boolean('Cut', 'NestScrewPassage' + str(i), nest, cylinder('NestScrewTool' + str(i), 1.65, (x, y, 5.4), 3.2, (0, 0, 1)))
nest = finish(nest, 'DockParts', True)
nest.Label = 'DockNest'

# Pin head. Loads are target face -> annular hard stops -> carrier -> base,
# and plunger -> PCB -> retainer -> carrier. Silicone is not the axial datum.
head = box('ContactHeadBlank', -46, 6, 17, 36, 6.7, 36)
foot_blocks = [box('ContactHeadFoot' + str(i), x-3.5, y-3.5, 5.5, 7, 7, 3) for i, (x, y) in enumerate(head_mounts)]
legs = [box('ContactHeadLeg' + str(i), x-2, 6, 8.4, 4, 6.7, 9) for i, (x, y) in enumerate(head_mounts)]
head = union('ContactHeadWithFeet', [head] + foot_blocks + legs)
pcb_recess = box('PinPCBRecess', -42.2, 5.9, 39.9, 28.4, PIN_PCB_Y-5.9, 10.6)
head = boolean('Cut', 'HeadPCBRecess', head, pcb_recess)
# PCB rear wires leave downward through a real opening, not a sealed cavity.
head = boolean('Cut', 'HeadWireExit', head, box('HeadWireExitTool', -39, 5.9, 34, 22, 1.9, 9.3))
head = boolean('Cut','HeadDownwardWireChannel',head,box('HeadDownwardWireTool',-32,5.9,16.9,5,1.9,17.4))
for i, x in enumerate(CONTACT_X):
    z = CONTACT_Z + OFFSET.z
    head = boolean('Cut', 'PogoBarrelClearance' + str(i), head, cylinder('PogoBarrelTool' + str(i), 1.05, (x, PIN_PCB_Y-.05, z), PIN_BODY+.2))
    head = boolean('Cut', 'PogoTipGuide' + str(i), head, cylinder('PogoTipTool' + str(i), .9, (x, PIN_PCB_Y+PIN_BODY, z), 3))
    ring = Part.makeCylinder(1.5, .5, A.Vector(x, 12.7, z), A.Vector(0, 1, 0)).cut(Part.makeCylinder(.9, .6, A.Vector(x, 12.65, z), A.Vector(0, 1, 0)))
    head = union('HardStopLand' + str(i), [head, feature('HardStopRing' + str(i), ring)])
for i, (x, z0) in enumerate(KEEPERS):
    z = z0 + OFFSET.z
    head = boolean('Cut', 'DockMagnetRearPocket' + str(i), head, cylinder('DockMagnetPocketTool' + str(i), 4.15, (x, 5.9, z), 6.3))
for i, (x, y) in enumerate(head_mounts):
    head = boolean('Cut', 'HeadBaseScrewPassage' + str(i), head, cylinder('HeadBaseScrewTool' + str(i), 1.65, (x, y, 5.4), 3.2, (0, 0, 1)))
for i, x in enumerate((-41.5, -13.5)):
    head = boolean('Cut', 'RetainerPilot' + str(i), head, cylinder('RetainerPilotTool' + str(i), .8, (x, 6, 37), 6.4))
head = finish(head, 'DockParts', True)
head.Label = 'PogoCarrier'

# Retainer closes both magnet rear pockets and clamps the blank PCB at its
# outer edges. A raised PCB pressure pad has solder-tail clearances.
retainer_outline = Part.makePolygon([A.Vector(x,y,17) for x,y in
                                   [(-44,4),(-10,4),(-10,6),(-46,6),(-44,4)]])
retainer = feature('RetainerPlate', Part.Face(retainer_outline).extrude(A.Vector(0,0,32)))
pressure = box('PCBPressurePad', -42, 6, 40.2, 28, PIN_PCB_Y-1-6, 10)
retainer = union('RetainerWithPCBPad', [retainer, pressure])
for i, x in enumerate(CONTACT_X):
    retainer = boolean('Cut', 'SolderTailRelief' + str(i), retainer, cylinder('SolderTailTool' + str(i), .9, (x, 3.9, CONTACT_Z+OFFSET.z), PIN_PCB_Y-3.8))
retainer = boolean('Cut', 'RetainerWireExit', retainer, box('RetainerWireTool', -39, 3.9, 34, 22, 4.1, 9.3))
retainer = boolean('Cut','RetainerDownwardWireChannel',retainer,box('RetainerDownwardWireTool',-32,3.9,16.9,5,2.2,17.4))
for i, x in enumerate((-41.5, -13.5)):
    retainer = boolean('Cut', 'RetainerPassage' + str(i), retainer, cylinder('RetainerScrewTool' + str(i), 1.1, (x, 3.9, 37), 2.2))
    retainer = boolean('Cut', 'RetainerCountersink' + str(i), retainer,
                       feature('RetainerHeadTool' + str(i), Part.makeCone(2,1.1,1,A.Vector(x,4,37),A.Vector(0,1,0))))
retainer = finish(retainer, 'DockParts', True)
retainer.Label = 'PogoRetainer'

pcb_shape = Part.makeBox(28, 1, 10, A.Vector(-42, PIN_PCB_Y-1, 40.2))
for x in CONTACT_X:
    pcb_shape = pcb_shape.cut(Part.makeCylinder(.3, 1.2, A.Vector(x, PIN_PCB_Y-1.1, CONTACT_Z+OFFSET.z), A.Vector(0, 1, 0)))
pcb = finish(feature('PinPCBBlank', pcb_shape), 'ComponentReferences', True)
pin_wire_allowances=[]
wire_pads=[p for p in pcb_data['pins']['pads'] if p['ref']=='J94']
assert len(wire_pads)==4 and all(p['back'] and not p['front'] for p in wire_pads)
for p in wire_pads:
    u,v=p['xy_mm']
    assert abs(v-8.5)<1e-7
    obj=feature('PinWireExitAllowance'+p['number'],Part.makeCylinder(.55,PIN_PCB_Y-1-4.2,A.Vector(-42+u,4.2,50.2-v),A.Vector(0,1,0)),'References')
    pin_wire_allowances.append(obj.Name)
for i, (x, z0) in enumerate(KEEPERS):
    z = z0 + OFFSET.z
    finish(cylinder('DockMagnet' + str(i), 4, (x, 9.2, z), 3), 'ComponentReferences')
    finish(feature('MagnetBackSpacer' + str(i), Part.makeCylinder(3.95, 3.2, A.Vector(x, 6, z), A.Vector(0, 1, 0))), 'DockParts', True)
for i, (x, net) in enumerate(zip(CONTACT_X, NETS)):
    z = CONTACT_Z+OFFSET.z
    # Conservative main envelopes, NOT OEM CAD; maximum collar/body diameter
    # used over the whole rigid C length. Pin is shown at 0.6 mm compression.
    barrel = Part.makeCylinder(.072*25.4/2, PIN_BODY, A.Vector(x, PIN_PCB_Y, z), A.Vector(0, 1, 0))
    tail = Part.makeCylinder(.017*25.4/2, .069*25.4, A.Vector(x, PIN_PCB_Y-.069*25.4, z), A.Vector(0, 1, 0))
    finish(feature('PogoBarrel_' + net, barrel.fuse(tail)), 'ComponentReferences')
    tip = Part.makeCylinder(.042*25.4/2, PIN_FREE-.6-PIN_BODY, A.Vector(x, PIN_PCB_Y+PIN_BODY, z), A.Vector(0, 1, 0))
    finish(feature('PogoPlunger_' + net, tip), 'ComponentReferences')

intent = D.addObject('App::FeaturePython', 'DesignIntent')
for key, value in {
    'Scope': 'Printed mechanical fit/prototype study only; no electrical/material/UV release',
    'Product': 'Four main custom rigid parts preserved; revised rear half, four fixed spool targets and buried steel keepers',
    'Interface': f'Along +Z flange edge: X-38 GND, -32 D-, -26 D+, -20 5V;6mm pitch; all Z{CONTACT_Z}, faceY-26.8',
    'Target': 'Custom4mm spool head,0.3mm proud,0.15edge radius; M2x0.4 root envelope +4AFx1.6nut; materials/torque OPEN',
    'ContactSeal': 'Trial2x0.5NBR70 ring in metal face gland ID2.1/OD3.6/depth0.38 against flat plastic; compatibility/finish/squeeze/leaks unqualified',
    'Magnetics': 'Permanent8x3 magnets in DOCK only; buried8x1 steel keepers in device; magnetic/compass tests required',
    'PinCandidate': 'Mill-Max0906-2-15-20-75-14-11-0; 5.0038free,1.397travel; simplified conservative envelopes, not OEM CAD',
    'Stroke': '0.6mm nominal set by insulating annular stops on METAL contact faces, not by silicone',
    'Loading': 'Lid open: lower atY+3mm, then slide-3mm along guides. Reverse slide before lifting; do not scrape free pins',
    'Tool': 'Unscrew and pull ContactFaceMask along-Y first, then A-Z/B+Z; open-sided mask slot avoids trapped proud heads',
    'Case': '115x155x65shell,hinge/latch add length; plain opaque lid, optional controls not implemented; M3 prototype screw latch',
    'Electronics': 'Routed EVT1 dock and pin PCBs; GCT USB4105 face flush, four M2 board bosses, pin loom on rear face with open pressure-pad window. USB/power/physical qualification pending',
    'UV': 'No UV hardware, windows, dose or efficacy; future UV requires independent lid cutoff and full validation',
}.items():
    intent.addProperty('App::PropertyString', key, 'DesignIntent')
    setattr(intent, key, value)
D.recompute()

# Canonical filenames follow final labels even when native boolean names differ.
roles = {}
for name in list(exports):
    obj = D.getObject(name)
    label = obj.Label if obj in (cover, mask, tool_b, base, lid, nest, head, retainer) else obj.Name
    roles[label] = obj.Name
    step = OUT / (label+'.step')
    obj.Shape.exportStep(str(step))
    step.write_text('\n'.join(line.rstrip() for line in step.read_text().splitlines())+'\n')
    mesh = MeshPart.meshFromShape(Shape=obj.Shape, LinearDeflection=.05, AngularDeflection=.2, Relative=False)
    assert mesh.isSolid(), label
    view = OUT/(label+'-view.stl')
    mesh.write(str(view))
    exports[name] = {'label': label, 'STEP_sha256': sha(step), 'view_STL_sha256': sha(view)}
    if name in print_names:
        shape = obj.Shape.copy()
        if obj in (tool_b, lid):
            shape.rotate(A.Vector(), A.Vector(1, 0, 0), 180)
        elif obj in (cover, mask, gauge):
            shape.rotate(A.Vector(), A.Vector(1, 0, 0), 90)
        elif obj in (head, retainer, pcb) or name.startswith('MagnetBackSpacer'):
            shape.rotate(A.Vector(), A.Vector(1, 0, 0), 90)
        bounds = shape.BoundBox
        shape.translate(A.Vector(-bounds.XMin, -bounds.YMin, -bounds.ZMin))
        printed = MeshPart.meshFromShape(Shape=shape, LinearDeflection=.04, AngularDeflection=.2, Relative=False)
        assert printed.isSolid()
        path = OUT/(label+'.stl')
        printed.write(str(path))
        exports[name]['print_STL_sha256'] = sha(path)

# Native planar section faces, intentionally OPEN view meshes, never print
# parts. Opposite walls of half-parts would obscure the real cavity void.
def section_mesh(obj, z, path):
    wires = obj.Shape.slice(A.Vector(0,0,1),z)
    assert wires and all(w.isClosed() for w in wires),obj.Label
    section = Part.makeFace(wires,'Part::FaceMakerBullseye')
    assert section.isValid() and section.Area>0,obj.Label
    faces=[]
    for face in section.Faces:
        face=face.copy()
        if face.normalAt(0,0).z<0: face.reverse()
        faces.append(face)
    MeshPart.meshFromShape(Shape=Part.makeCompound(faces),LinearDeflection=.02,AngularDeflection=.15,Relative=False).write(str(path))
    return {'section_view_STL_sha256':sha(path),'section_plane_Z_mm':z,'section_area_mm2':section.Area}

for obj in (cover, skin) + tuple(targets) + tuple(nuts) + tuple(seals):
    path = OUT/(obj.Label+'-section-view.stl')
    exports[obj.Name].update(section_mesh(obj,CONTACT_Z,path))

render_meshes = {}
for name in ['SeatedMetalBody','SeatedMetalCap','SeatedSiliconeSkin'] + ['SeatedTarget_'+net for net in NETS] + usb_components:
    path = OUT/(name+'-view.stl')
    MeshPart.meshFromShape(Shape=D.getObject(name).Shape,LinearDeflection=.06,AngularDeflection=.2,Relative=False).write(str(path))
    render_meshes[path.name] = sha(path)
for obj in [head,retainer,pcb] + [D.getObject('PogoBarrel_'+net) for net in NETS] + [D.getObject('PogoPlunger_'+net) for net in NETS]:
    path = OUT/(obj.Label+'-section-view.stl')
    exports[obj.Name].update(section_mesh(obj,CONTACT_Z+OFFSET.z,path))
open_lid = lid.Shape.copy()
open_lid.rotate(A.Vector(0,155,34.15),A.Vector(1,0,0),-110)
path = OUT/'DockLidOpen-view.stl'
MeshPart.meshFromShape(Shape=open_lid,LinearDeflection=.05,AngularDeflection=.2,Relative=False).write(str(path))
render_meshes[path.name] = sha(path)

native = OUT/'ChargingDock.FCStd'
D.saveAs(str(native))
with zipfile.ZipFile(native) as z:
    payload = [(i,z.read(i)) for i in z.infolist()]
    xml = ET.fromstring(z.read('Document.xml'))
names = [o.get('name') for o in xml.findall('Objects/Object')]
visible = {'DockParts', base.Name, nest.Name, head.Name, retainer.Name, 'DesignIntent'}
gui = ET.Element('Document',SchemaVersion='1',HasExpansion='1')
ET.SubElement(gui,'Expand',count='0')
providers = ET.SubElement(gui,'ViewProviderData',Count=str(len(names)))
for rank,name in enumerate(names):
    provider = ET.SubElement(providers,'ViewProvider',name=name,expanded='0',treeRank=str(rank))
    props = ET.SubElement(provider,'Properties',Count='1',TransientCount='0')
    prop = ET.SubElement(props,'Property',name='Visibility',type='App::PropertyBool',status='1')
    ET.SubElement(prop,'Bool',value='true' if name in visible else 'false')
pending = native.with_suffix('.view-tmp')
with zipfile.ZipFile(pending,'w',compression=zipfile.ZIP_DEFLATED) as z:
    for info,blob in payload:
        if info.filename!='GuiDocument.xml': z.writestr(info,blob)
    z.writestr('GuiDocument.xml',ET.tostring(gui,encoding='utf-8',xml_declaration=True))
with zipfile.ZipFile(pending) as z:
    assert all(z.read(i.filename)==b for i,b in payload if i.filename!='GuiDocument.xml')
pending.replace(native)

report = {
    'scope':'Four-contact flange, removable face mask and printable clamshell dock; mechanical prototype only',
    'native_sha256':sha(native), 'builder_sha256':sha(Path(__file__)),
    'source_native_sha256':source_report['native_sha256'], 'source_trial_native_sha256':trial_report['native_sha256'],
    'contact_seal_spec_sha256':sha(seal_spec_path),
    'contact_seal':seal_spec,
    'contact_seal_roles':[o.Name for o in seals],
    'native_roles':roles, 'exports':exports, 'render_meshes':render_meshes,
    'pcb_sources':{k:{'board_file':v['board_file'],'board_sha256':v['board_sha256']} for k,v in pcb_data.items()},
    'usb_board':{'native_role':usb_board.Name,'component_roles':usb_components,'mount_centers_XY_mm':usb_mounts,
                 'PCB_bottom_top_Z_mm':[5.4,6.4],'socket_face_X_mm':-57.5,'port_XYZ_size_mm':[-58,47.5,5.1,5,11,5.9]},
    'pin_wire_exit':{'allowance_roles':pin_wire_allowances,'wire_pad_face':'rear / B.Cu','pad_Z_mm':41.7,'allowance_OD_mm':1.1,'retainer_window_XYZ_size_mm':[-39,3.9,34,22,4.1,9.3]},
    'print_parts':[D.getObject(n).Label if D.getObject(n) in (cover,mask,tool_b,base,lid,nest,head,retainer) else n for n in print_names],
    'dock_device_translation_xyz_mm':list(OFFSET),
    'contacts':[{'net':net,'device_xyz_mm':[x,FACE_Y,CONTACT_Z],'dock_xyz_mm':[x,FACE_Y+40,CONTACT_Z+32]} for x,net in zip(CONTACT_X,NETS)],
    'contact_head':{'OD_mm':4,'proud_mm':.3,'edge_radius_mm':.15,'silicone_key_groove_OD_mm':3.3,'groove_Y_mm':[-26.4,-25.7],
                    'bearing_Y_mm':-24.5,'thread':'M2x0.4 root envelope only','nut_AF_thickness_mm':[4,1.6]},
    'keeper_centers_XZ_mm':KEEPERS,'keeper_size_mm':[8,1], 'dock_magnet_size_mm':[8,3],
    'nominal_magnet_to_keeper_gap_mm':2.7,
    'pogo':{'candidate':'0906-2-15-20-75-14-11-0','free_height_mm':PIN_FREE,'max_travel_mm':PIN_STROKE,
            'nominal_compression_mm':.6,'PCB_front_Y_mm':PIN_PCB_Y,'barrel_height_envelope_mm':PIN_BODY,
            'body_OD_envelope_mm':.072*25.4,'tip_OD_mm':.042*25.4,
            'length_tolerance_mm':.006*25.4,'diameter_tolerance_mm':.002*25.4,
            'stop_land_OD_ID_mm':[3,1.8]},
    'case_shell_size_xyz_mm':[115,155,65], 'hinge_axis_xyz_mm':[0,155,34.15], 'open_lid_angle_deg':-110,
    'device_loading_axial_slide_mm':3,
    'hardware_trial':{'M3x60_hinge_bolt':1,'M3_hinge_locknut':1,'M3x10_latch_screw':1,
                      'M3x8_nest_and_carrier_screw':6,'M2x6_countersunk_carrier_retainer_screw':2,
                      'M3x10_face_mask_screw':2,'M2_target_nut':4,'custom_target_post':4,'HANSA_FLEX_OR2_0_5_trial_seal':4,
                      '8x1_steel_keeper':2,'8x3_dock_magnet':2,'MillMax0906_spring_pin':4,'pin_PCB_EVT1':1,'USB_PCB_EVT1':1,'M2x4_USB_board_screw':4},
    'sources':{
        'pogo_manufacturer_authored_2025_pdf':'https://static6.arrow.com/aropdfconversion/adfa1bc04697174a4358693f99b5c90949307da3/0906-2-15-20-75-14-11-0.pdf',
        'magnet':'https://www.supermagnete.de/eng/data_sheet_S-08-03-N.pdf',
        'native_USB':'https://docs.espressif.com/projects/esp-idf/en/v5.5.3/esp32c3/api-guides/usb-serial-jtag-console.html'},
    'limits':[
        'Custom target contact material/plating, thread fit/locking, creep, pullout and finished-contact acceptance OPEN.',
        'Silicone-key groove is mechanical capture geometry, not proof of a liquid-tight metal/silicone bond; button/cavity sealing still OPEN.',
        'Inner metal face-seal gland and4NBR70 ring envelopes are a trial design only; printed counterfaces, ring tolerances/cure compatibility, preload and actual sealing unqualified.',
        'Zero nominal mask-face shutoff,0.05mm nominal mask sliding clearance; real finish,flash and contact masking need inert casting trials.',
        'Pin envelopes simplified from manufacturer dimensions; not OEM CAD, current-part receipt or guaranteed spring force.',
        'Two dock magnets plus buried steel keepers: installed retention/rocking,removal and compass interference unmeasured.',
        'Nominal hard-stop compression and flange guide clearances are unqualified manufacturing budgets, not ordinary-print fit guarantees.',
        'EVT1 cradle boards are routed; component bodies use fab outlines and conservative heights. Native USB, power, screw/thread fit, completed loom and received-part fit remain untested.',
        'Lower then slide to dock; reverse slide before lifting. No arbitrary drop-in/tilted approach or wrong-way use qualified.',
        'Opaque lid has no selected display,buttons,UV emitters or interlock. M3 screw latch is a prototype closure.',
        'No slicer,physical print,assembly,cast,powered charging,programming or human-use result. Source product/trial files unchanged.']}
(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n')
assert sha(SOURCE/'ManufacturingLayout.FCStd')==source_report['native_sha256']
assert sha(SOURCE/'overmold-trial/OvermoldTrial.FCStd')==trial_report['native_sha256']
print(json.dumps({'native':str(native),'exported_parts':len(exports),'print_parts':report['print_parts']}),flush=True)
