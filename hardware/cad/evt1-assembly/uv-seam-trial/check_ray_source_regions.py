"""Read-only explanation of raw clear-ray origins; never removes findings."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'tools'))
import FreeCAD as App
import Part
import build_evt1_dock_uv_labyrinth as seam

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    raw_path=OUT/'native-checks.json';native=OUT/'UVSeamTrial.FCStd'
    raw=json.loads(raw_path.read_text());assert sha(native)==raw['native_SHA256']
    assert sha(Path(seam.__file__))==raw['builder_SHA256']
    doc=App.openDocument(str(native));root=doc.UVSeam
    assert abs(float(root.Parameters.OpeningAngle))<1e-8
    retainers=[(name,shape)for side in('lower','upper')for name,shape in seam.items(root,side)if name.endswith('Retainer')]
    clear=raw['closed_finite_ray_screen']['direct_clear_segment_findings']
    origins=sorted(set(tuple(row['interior_mm'])for row in clear));records=[]
    for origin in origins:
        end=(origin[0],20.,origin[2]);line=Part.makeLine(App.Vector(*origin),App.Vector(*end));blocks=[]
        for name,shape in retainers:
            common=line.common(shape)
            if common.Length>1e-6:
                blocks.append({'body':name,'material_length_mm':common.Length,'intersection_exact_bounds_mm':seam.bounds(common)})
        assert blocks,('Front-baffle interpretation not supported',origin)
        records.append({'raw_clear_ray_origin_mm':origin,'probe_toward_chamber_mm':end,'exact_retainer_intersections':blocks,
                        'geometric_interpretation':'Origin lies ahead of a rear catch baffle along dock+Y, in the front vestibule. This does not remove its clear exterior lines or prove optical containment.'})
    App.closeDocument(doc.Name)
    report={'builder_SHA256':sha(Path(__file__)),'frozen_geometry_helper_SHA256':sha(Path(seam.__file__)),'raw_native_checks_SHA256':sha(raw_path),'native_SHA256':sha(native),
            'raw_sampled_segments':raw['closed_finite_ray_screen']['sampled_segments'],'raw_clear_ray_count_retained':len(clear),'raw_clear_rays_retained':clear,
            'unique_clear_origin_count':len(origins),'source_region_evidence':records,
            'qualification':'All14 raw clear rays remain findings. Region evidence explains their origins ahead of the rear baffle. It is not an all-rays containment claim; reflection, scattering, material transmission and measured optical leakage remain open.',
            'optical_containment_qualified':False}
    (OUT/'ray-source-regions.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'raw_clear_rays_retained':len(clear),'origins_with_exact_baffle_evidence':len(records),'helper_unchanged':True,'optical_qualified':False}))
if __name__=='__main__':main()
