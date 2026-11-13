"""Fill the source block in a fresh process after its native save."""
from pathlib import Path
import hashlib,json
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent
p=H/'source-block.kicad_pcb';b=k.LoadBoard(str(p));b.BuildConnectivity()
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
m=json.loads((H/'placement.json').read_text());m['board_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
(H/'placement.json').write_text(json.dumps(m,indent=2)+'\n')
print('Filled native ground reference; rebound board hash',m['board_sha256'])
