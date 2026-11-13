"""Cold-read exact UV source geometry, mechanical interfaces and UI endpoints."""
from pathlib import Path
import hashlib,json,runpy,sys
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
M=runpy.run_path(str(ROOT/'tools/build_evt1_dock_uv_modules.py'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
V=App.Vector
doc=App.openDocument(str(HERE/'UVModuleThermalTrial.FCStd'));doc.recompute()
bodies=[o for o in doc.Objects if o.TypeId=='PartDesign::Body']
for b in bodies:assert b.Shape.isValid()and len(b.Shape.Solids)==1,b.Name
canonical_lid=M['apply_pose'](doc.getObject('UVLidSpreader6061').Shape,M['side_transform']('Lid').inverse())
canonical_base=doc.getObject('UVBaseSpreader6061').Shape
same_part_difference=canonical_lid.cut(canonical_base).Volume+canonical_base.cut(canonical_lid).Volume
assert same_part_difference<1e-5,same_part_difference
rotation=M['side_transform']('Lid').Rotation
det=rotation.multVec(V(1,0,0)).cross(rotation.multVec(V(0,1,0))).dot(rotation.multVec(V(0,0,1)))
assert abs(det-1)<1e-12 and(rotation.multVec(V(0,1,0))-V(0,1,0)).Length<1e-12
pairs=[];threads=[];UIchecks=[]
for side in('Base','Lid'):
    prefix='UV'+side
    parts=[b for b in bodies if b.Name.startswith(prefix)and 'SourceSolid'not in b.Name]
    pose=M['side_transform'](side)
    expected={}
    for i,(x,y)in enumerate([(M['NTC_X'],100),(M['NTC_X'],117),(42,124.5)]):
        receiver=prefix+('DryNTCClip'if i<2 else'TerminalGuard')
        key=frozenset((prefix+'AccuCS4_'+str(i),receiver))
        expected[key]=M['apply_pose'](Part.makeCylinder(1.01,2.8,V(x,y,5)),pose)
    expected[frozenset((prefix+'NBKThermostatM2x3',prefix+'Spreader6061'))]=M['apply_pose'](
        Part.makeCylinder(1.01,1.26,V(42,M['THERM_Y']+2.79,10.5)),pose)
    for i,a in enumerate(parts):
        for b in parts[i+1:]:
            if not a.Shape.BoundBox.intersect(b.Shape.BoundBox):continue
            intersection=a.Shape.common(b.Shape);vol=intersection.Volume
            key=frozenset((a.Name,b.Name))
            if key in expected:
                excess=intersection.cut(expected[key]).Volume
                assert excess<1e-5,(a.Name,b.Name,'outsideactualthreadregion',excess)
                threads.append({'pair':[a.Name,b.Name],'thread_major_overlap_mm3':vol,'outside_thread_region_mm3':excess})
            else:
                pairs.append({'pair':[a.Name,b.Name],'intersection_mm3':vol})
                assert vol<1e-5,(a.Name,b.Name,vol)
    # Actualexistingposts arecylindricalrootfeatures, not PCBfitproxies.
    for x,y in M['HOLES']:
        post=M['apply_pose'](Part.makeCylinder(2.6,9.2,V(x,y,3)),pose)
        vol=doc.getObject(prefix+'Spreader6061').Shape.common(post).Volume
        assert vol<1e-5,('spreader_existingpost',side,x,y,vol)

# ReadactualsourceStepUp UI geometry withoutsaving orchanging thatsource.
uipath=ROOT/'hardware/cad/evt1-assembly/pcb/LidUI.FCStd'
ui_doc=App.openDocument(str(uipath))
ui_root=next(o for o in ui_doc.Objects if o.TypeId=='App::Part'and not o.InList)
try:raw=ui_root.Shape.copy()
except AttributeError:raw=Part.makeCompound([o.Shape for o in ui_root.Group if hasattr(o,'Shape')and not o.Shape.isNull()])
assert raw.isValid()and len(raw.Solids)>0
for z in(60,60.5,61):
    ui=M['apply_pose'](raw,App.Placement(V(0,84.5,z),App.Rotation()))
    for p in[b for b in bodies if b.Name.startswith('UVLid')and 'SourceSolid'not in b.Name]:
        if not p.Shape.BoundBox.intersect(ui.BoundBox):continue
        vol=p.Shape.common(ui).Volume
        UIchecks.append({'UI_Fplane_Z_mm':z,'part':p.Name,'intersection_mm3':vol})
        assert vol<1e-5,('actualUI',z,p.Name,vol)
App.closeDocument(ui_doc.Name)

# Curves are actualsections of the savednative, not invented diagramgeometry.
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1260" height="520" viewBox="0 0 1260 520">',
 '<rect width="1260" height="520" fill="#faf9f5"/>',
 '<text x="20" y="28" font-family="Arial" font-size="17">Actual UV-module native sections · assembly and thermal qualification pending</text>']
panels=[('LED isolation / Y94','xz',94,42),('Dry NTC saddle / Y108.5','xz',108.5,M['NTC_X']),
        ('67L045 and clamp / X42','yz',42,110.5)]
selected=[b for b in bodies if b.Name.startswith('UVBase')]
for index,(label,axis,coord,center)in enumerate(panels):
    sx=20+420*index;scale=18 if axis=='xz'else 12
    svg.append(f'<text x="{sx}" y="60" font-family="Arial" font-size="13">{label}</text>')
    if axis=='xz':pts=[V(center-10,coord,4),V(center+10,coord,4),V(center+10,coord,16),V(center-10,coord,16)]
    else:pts=[V(coord,96,4),V(coord,125,4),V(coord,125,16),V(coord,96,16)]
    plane=Part.Face(Part.makePolygon(pts+[pts[0]]))
    for o in selected:
        col='#797d84'
        if 'SourceSolid'in o.Name:col='#68744b'
        elif 'Insulator'in o.Name or'SoftSupport'in o.Name:col='#bd7b9b'
        elif 'NTC'in o.Name or'Guard'in o.Name or'Sensata'in o.Name:col='#1d6289'
        for edge in o.Shape.section(plane).Edges:
            points=edge.discretize(Deflection=.03);coords=[]
            for p in points:
                u=(p.x-center)if axis=='xz'else(p.y-center)
                coords.append(f'{sx+190+u*scale:.3f},{410-(p.z-4)*scale:.3f}')
            if len(coords)>1:svg.append(f'<polyline points="{" ".join(coords)}" fill="none" stroke="{col}" stroke-width="1.3"/>')
svg.extend(['<text x="20" y="460" font-family="Arial" font-size="13">Grey: 6061 and fasteners · pink: insulating thermal pad · blue: selected sensors and removable printed retainers · olive: frozen PCBA</text>',
 '<text x="20" y="486" font-family="Arial" font-size="13">Sensor lag, FR4 heat path, dielectric endurance, wire restraint, UV containment, dose and cleaning performance remain unmeasured.</text>','</svg>'])
(HERE/'native-sections.svg').write_text('\n'.join(svg)+'\n')
report={'native_sha256':sha(HERE/'UVModuleThermalTrial.FCStd'),'builder_sha256':sha(ROOT/'tools/build_evt1_dock_uv_modules.py'),
 'checker_sha256':sha(Path(__file__)),'native_body_count':len(bodies),'all_valid_single_solid':True,
 'same_spreader_rigid_difference_mm3':same_part_difference,'lid_rotation_determinant':det,'lid_preserves_Y':True,
 'actual_mechanical_pairs':pairs,'bounded_thread_major_overlaps':threads,'actual_UI_endpoint_checks':UIchecks,
 'UI_native_sha256':sha(uipath),'UI_reference_Fplanes_mm':[60,60.5,61],
 'actual_existing_post_radial_clearance_mm':.3,'native_sections_sha256':sha(HERE/'native-sections.svg'),
 'received_tolerance_or_physical_validation':False}
(HERE/'native-readback.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'body_count':len(bodies),'hardpairs':len(pairs),'bounded_threads':len(threads),'actual_UI_checks':len(UIchecks)}))
App.closeDocument(doc.Name)
