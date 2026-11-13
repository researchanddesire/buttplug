from pathlib import Path
import FreeCAD as A,Part,json,hashlib
H=Path(__file__).resolve().parent;p=Path('/private/tmp/ESP32-C3-MINI-1-OEM.STEP');s=Part.Shape();s.read(str(p))
b=lambda s:[getattr(s.optimalBoundingBox(False,False),n)for n in ('XMin','YMin','ZMin','XMax','YMax','ZMax')]
r={'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'valid':s.isValid(),'solids':len(s.Solids),'faces':len(s.Faces),'bounds':b(s),'solid_bounds':[b(q)for q in s.Solids]}
(H/'OEM-module-inspection.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k]for k in ('valid','solids','faces','bounds')}))
