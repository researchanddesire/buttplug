import sys,json,ast,itertools,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[6]
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib');sys.path.insert(0,str(ROOT/'tools'))
import FreeCAD as A,Part
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakePipeShell
from OCC.Core.TopoDS import topods
from evt1_loom_paths import interboard
root=ROOT
snapshot=json.loads(Path(__file__).with_name('source-snapshot.json').read_text())
import hashlib
for file,digest in snapshot['files'].items():assert hashlib.sha256((root/file).read_bytes()).hexdigest()==digest,('Preflight source changed',file)
base=root/'hardware/cad/manufacturing-layout/evt1-integration'
r=json.loads((base/'review.json').read_text());data={n:json.loads((root/'hardware/pcb/evt1'/n/'mcad.json').read_text()) for n in ('body','flange')}
c=json.loads(Path(__file__).with_name('placement-proposal.json').read_text());assert not c['courtyard_intersections']
assert hashlib.sha256(Path(__file__).with_name('placement-proposal.json').read_bytes()).hexdigest()==snapshot['placement_proposal_sha256']
s=A.openDocument(str(base/'EVT1Product.FCStd'));d=A.newDocument('NeckFacingJ7Preflight')
def bounds(shape):
    b=shape.BoundBox;return [getattr(b,n) for n in ('XMin','YMin','ZMin','XMax','YMax','ZMax')]
def box(rect,height):
    x,y,a,b=rect
    return Part.makeBox(a-x,height,b-y,A.Vector(x+1.5,-18.3125,y+17.5125))
new={}
for ref,v in c['poses'].items():
    item=next(q for q in data['flange']['components'] if q['ref']==ref);item.update({'fab_bounds_xy_mm':v['fab'],'angle_deg':v['angle'],'xy_mm':v['origin']})
    new['Flange_'+ref]=box(v['fab'],item['height_budget_mm'])
new['Flange_J7_Mate']=box(c['poses']['J7']['mate_xy'],3.2)
outline=c['outline_xy_mm'];points=[A.Vector(x+1.5,-18.3125,y+17.5125) for x,y in outline]
board=Part.Face(Part.makePolygon(points+points[:1])).extrude(A.Vector(0,-1,0))
for hole in data['flange']['holes']:
    x,y=hole['xy_mm'];dx,dy=hole['drill_xy_mm'];assert abs(dx-dy)<1e-8
    board=board.cut(Part.makeCylinder(dx/2,1.2,A.Vector(x+1.5,-18.2,y+17.5125),A.Vector(0,-1,0)))
assert board.isValid() and len(board.Solids)==1;new['FlangePCB']=board
r['bounds']['Flange_J7_Mate']=bounds(new['Flange_J7_Mate'])
data['flange']['pads']=[v for v in data['flange']['pads'] if v['ref']!='J7']+[{'ref':'J7',**v} for v in c['poses']['J7']['pads']]
context={}
for group in ('ProductParts','Electronics','Contacts','SoftGoods','References','MatingAllowances'):
    for o in s.getObject(group).Group:
        if hasattr(o,'Shape') and not o.Shape.isNull():context[o.Name]=new.get(o.Name,o.Shape.copy())
tree=ast.parse((root/'tools/build_evt1_loom_cad.py').read_text());nodes=[v for v in tree.body if isinstance(v,ast.FunctionDef) and v.name in ('vector','edge')]
exec(compile(ast.Module(body=nodes,type_ignores=[]),'CAD constructor functions','exec'))
wires={};findings=[];measurements={}
for item in interboard(r,data['body'],data['flange']):
    name=item['name'];path=Part.Wire([edge(v) for v in item['sections']]);p=path.Edges[0].valueAt(path.Edges[0].FirstParameter);t=path.Edges[0].tangentAt(path.Edges[0].FirstParameter)
    circle=Part.Wire([Part.makeCircle(.3,p,t)]);pipe=BRepOffsetAPI_MakePipeShell(topods.Wire(Part.__toPythonOCC__(path)))
    pipe.SetMode(False);pipe.SetTolerance(1e-6,1e-6,1e-6);pipe.SetMaxDegree(12);pipe.SetMaxSegments(500);pipe.SetForceApproxC1(True)
    pipe.Add(topods.Wire(Part.__toPythonOCC__(circle)),False,False);pipe.Build();assert pipe.IsDone() and pipe.MakeSolid()
    shape=Part.__fromPythonOCC__(pipe.Shape());assert shape.isValid() and len(shape.Solids)==1
    maximum=0
    for e in path.Edges:
        knots=e.Curve.getKnots() if hasattr(e.Curve,'getKnots') else [e.FirstParameter,e.LastParameter]
        cuts=sorted(set([e.FirstParameter,e.LastParameter]+[v for v in knots if e.FirstParameter<=v<=e.LastParameter]))
        for lo,hi in zip(cuts,cuts[1:]):
            for j in range(13):maximum=max(maximum,abs(e.curvatureAt(lo+(hi-lo)*j/12)))
    radius=1/maximum;assert radius>=3.999,(name,radius)
    wires[name]=shape;measurements[name]={'length_mm':path.Length,'minimum_sampled_radius_mm':radius}
    o=d.addObject('PartDesign::Feature',name);o.Shape=shape;o=d.addObject('PartDesign::Feature',name+'Centerline');o.Shape=path
    print(name,'R',radius,'L',path.Length,flush=True)
def overlap(a,b):
    x,y=a.BoundBox,b.BoundBox
    if any(min(getattr(x,c+'Max'),getattr(y,c+'Max'))<=max(getattr(x,c+'Min'),getattr(y,c+'Min'))+1e-7 for c in 'XYZ'):return 0
    shape=a.common(b);assert shape.isValid(),'Invalid collision Boolean';return shape.Volume
component_pairs=0
for name,shape in new.items():
    for ref,other in context.items():
        if ref==name:continue
        volume=overlap(shape,other);component_pairs+=1
        if volume>1e-4:findings.append({'candidate_component':name,'part':ref,'collision_mm3':volume})
for name,shape in wires.items():
    for ref,other in context.items():
        if ref in ('Body_J81','Sensor_J82','Flange_J1'):continue
        volume=overlap(shape,other)
        if volume>1e-5:findings.append({'wire':name,'part':ref,'collision_mm3':volume})
minimum=999
for a,b in itertools.combinations(wires,2):
    distance=wires[a].distToShape(wires[b])[0];minimum=min(minimum,distance)
    if distance<.005:findings.append({'wires':[a,b],'distance_mm':distance})
for name,shape in context.items():
    o=d.addObject('PartDesign::Feature','Source_'+name);o.Shape=shape
d.recompute();d.saveAs(str(Path(__file__).with_name('NeckFacingJ7Preflight.FCStd')))
nearby_gaps={ref:min(w.distToShape(context[ref])[0] for w in wires.values()) for ref in ('Flange_D73','Flange_J7_Mate','RearNutReference')}
result={'scope':'Temporary geometry preflight before rerouting the PCB; source native board remains unchanged','pass':not findings,'findings':findings,'wires':measurements,'candidate_component_pair_checks':component_pairs,'minimum_wire_surface_gap_mm':minimum,'minimum_wire_to_nearby_part_gaps_mm':nearby_gaps,'source_snapshot_sha256':hashlib.sha256(Path(__file__).with_name('source-snapshot.json').read_bytes()).hexdigest(),'preflight_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'native_sha256':hashlib.sha256(Path(__file__).with_name('NeckFacingJ7Preflight.FCStd').read_bytes()).hexdigest(),'physical_validation':False}
Path(__file__).with_name('geometry-preflight.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
