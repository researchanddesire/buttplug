"""Import the two existing routed dock PCBs through the installed StepUp WB.

Run in a FreeCAD GUI with the main dock assembly closed. Native files and the
source/geometry reports are regenerated; the KiCad PCB sources are read-only.
"""
from pathlib import Path
import hashlib
import json
import os

import FreeCAD as App
import FreeCADGui as Gui
import kicadStepUptools as ksu

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'hardware/cad/evt1-assembly'
models = OUT/'vendor/kicad-models'
assert models.is_dir()
preferences = App.ParamGet('User parameter:BaseApp/Preferences/Mod/kicadStepUpGui')
settings = {'prefix3d_1':str(models)+'/', 'pcb_placement':2,
            'help_warning_enabled':False}
previous = {key:(preferences.GetString(key) if isinstance(value,str) else
                 preferences.GetBool(key) if isinstance(value,bool) else preferences.GetInt(key))
            for key,value in settings.items()}

def set_setting(key,value):
    if isinstance(value,str):preferences.SetString(key,value)
    elif isinstance(value,bool):preferences.SetBool(key,value)
    else:preferences.SetInt(key,value)

old_messages=ksu.show_messages
try:
    for key,value in settings.items():set_setting(key,value)
    ksu.cfg_read_all()
    ksu.models3D_prefix=str(models)+'/'
    ksu.show_messages=False
    for domain,filename in (('dock','DockUSB.FCStd'),('pins','PinPCB.FCStd')):
        target=OUT/'pcb'/filename
        for existing in list(App.listDocuments().values()):
            if existing.FileName==str(target):
                if any(parent.Document!=existing for o in existing.Objects for parent in o.InList):
                    raise RuntimeError('Close the assembly using '+filename+' before importing its source')
                App.closeDocument(existing.Name)
        source=ROOT/'hardware/pcb/evt1'/domain/(domain+'-evt1.kicad_pcb')
        source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
        App.setActiveDocument('')
        ksu.open(str(source))
        doc=App.ActiveDocument
        roots=[o for o in doc.Objects if o.TypeId=='App::Part' and not any(p.Document==doc for p in o.InList)]
        assert len(roots)==1
        assert roots[0].Shape.isValid()
        target.parent.mkdir(parents=True,exist_ok=True)
        doc.recompute();doc.saveAs(str(target))
        components=[{'name':o.Name,'label':o.Label,'type':o.TypeId,
                     'parents':[p.Name for p in o.InList if p.Document==doc]}
                    for o in doc.Objects]
        bounds=roots[0].Shape.optimalBoundingBox(False,False)
        report={'board_file':str(source.relative_to(ROOT)), 'source_board_sha256':source_sha,
                'native_file':str(target.relative_to(ROOT)),
                'native_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                'root_object':roots[0].Name,'stepup_version':str(getattr(ksu,'ksu_version','12.6.9')),
                'FreeCAD_version':App.Version(),'objects':components,
                'root_exact_bounds_mm':[getattr(bounds,k) for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax')]}
        (target.parent/(domain+'-stepup-import.json')).write_text(json.dumps(report,indent=2)+'\n')
        assert hashlib.sha256(source.read_bytes()).hexdigest()==source_sha
finally:
    for key,value in previous.items():set_setting(key,value)
    ksu.show_messages=old_messages
    ksu.cfg_read_all()
