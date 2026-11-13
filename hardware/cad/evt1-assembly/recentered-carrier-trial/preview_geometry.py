"""Presentation-source geometry fingerprints, insensitive to BRep text IDs.

This binds preview meshes to the same saved native geometry. It does not
replace the separate Boolean/clearance checks or waive the C0 coil limitation.
"""
import math
def point(v):return [float(v.x),float(v.y),float(v.z)]
def key(row):return tuple(round(x,6)for x in row)
def fingerprint(shape):
    b=shape.optimalBoundingBox(False,False)
    edges=[]
    for e in shape.Edges:
        a,z=e.ParameterRange
        pts=[point(e.valueAt(a+(z-a)*i/8))for i in range(9)]
        f=[x for p in pts for x in p];r=[x for p in reversed(pts)for x in p]
        edges.append([e.Length]+(f if key(f)<=key(r)else r))
    faces=[]
    for f in shape.Faces:
        a,b1,c,d=f.ParameterRange
        pts=sorted([point(f.valueAt(a+(b1-a)*i/2,c+(d-c)*j/2))for i in range(3)for j in range(3)],key=key)
        faces.append([f.Area]+[x for p in pts for x in p])
    return {'counts':[len(shape.Solids),len(shape.Faces),len(shape.Edges),len(shape.Vertexes)],
            'volume_area':[shape.Volume,shape.Area],
            'bounds':[b.XMin,b.YMin,b.ZMin,b.XMax,b.YMax,b.ZMax],
            'vertices':sorted([point(v.Point)for v in shape.Vertexes],key=key),
            'edge_samples':sorted(edges,key=key),'face_samples':sorted(faces,key=key)}
def same(a,b,tolerance=1e-7):
    if isinstance(a,dict):return a.keys()==b.keys()and all(same(a[k],b[k],tolerance)for k in a)
    if isinstance(a,list):return len(a)==len(b)and all(same(x,y,tolerance)for x,y in zip(a,b))
    return math.isclose(a,b,rel_tol=1e-12,abs_tol=tolerance)
