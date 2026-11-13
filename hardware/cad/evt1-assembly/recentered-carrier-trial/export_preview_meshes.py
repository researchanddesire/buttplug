"""Read-only native-to-preview tessellations and exact physical BRep signatures."""
from pathlib import Path
import hashlib,json,sys
import FreeCAD as App
import Part
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
import build_evt1_dock_recentered_carrier as m
from preview_geometry import fingerprint
p=m.OUT/'RecenteredCarrierTrial.FCStd';before=m.sha(p)
d=App.openDocument(str(p));part=d.RecenteredContactModule;items=[];signatures={};geometry={}
for name,s in m.physical_shapes(part):
    signatures[name]=hashlib.sha256(s.cleaned().exportBrepToString().encode()).hexdigest()
    geometry[name]=fingerprint(s)
    verts,faces=s.tessellate(.12)
    rgb=[.90,.86,.76] if name in (part.Carrier.Name,part.Retainer.Name) else [.75,.57,.18] if 'Pogo' in name else [.25,.28,.30] if 'Magnet' in name else [.25,.55,.28] if 'PinBoard' in name else [.60,.63,.67]
    items.append({'name':name,'vertices':[list(v)for v in verts],'triangles':faces,'color':rgb})
assert before==m.sha(p)
(m.OUT/'preview-meshes-render-source.json').write_text(json.dumps(items))
(m.OUT/'preview-input-binding.json').write_text(json.dumps({'source_native':str(p),'source_native_SHA256_at_export':before,'physical_clean_BRep_signatures':signatures,'physical_geometry_fingerprints':geometry,'geometry_fingerprint_tolerance_mm':1e-7,'binding_scope':'Presentation source only; separate native Boolean/fit checks and coil C0 exception unchanged','source_saved':False},indent=2)+'\n')
print('Read-only native preview export:',len(items),'physical components',flush=True)
