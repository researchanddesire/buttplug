"""Draw saved native sections, not an AI/product render. No source mutation."""
from pathlib import Path
import sys,json,hashlib,html
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
from PySide6 import QtWidgets,QtSvg,QtGui,QtCore
P=Path(__file__).resolve().parent;N=Path(sys.argv[1])if len(sys.argv)>1 else P/'SingleFlangeBoardTrial.FCStd';DEST=Path(sys.argv[2])if len(sys.argv)>2 else P;DEST.mkdir(parents=True,exist_ok=True);PARTIAL='archive'in N.parts;d=A.openDocument(str(N));s=A.openDocument(str(P.parent.parent/'EVT1Product.FCStd'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sh=lambda n:d.getObject('ActualNativeFlangePCB'if n=='SingleFlangePCB'and d.getObject('ActualNativeFlangePCB')else n).Shape
S=['<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="1500" viewBox="0 0 1500 1500">','<rect width="1500" height="1500" fill="#fff"/>','<style>text{font-family:Arial,sans-serif;fill:#20323e}.small{font-size:18px}.title{font-size:26px;font-weight:bold}</style>']
def txt(x,y,t,size=19):S.append(f'<text x="{x}" y="{y}" font-size="{size}">{html.escape(t)}</text>')
def section(shape,axis,dist,coords,cx,cy,k,col,offset=0,dash=False,crop=None):
 q=shape.copy();q.translate(A.Vector(0,offset,0))
 if crop:q=q.common(Part.makeBox(crop[3]-crop[0],crop[4]-crop[1],crop[5]-crop[2],A.Vector(*crop[:3])))
 norm=A.Vector(1,0,0)if axis=='x'else A.Vector(0,1,0);paths=[]
 for w in q.slice(norm,dist):
  pts=w.discretize(Deflection=.04)
  if not pts:continue
  xy=[(cx+k*getattr(p,coords[0]),cy-k*getattr(p,coords[1]))for p in pts]
  paths.append('M'+' L'.join(f'{x:.2f},{y:.2f}'for x,y in xy)+' Z')
 if paths:S.append(f'<path d="{" ".join(paths)}" fill="{col if not dash else "none"}" fill-rule="evenodd" stroke="#334858" stroke-width="1.2"'+(' stroke-dasharray="6 4"'if dash else'')+'/>')
def legend(x,y):
 for i,(c,t)in enumerate([('#e1d8c0','Actual source-derived cover / Tray'),('#51976a','Proposed single flange PCB,1mm'),('#ddba4c','Selected Mill-Max1946 fixed targets'),('#b9c5d1','Requested protected pack'),('#8f76aa','Requested growth keepout'),('#80b9d8','Integral silicone boss trial')]):
  yy=y+i*25;S.append(f'<rect x="{x}" y="{yy-13}" width="18" height="15" fill="{c}"/>');txt(x+27,yy,t,17)
txt(35,43,'Single flange PCB / source-derived layout preview',30)
txt(35,75,('Body PCB retained · requested pack beneath PCB · rear rigid extent +3.2mm · partial component fit'if PARTIAL else'Body PCB retained · requested pack beneath PCB · rear rigid extent +3.2mm · all39 selected positions bound'),21)
txt(35,105,('21-body datum candidate;39-part/lead/barrier refinement in progress. No physical, RF, sealing or powered result.'if PARTIAL else'Actual 39-position models and continuous skin; nominal assembly checks only. No powered, RF or physical validation.'),18)
# Rear-facing native slices, each sampled at its actual material plane.
txt(35,155,'REAR XZ VIEW / actual-part section planes',23)
section(sh('ProposedRearHalf'),'y',-28.5,('x','z'),750,350,10,'#e1d8c0')
section(sh('SingleFlangePCB'),'y',-26.452,('x','z'),750,350,10,'#51976a')
for n in('GND','USB_DM_CONTACT','USB_DP_CONTACT','DOCK_5V'):section(sh('Contact_'+n),'y',-29.8,('x','z'),750,350,10,'#ddba4c')
section(sh('PermanentSixOpeningDiaphragm'),'y',-28.9,('x','z'),750,350,10,'#80b9d8')
for i in range(2):
 section(sh('OmronB3U1000P_'+str(i)),'y',-28.35,('x','z'),750,350,10,'#444')
 section(sh('IntegralSiliconeBoss'+str(i)),'y',-29.8,('x','z'),750,350,10,'#80b9d8')
 section(sh('MovedSteelKeeper'+str(i)),'y',-27.8,('x','z'),750,350,10,'#999',dash=True)
txt(52,545,'Antenna edge notch provisional; keepers moved+24X/−3.2Y. RF and magnetic qualification remain OPEN.',18)
if d.getObject('RevisedContinuousSkin'):section(sh('RevisedContinuousSkin'),'y',-29.5,('x','z'),750,350,10,'#bdddea',dash=True)
# Through-contactYZsection: exact contact atX−10, wholeboard loading+Yfrominside.
txt(35,600,'CONTACT SECTION X−10 / final closed position',23)
for n,c in ([('RevisedContinuousSkin','#c3dfea')]if d.getObject('RevisedContinuousSkin')else[])+[('ProposedRearHalf','#e1d8c0'),('ProposedFlangeTray','#d9ceb4'),('SingleFlangePCB','#51976a'),('PermanentSixOpeningDiaphragm','#80b9d8'),('Contact_USB_DM_CONTACT','#ddba4c')]:section(sh(n),'x',-10,('y','z'),1180,960,22,c,crop=(-100,-31.2,7,100,-21.5,13))
txt(40,635,'Target face Y−30.0',18);txt(40,662,'Skin rear datum Y−29.7;0.3mm proud',18);txt(40,689,'Target base → laminate compression → Tray post',18);txt(40,716,'No solder strength or PCB bending load credit',18);txt(40,743,'Nominal head-through-cover loading shown',18);txt(40,770,'Received target angle/flatness/aperture fit pending',18)
# Battery cross-section, actual source plus requested growthoutline.
txt(770,600,'BATTERY SECTION X20 / requested pack',23)
for n,c in [('ProposedRearHalf','#e1d8c0'),('SingleFlangePCB','#51976a')]:section(sh(n),'x',20,('y','z'),1460,810,12,c)
for o in d.Objects:
 if o.TypeId=='PartDesign::Body'and o.Name.startswith('Actual_'):section(o.Shape,'x',20,('y','z'),1460,810,12,'#626b75')
section(s.getObject('PackSizeReference').Shape,'x',20,('y','z'),1460,810,12,'#b9c5d1')
section(s.getObject('PackGrowthAllowance').Shape,'x',20,('y','z'),1460,810,12,'#8f76aa',dash=True)
txt(780,1020,'B plane to requested growth:3.352mm',18)
txt(780,1047,'2.95mm component leaves0.402mm nominal',18)
txt(780,1074,'Actual selected models are separately source bound',18)
# Two source-derived movement frames, transposedYZcentredtofit.
txt(35,1120,'WHOLE PCB INSERTION / contact section shown',21)
for n,c in [('ProposedRearHalf','#e1d8c0'),('SingleFlangePCB','#51976a'),('Contact_USB_DM_CONTACT','#ddba4c')]:section(sh(n),'x',-10,('y','z'),1040,1530,18,c,offset=4 if n!='ProposedRearHalf'else 0,crop=(-100,-35,7,100,-20,13))
txt(35,1160,'One populated PCB moves−Y through head apertures.',17)
txt(35,1186,'Then four dry-side stock screws retain the whole board.',17)
txt(35,1212,'Integral skin presses closed precured cups; no loose plungers.',17)
txt(770,1120,'CASE CLOSURE / populated PCB approaches Tray',21)
for n,c in [('ProposedFlangeTray','#d9ceb4'),('ProposedRearHalf','#e1d8c0'),('SingleFlangePCB','#51976a'),('Contact_USB_DM_CONTACT','#ddba4c')]:section(sh(n),'x',-10,('y','z'),1830,1530,18,c,offset=-3 if n!='ProposedFlangeTray'else 0,crop=(-100,-35,7,100,-20,13))
txt(775,1160,'PCB/cover moves+Y until rear lands meet four posts.',17)
txt(775,1186,'Close both halves before continuous skin molding.',17)
txt(775,1212,'Permanentsoftbarrier modeled; leak/tear/cure trial OPEN.',17)
txt(35,1465,'Native SHA256 '+sha(N)[:32]+' · nominal sections only · no supplier or physical acceptance',16)
S.append('</svg>');svg=DEST/'native-sections.svg';svg.write_text('\n'.join(S)+'\n')
app=QtWidgets.QApplication.instance()or QtWidgets.QApplication([]);r=QtSvg.QSvgRenderer(str(svg));im=QtGui.QImage(1500,1500,QtGui.QImage.Format_ARGB32);im.fill(QtCore.Qt.white);p=QtGui.QPainter(im);r.render(p);p.end();im.save(str(DEST/'native-sections.png'))
(DEST/'render-binding.json').write_text(json.dumps({'native_sha256':sha(N),'source_product_sha256':sha(P.parent.parent/'EVT1Product.FCStd'),'renderer_sha256':sha(Path(__file__)),'svg_sha256':sha(svg),'png_sha256':sha(DEST/'native-sections.png'),'mode':'actual saved-native slices at stated planes; no invented product render'},indent=2)+'\n')
print(DEST/'native-sections.png')
