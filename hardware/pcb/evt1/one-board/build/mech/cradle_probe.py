import FreeCAD as A,Part,json,os
r='/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/'
out={}
for n in ['MotorThermistorCap','MetalBody']:
 s=Part.Shape();s.read(r+'mech/'+n+'.step')
 sec=s.section(Part.makePlane(200,200,A.Vector(-100,-100,0),A.Vector(0,0,1)))
 rows=[]
 for y in [63,64,64.5,65,65.5,66,66.5,67,67.5,68,70,80,90,93,93.3,94]:
  line=Part.makeLine(A.Vector(0,y,0),A.Vector(30,y,0));xs=[]
  for e in sec.Edges:
   if e.BoundBox.YMin-1e-6<=y<=e.BoundBox.YMax+1e-6:
    d,pts,_=e.distToShape(line)
    if d<1e-5:xs += [round(p[0].x,4) for p in pts if p[0].x>1e-6]
  rows.append([y,sorted(set(xs))])
 out[n]=rows
open(r+'build/mech/cradle-probe.json','w').write(json.dumps(out,indent=2))
os._exit(0)
