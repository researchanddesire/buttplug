"""Native KiCad10 UV board authoring; one domain per Python process.

Frozen schematic libraries and exports are inputs only. Generated PCB files
live in leaf pcb/ directories so SaveBoard cannot replace schematic projects.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import shutil
import sys
import xml.etree.ElementTree as ET
import wx
APP=wx.App(False)
import pcbnew as k

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def xy(x,y):return k.VECTOR2I(k.FromMM(100+x),k.FromMM(200-y))
def dock(p):return (round(k.ToMM(p.x)-100,6),round(200-k.ToMM(p.y),6))
OUTLINE=[(-49,86),(-35,86),(-35,128),(35,128),(35,86),(49,86),(49,135),(-49,135)]
MOUNTS=[(-45,89),(45,89),(-45,132),(45,132)]
POSITIONS={
 'U':(-42.5,107.5,90,'B'),'L':(-42.5,103,180,'B'),
 'D1':(-46.5,107,90,'B'),'D2':(-42,94,0,'F'),'D3':(42,94,0,'F'),
 'Q':(-37.5,111.5,0,'B'),'J':(0,131.5,0,'B'),
 'R1':(-41.5,112,0,'B'),'R2':(-42,118,0,'B'),'R3':(-38,118,0,'B'),
 'R4':(-46,118,0,'B'),'R5':(-46,122,0,'B'),'R6':(-42,122,0,'B'),
 'R7':(-38,122,0,'B'),'R8':(-38,125.5,0,'B'),
 'C1':(-38,106,90,'B'),'C2':(-46.5,97.9,270,'B'),
 'C3':(-45,112,0,'B'),'C4':(-42,125.5,0,'B'),'C5':(-46,125.5,0,'B'),
 'TP1':(40,104,0,'B'),'TP2':(44,104,0,'B'),'TP3':(40,111,0,'B'),'TP4':(44,111,0,'B')}

def line(board,points,layer,width=.05):
    for a,b in zip(points,points[1:]+points[:1]):
        g=k.PCB_SHAPE(board);g.SetShape(k.SHAPE_T_SEGMENT)
        g.SetStart(xy(*a));g.SetEnd(xy(*b));g.SetWidth(k.FromMM(width));g.SetLayer(layer);board.Add(g)

def track(board,net,points,layer=k.B_Cu,width=.25):
    for a,b in zip(points,points[1:]):
        if math.dist(a,b)<1e-6:continue
        t=k.PCB_TRACK(board);t.SetStart(xy(*a));t.SetEnd(xy(*b));t.SetWidth(k.FromMM(width))
        t.SetLayer(layer);t.SetNet(board.FindNet(net));board.Add(t)

def via(board,net,point):
    v=k.PCB_VIA(board);v.SetPosition(xy(*point));v.SetWidth(k.FromMM(.6));v.SetDrill(k.FromMM(.3))
    v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(board.FindNet(net));board.Add(v)

def zone(board,net,points,layer,priority=0):
    z=k.ZONE(board);z.SetLayer(layer);z.SetNet(board.FindNet(net))
    z.SetLocalClearance(k.FromMM(.2));z.SetMinThickness(k.FromMM(.2))
    z.SetPadConnection(k.ZONE_CONNECTION_FULL);z.SetAssignedPriority(priority)
    z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
    poly=z.Outline();poly.NewOutline()
    for q in points:
        p=xy(*q);poly.Append(p.x,p.y)
    board.Add(z)

def save(board,path):
    k.SaveBoard(str(path),board)

def place(side,restart=False):
    folder=HERE/side;out=folder/'pcb';out.mkdir(exist_ok=True)
    (out/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "DockUV") (type "KiCad") (uri "${KIPRJMOD}/../DockUV.pretty") (options "") (descr "Frozen selected UV footprints")))\n')
    path=out/('dock-uv-'+side+'.kicad_pcb')
    if path.exists():
        previous=json.loads((out/'placement.json').read_text())
        text=path.read_text()
        assert restart and sha(path)==previous['board_sha256'] and '(segment 'not in text and '(via 'not in text,'Preserve routed/edited PCB before restarting layout'
        archive=Path('/private/tmp/compass-uv-layout-archive');archive.mkdir(exist_ok=True)
        shutil.copy2(path,archive/(side+'-'+sha(path)+'.kicad_pcb'))
    manifest=json.loads((folder/'parts-selection.json').read_text())
    checks=json.loads((folder/'native-checks.json').read_text())
    for rel,h in checks['source_sha256'].items():assert sha(folder/rel)==h,rel
    tree=ET.parse(folder/'native.xml').getroot()
    netmap={(n.get('ref'),n.get('pin')):net.get('name') for net in tree.findall('./nets/net') for n in net.findall('node')}
    comps={c.get('ref'):c for c in tree.findall('./components/comp')}
    b=k.BOARD();b.SetFileName(str(path));b.SetCopperLayerCount(2)
    d=b.GetDesignSettings();d.SetBoardThickness(k.FromMM(1))
    d.m_MinClearance=k.FromMM(.2);d.m_TrackMinWidth=k.FromMM(.2)
    d.m_HoleClearance=k.FromMM(.25);d.m_CopperEdgeClearance=k.FromMM(.3)
    d.m_MinThroughDrill=k.FromMM(.3);d.m_ViasMinSize=k.FromMM(.6)
    nc=d.m_NetSettings.GetDefaultNetclass() if hasattr(d.m_NetSettings,'GetDefaultNetclass') else d.m_NetSettings.m_DefaultNetClass
    nc.SetClearance(k.FromMM(.2));nc.SetTrackWidth(k.FromMM(.25))
    nc.SetViaDiameter(k.FromMM(.6));nc.SetViaDrill(k.FromMM(.3));d.SetAuxOrigin(xy(0,0))
    for net in sorted(set(netmap.values())):b.Add(k.NETINFO_ITEM(b,net))
    base=400 if side=='base' else 500
    for p in manifest['parts']:
        if p['offboard']:continue
        ref=p['reference'];prefix=''.join(c for c in ref if c.isalpha())
        number=int(''.join(c for c in ref if c.isdigit()))-base
        key=prefix+(str(number) if prefix in('R','C','D','TP') else'')
        x,y,angle,surface=POSITIONS[key]
        lib,name=p['footprint'].split(':')
        f=k.FootprintLoad(str(folder/(lib+'.pretty')),name);assert f
        f.SetFPID(k.LIB_ID(lib,name));f.SetReference(ref);f.SetValue(p['value'])
        b.Add(f)  # Flip requires a board parent in the native KiCad API.
        f.SetPosition(xy(x,y))
        if surface=='B':f.Flip(f.GetPosition(),True)
        f.SetOrientationDegrees(angle);f.SetLocked(True)
        c=comps[ref];f.SetPath(k.KIID_PATH(c.find('sheetpath').get('tstamps')+c.findtext('tstamps')))
        f.Reference().SetVisible(False);f.Value().SetVisible(False)
        for pad in f.Pads():pad.SetNet(b.FindNet(netmap[ref,pad.GetNumber()]))
    line(b,OUTLINE,k.Edge_Cuts)
    for i,(x,y) in enumerate(MOUNTS,1):
        f=k.FootprintLoad('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/MountingHole.pretty','MountingHole_2.2mm_M2')
        f.SetReference('H'+str(base+i));f.SetPosition(xy(x,y));f.SetLocked(True)
        f.SetAttributes(k.FP_EXCLUDE_FROM_BOM|k.FP_EXCLUDE_FROM_POS_FILES)
        f.Reference().SetVisible(False);f.Value().SetVisible(False);b.Add(f)
        # Both-side hardware clearance, not merely a drill-to-copper clearance.
        for layer in(k.F_Cu,k.B_Cu):
            z=k.ZONE(b);z.SetLayer(layer);z.SetIsRuleArea(True)
            z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowCopperPour(True)
            # Central NPTH footprint is intentional. Independently audit all
            # non-mount pads/bodies against this hardware reservation.
            z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False)
            poly=z.Outline();poly.NewOutline()
            for j in range(48):
                q=xy(x+3*math.cos(j*math.tau/48),y+3*math.sin(j*math.tau/48));poly.Append(q.x,q.y)
            b.Add(z)
    label=k.PCB_TEXT(b);label.SetText('UV EVT / 1mm FR4 / 2oz Cu / NOT QUALIFIED')
    label.SetPosition(xy(0,134.4));label.SetTextSize(k.VECTOR2I(k.FromMM(.7),k.FromMM(.7)))
    label.SetTextThickness(k.FromMM(.12));label.SetLayer(k.Dwgs_User);b.Add(label)
    save(b,path)
    rows=[]
    for f in b.GetFootprints():
        rows.append({'reference':f.GetReference(),'xy_mm':dock(f.GetPosition()),'side':'B'if f.GetLayer()==k.B_Cu else'F',
            'angle_deg':f.GetOrientationDegrees(),'pads':[{'number':p.GetNumber(),'xy_mm':dock(p.GetPosition()),'net':p.GetNetname()}for p in f.Pads()]})
    report={'status':'unrouted placement; no fabrication release','board':path.name,'board_sha256':sha(path),
            'schematic_native_xml_sha256':sha(folder/'native.xml'),'parts_sha256':sha(folder/'parts-selection.json'),
            'builder_sha256':sha(Path(__file__)),'outline_dock_planar_mm':OUTLINE,'mount_centers_mm':MOUNTS,
            'hardware_keepout_radius_mm':3,'thickness_mm':1,'target_copper_um':70,'placements':rows,
            'ECAD_to_planar':'x=nativeX-100,y=200-nativeY',
            'StepUp_center_mm':[0,110.5],'base_global_F_plane_Z_mm':13.2,'lid_global_F_plane_Z_mm':55.3,
            'base_rigid_4x4':[[1,0,0,0],[0,1,0,110.5],[0,0,1,13.2],[0,0,0,1]],
            'lid_rigid_4x4':[[-1,0,0,0],[0,1,0,110.5],[0,0,-1,55.3],[0,0,0,1]],
            'note':'LidRy180 is a proper rotation; physicalleft/rightLEDreferences swap. Liner aperture/supports being revised separately.',
            'physical_fit':False,'thermal_validation':False}
    (out/'placement.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'board':str(path),'positions':len(rows),'routing':False}))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['place']);ap.add_argument('side',choices=['base','lid'])
    ap.add_argument('--restart-layout',action='store_true')
    a=ap.parse_args();place(a.side,a.restart_layout)
