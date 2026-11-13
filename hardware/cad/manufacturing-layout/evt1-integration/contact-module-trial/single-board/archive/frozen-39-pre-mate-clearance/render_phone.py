"""Phone preview from actual saved selected-model meshes and exact native sections."""
from pathlib import Path
import sys,json,hashlib,html,math
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
from PySide6 import QtWidgets,QtSvg,QtGui,QtCore
P=Path(__file__).resolve().parent;N=P/'SingleFlangeBoardTrial.FCStd';R=P.parents[5];d=A.openDocument(str(N));src=A.openDocument(str(P.parent.parent/'EVT1Product.FCStd'));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();F=-26.952
mc=json.loads((R/'hardware/pcb/evt1/single-flange-study/mcad.json').read_text());S=['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="1300" viewBox="0 0 900 1300">','<rect width="900" height="1300" fill="#fff"/>','<style>text{font-family:Arial,sans-serif;fill:#203341}</style>']
def text(x,y,t,n=24,bold=False):S.append(f'<text x="{x}" y="{y}" font-size="{n}" font-weight="{"bold"if bold else"normal"}">{html.escape(t)}</text>')
def shape(n):return d.getObject(n).Shape

def section(s,axis,plane,xy,fill,dash=False,crop=None):
 if crop:s=s.common(Part.makeBox(crop[3]-crop[0],crop[4]-crop[1],crop[5]-crop[2],A.Vector(*crop[:3])))
 paths=[]
 for w in s.slice(A.Vector(1,0,0)if axis=='x'else A.Vector(0,1,0),plane):
  pts=w.discretize(Deflection=.025)
  if pts:paths.append('M'+' L'.join(f'{xy(p)[0]:.2f},{xy(p)[1]:.2f}'for p in pts)+' Z')
 if paths:S.append('<path d="'+' '.join(paths)+'" fill="'+('none'if dash else fill)+'" fill-rule="evenodd" stroke="#3b4d58" stroke-width="1"'+(' stroke-dasharray="6 4"'if dash else'')+'/>')
text(35,45,'One flange PCB',34,True)
text(35,80,'Contacts, buttons and compass share the board.',24)
text(35,112,'Inside view · existing body PCB retained',21)
section(shape('ActualNativeFlangePCB'),'y',F+.5,lambda p:(450+9.5*p.x,252-9.5*p.z),'#3d9465')
# Render the actual B-side selected models; no package fit boxes.
triangles=[]
for c in mc['components']:
 if c['side']!='B':continue
 g=d.getObject('Actual_'+c['ref'])
 for o in g.Group:
  if o.TypeId!='PartDesign::Body':continue
  verts,faces=o.Shape.tessellate(.04)
  for face in faces:
   vs=[verts[k]for k in face];normal=(vs[1]-vs[0]).cross(vs[2]-vs[0]);ln=normal.Length
   light=abs(normal.dot(A.Vector(-.3,.8,.5)))/ln if ln else .5
   grey=max(62,min(180,int(76+85*light)));col=f'#{grey:02x}{min(grey+8,255):02x}{min(grey+12,255):02x}'
   triangles.append((sum(p.y for p in vs)/3,vs,col))
for depth,vs,col in sorted(triangles,key=lambda x:x[0]):
 pts=' '.join(f'{450+9.5*p.x:.2f},{252-9.5*p.z:.2f}'for p in vs)
 S.append(f'<polygon points="{pts}" fill="{col}" stroke="{col}" stroke-width=".25"/>')
text(35,410,'Battery beneath the board',28,True)
stack=lambda p:(450+13*p.z,515+13*(p.y-F))
for n,c in [('RevisedContinuousSkin','#b8dae9'),('ProposedRearHalf','#dfd5bc'),('ProposedFlangeTray','#dfd5bc'),('ActualNativeFlangePCB','#3d9465')]:section(shape(n),'x',20,stack,c)
for o in d.Objects:
 if o.TypeId=='PartDesign::Body'and o.Name.startswith('Actual_'):section(o.Shape,'x',20,stack,'#666e76')
section(src.getObject('PackSizeReference').Shape,'x',20,stack,'#bcc7d0')
section(src.getObject('PackGrowthAllowance').Shape,'x',20,stack,'#9b7cb3',True)
text(35,840,'Requested pack and growth allowance.',23)
text(35,870,'Rear cover grows by 3.2 mm.',23)
text(35,925,'PCB-mounted contact',25,True)
text(475,925,'Closed button cup',25,True)
contact=lambda p:(235+30*(p.z-10),1055+30*(p.y-F))
for n,c in [('RevisedContinuousSkin','#b8dae9'),('ProposedRearHalf','#dfd5bc'),('ProposedFlangeTray','#dfd5bc'),('PermanentSixOpeningDiaphragm','#6fa7c1'),('ActualNativeFlangePCB','#3d9465'),('Contact_USB_DM_CONTACT','#d7ad43')]:section(shape(n),'x',-10,contact,c,crop=(-100,-31,7,100,-22.4,13))
button=lambda p:(675+40*p.z,1080+40*(p.y-F))
for n,c in [('RevisedContinuousSkin','#b8dae9'),('ProposedRearHalf','#dfd5bc'),('PermanentSixOpeningDiaphragm','#6fa7c1'),('ActualNativeFlangePCB','#3d9465')]:section(shape(n),'x',-17,button,c,crop=(-100,-30.1,-3.6,100,-25.7,3.6))
g=d.getObject('Actual_SW1')
for o in g.Group:
 if o.TypeId=='PartDesign::Body':section(o.Shape,'x',-17,button,'#3d4349',crop=(-100,-30.1,-3.6,100,-25.7,3.6))
text(35,1220,'Target → board → Tray post',22)
text(475,1220,'A closed cup protects the switch.',22)
text(35,1260,'Digital fit only. Physical casting and force trials remain.',21)
text(35,1288,'Saved native '+sha(N)[:16]+' · requested battery is not supplier accepted',15)
S.append('</svg>');svg=P/'native-sections.svg';svg.write_text('\n'.join(S)+'\n');app=QtWidgets.QApplication.instance()or QtWidgets.QApplication([]);renderer=QtSvg.QSvgRenderer(str(svg));im=QtGui.QImage(900,1300,QtGui.QImage.Format_ARGB32);im.fill(QtCore.Qt.white);painter=QtGui.QPainter(im);renderer.render(painter);painter.end();png=P/'native-sections.png';im.save(str(png));(P/'render-binding.json').write_text(json.dumps({'native_sha256':sha(N),'source_product_sha256':sha(P.parent.parent/'EVT1Product.FCStd'),'MCAD_sha256':sha(R/'hardware/pcb/evt1/single-flange-study/mcad.json'),'renderer_sha256':sha(Path(__file__)),'svg_sha256':sha(svg),'png_sha256':sha(png),'rendering':'Actual selected B-side component meshes for display only; exact native BRep sections elsewhere; no fit proxy or invented product render'},indent=2)+'\n');print(png)
