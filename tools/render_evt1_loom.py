"""Phone-readable wire views from the checked native product/loom meshes."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image,ImageDraw,PngImagePlugin
import render_mechanical_r2 as draw
ROOT=Path(__file__).resolve().parents[1]
PRODUCT=ROOT/'hardware/cad/manufacturing-layout/evt1-integration';LOOM=PRODUCT/'loom'
OUT=ROOT/'developer-docs/docs/assets/evt1-loom.png'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((LOOM/'review.json').read_text());p=json.loads((PRODUCT/'review.json').read_text())
assert r['geometry_checks']['pass'] and sha(LOOM/'EVT1Loom.FCStd')==r['native_sha256']
assert sha(PRODUCT/'EVT1Product.FCStd')==r['source_product_native_sha256']==p['native_sha256']
assert sha(PRODUCT/'review.json')==r['geometry_checks']['verified_product_review_sha256']
assert sha(ROOT/'tools/evt1_loom_paths.py')==r['path_builder_sha256']
assert sha(ROOT/'tools/build_evt1_loom_cad.py')==r['builder_sha256']
assert sha(ROOT/'tools/verify_evt1_loom_cad.py')==r['geometry_checks']['verifier_sha256']
product=draw.NativeMeshes(PRODUCT);product.expected={n+'-view.stl':v['view_STL_sha256'] for n,v in p['exports'].items()}
loom=draw.NativeMeshes(LOOM);loom.expected={n+'-view.stl':v['view_STL_sha256'] for n,v in r['exports'].items()}
base_color=draw.part_color
def color(name):
    if name.startswith('IB'):return (218,133,41) if int(name[2:])%2 else (62,134,171)
    if name.endswith('PCB'):return (55,139,93)
    if 'Mate' in name or '_J' in name:return (217,210,183)
    if name=='Flange_D73':return (76,80,88)
    return base_color(name)
draw.part_color=color
wires=[(v['name'],loom.load(v['name']+'-view'),None) for v in r['wires']]
def context(names):return [(n,product.load(n+'-view'),None) for n in names]
canvas=Image.new('RGB',(1400,1550),'white');d=ImageDraw.Draw(canvas)
draw.label(d,(28,20),'EVT1 / neck-facing interboard harness',34,True)
draw.label(d,(28,69),'Ten native wire forms between the actual body and flange connectors.',23,fill=draw.MUTED)
draw.panel(canvas,(22,112,1356,760),'BODY CONNECTOR / NECK / FLANGE CONNECTOR',
    'Metal shell and plastic halves hidden to expose the paths.',
    wires+context(['BodyPCB','Body_J6','Body_J6_Mate','FlangePCB','Flange_J7','Flange_J7_Mate']),
    camera=(-1,.6,1.2),focus_bounds=((-25,-20,-5),(7,34,10)))
flange=[(n,t[:,:,[0,2,1]]*np.array([1,1,-1]),role) for n,t,role in
        wires+context(['FlangePCB','Flange_J7','Flange_J7_Mate','Flange_D73'])]
draw.panel(canvas,(22,892,1356,430),'J7 / FINAL FAN AND S BEND',
    'Oblique front view; 1 mm connector pitch. Other parts omitted.',flange,
    camera=(.35,.15,-1),focus_bounds=((-24,-5,13),(-10,9,20)))
g=r['geometry_checks'];radius=min(v['sampled_minimum_bend_radius_mm'] for v in g['checks'].values())
draw.label(d,(36,1353),f'Nominal sampled minimum bend radius {radius:.3f} mm; minimum wire gap {g["minimum_wire_surface_distance_mm"]:.3f} mm.',23,fill=draw.MUTED)
draw.label(d,(36,1396),'Colors distinguish paths; the actual interboard wire is amber/brown.',23,fill=draw.MUTED)
draw.label(d,(36,1439),'SH egress, crimps, forming, restraint and the other ten neck conductors need trials.',23,fill=draw.MUTED)
draw.label(d,(36,1482),'Static CAD evidence only. Keep 120 mm starting blanks; no finished-cut drawing.',23,fill='#a8641a')
product.verify();loom.verify()
meta={'native_sha256':r['native_sha256'],'loom_review_sha256':sha(LOOM/'review.json'),'source_product_native_sha256':p['native_sha256'],
      'renderer_sha256':sha(Path(__file__)),'wire_meshes_sha256':loom.used,'product_meshes_sha256':product.used,
      'scope':'Unmodified native mesh views with shells/other parts hidden and explicit viewport crops; path colors are illustrative; no physical assembly result'}
info=PngImagePlugin.PngInfo();info.add_text('Source',json.dumps(meta,sort_keys=True));canvas.save(OUT,pnginfo=info)
OUT.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n');print(OUT)
