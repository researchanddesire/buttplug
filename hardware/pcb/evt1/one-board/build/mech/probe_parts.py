import FreeCAD as App, Part, json, sys
sys.path.insert(0,'/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/mech')
from compass_datums import *
M=MECH
pcb=Part.Shape(); pcb.read(M+'/compass-one-board.step')
m=pcb_matrix(); pcb=pcb.transformShape(m,True) or pcb
rows=[]
for s in pcb.Solids:
    bb=s.BoundBox
    if bb.YMax>BOARD_B_Y+0.2 and bb.YLength<20:   # B-side parts (toward +Y)
        rows.append((round(bb.XMin,1),round(bb.XMax,1),round(bb.ZMin,1),round(bb.ZMax,1),round(bb.YMax,2)))
rows.sort()
for r in rows: print('B part X %6.1f..%6.1f Z %6.1f..%6.1f top Y %.2f (h %.2f)'%(r[0],r[1],r[2],r[3],r[4],r[4]-BOARD_B_Y))
# old body outer meridian, finely sampled, for the contour design
body=Part.Shape(); body.read(M+'/MetalBody.step')
sec=body.section(Part.makePlane(200,200,App.Vector(-100,-100,0),App.Vector(0,0,1)))
pts=[]
for e in sec.Edges:
    bb=e.BoundBox
    if bb.XMin>=7.4 and bb.YMin>=-0.01 and bb.YMax<=64.01 and bb.XMax>7.49:
        for p in e.discretize(Distance=0.25):
            if p.x>0: pts.append((round(p.y,4),round(p.x,4)))
pts=sorted(set(pts))
json.dump(pts,open('/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/build/mech/old_meridian.json','w'))
print('meridian pts',len(pts),pts[:3],pts[-3:])
