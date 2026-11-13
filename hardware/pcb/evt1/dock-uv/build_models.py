"""Selected external-package geometry for the UV PCB, not fit boxes.

Run FreeCAD's Python outside the sandbox; no GUI/document belonging to another
task is opened. Manufacturer/family/nominal reconstruction scopes are explicit.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
OUT=HERE/'models';OUT.mkdir(exist_ok=True)
STOCK=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows={}
families={
 'R_0603_1608Metric':'Resistor_SMD','R_0805_2012Metric':'Resistor_SMD',
 'C_0603_1608Metric':'Capacitor_SMD','C_1210_3225Metric':'Capacitor_SMD',
 'SOT-23':'Package_TO_SOT_SMD','SOT-23-6':'Package_TO_SOT_SMD',
 'D_SOD-123F':'Diode_SMD',
 'JST_GH_SM08B-GHS-TB_1x08-1MP_P1.25mm_Horizontal':'Connector_JST'}
for name,family in families.items():
    source=STOCK/(family+'.3dshapes')/(name+'.step');target=OUT/source.name
    shutil.copy2(source,target);shape=Part.Shape();shape.read(str(target))
    bb=shape.BoundBox
    rows[name]={'source':str(source),'source_sha256':sha(source),'local_step':target.name,
        'source_kind':'KiCad selected external standard package geometry',
        'model_bounds_mm':[bb.XMin,bb.YMin,bb.ZMin,bb.XMax,bb.YMax,bb.ZMax],
        'scope':'Nominal package geometry; selected case maximum dimensions checked separately. Not tolerance or internal construction proof.',
        'license':'KiCad CC-BY-SA4.0 with library exception; see KiCad-LICENSE.md'}
source=ROOT/'hardware/cad/evt1-assembly/vendor/uv/VLMU35CB.stp'
target=OUT/'Vishay_VLMU35CB.stp';shutil.copy2(source,target)
rows['Vishay_VLMU35CB2_Actual_TwoTerminal']={
    'source':'https://www.vishay.com/docs/80469/led_smd_ceramic_vlmu35cb.zip',
    'source_sha256':sha(source),'local_step':target.name,
    'source_kind':'Manufacturer family10-solid STEP',
    'KiCad_model_rotation_XYZ_deg':[-90,0,0],'KiCad_model_offset_XYZ_mm':[0,0,.7],
    'active_geometric_rotation_XYZ_deg':[90,0,0],
    'rotation_convention':'KiCad model Euler angles have opposite active sign; confirmed with native STEP exported terminal/optical planes',
    'optical_axis_after_rotation':[0,0,1],'mounting_plane_after_offset_Z_mm':0,
    'scope':'OEM family height1.775mm versus selected datasheet nominal1.68mm discrepancy retained; actual cathode marking/received package controls assembly',
    'license':'Manufacturer rights retained'}
# The selected Bourns drawing has no supplied STEP. Reconstruct its molded
# body and two wraparound terminals, recording all cosmetic choices explicitly.
doc=App.newDocument('SelectedBournsSRP4020TA')
root=doc.addObject('App::Part','SRP4020TA100M')
root.addProperty('App::PropertyString','SelectedMPN','Source');root.SelectedMPN='SRP4020TA-100M'
root.addProperty('App::PropertyString','PrimarySource','Source')
root.PrimarySource='https://www.bourns.com/docs/Product-Datasheets/SRP4020TA.pdf'
for name,value in [('BodyLength',4.45),('BodyWidth',4.06),('BodyHeight',1.8),('TerminalWidth',.76),('TerminalLength',2.0)]:
    root.addProperty('App::PropertyLength',name,'Drawing');setattr(root,name,value)
root.addProperty('App::PropertyString','ModelLimit','Source')
root.ModelLimit='Nominal selected external drawing reconstruction. Terminal wrap thickness0.15mm/height0.6mm and mold corner radius0.2mm are cosmetic, not toleranced source dimensions. No internal coil/core model.'
shapes=[]
core=Part.makeBox(4.45,4.06,1.65,App.Vector(-2.225,-2.03,.15))
edges=[e for e in core.Edges if abs(e.Vertexes[-1].Point.z-e.Vertexes[0].Point.z)>1]
core=core.makeFillet(.2,edges)
for name,shape in [('MoldedCore',core)]:
    body=doc.addObject('PartDesign::Body',name);root.addObject(body)
    feature=body.newObject('PartDesign::Feature',name+'ExternalShape');feature.Shape=shape;shapes.append(shape)
for sign,name in [(-1,'LeftTerminal'),(1,'RightTerminal')]:
    x=-2.225 if sign<0 else 1.465
    bottom=Part.makeBox(.76,2.0,.15,App.Vector(x,-1,0))
    wallx=-2.225 if sign<0 else 2.075
    wrap=Part.makeBox(.15,2.0,.6,App.Vector(wallx,-1,0))
    shape=bottom.fuse(wrap).removeSplitter()
    body=doc.addObject('PartDesign::Body',name);root.addObject(body)
    feature=body.newObject('PartDesign::Feature',name+'DrawingShape');feature.Shape=shape;shapes.append(shape)
doc.recompute();doc.saveAs(str(OUT/'Bourns_SRP4020TA_100M.FCStd'))
compound=Part.makeCompound(shapes);assert compound.isValid() and len(compound.Solids)==3
compound.exportStep(str(OUT/'Bourns_SRP4020TA_100M.step'))
rows['Bourns_SRP4020TA_Actual_Lands']={'source':root.PrimarySource,
    'source_kind':'Selected manufacturer-drawing external package reconstruction',
    'local_step':'Bourns_SRP4020TA_100M.step','native':'Bourns_SRP4020TA_100M.FCStd',
    'nominal_body_mm':[4.45,4.06,1.8],'maximum_body_mm':[4.7,4.31,2.0],
    'terminal_bottom_width_length_mm':[.76,2.0],'cosmetic_assumptions':root.ModelLimit,
    'scope':'Three native component bodies; no generic single fit box'}
for row in rows.values():row['local_step_sha256']=sha(OUT/row['local_step'])
license_path=ROOT/'hardware/pcb/evt1/dock-control/DockControl.3dshapes/KiCad-LICENSE.md'
shutil.copy2(license_path,OUT/license_path.name)
(OUT/'source-manifest.json').write_text(json.dumps({'builder_sha256':sha(Path(__file__)),'parts':rows,
    'physical_fit':False,'thermal_validation':False},indent=2)+'\n')
print(json.dumps({'models':len(rows),'Bourns_native_bodies':3,'out':str(OUT)}))
App.closeDocument(doc.Name)
