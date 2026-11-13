"""Read the actual KiCad10 J302-only STEP export and check its physical pose.

Export command (KiCad10.0.8): pcb export step --force --no-board-body
--component-filter J302 --user-origin 100x86mm --no-extra-pad-thickness.
KiCad10 uses its own body/copper placement and fixed0.05mm BOARD_OFFSET.
This check measures the actual separately exported board body, then compares
both full OEM solids after the software placement. That fixed export offset is
not a selected solder or loaded-contact-height datum. StepUp has its own frame.
"""
from pathlib import Path
import hashlib,json,sys
import FreeCAD as App
import Part
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
OUT=ROOT/'hardware/pcb/evt1/dock-control/routed-lid'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def bounds(shape):
    b=shape.optimalBoundingBox(False,False)
    return [getattr(b,k)for k in ('XMin','YMin','ZMin','XMax','YMax','ZMax')]

def main():
    pcb=OUT/'dock-lid-routed.kicad_pcb';model=HERE/'Molex524372771ClosedBoardFrame.step'
    exported=HERE/'KiCad10J302Pose.step'
    binding=json.loads((OUT/'lcd-socket-model-binding.json').read_text())
    assert sha(pcb)==binding['board_after_model_binding_SHA256']
    assert sha(model)==binding['model_SHA256']
    board_export=HERE/'KiCad10BoardDatum.step'
    board=Part.read(str(board_export));board_bounds=bounds(board)
    assert board.isValid()and len(board.Solids)==1
    assert abs(board_bounds[2])<1e-7 and abs(board_bounds[5]-.91)<1e-7
    # Primary10.0.8 getModelLocation(): bodytop + F_Cu thickness + BOARD_OFFSET.
    # Board has no released physical stackup; these are actual exporter defaults.
    software_h=board_bounds[5]+.035+.05
    assert abs(software_h-.995)<1e-7
    shape=Part.read(str(exported));source=Part.read(str(model))
    assert shape.isValid()and len(shape.Solids)==2 and len(shape.Faces)==1001
    wanted=[-10.05,-5.1,software_h-.04,10.05,.1,software_h+2]
    assert all(abs(a-b)<1e-6 for a,b in zip(bounds(shape),wanted)),(bounds(shape),wanted)
    rows=[]
    for src in source.Solids:
        matches=[s for s in shape.Solids if len(s.Faces)==len(src.Faces)and abs(s.Volume-src.Volume)<1e-6]
        assert len(matches)==1
        got=matches[0];placed=src.copy();placed.translate(App.Vector(0,0,software_h))
        assert all(abs(a-b)<1e-6 for a,b in zip(bounds(got),bounds(placed)))
        common=got.common(placed).Volume
        assert abs(common-got.Volume)<1e-6 and abs(common-placed.Volume)<1e-6
        rows.append({'faces':len(got.Faces),'volume_mm3':got.Volume,'exact_bounds_mm':bounds(got),
                     'full_BRep_common_with_expected_pose_mm3':common})
    tails=[]
    for f in shape.Faces:
        t=f.Surface;b=bounds(f)
        if isinstance(t,Part.Plane)and abs(t.Axis.z)>.999 and abs(t.Position.z-software_h-.14)<1e-7:
            if abs(b[3]-b[0]-.2)<1e-7 and abs(b[1]+.4)<1e-7 and abs(b[4]-.1)<1e-7:
                tails.append([(b[0]+b[3])/2,(b[1]+b[4])/2,software_h+.14])
    tails.sort();assert len(tails)==27
    for i,p in enumerate(tails):assert abs(p[0]-(-6.5+.5*i))<1e-7
    report={'board_SHA256':sha(pcb),'model_SHA256':sha(model),'actual_KiCad_exported_pose_valid':True,
            'native_exporter':'KiCad10.0.8 pcb export step,component-filterJ302/no-board-body/user-origin100x86mm/no-extra-pad-thickness',
            'actual_export_file':str(exported.relative_to(ROOT)),'actual_export_SHA256':sha(exported),
            'board_datum_export_file':str(board_export.relative_to(ROOT)),'board_datum_export_SHA256':sha(board_export),
            'actual_exported_board_body_bounds_mm':board_bounds,
            'checker_file':str(Path(__file__).resolve().relative_to(ROOT)),'checker_SHA256':sha(Path(__file__)),
            'actual_export_solids':2,'actual_export_faces':1001,'actual_full_BRep_pose_checks':rows,
            'actual_export_pin1_tail_top_centre_mm':tails[0],'actual_export_pin27_tail_top_centre_mm':tails[-1],
            'actual_tail_pitch_mm':.5,'actual_tail_count':27,'exported_software_model_H_datum_Z_mm':software_h,
            'KiCad_software_BOARD_OFFSET_mm':.05,'KiCad_export_F_Cu_thickness_mm':.035,
            'software_offset_is_physical_solder_or_contact_datum':False,
            'primary_exporter_source':'https://gitlab.com/kicad/code/kicad/-/raw/10.0.8/pcbnew/exporters/step/step_pcb_model.cpp',
            'primary_code_functions':['getBoardBodyZPlacement','getModelLocation; BOARD_OFFSET0.05 + outercopperthickness'],
            'board_frame_normalized_pin1_tail_top_centre_mm':[-6.5,-.15,.14],
            'physical_board_mouth_vector':[0,-1,0],'native_footprint_mouth_vector':[0,1],
            'model_to_board_front_offset_mm':[0,0,0],'model_rotation_deg':[0,0,0],
            'loaded_contact_plane_and_received_mating_qualified':False,'StepUp_assembly_import_checked':False,
            'FreeCAD_version':App.Version()}
    (OUT/'lcd-socket-native-pose.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'actual_KiCad_J302_export':'pose valid','solids':2,'actual_terminal_count':27,'loaded_contact_height_qualified':False}))

if __name__=='__main__':main()
