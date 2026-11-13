"""Candidate service loops and all sixteen neck conductors, product mm.

Every curve has explicit endpoints/tangents. These are nominal assembly
candidates; source lead positions and actual forming/strain relief need trial.
"""
import math
PI=math.pi

def add(a,b):return [x+y for x,y in zip(a,b)]
def mul(a,k):return [x*k for x in a]
def sub(a,b):return [x-y for x,y in zip(a,b)]
def norm(a):return math.sqrt(sum(x*x for x in a))
def unit(a):return mul(a,1/norm(a))
def line(a,b):return {'kind':'line','points':[list(a),list(b)]}
def arc(a,d,n,r,t):
 at=lambda q:add(a,mul(add(mul(d,math.sin(q)),mul(n,1-math.cos(q))),r))
 return {'kind':'arc','points':[list(a),at(t/2),at(t)],'design_radius_mm':r}
def s_curve(a,b,axis=1):
 d=[0,0,0];d[axis]=1 if b[axis]>a[axis]else -1
 axial=abs(b[axis]-a[axis]);delta=sub(b,a);delta[axis]=0;l=norm(delta)
 if l<1e-10:return [line(a,b)]
 n=unit(delta);r=(axial*axial+l*l)/(4*l);t=2*math.atan2(l,axial)
 first=arc(a,d,n,r,t);dd=add(mul(d,math.cos(t)),mul(n,math.sin(t)));nn=sub(mul(d,math.sin(t)),mul(n,math.cos(t)))
 second=arc(first['points'][-1],dd,nn,r,t)
 assert norm(sub(second['points'][-1],b))<1e-8
 return [first,second]
def ease(a,b,axis):
 pts=[]
 for i in range(6):
  p=list(a if i<3 else b);p[axis]=a[axis]+(b[axis]-a[axis])*i/5;pts.append(p)
 return {'kind':'bezier','points':pts}
def reverse(ss):
 out=[]
 for s in ss[::-1]:
  q=dict(s);q['points']=s['points'][::-1]
  if s['kind']=='bspline':q['first_tangent']=mul(s['last_tangent'],-1);q['last_tangent']=mul(s['first_tangent'],-1)
  out.append(q)
 return out

def helix_xy(cx,cy,r,z0,pitch):
 result=[]
 smooth=lambda t:10*t**3-15*t**4+6*t**5
 deriv=lambda t:30*t*t-60*t**3+30*t**4
 point=lambda t:[cx+r*math.cos(2*PI*t),cy+r*math.sin(2*PI*t),z0+pitch*smooth(t)]
 tangent=lambda t:[-2*PI*r*math.sin(2*PI*t),2*PI*r*math.cos(2*PI*t),pitch*deriv(t)]
 for k in range(4):
  a,b=k/4,(k+1)/4
  result.append({'kind':'bspline','points':[point(a+(b-a)*j/45)for j in range(46)],
    'first_tangent':tangent(a),'last_tangent':tangent(b),'purpose':'stored service loop; pitch avoids geometric self-contact'})
 return result

def interboard():
 names=('GND','VBUS_CHG','3V3','PACK_P','MOTOR_ARM','MOTOR_PWM','DOCK_PRESENT_N','I2C_SDA','I2C_SCL','TIP_EXC_EN')
 answer=[]
 for i in range(10):
  u=i-4.5;zi=-u;start=[u,31.525,1.51];a=[u,29.525,1.51];b=[u*.75,16,1.51]
  twist=[]
  for j in range(121):
   t=j/120;f=10*t**3-15*t**4+6*t**5;theta=PI/2*f;spacing=.75+.25*f
   twist.append([2.775*f+u*spacing*math.cos(theta),16-24*t,1.51*(1-f)-u*spacing*math.sin(theta)])
  bendstart=[2.775,-19.942,zi]
  bend=arc(bendstart,[0,-1,0],[-1,0,0],4.5,PI/2)
  ss=[line(start,a),ease(a,b,1),{'kind':'bspline','points':twist,'first_tangent':[0,-1,0],'last_tangent':[0,-1,0]},
      line(twist[-1],bendstart),bend,line(bend['points'][-1],[-2.525,-24.442,zi])]
  answer.append({'name':'IB%02d'%(i+1),'net':names[i],'pin':i+1,'OD_mm':.6,'minimum_radius_mm':4.,'wire':'Accu-Glass100690',
   'sections':ss,'purpose':'Nominal installed route; service forming remains a physical assembly trial'})
 return answer


def power():
 result=[]
 for pin,z,net in ((1,-1.7,'PACK_P'),(2,-.5,'GND')):
  yp=-17.7 if pin==1 else -18.9; peak_y=-20.3 if pin==1 else -21.5;peak_z=7.2 if pin==1 else 8.4
  first=[7,yp,7.5];a=[5,yp,7.5];b=[-15.4,peak_y,peak_z]
  end_y=-17.5 if pin==1 else -18.7
  delta=[0,end_y-peak_y,z-peak_z];r=norm(delta)/2
  loop=arc(b,[-1,0,0],unit(delta),r,PI)
  end=[-10.9,-17.5,z]
  tail=s_curve(loop['points'][-1],end,0)
  result.append({'name':'PACK_FACTORY_POWER'+str(pin),'net':net,'pin':pin,'OD_mm':.63,'minimum_radius_mm':4.,'wire':'Requested pack factory28AWG',
    'sections':[line(first,a),ease(a,b,0),loop]+tail,'purpose':'Longer requested factory lead proposal; original RFQ is unchanged'})
  first=[-4.1,-17.5,z];a=[-3.8,-17.5,z];q=arc(a,[1,0,0],[0,1,0],4.5,PI/2)
  z0=3.1 if pin==1 else 4.3;zout=5.0 if pin==1 else 5.8
  p0=q['points'][-1];neck=[-4.3,0,z];b=[-4.3,2,z];c=[-3.6,12,z0];east=[8 if pin==1 else 8.7,38,zout]
  ss=[line(first,a),q]+s_curve(p0,neck)+[line(neck,b)]+s_curve(b,c)+[line(c,[-3.6,16,z0])]+s_curve([-3.6,16,z0],east)
  target=[-1.985,47.75,0]if pin==1 else[-2.2,46.9,0]
  a=[east[0],target[1]-4.5,zout];turn=arc(a,[0,1,0],[-1,0,0],4.5,PI/2)
  final_start=[target[0]+zout,target[1],zout];final=arc(final_start,[-1,0,0],[0,0,-1],zout,PI/2)
  assert norm(sub(final['points'][-1],target))<1e-7
  ss += [line(east,a),turn,line(turn['points'][-1],final_start),final]
  result.append({'name':'BODY_POWER'+str(pin),'net':net,'pin':pin,'OD_mm':.6,'bare_end_OD_mm':.4,'bare_end_length_mm':1.5,
    'minimum_radius_mm':4.,'wire':'Accu-Glass100690','sections':ss,'body_pad':'J2.1'if pin==1 else'J2.2P','purpose':'Separate body power return; no sensor-return splice'})
 return result


def ntcs():
 result=[]
 # Signal joint is upstream on the return path; stagger sleeves10mm so the
 # two2.4mm installed sleeves do not overlap. Factory PVC stays outside the
 # narrow throat; only selected32AWG extensions enter behind the rear stub.
 for sensor,sign in ((1,1),(2,-1)):
  for role in ('signal','return'):
   factory_y=-13.1 if role=='signal'else -14.3;joint_x=30.9 if role=='signal'else 36.1
   joint_y=factory_y+.4;first=[22.5,factory_y,sign*4];joint=[joint_x,joint_y,sign*4]
   shifted=[29.7,joint_y,sign*4]
   factory=[line(first,[26.5,factory_y,sign*4])]+s_curve([26.5,factory_y,sign*4],shifted,0)+[line(shifted,joint)]
   rowz=sign*(1.2 if role=='signal'else 2.1)
   a=[joint_x+1.2,joint_y,sign*4]
   turn=arc(a,[1,0,0],[0,0,sign],2,PI)
   c=[5.5 if role=='signal'else 5.05,-14.725,sign*(8.4 if role=='signal'else 9.3)]
   extension=[line(joint,a),turn]
   if role=='return':
    low=[32.,-14.3,sign*8.];high=[28.5,-14.3,sign*10.15];clear=[8.5,-14.3,sign*10.15]
    extension+=s_curve(turn['points'][-1],low,0)+s_curve(low,high,0)+[line(high,clear)]+s_curve(clear,c,0)
   else:extension+=s_curve(turn['points'][-1],c,0)
   b=[-3.1,-14.725 if role=='signal'else -15.9,rowz]
   extension+=s_curve(c,b,0);turn=arc(b,[-1,0,0],[0,1,0],2 if role=='signal'else 1.7,PI/2);extension.append(turn)
   neck=turn['points'][-1]
   c=[neck[0],25 if role=='signal'else 26,rowz];extension.append(line(neck,c))
   if sensor==2 and role=='return':layer=2.;target=[-2.285,46.25,0];net='GND'
   elif sensor==2:layer=2.9;target=[-1.985,43.25,0];net='PACK_GUARD'
   elif role=='signal':layer=3.8;target=[-1.985,44.75,0];net='PACK_NTC'
   else:layer=4.7;target=[-1.685,46.25,0];net='GND'
   side_x=target[0]-layer-3.
   above=[side_x,35,layer];extension+=s_curve(c,above)
   a=[side_x,target[1]-2,layer];turn=arc(a,[0,1,0],[1,0,0],2,PI/2)
   start=[target[0]-layer,target[1],layer];end=arc(start,[1,0,0],[0,0,-1],layer,PI/2)
   extension += [line(above,a),turn,line(turn['points'][-1],start),end]
   assert norm(sub(end['points'][-1],target))<1e-6
   result.append({'name':'NTC%d_%s'%(sensor,role.upper()),'net':net,'sensor':sensor,'role':role,
      'factory_OD_mm':1.1,'OD_mm':.55,'bare_end_OD_mm':.26,'bare_end_length_mm':1.5,
      'minimum_radius_mm':2. if role=='signal'else 1.65,'factory_minimum_radius_requirement_mm':5.5,'wire':'Vishay factory PVC plus Accu-Glass113094',
      'factory_sections':factory,'sections':extension,'joint_center_mm':joint,'sleeve_cut_length_mm':5.,'sleeve_installed_OD_limit_mm':2.2,
      'body_pad':'J2.4'if net=='PACK_GUARD'else'J2.3'if net=='PACK_NTC'else'J2.2S',
      'purpose':'Dry NTC, separately insulated solder transition outside the rear-stub passage; no pack-side return join'})
 return result
