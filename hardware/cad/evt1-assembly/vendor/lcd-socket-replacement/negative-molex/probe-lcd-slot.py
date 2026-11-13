from pathlib import Path
import FreeCAD as App
import Part,json,hashlib
P=Path('/private/tmp/compass-jobs/candidate050/DockAssembly.FCStd')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bb(s):
 b=s.optimalBoundingBox(False,False);return [getattr(b,k)for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax')]
def com(a,b):
 if not a.optimalBoundingBox(False,False).intersect(b.optimalBoundingBox(False,False)):return 0.
 if len(a.Solids)>1 or len(b.Solids)>1:return sum(com(x,y)for x in a.Solids for y in b.Solids)
 return a.common(b).Volume
old=sha(P);d=App.openDocument(str(P));print('Opened',flush=True)
lcd=d.getObject('DockLCDInstance').Shape; ui=d.UIBoardAssembly.Shape
print('LCD',len(lcd.Solids),'UI',len(ui.Solids),flush=True)
ffc=lcd.Solids[5];socket=list(ui.Solids)[5:7]
assert abs(bb(ffc)[2]-61.7)<1e-6 and abs(bb(socket[0])[0]+9.75)<1e-6
assert abs(bb(socket[1])[0]+10.05)<1e-6
rows=[]
for F in (60.5,61.,61.05,61.075,61.09,61.095,61.1,61.105,61.11,61.125,61.15,61.2,61.3,61.4):
 r={'board_F_Z_mm':F,'shim_mm':61.5-F,'common_mm3':[]}
 for s in socket:
  s=s.copy();s.translate(App.Vector(0,0,F-60.5));r['common_mm3'].append(com(ffc,s))
 print(r,flush=True);rows.append(r)
report={'source':str(P),'source_SHA256':old,'source_saved':False,'LCD_bounds':bb(lcd),'FFC_bounds':bb(ffc),'socket_bounds_at_F60p5':[bb(s)for s in socket],'samples':rows}
assert old==sha(P)
Path('/private/tmp/compass-jobs/lcd-slot-height-probe.json').write_text(json.dumps(report,indent=2)+'\n')
