"""Actual selected footprint snapshots and primary RSV16 land geometry.

2D source authoring only. Installed RF/connector/3D poses require separate audit.
"""
from pathlib import Path
import hashlib,json,shutil
H=Path(__file__).resolve().parent;O=H/'case-radio';F=O/'Radio.pretty'
STOCK=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
MODELS=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    F.mkdir(parents=True,exist_ok=True);(O/'models').mkdir(exist_ok=True)
    names=[('Resistor_SMD','R_0402_1005Metric'),('Capacitor_SMD','C_0402_1005Metric'),
           ('Capacitor_SMD','C_0603_1608Metric'),('Capacitor_SMD','C_0805_2012Metric'),
           ('Connector_JST','JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal'),
           ('Package_DFN_QFN','HVQFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm'),
           ('Crystal','Crystal_SMD_Abracon_ABM8G-4Pin_3.2x2.5mm')]
    inputs={};modelrows=[]
    for library,name in names:
        src=STOCK/(library+'.pretty')/(name+'.kicad_mod');assert src.exists(),src
        inputs[str(src)]=sha(src);shutil.copyfile(src,F/src.name)
        # Exact stock family profiles are reputable dimensional geometry,
        # not OEM MPN qualification. Do not pretend they prove received fit.
        model=MODELS/(library+'.3dshapes')/(name+'.step')
        if model.exists():
            shutil.copyfile(model,O/'models'/model.name)
            modelrows.append({'family':name,'source_path':str(model),'sha256':sha(model),
                              'scope':'KiCad package-family solid; not OEM exact-MPN or tolerance acceptance'})
    src=H/'vendor/nina/OEM.pretty/NINA-B112_OEM.kicad_mod'
    shutil.copyfile(src,F/src.name);inputs[str(src)]=sha(src)
    # TI RSV0016A4220314C example. Native top-side numbering is important:
    # four contacts per side, pin16 elongated0.7; no exposed centre pad.
    name='TI_RSV0016A'
    lines=[f'(footprint "{name}" (version 20221018)(generator telemetry_primary_land)(layer "F.Cu")(attr smd)',
           '(descr "TMUX1511RSV16;TI4220314C example:15x0.6x0.2, pin16 0.7x0.2;row centres1.6x2.4mm;p0.4mm;noEP")',
           '(fp_text reference "REF**"(at 0 -2)(layer "F.SilkS")(effects(font(size .7 .7)(thickness .1))))',
           f'(fp_text value "{name}"(at 0 2)(layer "F.Fab")(effects(font(size .5 .5)(thickness .08))))',
           '(fp_rect(start -1.375 -1.825)(end 1.375 1.825)(layer "F.CrtYd")(width .05)(fill none))',
           '(fp_rect(start -.925 -1.325)(end .925 1.325)(layer "F.Fab")(width .05)(fill none))']
    pads=[]
    pads +=[(i+1,-.8,-.6+.4*i,.6,.2)for i in range(4)]
    pads +=[(i+5,-.6+.4*i,1.2,.2,.6)for i in range(4)]
    pads +=[(i+9,.8,.6-.4*i,.6,.2)for i in range(4)]
    pads +=[(i+13,.6-.4*i,-1.2,.2,.7 if i==3 else .6)for i in range(4)]
    for n,x,y,w,h in pads:
        lines.append(f'(pad "{n}" smd roundrect(at {x:.6f} {y:.6f})(size {w} {h})(layers "F.Cu" "F.Paste" "F.Mask")(roundrect_rratio .25))')
    lines.append(')');(F/(name+'.kicad_mod')).write_text('\n'.join(lines)+'\n')
    report={'status':'Selected native land patterns; no3D pose/installedRF/receivedtolerance acceptance',
            'builder_sha256':sha(Path(__file__)),'source_footprints_sha256':inputs,
            'selected_family_models':modelrows,
            'TI_RSV_primary_source':'https://www.ti.com/lit/ds/symlink/tmux1511.pdf RSV0016A4220314C',
            'TI_RSV_native_pad_centres_mm':{str(n):[x,y]for n,x,y,w,h in pads},
            'OEM_NINA_source':'vendor/nina/extraction.json; PIFA B112, not B111',
            'model_pose_binding_pending':True,
            'outputs_sha256':{p.name:sha(p)for p in F.glob('*.kicad_mod')}}
    (O/'footprint-provenance.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Nine selected native footprints; exactNINA+ABM8G family sources')


if __name__=='__main__':main()
