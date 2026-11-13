"""Source-bound conservative cell masks of actual saved native filled copper.

Engineering DC sheet study, not physical voltage-drop qualification. Tracks
outside the selected plane and other parallel layers are deliberately omitted.
"""
from pathlib import Path
import argparse,hashlib,json,math,re
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;P=H/'dock-main.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def pos(x,y):return k.VECTOR2I(round((100+x)*1e6),round((200-y)*1e6))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--grid',type=float,default=.2);ap.add_argument('--label',default='');a=ap.parse_args();h=a.grid
 assert re.fullmatch(r'[a-z0-9_-]*',a.label)
 assert .05<=h<=.25;b=k.LoadBoard(str(P));folder=H/'power-study'/a.label;folder.mkdir(exist_ok=True)
 settings={
 'HOST':('HOST_5V',k.In2_Cu,(-40,-4,46,31),[[-2.4,3.5],[2.4,3.5]],{'VIN':[[21.9,23]]}),
 'UV':('UV_5V_SW',k.In2_Cu,(28,26,48,65),[[32.7,27.8],[32.7,28.6]],{'BASE':[[30.375,58],[30.375,58.6]],'LID':[[45.275,61.3],[45.275,61.9]]}),
 'GND':('GND',k.In1_Cu,(-48,-4,48,68),[[-3.2,3.5],[3.2,3.5]],{'BASE':[[29.125,58],[29.125,58.6]],'LID':[[44.025,61.3],[44.025,61.9]]})}
 reports=[]
 for name,(net,layer,bounds,feed,outputs)in settings.items():
  zone=next(z for z in b.Zones()if not z.GetIsRuleArea()and z.IsOnLayer(layer)and z.GetNetname()==net)
  polys=zone.GetFilledPolysList(layer);x0,y0,x1,y1=bounds;nx=math.ceil((x1-x0)/h);ny=math.ceil((y1-y0)/h)
  mask=[];centres=[];corner=h/2-1e-6
  for iy in range(ny):
   line=[]
   for ix in range(nx):
    x=x0+(ix+.5)*h;y=y0+(iy+.5)*h
    keep=all(polys.Contains(pos(x+dx,y+dy),-1,0,True)for dx,dy in((0,0),(-corner,-corner),(corner,-corner),(-corner,corner),(corner,corner)))
    line.append('1'if keep else'0');centres.append((x,y))
   mask.append(''.join(line))
  def patch(points):
   result=[];radius=.25-h/math.sqrt(2)
   for px,py in points:
    found=[i for i,(x,y)in enumerate(centres)if mask[i//nx][i%nx]=='1'and math.hypot(x-px,y-py)<=radius+1e-8]
    assert found,('No fully inside via-contact cells; refine grid',name,px,py,h)
    result.extend(found)
   return sorted(set(result))
  source=patch(feed)
  for target,points in outputs.items():
   sink=patch(points);path=folder/(name+'-'+target+'-'+str(h)+'.grid')
   path.write_text(f'{nx} {ny} {h} {len(source)} {len(sink)}\n'+' '.join(map(str,source))+'\n'+' '.join(map(str,sink))+'\n'+'\n'.join(mask)+'\n')
   reports.append({'name':name+'-'+target,'file':path.name,'grid_mm':h,'sha256':sha(path),'net':net,'layer':k.LayerName(layer),'feed_vias_dock_mm':feed,'sink_vias_dock_mm':points,'feed_cell_groups':[patch([p])for p in feed],'sink_cell_groups':[patch([p])for p in points],'kept_full_copper_cells':sum(row.count('1')for row in mask)})
 before=sha(P);out={'board_sha256':before,'mesh_rule':'retain cell only if allfourcorners+centre are in actual fillednativecopper; omitotherparallelcopper','contact_rule':'equipotential patches fit fully within selected0.5mm via annuli outerdiameter; barrel resistance added separately','grids':reports,'physical_validation':False}
 (folder/('grid-'+str(h)+'.json')).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'board_sha256':before,'grids':len(reports),'grid_mm':h}))
if __name__=='__main__':main()
