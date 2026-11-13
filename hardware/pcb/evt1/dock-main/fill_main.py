"""Fill the continuous inner ground reference in a separate native process."""
from pathlib import Path
import json
import hashlib
import wx
APP=wx.App(False)
import pcbnew as k
HERE=Path(__file__).resolve().parent
path=HERE/'dock-main.kicad_pcb'
board=k.LoadBoard(str(path));assert board.GetCopperLayerCount()==4
meta=json.loads((HERE/'placement.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(path)==meta['native_board_sha256'],'Preserve edits before filling a different board'
# Retained power-zone fill caches must not propagate their old net into a
# newly inserted free stitching via before the new clearance is computed.
for zone in list(board.Zones()):
    if not zone.GetIsRuleArea():zone.UnFill()
    if not zone.GetIsRuleArea() and zone.GetNetname()=='GND':board.Delete(zone)
repairs=[]
for report in (HERE/'routing').glob('ground-stitches-*.json'):
    for row in json.loads(report.read_text())['added']:
        matches=[t for t in board.GetTracks()if t.m_Uuid.AsString()==row['uuid']]
        assert len(matches)==1
        via=matches[0]
        if via.GetNetname()!='GND':
            repairs.append({'uuid':row['uuid'],'prior_net':via.GetNetname(),'intended_net':'GND','native_mm':row['native_mm']})
            via.SetNet(board.FindNet('GND'))
intended_nets={t.m_Uuid.AsString():t.GetNetname()for t in board.GetTracks()}

for layer in (k.In1_Cu,k.F_Cu,k.B_Cu):
    zone=k.ZONE(board);zone.SetLayer(layer);zone.SetNet(board.FindNet('GND'))
    zone.SetLocalClearance(k.FromMM(.2));zone.SetMinThickness(k.FromMM(.15))
    zone.SetPadConnection(k.ZONE_CONNECTION_FULL if layer==k.In1_Cu else k.ZONE_CONNECTION_THERMAL)
    zone.SetThermalReliefGap(k.FromMM(.2));zone.SetThermalReliefSpokeWidth(k.FromMM(.25))
    zone.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
    polygon=zone.Outline();polygon.NewOutline()
    for x,y in meta['outline_dock_xy_mm']:
        polygon.Append(k.FromMM(100+x),k.FromMM(200-y))
    board.Add(zone)
board.BuildConnectivity();k.ZONE_FILLER(board).Fill(board.Zones())
assert {t.m_Uuid.AsString():t.GetNetname()for t in board.GetTracks()}==intended_nets,'Native refill changed an authored copper net'
k.SaveBoard(str(path),board)
if repairs:
    (HERE/'routing/ground-stitch-net-repair.json').write_text(json.dumps({'before_board_sha256':meta['native_board_sha256'],'repaired_own_new_vias_only':repairs,'all_other_copper_nets_and_geometry_preserved':True,'all_fill_caches_cleared_before_connectivity':True,'result_board_sha256':sha(path)},indent=2)+'\n')

meta['native_board_sha256']=sha(path);meta['ground_reference_filled']=True
(HERE/'placement.json').write_text(json.dumps(meta,indent=2)+'\n')
if meta.get('routing_started') and not meta.get('general_routing_imported'):
    critical=json.loads((HERE/'critical-routing.json').read_text())
    critical['board_sha256']=sha(path)
    (HERE/'critical-routing.json').write_text(json.dumps(critical,indent=2)+'\n')
print('Filled main inner GND plus surface reference pours')
