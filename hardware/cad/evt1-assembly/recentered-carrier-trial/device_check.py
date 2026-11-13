"""Read-only frozen canonical exterior and exact button-press keepout checks."""
from pathlib import Path
import FreeCAD as App
import Part
import build_evt1_dock_recentered_carrier as m

NAMES=('MetalBody','MotorThermistorCap','ContinuousSkin','Contact_GND',
       'Contact_USB_DM','Contact_USB_DP','Contact_DOCK_5V','SteelKeeper0','SteelKeeper1')
EXTERIOR_SHA='4b9471fea1af7ace656350d1bc001c665d675ac7fe8014103637b7c204a3b7c5'
KEEP_SHA='a53dd2418516020987e14224f249a8deb583b08baf07801c0e843c2d9926f1ca'

def common(a,b):
    if not a.optimalBoundingBox(False,False).intersect(b.optimalBoundingBox(False,False)):return 0.
    if len(a.Solids)>1 or len(b.Solids)>1:return sum(common(x,y)for x in a.Solids for y in b.Solids)
    return a.common(b).Volume

def shifted_bounds(bb,offset):
    result=App.BoundBox(bb.XMin,bb.YMin+offset,bb.ZMin,
                        bb.XMax,bb.YMax+offset,bb.ZMax)
    return result

def check_device(doc,part,path,lid_context=()):
    assert m.sha(path)==EXTERIOR_SHA
    keep_path=Path(path).parent/'ButtonPressKeepouts.FCStd';assert m.sha(keep_path)==KEEP_SHA
    source=App.openDocument(str(Path(path).resolve()));keep=App.openDocument(str(keep_path.resolve()))
    assert {o.Name for o in source.Objects if o.TypeId=='PartDesign::Body'}==set(NAMES)
    pose=App.Placement(App.Vector(*m.DEVICE_POSE),App.Rotation())
    selected=[(n,m.placed(source.getObject(n).Shape,pose))for n in NAMES]
    contact_rows=[]
    for x,name in zip(m.CONTACT_X,NAMES[3:7]):
        b=source.getObject(name).Shape.optimalBoundingBox(False,False)
        assert abs(b.YMin+30)<1e-6 and abs((b.XMin+b.XMax)/2-x)<1e-6
        assert abs((b.ZMin+b.ZMax)/2-10)<1e-6 and abs(b.XLength-3.175)<1e-6
        contact_rows.append({'name':name,'dock_axis_XZ_mm':[x,42],
                             'dock_face_Y_mm':23.2,'actual_head_diameter_mm':b.XLength,
                             'stop_OD_mm':2.4,'nominal_radial_margin_mm':.3875})
    pogo=doc.RecenteredPogoSource;mating=[];hits=[];case_hits=[]
    from check_trial import pair_common,posed_box
    context_boxes={n:s.optimalBoundingBox(False,False)for n,s,side in lid_context}
    # Compute exact bounds once. The only moving module geometry is the four
    # linked plungers, whose compression is recomputed and bounded every pose.
    fixed_hardware=m.physical_shapes(part)
    hardware_boxes={n:s.optimalBoundingBox(False,False)for n,s in fixed_hardware}
    selected_boxes={n:s.optimalBoundingBox(False,False)for n,s in selected}
    xmin=min(b.XMin for b in hardware_boxes.values());xmax=max(b.XMax for b in hardware_boxes.values())
    skin=dict(selected)['ContinuousSkin'];sb=selected_boxes['ContinuousSkin']
    skin_clip=skin.common(Part.makeBox(xmax-xmin,23.3-(sb.YMin-1),sb.ZLength+2,
                                     App.Vector(xmin,sb.YMin-1,sb.ZMin-1)))
    assert skin_clip.Volume<1e-8,('skin in module X domain below Y23.3',skin_clip.Volume)
    assert all(b.YMax<=23.200001 for n,b in hardware_boxes.items()if 'Pogo'not in n)
    assert all(b.YMin>=23.199999 for n,b in selected_boxes.items()if n!='ContinuousSkin')
    certificate={'module_X_domain_mm':[xmin,xmax],
                 'actual_skin_clip_X_domain_and_Y_le_23p3_volume_mm3':skin_clip.Volume,
                 'actual_skin_clip_method':'Exact BRep common, not a global bounding-box minimum inference',
                 'fixed_nonplunger_hardware_max_Y_mm':max(b.YMax for n,b in hardware_boxes.items()if 'Pogo'not in n),
                 'skin_in_module_X_domain_minimum_Y_mm':23.3,
                 'positive_Y_loading_separation':'The arrow outside this X domain cannot touch the module. All other device parts start at or behind Y23.2. Exact linked-plunger bounds are rechecked at each compression pose.',
                 'per_pose_certificate_counts':[]}
    for step in range(49):
        offset=3*(48-step)/48
        compression=max(0.,.6-offset);pogo.Parameters.Compression=compression;doc.recompute()
        hardware=[(n,doc.getObject(n).Shape if 'Pogo'in n else s)for n,s in fixed_hardware];n=0;certified=0;booleans=0
        actual_boxes=dict(hardware_boxes)
        for hn,hs in hardware:
            if 'Pogo'in hn:
                actual_boxes[hn]=hs.optimalBoundingBox(False,False)
                assert actual_boxes[hn].YMax<=23.2+offset+1e-6,(hn,offset,actual_boxes[hn].YMax)
        for name,original in selected:
            mb=shifted_bounds(selected_boxes[name],offset)
            moved=None
            for other,shape in hardware:
                n+=1;hb=actual_boxes[other]
                separated=(not mb.intersect(hb) or mb.YMin>=hb.YMax-1e-7)
                if name=='ContinuousSkin':
                    separated=(hb.XMin>=xmin-1e-7 and hb.XMax<=xmax+1e-7
                               and hb.YMax<=23.3+offset-1e-7)
                if separated:certified+=1;continue
                if moved is None:moved=original.copy();moved.translate(App.Vector(0,offset,0))
                booleans+=1;v=pair_common(other,shape,name,moved)
                if v>1e-5:hits.append({'device':name,'dock':other,'offset_Y_mm':offset,'mm3':v})
            for other,shape,side in lid_context:
                if side!='base' or not mb.intersect(context_boxes[other]):continue
                if moved is None:moved=original.copy();moved.translate(App.Vector(0,offset,0))
                v=common(moved,shape)
                if v>1e-5:case_hits.append({'device':name,'preceding_context':other,'offset_Y_mm':offset,'mm3':v})
            del moved
        mating.append({'offset_Y_mm':offset,'pogo_compression_mm':compression,'physical_pairs':n})
        certificate['per_pose_certificate_counts'].append({'offset_Y_mm':offset,'plane_or_exact_skin_certificate_pairs':certified,'actual_Boolean_pairs':booleans})
        print('Device mating offset checked',offset,flush=True)
    assert not hits,hits
    buttons=[]
    for name in ('IntegralSiliconeBoss0','IntegralSiliconeBoss1'):
        obj=keep.getObject(name);assert obj is not None;crown=m.placed(obj.Shape,pose)
        assert abs(crown.optimalBoundingBox(False,False).YMin-23.4)<1e-6
        clearance=part.Carrier.Shape.distToShape(crown)[0];assert abs(clearance-.3)<1e-6
        for press in (0,.1,.25,.5,.7):
            moved=crown.copy();moved.translate(App.Vector(0,press,0))
            for other,shape in m.physical_shapes(part):assert common(moved,shape)<1e-6,(name,press,other)
        buttons.append({'exact_source_body':name,'actual_unpressed_carrier_clearance_mm':clearance,
                        'additional_plusY_press_samples_mm':[0,.1,.25,.5,.7],
                        'press_force_travel_or_seal_qualified':False})
    lid=[];lid_hits=[]
    device_boxes=[s.optimalBoundingBox(False,False)for n,s in selected]
    for angle in (0,.25,.5,1,2,3,5,10,30,60,90,110):
        transform=App.Placement(App.Vector(0,0,0),App.Rotation(App.Vector(1,0,0),-angle),App.Vector(0,164.4,40.15))
        posed=[]
        for other,b,side in lid_context:
            if side!='lid':continue
            enclosure=posed_box(context_boxes[other],transform)
            if any(enclosure.intersect(bb)for bb in device_boxes):posed.append((other,m.placed(b,transform)))
        posed_boxes={other:s.optimalBoundingBox(False,False)for other,s in posed}
        for name,a in selected:
            ab=a.optimalBoundingBox(False,False)
            for other,moved in posed:
                if not ab.intersect(posed_boxes[other]):continue
                v=common(a,moved)
                if v>1e-5:lid_hits.append({'device':name,'preceding_context':other,'angle_deg':angle,'mm3':v})
        lid.append({'angle_deg':angle,'clear':not any(h['angle_deg']==angle for h in lid_hits)})
        print('Device/lid angle checked',angle,flush=True)
    pogo.Parameters.Compression=.6;doc.recompute()
    return {'state':'Frozen complete canonical exterior and exact separate pressed keepouts checked read-only',
            'source_path':str(path),'source_SHA256':m.sha(path),'pressed_keepout_path':str(keep_path),
            'pressed_keepout_SHA256':m.sha(keep_path),'selected_physical_bodies':list(NAMES),
            'whole_continuous_skin_included':True,'device_translation_mm':list(m.DEVICE_POSE),
            'contact_datums':contact_rows,'device_mating_samples':mating,'device_dock_intersections':hits,
            'continuous_separation_certificate':certificate,
            'actual_button_crown_keepout':buttons,'candidate_lid_motion':lid,
            'device_vs_preceding_base_context':case_hits,'device_vs_preceding_lid_context':lid_hits,
            'preceding_context_all_clear':not case_hits and not lid_hits,
            'context_scope':'050 precedes parent body-seat/device integration; inherited case hits remain explicit, not waived',
            'skin_forward_minimum':'Preserved arrow X25..36 outside carrier maximumX12; complete skin checked, no bbox-minimum preload inference'}
