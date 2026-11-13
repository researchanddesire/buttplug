"""Phone-readable EVT1 board fit views from verified native CAD meshes."""
from pathlib import Path
import hashlib
import itertools
import json
import numpy as np
from PIL import Image,ImageDraw,PngImagePlugin
import render_mechanical_r2 as draw

ROOT=Path(__file__).resolve().parents[1]
CAD=ROOT/'hardware/cad/manufacturing-layout/evt1-integration'
OUT=ROOT/'developer-docs/docs/assets/evt1-product.png'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((CAD/'review.json').read_text())
assert sha(CAD/'EVT1Product.FCStd')==r['native_sha256'] and 'geometry_checks' in r
meshes=draw.NativeMeshes(CAD)
meshes.expected={n+'-view.stl':v['view_STL_sha256'] for n,v in r['exports'].items()}
def color(n):
    if n.startswith('PackNTC'):return (223,132,54)
    if n=='PackSizeReference':return (98,139,197)
    if n.startswith(('Contact_','ContactNut_','RearNut')):return (210,164,65)
    if n.endswith('PCB'):return (48,141,91)
    if n.startswith(('FlangeTray','RearHalf')):return (99,155,172)
    if n.startswith(('MetalBody','MotorThermistorCap')):return (176,188,201)
    if n.startswith(('MotorReference','MotorLeadExitAllowance')):return (204,151,66)
    if n=='BatteryPowerConnector':return (221,214,187)
    if n.startswith('SensorScrew'):return (231,221,193)
    if 'Sleeve' in n:return (135,149,170)
    if 'Foam' in n:return (104,112,126)
    if 'Mate' in n or '_J' in n:return (221,214,187)
    return (66,69,74)
def geometry(names,flange=False,delta=None):
    values=[]
    for name in names:
        t=meshes.load(name+'-view')
        if delta is not None:t=t+np.array(delta)
        if flange:t=t[:,:,[0,2,1]]*np.array([1,1,-1])
        values.append((name,t))
    return values
def panel(canvas,xywh,title,subtitle,items,camera):
    x,y,w,h=xywh;d=ImageDraw.Draw(canvas)
    d.rounded_rectangle((x,y,x+w,y+h),18,fill='#f5f7fa',outline='#dbe3ec',width=2)
    draw.label(d,(x+22,y+16),title,27,True);draw.label(d,(x+22,y+59),subtitle,20,fill=draw.MUTED)
    cam,right,up=draw.camera_basis(camera);light=.7*cam+.6*up-.3*right;light/=np.linalg.norm(light)
    vertices=np.concatenate([t.reshape(-1,3) for _,t in items]);u,v=vertices@right,vertices@up
    rw,rh=w-12,h-115;scale=min((rw-50)/np.ptp(u),(rh-25)/np.ptp(v))
    cx=rw/2-(u.min()+u.max())/2*scale;cy=rh/2+(v.min()+v.max())/2*scale
    rgb=np.full((rh,rw,3),(245,247,250),np.uint8);depth=np.full((rh,rw),-np.inf)
    for name,t in items:
        normal=np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]);normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-12)
        shade=.6+.4*np.maximum(normal@light,0);p=np.stack((cx+t@right*scale,cy-t@up*scale),axis=-1);distance=t@cam
        for i in np.flatnonzero(normal@cam>1e-10):
            pts=p[i];lo=np.maximum(np.floor(pts.min(axis=0)).astype(int),(0,0));hi=np.minimum(np.ceil(pts.max(axis=0)).astype(int),(rw-1,rh-1))
            if np.any(lo>hi):continue
            a,b,c=pts;den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(den)<1e-12:continue
            yy,xx=np.ogrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1];xx=xx+.5;yy=yy+.5
            wa=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/den
            wb=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/den;wc=1-wa-wb
            z=wa*distance[i,0]+wb*distance[i,1]+wc*distance[i,2];tile=depth[lo[1]:hi[1]+1,lo[0]:hi[0]+1]
            selected=(wa>=-1e-8)&(wb>=-1e-8)&(wc>=-1e-8)&(z>tile+1e-8);tile[selected]=z[selected]
            rgb[lo[1]:hi[1]+1,lo[0]:hi[0]+1][selected]=np.array(color(name))*shade[i]
    canvas.paste(Image.fromarray(rgb),(x+6,y+100))

def module(domain):
    return [r['boards'][domain]['role']]+[n for n,v in r['components'].items() if v['domain']==domain]
image=Image.new('RGB',(1200,1600),'white');d=ImageDraw.Draw(image)
draw.label(d,(28,20),'EVT1 / actual boards in the four-part assembly',31,True)
draw.label(d,(28,67),'Saved native CAD. Nominal geometry checks pass; no physical build yet.',22,fill=draw.MUTED)
flange=['FlangeTray','RearNutReference']+module('flange')+module('sensor')+[n for v in r['sensor_screw_refs'].values() for n in v]
panel(image,(24,112,1152,620),'Open flange / boards installed','Rear half and pack omitted for this assembly step.',geometry(flange,True),(.25,.35,1.0))
draw.label(d,(46,685),'Left: control / USB PCB     Right: fixed compass board on two integral bosses',20,fill=draw.MUTED)
body=['MotorThermistorCap','MotorReference','MotorLeadExitAllowance','TipThermistor']+module('body')
g=geometry(body)+geometry(['MetalBody'],delta=(48,0,0))
panel(image,(24,750,1152,680),'Cap module and straight-bore body','Body translated sideways for display; board / motor positions stay native.',g,(.7,.15,1.8))
draw.label(d,(46,1448),'Green = actual PCB outline    Dark = component height envelopes',21,fill=draw.MUTED)
draw.label(d,(46,1487),'Amber motor includes a separate 6 mm rear lead-exit allowance.',21,fill=draw.MUTED)
draw.label(d,(46,1526),'Contact and clamshell print files remain in the separate dock kit.',21,fill=draw.MUTED)
meshes.verify()
meta={'native_sha256':r['native_sha256'],'review_sha256':sha(CAD/'review.json'),'renderer_sha256':sha(Path(__file__)),
      'meshes_sha256':meshes.used,'scope':'Native CAD review; display offsets documented above; no physical fit result'}
info=PngImagePlugin.PngInfo();info.add_text('Source',json.dumps(meta,sort_keys=True))
image.save(OUT,pnginfo=info);OUT.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n')
print(OUT)

packout=OUT.with_name('evt1-pack.png')
image=Image.new('RGB',(1200,1150),'white');d=ImageDraw.Draw(image)
draw.label(d,(28,20),'EVT1 / protected-pack interface',32,True)
draw.label(d,(28,67),'Requested supplier maximum, not an approved or received pack.',23,fill=draw.MUTED)
names=['PackSizeReference','PackNTC0','PackNTC1','BatteryPowerConnector']+module('sensor')
panel(image,(24,112,1152,685),'Pack and two independent temperature sensors','Plastic halves omitted to expose the dry internal interface.',geometry(names,True),(.15,.25,-1.0))
draw.label(d,(46,830),'Blue: requested 33 x 21 x 6.3 mm protected pack, PCM / leads toward the neck.',22,fill=draw.MUTED)
draw.label(d,(46,875),'Orange: two tape-coupled NTC head / transition envelopes on the broad face.',22,fill=draw.MUTED)
draw.label(d,(46,920),'Growth space: +1.1 mm thickness and +0.25 mm per lateral side reserved in CAD.',22,fill=draw.MUTED)
draw.label(d,(46,965),'Six conductors; ACH power disconnect allowance. Retention / lead routes remain open.',22,fill=draw.MUTED)
draw.label(d,(46,1010),'1.5 A continuous / 2 A for 100 ms requested. Supplier acceptance pending.',22,fill=draw.MUTED)
meshes.verify()
meta={'native_sha256':r['native_sha256'],'review_sha256':sha(CAD/'review.json'),'renderer_sha256':sha(Path(__file__)),
      'pack_spec_sha256':r['pack_spec_sha256'],'meshes_sha256':meshes.used,
      'scope':'Native requested-pack and two NTC envelopes; plastics omitted; no supplied/validated battery or physical assembly'}
info=PngImagePlugin.PngInfo();info.add_text('Source',json.dumps(meta,sort_keys=True))
image.save(packout,pnginfo=info);packout.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n')
print(packout)
