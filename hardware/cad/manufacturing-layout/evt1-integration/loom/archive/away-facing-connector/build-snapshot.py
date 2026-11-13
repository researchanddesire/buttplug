"""Native wire forms from actual EVT product/PCB sources; FreeCAD Python.

True circular sweeps and independent saved checks supplement the WireViz
pin map. No flexible assembly, received-wire/crimp or physical fit proof.
"""
from pathlib import Path
import hashlib
import json
import sys
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
import MeshPart
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakePipeShell
from OCC.Core.TopoDS import topods
from evt1_loom_paths import interboard
ROOT=Path(__file__).resolve().parents[1]
PRODUCT=ROOT/'hardware/cad/manufacturing-layout/evt1-integration'
OUT=PRODUCT/'loom';OUT.mkdir(exist_ok=True)
PCB=ROOT/'hardware/pcb/evt1';CABLE=ROOT/'hardware/cables/evt1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((PRODUCT/'review.json').read_text());assert sha(PRODUCT/'EVT1Product.FCStd')==r['native_sha256']
data={d:json.loads((PCB/d/'mcad.json').read_text()) for d in ('body','flange','sensor')}
for d,v in data.items():assert sha(ROOT/v['board_file'])==v['board_sha256']
S=A.openDocument(str(PRODUCT/'EVT1Product.FCStd'));D=A.newDocument('EVT1Loom');D.Label='EVT1 wire forms / actual-board integration'
groups={n:D.addObject('App::DocumentObjectGroup',n) for n in ('Wires','Centerlines','SourceAssembly','Construction')}
def feat(name,shape,group):
    o=D.addObject('PartDesign::Feature',name);o.Shape=shape;groups[group].addObject(o);return o
def vector(p):return A.Vector(*[float(x) for x in p])
def edge(spec):
    pts=[vector(v) for v in spec['points']]
    if spec['kind']=='line':return Part.makeLine(*pts)
    if spec['kind']=='arc':return Part.Arc(*pts).toShape()
    if spec['kind']=='bezier':
        c=Part.BezierCurve();c.setPoles(pts);return c.toShape()
    # Preserve the natural interpolation handle lengths. FreeCAD's endpoint
    # tangent constraint rescaling introduced tight local hooks near arc ends.
    # Align only the two end handles to join the neighbouring sections.
    c=Part.BSplineCurve();c.interpolate(pts)
    first=vector(spec['first_tangent']);first.normalize()
    last=vector(spec['last_tangent']);last.normalize()
    c.setPole(2,pts[0]+first*(c.getPole(2)-pts[0]).Length)
    c.setPole(c.NbPoles-1,pts[-1]-last*(c.getPole(c.NbPoles-1)-pts[-1]).Length)
    return c.toShape()
plan=interboard(r,data['body'],data['flange'])
exports={};rows=[]
for item in plan:
    print('Building',item['name'],flush=True)
    path=Part.Wire([edge(v) for v in item['sections']])
    assert path.isValid(),item['name']
    start=path.Edges[0].valueAt(path.Edges[0].FirstParameter);tangent=path.Edges[0].tangentAt(path.Edges[0].FirstParameter)
    circle=Part.Wire([Part.makeCircle(item['OD_mm']/2,start,tangent)])
    # Tighten the actual sweep solver's tolerances rather than fitting away
    # section boundaries. Default pipe settings gave valid-looking solids
    # whose tessellation had open seams. Keep the original checked centreline.
    pipe=BRepOffsetAPI_MakePipeShell(topods.Wire(Part.__toPythonOCC__(path)))
    pipe.SetMode(False);pipe.SetTolerance(1e-6,1e-6,1e-6)
    pipe.SetMaxDegree(12);pipe.SetMaxSegments(500);pipe.SetForceApproxC1(True)
    pipe.Add(topods.Wire(Part.__toPythonOCC__(circle)),False,False)
    pipe.Build();assert pipe.IsDone() and pipe.MakeSolid(),item['name']
    shape=Part.__fromPythonOCC__(pipe.Shape())
    assert shape.isValid() and len(shape.Solids)==1,(item['name'],'Sweep failed')
    obj=feat(item['name'],shape,'Wires');center=feat(item['name']+'Centerline',path,'Centerlines')
    for key,value in (('Net',item['net']),('WirePart',item['wire']),('Start',str(item['start'])),('End',str(item['end']))):
        obj.addProperty('App::PropertyString',key,'Harness');setattr(obj,key,value)
    obj.addProperty('App::PropertyLength','WireOD','Harness');obj.WireOD=item['OD_mm']
    step=OUT/(obj.Name+'.step');obj.Shape.exportStep(str(step))
    view=OUT/(obj.Name+'-view.stl');mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.015,AngularDeflection=.1,Relative=False);assert mesh.isSolid(),item['name'];mesh.write(str(view))
    exports[obj.Name]={'STEP_sha256':sha(step),'view_STL_sha256':sha(view),'centerline_role':center.Name}
    rows.append({**item,'insulated_path_length_mm':path.Length,'centerline_role':center.Name,'solid_role':obj.Name})
# The source parts are copied as immutable geometric context, never boolean
# obstacles altered to make a wire pass. Hand-solder allowances are labeled
# separately by the independent checker.
copied=[]
for group in ('ProductParts','Electronics','Contacts','SoftGoods','References','MatingAllowances'):
    for source in S.getObject(group).Group:
        if not hasattr(source,'Shape') or source.Shape.isNull():continue
        feat('Source_'+source.Name,source.Shape.copy(),'SourceAssembly');copied.append(source.Name)
D.recompute();native=OUT/'EVT1Loom.FCStd';D.saveAs(str(native))
report={'scope':'Nominal EVT interboard wire-form integration; other looms and physical/crimp/assembly qualification pending',
    'native_sha256':sha(native),'builder_sha256':sha(Path(__file__)),'path_builder_sha256':sha(ROOT/'tools/evt1_loom_paths.py'),
    'source_product_native_sha256':r['native_sha256'],'source_product_review_sha256':sha(PRODUCT/'review.json'),
    'source_mcad_sha256':{d:sha(PCB/d/'mcad.json') for d in data},'exports':exports,'wires':rows,
    'source_context_roles':copied,'wire_specs':{'AG100690':{'manufacturer':'Accu-Glass','mpn':'100690','AWG':28,'catalogue_OD_mm':.508,'incoming_max_OD_mm':.6,'design_centerline_radius_mm':4,'source':'https://www.accuglassproducts.com/sites/default/files/catalog/kapton_insulated_uhv_wire.pdf'}},
    'termination_datum_scope':'SH wire centers1.4mm from board mount face are fixture targets, not controlled OEM exit dimensions. Mated envelopes use catalogue assembly dimensions; received first article must reconcile free length and egress.',
    'sweep_tolerances':{'3d_mm':1e-6,'boundary_mm':1e-6,'angular_rad':1e-6,'max_degree':12,'max_segments':500,'force_approx_C1':True},
    'curve_endpoint_handles':'Natural interpolation handle lengths retained; end handle directions aligned to the declared adjacent tangent. Saved native curve is authoritative and independently checked.',
    'physical_validation':False,'full_product_order_ready':False}
(OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n')
(CABLE/'routing-plan.json').write_text(json.dumps({'source_product_native_sha256':r['native_sha256'],'path_builder_sha256':report['path_builder_sha256'],'wires':rows},indent=2)+'\n')
print(json.dumps({'native':str(native),'wire_forms':len(rows),'path_lengths_mm':{v['name']:round(v['insulated_path_length_mm'],3) for v in rows}}),flush=True)
