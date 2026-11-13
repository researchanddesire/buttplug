"""Phone-readable native fixture/section views; no invented hidden surfaces."""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image,ImageDraw,PngImagePlugin
import render_mechanical_r2 as draw
ROOT=Path(__file__).resolve().parents[1]
CAD=ROOT/'hardware/cad/manufacturing-layout/charging-dock/contact-seal-trial'
OUT=ROOT/'developer-docs/docs/assets/contact-seal-trial.png'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((CAD/'review.json').read_text());assert sha(CAD/'ContactSealTrial.FCStd')==r['native_sha256'] and 'geometry_checks' in r
meshes=draw.NativeMeshes(CAD)
for name,values in r['exports'].items():
    for suffix,key in (('-view.stl','view_STL_sha256'),('-section-view.stl','section_view_STL_sha256')):meshes.expected[name+suffix]=values[key]
def color(n):
    if n=='ContactInnerSeal':return (170,87,182)
    if n=='FixtureOuterSeal':return (98,103,114)
    if n.startswith(('ContactPost','ContactNut')):return (210,166,67)
    if n=='ContactSealPlate':return (88,150,166)
    return (183,200,219)
draw.part_color=color
def geom(names,section=False,offsets=None):
    values=[]
    for n in names:
        t=meshes.load(n+('-section-view' if section else '-view'))
        if offsets and n in offsets:t=t+np.array(offsets[n])
        # NativeY becomes displayX: wet left, dry right in the section.
        t=t[:,:,[1,0,2]]*np.array([1,-1,1])
        values.append((n,t,None))
    return values
image=Image.new('RGB',(1200,1650),'white');d=ImageDraw.Draw(image)
draw.label(d,(28,20),'Contact feedthrough / inner seal trial',33,True)
draw.label(d,(28,68),'Saved native geometry. Two fixture prints; no physical leak result.',23,fill=draw.MUTED)
names=list(r['exports'])
draw.panel(image,(24,114,1152,570),'INERT WATER-COLUMN FIXTURE',
    'Cup and outer fixture ring moved15mm left for this exploded view.',
    geom(names,offsets={'ContactSealCup':(0,-15,0),'FixtureOuterSeal':(0,-15,0)}),camera=(.3,.35,1.2))
detail=['ContactSealPlate','ContactPost','ContactNut','ContactInnerSeal']
draw.panel(image,(24,712,1152,625),'SINGLE CONTACT / REAL NATIVE SECTION',
    'Wet side left. Purple = trial face seal between the metal post and plate.',
    geom(detail,section=True),camera=(0,0,1),focus_bounds=((-2.8,-2.7,0),(4.5,2.7,.001)))
draw.label(d,(46,1370),'Metal gland: ID2.1 / OD3.6 / depth0.38mm. Trial ring: ID2 / CS0.5mm.',23,fill=draw.MUTED)
draw.label(d,(46,1415),'The outer silicone groove captures the post; it is separate from this inner seal.',23,fill=draw.MUTED)
draw.label(d,(46,1460),'Fixture cup uses an8 x1.5mm ring and a gravity-fed water column.',23,fill=draw.MUTED)
draw.label(d,(46,1505),'Printed rough faces check assembly only. Machined finish and cure coupons follow.',23,fill=draw.MUTED)
draw.label(d,(46,1550),'Material, preload, aging, complete cavity/buttons and wet qualification remain open.',23,fill=draw.MUTED)
meshes.verify()
meta={'native_sha256':r['native_sha256'],'review_sha256':sha(CAD/'review.json'),'renderer_sha256':sha(Path(__file__)),
    'meshes_sha256':meshes.used,'scope':'Native fixture exploded view and unchanged Z0 section/crop. Display rotation maps wet side left. Ring ellipse is an installed-space model, not FEA. No physical assembly or leak result.'}
info=PngImagePlugin.PngInfo();info.add_text('Source',json.dumps(meta,sort_keys=True));image.save(OUT,pnginfo=info)
OUT.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n');print(OUT)
