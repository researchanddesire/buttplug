from pathlib import Path
import FreeCAD as App
import Part
p=Path('hardware/cad/evt1-assembly/vendor/lcd-socket/524372771.stp');h,l=Part.read(str(p)).Solids
l=l.copy();l.translate(App.Vector(0,0,-1.6))
out=['<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1000" viewBox="0 0 1600 1000"><rect width="1600" height="1000" fill="white"/>']
for row,x in enumerate((0,.25)):
 for col,F in enumerate((61.1,61.3)):
  ox=60+col*800;oy=100+row*470;scale=100
  out.append(f'<text x="{ox}" y="{oy-45}" font-family="sans-serif" font-size="22">OEM closed section X={x}; PCB F={F}</text>')
  def pt(z,y):return f'{ox+z*scale:.4f},{oy+(2.4-y)*scale:.4f}'
  vs=[App.Vector(x,-.2,-1),App.Vector(x,2.5,-1),App.Vector(x,2.5,7),App.Vector(x,-.2,7),App.Vector(x,-.2,-1)]
  face=Part.Face(Part.makePolygon(vs))
  for shape,color in ((h,'#706b52'),(l,'#8c421e')):
   sec=shape.section(face)
   for e in sec.Edges:
    ps=e.discretize(Deflection=.0005)
    d='M '+' L '.join(pt(v.z,v.y)for v in ps)
    out.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"/>')
  tip=.824777961;top=62-F;bot=61.7-F
  out.append(f'<polygon points="{pt(tip,bot)} {pt(tip+5,bot)} {pt(tip+5,top)} {pt(tip,top)}" fill="#33aaee" fill-opacity=".3" stroke="#007cbe" stroke-width="1.5"/>')
  out.append(f'<text x="{ox}" y="{oy+310}" font-family="sans-serif" font-size="18">Blue: complete 0.30 mm FPC end; mouth to right. Source height up.</text>')
out.append('</svg>');Path('/private/tmp/compass-jobs/socket-sections.svg').write_text(''.join(out))
