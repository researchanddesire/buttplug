"""Phone-readable review figures from the checked native dock/contact meshes."""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
from PIL import Image, ImageDraw, PngImagePlugin
import render_mechanical_r2 as draw

ROOT=Path(__file__).resolve().parents[1]
FOLDER=Path(sys.argv[1]).resolve()
OUT=Path(sys.argv[2]).resolve() if len(sys.argv)>2 else ROOT/'developer-docs/docs/assets'
OUT.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((FOLDER/'review.json').read_text())
assert sha(FOLDER/'ChargingDock.FCStd')==r['native_sha256']
assert 'geometry_checks' in r,'Verify saved native before rendering'
meshes=draw.NativeMeshes(FOLDER)
for values in r['exports'].values():
    name=values['label']
    meshes.expected[name+'-view.stl']=values['view_STL_sha256']
    if 'section_view_STL_sha256' in values:
        meshes.expected[name+'-section-view.stl']=values['section_view_STL_sha256']
meshes.expected.update(r['render_meshes'])


def color(name):
    if name.startswith('TargetSeal_'):return (165,85,185)
    if name.startswith(('Target_','SeatedTarget_','PogoBarrel_','PogoPlunger_','TargetNut_')): return (206,161,62)
    if name in ('DockBase','DockLid','DockLidOpen'): return (229,119,53)
    if name.startswith(('SeatedMetal','BodyReference','CapReference')): return (184,193,202)
    if name in ('FourContactSkin','SeatedSiliconeSkin'): return (119,166,145)
    if name=='FourContactRearHalf': return (93,145,153)
    if name in ('PinPCBBlank','DockUSBPCB'): return (65,142,102)
    if name=='USBComponent_J91': return (184,193,202)
    if name.startswith('USBComponent_U'): return (60,65,70)
    if name.startswith('USBComponent_'): return (173,153,114)
    if name.startswith(('DockMagnet','MagnetBack','BuriedSteel')): return (100,111,125)
    if name.startswith('ContactMold'): return (138,162,191)
    if name=='ContactFaceMask': return (203,167,105)
    return (218,213,193)


draw.part_color=color


def panel(canvas,box,title,subtitle,geometry,*,camera=(1,1,2),focus_bounds=None):
    """Orthographic triangle depth buffer; hidden CAD faces never show through.

    Existing shared renderer utilities supply colors, camera basis and type.
    Depth is interpolated per pixel rather than sorting long triangles by mean.
    """
    x,y,w,h=box
    drawing=ImageDraw.Draw(canvas)
    drawing.rounded_rectangle((x,y,x+w,y+h),radius=18,fill='#f5f7fa',outline='#dbe3ec',width=2)
    draw.label(drawing,(x+24,y+20),title,25,True)
    draw.label(drawing,(x+24,y+63),subtitle,19,fill=draw.MUTED)
    cam,right,up=draw.camera_basis(camera)
    light=.7*cam+.6*up-.3*right
    light/=np.linalg.norm(light)
    if focus_bounds:
        import itertools
        vertices=np.array(list(itertools.product(*zip(*focus_bounds))))
    else:
        vertices=np.concatenate([tri.reshape(-1,3) for _,tri,_ in geometry])
    u,v=vertices@right,vertices@up
    rw,rh=w-12,h-130
    scale=min((w-80)/np.ptp(u),(h-155)/np.ptp(v))
    cx=rw/2-(u.max()+u.min())/2*scale
    cy=rh/2+(v.max()+v.min())/2*scale
    rgb=np.full((rh,rw,3),(245,247,250),dtype=np.uint8)
    depth=np.full((rh,rw),-np.inf,dtype=float)
    for name,triangles,_ in geometry:
        normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
        normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-12)
        shade=.60+.40*np.maximum(normals@light,0)
        projected=np.stack((cx+triangles@right*scale,cy-triangles@up*scale),axis=-1)
        distances=triangles@cam
        for index in np.flatnonzero(normals@cam>1e-10):
            pts=projected[index]
            low=np.maximum(np.floor(pts.min(axis=0)).astype(int),(0,0))
            high=np.minimum(np.ceil(pts.max(axis=0)).astype(int),(rw-1,rh-1))
            if np.any(low>high): continue
            a,b,c=pts
            denominator=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
            if abs(denominator)<1e-12: continue
            yy,xx=np.ogrid[low[1]:high[1]+1,low[0]:high[0]+1]
            xx=xx+.5; yy=yy+.5
            wa=((b[1]-c[1])*(xx-c[0])+(c[0]-b[0])*(yy-c[1]))/denominator
            wb=((c[1]-a[1])*(xx-c[0])+(a[0]-c[0])*(yy-c[1]))/denominator
            wc=1-wa-wb
            z=wa*distances[index,0]+wb*distances[index,1]+wc*distances[index,2]
            tile=depth[low[1]:high[1]+1,low[0]:high[0]+1]
            selected=(wa>=-1e-8)&(wb>=-1e-8)&(wc>=-1e-8)&(z>tile+1e-8)
            tile[selected]=z[selected]
            rgb[low[1]:high[1]+1,low[0]:high[0]+1][selected]=np.array(color(name))*shade[index]
    canvas.paste(Image.fromarray(rgb),(x+6,y+106))


def geom(name,section=False,dock=False,delta=None):
    triangles=meshes.load(name+('-section-view' if section else '-view'))
    if delta is not None: triangles=triangles+np.array(delta)
    if dock:
        # Display-only global rotation: native Z-up becomes the renderer's Y-up.
        triangles=triangles[:,:,[0,2,1]]*np.array([1,1,-1])
    return (name,triangles,None)


def save(canvas,name,scope):
    meshes.verify()
    meta={'native_sha256':r['native_sha256'],'review_sha256':sha(FOLDER/'review.json'),
          'renderer_sha256':sha(Path(__file__)),'meshes_sha256':meshes.used.copy(),'scope':scope}
    info=PngImagePlugin.PngInfo()
    info.add_text('Source',json.dumps(meta,sort_keys=True))
    path=OUT/(name+'.png')
    canvas.save(path,pnginfo=info)
    path.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(path)


nets=[c['net'] for c in r['contacts']]
case=Image.new('RGB',(1660,1700),'white')
d=ImageDraw.Draw(case)
draw.label(d,(30,20),'Charging dock / PCB and print integration',32,True)
draw.label(d,(30,70),'Rounded clamshell and guided magnetic contacts, shown from saved native CAD.',22,fill=draw.MUTED)
open_names=['DockBase','DockNest','PogoCarrier','PogoRetainer','DockLidOpen','SeatedMetalBody','SeatedMetalCap','SeatedSiliconeSkin']
open_names+=['SeatedTarget_'+net for net in nets]
panel(case,(20,115,1620,880),'OPEN / DEVICE SEATED',
           'Lid at 110 degrees. Lower at +3 mm, then slide toward the contacts.',
           [geom(n,dock=True) for n in open_names],camera=(-1.05,.95,1.6))
panel(case,(20,1015,790,470),'CLOSED / DRY STORAGE',
           '166 x 115 x 65 mm including hinge/latch.',
           [geom('DockBase',dock=True),geom('DockLid',dock=True)],camera=(-1.1,.9,1.6))
panel(case,(830,1015,810,470),'REMOVABLE PIN HEAD / FRONT',
           'Spring pins in dock; fixed targets in device.',
           [geom(n,dock=True) for n in ['PogoCarrier']+['PogoPlunger_'+net for net in nets]],camera=(.3,.2,-3))
d=ImageDraw.Draw(case)
draw.label(d,(32,1520),'First print uses a screw closure and solid opaque lid. Screen/buttons remain optional.',22)
draw.label(d,(32,1565),'EVT1 cradle PCBs are routed. Physical USB, power, retention and seals remain untested.',22,fill=draw.AMBER)
draw.label(d,(32,1610),'Print STLs + native/STEP + assembly notes are saved. Physical fit, holding and USB need trials.',22,fill=draw.MUTED)
save(case,'charging-dock','Actual native meshes; display-only Z-up rotation. Open lid is a native-derived -110degree hinge rotation. No physical build or electrical validation.')

detail=Image.new('RGB',(1660,1550),'white')
d=ImageDraw.Draw(detail)
draw.label(d,(30,20),'Four fixed contacts through the silicone',34,True)
draw.label(d,(30,70),'GND / USB D- / USB D+ / 5V, at 6 mm pitch. Row is along the flange edge.',22,fill=draw.MUTED)
parts=[geom('FourContactRearHalf',section=True,delta=(0,40,32)),geom('FourContactSkin',section=True,delta=(0,40,32))]
parts += [geom(prefix+net,section=True,delta=(0,40,32)) for prefix in ('Target_','TargetNut_','TargetSeal_') for net in nets]
parts += [geom('PogoCarrier',section=True),geom('PogoRetainer',section=True),geom('PinPCBBlank',section=True)]
parts += [geom(prefix+net,section=True) for prefix in ('PogoBarrel_','PogoPlunger_') for net in nets]
panel(detail,(20,115,1620,610),'MATED INTERFACE / NATIVE SECTION THROUGH THE CONTACT ROW',
           'Green: skin. Blue: rear half. Gold: metal. Cream: dock. Dark green: PCB envelope. White: cavity.',
           parts,camera=(0,0,3),focus_bounds=((-41,5.5,43.5),(-17,21,49.5)))
panel(detail,(20,745,790,535),'REMOVABLE CONTACT-FACE MASK',
           'Pull mask along -Y FIRST, then split the main mold.',
           [geom('ContactFaceMask'),geom('ContactMoldHalfB',delta=(0,0,25))],camera=(-.3,-1,-2.5))
panel(detail,(830,745,810,535),'REAR HALF / POSTS AND BURIED KEEPERS',
           'Keeper discs replace permanent device magnets.',
           [geom('FourContactRearHalf')]+[geom('Target_'+net) for net in nets]+[geom('BuriedSteelKeeper0'),geom('BuriedSteelKeeper1')],
           camera=(.15,-3,1.3))
d=ImageDraw.Draw(detail)
draw.label(d,(32,1310),'4 mm fixed heads stand 0.3 mm proud. Silicone wraps the machined groove; metal bears on plastic.',22,True)
draw.label(d,(32,1358),'Nominal pin compression: 0.6 mm, set at the metal faces. Retention magnets live in the dock.',22)
draw.label(d,(32,1406),'A groove does not prove sealing. Contact finish, bonds, nut retention and magnetic holding need tests.',22,fill=draw.AMBER)
draw.label(d,(32,1454),'Threads and pin contours are engineering envelopes. No liquid-tight, USB or human-use result.',22,fill=draw.MUTED)
save(detail,'charging-interface','Native planar section profiles at sourceZ11.5/dockZ43.5; view meshes intentionally open. Source profiles translated40Y/32Z. MoldB exploded25Z for visibility, not a qualified opening path. Geometry only.')

electronics=Image.new('RGB',(1660,1450),'white')
d=ImageDraw.Draw(electronics)
draw.label(d,(30,20),'Two routed PCB designs inside the cradle',34,True)
draw.label(d,(30,70),'Native routed boards drive the mechanical datums. Component bodies are conservative envelopes.',21,fill=draw.MUTED)
panel(electronics,(20,115,1620,620),'USB-C BOARD / CASE WALL AND MOUNTS',
      'Narrow PCB nose brings the GCT socket face flush with the wall. Four M2 screws hold the board.',
      [geom(n,dock=True) for n in ['DockBase','DockUSBPCB']+r['usb_board']['component_roles']],
      camera=(1.2,2,.7),focus_bounds=((-58,2,-66),(-25,12,-41)))
panel(electronics,(20,755,1620,430),'PIN BOARD / OPEN REAR WIRE EXIT',
      'Loom pads are on the rear face, beside the lower edge. Retainer shown 10 mm away for visibility.',
      [geom('PogoCarrier',dock=True),geom('PinPCBBlank',dock=True),geom('PogoRetainer',dock=True,delta=(0,-10,0))],
      camera=(.2,1.5,3),focus_bounds=((-47,33,-14),(-9,53,7)))
d=ImageDraw.Draw(electronics)
draw.label(d,(32,1220),'USB-C  ->  current-limited input board  ->  four-wire loom  ->  spring-pin board',26,True)
draw.label(d,(32,1270),'Contact order: GND / D- / D+ / 5V. Pins move in the dock; device targets remain fixed.',22)
draw.label(d,(32,1320),'Print the carrier, retainer and case; fabricate FR4 PCBs from the electrical files.',22)
draw.label(d,(32,1370),'Digital layout and fit checks only. Full product EVT integration and physical qualification continue.',21,fill=draw.AMBER)
save(electronics,'charging-dock-electronics','Native board outlines and footprint body envelopes linked by PCB SHA256. Retainer exploded for visibility, not an assembly-motion claim. No physical result.')
