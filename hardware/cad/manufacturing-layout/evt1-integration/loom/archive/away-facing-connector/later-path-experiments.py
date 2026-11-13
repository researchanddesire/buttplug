"""EVT wire-form geometry in the product frame, in mm.

The SH wire-center height is a fixture target inside the mated envelope,
not a controlled OEM exit dimension. Validate the first received assembly.
"""
import math
import numpy as np

def point(v):return np.asarray(v,dtype=float)
def line(a,b):return {'kind':'line','points':[list(a),list(b)]}
def bezier(p):return {'kind':'bezier','points':[list(v) for v in p]}
def ease(a,b):
    """Quintic lateral easing with linearY and axial tangents at both ends."""
    a,b=point(a),point(b)
    return bezier([[*(a if i<3 else b)[:1],a[1]+(b[1]-a[1])*i/5,*(a if i<3 else b)[2:]] for i in range(6)])
def curve(p,t):
    p=np.asarray(p);q=p.copy()
    for n in range(len(p)-1,0,-1):q[:n]=(1-t)*q[:n]+t*q[1:n+1]
    return q[0]
def derivative(p,t):
    p=np.asarray(p);return curve((len(p)-1)*np.diff(p,axis=0),t)
def sampled(points,first,last):return {'kind':'bspline','points':[list(v) for v in points],'first_tangent':list(first),'last_tangent':list(last)}
def quarter(start,direction,end_direction,radius):
    p=point(start);a=point(direction);b=point(end_direction)
    assert abs(np.dot(a,b))<1e-9 and abs(np.linalg.norm(a)-1)<1e-9 and abs(np.linalg.norm(b)-1)<1e-9
    mid=p+radius*(math.sqrt(.5)*a+(1-math.sqrt(.5))*b)
    end=p+radius*(a+b)
    return {'kind':'arc','points':[list(p),list(mid),list(end)]}

def interboard(product,body_mcad,flange_mcad):
    bodies={int(p['number']):p for p in body_mcad['pads'] if p['ref']=='J6' and p['number'].isdigit()}
    flanges={int(p['number']):p for p in flange_mcad['pads'] if p['ref']=='J7' and p['number'].isdigit()}
    assert set(bodies)==set(flanges)==set(range(1,11))
    y0=product['bounds']['Body_J6_Mate'][1]
    z0=product['bounds']['BodyPCB'][5]+1.4
    yend=product['bounds']['FlangePCB'][4]+1.4
    zend=product['bounds']['Flange_J7_Mate'][5]
    # Split alternating pins into two rows. Keep their layer separation
    # through the flange fan and use alternate final bend radii.
    # The broad rising bend carries its upward tangent into the fan instead
    # of flattening and immediately rising again. Parallel transport and a
    # gradual40deg roll keep each row horizontal across the flange.
    phi=math.radians(40);first_radius=7.6
    trunk_start_y=-16.5+first_radius
    d0=np.array([0.,-1,0]);diagonal=np.array([-math.cos(phi),0,math.sin(phi)])
    axis=np.cross(d0,diagonal);u0=np.array([1.,0,0])
    def rotate(v,k,a):return v*math.cos(a)+np.cross(k,v)*math.sin(a)+k*np.dot(k,v)*(1-math.cos(a))
    natural=rotate(u0,axis,math.pi/2)
    roll=math.atan2(np.dot(diagonal,np.cross(natural,(0,-1,0))),np.dot(natural,(0,-1,0)))
    answer=[]
    for i in range(10):
        number=i+1;u=(i//2-2)*.8;v=-.4 if i%2==0 else .4
        R=4 if i%2==0 else 4.8
        start=np.array([bodies[number]['xy_mm'][0],y0,z0]);p1=start+np.array([0,-2,0])
        p2=np.array([start[0],24,z0+v]);p3=np.array([u,12,z0+v])
        sections=[line(start,p1),ease(p1,p2),ease(p2,p3)]
        twist=[]
        for t in np.linspace(0,1,81):
            f=10*t**3-15*t**4+6*t**5;angle=0.
            twist.append((u*math.cos(angle)-v*math.sin(angle),12+(trunk_start_y-12)*t,z0+(2-z0)*f+u*math.sin(angle)+v*math.cos(angle)))
        sections.append(sampled(twist,(0,-1,0),(0,-1,0)))
        bank=[];center_start=np.array([0,trunk_start_y,2.])
        for t in np.linspace(0,1,101):
            theta=t*math.pi/2;d=math.cos(theta)*d0+math.sin(theta)*diagonal
            p=center_start+first_radius*(math.sin(theta)*d0+(1-math.cos(theta))*diagonal)
            transverse=rotate(rotate(u0,axis,theta),d,roll*(10*t**3-15*t**4+6*t**5))
            vertical=np.cross(d,transverse);bank.append(p+u*transverse+v*vertical)
        sections.append(sampled(bank,d0,diagonal))
        bank2=[bank[-1],bank[-1]+2*diagonal]
        sections.append(line(*bank2))
        target=np.array([flanges[number]['xy_mm'][0]+1.5,yend,zend])
        # Alternating layers preserve wire order through the fan. A steep
        # common diagonal separates adjacent final bends by0.75mm normal to
        # their horizontal tangent, before their1mm-pitch vertical ends.
        ey=-.75
        e=np.array([-math.sqrt(1-ey*ey),ey,0.])
        arc_start=target-R*e+np.array([0,0,R+1])
        dx=bank2[-1][0]-arc_start[0]
        sections.append(bezier([bank2[-1],bank2[-1]+diagonal*(dx/(3*math.cos(phi))),arc_start-e*5,arc_start]))
        arc=quarter(arc_start,e,(0,0,-1),R);sections.append(arc)
        sections.append(line(arc['points'][-1],target))
        assert bodies[number]['net']==flanges[number]['net']
        answer.append({'name':'IB'+str(number).zfill(2),'harness':'W-INTERBOARD-EVT1','net':bodies[number]['net'],
            'start':{'domain':'body','ref':'J6','pin':str(number),'kind':'SH wire-exit plane'},
            'end':{'domain':'flange','ref':'J7','pin':str(number),'kind':'SH wire-exit plane'},
            'wire':'AG100690','OD_mm':.6,'minimum_centerline_radius_mm':4,'sections':sections})
    return answer
