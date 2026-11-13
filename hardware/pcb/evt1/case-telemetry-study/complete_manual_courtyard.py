"""Represent J81's existing explicit wire reservation in the new packing seed.

The original body copper/artwork/library remain read-only. This corrects missing
non-electrical courtyard metadata only in the separate candidate and its local
library snapshot; it is not an inherited-check waiver.
"""
from pathlib import Path
import hashlib,json,shutil,sys
H=Path(__file__).resolve().parent;ROOT=H.parents[3];O=H/'body-instrumentation'
sys.path.insert(0,str(ROOT/'tools'));import kicad_sexp as s
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
P=O/'body-instrumentation-placement.kicad_pcb'


def main():
    assert sha(P)=='4de1aa8291d38b7e9c39ac86307dc720f93e69a566dbcd50008d8d9fd08f54e3'
    original=ROOT/'hardware/pcb/evt1/body/body-evt1.kicad_pcb';oldsha=sha(original)
    tree=s.parse(P.read_text());fps=s.children(tree,'footprint')
    f=next(f for f in fps if any(t[1].value=='reference'and t[2].value=='J81'for t in s.children(f,'fp_text')))
    assert f[1].value=='EVT1:Sensor_Loom_4Land'
    assert s.dump(s.child(f,'at'))=='(at 91.3 90 90)'
    pads=[s.dump(p)for p in s.children(f,'pad')]
    source=ROOT/'hardware/pcb/evt1/EVT1.pretty'
    shutil.copytree(source,O/'EVT1.pretty',dirs_exist_ok=True)
    libpath=O/'EVT1.pretty/Sensor_Loom_4Land.kicad_mod'
    lib=s.parse(libpath.read_text())
    assert not any(s.value(x,'layer')=='F.CrtYd'for x in lib if isinstance(x,list))
    # Source mcad.json explicitly reserves bodyX−9.2..−8.2,Y39.5..45.
    # J81 is atnative91.3,90,90deg, so that is localX−.5..5,Y±.5.
    rect=s.parse('(fp_rect(start -.5 -.5)(end 5 .5)(layer "F.CrtYd")(width .05)(fill none))')
    lib.append(rect);f.append(s.parse(s.dump(rect)))
    s.write(libpath,lib);s.write(P,tree)
    assert pads==[s.dump(p)for p in s.children(f,'pad')]
    table=s.parse((O/'fp-lib-table').read_text())
    e=next(x for x in s.children(table,'lib')if s.value(x,'name')=='EVT1')
    s.child(e,'uri')[1]=s.string('${KIPRJMOD}/EVT1.pretty');s.write(O/'fp-lib-table',table)
    assert sha(original)==oldsha
    r=json.loads((O/'placement.json').read_text());r['candidate_board_sha256']=sha(P)
    r['J81_non_electrical_metadata_delta']='Added existing source wire-access rectangle as courtyard in candidate/local library; all69retained poses and all original pad geometry/nets preserved.'
    r['manual_courtyard_source_sha256']=sha(ROOT/'hardware/pcb/evt1/body/mcad.json')
    (O/'placement.json').write_text(json.dumps(r,indent=2)+'\n')
    report={'status':'Bounded new-candidate courtyard completion; original artwork unchanged',
            'builder_sha256':sha(Path(__file__)),'source_library_footprint_sha256':sha(source/libpath.name),
            'candidate_library_footprint_sha256':sha(libpath),'candidate_board_sha256':sha(P),
            'original_body_artwork_sha256':oldsha,'J81_pose_native':[91.3,90,90],
            'source_wire_access_body_XY_mm':[-9.2,39.5,-8.2,45],
            'candidate_courtyard_local_XY_mm':[-.5,-.5,5,.5],
            'all_original_pad_tokens_preserved':True,'no_ignored_rule_or_waiver_added':True}
    (O/'manual-courtyard.json').write_text(json.dumps(report,indent=2)+'\n')
    print(report['candidate_board_sha256'])


if __name__=='__main__':main()
