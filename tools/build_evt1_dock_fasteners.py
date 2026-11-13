"""Selected screw external profiles as editable native revolutions.

Manufacturer dimension reconstruction, not supplier CAD. Cosmetic threads,
drive recesses, edge breaks and undisclosed radii are omitted. The maximum
head diameter/height, 90-degree cone and nominal thread-major diameter are
used for installation/access checks. NBK socket heads use the published
nominal external dimensions; the under-head bearing plane is their Z0 datum.
No fastening strength or received dimensional acceptance follows from CAD.
"""

SPECS = {
    'M2x6': dict(mpn='SIK-M2-6-A2', diameter=2., length=6., head=3.8,
                height=1.2, pitch=.4,
                url='https://www.accu.co.uk/phillips-countersunk-screws/65898-SIK-M2-6-A2'),
    'M3x12': dict(mpn='SIK-M3-12-A2', diameter=3., length=12., head=5.5,
                 height=1.65, pitch=.5,
                 url='https://www.accu.co.uk/phillips-countersunk-screws/65913-SIK-M3-12-A2'),
    'M2x4Socket': dict(mpn='SNSS-M2-4', diameter=2., length=4., head=3.8,
                      height=2., pitch=.4, style='socket', maker='NBK',
                      url='https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/miniaturescrew/SNSS/'),
    'M2x6Socket': dict(mpn='SNSS-M2-6', diameter=2., length=6., head=3.8,
                      height=2., pitch=.4, style='socket', maker='NBK',
                      url='https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/miniaturescrew/SNSS/'),
    'M2x10Socket': dict(mpn='SNSS-M2-10', diameter=2., length=10., head=3.8,
                       height=2., pitch=.4, style='socket', maker='NBK',
                       url='https://www.nbk1560.com/en-US/products/specialscrew/nedzicom/miniaturescrew/SNSS/'),
}


def build(doc, key):
    import FreeCAD as App
    import Part
    import Sketcher
    spec = SPECS[key]
    body = doc.addObject('PartDesign::Body', 'SelectedScrew' + key)
    body.Label = spec.get('maker','Accu')+' '+spec['mpn']
    for name, value in (('ManufacturerPartNumber', spec['mpn']),
                        ('SourceURL', spec['url']),
                        ('ModelBasis', __doc__.strip())):
        body.addProperty('App::PropertyString', name, 'Source')
        setattr(body, name, value)
    for name, value in (('ThreadDiameter', spec['diameter']),
                        ('ThreadPitch', spec['pitch']),
                        ('OverallLength', spec['length']),
                        ('HeadDiameter', spec['head']),
                        ('HeadHeight', spec['height'])):
        body.addProperty('App::PropertyLength', name, 'Drawing dimensions')
        setattr(body, name, value)
        body.setEditorMode(name, 1)
    sketch = body.newObject('Sketcher::SketchObject', 'ScrewSection' + key)
    sketch.Placement.Rotation = App.Rotation(App.Vector(1, 0, 0), 90)
    r, rh, h = spec['diameter']/2, spec['head']/2, spec['height']
    # Head-top datum Z=0, threaded shaft points toward -Z. Published head
    # height exceeds the 90-degree conical depth; retain the top rim.
    if spec.get('style')=='socket':
        points=[(0,h),(rh,h),(rh,0),(r,0),(r,-spec['length']),(0,-spec['length'])]
    else:
        rim = h - (rh-r)
        assert rim > 0
        points = [(0, 0), (rh, 0), (rh, -rim), (r, -h),
                  (r, -spec['length']), (0, -spec['length'])]
    for a, b in zip(points, points[1:]+points[:1]):
        i = sketch.addGeometry(Part.LineSegment(App.Vector(*a, 0),
                                               App.Vector(*b, 0)), False)
        sketch.addConstraint(Sketcher.Constraint('Block', i))
    doc.recompute()
    assert sketch.FullyConstrained
    feature = body.newObject('PartDesign::Revolution', 'TurnedScrew' + key)
    feature.Profile = sketch
    feature.ReferenceAxis = (sketch, ['V_Axis'])
    feature.Angle = 360
    doc.recompute()
    assert feature.Shape.isValid() and len(feature.Shape.Solids) == 1
    sketch.Visibility = False
    body.ViewObject.ShapeColor = (.76, .77, .78)
    return body


def build_M2_nut(doc):
    """Accu HPN-M2-A2-BL drawing reconstruction; no cosmetic threads/chamfers."""
    import FreeCAD as App
    import Part,Sketcher,math
    b=doc.addObject('PartDesign::Body','SelectedM2Nut')
    b.Label='Accu HPN-M2-A2-BL / selected DIN934 full nut'
    for name,value in (
            ('ManufacturerPartNumber','HPN-M2-A2-BL'),
            ('SourceURL','https://www.accu.co.uk/hexagon-nuts/154931-HPN-M2-A2-BL'),
            ('ModelBasis','Published max4mm AF and1.6mm height; 1.6mm cosmetic minor bore. AF3.82..4,height1.35..1.6,pitch0.4. Threads/chamfers omitted; received fit and availability unverified.')):
        b.addProperty('App::PropertyString',name,'Source');setattr(b,name,value)
    sk=b.newObject('Sketcher::SketchObject','M2NutSection')
    points=[App.Vector(4/math.sqrt(3)*math.cos(i*math.pi/3),
                       4/math.sqrt(3)*math.sin(i*math.pi/3),0)for i in range(6)]
    for i in range(6):
        n=sk.addGeometry(Part.LineSegment(points[i],points[(i+1)%6]),False)
        sk.addConstraint(Sketcher.Constraint('Block',n))
    n=sk.addGeometry(Part.Circle(App.Vector(),App.Vector(0,0,1),.8),False)
    sk.addConstraint(Sketcher.Constraint('Coincident',n,3,-1,1))
    sk.addConstraint(Sketcher.Constraint('Radius',n,.8))
    doc.recompute();assert sk.FullyConstrained
    p=b.newObject('PartDesign::Pad','M2NutBody');p.Profile=sk;p.Length=1.6
    doc.recompute();assert p.Shape.isValid()and len(p.Shape.Solids)==1
    sk.Visibility=False;b.ViewObject.ShapeColor=(.18,.18,.19)
    return b
