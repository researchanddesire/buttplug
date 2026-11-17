"""Place the selected Hall head packages at the closed-shell review coordinates.

Run using KiCad 10.0.8's bundled Python. Supply the saved routing JSON to replay
routed copper. Placement uses local mm with the Hall at (0, 0), +X is dock +X on
both stations and +Y is toward the original front edge.
"""
import argparse
import json
from pathlib import Path
import uuid
from xml.etree import ElementTree

import pcbnew as k

HERE = Path(__file__).resolve().parent
STEM = 'wired-hall-head'
NAMESPACE = uuid.UUID('15c9a325-7fe9-4254-9495-c0f310f37681')
OUTLINE = [(-3.5, -13.5), (3.5, -13.5), (4.4, -12.0), (4.4, 2.5), (-4.4, 2.5), (-4.4, -12.0)]
LOCATIONS = {
    'U1': (0, 0, 0), 'U2': (2.125, -8.825, 90), 'U3': (-1.925, -9.275, 0),
    'Q1': (-2.535, -5.970, 90), 'J1': (0, -12.250, 0),
    'R1': (-3.2, .100, 90), 'R2': (1.150, -5.000, 90),
    'R3': (3.250, -1.700, 90), 'R4': (-3.200, -3.200, 90),
    'R5': (-.650, -5.750, 90), 'R6': (3.250, -5.000, 90),
    'C1': (2.720, .890, 270), 'C2': (2.650, -12.200, 90),
    'C3': (-2.750, -12.000, 90),
}


def xy(point):
    return k.VECTOR2I(k.FromMM(100 + point[0]), k.FromMM(100 - point[1]))


def assign_uuid(item, key):
    item.SetUuid(k.KIID(str(uuid.uuid5(NAMESPACE, key))))


def place(folder, routes):
    path = folder / (STEM + '.kicad_pcb')
    data = json.loads((folder / 'parts-selection.json').read_text())
    board = k.BOARD()
    board.SetFileName(str(path))
    board.SetCopperLayerCount(2)
    board.GetDesignSettings().SetBoardThickness(k.FromMM(.8))
    parts = data['parts']
    assert set(LOCATIONS) == {row['reference'] for row in parts}
    from_xml = {(node.get('ref'), node.get('pin')): net.get('name')
                for net in ElementTree.parse(folder / 'native.xml').findall('./nets/net') for node in net.findall('node')
                if not node.get('ref').startswith('#')}
    net_names = sorted(set(from_xml.values()))
    nets = {name: k.NETINFO_ITEM(board, name) for name in net_names}
    for net in nets.values():
        board.Add(net)
    project_uuid = str(uuid.uuid5(NAMESPACE, STEM))
    for row in sorted(parts, key=lambda part: part['reference']):
        ref = row['reference']
        library, name = row['footprint'].split(':')
        footprint = k.FootprintLoad(str(folder / (library + '.pretty')), name)
        assert footprint, name
        assign_uuid(footprint, f'footprint/{ref}')
        assign_uuid(footprint.Reference(), f'field/{ref}/Reference')
        assign_uuid(footprint.Value(), f'field/{ref}/Value')
        for index, item in enumerate(footprint.GraphicalItems()):
            assign_uuid(item, f'footprint/{ref}/graphic/{index}')
        for pad in footprint.Pads():
            assign_uuid(pad, f'footprint/{ref}/pad/{pad.GetNumber()}')
        footprint.SetFPID(k.LIB_ID(library, name))
        footprint.SetReference(ref)
        footprint.SetValue(row['value'])
        footprint.SetPath(k.KIID_PATH(f'/{project_uuid}/{uuid.uuid5(NAMESPACE, ref)}'))
        x, y, angle = LOCATIONS[ref]
        footprint.SetOrientationDegrees(angle)
        footprint.SetPosition(xy((x, y)))
        fields = {'DesignStatus': 'CANDIDATE — NOT RELEASED', 'AssemblyDomain': 'MAIN_T',
                  'Manufacturer': row['manufacturer'], 'MPN': row['mpn'],
                  'ReviewNote': row['note'],
                  'Datasheet': row['primary_source'] if ref.startswith(('U', 'Q')) else ''}
        footprint.SetFields(fields)
        for board_field in footprint.GetFields():
            assign_uuid(board_field, f'field/{ref}/{board_field.GetName()}')
            board_field.SetVisible(False)
        footprint.Reference().SetVisible(False)
        footprint.Value().SetVisible(False)
        board.Add(footprint)
        for pad in footprint.Pads():
            name = from_xml[ref, pad.GetNumber()]
            if name:
                pad.SetNet(nets[name])
    for index, (start, end) in enumerate(zip(OUTLINE, OUTLINE[1:] + OUTLINE[:1])):
        edge = k.PCB_SHAPE(board)
        assign_uuid(edge, f'outline/{index}')
        edge.SetShape(k.SHAPE_T_SEGMENT)
        edge.SetStart(xy(start))
        edge.SetEnd(xy(end))
        edge.SetLayer(k.Edge_Cuts)
        edge.SetWidth(k.FromMM(.05))
        board.Add(edge)
    if routes:
        for index, (net, side, width, start, end) in enumerate(routes['segments']):
            track = k.PCB_TRACK(board)
            assign_uuid(track, f'track/{index}')
            track.SetStart(xy(start))
            track.SetEnd(xy(end))
            track.SetWidth(k.FromMM(width))
            track.SetLayer({'F.Cu': k.F_Cu, 'B.Cu': k.B_Cu}[side])
            track.SetNet(nets[net])
            board.Add(track)
        for index, (net, diameter, drill, center) in enumerate(routes['vias']):
            via = k.PCB_VIA(board)
            assign_uuid(via, f'via/{index}')
            via.SetPosition(xy(center))
            via.SetWidth(k.FromMM(diameter))
            via.SetDrill(k.FromMM(drill))
            via.SetLayerPair(k.F_Cu, k.B_Cu)
            via.SetNet(nets[net])
            board.Add(via)
    assert k.SaveBoard(str(path), board)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=HERE)
    parser.add_argument('--routes', type=Path)
    args = parser.parse_args()
    assert k.GetBuildVersion() == '10.0.8'
    place(args.directory, json.loads(args.routes.read_text()) if args.routes else None)
