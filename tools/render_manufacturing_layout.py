"""Render verified native parts: overall layout, rear joint and machining access."""
from pathlib import Path
import sys,json,hashlib
from PIL import Image,ImageDraw,PngImagePlugin
import numpy as np
import render_mechanical_r2 as draw
ROOT=Path(__file__).resolve().parents[1];folder=Path(sys.argv[1]).resolve();out=ROOT/'developer-docs/docs/assets/manufacturing-layout.png'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();r=json.loads((folder/'review.json').read_text());assert sha(folder/'ManufacturingLayout.FCStd')==r['native_sha256']
meshes=draw.NativeMeshes(folder);meshes.expected={p.name:sha(p)for p in folder.glob('*.stl')}
def color(name):
 if name.startswith(('MetalBody','MotorThermistorCap')):return(185,193,201)
 if name.startswith('MotorReference'):return(209,158,72)
 if name.startswith('TipThermistor'):return(202,77,66)
 if name.startswith('TipPotting'):return(160,129,180)
 if name.startswith('ThinRearNut'):return(181,137,56)
 if name.startswith('BondedBoot'):return(173,142,190)
 if name.startswith('CapFaceSeal'):return(53,97,137)
 if 'Electronics' in name:return(74,144,105)
 if 'PackReference' in name:return(100,157,192)
 if 'FoamSpacer' in name:return(158,160,164)
 return(104,156,147)
draw.part_color=color
def g(name,file=None,delta=None):
 triangles=meshes.load(file or name+'-view')
 if delta is not None:triangles=triangles+np.array(delta)
 return(name,triangles,None)
assembly=[g('MetalBody','MetalBody-half-view'),g('MotorThermistorCap','MotorThermistorCap-half-view'),g('FlangeTray'),g('ThinRearNut'),g('BodyElectronicsReference'),g('FlangeElectronicsMechanicalProposal'),g('UnselectedPackReference'),g('MotorReferenceFitTBD')]
rear=[g('MetalBody','MetalBody-rear-half-view'),g('FlangeTray','FlangeTray-rear-half-view'),g('ThinRearNut','ThinRearNut-half-view'),g('BondedBootCuffProcessSpace','BondedBootCuffProcessSpace-half-view')]
plastic=[g('FlangeTray','FlangeTray'),g('RearCover','RearCover',delta=(99,0,0))]
cap=[g('MetalBody','MetalBody-front-half-view'),g('MotorThermistorCap','MotorThermistorCap-half-view'),g('MotorReferenceFitTBD'),g('TipPottingProcessSpace'),g('TipThermistorHeadReference'),g('CapFaceSealProcessSpace','CapFaceSealProcessSpace-half-view')]
im=Image.new('RGB',(2160,1510),'white');d=ImageDraw.Draw(im)
draw.label(d,(32,22),'Short threaded rear stub / keyed flange joint',35,True)
draw.label(d,(32,77),'Turned body with indexed collar flats + nose cap. Plastic tray/cover, thin nut, seals and silicone boot.',22,fill=draw.MUTED)
draw.panel(im,(20,125,960,570),'ASSEMBLY / METAL HALF SECTION','15 mm neck and rounded outside retained.',assembly,camera=(.6,-.25,2.5))
draw.panel(im,(1000,125,1140,570),'REAR JOINT / SECTION','M18 x 1 stub + 4 mm nut; collar flats resist twisting.',rear,camera=(0.,-.1,3.))
draw.panel(im,(20,715,960,570),'TWO OPEN PLASTIC PARTS / PRINT POSES','Local nut well; shifted posts. Nut installs before electronics.',plastic,camera=(.35,-1.6,2.1))
draw.panel(im,(1000,715,1140,570),'NOSE / MOTOR POCKET AND OFFSET SENSOR','Straight counterbore and bores. One offset live-tool drill.',cap,camera=(0.,-.05,3.))
d=ImageDraw.Draw(im)
draw.label(d,(35,1320),'Gold: 24 AF x 4 mm nut clamping a 2 mm tray pad against the shoulder. Purple cuff: partial silicone boot.',22)
draw.label(d,(35,1364),'M30 x 1.5 thread callout; CAD uses pilot/root envelopes. Face O-ring gland shown. Actual fits and tooling remain to review.',22)
draw.label(d,(35,1408),'Sensor leads exit beside the motor. Motor bears on metal; no PCB motor mount, deep lead keyway or internal cage.',22)
draw.label(d,(35,1456),'DFM study. Nut locking, thread strength/fit, creep, tool qualification, full boot, loom and physical trials remain open.',21,fill=draw.AMBER)
meshes.verify();meta={'native_sha256':r['native_sha256'],'renderer_sha256':sha(Path(__file__)),'meshes_sha256':meshes.used,'scope':'Actual native solids/half sections. Rear clip excludes wings for close view; generic nut and cuff/seal are engineering reservations. Plastic panel uses exported print poses; cover translated99mm. No photorealistic or inferred geometry.'}
info=PngImagePlugin.PngInfo();info.add_text('Source',json.dumps(meta,sort_keys=True));im.save(out,pnginfo=info);out.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n');print(out)
