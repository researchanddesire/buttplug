"""Import routed functional dock boards with actual models through StepUp.

Run in the Linux FreeCAD GUI. Sibling KiCad sources/models are read-only.
All component models are resolved from the routed sources; no substitute boxes
are created. IMPORT_BOARD_NAMES may select a subset for a source-only refresh.
"""
from pathlib import Path
import hashlib
import json
import re
import sys
import FreeCAD as App
import FreeCADGui as Gui
import kicadStepUptools as ksu

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import kicad_sexp as s
OUT=ROOT/'hardware/cad/evt1-assembly/pcb'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
BOARDS=(
    ('UVBase','dock-uv/base/pcb/dock-uv-base.kicad_pcb',20),
    ('UVLid','dock-uv/lid/pcb/dock-uv-lid.kicad_pcb',20),
    ('LidUI','dock-control/routed-lid/dock-lid-routed.kicad_pcb',28),
    ('MainPCB','dock-main/dock-main-MCAD-placement.kicad_pcb',138),
)
prefs=App.ParamGet('User parameter:BaseApp/Preferences/Mod/kicadStepUpGui')
old_placement=prefs.GetInt('pcb_placement');old_warning=prefs.GetBool('help_warning_enabled')
old_messages=ksu.show_messages
results=[]
try:
    prefs.SetInt('pcb_placement',2);prefs.SetBool('help_warning_enabled',False)
    ksu.cfg_read_all();ksu.show_messages=False
    for name,relative,expected_models in BOARDS:
        if globals().get('IMPORT_BOARD_NAMES') and name not in IMPORT_BOARD_NAMES:
            continue
        source=ROOT/'hardware/pcb/evt1'/relative;target=OUT/(name+'.FCStd')
        digest=sha(source);tree=s.parse(source.read_text());models={};without=[]
        copper_only=[];classification={};model_coverage_binding=None
        if name=='MainPCB':
            selected=json.loads((OUT/'MainPCB-source-models.json').read_text())
            assert digest==selected['snapshot_board_sha256']
            copper_only=selected['copper_only_references']
            classification={v['reference']:v for v in selected['coverage']['references']}
            model_coverage_binding={'file':str((OUT/'MainPCB-source-models.json').relative_to(ROOT)),
                                    'sha256':sha(OUT/'MainPCB-source-models.json')}
        for footprint in s.children(tree,'footprint'):
            reference=next(t[2].value for t in s.children(footprint,'fp_text')if t[1].value=='reference')
            selected=s.children(footprint,'model')
            if not selected:
                if reference in copper_only:continue
                if not reference.startswith(('H','TP')):without.append(reference)
                continue
            assert len(selected)==1,(name,reference)
            uri=selected[0][1].value
            path=Path(uri.replace('${KIPRJMOD}',str(source.parent))).resolve()
            assert '$'not in str(path)and path.is_file(),(name,reference,path)
            models[reference]={'path':str(path.relative_to(ROOT)),'sha256':sha(path)}
            if classification:
                entry=classification[reference]
                assert not entry['copper_only'] and models[reference]['sha256']==entry['model']['model_sha256']
        assert len(models)==expected_models,(name,len(models),expected_models)
        for existing in list(App.listDocuments().values()):
            if existing.FileName==str(target):
                assert not any(parent.Document!=existing for o in existing.Objects for parent in o.InList), 'Close assembly using '+name
                App.closeDocument(existing.Name)
        App.setActiveDocument('');ksu.open(str(source));doc=App.ActiveDocument
        roots=[o for o in doc.Objects if o.TypeId=='App::Part'and not any(p.Document==doc for p in o.InList)]
        assert len(roots)==1,(name,[o.Name for o in roots])
        root=roots[0];assert root.Shape.isValid()and root.Shape.Solids,name
        imported={}
        for reference in models:
            pattern=re.compile(r'(?<![A-Za-z0-9])'+re.escape(reference)+r'(?![0-9])')
            hits=[o for o in doc.Objects if hasattr(o,'Shape')and not o.Shape.isNull()
                  and pattern.search(o.Name+' '+o.Label)]
            assert hits,(name,'Selected model was not imported',reference)
            imported[reference]=[{'name':o.Name,'label':o.Label}for o in hits]
        OUT.mkdir(parents=True,exist_ok=True);doc.recompute();doc.saveAs(str(target))
        bounds=root.Shape.optimalBoundingBox(False,False)
        report={'scope':'Actual source-bound StepUp board/model import; nominal assembly fit not yet established',
                'board':str(source.relative_to(ROOT)),'board_sha256':digest,
                'native':str(target.relative_to(ROOT)),'native_sha256':sha(target),
                'root_object':root.Name,'selected_models':models,'imported_model_objects':imported,
                'missing_component_models':without,'solid_count':len(root.Shape.Solids),
                'unmodeled_copper_only_references':copper_only,
                'model_coverage_binding':model_coverage_binding,
                'FreeCAD_version':App.Version(),'pcb_placement':2,
                'root_exact_bounds_mm':[getattr(bounds,k)for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax')],
                'objects':[{'name':o.Name,'label':o.Label,'type':o.TypeId}for o in doc.Objects],
                'importer_sha256':sha(Path(__file__)),'physical_fit':False}
        (OUT/(name+'-stepup-import.json')).write_text(json.dumps(report,indent=2)+'\n')
        assert sha(source)==digest,'Source board changed during import'
        for item in models.values():assert sha(ROOT/item['path'])==item['sha256']
        results.append({'board':name,'models':len(models),'solids':len(root.Shape.Solids),'missing':without})
finally:
    prefs.SetInt('pcb_placement',old_placement);prefs.SetBool('help_warning_enabled',old_warning)
    ksu.show_messages=old_messages;ksu.cfg_read_all()
print(json.dumps(results,indent=2))
