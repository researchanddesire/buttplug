"""Cold-read the final saved physical geometry and bind the preview/report package."""
from pathlib import Path
import hashlib,json,sys
import FreeCAD as App
import Part
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT/'tools'))
import build_evt1_dock_recentered_carrier as m
from preview_geometry import fingerprint,same
H=m.OUT;native=H/'RecenteredCarrierTrial.FCStd';check=H/'native-checks.json'
r=json.loads(check.read_text());assert r['pass'] and r['source_hashes_unchanged']
assert r['builder_SHA256']==m.sha(Path(m.__file__)) and r['native_SHA256']==m.sha(native)
for row in r['source_inputs']:assert m.sha(row['path'])==row['SHA256'],('changed final input',row['path'])
d=App.openDocument(str(native));p=d.RecenteredContactModule;physical=m.physical_shapes(p)
assert len(physical)==15
preview=json.loads((H/'preview-input-binding.json').read_text());current={n:hashlib.sha256(s.cleaned().exportBrepToString().encode()).hexdigest()for n,s in physical}
assert preview['source_native_SHA256_at_export']==m.sha(native)
assert all(same(fingerprint(s),preview['physical_geometry_fingerprints'][n])for n,s in physical),'Preview source geometry changed'
preview['source_native_SHA256_after_final_validation']=m.sha(native)
preview['cold_saved_native_geometry_fingerprints_match_render_source']=True
preview['raw_BRep_text_signature_differences']=[n for n in current if current[n]!=preview['physical_clean_BRep_signatures'][n]]
preview['raw_BRep_text_signature_note']='Shared AppLink instance serialization IDs/order can differ across identical saved-native cold reads; native SHA and topology/area/volume/bounds/vertices plus edge and surface samples are checked to1e-7mm for presentation binding. No coil BOP waiver.'
preview['image_SHA256']={f:m.sha(H/f)for f in ('assembled-preview.png','exploded-rear-preview.png')}
(H/'preview-input-binding.json').write_text(json.dumps(preview,indent=2)+'\n')
for n,s in physical:assert s.isValid() and len(s.Solids)>0,n
assert all(s.FullyConstrained for s in d.Objects if s.TypeId=='Sketcher::SketchObject')
assert r['native_SHA256']==m.sha(native)
files=['README.md','integration-contract.json','RecenteredCarrierTrial.FCStd','native-checks.json',
       'check_trial.py','device_check.py','freeze_outputs.py','selected-coil-source.brp','selected-coil-bop-evidence.json',
       'negative-prefix-findings.json','negative-skin-collar-findings.json','liner-relief-13p1-ledged-probe.json',
       'export_preview_meshes.py','preview_geometry.py','render_preview.py','preview-input-binding.json','preview-meshes-render-source.json',
       'assembled-preview.png','exploded-rear-preview.png']
manifest={'scope':'Frozen isolated recentered carrier trial; no master/source artwork edits or physical release',
          'helper':str(Path(m.__file__)),'helper_SHA256':m.sha(Path(m.__file__)),
          'native_cold_read_valid_physical_components':len(physical),
          'native_cold_read_fully_constrained_sketches':True,
          'preview_matches_final_saved_native_geometry':True,
          'preview_geometry_binding_tolerance_mm':1e-7,
          'new_module_nominal_fit_pass':r['pass'],
          'whole_dock_with_device_pass':r['whole_dock_with_device_pass'],
          'all_component_BOP_checks_pass':r['all_component_BOP_checks_pass'],
          'coil_C0_exception_preserved':True,'received_or_physical_qualification':False,
          'source_inputs':r['source_inputs'],
          'files_SHA256':{f:m.sha(H/f)for f in files},
          'nonpackage_diagnostics':'Partial/failed logs, generated FCBak and pycache are not release inputs; unique negative findings are preserved in the named JSON files.'}
(H/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps({'cold_read_physical_components':len(physical),'native_SHA256':m.sha(native),'report_SHA256':m.sha(check),'manifest_SHA256':m.sha(H/'source-manifest.json'),'all_component_BOP_checks_pass':r['all_component_BOP_checks_pass']},indent=2),flush=True)
