"""Source-bound sections of the actual saved seat/device geometry."""
from pathlib import Path
import hashlib,json,sys
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
from PySide6 import QtGui,QtSvg,QtWidgets
H=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();V=A.Vector
r=json.loads((H/'native-readback.json').read_text());assert r['native_sha256']==sha(H/'DeviceSeatingTrial.FCStd')
d=A.openDocument(str(H/'DeviceSeatingTrial.FCStd'));d.recompute()
soft=[o for o in d.Objects if o.TypeId=='PartDesign::Body'and o.Name!='SeatLinerCoupon']
shapes=[(d.SeatLinerCoupon.Shape,'#a7986b'),(d.ActualDevice.Shape,'#546c62')]+[(p.Shape,'#448bad'if'PET'in p.Name else'#925eb0')for p in soft]
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="660" viewBox="0 0 1200 660">','<rect width="1200" height="660" fill="#faf9f5"/>','<text x="20" y="28" font-family="Arial" font-size="18">Actual source-derived device seating · physical load and UV validation pending</text>']
for i,(title,axis,c,center,k)in enumerate([('Flange pad closeup / X−28,Y30','xz',30,-28,22),('Narrow body saddle / Y106.5','xz',106.5,0,17),('Retained flange tail / X−28','yz',-28,39,8.8)]):
 x0=20+400*i;svg.extend([f'<defs><clipPath id="p{i}"><rect x="{x0}" y="80" width="380" height="230"/></clipPath></defs>',f'<text x="{x0}" y="63" font-family="Arial" font-size="13">{title}</text>',f'<g clip-path="url(#p{i})">'])
 if axis=='xz':pts=[V(center-12,c,10),V(center+12,c,10),V(center+12,c,17),V(center-12,c,17)]
 else:pts=[V(c,20,10),V(c,58,10),V(c,58,17),V(c,20,17)]
 plane=Part.Face(Part.makePolygon(pts+[pts[0]]))
 for s,col in shapes:
  for e in s.section(plane).Edges:
   pp=[]
   for p in e.discretize(Deflection=.01):
    xx=p.x-center if axis=='xz'else p.y-center;pp.append(f'{x0+190+xx*k:.3f},{280-(p.z-11)*k:.3f}')
   svg.append(f'<polyline points="{" ".join(pp)}" fill="none" stroke="{col}" stroke-width="1.3"/>')
 svg.append('</g>')
svg.extend(['<text x="20" y="340" font-family="Arial" font-size="13">Cream: printable floor/support · green: actual device · blue: registered PET · purple: solid silicone sheet</text>','<text x="20" y="365" font-family="Arial" font-size="13">Pad contact envelope≤100mm². Tails and catches also block rays. Transparent sheet has no275nm transmission credit.</text>'])
for s,col in shapes[:1]+shapes[2:]:
 for e in s.Edges:
  pp=e.discretize(Deflection=.08);coords=' '.join(f'{600+p.x*4:.2f},{605-(p.y-23)*2.7:.2f}'for p in pp)
  svg.append(f'<polyline points="{coords}" fill="none" stroke="{col}" stroke-width=".7"/>')
svg.extend(['<text x="20" y="640" font-family="Arial" font-size="13">Plan: three6×4mm pads, narrow7×4mm body band; integral tails and catches. Lift device to clean supported/shadowed surfaces.</text>','</svg>'])
(H/'native-sections.svg').write_text('\n'.join(svg)+'\n')
app=QtWidgets.QApplication([]);q=QtSvg.QSvgRenderer(str(H/'native-sections.svg'));img=QtGui.QImage(2400,1320,QtGui.QImage.Format_ARGB32);img.fill(QtGui.QColor('white'));p=QtGui.QPainter(img);q.render(p);p.end();assert img.save(str(H/'native-sections.png'))
(H/'preview-bindings.json').write_text(json.dumps({'native_sha256':r['native_sha256'],'renderer_sha256':sha(Path(__file__)),'svg_sha256':sha(H/'native-sections.svg'),'png_sha256':sha(H/'native-sections.png'),'actual_saved_native_sections':True},indent=2)+'\n')
print('Renderedsourceboundnativegeometry')
