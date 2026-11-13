"""1:1 starting cut profiles, with explicit neutral-path length corrections."""
from pathlib import Path
import hashlib,json,math,runpy,sys
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as A
import Part
H=Path(__file__).resolve().parent;ROOT=H.parents[3];M=runpy.run_path(str(ROOT/'tools/build_evt1_dock_device_seats.py'));V=A.Vector
rr=M['rr'];box=M['box'];fuse=M['fuse'];PET=M['PET'];R=M['BODY_R'];sil=M['SILICONE_LOADED']
extra=math.hypot(2,.05)-2+math.hypot(1.4,.4)-1.4
rows=[]
def flange(kind,short,x,y,quantity):
 length=(14 if short else 24)+extra
 shape=fuse([rr(0,0,6,4,.6,0,1),box((-1,1.9,0),(1,length,1)),Part.makeCylinder(2.4,1,V(0,length,0))]).cut(Part.makeCylinder(1.1,1.2,V(0,length,-.1)))
 if kind=='PET':shape=shape.cut(box((-.04,length+1,0),(.04,length+2.5,1)))
 shape.translate(V(x,y,0));rows.append({'name':'flange_'+('short'if short else'long')+'_'+kind,'quantity_default':quantity,'shape':shape,'head_centre_to_hole_mm':length,'manufactured_sheet_thickness_mm':PET if kind=='PET'else.254})
def body(kind,idx,y):
 h=PET if kind=='PET'else sil;lower=sil+idx*PET if kind=='PET'else 0
 mid=R+lower+h/2;edge=32-math.sqrt(mid*mid-3.5**2);flat=13+(idx*PET if kind=='PET'else 2*PET)+h/2
 length=2*(mid*math.asin(3.5/mid)+math.hypot(3.5,edge-flat)+17);half=length/2
 s=fuse([box((-half,-2,0),(half,2,1)),Part.makeCylinder(2.4,1,V(-half,0,0)),Part.makeCylinder(2.4,1,V(half,0,0))])
 for sign in(-1,1):
  s=s.cut(Part.makeCylinder(1.1,1.2,V(sign*half,0,-.1)))
  if kind=='PET':s=s.cut(box((half+1 if sign>0 else-half-2.5,-.04,0),(half+2.5 if sign>0 else-half-1,.04,1)))
 s.translate(V(32,y,0));rows.append({'name':'body_'+kind+str(idx),'quantity_default':1,'shape':s,'hole_centre_distance_mm':length,'neutral_path_radius_mm':mid,'manufactured_sheet_thickness_mm':PET if kind=='PET'else.254})
flange('silicone',False,8,6,2);flange('silicone',True,20,6,1);flange('PET',False,34,6,4);flange('PET',True,46,6,2)
body('silicone',0,52);body('PET',0,65);body('PET',1,78)
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="90mm" height="100mm" viewBox="0 0 90 100">','<rect width="90" height="100" fill="white"/>']
for r in rows:
 plane=Part.Face(Part.makePolygon([V(-5,-5,.5),V(90,-5,.5),V(90,100,.5),V(-5,100,.5),V(-5,-5,.5)]))
 for e in r['shape'].section(plane).Edges:
  pp=e.discretize(Deflection=.003);points=' '.join(f'{p.x:.4f},{p.y:.4f}'for p in pp)
  svg.append(f'<polyline points="{points}" fill="none" stroke="black" stroke-width="0.06"/>')
svg.extend(['<path d="M5 91H15M5 90V92M15 90V92" stroke="black" stroke-width=".1" fill="none"/>','<text x="5" y="96" font-family="Arial" font-size="2.4">10mm · 1:1 · fit/relaxation trial required</text>',
'<text x="58" y="7" font-family="Arial" font-size="2.2">Top four: long / short</text>','<text x="58" y="11" font-family="Arial" font-size="2.2">silicone2/1 · PET4/2</text>',
'<text x="61" y="52" font-family="Arial" font-size="2.2">Body silicone1</text>','<text x="61" y="65" font-family="Arial" font-size="2.2">Body PET layer1</text>','<text x="61" y="78" font-family="Arial" font-size="2.2">Body PET layer2</text>','</svg>'])
(H/'cut-patterns-1to1.svg').write_text('\n'.join(svg)+'\n')
for r in rows:del r['shape']
(H/'cut-patterns.json').write_text(json.dumps({'builder_sha256':M['sha'](ROOT/'tools/build_evt1_dock_device_seats.py'),'cut_exporter_sha256':M['sha'](Path(__file__)),'profiles':rows,'body_neutral_path':'centralradialarc pluslinearformedramps plusflatends; noPETstretchcredit','flange_developed_extra_mm':extra,'elastic_forming_or_received_fit_validated':False,'PET_slit_visual_kerf_mm':.08,'actual_knife_kerf_must_not_be_assumed':True,'silicone_shipping_liners_removed_before_relax_and_cut':True},indent=2)+'\n')
print('Exported',len(rows),'cutprofiles')
