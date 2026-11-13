"""Read-only native PCB/source/geometry audit; one board per process."""
from pathlib import Path
import collections
import json
import math
import subprocess
import sys
import xml.etree.ElementTree as ET
import build_pcbs as m
from route_pcbs import ctx
k=m.k
sys.path.insert(0,str(m.ROOT/'tools'))
import kicad_sexp as s

def rectangles(f,layers):
    boxes=[g.GetBoundingBox()for g in f.GraphicalItems()if isinstance(g,k.PCB_SHAPE)and g.GetLayer()in layers]
    if not boxes:return None
    corners=[m.dock(p)for bb in boxes for p in(bb.GetOrigin(),bb.GetEnd())]
    return[min(q[0]for q in corners),min(q[1]for q in corners),max(q[0]for q in corners),max(q[1]for q in corners)]

def gap(point,box):return math.hypot(max(box[0]-point[0],0,point[0]-box[2]),max(box[1]-point[1],0,point[1]-box[3]))

def main(side):
    folder,path,b=ctx(side);before=m.sha(path)
    cli='/private/tmp/compass-kicad10/mount/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
    version=subprocess.check_output([cli,'--version'],text=True).strip()
    assert version=='10.0.8',version
    run=subprocess.run([cli,'pcb','drc','--format','json','--exit-code-violations','-o',str(folder/'native-drc.json'),str(path)],capture_output=True,text=True)
    assert run.returncode==0,(run.stdout,run.stderr)
    assert m.sha(path)==before,'Native DRC changed the saved PCB'
    project=json.loads(path.with_suffix('.kicad_pro').read_text())
    assert not project.get('board',{}).get('design_settings',{}).get('drc_exclusions',[])
    report=json.loads((folder/'native-drc.json').read_text())
    assert not report['violations'] and not report['unconnected_items']
    source=m.HERE/side;manifest=json.loads((source/'parts-selection.json').read_text())
    frozen=json.loads((source/'native-checks.json').read_text())
    for rel,h in frozen['source_sha256'].items():assert m.sha(source/rel)==h,rel
    tree=ET.parse(source/'native.xml').getroot()
    netmap={(n.get('ref'),n.get('pin')):net.get('name')for net in tree.findall('./nets/net')for n in net.findall('node')}
    expected={p['reference']:p for p in manifest['parts']if not p['offboard']}
    fps={f.GetReference():f for f in b.GetFootprints()};base=400 if side=='base'else 500
    assert set(fps)==set(expected)|{'H'+str(base+i)for i in range(1,5)}
    padcount=0;bodychecks=0;padchecks=0;placed=[]
    for ref,p in expected.items():
        f=fps[ref];assert f.GetValue()==p['value'];assert str(f.GetFPID().GetLibItemName())==p['footprint'].split(':')[1]
        sourcefp=k.FootprintLoad(str(source/'DockUV.pretty'),p['footprint'].split(':')[1])
        assert collections.Counter(q.GetNumber()for q in sourcefp.Pads())==collections.Counter(q.GetNumber()for q in f.Pads()),ref
        for q in f.Pads():
            assert q.GetNetname()==netmap[ref,q.GetNumber()],(ref,q.GetNumber(),q.GetNetname())
            bb=q.GetBoundingBox();a,c=m.dock(bb.GetOrigin()),m.dock(bb.GetEnd());box=[a[0],c[1],c[0],a[1]]
            for hole in m.MOUNTS:assert gap(hole,box)>=3-.01,(ref,q.GetNumber(),'hardware',hole,box)
            padcount+=1;padchecks+=4
        for layers in[(k.F_Fab,k.B_Fab),(k.F_CrtYd,k.B_CrtYd)]:
            box=rectangles(f,layers)
            if box:
                for hole in m.MOUNTS:assert gap(hole,box)>=3-.05,(ref,'body/courtyard hardware',hole,box)
                bodychecks+=4
        if not ref.startswith('TP'):assert len(f.Models())==1,ref
        placed.append({'reference':ref,'value':f.GetValue(),'side':'B'if f.GetLayer()==k.B_Cu else'F','angle_deg':f.GetOrientationDegrees(),'xy_mm':m.dock(f.GetPosition()),
            'pads':[{'number':q.GetNumber(),'net':q.GetNetname(),'xy_mm':m.dock(q.GetPosition())}for q in f.Pads()],
            'fab_bounds_mm':rectangles(f,(k.F_Fab,k.B_Fab)),'models':[str(x.m_Filename)for x in f.Models()]})
    for i,position in enumerate(m.MOUNTS,1):
        f=fps['H'+str(base+i)];assert m.dock(f.GetPosition())==position
        pads=list(f.Pads());assert len(pads)==1 and abs(k.ToMM(pads[0].GetDrillSize().x)-2.2)<1e-6
    assert b.GetCopperLayerCount()==2 and abs(k.ToMM(b.GetDesignSettings().GetBoardThickness())-1)<1e-6
    routes=[]
    for t in b.GetTracks():
        if isinstance(t,k.PCB_VIA):routes.append({'kind':'via','net':t.GetNetname(),'point':m.dock(t.GetPosition()),'diameter':k.ToMM(t.GetWidth()),'drill':k.ToMM(t.GetDrillValue())})
        else:routes.append({'kind':'track','net':t.GetNetname(),'layer':b.GetLayerName(t.GetLayer()),'start':m.dock(t.GetStart()),'end':m.dock(t.GetEnd()),'width':k.ToMM(t.GetWidth())})
    # Original fixed local boost/sense copper is preserved. The documented
    # input-feed improvement is checked separately; low-speed fanout repairs
    # are intentionally outside this protected scope.
    critical=s.parse((m.HERE/'base/pcb/critical.kicad_pcb').read_text())
    names={int(n[1].value):n[2].value for n in s.children(critical,'net')}
    protected={'BASE_SW','BASE_COMP','BASE_FB_RAW'}
    existing={(r['net'].replace('LID','BASE'),r.get('layer'),tuple(sorted([tuple(r['start']),tuple(r['end'])])),round(r['width'],6))for r in routes if r['kind']=='track'}
    fixed=0
    for t in s.children(critical,'segment'):
        net=names[int(s.value(t,'net'))]
        if net not in protected:continue
        a=s.child(t,'start');c=s.child(t,'end')
        point=lambda n:(round(float(n[1].value)-100,6),round(200-float(n[2].value),6))
        sig=(net,s.value(t,'layer'),tuple(sorted([point(a),point(c)])),round(float(s.value(t,'width')),6))
        assert sig in existing,('Fixed boost/sense route changed',sig);fixed+=1
    boardtree=s.parse(path.read_text());stack=s.child(s.child(boardtree,'setup'),'stackup')
    thicknesses={n[1].value:float(s.value(n,'thickness'))for n in s.children(stack,'layer')if s.child(n,'thickness')}
    assert abs(thicknesses['F.Cu']-.07)<1e-9 and abs(thicknesses['B.Cu']-.07)<1e-9
    assert abs(thicknesses['dielectric 1']-.86)<1e-9
    assert m.sha(path)==before
    sourcefiles={path.name:m.sha(path),path.with_suffix('.kicad_pro').name:m.sha(path.with_suffix('.kicad_pro')),
        'fp-lib-table':m.sha(folder/'fp-lib-table'),'native-drc.json':m.sha(folder/'native-drc.json')}
    sourcefiles.update({str(p.relative_to(folder)):m.sha(p)for p in(folder/'DockUV.pretty').glob('*.kicad_mod')})
    result={'status':'pass: native DRC0/0, complete selected pad/net parity, hardware clearance and protected boost/sense copper',
        'board_sha256':before,'native_kicad_DRC_version':version,'DRC_exclusions':[],'source_sha256':sourcefiles,
        'schematic_native_xml_sha256':m.sha(source/'native.xml'),'schematic_native_checks_sha256':m.sha(source/'native-checks.json'),
        'selected_parts_sha256':m.sha(source/'parts-selection.json'),'checker_sha256':m.sha(Path(__file__)),
        'onboard_source_positions':len(expected),'mechanical_holes':4,'physical_source_pads_checked':padcount,
        'pad_hardware_checks':padchecks,'body_and_courtyard_hardware_checks':bodychecks,'protected_route_segments':fixed,
        'track_objects':len(routes),'via_count':sum(r['kind']=='via'for r in routes),'DRC_violations':0,'unconnected_items':0,
        'stackup_mm':thicknesses,'placements':placed,'routes':routes,
        'outline':{'extremes_planar_mm':[-49,86,49,135],'arms_inner_X_mm':[-35,35],'rear_crossbar_front_Y_mm':128,'inner_mill_radius_mm':1,'mounts':m.MOUNTS},
        'physical_fit':False,'powered_validation':False,'thermal_validation':False,'full_product_order_ready':False}
    (folder/'pcb-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({key:result[key]for key in('status','onboard_source_positions','mechanical_holes','physical_source_pads_checked','protected_route_segments','track_objects','via_count')},indent=2))

if __name__=='__main__':main(sys.argv[1])
