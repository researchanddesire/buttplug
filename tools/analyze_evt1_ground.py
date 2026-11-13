"""Diagnose disconnected GND copper components from the saved native board.

Requires Shapely; exact native pad contours are supplied by the KiCad export.
This is a diagnostic to locate repairs, not native DRC acceptance evidence.
"""
from pathlib import Path
import argparse
import json
import math
from shapely.geometry import Point, Polygon, LineString
from shapely import make_valid
from shapely.strtree import STRtree
from shapely.ops import nearest_points
import kicad_sexp as s

ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser();ap.add_argument('domain',choices=('body','flange'));a=ap.parse_args()
    folder=ROOT/'hardware/pcb/evt1'/a.domain
    b=s.parse((folder/(a.domain+'-evt1.kicad_pcb')).read_text())
    nodes=[]
    def add(layer,shape,label):
        if shape.is_empty:return
        nodes.append({'layer':layer,'shape':make_valid(shape).buffer(.000002),'label':label})
    xy=lambda item:[float(v.value) for v in item[1:3]]
    mech=lambda q:(q[0]-100,130-q[1])
    layers=[v[1].value for v in s.child(b,'layers')[1:] if isinstance(v,list) and int(v[0].value)<32]
    nets={n[1].value:n[2].value for n in s.children(b,'net')}
    via_groups=[]
    for j,z in enumerate(s.children(b,'zone')):
        if s.value(z,'net_name')!='GND' or s.child(z,'keepout'):continue
        for i,p in enumerate(s.children(z,'filled_polygon')):
            pts=[mech(xy(q)) for q in s.children(s.child(p,'pts'),'xy')]
            add(s.value(p,'layer'),Polygon(pts),f'zone{j}/poly{i}')
    for t in s.children(b,'segment'):
        if nets[s.value(t,'net')]!='GND':continue
        add(s.value(t,'layer'),LineString([mech(xy(s.child(t,'start'))),mech(xy(s.child(t,'end')))]).buffer(float(s.value(t,'width'))/2),s.value(t,'tstamp'))
    for t in s.children(b,'via'):
        if nets[s.value(t,'net')]!='GND':continue
        indexes=[]
        for ly in layers:
            indexes.append(len(nodes));add(ly,Point(mech(xy(s.child(t,'at')))).buffer(float(s.value(t,'size'))/2,quad_segs=32),'via/'+s.value(t,'tstamp'))
        via_groups.append(indexes)
    for p in json.loads(Path('/private/tmp/compass-evt1/ground-'+a.domain+'-pads.json').read_text()):
        indexes=[]
        for ly in p['layers']:
            for pts in p['polygons']:
                indexes.append(len(nodes));add(ly,Polygon(pts),p['ref']+'/'+p['number'])
        if len(p['layers'])>1:via_groups.append(indexes)
    parent=list(range(len(nodes)))
    def root(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def union(i,j):parent[root(i)]=root(j)
    for g in via_groups:
        for i in g[1:]:union(g[0],i)
    for ly in layers:
        ids=[i for i,n in enumerate(nodes) if n['layer']==ly];shapes=[nodes[i]['shape'] for i in ids];tree=STRtree(shapes)
        for j,shape in enumerate(shapes):
            for k in tree.query(shape,predicate='intersects'):union(ids[j],ids[int(k)])
    groups={}
    for i,n in enumerate(nodes):groups.setdefault(root(i),[]).append(i)
    groups=sorted(groups.values(),key=len,reverse=True)
    print('GND components',len(groups),[len(g) for g in groups])
    details=[]
    for g in groups[1:]:
        labels=[nodes[i]['label']+' '+nodes[i]['layer'] for i in g]
        print('ISOLATED',labels)
        best=None
        for i in g:
            for j in groups[0]:
                if nodes[i]['layer']!=nodes[j]['layer']:continue
                x,y=nearest_points(nodes[i]['shape'],nodes[j]['shape']);d=x.distance(y)
                if best is None or d<best['distance_mm']:
                    best={'layer':nodes[i]['layer'],'distance_mm':d,'from_xy_mm':list(x.coords[0]),'to_xy_mm':list(y.coords[0]),'from':nodes[i]['label'],'to':nodes[j]['label']}
        details.append({'nodes':labels,'closest_main_component':best})
        print('NEAREST',best)
    Path('/private/tmp/compass-evt1/ground-'+a.domain+'-components.json').write_text(json.dumps(details,indent=2)+'\n')


if __name__=='__main__':main()
