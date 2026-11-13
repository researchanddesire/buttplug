"""Build the shared base PCB from source/controller/safety native terminals.

Run with KiCad7 Python, one BOARD per process. Original source sheets and
audited placement candidates are read-only. New routed edits cannot be
overwritten by this placement builder.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import shutil
import sys
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import wx
APP=wx.App(False)
import pcbnew as k
import kicad_sexp as s

sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def xy(x,y):return k.VECTOR2I(round((100+x)*1e6),round((200-y)*1e6))
def dock(point):return [round(k.ToMM(point.x)-100,6),round(200-k.ToMM(point.y),6)]

# Placement is local to the current mechanical regions. GH side-entry mates
# point toward the rear, with room for a planar wire exit under the liner.
SAFETY={
 'U610':(28,28,0),'U611':(31,28,0),
 'C610':(28.5,26,0),'C611':(31,24.8,0),
 'C620':(25,28,90),'C621':(29.5,31,0),'C622':(34,28,90),
 'C623':(28,33.5,90),'C624':(31,33.5,90),
 'R610':(25.5,33.5,90),'R611':(34,33.5,90),
 'R612':(25,36,0),'R613':(34,36,0),'R616':(37,29,90),
 'U602':(40,28,0),'C602':(43.5,28,90),
 'U608':(13,37,0),'C608':(10.2,37,90),'R617':(13,33.5,0),
 'U614':(33,44.3,0),'C614':(30,44.3,90),'R619':(33,41.8,0),
 'U606':(21,39,0),'C606':(18,39,90),'R603':(21,35,0),
 'R602':(18,43,90),'R601':(21,43,0),'R606':(18,46,0),
 'U607':(27,39,0),'C607':(24,39,90),
 'U616':(13,46,0),'C616':(10,46,90),'R607':(13,50,0),'R608':(10,50,90),
 'U613':(41,38,0),'C613':(44,38,90),
 'R614':(40,34,90),'R615':(43,34,90),
 'U612':(23,50,0),'C612':(25.7,53.7,0),
 'U609':(33,50,0),'C609':(35.7,53.7,0),
 'U615':(42,50,0),'C615':(46.4,52,90),
 'R604':(28,55,90),'R605':(19,55,90),'R618':(16.7,49.8,90),
 'J601':(13,56,180),'J602':(13,64,180),
 'J621':(26,62,180),'J622':(40.9,62,180),
 'TP601':(8,30,0),'TP602':(4,32,0),'TP603':(4,35,0),
 'TP604':(4,46,0),'TP605':(4,49,0),'TP606':(8,33,0),'TP607':(8,36,0),
}


def source_tables():
    libraries={}
    for folder in ('dock-ui','dock-control','dock-safety'):
        owner=BASE/folder
        for lib in s.children(s.parse((owner/'fp-lib-table').read_text()),'lib'):
            name=s.value(lib,'name')
            path=Path(s.value(lib,'uri').replace('${KIPRJMOD}',str(owner))).resolve()
            libraries[name]=path
    # Parent-owned critical source copper uses only documented nonphysical
    # silk/courtyard edits. Take those exact local footprint snapshots too.
    libraries['DockUI']=HERE/'source-block/SourceBlock.pretty'
    return libraries


def local_footprints(components):
    libraries=source_tables();provenance={};namespaces=set()
    for comp in components:
        footprint=comp.findtext('footprint');alias,name=footprint.split(':')
        source=libraries[alias]/(name+'.kicad_mod')
        destination=HERE/(alias+'.pretty')/source.name
        destination.parent.mkdir(exist_ok=True)
        tree=s.parse(source.read_text())
        models=[]
        for model in s.children(tree,'model'):
            original=model[1].value
            if '${KIPRJMOD}' in original:
                owner=libraries[alias].parent
                resolved=Path(original.replace('${KIPRJMOD}',str(owner))).resolve()
                assert resolved.exists(),resolved
                relative=__import__('os').path.relpath(resolved,HERE)
                model[1]=s.string('${KIPRJMOD}/'+relative)
                models.append({'source':str(resolved.relative_to(ROOT)),'sha256':sha(resolved)})
        s.write(destination,tree)
        provenance[footprint]={'source':str(source.relative_to(ROOT)),
                               'source_sha256':sha(source),
                               'local':str(destination.relative_to(HERE)),
                               'local_sha256':sha(destination),
                               'change':'Only local3D URIs rebased; pads/body/numbering retained',
                               'models':models}
        namespaces.add(alias)
    table=s.parse('(fp_lib_table (version 7))')
    for alias in sorted(namespaces):
        table.append(s.parse('(lib (name '+json.dumps(alias)+')(type "KiCad")(uri '+
                             json.dumps('${KIPRJMOD}/'+alias+'.pretty')+')(options "")(descr "Attributed dock source footprint snapshot"))'))
    s.write(HERE/'fp-lib-table',table)
    (HERE/'footprint-provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')


def line_loop(board,points):
    for start,end in zip(points,points[1:]+points[:1]):
        edge=k.PCB_SHAPE(board);edge.SetShape(k.SHAPE_T_SEGMENT)
        edge.SetStart(xy(*start));edge.SetEnd(xy(*end));edge.SetWidth(k.FromMM(.05))
        edge.SetLayer(k.Edge_Cuts);board.Add(edge)


def hardware_clearance(board,x,y,radius=3):
    # Surface copper/vias must clear the actual M2 screw head, not only its
    # drilled bore. Native courtyards and the independent pad-radius audit
    # cover component placement; NPTH mechanical pads are not copper pads.
    for layer in (k.F_Cu,k.B_Cu):
        zone=k.ZONE(board);zone.SetLayer(layer);zone.SetIsRuleArea(True)
        zone.SetDoNotAllowTracks(True);zone.SetDoNotAllowVias(True)
        zone.SetDoNotAllowCopperPour(True);zone.SetDoNotAllowPads(False)
        zone.SetDoNotAllowFootprints(False)
        shape=zone.Outline();shape.NewOutline()
        for i in range(32):
            t=math.pi*2*i/32;p=xy(x+radius*math.cos(t),y+radius*math.sin(t));shape.Append(p.x,p.y)
        board.Add(zone)


def block_data(path):
    """Read placements and copper without loading a second live native BOARD."""
    tree=s.parse(path.read_text());positions={}
    for fp in s.children(tree,'footprint'):
        if not any(p[1].value for p in s.children(fp,'pad')):
            continue  # Mechanical holes are recreated from the shell datums.
        ref=next(t[2].value for t in s.children(fp,'fp_text')if t[1].value=='reference')
        at=s.child(fp,'at');position=[float(at[1].value)-100,200-float(at[2].value),float(at[3].value)if len(at)>3 else 0]
        assert s.value(fp,'layer')=='F.Cu',('Source block B-side placement needs explicit handling',ref)
        positions[ref]=position
    nets={int(n[1].value):n[2].value for n in s.children(tree,'net')}
    return positions,tree,nets


def import_locked_copper(board,tree,nets):
    count=0
    layers={name:board.GetLayerID(name)for name in ('F.Cu','In1.Cu','In2.Cu','B.Cu')}
    for segment in s.children(tree,'segment'):
        track=k.PCB_TRACK(board)
        def point(name):
            p=s.child(segment,name);return k.VECTOR2I(round(float(p[1].value)*1e6),round(float(p[2].value)*1e6))
        track.SetStart(point('start'));track.SetEnd(point('end'))
        track.SetWidth(k.FromMM(float(s.value(segment,'width'))))
        track.SetLayer(layers[s.value(segment,'layer')])
        track.SetNet(board.FindNet(nets[int(s.value(segment,'net'))]))
        track.SetLocked(True);board.Add(track);count+=1
    for source in s.children(tree,'via'):
        via=k.PCB_VIA(board);at=s.child(source,'at')
        via.SetPosition(k.VECTOR2I(round(float(at[1].value)*1e6),round(float(at[2].value)*1e6)))
        via.SetWidth(k.FromMM(float(s.value(source,'size'))));via.SetDrill(k.FromMM(float(s.value(source,'drill'))))
        pair=s.child(source,'layers');via.SetLayerPair(layers[pair[1].value],layers[pair[2].value])
        via.SetViaType(k.VIATYPE_THROUGH);via.SetNet(board.FindNet(nets[int(s.value(source,'net'))]))
        via.SetLocked(True);board.Add(via);count+=1
    assert not s.children(tree,'arc'),'Explicit arc import required before preserving source copper'
    assert all(s.value(zone,'net_name') in ('GND',None)or s.child(zone,'keepout')is not None
               for zone in s.children(tree,'zone')),'Non-GND source zone needs explicit preservation'
    return count


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source-block',type=Path,required=True)
    parser.add_argument('--restart-placement',action='store_true')
    args=parser.parse_args();path=HERE/'dock-main.kicad_pcb'
    if path.exists():
        previous=json.loads((HERE/'placement.json').read_text())
        assert not previous.get('routing_started',False),'Routed main candidate cannot be restarted; preserve it explicitly first'
        assert args.restart_placement and sha(path)==previous['native_board_sha256'], 'Preserve edited/routed main board before restarting placement'
    source=args.source_block.resolve();source_positions,source_tree,source_nets=block_data(source)
    source_checked=json.loads((HERE/'source-block/checks.json').read_text())
    assert source_checked['board_sha256']==sha(source),'Only the final native-checked source block may be promoted'
    system=BASE/'dock-system/native.xml';xml=ET.parse(system).getroot()
    checked=json.loads((BASE/'dock-system/native-checks.json').read_text())
    assert checked['status']=='pass' and checked['reports_sha256']['native.xml']==sha(system)
    components=[c for c in xml.findall('./components/comp')
                if c.find('sheetpath').get('names') in ('/dock-ui-source/','/dock-controller/','/dock-safety/') and c.findtext('footprint')]
    local_footprints(components)
    controller=json.loads((BASE/'dock-control/dock-controller-placement.json').read_text())
    positions=dict(controller['footprint_placements_dock_xy_and_native_angle'])
    # Actual local bypass/filter placement, independent of the earlier banks.
    positions.update({'C201':(-31.75,49.8,0),'C202':(-35.4,45.75,90),
                      'C203':(-24.3,36.7,0),'C204':(-22.5,45.75,90),
                      'C208':(-30.5,36.1,90),'C209':(-27.5,36.1,90),
                      'R220':(-30.5,33.5,90),'R221':(-27.5,33.5,90),
                      'R218':(-22,31,90),'R219':(-18,31,90)})
    assert not set(positions)&set(source_positions)
    positions.update(source_positions)
    assert not set(positions)&set(SAFETY)
    positions.update(SAFETY)
    expected={c.get('ref')for c in components}
    assert expected==set(positions),(sorted(expected-set(positions)),sorted(set(positions)-expected))
    board=k.BOARD();board.SetFileName(str(path));board.SetCopperLayerCount(4)
    ds=board.GetDesignSettings();ds.SetBoardThickness(k.FromMM(1))
    ds.m_MinClearance=k.FromMM(.15);ds.m_TrackMinWidth=k.FromMM(.15)
    ds.m_HoleClearance=k.FromMM(.2);ds.m_CopperEdgeClearance=k.FromMM(.3)
    ds.m_MinThroughDrill=k.FromMM(.2);ds.m_ViasMinSize=k.FromMM(.5)
    default=ds.m_NetSettings.m_DefaultNetClass
    default.SetClearance(k.FromMM(.15));default.SetTrackWidth(k.FromMM(.2))
    default.SetViaDiameter(k.FromMM(.5));default.SetViaDrill(k.FromMM(.2))
    board.GetDesignSettings().SetAuxOrigin(xy(0,0));pin_nets={}
    for net in xml.findall('./nets/net'):
        name=net.get('name');board.Add(k.NETINFO_ITEM(board,name))
        for node in net.findall('node'):pin_nets[(node.get('ref'),node.get('pin'))]=name
    for component in components:
        ref=component.get('ref');alias,name=component.findtext('footprint').split(':')
        footprint=k.FootprintLoad(str(HERE/(alias+'.pretty')),name)
        assert footprint,(ref,alias,name)
        footprint.SetFPID(k.LIB_ID(alias,name));footprint.SetReference(ref)
        footprint.SetValue(component.findtext('value'));pos=positions[ref]
        footprint.SetPosition(xy(*pos[:2]));footprint.SetOrientationDegrees(pos[2]);footprint.SetLocked(True)
        footprint.SetPath(k.KIID_PATH(component.find('sheetpath').get('tstamps')+component.findtext('tstamps')))
        footprint.Reference().SetVisible(False);footprint.Value().SetVisible(False)
        for pad in footprint.Pads():
            number=pad.GetNumber()
            if number:
                net=pin_nets.get((ref,number));assert net,(ref,number)
                pad.SetNet(board.FindNet(net))
                if ref in ('U610','U611') and number=='4':
                    # The0.25mm-wide RXP ground land cannot fit two0.25mm
                    # thermal spokes. A solid reference connection is intended.
                    pad.SetZoneConnection(k.ZONE_CONNECTION_FULL)
        board.Add(footprint)
    outline=controller['outline_dock_xy_mm'];line_loop(board,outline)
    for points in controller['cutouts_dock_xy_mm']:line_loop(board,points)
    copper=import_locked_copper(board,source_tree,source_nets)
    # Preserve the four actual USB-board shell bosses; add two rear supports
    # for the enlarged base. Rear bosses are a subsequent native assembly edit.
    holes=[]
    for i,(x,y)in enumerate(((-8,5.5),(8,5.5),(-8,23.5),(8,23.5),(-44,64),(44,55.7))):
        footprint=k.FOOTPRINT(board);footprint.SetReference('H'+str(701+i));footprint.SetValue('M2clearance2.3')
        footprint.SetPosition(xy(x,y));footprint.Reference().SetVisible(False);footprint.Value().SetVisible(False)
        pad=k.PAD(footprint);pad.SetNumber('');pad.SetAttribute(k.PAD_ATTRIB_NPTH)
        pad.SetShape(k.PAD_SHAPE_CIRCLE);pad.SetSize(k.VECTOR2I(k.FromMM(2.3),k.FromMM(2.3)))
        pad.SetDrillSize(k.VECTOR2I(k.FromMM(2.3),k.FromMM(2.3)))
        layers=k.LSET.AllCuMask();layers.AddLayer(k.F_Mask);layers.AddLayer(k.B_Mask);pad.SetLayerSet(layers)
        footprint.SetLocked(True)
        footprint.Add(pad);board.Add(footprint);holes.append([x,y,2.3])
        hardware_clearance(board,x,y)
    k.SaveBoard(str(path),board)
    (HERE/'dock-main.kicad_dru').write_text('''(version 1)
# Manufacturer USB4105 locating-hole/pad pattern has0.1751mm nominal copper
# separation. This bounded exception preserves that pattern; fabricator
# acceptance is still required. All other holes retain0.20mm minimum.
(rule "USB4105 manufacturer locating-hole pattern"
 (condition "A.memberOfFootprint('J101') && B.memberOfFootprint('J101')")
 (constraint hole_clearance (min 0.15mm)))
''')
    report={'scope':'Shared dock source/controller/safety placement with preserved source copper; routing/fit incomplete',
            'native_board_sha256':sha(path),'builder_sha256':sha(Path(__file__)),
            'system_xml_sha256':sha(system),'source_block':str(source.relative_to(ROOT)),
            'source_block_sha256':sha(source),'preserved_source_route_objects':copper,
            'footprints':len(components),'footprint_placements_dock_xy_native_angle':positions,
            'mounting_holes_dock_xy_d_mm':holes,'outline_dock_xy_mm':outline,
            'cutouts_dock_xy_mm':controller['cutouts_dock_xy_mm'],'layers':4,'thickness_mm':1,
            'F_Cu_global_Z_mm':6.4,'mechanical_integration_verified':False,
            'full_product_order_ready':False}
    (HERE/'placement.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'footprints':len(components),'preserved_source_routes':copper,'board':str(path)},indent=2))


if __name__=='__main__':main()
