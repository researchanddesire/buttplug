"""Cold native checks: actual purchased LCD, rigid joints, FFC and UI endpoints."""
from pathlib import Path
import hashlib,json,runpy,sys
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
M=runpy.run_path(str(ROOT/'tools/build_evt1_dock_lcd_retention.py'));V=App.Vector
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
build_report=json.loads((HERE/'review.json').read_text())
assert build_report['builder_sha256']==sha(ROOT/'tools/build_evt1_dock_lcd_retention.py')
assert build_report['display_builder_sha256']==sha(ROOT/'tools/build_evt1_dock_display.py')
assert build_report['display_source_manifest_sha256']==sha(ROOT/'hardware/cad/evt1-assembly/vendor/display/source-manifest.json')
doc=App.openDocument(str(HERE/'LCDRetentionTrial.FCStd'));doc.recompute()
bodies=[o for o in doc.Objects if o.TypeId=='PartDesign::Body']
for b in bodies:assert b.Shape.isValid()and len(b.Shape.Solids)==1,b.Name
lcd=doc.getObject('SelectedLCD');lb=lcd.Shape.BoundBox
assert abs(lb.XMin+24)<1e-5 and abs(lb.XMax-24)<1e-5
assert abs(lb.YMin-57.95)<1e-5 and abs(lb.YMax-112.57522203923)<1e-5,(lb.YMin,lb.YMax)
assert abs(lb.ZMax-68.8)<1e-5,(lb.ZMin,lb.ZMax)
new=[b for b in bodies if b.Name.startswith('LCDRetention')]
fixed=[doc.RoofCoupon,doc.BezelCoupon]
screws=[b for b in bodies if b.Name.startswith('ExistingBezelM2x6')]
checks=[];threads=[]
members=new+fixed+screws
for i,a in enumerate(members):
    for b in members[i+1:]:
        if not a.Shape.BoundBox.intersect(b.Shape.BoundBox):continue
        intersection=a.Shape.common(b.Shape);vol=intersection.Volume
        screw=a if a in screws else b if b in screws else None
        other=b if screw==a else a
        if screw and other==doc.BezelCoupon:
            x,y=M['MOUNTS'][int(screw.Name.rsplit('_',1)[1])]
            allowed=Part.makeCylinder(1.01,2.31,V(x,y,67.7))
            excess=intersection.cut(allowed).Volume
            assert excess<1e-5,(a.Name,b.Name,'outsidebezelthread',excess)
            threads.append({'pair':[a.Name,b.Name],'thread_major_overlap_mm3':vol,'outside_region_mm3':excess})
        else:
            assert vol<1e-5,(a.Name,b.Name,vol)
            checks.append({'pair':[a.Name,b.Name],'intersection_mm3':vol})
for b in members:
    vol=b.Shape.common(lcd.Shape).Volume
    assert vol<1e-5,(b.Name,'purchasedLCD',vol)
    checks.append({'pair':[b.Name,'PurchasedLCDincludingFFC'],'intersection_mm3':vol})
ffc_reserve=Part.makeBox(15,55,6.7,V(-7.5,57.8,61.5))
for b in new:
    assert b.Shape.common(ffc_reserve).Volume<1e-5,(b.Name,'FFCreservedspace')

# Check only new mounting parts against actual savedStepUp UI at all3heights;
# the rectangular benchroof is a real fixture, not a substitute for the master.
uipath=ROOT/'hardware/cad/evt1-assembly/pcb/LidUI.FCStd';ud=App.openDocument(str(uipath))
ur=next(o for o in ud.Objects if o.TypeId=='App::Part'and not o.InList)
raw=ur.Shape.copy();uichecks=[]
for z in(60,60.5,61):
    shape=raw.copy();shape.Placement=App.Placement(V(0,84.5,z),App.Rotation()).multiply(shape.Placement)
    for b in new:
        disjoint=not b.Shape.BoundBox.intersect(shape.BoundBox)
        vol=0 if disjoint else b.Shape.common(shape).Volume
        assert vol<1e-5,(b.Name,'actualUI',z,vol)
        uichecks.append({'part':b.Name,'UI_Fplane_Z_mm':z,'bounds_disjoint':disjoint,'intersection_mm3':vol})
App.closeDocument(ud.Name)

stacks=[]
for front in(68.5,68.6,68.8):
    for depth in(1.4,1.6,1.8,2.1):
        if 68.8-front+depth>2.1+1e-9:continue
        for foam in(.675,.75,.825,.8758):
            gap=max(69.1,front+foam*.75)-front
            n=max(0,round((front-depth-gap-66)/.0508));stack=n*.0508
            rear_gap=front-depth-66-stack;strain=1-rear_gap/foam
            assert stack<=.94 and .1<strain<.45
            stacks.append({'trial_local_front_Z_mm':front,'trial_local_depth_mm':depth,'trial_total_foam_mm':foam,'PET_layers':n,'rear_strain':strain})

svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1260" height="520" viewBox="0 0 1260 520">',
 '<rect width="1260" height="520" fill="#faf9f5"/>',
 '<text x="20" y="28" font-family="Arial" font-size="17">Actual LCD retention sections · measured glass load and optical qualification pending</text>']
panels=[('Paired border-face pads / Y87','xz',87,26,28),('Shared bezel fastener / Y105','xz',105,13,28),
        ('Unobstructed actual FFC / X0','yz',0,85,6)]
objects=[(doc.RoofCoupon.Shape,'#c76e26'),(doc.BezelCoupon.Shape,'#a2946c'),(lcd.Shape,'#657951')]
objects.extend((b.Shape,'#ab6383'if'PORON'in b.Name else'#67a8a2'if'PET'in b.Name else'#455365')for b in new+screws)
for idx,(title,axis,coord,center,scale)in enumerate(panels):
    sx=20+420*idx;svg.append(f'<text x="{sx}" y="60" font-family="Arial" font-size="13">{title}</text>')
    if axis=='xz':pts=[V(center-6,coord,61),V(center+6,coord,61),V(center+6,coord,71),V(center-6,coord,71)]
    else:pts=[V(coord,57,61),V(coord,113,61),V(coord,113,71),V(coord,57,71)]
    plane=Part.Face(Part.makePolygon(pts+[pts[0]]))
    for shape,col in objects:
        for edge in shape.section(plane).Edges:
            coords=[]
            for p in edge.discretize(Deflection=.02):
                u=(p.x-center)if axis=='xz'else(p.y-center)
                coords.append(f'{sx+195+u*scale:.3f},{410-(p.z-61)*scale:.3f}')
            if len(coords)>1:svg.append(f'<polyline points="{" ".join(coords)}" fill="none" stroke="{col}" stroke-width="1.4"/>')
svg.extend(['<text x="20" y="460" font-family="Arial" font-size="13">Orange: roof · cream: bezel · olive: actual selected LCD/FFC · pink: PORON · teal: screw-registered PET stack · dark: carriers/fasteners</text>',
 '<text x="20" y="486" font-family="Arial" font-size="13">OEM visual layers overlap; measure local glass faces. No edge squeeze, adhesive credit, supplier force approval or physical result is claimed.</text>','</svg>'])
(HERE/'native-sections.svg').write_text('\n'.join(svg)+'\n')

# 1:1die-cut film profiles from actualnative sections; four foam strips.
cut=['<svg xmlns="http://www.w3.org/2000/svg" width="110mm" height="60mm" viewBox="0 0 110 60">']
for b in new:
    if 'PETStack'not in b.Name:continue
    z=b.Shape.BoundBox.Center.z
    plane=Part.Face(Part.makePolygon([V(-44,55,z),V(44,55,z),V(44,113,z),V(-44,113,z),V(-44,55,z)]))
    for e in b.Shape.section(plane).Edges:
        pp=e.discretize(Deflection=.005)
        coords=' '.join(f'{p.x+44:.4f},{p.y-55:.4f}'for p in pp)
        cut.append(f'<polyline points="{coords}" fill="none" stroke="black" stroke-width="0.05"/>')
for i in range(4):cut.append(f'<rect x="{91+i*3.5}" y="10" width="1.2" height="22" fill="none" stroke="black" stroke-width="0.05"/>')
cut.append('</svg>');(HERE/'cut-patterns-1to1.svg').write_text('\n'.join(cut)+'\n')
report={'native_sha256':sha(HERE/'LCDRetentionTrial.FCStd'),'builder_sha256':sha(ROOT/'tools/build_evt1_dock_lcd_retention.py'),
 'checker_sha256':sha(Path(__file__)),'native_valid_single_solid_bodies':len(bodies),'actual_LCD_and_mechanical_pairs':checks,
 'bounded_bezel_thread_overlaps':threads,'FFC_reserved_space_checks':len(new),'actual_UI_endpoint_checks':uichecks,
 'actual_UI_source_sha256':sha(uipath),'received_stack_scenarios':stacks,
 'LCD_world_bounds_mm':[lb.XMin,lb.YMin,lb.ZMin,lb.XMax,lb.YMax,lb.ZMax],
 'LCD_internal_vendor_visual_overlaps_not_treated_as_physical_layers':True,
 'physical_validation':False,'manufacturer_allowable_glass_load_established':False}
(HERE/'native-readback.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'valid_bodies':len(bodies),'actual_LCD_and_mechanical_pairs':len(checks),'bounded_thread_pairs':len(threads),
 'UI_endpoint_checks':len(uichecks),'stack_scenarios':len(stacks)}))
App.closeDocument(doc.Name)
