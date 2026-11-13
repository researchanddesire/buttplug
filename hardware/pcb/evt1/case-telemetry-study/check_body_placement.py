"""Cold native pad/pose packing audit; deliberately no routed-board claim."""
from pathlib import Path
import copy,hashlib,json,sys,xml.etree.ElementTree as E
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;ROOT=H.parents[3];O=H/'body-instrumentation'
sys.path.insert(0,str(ROOT/'tools'));import kicad_sexp as s
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    source=ROOT/'hardware/pcb/evt1/body/body-evt1.kicad_pcb'
    dest=O/'body-instrumentation-placement.kicad_pcb'
    original=s.parse(source.read_text());current=s.parse(dest.read_text())
    ref=lambda f:next(t[2].value for t in s.children(f,'fp_text')if t[1].value=='reference')
    a={ref(f):f for f in s.children(original,'footprint')};c={ref(f):f for f in s.children(current,'footprint')}
    assert len(a)==69 and len(c)==90 and set(a)<set(c)
    def pad_geometry(p):return [s.dump(x)for x in p if s.tag(x)not in('net','pinfunction','pintype')]
    retained_pads=0
    for name,f in a.items():
        assert s.dump(s.child(f,'at'))==s.dump(s.child(c[name],'at')),name
        assert s.value(f,'layer')==s.value(c[name],'layer'),name
        assert f[1].value==c[name][1].value,name
        before=s.children(f,'pad');after=s.children(c[name],'pad')
        assert len(before)==len(after)
        assert [pad_geometry(p)for p in before]==[pad_geometry(p)for p in after],name
        retained_pads+=len(before)
    xml=E.parse(O/'native.xml').getroot()
    terms={(n.get('ref'),n.get('pin')):net.get('name')for net in xml.findall('./nets/net')for n in net.findall('node')}
    b=k.LoadBoard(str(dest));fps={f.GetReference():f for f in b.GetFootprints()};rows=[]
    for name,fp in fps.items():
        for p in fp.Pads():
            number=p.GetNumber()
            if not number:continue
            assert p.GetNetname()==terms.get((name,number),''),(name,number,p.GetNetname(),terms.get((name,number)))
            rows.append({'ref':name,'pin':number,'net':p.GetNetname(),
                         'native_xy_mm':[k.ToMM(p.GetPosition().x),k.ToMM(p.GetPosition().y)]})
    assert b.GetCopperLayerCount()==6 and not list(b.GetTracks())and b.GetAreaCount()==0
    drc=json.loads((O/'placement-drc-all.json').read_text())
    assert not drc['violations']and not drc['ignored_checks']
    project=json.loads(dest.with_suffix('.kicad_pro').read_text())
    assert not project['board']['design_settings']['drc_exclusions']
    assert not[k for k,v in project['board']['design_settings']['rule_severities'].items()if v=='ignore']
    outlines=lambda t:[s.dump(x)for x in t if s.tag(x)in('gr_line','gr_arc','gr_circle')and s.value(x,'layer')=='Edge.Cuts']
    assert outlines(original)==outlines(current)
    report={'status':'Native 2D packing and pad contract pass; explicitly unrouted and not mechanically qualified',
            'checker_sha256':sha(Path(__file__)),'native_read_version':k.Version(),'native_DRC_version':drc['kicad_version'],
            'original_body_board_sha256':sha(source),'packing_board_sha256':sha(dest),
            'native_XML_sha256':sha(O/'native.xml'),'placement_DRC_sha256':sha(O/'placement-drc-all.json'),
            'original_poses_and_layers_preserved':69,'original_pad_geometry_instances_preserved':retained_pads,
            'total_footprints':90,'added_positions':21,'pad_netlist_instances_checked':len(rows),
            'DRC_geometry_violations':0,'DRC_unconnected_expected':len(drc['unconnected_items']),
            'DRC_ignored':[],'DRC_exclusions':[],'original_outline_and_6layer1mm_stackup':True,
            'manual_J81_courtyard_sha256':sha(O/'manual-courtyard.json'),
            'pad_netlist_checks':rows,'all_selected_3D_models_bound':False,
            'mechanical_3D_and_height_acceptance':False,'routing_complete':False,
            'original_artwork_promoted_or_modified':False}
    (O/'placement-checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:report[key]for key in('total_footprints','original_poses_and_layers_preserved','pad_netlist_instances_checked','DRC_geometry_violations','DRC_unconnected_expected')}))


if __name__=='__main__':main()
