"""Give the milled U opening explicit1mm internal router radii."""
import sys
import build_pcbs as m
from route_pcbs import ctx
k=m.k
folder,path,b=ctx(sys.argv[1])
for item in list(b.GetDrawings()):
    if item.GetLayer()==k.Edge_Cuts:b.Delete(item)
segments=[((-49,86),(-35,86)),((-35,86),(-35,127)),((-34,128),(34,128)),
          ((35,127),(35,86)),((35,86),(49,86)),((49,86),(49,135)),
          ((49,135),(-49,135)),((-49,135),(-49,86))]
for a,c in segments:
    line=k.PCB_SHAPE(b);line.SetShape(k.SHAPE_T_SEGMENT);line.SetStart(m.xy(*a));line.SetEnd(m.xy(*c));line.SetWidth(k.FromMM(.05));line.SetLayer(k.Edge_Cuts);b.Add(line)
for a,mid,c in[((-35,127),(-34.7071067812,127.7071067812),(-34,128)),
                ((34,128),(34.7071067812,127.7071067812),(35,127))]:
    arc=k.PCB_SHAPE(b);arc.SetShape(k.SHAPE_T_ARC)
    arc.SetArcGeometry(m.xy(*a),m.xy(*mid),m.xy(*c));arc.SetWidth(k.FromMM(.05));arc.SetLayer(k.Edge_Cuts);b.Add(arc)
m.save(b,path)
print('Rounded',sys.argv[1],'U cornersR1mm')
