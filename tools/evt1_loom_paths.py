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

def ease_axis(a,b,axis):
    a,b=point(a),point(b);p=[]
    for i in range(6):
        v=(a if i<3 else b).copy();v[axis]=a[axis]+(b[axis]-a[axis])*i/5;p.append(v)
    return bezier(p)

def circular_turn(start,direction,normal,radius,angle):
    p=point(start);d=point(direction);n=point(normal)
    at=lambda t:p+radius*(math.sin(t)*d+(1-math.cos(t))*n)
    return {'kind':'arc','points':[list(p),list(at(angle/2)),list(at(angle))]}

def interboard(product,body_mcad,flange_mcad):
    bodies={int(p['number']):p for p in body_mcad['pads'] if p['ref']=='J6' and p['number'].isdigit()}
    flanges={int(p['number']):p for p in flange_mcad['pads'] if p['ref']=='J7' and p['number'].isdigit()}
    header=next(v for v in flange_mcad['components'] if v['ref']=='J7')
    assert abs(header['angle_deg']+90)<1e-6,'Route requires the neck-facing J7 placement, not the prior board'
    assert set(bodies)==set(flanges)==set(range(1,11))
    y0=product['bounds']['Body_J6_Mate'][1];z0=product['bounds']['BodyPCB'][5]+1.4
    target_x=product['bounds']['Flange_J7_Mate'][3]
    target_y=product['bounds']['FlangePCB'][4]+1.4
    center_z=sum(p['xy_mm'][1]+17.5125 for p in flanges.values())/10
    flat_y=target_y+.8;turn_radius=4.5;turn_y=flat_y+turn_radius
    fan_end_x=-13.8;length=fan_end_x-target_x;drop=flat_y-target_y
    s_radius=(length*length+drop*drop)/(4*drop)
    assert length>0 and s_radius>=4.05,(length,s_radius)
    angle=2*math.atan(drop/length);answer=[]
    for i in range(10):
        number=i+1;u=(i-4.5)*.65
        start=np.array([bodies[number]['xy_mm'][0],y0,z0]);p1=start+(0,-2,0)
        p2=np.array([u,16,center_z]);sections=[line(start,p1),ease_axis(p1,p2,1)]
        # Turn the flat row into a vertical row while it is still in the bore.
        neck=[]
        for t in np.linspace(0,1,101):
            f=10*t**3-15*t**4+6*t**5;theta=math.pi/2*f
            neck.append((u*math.cos(theta),16-24*t,center_z-u*math.sin(theta)))
        sections.append(sampled(neck,(0,-1,0),(0,-1,0)))
        a=np.array([0,turn_y,center_z-u]);sections.append(line(neck[-1],a))
        bend=quarter(a,(0,-1,0),(-1,0,0),turn_radius);sections.append(bend)
        target_z=flanges[number]['xy_mm'][1]+17.5125
        fan_end=np.array([fan_end_x,flat_y,target_z])
        sections.append(ease_axis(bend['points'][-1],fan_end,0))
        first=circular_turn(fan_end,(-1,0,0),(0,-1,0),s_radius,angle);sections.append(first)
        d=(-math.cos(angle),-math.sin(angle),0);n=(-math.sin(angle),math.cos(angle),0)
        second=circular_turn(first['points'][-1],d,n,s_radius,angle);sections.append(second)
        target=np.array([target_x,target_y,target_z]);assert np.linalg.norm(point(second['points'][-1])-target)<1e-8
        assert bodies[number]['net']==flanges[number]['net']
        answer.append({'name':'IB'+str(number).zfill(2),'harness':'W-INTERBOARD-EVT1','net':bodies[number]['net'],
            'start':{'domain':'body','ref':'J6','pin':str(number),'kind':'SH wire-exit plane'},
            'end':{'domain':'flange','ref':'J7','pin':str(number),'kind':'SH wire-exit plane'},
            'wire':'AG100690','OD_mm':.6,'minimum_centerline_radius_mm':4,'sections':sections})
    return answer
