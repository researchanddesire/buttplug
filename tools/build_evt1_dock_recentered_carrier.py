"""Separate native recentered contact carrier; never edits source CAD/PCB files.

build(doc, prefix='Recentered') returns the installed App::Part. Its Carrier
and Retainer links identify editable Bodies; selected component sources stay
in a separate hidden App::Part. add_pin_board() links the unchanged PinPCB.
All coordinates below are in the dock's physical closed frame, in mm.
"""
from pathlib import Path
import argparse, ast, hashlib, itertools, json, math, sys
import FreeCAD as App
import Part, Sketcher

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'hardware/cad/evt1-assembly/recentered-carrier-trial'
SOURCE = ROOT / 'tools/build_evt1_native_dock.py'
PREFLIGHT = Path('/private/tmp/compass-jobs/RootFeaturePreflight.FCStd')
PIN_PCB = ROOT / 'hardware/cad/evt1-assembly/pcb/PinPCB.FCStd'
MAIN_PCB = ROOT / 'hardware/cad/evt1-assembly/pcb/MainPCB.FCStd'
SHELL = Path('/private/tmp/compass-jobs/full-shell-prefix/ShellFeaturePreflight.FCStd')
CONTACT_X = (-16., -10., -4., 2.)
MAGNET_XZ = ((-14.5, 24.), (3., 21.5))
FOOT_X = (-43., -15.)
RETAINER_X = (-41.5, -13.5)
PIN_POSE = ((-6., 18.7962, 40.3), -90.)
DEVICE_POSE = (0., 53.2, 32.)


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def bounds(shape):
    b = shape.optimalBoundingBox(False, False)
    return [getattr(b, k) for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax')]
def note(obj, name, value):
    obj.addProperty('App::PropertyString', name, 'Engineering'); setattr(obj, name, value)
def color(obj, rgb):
    if obj.ViewObject: obj.ViewObject.ShapeColor = rgb
def box(x0,y0,z0,x1,y1,z1):
    return Part.makeBox(x1-x0,y1-y0,z1-z0,App.Vector(x0,y0,z0))
def placed(shape, pose):
    s=shape.copy(); s.Placement=pose.multiply(s.Placement); return s
def root_part(doc):
    return next(o for o in doc.Objects if o.TypeId=='App::Part' and
                not any(p.TypeId=='App::Part' for p in o.InList))


def _profiles(doc):
    """Reuse only pure native sketch/feature functions, never run the master."""
    tree=ast.parse(SOURCE.read_text())
    ns=dict(D=doc, App=App, Part=Part, Sketcher=Sketcher, math=math, profile_checks=[])
    for name in ('rr','circle','xz_profile','pad','pocket'):
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),'exec'),ns)
    return ns


def _screw(doc, key, name):
    """Same selected external dimensions/native profile as frozen fasteners helper."""
    import build_evt1_dock_fasteners as f
    spec=f.SPECS[key]
    b=doc.addObject('PartDesign::Body',name)
    note(b,'ManufacturerPartNumber',spec['mpn']); note(b,'SourceURL',spec['url'])
    note(b,'ModelBasis','Selected external dimensional reconstruction; cosmetic threads, drive recess and edge breaks omitted. No strength/torque qualification.')
    sk=b.newObject('Sketcher::SketchObject',name+'Section')
    sk.Placement.Rotation=App.Rotation(App.Vector(1,0,0),90)
    r,rh,h=spec['diameter']/2,spec['head']/2,spec['height']
    if spec.get('style')=='socket': pts=[(0,h),(rh,h),(rh,0),(r,0),(r,-spec['length']),(0,-spec['length'])]
    else:
        rim=h-(rh-r); pts=[(0,0),(rh,0),(rh,-rim),(r,-h),(r,-spec['length']),(0,-spec['length'])]
    for a,c in zip(pts,pts[1:]+pts[:1]):
        i=sk.addGeometry(Part.LineSegment(App.Vector(*a,0),App.Vector(*c,0)),False)
        sk.addConstraint(Sketcher.Constraint('Block',i))
    doc.recompute(); assert sk.FullyConstrained
    rev=b.newObject('PartDesign::Revolution',name+'ExternalProfile')
    rev.Profile=sk; rev.ReferenceAxis=(sk,['V_Axis']); rev.Angle=360
    doc.recompute(); assert rev.Shape.isValid() and len(rev.Shape.Solids)==1
    sk.Visibility=False; color(b,(.65,.67,.69)); return b


def build(doc, prefix='Recentered'):
    """Build separate editable Bodies and actual selected hardware instances."""
    sys.path.insert(0,str(ROOT/'tools'))
    import build_evt1_dock_pogo as pogo
    import build_evt1_dock_button_mechanics as coils
    part=doc.addObject('App::Part',prefix+'ContactModule')
    sources=doc.addObject('App::Part',prefix+'SelectedSources')
    ns=_profiles(doc); rr,circle,xz,pad,pocket=[ns[n] for n in ('rr','circle','xz_profile','pad','pocket')]
    def body(suffix):
        b=doc.addObject('PartDesign::Body',prefix+suffix); part.addObject(b)
        color(b,(.90,.86,.76)); return b
    c=body('Carrier'); r=body('Retainer')
    pad(c,prefix+'CarrierBlank',rr(c,prefix+'CarrierBlankProfile',58,7.1,.4,17,(-17,19.55)),30)
    for i,x in enumerate(FOOT_X):
        pad(c,prefix+'CarrierLeg'+str(i),rr(c,prefix+'CarrierLegProfile'+str(i),6,6.7,.2,8.4,(x,19.35)),8.9)
        pad(c,prefix+'CarrierFoot'+str(i),rr(c,prefix+'CarrierFootProfile'+str(i),7,7,.5,5.5,(x,19)),3)
        pad(c,prefix+'CarrierFloorLightTrap'+str(i),rr(c,prefix+'CarrierFloorLightTrapProfile'+str(i),10,10,.5,13.3,(x,19)),1)
        pocket(c,prefix+'CollarSkinClearance'+str(i),xz(c,prefix+'CollarSkinClearanceProfile'+str(i),10.4,1.2,.1,(x,24.1,13.8)),.9)
        pad(c,prefix+'CollarFrontReturnSkirt'+str(i),rr(c,prefix+'CollarFrontReturnSkirtProfile'+str(i),7.2,.7,.1,11.8,(x,22.35)),1.7)
        pocket(c,prefix+'CarrierMountBore'+str(i),circle(c,prefix+'CarrierMountBoreProfile'+str(i),1.25,(x,19,13.5)),8.1)
    pocket(c,prefix+'PinBoardRecess',xz(c,prefix+'PinBoardRecessProfile',28.4,10.4,.15,(-6,15.9,40.3),False),2.8962)
    pocket(c,prefix+'CarrierWireWindow',xz(c,prefix+'CarrierWireWindowProfile',22,3.2,.2,(-6,15.9,43.8),False),2.2)
    pocket(c,prefix+'ContactLacingReturnChannel',xz(c,prefix+'ContactLacingReturnProfile',14,2.6,.3,(-28,15.9,34),False),1.5)
    for i,x in enumerate(CONTACT_X):
        pocket(c,prefix+'BarrelClearance'+str(i),circle(c,prefix+'BarrelClearanceProfile'+str(i),1.05,(x,18.7,42),App.Rotation(App.Vector(1,0,0),90)),3.9)
        pocket(c,prefix+'TipPassage'+str(i),circle(c,prefix+'TipPassageProfile'+str(i),.9,(x,22.5,42),App.Rotation(App.Vector(1,0,0),90)),.8)
        sk=circle(c,prefix+'MetalFaceStopProfile'+str(i),1.2,(x,23.1,42),App.Rotation(App.Vector(1,0,0),-90))
        sk.addGeometry(Part.Circle(App.Vector(),App.Vector(0,0,1),.9),False)
        sk.addConstraint(Sketcher.Constraint('Coincident',1,3,-1,1)); sk.addConstraint(Sketcher.Constraint('Radius',1,.9))
        doc.recompute(); assert sk.FullyConstrained
        pad(c,prefix+'MetalFaceStop'+str(i),sk,.1)
    for i,(x,z) in enumerate(MAGNET_XZ):
        pocket(c,prefix+'KeeperMagnetPocket'+str(i),circle(c,prefix+'KeeperMagnetPocketProfile'+str(i),4.15,(x,15.9,z),App.Rotation(App.Vector(1,0,0),90)),6.3)
    pad(r,prefix+'RetainerBack',rr(r,prefix+'RetainerBackProfile',58,2,.2,17,(-17,15)),29)
    pad(r,prefix+'ContactWireLightTrapHood',rr(r,prefix+'ContactWireHoodProfile',8,8,.2,13.3,(-28,12)),7.7)
    pocket(r,prefix+'ContactWireHoodInterior',rr(r,prefix+'ContactWireHoodInteriorProfile',6,6.4,.1,20.2,(-28,12)),6.9)
    pad(r,prefix+'ContactWireLightTrapBaffle',rr(r,prefix+'ContactWireBaffleProfile',6,.8,.1,13.3,(-28,11.1)),3.7)
    pocket(r,prefix+'ContactWireHoodEntry',xz(r,prefix+'ContactWireHoodEntryProfile',6,2,.3,(-28,7.9,17.5),False),1.1)
    for i,(x,z) in enumerate(MAGNET_XZ):
        pocket(r,prefix+'MagnetSpringSeat'+str(i),circle(r,prefix+'MagnetSpringSeatProfile'+str(i),2.6,(x,16,z),App.Rotation(App.Vector(1,0,0),-90)),.6)
        pad(r,prefix+'MagnetSpringPilot'+str(i),circle(r,prefix+'MagnetSpringPilotProfile'+str(i),1,(x,15.4,z),App.Rotation(App.Vector(1,0,0),-90)),.8)
    pad(r,prefix+'PinBoardPressurePad',xz(r,prefix+'PinBoardPressurePadProfile',28,10,.1,(-6,16,40.3)),1.7962)
    pocket(r,prefix+'RearWireWindow',xz(r,prefix+'RearWireWindowProfile',22,3.2,.2,(-6,18,43.8)),4.2)
    for i,x in enumerate(CONTACT_X):
        pocket(r,prefix+'SolderTailPassage'+str(i),circle(r,prefix+'SolderTailPassageProfile'+str(i),.9,(x,18,42),App.Rotation(App.Vector(1,0,0),-90)),4.2)
    for i,x in enumerate((-33,-23)):
        pocket(r,prefix+'ContactLoomLacingSlot'+str(i),xz(r,prefix+'ContactLoomLacingSlotProfile'+str(i),2,2.2,.2,(x,13.9,34),False),2.3)
    for i,x in enumerate(RETAINER_X):
        pocket(c,prefix+'RetainerScrewPilot'+str(i),circle(c,prefix+'RetainerScrewPilotProfile'+str(i),.8,(x,15.9,33),App.Rotation(App.Vector(1,0,0),90)),6.3)
        pocket(r,prefix+'RetainerScrewBore'+str(i),circle(r,prefix+'RetainerScrewBoreProfile'+str(i),1.1,(x,16.1,33),App.Rotation(App.Vector(1,0,0),-90)),2.2)
    for key,b in (('Carrier',c),('Retainer',r)):
        part.addProperty('App::PropertyLink',key,'Native bodies'); setattr(part,key,b)
    note(part,'SourceBuilderSHA256',sha(SOURCE))
    note(part,'Qualification','Nominal digital trial only. Received dimensions, print process/material, preload/creep, strength, seal and optical/electrical qualification OPEN.')
    note(part,'AssemblySequence','Install lower liner/closure plug first; prefeed lacing and solder wires, capture pins/PCB/magnets/coils and close rear retainer outside case, then lower feet vertically through unchanged floor apertures and mount with underside M3 screws. Rear driver access is not available after installation.')
    note(part,'WireInterface','Unchanged PinPCB translated+22X/−1.5Z. J94 rear wire lands nowZ43.8. Hood/lacing stayX−28; installed flexible wire route and restraint need design/physical trial.')
    note(part,'CollarException','Source-bound revised-skin test found5.2617mm3 overlap with oldcollarfronts. Parent-approved trimtoY23.2 plusintegral7.2x.7frontreturnskirtsY22.0..22.7/Z11.8..13.5 preserves7mmfeet,M3axes,PCB/floorports. Prior optical/ray blocking evidence doesnot transfer; no containment claim.')
    p=pogo.build(doc,.6,prefix+'PogoSource'); sources.addObject(p)
    params=p.Parameters; p.removeProperty('Parameters'); p.addProperty('App::PropertyLinkGlobal','Parameters','Assembly'); p.Parameters=params
    pogo.validate(p)
    magnet=doc.addObject('PartDesign::Body',prefix+'MagnetSource'); sources.addObject(magnet)
    pad(magnet,prefix+'MagnetCylinder',circle(magnet,prefix+'MagnetProfile',4,(0,0,0)),3)
    note(magnet,'ManufacturerPartNumber','supermagnete S-08-03-N')
    note(magnet,'SourceURL','https://www.supermagnete.de/eng/data_sheet_S-08-03-N.pdf')
    note(magnet,'ModelBasis','Published nominalØ8×3, ±0.1mm; N45 axial/Ni-Cu-Ni. No holding/compass qualification.')
    coil_path=OUT/'selected-coil-source.brp'
    assert sha(coil_path)=='c06a4e36ab094548564cd8980438655a02634330439ce5a1ad72bf04272ffcb9'
    coil=doc.addObject('PartDesign::Body',prefix+'MagnetSpringSource');sources.addObject(coil)
    coil_shape=Part.Shape();coil_shape.importBrep(str(coil_path))
    coil_feature=coil.newObject('PartDesign::Feature',prefix+'FrozenCatalogHelix');coil_feature.Shape=coil_shape
    note(coil,'ManufacturerPartNumber','LC014B02S')
    note(coil,'SourceURL',coils.SPRING['source'])
    note(coil,'ModelBasis','Exact frozen BRep of earlier selected OD4.57/wire0.36/length3.8 reconstructed5.5-turn helix. Inherited C0 BOP finding retained; not OEM end geometry, force or received proof.')
    note(coil,'BRepSourceSHA256',sha(coil_path));color(coil,(.64,.66,.69))
    m3=_screw(doc,'M3x12',prefix+'M3Source'); sources.addObject(m3)
    m2=_screw(doc,'M2x6Socket',prefix+'M2Source'); sources.addObject(m2)
    def link(name,source,point,rotation):
        o=doc.addObject('App::Link',prefix+name); o.setLink(source); part.addObject(o)
        o.LinkPlacement=App.Placement(App.Vector(*point),rotation); return o
    for i,x in enumerate(CONTACT_X):
        link('Pogo'+str(i),p,(x,18.7962,42),App.Rotation(App.Vector(0,0,1),App.Vector(0,1,0)))
    for i,(x,z) in enumerate(MAGNET_XZ):
        link('Magnet'+str(i),magnet,(x,19.2,z),App.Rotation(App.Vector(1,0,0),-90))
        link('MagnetSpring'+str(i),coil,(x,15.4,z),App.Rotation(App.Vector(1,0,0),-90))
    for i,x in enumerate(FOOT_X): link('FootScrew'+str(i),m3,(x,19,.25),App.Rotation(App.Vector(1,0,0),180))
    for i,x in enumerate(RETAINER_X): link('RetainerScrew'+str(i),m2,(x,14,33),App.Rotation(App.Vector(1,0,0),90))
    for b in (c,r):
        for feature in b.Group: feature.Visibility=False
        b.Tip.Visibility=True
    sources.Visibility=False
    part.addProperty('App::PropertyLinkGlobal','SelectedSources','Assembly'); part.SelectedSources=sources
    doc.recompute(); return part


def add_pin_board(doc, part, path=PIN_PCB, name='RecenteredPinBoard'):
    """Link original PCB artwork/model with the explicitly changed rigid pose."""
    if not doc.FileName: raise ValueError('Save owner before adding external PCB link')
    source=App.openDocument(str(Path(path).resolve())); source_root=root_part(source)
    o=doc.addObject('App::Link',name); o.setLink(source_root); part.addObject(o)
    o.LinkPlacement=App.Placement(App.Vector(*PIN_POSE[0]),App.Rotation(App.Vector(1,0,0),PIN_POSE[1]))
    source_root.Visibility=False; doc.recompute(); return o


def apply_lower_liner_relief(liner_body, prefix='RecenteredCarrierLiner'):
    """Append the approved local loading relief to an identity-placed liner.

    Native RR10.6×10.6,R.8 at(−43,19), cut fromZ37.1 down to13.0.
    This leaves the full2mm source floor below13.0 intact. The parent owns applying
    this API to its future master; the trial applies it only to a context copy.
    """
    if liner_body.Placement.Base.Length>1e-8 or abs(liner_body.Placement.Rotation.Angle)>1e-8:
        raise ValueError('Lower liner must use the physical identity dock frame')
    ns=_profiles(liner_body.Document)
    sk=ns['rr'](liner_body,prefix+'Profile',10.6,10.6,.8,37.1,(-43,19))
    feature=ns['pocket'](liner_body,prefix+'Relief',sk,24.1)
    note(feature,'Scope','Approved local inner-wall loading relief; no floor cut belowZ13.0. Earlier13.1-bottom proposal left a0.2mm collar/ledge gap; corrected to the actual floor top for0.3mm nominal gap. Verify actual outer-profile wall and full loading in parent assembly.')
    return feature


def physical_shapes(part):
    return [(o.Name,o.Shape) for o in part.Group if hasattr(o,'Shape') and not o.Shape.isNull()]


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--device'); parser.add_argument('--context')
    parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if args.check_only:
        doc=App.openDocument(str(OUT/'RecenteredCarrierTrial.FCStd')); part=doc.RecenteredContactModule
    else:
        doc=App.newDocument('RecenteredCarrierTrial'); doc.Label='Recentered carrier / isolated nominal EVT trial'
        part=build(doc); doc.recompute(); doc.saveAs(str(OUT/'RecenteredCarrierTrial.FCStd'))
        add_pin_board(doc,part); doc.recompute(); doc.save()
    sys.path.insert(0,str(OUT))
    from check_trial import validate
    report=validate(doc,part,device_path=args.device,context_path=args.context)
    report['builder_SHA256']=sha(Path(__file__))
    report['native_SHA256']=sha(OUT/'RecenteredCarrierTrial.FCStd')
    (OUT/'native-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('pass','body_checks','static_pair_count','hard_intersections','context_intersections')},indent=2),flush=True)


if __name__=='__main__': main()
