import FreeCAD as App, Part, math, json
M='/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/mech'
body=Part.Shape(); body.read(M+'/MetalBody.step')
# section at Z=0 plane
sec=body.section(Part.makePlane(200,200,App.Vector(-100,-100,0),App.Vector(0,0,1)))
rows=[]
for y in [i*1.0 for i in range(-14,65)]:
    pts=[]
    for e in sec.Edges:
        bb=e.BoundBox
        if bb.YMin-1e-6<=y<=bb.YMax+1e-6:
            try:
                ln=Part.makeLine(App.Vector(-40,y,0),App.Vector(40,y,0))
                d,p,_=e.distToShape(ln)
                if d<1e-4:
                    for a,b in p: pts.append(abs(a.x))
            except Exception: pass
    pts=sorted(set(round(v,3) for v in pts))
    rows.append((y,pts))
for y,p in rows: print(y,p)
# faces of revolution outer: list surface types along the meridian
print('faces',len(body.Faces))
for f in body.Faces:
    bb=f.BoundBox
    if bb.XMax>7.4 and bb.YMin>-0.1 and bb.YMax<64.1:
        print(f.Surface.__class__.__name__, round(bb.YMin,2), round(bb.YMax,2), round(bb.XMax,3))
intr=Part.Shape(); intr.read(M+'/Internals.step')
for s in intr.Solids:
    bb=s.BoundBox; print('internal solid', [round(v,1) for v in (bb.XMin,bb.YMin,bb.ZMin,bb.XMax,bb.YMax,bb.ZMax)], 'rmax', round(max(math.hypot(x,z) for x in (bb.XMin,bb.XMax) for z in (bb.ZMin,bb.ZMax)),1))
