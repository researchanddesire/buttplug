from pathlib import Path
import FreeCAD as App
import Part,json
P=Path('/private/tmp/compass-jobs/candidate050/DockAssembly.FCStd')
def bb(s):
 b=s.optimalBoundingBox(False,False);return [getattr(b,k)for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax')]
d=App.openDocument(str(P));ffc=d.DockLCDInstance.Shape.Solids[5]
rows=[]
for F in (60.5,61.0,61.095,61.1):
 r={'F':F,'parts':[]}
 for i,s in enumerate(d.UIBoardAssembly.Shape.Solids[5:7]):
  s=s.copy();s.translate(App.Vector(0,0,F-60.5));c=ffc.common(s)
  r['parts'].append({'socket_index':i,'mm3':c.Volume,'bounds':bb(c)if c.Volume>1e-10 else[],'solids':[{'v':v.Volume,'b':bb(v)}for v in c.Solids]})
  if F==61.095:
   c.exportStep('/private/tmp/compass-jobs/lcd-common-61p095-'+str(i)+'.step')
 print(r,flush=True);rows.append(r)
Path('/private/tmp/compass-jobs/lcd-common-details.json').write_text(json.dumps(rows,indent=2)+'\n')
