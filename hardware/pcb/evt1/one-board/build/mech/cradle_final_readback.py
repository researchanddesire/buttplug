import os,json,hashlib
import FreeCAD as A,Part
r='/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/'
report={'parts':{},'assembly_links':{},'outputs':{}}
try:
 for n in ['InternalCradle','CradleWireGuide']:
  d=A.openDocument(r+'mech/'+n+'.FCStd');b=d.getObject(n);s=Part.Shape();s.read(r+'mech/'+n+'.step')
  assert b.Shape.isValid() and len(b.Shape.Solids)==1 and s.isValid() and len(s.Solids)==1
  assert abs(b.Shape.Volume-s.Volume)<0.01
  report['parts'][n]={'native':d.FileName,'valid':True,'volume_delta_mm3':round(b.Shape.Volume-s.Volume,6),'body_type':b.TypeId}
 d=A.openDocument(r+'mech/compass-device.FCStd')
 for n in ['InternalCradle','CradleWireGuide']:
  o=d.getObject(n);assert o.TypeId=='App::Link' and o.LinkedObject.Shape.isValid()
  report['assembly_links'][n]=o.LinkedObject.Document.FileName
 for n in ['InternalCradle.FCStd','InternalCradle.step','CradleWireGuide.FCStd','CradleWireGuide.step','Internals.FCStd','Internals.step','compass-device.FCStd','compass-device.step','compass-device-cutaway.step','compass-internal-module.step']:
  p=r+'mech/'+n;report['outputs'][n]={'sha256':hashlib.sha256(open(p,'rb').read()).hexdigest(),'bytes':os.path.getsize(p)}
 report['pass']=True
except Exception:
 import traceback;report['error']=traceback.format_exc();report['pass']=False
open(r+'mech/cradle-saved-readback.json','w').write(json.dumps(report,indent=2)+'\n')
os._exit(0 if report['pass'] else 1)
