"""Read back actual native-exported STEP and record unambiguous MCAD planes."""
from pathlib import Path
import hashlib
import json
import sys
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for side in('base','lid'):
    folder=HERE/side/'pcb';path=folder/('dock-uv-'+side+'.step')
    shape=Part.Shape();shape.read(str(path))
    assert shape.isValid() and all(s.isValid() for s in shape.Solids)
    board=max(shape.Solids,key=lambda s:s.Volume);bb=board.BoundBox
    assert all(abs(a-b)<1e-6 for a,b in zip((bb.XMin,bb.YMin,bb.ZMin,bb.XMax,bb.YMax,bb.ZMax),(-49,86,0,49,135,.86)))
    electrodes=[s for s in shape.Solids if .81<s.Volume<.84]
    assert len(electrodes)==4
    assert all(abs(s.BoundBox.ZMin-.98)<1e-6 and abs(s.BoundBox.ZMax-1.18)<1e-6 for s in electrodes)
    assert abs(shape.BoundBox.ZMax-2.755)<1e-6,'LED optical direction/model rotation changed'
    checks=json.loads((folder/'pcb-checks.json').read_text())
    assert checks['board_sha256']==sha(folder/('dock-uv-'+side+'.kicad_pcb'))
    data={'status':'pass: actual STEP valid and selected LED terminal/optical planes verified',
        'board_file':'dock-uv-'+side+'.kicad_pcb','board_sha256':checks['board_sha256'],
        'STEP_file':path.name,'STEP_sha256':sha(path),'checker_sha256':sha(Path(__file__)),
        'valid_solid_count':len(shape.Solids),'core_bounds_mm':[bb.XMin,bb.YMin,bb.ZMin,bb.XMax,bb.YMax,bb.ZMax],
        'CLI_source_planar_origin_mm':[100,200],'CLI_STEP_planar_center_mm':[0,110.5],
        'CLI_STEP_F_copper_plane_Z_mm':.93,'CLI_STEP_B_copper_plane_Z_mm':-.07,
        'CLI_STEP_F_package_mount_Z_mm':.98,'CLI_STEP_B_package_mount_Z_mm':-.12,
        'CLI_STEP_LED_optical_top_Z_mm':2.755,'CLI_STEP_LED_active_optical_normal':[0,0,1],
        'CLI_STEP_solder_standoff_mm':.05,
        'CLI_STEP_to_dock_rigid_4x4':[[1,0,0,0],[0,1,0,0],[0,0,1,12.27],[0,0,0,1]]if side=='base'else[[-1,0,0,0],[0,1,0,0],[0,0,-1,56.23],[0,0,0,1]],
        'StepUp_expected_centered_Fplane0_to_dock_rigid_4x4':[[1,0,0,0],[0,1,0,110.5],[0,0,1,13.2],[0,0,0,1]]if side=='base'else[[-1,0,0,0],[0,1,0,110.5],[0,0,-1,55.3],[0,0,0,1]],
        'StepUp_note':'The centered StepUp convention must be checked after native import; do not apply it directly to this uncentered CLI STEP. Lid is Ry180, not a mirror; X-site references intentionally exchange.',
        'selected_models_manifest_sha256':sha(HERE/'models/source-manifest.json'),
        'remote_parts':'NTC and67L045 are not solder-mounted PCB bodies; their thermal attachment/retention is separate.',
        'physical_fit':False,'thermal_validation':False,'optical_validation':False}
    (folder/'mcad.json').write_text(json.dumps(data,indent=2)+'\n')
    print(side,len(shape.Solids),'valid solids; FterminalZ.98; optical+Z')
