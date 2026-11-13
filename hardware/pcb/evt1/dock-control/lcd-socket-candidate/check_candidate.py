"""Independent saved-native pad/copper audit against original and derived XML."""
from pathlib import Path
import collections,datetime,hashlib,json,sys,xml.etree.ElementTree as ET
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;P=H.parent;R=P.parents[3]
sys.path.insert(0,str(R/'tools'));import kicad_sexp as s
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
board=H/'dock-lid-jst-candidate.kicad_pcb';start=sha(board)
bindings=json.loads((H/'candidate-source-bindings.json').read_text())
for rel,want in bindings['source_sha256'].items():assert sha(R/rel)==want,rel
fullbind=json.loads((H/'system-snapshot/source-bindings.json').read_text())
for rel,want in fullbind['source_sha256'].items():assert sha(R/rel)==want,rel
def netmap(path):
    x=ET.parse(path).getroot()
    pins={(n.get('ref'),n.get('pin')):(net.get('name'),n.get('pintype'),n.get('pinfunction'))for net in x.findall('./nets/net')for n in net.findall('node')}
    comps={c.get('ref'):c for c in x.findall('./components/comp')}
    return pins,comps
old,oldparts=netmap(P/'dock-lid-ui-native.xml');new,newparts=netmap(H/'dock-lid-ui-native.xml')
assert old==new,'Lid electrical terminals or functions changed'
origfull,of=netmap(P.parent/'dock-system/native.xml');full,nf=netmap(H/'system-snapshot/native.xml')
assert origfull==full,'Complete system terminal graph changed'
assert set(of)==set(nf)and set(oldparts)==set(newparts)
for r,c in oldparts.items():
    if r!='J302':assert c.findtext('value')==newparts[r].findtext('value')and c.findtext('footprint')==newparts[r].findtext('footprint'),r
d=json.loads((H/'drc.json').read_text());assert not d['violations']and not d['unconnected_items']and not d['ignored_checks']
e=json.loads((H/'system-snapshot/erc.json').read_text());assert not[v for sh in e['sheets']for v in sh['violations']]and not e['ignored_checks']
assert not json.loads(board.with_suffix('.kicad_pro').read_text())['board']['design_settings']['drc_exclusions']
frozen=s.parse((P/'routed-lid/dock-lid-routed.kicad_pcb').read_text());current=s.parse(board.read_text())
def ref(fp):return next(t[2].value for t in s.children(fp,'fp_text')if t[1].value=='reference')
a={ref(f):f for f in s.children(frozen,'footprint')};c={ref(f):f for f in s.children(current,'footprint')}
assert set(a)==set(c)
for r,f in a.items():
    assert s.dump(s.child(f,'at'))==s.dump(s.child(c[r],'at')),(r,'moved')
    if r!='J302':
        assert s.dump(f)==s.dump(c[r]),(r,'changed footprint')
def uid(n):return s.value(n,'tstamp')or s.value(n,'uuid')
oldcopper={uid(n):n for n in frozen if s.tag(n)in ['segment','via','arc']}
newcopper={uid(n):n for n in current if s.tag(n)in ['segment','via','arc']}
assert oldcopper.keys()==newcopper.keys()
changes=[]
for u,node in oldcopper.items():
    n=newcopper[u]
    if s.dump(node)==s.dump(n):continue
    # Exactly one supply via and its incident track endpoints may move +0.1X.
    assert s.value(node,'net')==s.value(n,'net')
    changed=False
    for tag in ['at','start','end']:
        x=s.child(node,tag);y=s.child(n,tag)
        if x is None:continue
        if s.dump(x)!=s.dump(y):
            assert [float(v.value)for v in x[1:3]]==[106.8,85.175]
            assert [float(v.value)for v in y[1:3]]==[106.9,85.175]
            clone=list(y);clone[1:3]=x[1:3];assert s.dump(clone)==s.dump(x)
            changed=True
    assert changed
    def remainder(q):return [s.dump(v)for v in q if s.tag(v)not in ['at','start','end']]
    assert remainder(node)==remainder(n)
    changes.append(u)
assert len(changes)==6,changes
def keepouts(t):return collections.Counter(s.dump(z)for z in s.children(t,'zone')if s.child(z,'keepout'))
assert keepouts(frozen)==keepouts(current),'FFC/hardware keepouts changed'
assert [s.dump(x)for x in s.children(frozen,'gr_line')]==[s.dump(x)for x in s.children(current,'gr_line')],'Outline changed'
b=k.LoadBoard(str(board));assert b.GetCopperLayerCount()==4
fps={f.GetReference():f for f in b.GetFootprints()};rows=[]
for r,fp in sorted(fps.items()):
    if r.startswith('H3'):continue
    part=newparts[r]
    assert fp.GetValue()==part.findtext('value')
    assert str(fp.GetFPID().GetLibNickname())+':'+str(fp.GetFPID().GetLibItemName())==part.findtext('footprint'),r
    for p in fp.Pads():
        n=p.GetNumber()
        if not n:continue
        assert p.GetNetname()==(new.get((r,n),('',None,None))[0]or''),(r,n,p.GetNetname())
        rows.append({'ref':r,'pin':n,'net':p.GetNetname(),'native_xy_mm':[k.ToMM(p.GetPosition().x),k.ToMM(p.GetPosition().y)]})
assert len(rows)==109
j=fps['J302'];assert len(list(j.Pads()))==29 and not list(j.Models())
for p in j.Pads():
    n=p.GetNumber();x=k.ToMM(p.GetPosition().x)-100;y=k.ToMM(p.GetPosition().y)-86
    if n=='MP':assert abs(abs(x)-8.75)<1e-8 and abs(y-1.25)<1e-8 and abs(k.ToMM(p.GetSizeX())-2.1)<1e-8
    else:
        assert abs(x-(-6.5+.5*(int(n)-1)))<1e-8 and abs(y)<1e-8
        assert abs(k.ToMM(p.GetSizeX())-.35)<1e-8 and abs(k.ToMM(p.GetSizeY())-1.1)<1e-8
assert all(isinstance(t,k.PCB_VIA)or t.GetLayer()!=k.In1_Cu for t in b.GetTracks())
assert sha(board)==start
files=[p for p in H.rglob('*')if p.is_file()and p.suffix not in ['.pyc','.kicad_prl']and p.name!='native-checks.json'and '__pycache__'not in p.parts]
out={'status':'pass: separate JST board electrical candidate; physical socket fit OPEN','checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'KiCad_DRC_version':d['kicad_version'],'KiCad_ERC_version':e['kicad_version'],'native_board_sha256':start,'physical_electrical_pad_instances':len(rows),'lid_unchanged_logical_terminal_checks':len(new),'whole_system_unchanged_terminal_checks':len(full),'whole_system_components':len(nf),'native_DRC_violations':0,'native_DRC_unconnected':0,'native_DRC_ignored':[],'complete_system_ERC_violations':0,'complete_system_ERC_ignored':[],'fixed_placements_outline_keepouts_preserved':True,'changed_copper_objects':changes,'local_copper_delta':'Only supply via(6.8,114.825)→(6.9,114.825) dockXY and its five incident endpoints; all other tracks/vias unchanged; zones refilled','J302_loaded_3D_model_bound':False,'native_pin_net_checks':rows,'source_sha256':{str(p.relative_to(H)):sha(p)for p in files},'manufacturer_number1_legend_available':False,'received_continuity_tail_and_height_required':True,'complete_MCAD_or_physical_fit_qualified':False,'full_product_order_ready':False}
(H/'native-checks.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps({k:out[k]for k in ['status','native_board_sha256','physical_electrical_pad_instances','lid_unchanged_logical_terminal_checks','whole_system_unchanged_terminal_checks','native_DRC_violations','complete_system_ERC_violations']}))
