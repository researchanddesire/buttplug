"""Compare the placement and mechanical geometry of a wired PCB update."""
from hashlib import sha256
import argparse
import json
from pathlib import Path
import sys


def digest(value):
    return sha256(value).hexdigest()


def mechanical_geometry(sx, board):
    root=sx.parse(board.read_text())

    def value(node):
        if node is None:
            return None
        if isinstance(node, list):
            return [value(item) for item in node]
        return node.value

    locations={}
    drills=[]
    for footprint in sx.children(root,'footprint'):
        ref=sx.prop(footprint,'Reference')
        packages=[]
        for model in sx.children(footprint,'model'):
            path=Path(model[1].value.replace('${KIPRJMOD}',str(board.parent))).resolve()
            packages.append([digest(path.read_bytes()),value(model[2:])])
        location=sx.child(footprint,'at')
        locations[ref]=[sx.value(footprint,'layer'),value(location),packages]
        for pad in sx.children(footprint,'pad'):
            if pad[2].value=='np_thru_hole':
                drills.append([ref,value(location),value(sx.child(pad,'at')),value(sx.child(pad,'drill'))])
    edges=[]
    for kind in ('gr_line','gr_arc','gr_rect','gr_poly','gr_circle','gr_curve'):
        edges.extend(value(item) for item in sx.children(root,kind) if sx.value(item,'layer')=='Edge.Cuts')
    general=sx.child(root,'general')
    return {'footprints':locations,'outline':edges,'npth_drills':sorted(drills),
            'aux_origin':value(sx.child(sx.child(root,'setup'),'aux_axis_origin')),
            'board_thickness':sx.value(general,'thickness')}


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path);parser.add_argument('prior',type=Path);parser.add_argument('current',type=Path);parser.add_argument('report',type=Path)
    args=parser.parse_args()
    sys.path.insert(0,str(args.repo/'tools'))
    import kicad_sexp as sexp
    first=mechanical_geometry(sexp,args.prior);second=mechanical_geometry(sexp,args.current)
    assert first==second,[name for name in first if first[name]!=second[name]]
    result={'prior_board':str(args.prior),'prior_board_sha256':digest(args.prior.read_bytes()),
            'current_board':str(args.current),'current_board_sha256':digest(args.current.read_bytes()),
            'mechanical_geometry_sha256':digest(json.dumps(first,sort_keys=True).encode()),
            'footprints_checked':len(first['footprints']),'models_checked':sum(bool(fp[2]) for fp in first['footprints'].values()),
            'outline_objects_checked':len(first['outline']),'npth_pads_checked':len(first['npth_drills']),
            'aux_origin':first['aux_origin'],'board_thickness':first['board_thickness']}
    args.report.write_text(json.dumps(result,indent=2)+'\n')
