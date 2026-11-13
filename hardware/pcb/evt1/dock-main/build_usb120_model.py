"""Selected USB4105 1.20mm stakes, derived from attributed KiCad family STEP.

Preserves every source solid except adding the manufacturer length delta to
four shell stakes. Imported source geometry remains explicit, with native
sketch/pad features only on the two shell bodies. Not OEM selected-part CAD.
"""
from pathlib import Path
import hashlib,json
import FreeCAD as A,Part,Sketcher
H=Path(__file__).resolve().parent;O=H/'DockMain.3dshapes'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
src=O/'USB4105-family-source.step';shape=Part.read(str(src));assert len(shape.Solids)==36
d=A.newDocument('USB4105_GF_A_120');p=d.addObject('App::Part','USB4105_GF_A_120')
records=[];bodies=[]
for i,solid in enumerate(shape.Solids):
 b=d.addObject('PartDesign::Body','SourceSolid%02d'%i);p.addObject(b)
 base=b.newObject('PartDesign::Feature','ImportedFamilySolid');base.Shape=solid
 if solid.BoundBox.ZMin < -.9:
  sec=solid.section(Part.makePlane(30,30,A.Vector(-15,-15,-.90)))
  groups=Part.sortEdges(sec.Edges);assert len(groups)==2
  sketch=b.newObject('Sketcher::SketchObject','StakeCrossSections');sketch.Placement.Base=A.Vector(0,0,-.90)
  for edges in groups:
   w=Part.Wire(edges);assert w.isClosed() and len(edges)==4
   for edge in edges:
    vs=edge.Vertexes;assert len(vs)==2
    sketch.addGeometry(Part.LineSegment(A.Vector(vs[0].Point.x,vs[0].Point.y,0),A.Vector(vs[1].Point.x,vs[1].Point.y,0)),False)
  pad=b.newObject('PartDesign::Pad','SelectedStakeLength');pad.Profile=sketch;pad.Length=.30;pad.Reversed=True
  d.recompute();assert b.Shape.isValid() and len(b.Shape.Solids)==1
  assert abs(b.Shape.BoundBox.ZMin+1.2)<1e-6
  if A.GuiUp:base.Visibility=False;sketch.Visibility=False
  records.append({'body':b.Name,'source_solid_index':i,'section_plane_mm':-.9,'source_stake_bottom_mm':-.95,'selected_stake_bottom_mm':-1.2,'additive_pad_mm':.30,'four_stakes_count':2})
 else:d.recompute()
 bodies.append(b)
assert len(records)==2
native=O/'USB4105-GF-A-120.FCStd';step=O/'USB4105-GF-A-120.step'
d.recompute();d.saveAs(str(native));Part.export(bodies,str(step))
original=shape.optimalBoundingBox(False,False);final=Part.makeCompound([b.Shape for b in bodies]).optimalBoundingBox(False,False)
assert all(abs(getattr(original,v)-getattr(final,v))<1e-6 for v in('XMin','XMax','YMin','YMax','ZMax'))
assert abs(final.ZMin+1.2)<1e-6
record={'selected_MPN':'GCT USB4105-GF-A-120','classification':'selected dimensional derivative of KiCad family STEP; NOT OEM selected-part CAD',
 'family_source_STEP':src.name,'family_source_sha256':sha(src),'family_source_license':'KiCad-LICENSE.md',
 'primary_drawing':'https://gct.co/files/drawings/usb4105.pdf','primary_drawing_sha256':sha(Path('/private/tmp/dock-usb4105.pdf')),
 'manufacturer_stake_below_seating_mm':1.20,'manufacturer_stake_tolerance_mm':.15,
 'native':native.name,'native_sha256':sha(native),'STEP':step.name,'STEP_sha256':sha(step),
 'editable_bodies':36,'changed_shell_bodies':records,'unchanged_geometry':'All other34 imported source solids; shell geometry above Z-0.90 unchanged. Only four stakes extended0.25mm below source bottom.',
 'bounds_mm':[final.XMin,final.YMin,final.ZMin,final.XMax,final.YMax,final.ZMax],
 'physical_validation':False,'qualification':'Family dimensions/model details other than selected stake delta remain nominal attributed CAD. Actual received parts, 1.00mm PCB protrusion and window tolerance require trial.'}
(O/'usb120-model-provenance.json').write_text(json.dumps(record,indent=2)+'\n')
print('USB120 native derivative built',len(bodies),record['bounds_mm'])
