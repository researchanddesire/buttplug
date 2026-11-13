"""Independent read-only peer audit of the separately owned routed lid."""
from pathlib import Path
import collections,hashlib,json,xml.etree.ElementTree as ET
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;C=H.parent/'dock-control';D=C/'routed-lid'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def xy(p):return [round(k.ToMM(p.x)-100,6),round(200-k.ToMM(p.y),6)]
def main():
 before=sha(D/'dock-lid-routed.kicad_pcb');report=json.loads((D/'native-checks.json').read_text())
 for rel,d in report['source_sha256'].items():assert sha(C/rel)==d,('stale lid binding',rel)
 for rel,d in report['reports_sha256'].items():assert sha(D/rel)==d
 drc=json.loads((D/'drc.json').read_text());assert not drc['violations'] and not drc['unconnected_items']
 project=json.loads((D/'dock-lid-routed.kicad_pro').read_text());assert not project['board']['design_settings']['drc_exclusions']
 assert not any(x=='ignore'for x in project['board']['design_settings']['rule_severities'].values())
 xml=ET.parse(C/'dock-lid-ui-native.xml').getroot();nets={};expected={}
 for n in xml.findall('./nets/net'):
  for p in n.findall('node'):nets[p.get('ref'),p.get('pin')]=n.get('name')
 for c in xml.findall('./components/comp'):
  if c.findtext('footprint'):expected[c.get('ref')]=c
 b=k.LoadBoard(str(D/'dock-lid-routed.kicad_pcb'));assert b.GetCopperLayerCount()==4
 fps={f.GetReference():f for f in b.GetFootprints()};electrical={r:f for r,f in fps.items()if r in expected}
 assert len(electrical)==28 and len(fps)==32
 checked=[]
 for r,c in sorted(expected.items()):
  f=fps[r];assert str(f.GetFPID().GetLibNickname())+':'+str(f.GetFPID().GetLibItemName())==c.findtext('footprint')
  assert f.GetValue()==c.findtext('value')
  assert {p.GetNumber()for p in f.Pads()if p.GetNumber()}=={n for rr,n in nets if rr==r}
  for p in f.Pads():
   n=p.GetNumber()
   if n:
    assert p.GetNetname()==nets[r,n],(r,n,p.GetNetname(),nets[r,n])
    checked.append([r,n,p.GetNetname(),xy(p.GetPosition())])
 assert len(checked)==109
 # Independent frame reasoning: mouth+nativeY ->dock-Y at0deg; the LCD
 # fold aboutX leaves pin1 at-X. No second numbering flip is introduced.
 for r,angle,origin,first_x in [('J302',0,[0,114],-6.5),('J301',180,[25,113],29.75)]:
  f=fps[r];assert xy(f.GetPosition())==origin and f.GetOrientationDegrees()==angle
  one=next(p for p in f.Pads()if p.GetNumber()=='1');assert xy(one.GetPosition())[0]==first_x
 assert next(p for p in fps['J302'].Pads()if p.GetNumber()=='1').GetNetname()=='LCD_V0'
 assert next(p for p in fps['J302'].Pads()if p.GetNumber()=='27').GetNetname()=='LCD_CSn'
 for r,x in [('S301',-22),('S302',0),('S303',22)]:assert xy(fps[r].GetPosition())==[x,54]
 mechanical=[]
 for r,f in fps.items():
  if r in electrical:continue
  ps=list(f.Pads());assert len(ps)==1;p=ps[0]
  assert p.GetAttribute()==k.PAD_ATTRIB_NPTH and round(k.ToMM(p.GetDrillSize().x),6)==2.3
  assert p.IsOnLayer(k.F_Mask) and p.IsOnLayer(k.B_Mask)
  mechanical.append([r,xy(p.GetPosition()),2.3])
 assert not any(not isinstance(t,k.PCB_VIA)and t.GetLayer()==k.In1_Cu for t in b.GetTracks())
 assert before==sha(D/'dock-lid-routed.kicad_pcb')
 out={'status':'PASS: independent saved routed-lid source/pad/connector/mount audit',
      'board_sha256':before,'native_source_XML_sha256':sha(C/'dock-lid-ui-native.xml'),
      'peer_report_sha256':sha(D/'native-checks.json'),'physical_pad_checks':checked,
      'electrical_references':28,'physical_electrical_pad_instances':109,'mechanical_mounts':mechanical,
      'native_DRC_violations':0,'native_DRC_unconnected':0,'rule_exclusions':0,'ignored_rule_severities':0,
      'LCD_order':'J302p toLCDp direct; folded pin1 remainsdock-X',
      'primary_reference':'Molex SD-52437-019 RevF mounting-side drawing independently reviewed previously',
      'PCB_modified_by_review':False,'powered_or_physical_mate_result':False}
 (H/'peer-lid-review.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({a:out[a]for a in('status','board_sha256','electrical_references','physical_electrical_pad_instances','native_DRC_violations','native_DRC_unconnected')}))
if __name__=='__main__':main()
