"""Snapshot exact existing crown bodies; no guessed replacement envelope."""
from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
P=Path(__file__).resolve().parent;src=P.parent/'SingleFlangeBoardTrial.FCStd';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();binding=json.loads((P/'source-binding.json').read_text());assert sha(src)==binding['mechanical_native_sha256'];d=A.openDocument(str(src));n=A.newDocument('ButtonPressKeepouts');rows=[]
for i in range(2):
 name='IntegralSiliconeBoss'+str(i);s=d.getObject(name).Shape;assert s.isValid()and len(s.Solids)==1
 b=n.addObject('PartDesign::Body',name);f=b.newObject('PartDesign::Feature',name+'Geometry');f.Shape=s.copy();b.Tip=f
 f.addProperty('App::PropertyString','SourceGeometry');f.SourceGeometry='Exact body '+name+' from mechanical native SHA256 '+sha(src)
 rows.append({'body':name,'volume_mm3':s.Volume,'bounds_mm':[s.BoundBox.XMin,s.BoundBox.YMin,s.BoundBox.ZMin,s.BoundBox.XMax,s.BoundBox.YMax,s.BoundBox.ZMax]})
n.recompute();p=P/'ButtonPressKeepouts.FCStd';n.saveAs(str(p))
for o in n.Objects:
 if o.TypeId=='PartDesign::Body':o.Tip.Shape.exportStep(str(P/(o.Name+'.step')))
c=A.openDocument(str(p));assert len([o for o in c.Objects if o.TypeId=='PartDesign::Body'])==2
for o in c.Objects:
 if o.TypeId=='PartDesign::Body':assert o.Shape.isValid()and len(o.Shape.Solids)==1
r={'native_sha256':sha(p),'source_mechanical_native_sha256':sha(src),'source_exterior_sha256':binding['native_sha256'],'bodies':rows,'dock_translation_mm':[0,53.2,32],'additional_press_Y_range_mm':[0,.7],'press_range_is_interference_keepout_not_allowable_switch_stroke':True,'external_links':0,'physical_validation':False};(P/'button-keepout-binding.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
