from pathlib import Path
import FreeCAD as App
import Part,json,hashlib
P=Path('/private/tmp/compass-jobs/candidate050/DockAssembly.FCStd')
def bb(s):
 b=s.optimalBoundingBox(False,False);return [getattr(b,k)for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax')]
d=App.openDocument(str(P));ffc=d.DockLCDInstance.Shape.Solids[5];h=d.UIBoardAssembly.Shape.Solids[5];l=d.UIBoardAssembly.Shape.Solids[6]
mask=Part.makeCompound([Part.makeBox(.200002,8,5,App.Vector(-6.5+.5*i-.100001,107,59))for i in range(27)])
rows=[]
for F in (61.095,61.1,61.2,61.25,61.275,61.28,61.3,61.35,61.4):
 s=h.copy();s.translate(App.Vector(0,0,F-60.5));c=ffc.common(s);remainder=c.cut(mask)
 latch=l.copy();latch.translate(App.Vector(0,0,F-60.5));lc=ffc.common(latch)
 r={'F':F,'shim':61.5-F,'fused_total':c.Volume,'outside_terminal_width_strips':remainder.Volume,'latch':lc.Volume,'common_bounds':bb(c),'solid_count':len(c.Solids),'solid_widths':[[round(x,6)for x in bb(v)]for v in c.Solids]}
 print({k:v for k,v in r.items()if k!='solid_widths'},flush=True);rows.append(r)
Path('/private/tmp/compass-jobs/lcd-terminal-separation.json').write_text(json.dumps(rows,indent=2)+'\n')
