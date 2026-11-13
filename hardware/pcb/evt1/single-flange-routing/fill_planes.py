from pathlib import Path
import json,hashlib
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;p=H/'single-flange.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=json.loads((H/'pcb-state.json').read_text());assert sha(p)==m['board_sha256'];project=H/'single-flange.kicad_pro';pro=project.read_bytes();b=k.LoadBoard(str(p))
for z in list(b.Zones()):
 if not z.GetIsRuleArea():z.UnFill();b.Delete(z)
intended={t.m_Uuid.AsString():t.GetNetname()for t in b.GetTracks()}
for layer in(k.In1_Cu,k.In2_Cu,k.B_Cu):
 z=k.ZONE(b);z.SetLayer(layer);z.SetNet(b.FindNet('GND'));z.SetLocalClearance(k.FromMM(.15));z.SetMinThickness(k.FromMM(.15));z.SetPadConnection(k.ZONE_CONNECTION_FULL if layer==k.In1_Cu else k.ZONE_CONNECTION_THERMAL);z.SetThermalReliefGap(k.FromMM(.2));z.SetThermalReliefSpokeWidth(k.FromMM(.25));z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS);poly=z.Outline();poly.NewOutline()
 for x,y in m['outline_product_XZ_mm']:poly.Append(round((100+x)*1e6),round((100-y)*1e6))
 b.Add(z)
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());assert {t.m_Uuid.AsString():t.GetNetname()for t in b.GetTracks()}==intended,'Fill changed an authored net'
k.SaveBoard(str(p),b);project.write_bytes(pro);m['board_sha256']=sha(p);m['planes_filled']=True;(H/'pcb-state.json').write_text(json.dumps(m,indent=2)+'\n');print('Filled In1 continuousGND plus In2/B returns')
