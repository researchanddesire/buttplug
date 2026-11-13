"""Intentional boost/sense copper, bounded offline routing and native pours."""
from pathlib import Path
import argparse
import json
import math
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import build_pcbs as m
k=m.k
sys.path.insert(0,str(m.ROOT/'tools'))
import kicad_sexp as s

def ctx(side):
    folder=m.HERE/side/'pcb';path=folder/('dock-uv-'+side+'.kicad_pcb')
    b=k.LoadBoard(str(path));return folder,path,b

def critical(side):
    folder,path,b=ctx(side);r=json.loads((folder/'placement.json').read_text())
    assert m.sha(path)==r['board_sha256'] and not list(b.GetTracks()),'Preserve existing routes first'
    base=400 if side=='base' else 500;prefix=side.upper()
    ref=lambda letter,n=1:letter+str(base+n)
    fps={f.GetReference():f for f in b.GetFootprints()}
    def pad(letter,pin,n=1):
        return m.dock(next(p for p in fps[ref(letter,n)].Pads() if p.GetNumber()==str(pin)).GetPosition())
    def t(net,pts,layer=k.B_Cu,width=.4):m.track(b,net,pts,layer,width)
    def v(net,point):m.via(b,net,point)
    sw=prefix+'_SW';fb=prefix+'_FB_RAW';comp=prefix+'_COMP'
    # Short fixed SW triangle. No long SW trace reaches the other emitter.
    t(sw,[pad('L',2),(-43.45,104.5),pad('U',3)],width=.5)
    t(sw,[pad('U',3),(-44.35,106.3625),pad('D',2)],width=.5)
    # Input inductor/IC triangle on the same face, adjacent local bypass.
    t('UV_5V_SW',[pad('L',1),(-40.65,105.4625),pad('U',1)],width=.5)
    t('UV_5V_SW',[pad('C',1),(-39.125,104.525),pad('L',1)],width=.6)
    # Output rectifier to capacitor, separated from the feedback path.
    t(prefix+'_VOUT',[pad('D',1),pad('C',1,2)],width=.7)
    t(prefix+'_VOUT',[pad('C',1,2),(-44.5,pad('C',1,2)[1]),(-44.5,95.5),(-44.6,95.5)],width=.6)
    # Compensation and Kelvin current feedback are fixed before general routing.
    t(comp,[pad('U',5),(-42.5,109.8),(-45.775,109.8),pad('C',1,3)],width=.25)
    t(fb,[pad('U',6),(-41.55,110.5),pad('R',1)],width=.25)
    t(fb,[pad('R',1),(-42.4125,113.6),(-39.4,113.6),pad('Q',2)],width=.4)
    for pp,end in [(pad('R',2),(-40.1,110.9)),(pad('U',4),(-44.5,108.8)),(pad('C',2,3),(-44.3,113.5))]:
        t('GND',[pp,end],width=.3);v('GND',end)
    # A low-resistance power trunk is reinforced by the F.Cu UV5V zone later.
    power_via=(pad('J',1)[0],131.6);cap_via=(-38,102.3)
    t('UV_5V_SW',[pad('J',1),power_via],width=.4);v('UV_5V_SW',power_via)
    t('UV_5V_SW',[power_via,(-38,131.6),cap_via],k.F_Cu,.6)
    v('UV_5V_SW',cap_via)
    t('UV_5V_SW',[cap_via,pad('C',1)],width=.6)
    # All GH contacts escape outside their reflow lands; no unfilled via-in-pad.
    for pin in range(2,9):
        pp=pad('J',pin);end=(pp[0],131.1)
        net=next(p.GetNetname() for p in fps[ref('J')].Pads() if p.GetNumber()==str(pin))
        t(net,[pp,end],width=.25);v(net,end)
    gx=pad('J',2)[0]
    t('GND',[(gx,131.1),(gx,133.4)],width=.25)
    t('GND',[(gx,133.4),(-40.5,133.4),(-40.5,128.3)],width=2.4)
    # Thermal stitches use the actual LED terminal nets; never tie them to GND.
    for n,x in((2,-42),(3,42)):
        for pin,sign in((1,1),(2,-1)):
            net=next(p.GetNetname() for p in fps[ref('D',n)].Pads() if p.GetNumber()==str(pin))
            for y in(92.5,94,95.5):
                point=(x+sign*2.6,y);v(net,point)
                t(net,[(x+sign*1.8,94),point],k.F_Cu,.4)
    # Long DC series/cathode paths run around the U, never across its opening.
    mid=prefix+'_LED_MID'
    t(mid,[(-39.4,95.5),(-35.8,99.1),(-35.8,128.6),(35.8,128.6),(35.8,99.1),(39.4,95.5)],k.F_Cu,.4)
    cathode=prefix+'_LED_K'
    t(cathode,[(44.6,95.5),(47,97.9),(47,125),(42.5,125),(40.8,126.7),(40.8,133.4),(-40.8,133.4),(-40.8,114.5)],k.F_Cu,.4)
    v(cathode,(-40.8,114.5))
    t(cathode,[(-40.8,114.5),(-35.9,114.5),(-35.9,112.1625),pad('Q',3)],width=.4)
    # Prevent additional signal routes directly beneath the B-side SW loop.
    z=k.ZONE(b);z.SetLayer(k.F_Cu);z.SetIsRuleArea(True)
    z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowCopperPour(False)
    z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False)
    poly=z.Outline();poly.NewOutline()
    for q in[(-48,102),(-42.8,102),(-42.8,108),(-48,108)]:
        p=m.xy(*q);poly.Append(p.x,p.y)
    b.Add(z)
    for item in b.GetTracks():item.SetLocked(True)
    m.save(b,path)
    (folder/'critical.kicad_pcb').write_bytes(path.read_bytes())
    assert k.ExportSpecctraDSN(b,str(path.with_suffix('.dsn')))
    # Filled planes are native final-board artifacts; autoroute the remaining
    # terminal connections, preserving all fixed critical tracks/holes.
    (folder/'critical.json').write_text(json.dumps({'board_sha256':m.sha(path),'placement_sha256':r['board_sha256'],'router_tool_sha256':m.sha(Path(__file__)),'fixed_route_objects':len(list(b.GetTracks()))},indent=2)+'\n')
    print('critical',side,len(list(b.GetTracks())))

def import_session(side):
    folder,path,b=ctx(side)
    critical=json.loads((folder/'critical.json').read_text())
    assert m.sha(path)==critical['board_sha256'],'Preserve edited board before importing routes'
    session=s.parse(path.with_suffix('.ses').read_text());routes=s.child(session,'routes')
    assert [a.value for a in s.child(routes,'resolution')[1:]]==['um','10']
    def point(a,c):return k.VECTOR2I(k.FromMM(float(a.value)/10000),k.FromMM(-float(c.value)/10000))
    for net in s.children(s.child(routes,'network_out'),'net'):
        name=net[1].value;assert b.FindNet(name),name
        for e in net[2:]:
            if s.tag(e)=='wire':
                p=s.child(e,'path');layer=k.F_Cu if p[1].value=='F.Cu'else k.B_Cu
                assert p[1].value in('F.Cu','B.Cu')
                points=[point(a,c)for a,c in zip(p[3::2],p[4::2])]
                for a,c in zip(points,points[1:]):
                    if any(not isinstance(t,k.PCB_VIA) and t.GetNetname()==name and t.GetLayer()==layer and ((t.GetStart()==a and t.GetEnd()==c)or(t.GetStart()==c and t.GetEnd()==a))for t in b.GetTracks()):continue
                    t=k.PCB_TRACK(b);t.SetStart(a);t.SetEnd(c);t.SetWidth(k.FromMM(float(p[2].value)/10000));t.SetLayer(layer);t.SetNet(b.FindNet(name));b.Add(t)
            elif s.tag(e)=='via':
                dims=re.fullmatch(r'Via\[0-1\]_(\d+):(\d+)_um',e[1].value);assert dims,e[1].value
                pp=point(e[2],e[3])
                if any(isinstance(t,k.PCB_VIA)and t.GetPosition()==pp for t in b.GetTracks()):continue
                v=k.PCB_VIA(b);v.SetPosition(pp);v.SetWidth(k.FromMM(float(dims[1])/1000));v.SetDrill(k.FromMM(float(dims[2])/1000))
                v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.FindNet(name));b.Add(v)
            else:raise ValueError(s.tag(e))
    m.save(b,path);print('imported',side,len(list(b.GetTracks())))

def fill(side):
    folder,path,b=ctx(side);prefix=side.upper()
    for z in list(b.Zones()):
        if not z.GetIsRuleArea():b.Delete(z)
    for layer in(k.F_Cu,k.B_Cu):
        m.zone(b,'GND',m.OUTLINE,layer)
        for x,n in((-42,2),(42,3)):
            f=next(f for f in b.GetFootprints()if f.GetReference()=='D'+str((400 if side=='base'else 500)+n))
            for pin,sign in((1,1),(2,-1)):
                net=next(p.GetNetname()for p in f.Pads()if p.GetNumber()==str(pin))
                xa,xb=(x+.25,x+5.8)if sign==1 else(x-5.8,x-.25)
                m.zone(b,net,[(xa,91.5),(xb,91.5),(xb,97),(xa,97)],layer,20)
    m.zone(b,'UV_5V_SW',[(-39.5,102.3),(-36.5,102.3),(-36.5,129.7),(5.5,129.7),(5.5,132.7),(-39.5,132.7)],k.F_Cu,10)
    b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());m.save(b,path);print('filled',side)

def restart(side):
    folder=m.HERE/side/'pcb';path=folder/('dock-uv-'+side+'.kicad_pcb')
    report=json.loads((folder/'critical.json').read_text())
    assert m.sha(path)==report['board_sha256'],'Only the unchanged generated critical candidate can restart'
    archive=Path('/private/tmp/compass-uv-layout-archive');archive.mkdir(exist_ok=True)
    shutil.copy2(path,archive/(side+'-critical-'+m.sha(path)+'.kicad_pcb'))
    path.unlink();m.place(side)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('action',choices=['critical','import','fill','restart']);ap.add_argument('side',choices=['base','lid']);a=ap.parse_args()
    {'critical':critical,'import':import_session,'fill':fill,'restart':restart}[a.action](a.side)
