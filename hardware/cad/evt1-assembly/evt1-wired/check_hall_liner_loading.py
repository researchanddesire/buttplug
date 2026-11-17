"""Measure straight loose Hall wire clearance while seating the product liner."""
from pathlib import Path
from hashlib import sha256
import json
import sys
import FreeCAD as A
import Part
from FreeCAD import Vector as V

base=Path(__file__).resolve().parent
report=Path(sys.argv[1]) if len(sys.argv)>1 else base/'hall-liner-loading-check.json'
vertical_end_z=85.0
wire_radius=.4191
native=base/'DockAssembly.FCStd'
spec=base/'hall-lead-routes.json'
d=A.openDocument(str(native))
data=json.loads(spec.read_text())
out={}
for side,sign in (('Left',-1),('Right',1)):
    crop=Part.makeBox(26,37,30,V(-66 if sign<0 else 42,14,10))
    liner=d.LowerChamber.Shape.common(crop)
    wires=[]
    for row in data[side]:
        curve=Part.BezierCurve()
        points=[V(sign*x,y,z) for x,y,z in row['poles'][0]]
        curve.setPoles(points)
        edge=curve.toShape()
        long_leg=Part.makeLine(points[-1],V(points[-1].x,points[-1].y,vertical_end_z))
        profile=Part.Wire([Part.makeCircle(wire_radius,points[0],V(sign,0,0))])
        solid=Part.Wire([edge,long_leg]).makePipeShell([profile],True,True)
        assert solid.isValid() and len(solid.Solids)==1
        wires.append(solid)
    rows=[]
    for dz in (0,.5,1,2,3,4,5,7,9,12,15,18,22,25,30,36,45,60):
        shifted=liner.copy();shifted.translate(V(0,0,dz))
        lead_checks=[]
        for wire in wires:
            gap=shifted.distToShape(wire)[0]
            vol=shifted.common(wire).Volume if gap<1e-6 else 0
            lead_checks.append({'gap_mm':gap,'overlap_mm3':vol})
        rows.append({'lift_mm':dz,'lead_checks_pin_order':lead_checks})
        print(side,dz,[(round(v['gap_mm'],3),round(v['overlap_mm3'],5)) for v in lead_checks],flush=True)
    assert all(c['overlap_mm3']<1e-7 for row in rows for c in row['lead_checks_pin_order']),side
    out[side]=rows
scope=(
    'Liner vertical motion with pre-mated Main ends and unsoldered, vertical loom ends. '
    'Test only liner-to-leads. Hall station is not installed during this motion. '
    'Body handling, head loading under wire flex, non-Hall assembly interferences '
    'and tolerances remain to demonstrate.'
)
readback={
    'scope':scope,
    'dock_sha256':sha256(native.read_bytes()).hexdigest(),
    'route_poles_sha256':sha256(spec.read_bytes()).hexdigest(),
    'wire_od_mm':2*wire_radius,
    'temporary_vertical_wire_tip_dock_z_mm':vertical_end_z,
    'sides':out,
}
report.write_text(json.dumps(readback,indent=2)+'\n')
