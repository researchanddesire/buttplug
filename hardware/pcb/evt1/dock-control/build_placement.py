"""Place the controller subset on the shared base and the separate lid UI.

Run ONE domain per KiCad7 Python process. This is an unrouted placement source;
source-power and safety parts must be merged into the same base PCB. Never
fabricate these incomplete candidates. No existing routed device board is read
or replaced. The LCD socket's physical mating height/depth remains unqualified.
"""
from pathlib import Path
import argparse, hashlib, json, sys, xml.etree.ElementTree as ET
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3] / 'tools'))
import wx
APP = wx.App(False)
import pcbnew as k
import kicad_sexp as s

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def xy(x, y):
    return k.VECTOR2I(k.FromMM(100 + x), k.FromMM(200 - y))
def dock(p):
    return [round(k.ToMM(p.x)-100, 6), round(200-k.ToMM(p.y), 6)]

CONTROLLER = {
    'U201':(-29,43,0), 'U202':(-9,42,0), 'J201':(0,63,180),
    'J202':(-32,29,0), 'TP201':(-40,33,0), 'D201':(-43,53,0),
    'C201':(-35,49,0), 'C202':(-35,37,0), 'C203':(-23,37,0),
    'C204':(-23,49,0), 'C205':(-36,43,90), 'C206':(-40,43,90),
    'C207':(-38,38,0), 'C208':(-20,30,0), 'C209':(-16,30,0),
    'C210':(-9,47,0), 'C211':(-19,53,0), 'C212':(-15,53,0),
    'R213':(-39,30,90), 'R214':(-43,59,0), 'R215':(7,57,90),
    'R216':(-16,46,90), 'R217':(-16,42,90),
    'R218':(-10,34,90), 'R219':(-5,34,90),
    'R220':(-20,34,90), 'R221':(-16,34,90),
    'R222':(1,43,90), 'R223':(1,39,90), 'R224':(-43,49,90),
    'R225':(-19,50,90), 'R226':(-15,50,90),
}
CONTROLLER.update({'R'+str(201+i):(-37+3*i,57,90) for i in range(12)})
LID = {
    'S301':(-22,54,0), 'S302':(0,54,0), 'S303':(22,54,0),
    # This is a 2D candidate pad-row position, NOT the FFC tip or a solved mate.
    'J302':(0,114,0), 'J301':(25,113,180),
    'C301':(-14,108,0), 'C302':(-18,108,0), 'C303':(-22,108,0),
    'C304':(-26,108,0), 'C305':(-30,108,0),
    'C306':(-15,102,90), 'C307':(-21,102,90),
    'C308':(-27,102,90), 'C309':(-32,102,90),
    'C310':(15,106,0), 'C311':(18,106,0),
    'R301':(15,100,90), 'R302':(19,100,90),
    'R303':(23,100,90), 'R304':(27,100,90),
}
LID.update({'R'+str(305+i):(15+4*(i%4),94-4*(i//4),90) for i in range(8)})
OUTLINES = {
    'controller':[(-5.5,-4),(5.5,-4),(5.5,2),(25,2),(47.5,15),
                  (48,25),(48,65),(45,68),(-45,68),(-48,65),
                  (-48,15),(-25,2),(-5.5,2)],
    'lid':[(-33,49),(33,49),(36,52),(36,117),(33,120),
           (-33,120),(-36,117),(-36,52)],
}

def lines(board, points, layer=k.Edge_Cuts, width=.05):
    for a,b in zip(points,points[1:]+points[:1]):
        line=k.PCB_SHAPE(board);line.SetShape(k.SHAPE_T_SEGMENT)
        line.SetStart(xy(*a));line.SetEnd(xy(*b));line.SetWidth(k.FromMM(width))
        line.SetLayer(layer);board.Add(line)

def label(board, text, point, size=1):
    item=k.PCB_TEXT(board);item.SetText(text);item.SetPosition(xy(*point))
    item.SetTextSize(k.VECTOR2I(k.FromMM(size),k.FromMM(size)))
    item.SetTextThickness(k.FromMM(.15));item.SetLayer(k.Dwgs_User);board.Add(item)

def region(board, name, box):
    x1,y1,x2,y2=box
    # Keepout is native and blocks components/copper in later placement/routing.
    zone=k.ZONE(board);zone.SetLayer(k.F_Cu);zone.SetIsRuleArea(True)
    zone.SetDoNotAllowTracks(True);zone.SetDoNotAllowVias(True)
    zone.SetDoNotAllowCopperPour(True);zone.SetDoNotAllowPads(True)
    zone.SetDoNotAllowFootprints(True)
    poly=zone.Outline();poly.NewOutline()
    for x,y in ((x1,y1),(x2,y1),(x2,y2),(x1,y2)):
        p=xy(x,y);poly.Append(p.x,p.y)
    board.Add(zone)
    label(board,name,((x1+x2)/2,(y1+y2)/2),.85)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('domain',choices=['controller','lid'])
    ap.add_argument('--restart-placement',action='store_true',help='Replace only this builder\'s unchanged, unrouted candidate')
    args=ap.parse_args();domain=args.domain
    path=HERE/('dock-'+domain+'-placement.kicad_pcb')
    if path.exists():
        previous=json.loads((HERE/('dock-'+domain+'-placement.json')).read_text())
        assert args.restart_placement and sha(path)==previous['native_board_sha256'] and not previous['routing_present'], 'Preserve edited/routed layout first; only unchanged placement candidates may be restarted'
    manifest=json.loads((HERE/'circuit-parts.json').read_text())
    check=json.loads((HERE/'native-checks.json').read_text())
    for rel,digest in check['source_sha256'].items():
        assert sha(HERE/rel)==digest,('Stale schematic check',rel)
    native=HERE/('dock-'+('lid-ui' if domain=='lid' else 'controller')+'-native.xml')
    xml=ET.parse(native).getroot();netmap={}
    board=k.BOARD();board.SetFileName(str(path));board.SetCopperLayerCount(2)
    settings=board.GetDesignSettings();settings.SetBoardThickness(k.FromMM(1))
    settings.m_MinClearance=k.FromMM(.2);settings.m_TrackMinWidth=k.FromMM(.15)
    settings.m_HoleClearance=k.FromMM(.2);settings.m_CopperEdgeClearance=k.FromMM(.3)
    settings.m_MinThroughDrill=k.FromMM(.3);settings.m_ViasMinSize=k.FromMM(.6)
    default=settings.m_NetSettings.m_DefaultNetClass
    default.SetClearance(k.FromMM(.2));default.SetTrackWidth(k.FromMM(.2))
    default.SetViaDiameter(k.FromMM(.6));default.SetViaDrill(k.FromMM(.3))
    board.GetDesignSettings().SetAuxOrigin(xy(0,0))
    for net in xml.findall('./nets/net'):
        name=net.get('name');board.Add(k.NETINFO_ITEM(board,name))
        for node in net.findall('node'):netmap[(node.get('ref'),node.get('pin'))]=name
    positions=CONTROLLER if domain=='controller' else LID
    instances={p['ref']:p for p in manifest['generated_pin_manifest']}
    placed=[]
    for c in xml.findall('./components/comp'):
        ref=c.get('ref');library=c.findtext('footprint')
        if not library:continue  # offboard LCD and intersheet-only annotations
        assert ref in positions,ref
        pos=positions[ref]
        name=library.split(':')[1];fp=k.FootprintLoad(str(HERE/'DockControl.pretty'),name)
        assert fp,library
        fp.SetFPID(k.LIB_ID('DockControl',name))
        fp.SetReference(ref);fp.SetValue(c.findtext('value'));fp.SetPosition(xy(*pos[:2]))
        fp.SetOrientationDegrees(pos[2]);fp.SetLocked(True)
        fp.SetPath(k.KIID_PATH(c.find('sheetpath').get('tstamps')+c.findtext('tstamps')))
        fp.Reference().SetVisible(False);fp.Value().SetVisible(False)
        for pad in fp.Pads():
            number=pad.GetNumber()
            if not number:continue
            assert number in instances[ref]['pins'],(ref,number)
            net=netmap.get((ref,number))
            if net:pad.SetNet(board.FindNet(net))
        board.Add(fp);placed.append(ref)
    assert set(placed)==set(positions),(set(positions)-set(placed))
    lines(board,OUTLINES[domain]);holes=[]
    if domain=='controller':
        for x,y in ((-43,19),(-15,19)):
            # Full7x7 carrier foot clearance inside8x8 opening; milling still DFM-open.
            pts=[(x-3.5,y-4),(x+3.5,y-4),(x+4,y-3.5),(x+4,y+3.5),
                 (x+3.5,y+4),(x-3.5,y+4),(x-4,y+3.5),(x-4,y-3.5)]
            lines(board,pts);holes.append(pts)
        # Reserved domains are graphics, not keepouts: sibling parts must occupy them.
        lines(board,[(-40,2),(40,2),(40,25),(-40,25)],k.Dwgs_User,.15)
        label(board,'RESERVED SOURCE / USB / NOT POPULATED', (0,10),1)
        lines(board,[(15,30),(45,30),(45,60),(15,60)],k.Dwgs_User,.15)
        label(board,'RESERVED SAFETY / NOT POPULATED',(30,45),.9)
    else:
        region(board,'LCD FFC RETURN / NO COMPONENTS',(-8,60,8,108.5))
        label(board,'J302 HEIGHT/DEPTH MATE OPEN',(0,84),.85)
    label(board,'EVT PLACEMENT ONLY / UNROUTED / NOT FABRICATION',
          (0,26) if domain=='controller' else (0,64),.9)
    k.SaveBoard(str(path),board)
    # Readback must happen in a separate process; do not load another live board.
    xs=[p[0]for p in OUTLINES[domain]];ys=[p[1]for p in OUTLINES[domain]]
    cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2
    top=6.4 if domain=='controller' else None
    report={
        'scope':'Controller subset on shared source/controller/safety base'if domain=='controller'else'Separate lid UI placement candidate',
        'status':'Unrouted; no physical fit or fabrication release',
        'native_board':path.name,'native_board_sha256':sha(path),
        'native_schematic_xml':native.name,'native_schematic_xml_sha256':sha(native),
        'builder_sha256':sha(Path(__file__)),
        'outline_dock_xy_mm':OUTLINES[domain],'cutouts_dock_xy_mm':holes,
        'thickness_mm':1,'F_Cu_global_Z_mm':top,
        'pcbnew_native_to_dock_xy':'dockX=nativeX-100; dockY=200-nativeY',
        'StepUp_import':{'pcb_placement':2,'F_Cu_local_Z_mm':0,'B_Cu_local_Z_mm':-1,
            'local_to_dock_4x4':[[1,0,0,cx],[0,1,0,cy],[0,0,1,top],[0,0,0,1]],
            'note':'StepUp centres outline bounds and reflects native down-pageY. Identity App::Placement rotation; lid Z translation must be solved from actual socket contact plane. No reflected FreeCAD placement.'},
        'footprint_placements_dock_xy_and_native_angle':positions,
        'socket_directions':{
            ('J201'if domain=='controller'else'J301'):{'native_footprint_angle_deg':180,'dock_mouth_vector':[0,1,0],'dock_pin1_side':'+X','cable_conductor_mapping':'p to p; TypeD opposite-face20way; physical routing/continuity open'},
            **({'J302':{'native_footprint_angle_deg':0,'dock_mouth_vector':[0,-1,0],'dock_pin1_side':'-X','electrical_mapping':'LCD p to socket p','padrow_position_is_not_FFC_tip':True,'FFC_tip_global_center_mm':[0,112.575222039,61.85],'FFC_contact_face_global_Z_mm':61.70,'FFC_contact_normal':[0,0,-1],'socket_mating_Z_mm':None,'insertion_depth_qualified':False}} if domain=='lid'else{})},
        'reserved_regions':{'source_Y_mm':[0,25],'safety_XY_mm':[15,30,45,60]}if domain=='controller'else{'FFC_return_XY_mm':[-8,60,8,108.5],'FFC_socket_transition':'Keepout stops before J302 courtyard; actual flex/socket mate remains open'},
        'mounting_boss_keepouts_dock_xy_R_mm':[[-52,60,3],[52,60,3],[-52,115,3],[52,115,3]],
        'routing_present':False,'full_product_order_ready':False,
    }
    (HERE/('dock-'+domain+'-placement.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'board':path.name,'placed_references':len(placed),'tracks':len(list(board.GetTracks())),'full_product_order_ready':False}))

if __name__=='__main__':main()
