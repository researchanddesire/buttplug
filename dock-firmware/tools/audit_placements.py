#!/usr/bin/env python3
"""Read-only KiCad native pad audit; one BOARD per worker process."""
import argparse
import hashlib
import json
import math
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HARDWARE=ROOT.parent/'hardware/pcb/evt1/dock-control'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def one(board_path,xml_path):
    # KiCad's native macOS loader needs a wxApp even for read-only file access.
    import wx
    app=wx.App(False)
    import pcbnew as k
    before=sha(board_path)
    xml=ET.parse(xml_path).getroot();term={};expected={}
    for n in xml.findall('./nets/net'):
        for node in n.findall('node'):term[(node.get('ref'),node.get('pin'))]=n.get('name')
    for c in xml.findall('./components/comp'):
        footprint=c.findtext('footprint')
        if footprint:expected[c.get('ref')]=(footprint,c.findtext('value'))
    b=k.LoadBoard(str(board_path));assert b
    footprints={f.GetReference():f for f in b.GetFootprints()}
    assert len(footprints)==len(list(b.GetFootprints()))
    assert set(footprints)==set(expected),('PCB/source reference mismatch',set(footprints)^set(expected))
    checked=[];poses={}
    for ref,f in footprints.items():
        footprint,value=expected[ref]
        actual_id=str(f.GetFPID().GetLibNickname())+':'+str(f.GetFPID().GetLibItemName())
        assert actual_id==footprint,(ref,actual_id,footprint)
        assert f.GetValue()==value,(ref,f.GetValue(),value)
        numbers={p.GetNumber()for p in f.Pads()if p.GetNumber()}
        source_numbers={pin for (part,pin)in term if part==ref}
        assert numbers==source_numbers,(ref,numbers,source_numbers)
        for pad in f.Pads():
            number=pad.GetNumber()
            if not number:continue # Unnumbered NPTH features have no electrical contract.
            native=pad.GetNetname();wanted=term[(ref,number)]
            if wanted.startswith('unconnected-'):assert not native or native.startswith('unconnected-'),(ref,number,native)
            else:assert native==wanted,(ref,number,wanted,native)
            checked.append({'reference':ref,'pad':number,'net':native,
                'board_XY_mm':[k.ToMM(pad.GetPosition().x),k.ToMM(pad.GetPosition().y)]})
        if ref in ('J201','J301','J302'):
            x,y=k.ToMM(f.GetPosition().x),k.ToMM(f.GetPosition().y)
            angle=f.GetOrientationDegrees();r=math.radians(angle)
            pin1=next(p for p in f.Pads()if p.GetNumber()=='1')
            px=k.ToMM(pin1.GetPosition().x);py=k.ToMM(pin1.GetPosition().y)
            # All selected connector footprints explicitly use mouth+nativeY.
            mouth=[-math.sin(r),-math.cos(r)]
            desired=1 if ref in('J201','J301')else-1
            assert abs(mouth[0])<1e-6 and abs(mouth[1]-desired)<1e-6,(ref,mouth)
            assert (px-x)*desired>0,(ref,'pin1 wrong side',px-x)
            poses[ref]={'board_origin_XY_mm':[x,y],'angle_deg':angle,
                'dock_origin_XY_mm':[x-100,200-y],
                'dock_pin1_XY_mm':[px-100,200-py],
                'dock_mouth_vector_XY':mouth,
                'conductor_order':'pin1+X'if desired>0 else'pin1-X',
                'mating_contract':'J201p toJ301p'if desired>0 else'J302p toLCDp'}
    tracks=len(list(b.GetTracks()))
    assert sha(board_path)==before,'Board changed during native read-only audit'
    return {'PCB':str(board_path.relative_to(ROOT.parent)),'sha256':before,
        'source_XML':str(xml_path.relative_to(ROOT.parent)),'source_XML_sha256':sha(xml_path),
        'KiCad_native_version':k.GetBuildVersion(),'references_checked':len(footprints),
        'physical_pads_checked':len(checked),'pad_checks':checked,'connector_poses':poses,
        'tracks_and_vias':tracks,'pass':True}

def main():
    p=argparse.ArgumentParser();p.add_argument('--kicad-python');p.add_argument('--one',nargs=2);a=p.parse_args()
    if a.one:
        print(json.dumps(one(Path(a.one[0]),Path(a.one[1]))));return
    assert a.kicad_python,'Provide the installed KiCad Python executable'
    from check_contract import check
    check() # The native XML must still be bound to current controller sources.
    results=[]
    for name,xml in [('dock-controller-placement','dock-controller'),('dock-lid-placement','dock-lid-ui')]:
        args=[a.kicad_python,str(Path(__file__).resolve()),'--one',str(HARDWARE/(name+'.kicad_pcb')),str(HARDWARE/(xml+'-native.xml'))]
        r=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        if r.returncode:print(r.stderr);print(r.stdout);r.check_returncode()
        results.append(json.loads(r.stdout))
    out={'status':'pass: native PCB pad/source and connector direction audit',
         'pass':True,'boards':results,'physical_pads_checked':sum(r['physical_pads_checked']for r in results),
         'limits':['Controller PCB is the controller subset of the future shared base, with source/safety areas unpopulated.',
                   'Observed track/via counts do not establish routing, DRC acceptance or fabrication readiness.',
                   'Connector mouth/pin order follows the stated native board frame; socket actual mate depth/Z and physical continuity remain unqualified.',
                   'This is pad identity and nominal placement evidence, not PCB DRC acceptance or complete-part CAD fit.'],
         'physical_validation':False,'full_product_order_ready':False}
    (ROOT/'placement-review.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'status':out['status'],'physical_pads_checked':out['physical_pads_checked'],
      'references_checked':[r['references_checked']for r in results],
      'connector_poses':[r['connector_poses']for r in results]},indent=2))
if __name__=='__main__':main()
