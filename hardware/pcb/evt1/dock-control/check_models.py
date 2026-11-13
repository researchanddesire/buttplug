"""Native FreeCAD readback of selected external package sources; no GUI bridge."""
from pathlib import Path
import hashlib,json
import FreeCAD as App
import Part
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for f in sorted((HERE/'DockControl.3dshapes').glob('*.step')):
    shape=Part.read(str(f));assert not shape.isNull() and shape.isValid(),f
    assert shape.Solids,f
    bb=shape.optimalBoundingBox(False,False)
    # Exercise the actual GUI risk: cached coarse mesh must not change bounds.
    shape.tessellate(.5);fine=shape.optimalBoundingBox(False,False)
    bounds=[getattr(bb,k)for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax')]
    assert all(abs(getattr(fine,k)-v)<1e-8 for k,v in zip(('XMin','YMin','ZMin','XMax','YMax','ZMax'),bounds))
    rows.append({'file':f.name,'sha256':sha(f),'valid':True,'solids':len(shape.Solids),
                 'faces':len(shape.Faces),'exact_bounds_mm':bounds})
out={'scope':'Native selected standard external package geometry; not component maximum tolerance, received fit or a solved LCD socket mate',
     'FreeCAD_version':App.Version(),'models':rows,'missing_LCD_socket_3D':'J302 Molex52437-2771. Manufacturer download failed; no substituted box or inferred mating plane.',
     'physical_mating_qualified':False,'full_product_order_ready':False}
(HERE/'model-checks.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({'native_models_valid':len(rows),'J302_3D_missing':True,'full_product_order_ready':False}))
