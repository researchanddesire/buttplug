"""Seed the routed candidate from the frozen43-footprint mechanical placement."""
from pathlib import Path
import argparse,hashlib,json,math,shutil,sys,xml.etree.ElementTree as ET
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;ROOT=H.parents[3];S=H.parent/'single-flange-study';sys.path.insert(0,str(ROOT/'tools'));import kicad_sexp as sx
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def xy(x,z):return k.VECTOR2I(round((100+x)*1e6),round((100-z)*1e6))
def keepout(b,x,z,r,layers,tracks):
 for layer in layers:
  zone=k.ZONE(b);zone.SetLayer(layer);zone.SetIsRuleArea(True);zone.SetDoNotAllowVias(True);zone.SetDoNotAllowTracks(tracks);zone.SetDoNotAllowCopperPour(tracks);zone.SetDoNotAllowPads(False);zone.SetDoNotAllowFootprints(False)
  poly=zone.Outline();poly.NewOutline();radius=r/math.cos(math.pi/64)
  for i in range(64):
   a=2*math.pi*i/64;p=xy(x+radius*math.cos(a),z+radius*math.sin(a));poly.Append(p.x,p.y)
  b.Add(zone)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--restart-placement',action='store_true');args=ap.parse_args();p=H/'single-flange.kicad_pcb'
 if p.exists():
  meta=json.loads((H/'pcb-state.json').read_text());assert not meta.get('routing_started'), 'Never overwrite routed edits';assert args.restart_placement and sha(p)==meta['board_sha256']
 checks=json.loads((H/'schematic-checks.json').read_text());assert checks['status'].startswith('pass')and checks['merged_XML_sha256']==sha(H/'single-flange-native.xml')
 frozen=json.loads((S/'native-checks.json').read_text());assert sha(S/'single-flange-placement.kicad_pcb')==frozen['board_sha256'];shutil.copyfile(S/'single-flange-placement.kicad_pcb',p)
 project=H/'single-flange.kicad_pro';settings=json.loads(project.read_text());b=k.LoadBoard(str(p));b.SetFileName(str(p));b.GetDesignSettings().SetAuxOrigin(xy(0,0))
 ds=b.GetDesignSettings();ds.m_MinClearance=k.FromMM(.15);ds.m_TrackMinWidth=k.FromMM(.15);ds.m_MinThroughDrill=k.FromMM(.2);ds.m_ViasMinSize=k.FromMM(.5);ds.m_HoleClearance=k.FromMM(.2);ds.m_CopperEdgeClearance=k.FromMM(.3)
 default=ds.m_NetSettings.m_DefaultNetClass;default.SetClearance(k.FromMM(.15));default.SetTrackWidth(k.FromMM(.15));default.SetViaDiameter(k.FromMM(.5));default.SetViaDrill(k.FromMM(.2))
 r=ET.parse(H/'single-flange-native.xml').getroot();comps={c.get('ref'):c for c in r.findall('./components/comp')};nets={(q.get('ref'),q.get('pin')):n.get('name')for n in r.findall('./nets/net')for q in n.findall('node')};fps={f.GetReference():f for f in b.GetFootprints()}
 assert set(fps)==set(comps)|{'MH1','MH2','MH3','MH4'} and not list(b.GetTracks())
 for ref,c in comps.items():
  f=fps[ref];assert f.GetValue()==c.findtext('value');assert str(f.GetFPID().GetLibNickname())+':'+str(f.GetFPID().GetLibItemName())==c.findtext('footprint');assert f.IsLocked()
  f.SetPath(k.KIID_PATH(c.find('sheetpath').get('tstamps')+c.findtext('tstamps')))
  for pad in f.Pads():
   n=pad.GetNumber()
   if (ref,n)in nets:assert pad.GetNetname()==nets[ref,n]
   else:assert n=='MP';pad.SetNetCode(0)
 for x,z in[(-30,-10),(-38,10),(38,-10),(38,10)]:keepout(b,x,z,1.75,(k.F_Cu,k.B_Cu),True)
 for x in(-16,-10,-4,2):keepout(b,x,10,2,(k.F_Cu,k.In1_Cu,k.In2_Cu,k.B_Cu),False)
 k.SaveBoard(str(p),b)
 settings['net_settings']['classes'][0].update(clearance=.15,track_width=.15,via_diameter=.5,via_drill=.2)
 rules=settings['board']['design_settings']['rules'];rules.update(min_clearance=.15,min_track_width=.15,min_hole_clearance=.2,min_hole_to_hole=.25,min_copper_edge_clearance=.3,min_through_hole_diameter=.2,min_via_diameter=.5,min_via_annular_width=.1)
 settings['board']['design_settings']['rule_severities'].update({key:'warning'for key in('track_not_centered_on_via','tuning_profile_track_geometries','footprint_filters_mismatch')})
 for key,value in settings['board']['design_settings']['rule_severities'].items():
  if value=='ignore':settings['board']['design_settings']['rule_severities'][key]='error'
 settings['board']['design_settings']['drc_exclusions']=[];project.write_text(json.dumps(settings,indent=2)+'\n')
 # Nominal proposed1mm finished envelope, including nominal10um mask each.
 # Fabricator must qualify actual laminate/impedance/thickness; not a release.
 tree=sx.parse(p.read_text());setup=sx.child(tree,'setup');old=sx.child(setup,'stackup')
 if old:setup.remove(old)
 setup.insert(1,sx.parse('''(stackup
 (layer "F.SilkS"(type "Top Silk Screen"))(layer "F.Paste"(type "Top Solder Paste"))
 (layer "F.Mask"(type "Top Solder Mask")(thickness .01))
 (layer "F.Cu"(type "copper")(thickness .035))
 (layer "dielectric 1"(type "prepreg")(thickness .10)(material "FR4 candidate")(epsilon_r 4.2)(loss_tangent .02))
 (layer "In1.Cu"(type "copper")(thickness .035))
 (layer "dielectric 2"(type "core")(thickness .64)(material "FR4 candidate")(epsilon_r 4.2)(loss_tangent .02))
 (layer "In2.Cu"(type "copper")(thickness .035))
 (layer "dielectric 3"(type "prepreg")(thickness .10)(material "FR4 candidate")(epsilon_r 4.2)(loss_tangent .02))
 (layer "B.Cu"(type "copper")(thickness .035))
 (layer "B.Mask"(type "Bottom Solder Mask")(thickness .01))
 (layer "B.Paste"(type "Bottom Solder Paste"))(layer "B.SilkS"(type "Bottom Silk Screen"))
 (copper_finish "ENIG candidate")(dielectric_constraints no))'''))
 sx.write(p,tree)
 meta={'board_sha256':sha(p),'frozen_study_board_sha256':frozen['board_sha256'],'frozen_study_checks_sha256':sha(S/'native-checks.json'),'merged_XML_sha256':sha(H/'single-flange-native.xml'),'full_schematic_checks_sha256':sha(H/'schematic-checks.json'),'routing_started':False,'fixed_electrical_refs':39,'fixed_NPTH_mounts':4,'outline_product_XZ_mm':json.loads((S/'placement.json').read_text())['outline_product_XZ_mm'],'source_protection':'All43 footprint poses/pads/models/outline/thickness remain frozen; changes limited to new paths, stackup and routing constraints.','stackup_candidate_mm':{'Fmask':.01,'Fcu':.035,'prepreg1':.1,'In1GND':.035,'core':.64,'In2powerSignal':.035,'prepreg2':.1,'Bcu':.035,'Bmask':.01},'fabricator_stackup_or_USB_acceptance':False}
 (H/'pcb-state.json').write_text(json.dumps(meta,indent=2)+'\n');print('Native fixed-placement seed',sha(p))
if __name__=='__main__':main()
