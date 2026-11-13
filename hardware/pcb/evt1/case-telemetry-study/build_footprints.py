"""Selected-body instrumentation land patterns from actual primary drawings.

These are editable 2D PCB footprints. They are not OEM3D models or a physical
packing acceptance. Manufacturer solder-mask/stencil examples require supplier
review, especially the0.22mm DTM centre lands.
"""
from pathlib import Path
import hashlib,json,shutil

H=Path(__file__).resolve().parent
O=H/'body-instrumentation/Telemetry.pretty'
STOCK=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    O.mkdir(exist_ok=True)
    inputs={}
    for lib,name in [('Resistor_SMD','R_0402_1005Metric'),('Capacitor_SMD','C_0402_1005Metric')]:
        src=STOCK/(lib+'.pretty')/(name+'.kicad_mod')
        shutil.copyfile(src,O/src.name);inputs[str(src)]=sha(src)
    # DCK0005A example: lands0.95x0.4,2.2mm across rows,0.65pitch.
    # Pin1..3 left top->bottom;4..5 right bottom->top, top-side view.
    name='SOT-353_SC-70-5'
    lines=[f'(footprint "{name}"(version 20221018)(generator telemetry_primary_land)(layer "F.Cu")(attr smd)',
           '(descr "TI DCK0005A example board layout:0.95x0.4 lands,2.2row spacing,0.65pitch;3D not supplied")',
           '(fp_text reference "REF**"(at 0 -2)(layer "F.SilkS")(effects(font(size .8 .8)(thickness .12))))',
           f'(fp_text value "{name}"(at 0 2)(layer "F.Fab")(effects(font(size .6 .6)(thickness .1))))']
    for layer,x,y in [('F.CrtYd',1.825,1.45),('F.Fab',.7,1.2)]:
        lines.append(f'(fp_rect(start {-x} {-y})(end {x} {y})(layer "{layer}")(width .05)(fill none))')
    for n,x,y in [(1,-1.1,-.65),(2,-1.1,0),(3,-1.1,.65),(4,1.1,.65),(5,1.1,-.65)]:
        lines.append(f'(pad "{n}" smd roundrect(at {x} {y})(size .95 .4)(layers "F.Cu" "F.Paste" "F.Mask")(roundrect_rratio .125))')
    lines.append(')');(O/(name+'.kicad_mod')).write_text('\n'.join(lines)+'\n')
    # DTM0008A top-side land view, not the mirrored package-bottom view.
    # Outer lands use primary45deg inner-corner cuts; roundradius0.05.
    name='TI_DTM0008A'
    lines=[f'(footprint "{name}"(version 20221018)(generator telemetry_primary_land)(layer "F.Cu")(attr smd)',
           '(descr "TI DTM0008A4224755B land example:6x0.42x0.2; row0.78/pitch0.5;2x0.22square45deg centresy+/-0.27; primary chamfers")',
           '(fp_text reference "REF**"(at 0 -1.2)(layer "F.SilkS")(effects(font(size .7 .7)(thickness .1))))',
           f'(fp_text value "{name}"(at 0 1.2)(layer "F.Fab")(effects(font(size .5 .5)(thickness .08))))',
           '(fp_rect(start -.8 -.9)(end .8 .9)(layer "F.CrtYd")(width .05)(fill none))',
           '(fp_rect(start -.425 -.7)(end .425 .7)(layer "F.Fab")(width .05)(fill none))']
    for n,x,y,ratio,corners in [(1,-.39,-.5,.5,'bottom_right'),(2,-.39,0,.395,'top_right bottom_right'),
                              (3,-.39,.5,.5,'top_right'),(5,.39,.5,.5,'top_left'),
                              (6,.39,0,.395,'top_left bottom_left'),(7,.39,-.5,.5,'bottom_left')]:
        lines.append(f'(pad "{n}" smd roundrect(at {x} {y})(size .42 .2)(layers "F.Cu" "F.Paste" "F.Mask")(roundrect_rratio .25)(chamfer_ratio {ratio})(chamfer {corners}))')
    for n,y in [(8,-.27),(4,.27)]:
        lines.append(f'(pad "{n}" smd roundrect(at 0 {y} 45)(size .22 .22)(layers "F.Cu" "F.Paste" "F.Mask")(roundrect_rratio .2272727273))')
    lines.append(')');(O/(name+'.kicad_mod')).write_text('\n'.join(lines)+'\n')
    report={'status':'Native 2D land patterns only; no3D/package/tolerance acceptance',
            'builder_sha256':sha(Path(__file__)), 'copied_passive_library_inputs_sha256':inputs,
            'primary_sources':{'DCK':'https://www.ti.com/lit/ds/symlink/opa391.pdf DCK0005A board layout4214834G',
                               'DTM':'https://www.ti.com/lit/ds/symlink/tca9536.pdf DTM0008A board layout4224755B'},
            'DCK_pad_centres_mm':{'1':[-1.1,-.65],'2':[-1.1,0],'3':[-1.1,.65],'4':[1.1,.65],'5':[1.1,-.65]},
            'DTM_pad_centres_mm':{'1':[-.39,-.5],'2':[-.39,0],'3':[-.39,.5],'4':[0,.27],'5':[.39,.5],'6':[.39,0],'7':[.39,-.5],'8':[0,-.27]},
            'not_claimed':['OEM3D','paste release','solder-mask registration','fabricator DFM','native3D/mechanical packing'],
            'outputs_sha256':{p.name:sha(p)for p in sorted(O.glob('*.kicad_mod'))}}
    (H/'body-instrumentation/footprint-provenance.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Four selected land patterns ready')


if __name__=='__main__':main()
