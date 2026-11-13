"""Resolve selected footprint-family STEP sources locally, without editing PCB."""
from pathlib import Path
import hashlib,json,shutil,sys
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H.parents[3]/'tools'))
import kicad_sexp as s
STANDARD=Path('/private/tmp/compass-kicad10/mount/KiCad/KiCad.app/Contents/SharedSupport/3dmodels')
OUT=H/'DockMain.3dshapes';OUT.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
custom={'DockUI:Texas_X2QFN-12_1.6x1.6mm_P0.4mm':'TUSB320_RWB12.step',
 'DockUI:Texas_YBH0006-C02_DSBGA-6_1.106x0.706mm_P0.4mm':'TPS22950_YBH6.step',
 'DockSafety:Texas_DRB0008A_3x3mm_P0.65_EP_Fingers':'TPS3431_DRB8.step',
 'DockSafety:Texas_RXP0008A_1.25x1.5mm_Asymmetric':'TPS22992_RXP8.step'}
plan={};missing=[]
for folder in sorted(H.glob('*.pretty')):
 for path in sorted(folder.glob('*.kicad_mod')):
  lib=folder.stem+':'+path.stem;t=s.parse(path.read_text());models=s.children(t,'model')
  if lib in custom:
   target=OUT/custom[lib];assert target.exists();plan[lib]={'local_STEP':target.name,'sha256':sha(target),'source':'custom-model-provenance.json','classification':'selected primary-dimensional reconstruction'};continue
  if not models:
   missing.append(lib);continue
  assert len(models)==1;original=models[0][1].value
  if original.startswith('${KIPRJMOD}'):
   source=Path(original.replace('${KIPRJMOD}',str(H))).resolve()
  elif original.startswith(('${KICAD6_3DMODEL_DIR}','${KICAD7_3DMODEL_DIR}')):
   source=STANDARD/Path(original.split('}/',1)[1]).with_suffix('.step')
  else:raise AssertionError(('Unresolved model namespace',lib,original))
  assert source.exists(),(lib,source)
  target=OUT/source.name
  if target.exists()and sha(target)!=sha(source):target=OUT/(source.stem+'-'+sha(source)[:10]+source.suffix)
  shutil.copyfile(source,target)
  plan[lib]={'original_URI':original,'source':str(source),'source_sha256':sha(source),
   'local_STEP':target.name,'sha256':sha(target),'classification':'attributed selected-footprint package-family STEP; dimensions/tolerances remain explicit physical qualification'}
  if lib.startswith('DockUI:USB_C_Receptacle_'):
   family=OUT/'USB4105-family-source.step';shutil.copyfile(source,family)
   selected=OUT/'USB4105-GF-A-120.step';assert selected.exists()
   plan[lib].update({'family_source_STEP':family.name,'local_STEP':selected.name,'sha256':sha(selected),'selected_variant_provenance':'usb120-model-provenance.json','classification':'selected1.20mm stake derivative; other family geometry unchanged'})
license=H.parent/'dock-control/DockControl.3dshapes/KiCad-LICENSE.md';assert license.exists();shutil.copyfile(license,OUT/'KiCad-LICENSE.md')
(H/'model-plan.json').write_text(json.dumps({'footprint_models':plan,'copper_only_footprints':missing,'no_PCB_or_footprint_mutation':True,'physical_validation':False},indent=2)+'\n')
print('Local STEP families',len(plan),'copper-only footprint types',missing)
