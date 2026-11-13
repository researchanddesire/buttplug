"""Native editable PCB body +39 links to actual selected STEP component bodies.

Finished PCB mounting planes are explicit. Raw KiCad STEP's solder/mask seating
conventions are retained separately; no component boxes or proxy geometry.
"""
from pathlib import Path
import hashlib,json
import FreeCAD as A,Part,Sketcher
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
data=json.loads((H/'mcad.json').read_text());assert sha(ROOT/data['native_board'])==data['board_sha256']
def mat(m):return A.Matrix(*[v for row in m for v in row])
def bnd(q):
 b=q.optimalBoundingBox(False,False);return[getattr(b,n)for n in('XMin','YMin','ZMin','XMax','YMax','ZMax')]
d=A.newDocument('SingleFlangePlacement');d.Label='Single flange / native PCB and selected parts / unrouted study'
root=d.addObject('App::Part','SingleFlange');root.Label='Single flange PCB /39 selected positions'
sources=d.addObject('App::DocumentObjectGroup','SelectedSourceGeometry');sources.Label='Actual selected STEP sources / linked component bodies'
board=d.addObject('PartDesign::Body','PCB');root.addObject(board)
profile=board.newObject('Sketcher::SketchObject','BoardOutlineAndHoles');pts=data['outline_product_XZ_mm']
for p,q in zip(pts,pts[1:]+pts[:1]):
 n=profile.addGeometry(Part.LineSegment(A.Vector(*p,0),A.Vector(*q,0)),False);profile.addConstraint(Sketcher.Constraint('Block',n))
for r in data['holes']:
 x,z=r['product_XZ_mm'];n=profile.addGeometry(Part.Circle(A.Vector(x,z,0),A.Vector(0,0,1),r['drill_mm']/2),False);profile.addConstraint(Sketcher.Constraint('Block',n))
for x,z in[(-16,10),(-10,10),(-4,10),(2,10)]:
 n=profile.addGeometry(Part.Circle(A.Vector(x,z,0),A.Vector(0,0,1),.8636/2),False);profile.addConstraint(Sketcher.Constraint('Block',n))
pad=board.newObject('PartDesign::Pad','FinishedPCB');pad.Profile=profile;pad.Length=1
d.recompute();assert profile.FullyConstrained and pad.Shape.isValid()and len(pad.Shape.Solids)==1
board.Placement=A.Placement(mat([[1,0,0,0],[0,0,-1,-25.952],[0,1,0,0],[0,0,0,1]]));profile.Visibility=False
board.addProperty('App::PropertyString','SourceKiCad');board.SourceKiCad=data['native_board'];board.addProperty('App::PropertyString','SourceSHA256');board.SourceSHA256=data['board_sha256'];board.addProperty('App::PropertyString','GeometryScope');board.GeometryScope='Finished1mmPCB envelope with native outline/drills; copper/mask are not separately represented; schematic/routing remain KiCad source.'
if board.ViewObject:board.ViewObject.ShapeColor=(.12,.35,.20)
cache={};rows=[]
for record in data['components']:
 p=ROOT/record['model'];assert sha(p)==record['model_sha256']
 if p not in cache:
  shape=Part.Shape();shape.read(str(p));assert not shape.isNull()and shape.isValid(),str(p)
  source=d.addObject('App::Part','Source_'+str(len(cache)+1));source.Label=p.stem+' / actual source geometry';sources.addObject(source)
  source.addProperty('App::PropertyString','RelativeSourceSTEP');source.RelativeSourceSTEP=record['model'];source.addProperty('App::PropertyString','SourceSHA256');source.SourceSHA256=record['model_sha256']
  for i,solid in enumerate(shape.Solids):
   body=d.addObject('PartDesign::Body','SourceBody_'+str(len(cache)+1)+'_'+str(i+1));source.addObject(body)
   feature=body.newObject('PartDesign::Feature','ImportedSTEP');feature.Shape=solid.copy();body.Tip=feature
   if body.ViewObject:body.ViewObject.ShapeColor=(.73,.72,.68)if 'MillMax'in p.name else(.35,.36,.37)
  source.Visibility=False;cache[p]=source
 link=d.addObject('App::Link',record['ref']);link.setLink(cache[p]);root.addObject(link);link.LinkPlacement=A.Placement(mat(record['model_to_product_matrix4']));link.Label=record['ref']+' / '+record['value'];link.Visibility=True
 rows.append({'ref':record['ref'],'link_object':link.Name,'source_part':cache[p].Name,'source_sha256':record['model_sha256'],'model_to_product_matrix4':record['model_to_product_matrix4']})
root.addProperty('App::PropertyString','SourceBoardSHA256');root.SourceBoardSHA256=data['board_sha256'];root.addProperty('App::PropertyString','StudyStatus');root.StudyStatus='Unrouted geometric study; solder stand-off/received dimensions/RF/sealing/loading remain unqualified'
d.recompute();assert root.Shape.isValid()and len(root.Shape.Solids)==142,(len(root.Shape.Solids),root.Shape.isValid())
path=H/'SingleFlangePlacement.FCStd';d.saveAs(str(path));root.Shape.exportStep(str(H/'SingleFlangePlacement.step'))
r={'status':'native multi-body PCB/source-links assembly saved; not physical fit acceptance','board_sha256':data['board_sha256'],'native_sha256':sha(path),'normalized_STEP_sha256':sha(H/'SingleFlangePlacement.step'),'root_object':root.Name,'FreeCAD_version':A.Version(),'component_links':rows,'unique_source_model_parts':len(cache),'package_solids':141,'finished_PCB_solids':1,'total_solids':len(root.Shape.Solids),'root_exact_bounds_product_mm':bnd(root.Shape),'PCB_fully_constrained':profile.FullyConstrained,'PCB_Parametric_Pad_mm':1,'source_linked_models':True,'component_proxy_boxes':False,'stand_off_assumption_mm':0,'physical_stand_off_acceptance':False,'raw_native_KiCad_seating_offsets_are_separate':True}
(H/'component-assembly-checks.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k]for k in('status','component_proxy_boxes','unique_source_model_parts','total_solids','root_exact_bounds_product_mm')}))
