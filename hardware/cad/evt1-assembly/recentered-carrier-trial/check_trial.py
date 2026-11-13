"""Actual-BRep checks for the isolated native carrier; no source saves."""
from pathlib import Path
import hashlib, itertools, json, math, sys
import FreeCAD as App
import Part, MeshPart

ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools'))
import build_evt1_dock_recentered_carrier as m


def common(a,b):
    if not a.optimalBoundingBox(False,False).intersect(b.optimalBoundingBox(False,False)): return 0.
    if len(a.Solids)>1 or len(b.Solids)>1:
        return sum(common(sa,sb) for sa in a.Solids for sb in b.Solids)
    return a.common(b).Volume


def coil_envelope(name,lift=0,broad=False):
    i=int(name[-1]); x,z=m.MAGNET_XZ[i]; axis=App.Vector(0,1,0)
    origin=App.Vector(x,15.4,z+lift)
    outer,inner=(2.6,1.0)if broad else(2.285,1.925)
    return Part.makeCylinder(outer,3.8,origin,axis).cut(Part.makeCylinder(inner,3.8,origin,axis))


def pair_common(na,a,nb,b,lift=0):
    if not a.optimalBoundingBox(False,False).intersect(b.optimalBoundingBox(False,False)): return 0.
    if 'MagnetSpring' in na:
        return common(coil_envelope(na,lift,True),b)
    if 'MagnetSpring' in nb:
        return common(a,coil_envelope(nb,lift,True))
    return common(a,b)


def posed_box(bb,pose):
    result=App.BoundBox()
    for x in (bb.XMin,bb.XMax):
        for y in (bb.YMin,bb.YMax):
            for z in (bb.ZMin,bb.ZMax):result.add(pose.multVec(App.Vector(x,y,z)))
    return result


def liner_relief(doc,source,rows):
    original=next(s for n,s,side in rows if n in ('LowerChamber','LowerChamberInstance'))
    group=doc.addObject('App::Part','ReadOnlyContextCopy')
    b=doc.addObject('PartDesign::Body','RelievedLowerLinerContext');group.addObject(b)
    seed=b.newObject('PartDesign::Feature','ExactSavedSourceLowerLiner');seed.Shape=original.copy()
    m.note(seed,'SourcePath',source.FileName);m.note(seed,'SourceSHA256',m.sha(source.FileName))
    feature=m.apply_lower_liner_relief(b)
    outer=source.ChamberOuterProfile.Shape.Wires[0].copy();outer.translate(App.Vector(0,0,-11))
    inner=source.ChamberCavityProfile.Shape.Wires[0].copy();inner.translate(App.Vector(0,0,-37))
    profile=feature.Profile[0] if isinstance(feature.Profile,tuple) else feature.Profile
    relief=profile.Shape.Wires[0].copy();relief.translate(App.Vector(0,0,-37.1))
    actual_inner=Part.Face(inner).fuse(Part.Face(relief)).removeSplitter().Faces[0].OuterWire
    distance=outer.distToShape(actual_inner)
    assert distance[0]>=1,(distance[0],distance[1])
    before_floor=original.common(m.box(-65,-5,11,65,165,12.99999))
    after_floor=b.Shape.common(m.box(-65,-5,11,65,165,12.99999))
    delta=before_floor.cut(after_floor).Volume+after_floor.cut(before_floor).Volume
    assert delta<1e-6,delta
    b.Shape.check(True)
    collar=doc.RecenteredCarrier.Shape.common(m.box(-49,13,13.3,-37,25,14.3))
    clearance=collar.distToShape(b.Shape)
    collar_wire=doc.RecenteredCarrierFloorLightTrapProfile0.Shape.Wires[0].copy()
    collar_wire.translate(App.Vector(0,0,-13.3))
    lateral=collar_wire.distToShape(relief)[0]
    assert abs(clearance[0]-.3)<1e-6 and abs(lateral-.3)<1e-6,(clearance[0],lateral)
    rows=[(n,b.Shape.copy() if n in ('LowerChamber','LowerChamberInstance') else s,side)for n,s,side in rows]
    group.Visibility=False
    return rows,{'native_body':b.Name,'source_copy_only':True,'remaining_wall_from_actual_profile_wires_mm':distance[0],
                 'remaining_wall_nearest_points':[[list(a),list(c)]for a,c in distance[1]],
                 'actual_collar_clearance_mm':clearance[0],'unchanged_full_floor_below_13p0_symmetric_difference_mm3':delta,
                 'actual_profile_lateral_clearance_mm':lateral,
                 'prior_13p1_control':'liner-relief-13p1-ledged-probe.json preserves measured0.2mm ledge gap; parent-authorized13.0 floor-top correction restores0.3 without thinning floor',
                 'BOP_pass':True,'relief':{'WH_mm':[10.6,10.6],'radius_mm':.8,'centerXY_mm':[-43,19],'Z_mm':[13.0,37.1]}}


def measure_coils(doc,part):
    def native_tool(feature):
        shape=feature.AddSubShape.copy()
        shape.Placement=feature.Placement.multiply(shape.Placement)
        return shape
    def radial(feature,radius):
        fs=[f for f in native_tool(feature).Faces if hasattr(f.Surface,'Radius') and abs(f.Surface.Radius-radius)<1e-7]
        assert len(fs)==1,(feature.Name,len(fs)); return fs[0]
    result=[]
    for i in range(2):
        coil=doc.getObject('RecenteredMagnetSpring'+str(i)).Shape
        magnet=doc.getObject('RecenteredMagnet'+str(i)).Shape
        pilot=native_tool(doc.getObject('RecenteredMagnetSpringPilot'+str(i)))
        seat=radial(doc.getObject('RecenteredMagnetSpringSeat'+str(i)),2.6)
        cavity=radial(doc.getObject('RecenteredKeeperMagnetPocket'+str(i)),4.15)
        values={'carrier_body_gap_mm':coil.distToShape(part.Carrier.Shape)[0],
                'retainer_body_end_bearing_gap_mm':coil.distToShape(part.Retainer.Shape)[0],
                'magnet_front_end_bearing_gap_mm':coil.distToShape(magnet)[0],
                'pilot_radial_gap_mm':coil.distToShape(pilot)[0],
                'seat_cylindrical_wall_radial_gap_mm':coil.distToShape(seat)[0],
                'carrier_cavity_radial_gap_mm':coil.distToShape(cavity)[0]}
        assert abs(values['pilot_radial_gap_mm']-.925)<1e-4,values
        assert abs(values['seat_cylindrical_wall_radial_gap_mm']-.315)<1e-4,values
        assert abs(values['carrier_cavity_radial_gap_mm']-1.865)<1e-4,values
        assert values['carrier_body_gap_mm']>1,values
        assert values['retainer_body_end_bearing_gap_mm']<1e-6 and values['magnet_front_end_bearing_gap_mm']<1e-6,values
        env=coil_envelope('RecenteredMagnetSpring'+str(i))
        envelope_intersections={'carrier':common(env,part.Carrier.Shape),
                                'retainer':common(env,part.Retainer.Shape),'magnet':common(env,magnet)}
        assert max(envelope_intersections.values())<1e-6,envelope_intersections
        result.append({'instance':i,'actual_helix_distances':values,
                       'nominal_annular_envelope_intersection_mm3':envelope_intersections,
                       'bearing_vs_radial':'Zero retainer/magnet distances are axial end-face bearings, not radial interference',
                       'BOP_continuity_exception':'Inherited source helix GeomAbs_C0; retained explicitly, no all-component BOP-clean claim'})
    return result


def _context(path):
    d=App.openDocument(str(Path(path).resolve())); rows=[]
    excluded=('ContactCarrierInstance','ContactRetainerInstance','PinBoardAssembly',
              'PogoContact','DockTargetMagnet','CarrierScrew','ContactRetainerScrew','DeviceAssembly')
    if d.getObject('BaseModule'):
        assert abs(d.LidModule.Placement.Rotation.Angle)<1e-8,'Context must be saved closed'
        for group,side in ((d.BaseModule,'base'),(d.LidModule,'lid')):
            for o in group.Group:
                if o.Name.startswith(excluded) or not hasattr(o,'Shape') or o.Shape.isNull(): continue
                rows.append((o.Name,o.Shape.copy(),side))
    else:
        base_names=('LowerShell','LowerChamber','FrontClosureLowerPlug','CustomHingePin','HingeRetainingWasher')
        lid_names=('UpperShell','UpperChamber','ScallopedBezel')
        for name in base_names+lid_names:
            o=d.getObject(name)
            if o: rows.append((name,o.Shape.copy(),'base' if name in base_names else 'lid'))
    return d,rows


def validate(doc,part,device_path=None,context_path=None):
    assert Path(doc.FileName).resolve()==(m.OUT/'RecenteredCarrierTrial.FCStd').resolve()
    old_context=doc.getObject('ReadOnlyContextCopy')
    if old_context:
        for old_body in list(old_context.Group):
            for feature in reversed(list(old_body.Group)):doc.removeObject(feature.Name)
            doc.removeObject(old_body.Name)
        doc.removeObject(old_context.Name);doc.recompute()
    paths=[m.SOURCE,m.PREFLIGHT,m.PIN_PCB,m.MAIN_PCB,
           ROOT/'tools/build_evt1_dock_pogo.py',ROOT/'tools/build_evt1_dock_fasteners.py',
           ROOT/'tools/build_evt1_dock_button_mechanics.py',Path(__file__),
           Path(m.__file__),Path(__file__).with_name('device_check.py'),
           Path(__file__).with_name('selected-coil-bop-evidence.json'),
           Path(__file__).with_name('selected-coil-source.brp')]
    complete=Path('/private/tmp/compass-jobs/candidate050/DockAssembly.FCStd')
    context_path=Path(context_path) if context_path else complete if complete.exists() else m.SHELL
    paths.append(context_path)
    if device_path: paths.append(Path(device_path))
    if device_path: paths.append(Path(device_path).parent/'ButtonPressKeepouts.FCStd')
    before={str(p):m.sha(p) for p in paths}
    # Actual Boolean/per-solid controls retain material containment and overlap.
    control=Part.makeBox(10,10,10); contained=Part.makeBox(2,2,2,App.Vector(4,4,4))
    assert control.distToShape(contained)[0]<1e-8 and abs(common(control,contained)-8)<1e-8
    assert abs(common(control,Part.makeBox(2,2,2,App.Vector(9,9,9)))-1)<1e-8
    assert abs(common(control,Part.makeCompound([contained,Part.makeBox(2,2,2,App.Vector(20,20,20))]))-8)<1e-8
    rows=m.physical_shapes(part); body_checks=[]
    for o in doc.Objects:
        if o.TypeId!='PartDesign::Body': continue
        s=o.Shape
        print('Checking native body',o.Name,flush=True)
        if o.Name=='RecenteredMagnetSpringSource':
            evidence=json.loads(Path(__file__).with_name('selected-coil-bop-evidence.json').read_text())
            frozen_path=Path(__file__).with_name('selected-coil-source.brp')
            assert m.sha(frozen_path)==evidence['serialized_BRep_SHA256']==o.BRepSourceSHA256
            reference=Part.Shape();reference.importBrep(str(frozen_path))
            assert len(s.Faces)==len(reference.Faces) and len(s.Edges)==len(reference.Edges)
            assert abs(s.Volume-reference.Volume)<1e-8 and abs(s.Area-reference.Area)<1e-8
            assert max(abs(a-b)for a,b in zip(m.bounds(s),m.bounds(reference)))<1e-7
            # Saving through a Body canonicalises BRep location/serialization.
            # Compare actual sampled edge geometry as well as the source import
            # hash and native geometry invariants; do not claim byte identity.
            def samples(shape):
                return sorted(tuple(round(c,8)for c in edge.valueAt(edge.FirstParameter+(edge.LastParameter-edge.FirstParameter)*j/8))
                              for edge in shape.Edges for j in range(9))
            assert samples(s)==samples(reference)
            assert m.sha(ROOT/'tools/build_evt1_dock_button_mechanics.py')==evidence['source_spring_helper_SHA256']
            errors=evidence['BOP_errors'];method='Known failing C0 source BRep imported by strict hash; saved-native topology/area/volume/exact bounds/edge samples match. Serialization is not claimed identical.'
        else:
            s.check(True); errors=[];method='Fresh actual BOP check'
        mesh=MeshPart.meshFromShape(Shape=s,LinearDeflection=.08,AngularDeflection=.2,Relative=False)
        check={'name':o.Name,'valid':s.isValid(),'solids':len(s.Solids),
               'volume_mm3':s.Volume,'BOP_errors':errors,'BOP_pass':not errors,'BOP_method':method,'closed_mesh':mesh.isSolid(),
               'bounds_mm':m.bounds(s)}
        assert check['valid'] and check['solids']==1 and check['closed_mesh'],check
        body_checks.append(check)
    assert all(s.FullyConstrained for s in doc.Objects if s.TypeId=='Sketcher::SketchObject')
    print('Measuring actual coil bearing/radial gaps',flush=True)
    coil_checks=measure_coils(doc,part)
    print('Actual selected coil checks',coil_checks,flush=True)
    hard=[]; intentional=[]; count=0
    for (na,a),(nb,b) in itertools.combinations(rows,2):
        count+=1; v=pair_common(na,a,nb,b)
        if v<1e-6: continue
        screw=na if 'Screw' in na else nb if 'Screw' in nb else None
        other=nb if screw==na else na
        if screw and other==part.Carrier.Name:
            hit=a.common(b); bb=hit.optimalBoundingBox(False,False)
            if 'FootScrew' in screw: assert bb.ZMin>=5.49999 and bb.ZMax<=12.25001
            else: assert bb.YMin>=15.99999 and bb.YMax<=20.00001
            intentional.append({'a':na,'b':nb,'mm3':v,'basis':'Cosmetic thread-major/pilot annulus; fastening remains unqualified'})
        else: hard.append({'a':na,'b':nb,'mm3':v})
    print('Static pairs checked',count,flush=True)
    old=App.openDocument(str(m.PREFLIGHT))
    clips=[('unchanged_feet_and_lower_legs_below_Z11p8',part.Carrier.Shape,old.ContactCarrier.Shape,m.box(-55,5,5,-5,30,11.7999)),
           ('unchanged_rear_hood_entry_baffle',part.Retainer.Shape,old.ContactRetainer.Shape,m.box(-32.01,7.9,13.2,-23.99,13.99,21.1))]
    preservation=[]
    for name,new,previous,region in clips:
        a,b=new.common(region),previous.common(region)
        delta=a.cut(b).Volume+b.cut(a).Volume
        assert delta<1e-6,(name,delta)
        preservation.append({'region':name,'symmetric_difference_mm3':delta})
    # Board's actual holes and all source land geometry remain untouched.
    pcb=next((s for n,s in rows if n=='RecenteredPinBoard'))
    assert max(abs(a-b) for a,b in zip(m.bounds(pcb),[-20,17.7962,35.3,8,18.7962,45.3]))<1e-6
    for i,x in enumerate(m.CONTACT_X):
        tip=doc.getObject('RecenteredPogo'+str(i)).Shape
        assert abs(m.bounds(tip)[4]-23.2)<1e-7
        passage=Part.makeCylinder(.5334,.8,App.Vector(x,22.5,42),App.Vector(0,1,0))
        assert common(passage,part.Carrier.Shape)<1e-7
    context_doc,context=_context(context_path)
    context,relief_report=liner_relief(doc,context_doc,context)
    print('Approved native liner relief',relief_report,flush=True)
    # The exact native main PCB is always checked, even for the shell-only context.
    main_doc=App.openDocument(str(m.MAIN_PCB)); main=m.root_part(main_doc).Shape.copy()
    main=m.placed(main,App.Placement(App.Vector(0,32,6.4),App.Rotation()))
    main_top=main.optimalBoundingBox(False,False).ZMax
    assert abs(main_top-10.645)<1e-6,main_top
    skirt_checks=[]
    for i in range(2):
        f=doc.getObject('RecenteredCollarFrontReturnSkirt'+str(i))
        tool=f.AddSubShape.copy();tool.Placement=f.Placement.multiply(tool.Placement)
        lower=tool.optimalBoundingBox(False,False).ZMin
        assert abs(lower-11.8)<1e-6 and lower-main_top>1.15
        aperture=doc.RelievedLowerLinerContext.Shape
        gap=tool.distToShape(aperture)[0]
        assert gap>=.29999,(i,gap)
        skirt_checks.append({'foot':i,'actual_floor_aperture_gap_mm':gap,'actual_MainPCB_top_mm':main_top,
                             'skirt_bottom_mm':lower,'guaranteed_vertical_MainPCB_separation_mm':lower-main_top})
    if not any('MainBoard' in n for n,s,side in context): context.append(('ActualMainPCB',main,'base'))
    context_boxes={n:s.optimalBoundingBox(False,False)for n,s,side in context}
    context_hits=[]; context_count=0
    for n,a in rows:
        for cn,b,side in context:
            context_count+=1
            if not a.optimalBoundingBox(False,False).intersect(context_boxes[cn]):continue
            v=pair_common(n,a,cn,b)
            if v>1e-5: context_hits.append({'trial':n,'context':cn,'mm3':v})
    # Close the retainer from behind before putting the module in the case.
    retainer_load=[]
    for offset in (-20,-15,-10,-7,-5,-3,-2,-1,-.5,-.2,0):
        s=part.Retainer.Shape.copy(); s.translate(App.Vector(0,offset,0))
        v=common(s,part.Carrier.Shape)
        assert v<1e-6,('retainer loading',offset,v)
        retainer_load.append({'rear_Y_offset_mm':offset,'carrier_intersection_mm3':v})
    # Insert the unchanged board/pins through the rear recess, with pins free.
    pogo=doc.getObject('RecenteredPogoSource'); pogo.Parameters.Compression=0; doc.recompute()
    board_load=[]
    for offset in (-12,-9,-6,-3,-1,-.5,-.2,0):
        for name in ['RecenteredPinBoard']+['RecenteredPogo'+str(i) for i in range(4)]:
            s=doc.getObject(name).Shape.copy(); s.translate(App.Vector(0,offset,0))
            v=common(s,part.Carrier.Shape)
            assert v<1e-6,('board loading',name,offset,v)
            board_load.append({'part':name,'rear_Y_offset_mm':offset,'carrier_intersection_mm3':v})
    free_rows=m.physical_shapes(part)
    pogo.Parameters.Compression=.6; doc.recompute()
    module_load=[]; loading_hits=[]
    for lift in (40,35,30,25,20,15,12,10,8,6,4,3,2,1,.5,0):
        for n,a in free_rows:
            if 'FootScrew' in n: continue
            s=a.copy(); s.translate(App.Vector(0,0,lift))
            moving_box=s.optimalBoundingBox(False,False)
            for cn,b,side in context:
                if side!='base': continue
                if not moving_box.intersect(context_boxes[cn]):continue
                v=pair_common(n,s,cn,b,lift)
                if v>1e-5: loading_hits.append({'trial':n,'context':cn,'Z_lift_mm':lift,'mm3':v})
        module_load.append({'Z_lift_mm':lift,'clear':not any(h['Z_lift_mm']==lift for h in loading_hits)})
    print('Vertical module loading checked',len(module_load),flush=True)
    drivers=[]
    for x in m.RETAINER_X:
        tool=Part.makeCylinder(1.7,22,App.Vector(x,-10,33),App.Vector(0,1,0))
        assert common(tool,part.Carrier.Shape)+common(tool,part.Retainer.Shape)<1e-6
        blocked=[cn for cn,s,side in context if side=='base' and common(tool,s)>1e-5]
        drivers.append({'role':'rear M2 driver reservation','X_mm':x,'radius_mm':1.7,
                        'preassembled_clear':True,'installed_blocking_context':blocked,
                        'qualified_actual_tool':False})
    for x in m.FOOT_X:
        tool=Part.makeCylinder(2.4,20.2,App.Vector(x,19,-20),App.Vector(0,0,1))
        blocked=[cn for cn,s,side in context if side=='base' and common(tool,s)>1e-5]
        assert not blocked,('underside M3 driver',x,blocked)
        drivers.append({'role':'underside M3 driver reservation','X_mm':x,'radius_mm':2.4,
                        'installed_clear':True,'qualified_actual_tool':False})
    lid_motion=[]
    trial_boxes=[s.optimalBoundingBox(False,False)for n,s in rows]
    for angle in (0,.25,.5,1,2,3,5,10,30,60,90,110):
        pose=App.Placement(App.Vector(0,0,0),App.Rotation(App.Vector(1,0,0),-angle),App.Vector(0,164.4,40.15))
        posed=[]
        for cn,s,side in context:
            if side!='lid':continue
            enclosure=posed_box(context_boxes[cn],pose)
            if any(enclosure.intersect(bb)for bb in trial_boxes):posed.append((cn,m.placed(s,pose)))
        posed_boxes={cn:s.optimalBoundingBox(False,False)for cn,s in posed}
        for n,a in rows:
            ab=a.optimalBoundingBox(False,False)
            for cn,b in posed:
                if not ab.intersect(posed_boxes[cn]):continue
                v=pair_common(n,a,cn,b)
                assert v<1e-5,('lid motion',angle,n,cn,v)
        lid_motion.append({'angle_deg':angle,'clear':True})
        print('Carrier/lid angle checked',angle,flush=True)
    device_checks={'state':'No frozen candidate supplied; actual device/skin mating remains open'}
    if device_path:
        from device_check import check_device
        print('Checking frozen revised device mating and case context',flush=True)
        device_checks=check_device(doc,part,Path(device_path),context)
    pogo.Parameters.Compression=.6; doc.recompute(); doc.save()
    # Save mesh inputs for a faithful standalone PNG renderer, not a fit proxy.
    preview=[]
    for n,s in m.physical_shapes(part):
        verts,faces=s.tessellate(.12)
        rgb=[.90,.86,.76] if n in (part.Carrier.Name,part.Retainer.Name) else [.75,.57,.18] if 'Pogo' in n else [.25,.28,.30] if 'Magnet' in n else [.25,.55,.28] if 'PinBoard' in n else [.60,.63,.67]
        preview.append({'name':n,'vertices':[list(v) for v in verts],'triangles':faces,'color':rgb})
    (m.OUT/'preview-meshes.json').write_text(json.dumps(preview))
    after={str(p):m.sha(p) for p in paths}; assert before==after
    report={'pass':not hard and not context_hits and not loading_hits,'scope':'New carrier/retainer BOP and nominal fit with approved context-only liner relief; inherited selected-coil BOP continuity exception is explicit, no strength/received/physical qualification',
            'whole_dock_with_device_pass':not hard and not context_hits and not loading_hits and device_checks.get('preceding_context_all_clear',False),
            'all_component_BOP_checks_pass':all(b['BOP_pass'] for b in body_checks),
            'body_checks':body_checks,'static_pair_count':count,'hard_intersections':hard,
            'intentional_thread_pilot_intersections':intentional,'source_geometry_preservation':preservation,
            'PinPCB_pose':{'translation_mm':list(m.PIN_POSE[0]),'Rx_deg':m.PIN_POSE[1]},
            'context_path':str(context_path),'context_pair_count':context_count,'context_intersections':context_hits,
            'context_objects':[{'name':n,'side':side,'bounds_mm':m.bounds(s)}for n,s,side in context],
            'approved_liner_relief':relief_report,
            'approved_collar_return_skirts':skirt_checks,
            'ray_source_blocking_state':'Prior fourteen clear seam rays remain historical findings. Oldcollar floor-blocking isnot transferred aftertrim; steppedskirts aregeometryonlyandneedfreshwholeassemblyray/leakage tests. No opticalcontainmentclaim.',
            'coil_pair_method':'Actual carrier/retainer/pilot/magnet helix distances separately measured. Case/motion pairs use conservative annular ID2.0/OD5.2,length3.8 strictly surrounding nominal source-helix ID3.85/OD4.57; every envelope overlap gets actual Boolean. Native helix retained, C0 failure explicit; no received/force qualification.',
            'actual_selected_coil_checks':coil_checks,
            'retainer_rear_loading':retainer_load,'board_pin_rear_loading':board_load,'module_vertical_loading':module_load,
            'module_vertical_loading_intersections':loading_hits,
            'driver_reservations':drivers,'lid_motion':lid_motion,'device_mating':device_checks,
            'source_inputs':[{'path':p,'SHA256':value} for p,value in before.items()],
            'source_hashes_unchanged':True,
            'open':['Received tolerances, print dimensional/material/creep/strength and thin-land durability',
                    'Inherited LC014B02S visualization BOPAlgo GeomAbs_C0 edge/face continuity exception; not OEM coil geometry',
                    'Received pin force/contact compression and metal-stop alignment',
                    'Installed flexible wires/tie/strain relief from recentered J94 to unchanged hood',
                    'Magnet retention/holding/compass interference and received coil force',
                    'Actual tools, screw torque/taps, sealing, UV leakage and physical assembly']}
    return report
