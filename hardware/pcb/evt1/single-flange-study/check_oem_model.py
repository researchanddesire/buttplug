"""Independent OEM MINI-1 footprint registration using actual copper solids."""
from pathlib import Path
import hashlib,json,sys
import FreeCAD as A,Part
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sys.path.insert(0,str(ROOT/'tools'));import kicad_sexp as s
p=H/'Selected.3dshapes/ESP32-C3-MINI-1-OEM.step';shape=Part.Shape();shape.read(str(p));t=s.parse((H/'Selected.pretty/Espressif_ESP32-C3-MINI-1_53Pads.kicad_mod').read_text());checks=[]
for pad in s.children(t,'pad'):
 at=s.child(pad,'at');x=float(at[1].value)+6.6;y=-float(at[2].value)+5.6;point=A.Vector(x,y,.017)
 solids=[q for q in shape.Solids if q.BoundBox.isInside(point)]
 okay=any(q.isInside(point,1e-6,True)for q in solids)
 checks.append({'pad':pad[1].value,'OEM_test_point_mm':[x,y,.017],'inside_actual_OEM_bottom_copper':okay})
failed=[r for r in checks if not r['inside_actual_OEM_bottom_copper']]
r={'OEM_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'valid':shape.isValid(),'solids':len(shape.Solids),'physical_pad_instance_registration_checks':checks,'failures':failed,'basis':'all native footprint contact centres tested within actual manufacturer STEP copper at17um above seating datum; this checks geometric registration, not pin electrical function, received dimensions or solder qualification'}
(H/'OEM-module-pose-checks.json').write_text(json.dumps(r,indent=2)+'\n');print('OEM registration',len(checks),'failed',len(failed));assert not failed,failed
