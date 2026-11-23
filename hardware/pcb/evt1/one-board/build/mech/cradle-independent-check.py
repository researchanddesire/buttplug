import FreeCAD as App, Part, json, math, hashlib
from pathlib import Path
r=Path('/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board')
V=App.Vector
sh={}
for n in ['InternalCradle','CradleWireGuide','MetalBody','MotorThermistorCap']:
 s=Part.Shape();s.read(str(r/'mech'/f'{n}.step'));assert s.isValid();sh[n]=s
pack=Part.makeBox(21,33,6.3,V(-10.5,31.75,-4.15))
# Screening growth envelope only: .25mm on both sides,1.1mm lower and1.1mm upper.
growth=Part.makeBox(21.5,33,8.5,V(-10.75,31.75,-5.25))
motor=Part.makeCylinder(5.55,26.3,V(0,67,0),V(0,1,0))
def cv(a,b):
 return sum(a.common(s).Volume for s in b.Solids if a.BoundBox.intersect(s.BoundBox))
def sweep_z(shape,hard,offsets):
 rows=[]
 for dz in offsets:
  s=shape.copy();s.translate(V(0,0,dz));v=cv(s,hard)
  rows.append({'z_offset_mm':dz,'overlap_mm3':round(v,6)})
 return {'poses':len(rows),'max_overlap_mm3':max(x['overlap_mm3'] for x in rows),'hits':[x for x in rows if x['overlap_mm3']>.001]}
report={'inputs_sha256':{n:hashlib.sha256((r/'mech'/f'{n}.step').read_bytes()).hexdigest() for n in sh},'growth_screen_mm':{'side_each':.25,'upper':1.1,'lower':1.1,'axial':0},'checks':{}}
c=report['checks'];offsets=[i*.5 for i in range(81)]
for n,p in [('nominal',pack),('screening_growth',growth)]:
 c[f'pack_{n}_plus_Z_loading']=sweep_z(p,sh['InternalCradle'],offsets)
 c[f'guide_plus_Z_removal_over_{n}_pack']=sweep_z(sh['CradleWireGuide'],p,offsets)
 c[f'guide_plus_Z_removal_over_lower_frame_{n}']=sweep_z(sh['CradleWireGuide'],sh['InternalCradle'],offsets)
loaded=Part.makeCompound([sh['InternalCradle'],sh['CradleWireGuide'],pack,motor])
# Check cap translation and simultaneous 1.5mm-pitch rotation, actual cap solid.
poses=[]
for i in range(101):
 dy=.25*i; cap=sh['MotorThermistorCap'].copy();cap.rotate(V(0,0,0),V(0,1,0),dy*240);cap.translate(V(0,dy,0))
 poses.append({'cap_plus_Y_mm':dy,'rotation_deg':dy*240,'overlap_mm3':round(cv(cap,loaded),6)})
c['cap_helical_closure_loaded_rigid_parts']={'poses':len(poses),'max_overlap_mm3':max(x['overlap_mm3'] for x in poses),'hits':[x for x in poses if x['overlap_mm3']>.001]}
# Frame axial travel until taper contact / motor rear contact.
rows=[]
for i in range(-12,13):
 dy=i*.025;s=sh['InternalCradle'].copy();s.translate(V(0,dy,0));rows.append({'offset_Y_mm':round(dy,4),'body_overlap_mm3':round(cv(s,sh['MetalBody']),6),'motor_overlap_mm3':round(cv(s,motor),6),'body_gap_mm':round(s.distToShape(sh['MetalBody'])[0],6),'motor_gap_mm':round(s.distToShape(motor)[0],6)})
c['cradle_axial_capture_offsets']=rows
# Exact first-contact displacement via bisection overlap tolerance.
for n,hard,direction in [('rear_taper',sh['MetalBody'],-1),('motor_stop',motor,1)]:
 lo,hi=0.,1.
 for _ in range(26):
  mid=(lo+hi)/2;s=sh['InternalCradle'].copy();s.translate(V(0,direction*mid,0))
  if cv(s,hard)>1e-6:hi=mid
  else:lo=mid
 c[f'cradle_first_{n}_contact_mm']=round(direction*(lo+hi)/2,6)
report['limits']=['Nominal rigid CAD only. Growth box is an explicit screening allowance, not a supplier swelling specification.','Cap closure sweep checks cradle,guide,pack,motor solids; cap-mounted NTC and flexible wires excluded. Thread tolerances/engagement not modeled.','No band,cushion,screw-head or actual motor-terminal geometry included in these independent checks.']
p=r/'build/mech/cradle-independent-report.json';p.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in c.items() if k!='cradle_axial_capture_offsets'},indent=2))
print('REPORT',str(p))

import os
os._exit(0)
