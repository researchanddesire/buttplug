"""Deterministic ten-wire centreline candidate, product mm; no CAD imports.

Wire-exit height is a measured-first-article parameter, not OEM control data.
The cylindrical passage is checked later against native metal/nut geometry.
"""
import math,json
from pathlib import Path

def line(a,b):return {'kind':'line','points':[a,b]}
def ease(a,b,axis):
 p=[]
 for i in range(6):
  v=list(a if i<3 else b);v[axis]=a[axis]+(b[axis]-a[axis])*i/5;p.append(v)
 return {'kind':'bezier','points':p}
def quarter(a,r=4.5):
 return {'kind':'arc','points':[a,[a[0]-r*(1-math.sqrt(.5)),a[1]-r*math.sqrt(.5),a[2]],[a[0]-r,a[1]-r,a[2]]]}
def make_plan(exit_w=1.51):
 result=[];dy=exit_w-1.51
 for i in range(10):
  n=i+1;u=i-4.5;first=[u,31.525,exit_w];a=[u,29.525,exit_w]
  b=[u*.65,16,exit_w];twist=[]
  for j in range(121):
   t=j/120;f=10*t**3-15*t**4+6*t**5;angle=math.pi*.5*f
   pitch=.65+.35*f
   twist.append([2.775*f+u*pitch*math.cos(angle),16-24*t,
                 exit_w*(1-f)-u*pitch*math.sin(angle)])
  bend_start=[2.775,-19.942+dy,-u];bend=quarter(bend_start)
  end=[-2.525,-24.442+dy,-u]
  result.append({'pin':n,'wire':'Accu-Glass100690','OD_mm':.6,'centreline_min_radius_requirement_mm':4.,
   'wire_exit_w_mm':exit_w,'sections':[line(first,a),ease(a,b,1),
    {'kind':'bspline','points':twist,'first_tangent':[0,-1,0],'last_tangent':[0,-1,0]},
    line(twist[-1],bend_start),bend,line(bend['points'][-1],end)]})
 return result
if __name__=='__main__':
 p=Path(__file__).with_name('path-plan.json')
 p.write_text(json.dumps({'status':'Centreline candidate; native fit/curvature checks required',
  'wire_exit_w_is_received_parameter':True,'wires':make_plan()},indent=2)+'\n')
 print(p)
