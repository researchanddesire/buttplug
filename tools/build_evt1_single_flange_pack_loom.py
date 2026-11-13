"""Selected ACH mated component source, editable manufacturer-drawing study.

No pack/master/ECAD mutation. Undimensioned internal details are explicit;
public selected-part outer profiles govern external mechanical checks only.
"""
from pathlib import Path
import json,sys,hashlib,importlib.util
R=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location('j7',R/'tools/build_evt1_single_flange_j7_loom.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
A=m.A;Part=m.Part;V=m.V
OUT=R/'hardware/cad/manufacturing-layout/evt1-integration/contact-module-trial/pack-loom-trial'
sha=m.sha

def profile_body(d,name,pts,z,height):
 b=d.addObject('PartDesign::Body',name);s=b.newObject('Sketcher::SketchObject',name+'Outline');s.Placement.Base=V(0,0,z)
 m.polygon(s,pts);d.recompute();f=b.newObject('PartDesign::Pad',name+'Base');f.Profile=s;f.Length=height;d.recompute();s.Visibility=False
 assert f.Shape.isValid()and len(f.Shape.Solids)==1;return b

def build_mated(d,name='ACHMatedAssembly'):
 g=d.addObject('App::Part',name)
 p=profile_body(d,'ACHTP02VS',[(0,-1.6),(3,-1.6),(3,-1.9),(5.25,-1.9),(5.25,1.9),(3,1.9),(3,1.6),(0,1.6)],0,1.85)
 m.pad(p,'OpenMatingWell',1.86,1.76,[(3.25,-1.65,5.35,1.65)],True)
 m.pad(p,'TwoPlugContactChannels',1.4,1.1,[(-.1,-1.,3.26,-.2),(-.1,.2,3.26,1.)],True)
 q=profile_body(d,'ACHTR02VS',[(3.3,-1.3),(5.25,-1.3),(5.25,-1.6),(6.8,-1.6),(6.8,1.6),(5.25,1.6),(5.25,1.3),(3.3,1.3)],.25,1.2)
 m.pad(q,'SocketWireEnd',0,1.85,[(5.25,-1.6,6.8,1.6)])
 m.pad(q,'TwoSocketContactChannels',1.4,1.0,[(3.2,-1.,6.9,-.2),(3.2,.2,6.9,1.)],True)
 for b,mpn in ((p,'ACHTP-02V-S'),(q,'ACHTR-02V-S')):
  g.addObject(b);b.addProperty('App::PropertyString','MPN');b.MPN=mpn
  m.note(b,'JST eACH1.pdf p2 external stepped profile: plug5.25 x3.2/3.8; socket3.5 x2.6/3.2, mating tongue1.2, full height1.85 mm. '
    'Mated overlap1.95 mm derives from5.25+3.5-6.8. Internal wells/channels, plug wall and fillets are illustrative; not OEM CAD or contact/retention qualification.')
  if b.ViewObject:b.ViewObject.ShapeColor=(.88,.87,.78)
 contacts=[]
 for kind,length,u0,width,height in (('SACHP',4.05,.3,.8,.95),('SACH',2.95,3.55,.8,.95)):
  for n,v in ((1,-.6),(2,.6)):
   b=d.addObject('PartDesign::Body',kind+'Pin'+str(n));s=b.newObject('Sketcher::SketchObject','FormedContactSection')
   # Section is transverse v,w, extruded along +u. A formed wall is shown,
   # with .10 mm sheet thickness explicitly illustrative.
   s.Placement=A.Placement(V(u0,0,0),A.Rotation(V(1,1,1),120))
   m.polygon(s,[(-width/2,.4),(width/2,.4),(width/2,.4+height),(width/2-.1,.4+height),
                 (width/2-.1,.5),(-width/2+.1,.5),(-width/2+.1,.4+height),(-width/2,.4+height)])
   d.recompute();f=b.newObject('PartDesign::Pad','StampedLength');f.Profile=s;f.Length=length;d.recompute();s.Visibility=False
   b.Placement.Base=V(0,v,0);g.addObject(b);b.addProperty('App::PropertyString','MPN');b.MPN=kind+'-003G-P0.2'
   b.addProperty('App::PropertyString','Net');b.Net='PACK_P'if n==1 else'GND'
   m.note(b,'Primary eACH1 p2 length '+str(length)+' and width0.8 mm. Formed0.10 mm wall, local seating and barrel reliefs are illustrative. '
     'Not an OEM crimp-die, retention or current qualification model. Pin1 is the marked lower-v row in the published top view.')
   if b.ViewObject:b.ViewObject.ShapeColor=(.79,.67,.22)
   contacts.append(b)
 d.recompute();return {'group':g,'plug':p,'socket':q,'contacts':contacts}

def installed_frame():
 # u long/mating -> -productX, v circuit row -> +productZ,
 # w thickness -> +productY: determinant+1, no mirror.
 return [[-1,0,0,-4.1],[0,0,1,-18.4],[0,1,0,-1.1],[0,0,0,1]]

def main():
 OUT.mkdir(parents=True,exist_ok=True);d=A.newDocument('ACHMatedComponentSource');v=build_mated(d);d.recompute()
 assert all(o.Shape.isValid()and len(o.Shape.Solids)==1 for o in d.Objects if o.TypeId=='PartDesign::Body')
 local=Part.makeCompound([b.Shape for b in [v['plug'],v['socket']]+v['contacts']]);bb=m.bound(local)
 assert max(abs(a-b)for a,b in zip(bb,[0,-1.9,0,6.8,1.9,1.85]))<1e-6,bb
 print('MATED_LOCAL_BOUNDS',bb,flush=True)
 d.saveAs(str(OUT/'ACHMatedComponentSource.FCStd'))
 # STEP uses actual Tip shapes, then independent readback. Never export an
 # unrecomputed Body and infer geometry coverage from file existence.
 for label,b in (('ACHTP-02V-S',v['plug']),('ACHTR-02V-S',v['socket'])):
  p=OUT/(label+'.step');b.Tip.Shape.exportStep(str(p));s=Part.Shape();s.read(str(p));assert s.isValid()and len(s.Solids)==1
 r={'status':'Selected-part public-drawing native reconstruction; no pack/source promotion',
 'native_sha256':sha(OUT/'ACHMatedComponentSource.FCStd'),'builder_sha256':sha(Path(__file__)),
 'source':{'url':'https://www.jst.com/wp-content/uploads/2021/03/eACH1.pdf','local':'sources/eACH1.pdf','sha256':sha(OUT/'sources/eACH1.pdf'),'pages':[1,2]},
 'parts':[{'mpn':'ACHTP-02V-S','qty':1,'purchase_scope':'body-side plug only'},{'mpn':'SACHP-003G-P0.2','qty':2,'purchase_scope':'body-side contacts only'},
 {'mpn':'ACHTR-02V-S','qty':1,'purchase_scope':'included in requested factory pack, not duplicate loose purchase'},{'mpn':'SACH-003G-P0.2','qty':2,'purchase_scope':'included in requested factory pack'}],
 'manufacturer':'JST','rated_A':2,'rating_wire_AWG':28,'wire_range_AWG':[30,28],'insulation_OD_mm':[.5,.63],
 'local_mated_bounds_mm':bb,'installed_candidate_matrix4':installed_frame(),'installed_frame_determinant':1,
 'installed_wire_exit_points_mm':{'body_pin1':[-4.1,-17.5,-1.7],'body_pin2':[-4.1,-17.5,-.5],
 'pack_pin1':[-10.9,-17.5,-1.7],'pack_pin2':[-10.9,-17.5,-.5]},
 'pose_is_disposable_candidate':True,'whole_geometry_receiver_tolerances_published':False,'physical_validation':False}
 (OUT/'selected-parts.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
