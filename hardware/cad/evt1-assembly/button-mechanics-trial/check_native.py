"""Cold-read geometric checks and actual CAD sections for the isolated coupon."""
from pathlib import Path
import hashlib,json,sys
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part

HERE=Path(__file__).resolve().parent
V=App.Vector
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
doc=App.openDocument(str(HERE/'ButtonMechanicsTrial.FCStd'))
doc.recompute()
bodies=[o for o in doc.Objects if o.TypeId=='PartDesign::Body']
valid=[]
for o in bodies:
    assert o.Shape.isValid()and len(o.Shape.Solids)==1,o.Name
    valid.append({'name':o.Name,'solid_count':len(o.Shape.Solids),'volume_mm3':o.Shape.Volume})
roof=doc.getObject('RoofCoupon');ret=doc.getObject('RetainerCoupon');support=doc.getObject('PCBSupportCoupon')
cap=doc.getObject('CenterCapInstalled');sw=doc.getObject('CenterSelectedB3FS1002P')
spring=doc.getObject('CenterLC014B02S');pressed=doc.getObject('CenterCapPressedPose').Shape.copy()
pressed.translate(V(0,-30,0))
checks=[]
for label in ('Left','Center','Right'):
    installed_cap=doc.getObject(label+'CapInstalled').Shape
    pressed_cap=doc.getObject(label+'CapPressedPose').Shape.copy()
    pressed_cap.translate(V(0,-30,0))
    for pose,shape in (('rest',installed_cap),('pressed',pressed_cap)):
        for fixed in (roof,ret):
            vol=shape.common(fixed.Shape).Volume
            checks.append({'pair':label+'_'+pose+'_'+fixed.Name,'intersection_mm3':vol})
            assert vol<1e-5,(label,pose,fixed.Name,vol)
for name,s1,s2 in [('cap_roof_rest',cap.Shape,roof.Shape),('cap_retainer_rest',cap.Shape,ret.Shape),
                  ('cap_switch_rest',cap.Shape,sw.Shape),('cap_coil_rest',cap.Shape,spring.Shape),
                  ('roof_retainer',roof.Shape,ret.Shape),('roof_support',roof.Shape,support.Shape),
                  ('cap_roof_pressed',pressed,roof.Shape),('cap_retainer_pressed',pressed,ret.Shape)]:
    vol=s1.common(s2).Volume
    checks.append({'pair':name,'intersection_mm3':vol})
    assert vol<1e-5,(name,vol)
# Pressed tip overlaps only the released actuator. We do not move the switch
# body or credit that artificial overlap as a mechanical overtravel allowance.
board_z=App.Units.Quantity(doc.Parameters.get('B1')).Value
solder=App.Units.Quantity(doc.Parameters.get('B2')).Value
case=sw.Shape.cut(Part.makeCylinder(1.6,10,V(0,54,board_z+solder+2.6)))
vol=pressed.common(case).Volume
checks.append({'pair':'pressed_cap_fixed_switch_case_excluding_actuator','intersection_mm3':vol})
assert vol<1e-5,('pressed_case',vol)
for o in doc.Objects:
    if o.Name.endswith('ContactTipProfile'):assert o.FullyConstrained,o.Name

# Section curves are calculated from the real saved component solids. They are
# an inspection drawing, not a redesigned sketch or a replacement fit model.
panels=[('Contact shoe and stock spring / Y54',54,'xz'),('Return finger / Y48.2',48.2,'xz'),
        ('Centre longitudinal section / X0',0,'yz')]
objects=[(roof,'#494e54'),(ret,'#b6a680'),(sw,'#7f6b8f'),(spring,'#878d95'),(cap,'#0089bf')]
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1260" height="520" viewBox="0 0 1260 520">',
     '<rect width="1260" height="520" fill="#f7f6f2"/>',
     '<text x="24" y="28" font-family="sans-serif" font-size="17">Saved-native button sections · unpowered mechanical trial</text>']
sections=[]
for index,(label,coord,axes)in enumerate(panels):
    sx=20+index*420;sy=65;scale=14
    svg.append(f'<text x="{sx}" y="{sy-8}" font-family="sans-serif" font-size="13">{label}</text>')
    svg.append('<g>')
    if axes=='xz':pts=[V(-13,coord,59),V(13,coord,59),V(13,coord,74),V(-13,coord,74)]
    else:pts=[V(coord,46,59),V(coord,61,59),V(coord,61,74),V(coord,46,74)]
    plane=Part.Face(Part.makePolygon(pts+[pts[0]]))
    for o,col in objects:
        section=o.Shape.section(plane);edge_count=0
        for edge in section.Edges:
            points=edge.discretize(Deflection=.025);coords=[]
            for p in points:
                u=p.x if axes=='xz'else p.y-54
                coords.append(f'{sx+200+u*scale:.3f},{sy+320-(p.z-59)*scale:.3f}')
            if len(coords)>1:
                svg.append(f'<polyline points="{" ".join(coords)}" fill="none" stroke="{col}" stroke-width="1.4"/>');edge_count+=1
        sections.append({'panel':index,'body':o.Name,'edge_count':edge_count})
    svg.append('</g>')
svg.extend(['<text x="24" y="462" font-family="sans-serif" font-size="13">Blue: one printed cap/shoe · grey: roof · cream: retainer · purple: selected released switch · silver: selected spring</text>',
            '<text x="24" y="486" font-family="sans-serif" font-size="13">No force, fatigue, received-stack or allowable switch overtravel is established by this drawing.</text>','</svg>'])
(HERE/'native-sections.svg').write_text('\n'.join(svg)+'\n')
report={'native_sha256':sha(HERE/'ButtonMechanicsTrial.FCStd'),'checker_sha256':sha(Path(__file__)),
 'all_bodies_valid_single_solid':True,'body_count':len(valid),'bodies':valid,'actual_solid_pairs':checks,
 'tip_profiles_fully_constrained':True,'sections':sections,'section_sha256':sha(HERE/'native-sections.svg'),
 'physical_force_or_fit_proof':False}
(HERE/'native-readback.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'body_count':len(valid),'native_checks':len(checks),'native':str(HERE/'ButtonMechanicsTrial.FCStd')}))
App.closeDocument(doc.Name)
