"""Build the six installed Hall lead bodies and check them against the linked dock."""
from hashlib import sha256
from pathlib import Path
import json
import sys
import FreeCAD as App
import Part
from FreeCAD import Vector as V

here=Path(__file__).resolve().parent
native=here/'DockAssembly.FCStd'
route_source=here/'hall-lead-routes.json'
output=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else here
output.mkdir(exist_ok=True,parents=True)
assembly=App.openDocument(str(native))
wire_radius=.4191

def gap(probe,other):
    distance=probe.distToShape(other)[0]
    overlap=probe.common(other) if distance<1e-7 else None
    volume=overlap.Volume if overlap else 0
    touches=[]
    if volume>1e-8:
        for solid in overlap.Solids:
            box=solid.BoundBox
            touches.append([box.XMin,box.YMin,box.ZMin,box.XMax,box.YMax,box.ZMax])
    return [distance,volume,touches]

def bbox_gap(first,second):
    lo=(first.XMin,first.YMin,first.ZMin);hi=(first.XMax,first.YMax,first.ZMax)
    low=(second.XMin,second.YMin,second.ZMin);high=(second.XMax,second.YMax,second.ZMax)
    return sum(max(0.,u-b,a-v)**2 for a,b,u,v in zip(lo,hi,low,high))**.5

def swept_edge(points,sign):
    if isinstance(points[0][0], (int,float)):
        points=[points]
    edges=[]
    for sequence in points:
        curve=Part.BezierCurve()
        curve.setPoles([V(sign*x,y,z) for x,y,z in sequence])
        edges.append(curve.toShape())
    circle=Part.makeCircle(wire_radius,edges[0].Vertexes[0].Point,edges[0].tangentAt(edges[0].FirstParameter))
    swept=Part.Wire(edges).makePipeShell([Part.Wire([circle])],True,True)
    assert swept.isValid() and len(swept.Solids)==1
    radius=1/max(edge.curvatureAt(edge.FirstParameter+(edge.LastParameter-edge.FirstParameter)*i/700) for edge in edges for i in range(701))
    return swept,sum(e.Length for e in edges),radius

raw=json.loads(route_source.read_text())
routes=App.newDocument('HallLeadRoutes')
result={}
for side, rows in raw.items():
    sign=-1 if side=='Left' else 1
    keepout_box=Part.makeBox(25,34,37,V(-66 if sign<0 else 42,13,3))
    lower_liner=assembly.LowerChamber.Shape.common(keepout_box)
    lower_shell=assembly.LowerShell.Shape.common(keepout_box)
    obstacles=[('LowerChamber',lower_liner),('LowerShell',lower_shell)]
    for o in assembly.BaseModule.Group:
        if not hasattr(o,'Shape') or o.Shape.isNull() or o.Name in {'LowerChamber','LowerChamberInstance','LowerShell','USBBoardAssembly','BaseModule'}:
            continue
        if bbox_gap(o.Shape.BoundBox,keepout_box.BoundBox)<.2: obstacles.append((o.Name,o.Shape))
    for name in (side+'Bracket',side+'HallPCBInstance','UpperChamber'):
        o=assembly.getObject(name)
        q=o.Shape.common(keepout_box)
        if not q.isNull() and q.Solids:
            obstacles.append((name,q))
    main=assembly.USBBoardAssembly
    for o in main.LinkedObject.Document.Objects:
        if o.TypeId!='Part::Feature' or not hasattr(o,'Shape') or o.Shape.isNull() or o.Label.startswith(('J601_','J602_')):
            continue
        shape=o.Shape.copy()
        shape.Placement=main.LinkPlacement*shape.Placement
        if bbox_gap(shape.BoundBox,keepout_box.BoundBox)<.2: obstacles.append((o.Label,shape))
    wires=[]
    bundle=routes.addObject('App::Part',side+'HallLeadBundle')
    ref='J630' if side=='Left' else 'J650'
    bundle.Label=f'{side} Hall leads · {ref} to J1'
    for row in rows:
        solid,length,radius=swept_edge(row['poles'],sign)
        gaps={}
        for name,obstruction in obstacles:
            if bbox_gap(solid.BoundBox,obstruction.BoundBox)>.5:continue
            gaps[name]=gap(solid,obstruction)
        assert radius>=4 and all(record[1]<1e-7 for record in gaps.values()),(side,row['pins'],gaps)
        body=bundle.newObject('PartDesign::Body',side+'HallLead'+str(row['pins']))
        function=('Feed','Signal','Return')[row['pins']-1]
        body.Label=f'{ref}.{row["pins"]} · {function}'
        feature=body.newObject('PartDesign::Feature','InsulationEnvelope')
        feature.Shape=solid
        wires.append(solid)
        row.update(exact_solid_length_mm=length,minimum_sampled_centerline_radius_mm=radius,checked_solid_gaps={k:v for k,v in sorted(gaps.items(),key=lambda item:item[1][0])})
        print(side,row['pins'],'length/R/gaps',length,radius,list(row['checked_solid_gaps'].items())[:4],flush=True)
    pairs=[{'pins':(i+1,j+1),'gap_and_volume':gap(wires[i],wires[j])} for i,j in ((0,1),(1,2),(0,2))]
    assert all(p['gap_and_volume'][0]>0 and p['gap_and_volume'][1]<1e-7 for p in pairs),(side,pairs)
    print(side,pairs,flush=True)
    result[side]={'leads':rows,'pair_checks':pairs,'obstacle_count':len(obstacles)}
native_output=output/'HallLeadRoutes.FCStd'
routes.recompute()
routes.saveAs(str(native_output))
App.closeDocument(routes.Name)
cold=App.openDocument(str(native_output))
bodies=[o for o in cold.Objects if o.TypeId=='PartDesign::Body']
assert len(bodies)==6 and all(o.Shape.isValid() and len(o.Shape.Solids)==1 for o in bodies)
receipt={
    'scope':'Static insulation envelopes against saved rigid dock, brackets, Hall heads and donor Main. Tangency at the Hall lands is intentional. Full updated Main components, solder, insulation strain relief, tolerance, installation motion and physical fit are outside this check.',
    'source_sha256':{p.name:sha256(p.read_bytes()).hexdigest() for p in (native,route_source,here/'hall-main-connector-fit.json',here/'pcb/MainPCB-Wired.FCStd',here/'pcb/WiredHallHead.FCStd') if p.is_file()},
    'native_output_sha256':sha256(native_output.read_bytes()).hexdigest(),
    'cold_native_body_count':len(bodies),
    'insulation_od_mm':.8382,
    'radius_design_target_mm':4,
    'check_format':['gap_mm','overlap_mm3','overlap_bbox_xyz_mm'],
    'sides':result,
}
(output/'hall-lead-route-check.json').write_text(json.dumps(receipt,indent=2)+'\n')
