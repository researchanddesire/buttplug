"""Native, circular-profile wire primitives for the isolated loom coupon."""
import sys, math
sys.path.insert(0, '/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakePipeShell
from OCC.Core.TopoDS import topods
V = A.Vector

def edge(s):
    p = [V(*x) for x in s['points']]
    if s['kind'] == 'line': return Part.makeLine(*p)
    if s['kind'] == 'arc': return Part.Arc(*p).toShape()
    if s['kind'] == 'bezier':
        c = Part.BezierCurve(); c.setPoles(p); return c.toShape()
    c = Part.BSplineCurve(); c.interpolate(p)
    first = V(*s['first_tangent']); last = V(*s['last_tangent'])
    first.normalize(); last.normalize()
    c.setPole(2, p[0] + first * (c.getPole(2)-p[0]).Length)
    c.setPole(c.NbPoles-1, p[-1] - last * (c.getPole(c.NbPoles-1)-p[-1]).Length)
    return c.toShape()

def path(sections): return Part.Wire([edge(s) for s in sections])

def edge_segment(e, start, end):
    if isinstance(e.Curve, Part.Line):
        a=e.valueAt(e.FirstParameter); d=e.tangentAt(e.FirstParameter)
        return Part.makeLine(a+d*start,a+d*end)
    assert isinstance(e.Curve, Part.Circle)
    return Part.Edge(e.Curve,e.FirstParameter+start/e.Curve.Radius,e.FirstParameter+end/e.Curve.Radius)

def head_path(w, length):
    edges=[]; left=length
    for e in w.Edges:
        if left<=1e-8:break
        if e.Length<=left+1e-8:edges.append(e);left-=e.Length
        else:edges.append(edge_segment(e,0,left));left=0
    assert left<1e-6
    return Part.Wire(edges)

def tail_path(w, length):
    edges=[]; left=length
    for e in reversed(w.Edges):
        if left<=1e-8:break
        if e.Length<=left+1e-8:edges.insert(0,e);left-=e.Length
        else:edges.insert(0,edge_segment(e,e.Length-left,e.Length));left=0
    assert left<1e-6
    return Part.Wire(edges)

def tube(wire, radius):
    e = wire.Edges[0]; a = e.valueAt(e.FirstParameter)
    profile = Part.Wire([Part.makeCircle(radius, a, e.tangentAt(e.FirstParameter))])
    pipe = BRepOffsetAPI_MakePipeShell(topods.Wire(Part.__toPythonOCC__(wire)))
    pipe.SetMode(False); pipe.SetTolerance(1e-6, 1e-6, 1e-6)
    pipe.SetMaxDegree(12); pipe.SetMaxSegments(500); pipe.SetForceApproxC1(True)
    pipe.Add(topods.Wire(Part.__toPythonOCC__(profile)), False, False)
    pipe.Build(); assert pipe.IsDone() and pipe.MakeSolid()
    q = Part.__fromPythonOCC__(pipe.Shape())
    assert q.isValid() and len(q.Solids) == 1
    return q

def trimmed_bare(wire, od, bare_od, bare_length):
    """Last section must be a circular solder-entry arc, split by arc length."""
    last = wire.Edges[-1]
    assert isinstance(last.Curve, Part.Circle) and last.Length > bare_length
    t = last.LastParameter - bare_length / last.Curve.Radius
    before = Part.Edge(last.Curve, last.FirstParameter, t)
    after = Part.Edge(last.Curve, t, last.LastParameter)
    large = tube(Part.Wire(wire.Edges[:-1] + [before]), od/2)
    small = tube(Part.Wire([after]), bare_od/2)
    q = large.fuse(small).removeSplitter()
    assert q.isValid() and len(q.Solids) == 1
    return q

def path_checks(wire, samples=1001):
    radii = []; joins = []
    for i, e in enumerate(wire.Edges):
        for j in range(samples):
            k = e.curvatureAt(e.FirstParameter + (e.LastParameter-e.FirstParameter)*j/(samples-1))
            if abs(k) > 1e-10: radii.append(1/abs(k))
        if i:
            prev = wire.Edges[i-1]
            joins.append({'gap_mm': (prev.valueAt(prev.LastParameter)-e.valueAt(e.FirstParameter)).Length,
                          'tangent_dot': prev.tangentAt(prev.LastParameter).dot(e.tangentAt(e.FirstParameter))})
    return {'minimum_sampled_radius_mm': min(radii) if radii else None, 'samples_per_edge': samples,
            'maximum_join_gap_mm': max((v['gap_mm'] for v in joins), default=0.),
            'minimum_join_tangent_dot': min((v['tangent_dot'] for v in joins), default=1.)}
