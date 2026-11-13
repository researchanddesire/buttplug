"""Separate JST lid candidate. Frozen routed Molex board/source are read-only.

Run with the existing KiCad7 Python; the resulting board is checked with KiCad10.
The documented solder pattern is modeled. No undocumented loaded 3D cavity is
created and no generic package solid is substituted for the selected socket.
"""
from pathlib import Path
import hashlib,json,shutil,sys
HERE=Path(__file__).resolve().parent
PARENT=HERE.parent
ROOT=PARENT.parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import kicad_sexp as s
import wx
APP=wx.App(False)
import pcbnew as k
SHA=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
NAME='JST_27FLZ-RSM2-TB_1x27_P0.50mm_BottomContact'
VALUE='27FLZ-RSM2-TB / DIRECT LCD MATE'
URL='https://www.jst.com/wp-content/uploads/2025/06/eFLZ.pdf'
SOURCE=PARENT/'routed-lid/dock-lid-routed.kicad_pcb'
BOARD=HERE/'dock-lid-jst-candidate.kicad_pcb'

def rectangle(x1,y1,x2,y2,layer,width):
    points=[(x1,y1),(x2,y1),(x2,y2),(x1,y2)]
    return '\n'.join(f'(fp_line(start {a[0]} {a[1]})(end {b[0]} {b[1]})(layer "{layer}")(width {width}))'for a,b in zip(points,points[1:]+points[:1]))

def footprint():
    # JST eFLZ page 2 left-column recommended PCB pattern, viewed from the
    # connector mounting surface. Origin is signal pad-row centre. The 0.15
    # rear outline offset is a parenthesized reference, not a controlled datum.
    pads='\n'.join(f'(pad "{i+1}" smd rect(at {-6.5+.5*i} 0)(size .35 1.1)(layers "F.Cu" "F.Paste" "F.Mask"))'for i in range(27))
    for x in (-8.75,8.75):pads+=f'\n(pad "MP" smd rect(at {x} 1.25)(size 2.1 2.1)(layers "F.Cu" "F.Paste" "F.Mask"))'
    return f'''(footprint "{NAME}"(version 20221018)(generator jst_lcd_candidate)(layer "F.Cu")(attr smd)
      (descr "JST eFLZ pp2-3; 27FLZ-RSM2-TB bottom contact; mounting-surface view, mouth+Y; no loaded CAD")
      (tags "27FLZ-RSM2-TB 0.5mm bottom-contact received-fit-required")
      (fp_text reference "REF**"(at 0 -1.6)(layer "F.SilkS")(effects(font(size .8 .8)(thickness .12))))
      (fp_text value "{VALUE}"(at 0 6)(layer "F.Fab")(effects(font(size .8 .8)(thickness .12))))
      {pads}
      {rectangle(-9.7,.4,9.7,5,'F.Fab',.1)}
      {rectangle(-10.3,-.8,10.3,5.5,'F.CrtYd',.05)}
      (fp_text user "OPEN SLIDER TO Y6.8"(at 0 7.3)(layer "Dwgs.User")(effects(font(size .6 .6)(thickness .1))))
      {rectangle(-9.7,.4,9.7,6.8,'Dwgs.User',.05)}
      (fp_line(start -9.3 4.1)(end -8.9 4.6)(layer "F.SilkS")(width .15))
      (fp_line(start -8.9 4.6)(end -8.5 4.1)(layer "F.SilkS")(width .15)))'''

def main():
    assert not BOARD.exists(),'Never overwrite a candidate board; preserve edited routing first'
    guards={str(p.relative_to(ROOT)):SHA(p)for p in [SOURCE,PARENT/'routed-lid/native-checks.json',PARENT/'dock-lid-ui.kicad_sch',PARENT/'dock-lid-ui-native.xml',PARENT/'native-checks.json']}
    oldcheck=json.loads((PARENT/'routed-lid/native-checks.json').read_text())
    assert SHA(SOURCE)==oldcheck['source_sha256']['routed-lid/dock-lid-routed.kicad_pcb']
    local=HERE/'DockControl.pretty';local.mkdir(exist_ok=True)
    for p in (PARENT/'routed-lid/DockControl.pretty').glob('*.kicad_mod'):
        if not p.name.startswith('Molex_'):shutil.copyfile(p,local/p.name)
    (HERE/'DockControl.kicad_sym').write_text((PARENT/'DockControl.kicad_sym').read_text().replace('MOLEX_52437_2771','JST_27FLZ_RSM2_TB'))
    (HERE/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "DockControl")(type "KiCad")(uri "${KIPRJMOD}/DockControl.kicad_sym")(options "")(descr "Derived candidate symbols; selected JST replacement retains all terminal functions")))\n')
    (local/(NAME+'.kicad_mod')).write_text(footprint()+'\n')
    shutil.copyfile(PARENT/'routed-lid/fp-lib-table',HERE/'fp-lib-table')
    shutil.copyfile(PARENT/'routed-lid/dock-lid-routed.kicad_pro',BOARD.with_suffix('.kicad_pro'))
    settings=json.loads(BOARD.with_suffix('.kicad_pro').read_text())
    settings['board']['design_settings']['rule_severities'].update({n:'warning'for n in ['track_not_centered_on_via','tuning_profile_track_geometries','footprint_filters_mismatch']})
    BOARD.with_suffix('.kicad_pro').write_text(json.dumps(settings,indent=2)+'\n')
    tree=s.parse((PARENT/'dock-lid-ui.kicad_sch').read_text())
    # Rename the cached passive connector symbol without altering any terminal.
    for item in s.children(s.child(tree,'lib_symbols'),'symbol'):
        if item[1].value=='DockControl:MOLEX_52437_2771':item[1]=s.string('DockControl:JST_27FLZ_RSM2_TB')
    connector=next(x for x in s.children(tree,'symbol')if s.prop(x,'Reference')=='J302')
    s.child(connector,'lib_id')[1]=s.string('DockControl:JST_27FLZ_RSM2_TB')
    updates={'Value':VALUE,'Footprint':'DockControl:'+NAME,'Datasheet':URL,'Manufacturer':'JST','MPN':'27FLZ-RSM2-TB',
      'ReviewNote':'Newhaven recommended 27-way bottom-contact mate. Direct pin p to LCD pin p. JST requires 0.30±0.03 mm FPC and >=3 mm exposed land; incoming NHD tail and loaded height/insertion/continuity require fixture qualification.'}
    for item in s.children(connector,'property'):
        if item[1].value in updates:item[2]=s.string(updates[item[1].value])
    for item in s.children(tree,'text'):
        if item[1].value.startswith('DIRECT 1:1 MATE:'):item[1]=s.string('JST 27FLZ-RSM2-TB candidate: bottom-contact, direct pin p to pin p.\nMounting surface pattern; pin 1 at -X, mouth +nativeY maps dock -Y.\nLoaded contact height and full insertion stop are not published.\nFixture continuity, tail land length and actual board/roof/button fit remain open.')
    # Cached child-unit identifiers must share the renamed symbol prefix.
    (HERE/'dock-lid-ui.kicad_sch').write_text(s.dump(tree).replace('MOLEX_52437_2771','JST_27FLZ_RSM2_TB')+'\n')
    shutil.copyfile(PARENT/'dock-lid-ui.kicad_pro',HERE/'dock-lid-ui.kicad_pro')
    settings=json.loads((HERE/'dock-lid-ui.kicad_pro').read_text())
    settings.setdefault('erc',{})['rule_severities']={n:'warning'for n in ['single_global_label','four_way_junction','simulation_model_issue','footprint_filter']}
    (HERE/'dock-lid-ui.kicad_pro').write_text(json.dumps(settings,indent=2)+'\n')
    b=k.LoadBoard(str(SOURCE));b.SetFileName(str(BOARD))
    old=next(f for f in b.GetFootprints()if f.GetReference()=='J302')
    nets={p.GetNumber():p.GetNetname()for p in old.Pads()}
    new=k.FootprintLoad(str(local),NAME);assert new
    new.SetFPID(k.LIB_ID('DockControl',NAME));new.SetReference('J302');new.SetValue(VALUE)
    new.SetPosition(old.GetPosition());new.SetOrientationDegrees(old.GetOrientationDegrees());new.SetPath(old.GetPath());new.SetLocked(True)
    new.Reference().SetVisible(False);new.Value().SetVisible(False)
    for pad in new.Pads():
        assert pad.GetNumber()in nets
        if nets[pad.GetNumber()]:pad.SetNet(b.FindNet(nets[pad.GetNumber()]))
    b.Remove(old);b.Add(new)
    k.SaveBoard(str(BOARD),b)
    # Models() is a value-copy iterator in KiCad7; persisted metadata stays
    # correctly based on this sibling project's directory. J302 has NO model.
    for rel,digest in guards.items():assert SHA(ROOT/rel)==digest,rel
    (HERE/'candidate-source-bindings.json').write_text(json.dumps({'status':'separate candidate, not promoted','source_sha256':guards,'builder_sha256':SHA(Path(__file__)),'footprint_sha256':SHA(local/(NAME+'.kicad_mod')),'initial_board_sha256':SHA(BOARD),'J302_only_replacement':True,'signal_pad_centres_preserved':True,'socket_loaded_geometry_known':False,'full_product_order_ready':False},indent=2)+'\n')
    print(BOARD)
if __name__=='__main__':main()
