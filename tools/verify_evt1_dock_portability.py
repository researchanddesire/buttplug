"""Cold-reopen the saved dock with only its relocated, source-bound natives.

Run in FreeCAD GUI after the geometry/loading checks. Unrelated documents are
left open. No source geometry or native file is saved by this check.
"""
from pathlib import Path
import hashlib,json,shutil
import FreeCAD as App
import FreeCADGui as Gui

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/cad/evt1-assembly'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
native=OUT/'DockAssembly.FCStd';digest=sha(native)
review=json.loads((OUT/'review.json').read_text())
check=json.loads((OUT/'native-check.json').read_text())
assert review['native_sha256']==check['native_sha256']==digest
assert check['nominal_geometry_pass']
sources={}
for row in review['external_sources']:
    file=ROOT/row['file']
    relative=file.resolve().relative_to(OUT.resolve())
    assert file.suffix=='.FCStd' and sha(file)==row['sha256'],file
    sources[str(relative)]=row['sha256']
assert sources
destination=ROOT.parent/'portable-review'/digest[:12]/'hardware/cad/evt1-assembly'
destination.mkdir(parents=True,exist_ok=True)
for relative in ['DockAssembly.FCStd']+sorted(sources):
    target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(OUT/relative,target)
    assert sha(OUT/relative)==sha(target)
owned={str((OUT/relative).resolve())for relative in ['DockAssembly.FCStd']+list(sources)}
for doc in list(App.listDocuments().values()):
    if doc.FileName and (str(Path(doc.FileName).resolve())in owned
                         or Path(doc.FileName).is_relative_to(destination)):
        App.closeDocument(doc.Name)
doc=App.openDocument(str(destination/'DockAssembly.FCStd'));doc.recompute()
links=[]
for obj in doc.Objects:
    if obj.TypeId=='App::Link' and obj.LinkedObject is not None and obj.LinkedObject.Document!=doc:
        linked=Path(obj.LinkedObject.Document.FileName).resolve()
        relative=str(linked.relative_to(destination.resolve()))
        assert relative in sources and sha(linked)==sources[relative],obj.Name
        links.append({'name':obj.Name,'file':relative,'sha256':sha(linked)})
assert {v['file']for v in links}==set(sources)
assert doc.DockAssembly.Shape.isValid()
for body in doc.Objects:
    if body.TypeId=='PartDesign::Body':
        assert body.Shape.isValid()and len(body.Shape.Solids)==1,body.Name
report={'scope':__doc__.strip(),'pass':True,'native_sha256':digest,
        'verifier_sha256':sha(Path(__file__)),'external_links':links,
        'external_files':sources,'physical_validation':False}
(OUT/'portable-check.json').write_text(json.dumps(report,indent=2)+'\n')
for d in list(App.listDocuments().values()):
    if d.FileName and Path(d.FileName).is_relative_to(destination):
        App.closeDocument(d.Name)
doc=App.openDocument(str(native));doc.recompute()
Gui.activeDocument().activeView().viewAxonometric()
Gui.activeDocument().activeView().fitAll()
print('Cold relative-link reopen:',len(links),'links from',len(sources),'native sources')
