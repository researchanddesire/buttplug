"""Isolated, retained button mechanism/coupon. Never edits the master dock.

Native FreeCAD bodies retain the selected switch geometry, cap features and
critical board-height/contact-tip expressions. Print FREE caps only: installed
and pressed copies represent elastic assembly poses, not printable geometry.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys
sys.path.insert(0,'/Applications/FreeCAD.app/Contents/Resources/lib')
import FreeCAD as App
import Part
import Sketcher
import MeshPart

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hardware/cad/evt1-assembly/button-mechanics-trial'
SWITCH=ROOT/'hardware/cad/evt1-assembly/vendor/buttons/SW_SPST_Omron_B3FS-100xP.step'
SWITCH_SHA='b329c059bd0fc4def23f1dbf3a8ab42d79451e42368166bfa454033e4741fdc1'
SPRING={'mpn':'LC014B02S','manufacturer':'Lee Spring','material':'302 stainless;304 substitution permitted by catalog',
 'OD_mm':4.57,'wire_mm':.36,'free_length_mm':7.95,'solid_height_approx_mm':1.96,
 'music_wire_rate_lbf_per_in':4.50,'music_wire_rate_N_per_mm':.79,
 'stainless_factor':5/6,'rate_N_per_mm':.79*5/6,'rate_tolerance_fraction':.10,
 'solid_height_tolerance_plus_fraction':.05,'free_length_tolerance_mm':None,
 'source':'https://www.leespring.com/sites/default/files/2023-03/lee-spring-catalog-us.pdf',
 'download_sha256':'b0f9e7f0ea1e2d3a7316cd69dd2b42b3d3fd8652bbdf59bc98f6b640280294b1',
 'PDF_page_1based':70,'printed_page':68,
 'catalog_instructions':'S suffix; rates for music wire multiply5/6 for stainless; nominal/solid/coils approximate; recommend<=80%deflectivecapacity',
 'engineering_source':'https://www.leespring.com/engineering-notes-and-tolerances'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
V=lambda x,y,z=0:App.Vector(x,y,z)
COLORS={'cap':(.02,.57,.81),'roof':(.20,.21,.23),'retainer':(.90,.86,.76),'spring':(.64,.66,.69)}

def color(o,c):
    if o.ViewObject:o.ViewObject.ShapeColor=c

def rr(w,h,r,z=0,cx=0,cy=0):
    x,y=w/2,h/2;q=math.sqrt(.5)
    seq=[((-x+r,-y),(x-r,-y),None),((x-r,-y),(x,-y+r),(x-r+r*q,-y+r-r*q)),
      ((x,-y+r),(x,y-r),None),((x,y-r),(x-r,y),(x-r+r*q,y-r+r*q)),
      ((x-r,y),(-x+r,y),None),((-x+r,y),(-x,y-r),(-x+r-r*q,y-r+r*q)),
      ((-x,y-r),(-x,-y+r),None),((-x,-y+r),(-x+r,-y),(-x+r-r*q,-y+r-r*q))]
    edges=[]
    for a,b,m in seq:
        p=lambda t:V(t[0]+cx,t[1]+cy,z)
        edges.append(Part.makeLine(p(a),p(b))if m is None else Part.Arc(p(a),p(m),p(b)).toShape())
    return Part.Wire(edges)

def plate(w,h,r,z,t,cx=0,cy=54):return Part.Face(rr(w,h,r,z,cx,cy)).extrude(V(0,0,t))
def box(x1,y1,z1,x2,y2,z2):return Part.makeBox(x2-x1,y2-y1,z2-z1,V(x1,y1,z1))
def union(shapes):
    out=shapes[0]
    for s in shapes[1:]:out=out.fuse(s)
    return out.removeSplitter()

def feature(doc,body,name,shape,note=''):
    f=body.newObject('PartDesign::Feature',name);f.Shape=shape
    if note:f.addProperty('App::PropertyString','EngineeringNote');f.EngineeringNote=note
    body.Tip=f
    doc.recompute()
    return f

def stage(doc,body,name,previous,adds=(),cuts=(),note=''):
    shape=union([previous]+list(adds))if adds else previous
    for c in cuts:shape=shape.cut(c)
    shape=shape.removeSplitter();assert shape.isValid(),name
    feature(doc,body,name,shape,note);return shape

def sweep(path_points,width,height):
    curve=Part.BSplineCurve();curve.interpolate([V(*p)for p in path_points])
    edge=curve.toShape();spine=Part.Wire([edge]);t=edge.tangentAt(edge.FirstParameter).normalize()
    # Cross-section axes: globalY and perpendicular within X/Z for return beams.
    a=V(0,1,0);b=t.cross(a).normalize();center=V(*path_points[0])
    verts=[center+a*width/2+b*height/2,center-a*width/2+b*height/2,
           center-a*width/2-b*height/2,center+a*width/2-b*height/2]
    profile=Part.makePolygon(verts+[verts[0]])
    return spine.makePipeShell([Part.Wire(profile.Edges)],True,False)

def guide_tether(sign,lift):
    # Three long legs;0.5mm Z thickness/0.4mm XY width. The free-print shoe
    # has0.5mm clearance above its lower seats. Loaded guide deflection is
    # visual geometry only; its reaction is a measured acceptance condition.
    pts=[(7.8,50.0),(6.9,50.0),(6.9,55.8),(5.95,55.8),
         (5.95,50.8),(5.0,50.8),(5.0,55.4),(4.1,55.4)]
    seg=[]
    lengths=[math.dist(a,b)for a,b in zip(pts,pts[1:])];total=sum(lengths);walk=0
    for i,(a,b)in enumerate(zip(pts,pts[1:])):
        length=lengths[i];q=[]
        for j in range(9):
            u=j/8;t=(walk+u*length)/total
            z=65.5+(lift-.5)*(t*t*(3-2*t))
            q.append((sign*(a[0]+u*(b[0]-a[0])),a[1]+u*(b[1]-a[1]),z))
        # Ruled small rectangular prisms with overlapping rounded junctions.
        p0,p1=V(*q[0]),V(*q[-1]);delta=p1-p0
        normal=V(-delta.y,delta.x,0).normalize()
        extension=delta*.01/length
        p0=p0-extension-normal*.2;p1=p1+extension-normal*.2
        # Keep0.5mm in globalZ. A skew ruled prism avoids rotating its end
        # faces into near-coincident slivers at tiny loaded shoe deflections.
        vertices=[p0,p1,p1+V(0,0,.5),p0+V(0,0,.5),p0]
        flat=Part.Face(Part.makePolygon(vertices)).extrude(normal*.4)
        seg.append(flat);walk+=length
    # Rounded junctions cover the tiny segment overlaps without closing the
    # designed0.5mm serpentine gaps.
    walk=0
    for i,(x,y)in enumerate(pts):
        if i:walk+=lengths[i-1]
        t=walk/total;z=65.5+(lift-.5)*(t*t*(3-2*t))
        seg.append(Part.makeCylinder(.20,.5,V(sign*x,y,z)))
    return union(seg)

def return_arm(sign,y,press,free=False):
    L=10.4;pre=.7;stem=4.1;delta=0 if free else press+pre
    # Solve rounded toe contact height with the rotated foot-stem, rather
    # than pretending the long toe remains vertical during beam bending.
    if not free:
        for _ in range(20):
            angle=1.5*delta/L
            f=delta+stem*(1-math.cos(angle))-(press+pre)
            delta-=f/(1+stem*math.sin(angle)*1.5/L)
    root=V(-sign*5.4,y,67.7-press)
    points=[]
    for i in range(21):
        t=i/20;x=root.x+sign*L*t
        deflection=delta*t*t*(3-t)/2
        points.append((x,y,root.z+deflection))
    beam=(box(min(p[0]for p in points),y-.4,root.z-.3,
              max(p[0]for p in points),y+.4,root.z+.3)
          if delta==0 else sweep(points,.8,.6))
    angle=1.5*delta/L
    end=V(*points[-1]);down=V(sign*math.sin(angle),0,-math.cos(angle))
    foot_center=end+V(0,0,.3)+down*stem
    foot=Part.makeSphere(.6,foot_center)
    # Upper stem begins at beam centreline; rounded contact carries no
    # unmodeled floor penetration in the installed/pressed CAD poses.
    stemshape=Part.makeCylinder(.40,stem,V(end.x,end.y,end.z+.3),down)
    return union([beam,stemshape,foot]),{'deflection_mm':delta,'angle_rad':angle,
       'toe_lowest_Z_mm':foot_center.z-.6,'strain_Euler_Bernoulli_estimate':1.5*.6*delta/L**2}

def cap(doc,name,w,h,params,press=0,lift=0,free=False):
    print('Building '+name,flush=True)
    b=doc.addObject('PartDesign::Body',name);b.Label=name+' / ONE printed cap, no loose plunger'
    # Major authoring geometry follows the selected concept cap face.
    shape=plate(w,h,min(w,h)/2-.2,70.3-press,2.7)
    feature(doc,b,name+'VisibleCrown',shape,'Original visible14x10/16x9 rounded blue cap,2.7mm thick.')
    # Short pilots leave a2.8mm insertion window in the free cap. Compress
    # the coil to<=2.6mm in a bench fixture, insert from the open rear and
    # release onto the pilots. Insertion is an unpowered coupon trial.
    adds=[Part.makeCylinder(1,.45,V(0,54,69.9-press))]
    crown_column=plate(w,h,min(w,h)/2-.2,66.0-press,4.35)
    for x in(-5.6,5.6):
        for y in(51.0,55.8):
            # Keep the square guide roots within the visible crown's outline.
            # Otherwise the14x10 outer variants clip the bezel's front corners.
            adds.append(box(x-.7,y-.7,66.0-press,x+.7,y+.7,70.35-press).common(crown_column))
    # Moving U retention ring and partial rear bridges; centre rear stays open.
    adds.extend([box(-8.8,49.5,65-press,8.8,50.5,66.2-press),
       box(-8.8,49.5,65-press,-7.6,56.8,66.2-press),box(7.6,49.5,65-press,8.8,56.8,66.2-press)])
    for sign in(-1,1):
        xa,xb=(3.1,8.8)if sign>0 else(-8.8,-3.1)
        adds.append(box(xa,55.8,65-press,xb,56.8,66.2-press))
    # The second return toe rolls in front of the ring. Relieve the front
    # crossbar locally so the return finger cannot bond to, or rub, its own
    # retention skirt through the whole travel.
    shape=stage(doc,b,name+'GuideSkirtAndRetention',shape,adds,
       cuts=[box(-7.1,48.4,64.8-press,-3.5,50.6,66.4-press)])
    # Lower internal shoes stop sits outside the6mm switch case, so it cannot
    # rigidly strike the switch case at the upper board-height setting.
    adds=[]
    for sign in(-1,1):
        xa,xb=(3.6,7.8)if sign>0 else(-7.8,-3.6)
        adds.append(box(xa,53.2,64.3-press,xb,54.8,65.0-press))
    shape=stage(doc,b,name+'InternalPreloadStops',shape,adds,note='Coil preload reacts against integral wing seats atrest, never the switch.')
    guides=[guide_tether(s,lift)for s in(-1,1)]
    for g in guides:g.translate(V(0,0,-press))
    shape=stage(doc,b,name+'IntegralShoeTethers',shape,guides)
    plate_bottom=65.0+lift-press
    shoe=Part.makeCylinder(2.4,.8,V(0,54,plate_bottom))
    wings=[box(-4.3,53.0,plate_bottom,-1.8,55.7,plate_bottom+.8),box(1.8,53.0,plate_bottom,4.3,55.7,plate_bottom+.8)]
    guidepost=Part.makeCylinder(1,.8,V(0,54,plate_bottom+.8))
    shape=stage(doc,b,name+'CaptiveIntegralShoe',shape,[shoe,guidepost]+wings)
    armdata=[];arms=[]
    for sign,y in[(1,48.2),(-1,49.3)]:
        a,data=return_arm(sign,y,press,free);arms.append(a);armdata.append(data)
        # Hidden root webs, relieved in the coupon's fixed retainer.
        x=-sign*5.4
        arms.append(box(x-.6,y-.4,67.7-press,x+.6,51.7,68.3-press))
    shape=stage(doc,b,name+'IntegralReturnArms',shape,arms)
    # Last feature is a native parametric pad, so BoardZ/RestGap directly
    # change the contact tip while crown/retention datums stay fixed.
    sk=b.newObject('Sketcher::SketchObject',name+'ContactTipProfile')
    sk.Placement.Base=V(0,54,params['board_z']+params['solder']+params['switch_height']+params['gap']+lift-press)
    sk.addGeometry(Part.Circle(V(0,0),V(0,0,1),1),False)
    sk.addConstraint(Sketcher.Constraint('Coincident',0,3,-1,1));sk.addConstraint(Sketcher.Constraint('Radius',0,1))
    sheet=params.get('sheet_name','Parameters')
    sk.setExpression('Placement.Base.z',sheet+'.BoardZ + '+sheet+'.SolderStandOff + '+sheet+'.MeasuredSwitchHeight + '+sheet+'.RestGap + '+str(lift-press)+' mm')
    doc.recompute();assert sk.FullyConstrained
    tip=b.newObject('PartDesign::Pad',name+'IntegralContactTip');tip.Profile=sk
    tip.Length=plate_bottom-sk.Placement.Base.z+.02
    tip.setExpression('Length',str(plate_bottom+.02)+' mm - '+sk.Name+'.Placement.Base.z')
    doc.recompute()
    assert tip.Shape.isValid() and len(tip.Shape.Solids)==1,(name,len(tip.Shape.Solids))
    b.addProperty('App::PropertyString','PoseLimit','Engineering')
    b.PoseLimit='PRINT ONLY the free cap; installed/pressed copies include elastic pose/contact and mustnotbe exported for printing.'
    color(b,COLORS['cap'])
    return b,armdata

def spring(doc,name,base_z,length,x=0):
    body=doc.addObject('PartDesign::Body',name);body.Label=SPRING['mpn']+' / selected stock stainless spring'
    wire=SPRING['wire_mm'];radius=(SPRING['OD_mm']-wire)/2;turns=5.5
    helix=Part.makeHelix(length/turns,length,radius)
    start=V(radius,0,0);tangent=helix.Edges[0].tangentAt(0)
    circle=Part.Wire([Part.makeCircle(wire/2,start,tangent)])
    shape=Part.Wire(helix.Edges).makePipeShell([circle],True,False)
    shape=shape.common(Part.makeCylinder(radius+wire,length,V(0,0,0))).removeSplitter()
    shape.translate(V(x,54,base_z));assert shape.isValid()
    f=feature(doc,body,name+'CatalogDimensionHelix',shape,
      'PublishedOD/wire/length;5.5turn distribution reconstructed for visualisation. Actualclosed-groundendshape andcoilcount are not OEMCAD or force proof.')
    for key,value in SPRING.items():
        if isinstance(value,str):body.addProperty('App::PropertyString',key,'Source');setattr(body,key,value)
    color(body,COLORS['spring']);return body

def stationary(doc):
    roof=doc.addObject('PartDesign::Body','RoofCoupon')
    shape=plate(86,24,3,64,3.7)
    feature(doc,roof,'CouponRoofStock',shape)
    cuts=[]
    for x,w,h in[(-22,14,10),(0,16,9),(22,14,10)]:
        cuts.append(box(x-9.3,47.6,63.8,x+9.3,57.1,68))
    cuts.append(box(-7.8,57.2,63,7.8,67,68.3))
    shape=stage(doc,roof,'HiddenCapPocketsAndFFCTailRelief',shape,cuts=cuts)
    lands=[]
    for x in(-22,0,22):
        for sign in(-1,1):
            xa,xb=(7.6,10.4)if sign>0 else(-10.4,-7.6)
            for y1,y2 in[(49.4,51.0),(55.2,56.9)]:
                lands.append(box(x+xa,y1,63,x+xb,y2,64))
        # Return spherical toes can roll along these broad captured seats.
        for fx,fy in[(5.5,48.2),(-5.5,49.3)]:
            # Extend the low seat into the uncut front roof: it is one fixed
            # printed body, not an unsupported island inside the cap pocket.
            lands.append(box(x+fx-1.8,46.5,63,x+fx+1.8,fy+.9,64))
    shape=stage(doc,roof,'IntegralDownStopsAndReturnSeats',shape,lands)
    holes=[]
    for x in(-32,32):
        for y in(45,63):holes.append(Part.makeCylinder(.8,5,V(x,y,63.5)))
    for x in(-38,38):
        for y in(45,63):holes.append(Part.makeCylinder(1.25,5,V(x,y,63.5)))
    shape=stage(doc,roof,'CouponTapPilots',shape,cuts=holes)
    assert len(shape.Solids)==1;color(roof,COLORS['roof'])
    ret=doc.addObject('PartDesign::Body','RetainerCoupon')
    shape=plate(86,24,3,67.7,2.8);feature(doc,ret,'CouponBezelSkin',shape)
    cuts=[]
    for x,w,h in[(-22,14,10),(0,16,9),(22,14,10)]:
        cuts.append(plate(w+.5,h+.5,min(w,h)/2,67.6,3.1,x,54))
        cuts.append(box(x-6.6,47.6,67.5,x+6.6,57,69.0))
    cuts.append(box(-7.8,57.2,67.5,7.8,67,68.3))
    shape=stage(doc,ret,'VisiblePassagesHiddenMotionAndFFCRelief',shape,cuts=cuts)
    rails=[]
    for x in(-22,0,22):
        rails.append(box(x-10,47.6,66.2,x-6.6,57,67.71))
        rails.append(box(x+6.6,47.6,66.2,x+10,57,67.71))
    shape=stage(doc,ret,'IntegralUpStopsAndGuideRails',shape,rails)
    holes=[]
    for x in(-32,32):
        for y in(45,63):
            holes.append(Part.makeCylinder(1.15,5,V(x,y,66)))
            holes.append(Part.makeCylinder(1.9,.3,V(x,y,70.5),V(0,0,-1)))
            holes.append(Part.makeCone(1.9,1.15,.75,V(x,y,70.2),V(0,0,-1)))
    for x in(-38,38):
        for y in(45,63):holes.append(Part.makeCylinder(1.8,5,V(x,y,66)))
    shape=stage(doc,ret,'CouponClearancesAndM2Countersinks',shape,cuts=holes)
    assert len(shape.Solids)==1;color(ret,COLORS['retainer']);return roof,ret

def support(doc,board_z):
    body=doc.addObject('PartDesign::Body','PCBSupportCoupon')
    shape=plate(86,24,3,board_z-3,2)
    feature(doc,body,'BackSupportPlate',shape,'Actualinertfixture; the real routedUIboard isnotreplacedbythispart.')
    posts=[Part.makeCylinder(3,65-board_z,V(x,y,board_z-1))for x in(-38,38)for y in(45,63)]
    posts.extend(Part.makeCylinder(1,1.5,V(x,65,board_z-1))for x in(-30,30))
    shape=stage(doc,body,'M3SupportColumnsAndActualPCBLocationPins',shape,posts,
       note='Integral2mm pins enter actual2.3mm NPTH H301/H302 atX±30,Y65; only lateral registration, not a board-clamp rating.')
    cuts=[Part.makeCylinder(2,4,V(x,54,board_z-3.1))for x in(-22,0,22)]
    for x in(-38,38):
        for y in(45,63):
            cuts.append(Part.makeCylinder(1.65,10,V(x,y,board_z-3.1)))
            cuts.append(Part.makeCylinder(2.75,.4,V(x,y,board_z-3),V(0,0,1)))
            cuts.append(Part.makeCone(2.75,1.65,1.1,V(x,y,board_z-2.6),V(0,0,1)))
    shape=stage(doc,body,'InstrumentProbePortsAndSupportFasteners',shape,cuts=cuts)
    assert shape.isValid()and len(shape.Solids)==1;color(body,COLORS['roof'])
    return body

def fixed_features():
    """Boolean features in global dock coordinates; real solids, no proxies.

    Cut the orange roof and cream bezel first, then fuse their own additions.
    Do not fuse the two moving/fixed products together. FFC relief remains the
    master assembly's responsibility; these mechanisms stay forward ofY57.
    """
    roof_cuts=[];roof_adds=[];bezel_cuts=[];bezel_adds=[]
    for x,w,h in[(-22,14,10),(0,16,9),(22,14,10)]:
        roof_cuts.append(box(x-10.4,47.6,64,x+10.4,57.1,68))
        bezel_cuts.append(plate(w+.5,h+.5,min(w,h)/2,67.6,3.1,x,54))
        bezel_cuts.append(box(x-6.6,47.6,67.5,x+6.6,57,69.0))
        for sign in(-1,1):
            xa,xb=(7.6,11.4)if sign>0 else(-11.4,-7.6)
            for y1,y2 in[(49.4,51.0),(55.2,56.9)]:
                roof_adds.append(box(x+xa,y1,63,x+xb,y2,64))
        for fx,fy in[(5.5,48.2),(-5.5,49.3)]:
            roof_adds.append(box(x+fx-1.8,46.5,63,x+fx+1.8,fy+.9,64))
        bezel_adds.append(box(x-10,47.6,66.2,x-6.6,57,67.71))
        bezel_adds.append(box(x+6.6,47.6,66.2,x+10,57,67.71))
    return {'orange_roof_cuts':roof_cuts,'orange_roof_downstop_and_return_adds':roof_adds,
            'cream_bezel_cuts':bezel_cuts,'cream_bezel_upstop_guide_adds':bezel_adds,
            'dimensions':{'centers_X_mm':[-22,0,22],'center_Y_mm':54,'roof_pocket_width_mm':20.8,
             'roof_pocket_Y_mm':[47.6,57.1],'roof_pocket_Z_mm':[64,68],
             'roof_stop_face_Z_mm':64,'bezel_guide_face_Z_mm':66.2,'crown_travel_mm':1,
             'moving_low_Y_max_mm':56.8,'tip_diameter_mm':2,'spring_seats_Z_mm':[65.8,70.3]}}

def clear_rail_pockets(doc,roof):
    """Finish coupon counterparts with the same API used by the dock master."""
    f=fixed_features()
    stage(doc,roof,'FinalRailPocketsAndConnectedStopWings',roof.Shape,
          f['orange_roof_downstop_and_return_adds'],f['orange_roof_cuts'],
          '20.8mm pocket clears separatecreamrails; widerlowstopwingsconnecttoroofoutsidepocket.')
    # Reapply low stop wings after cutting; the cut starts at their top plane.
    assert roof.Shape.isValid()and len(roof.Shape.Solids)==1
    return roof

def build_components(doc,board_z=60.5,gap=.2,solder=.05,switch_height=3.1,prefix='DockButton'):
    """Build only3retained blue caps +3selected springs in an existing native.

    Returns components and named boolean counterparts. No switch duplication,
    coupons, master mutations, external files or saves. Shapes use global dock
    coordinates. Call from a normal FreeCAD GUI/VM to retain assigned colours.
    """
    assert 60<=board_z<=61 and .15<=gap<=.25 and 2.9<=switch_height<=3.3
    sheet=doc.addObject('Spreadsheet::Sheet',prefix+'Parameters')
    for i,(name,value)in enumerate([('BoardZ',board_z),('SolderStandOff',solder),('RestGap',gap),
                                  ('MeasuredSwitchHeight',switch_height)],1):
        sheet.set('A'+str(i),name);sheet.set('B'+str(i),str(value)+' mm');sheet.setAlias('B'+str(i),name)
    params={'board_z':board_z,'gap':gap,'solder':solder,'switch_height':switch_height,'sheet_name':sheet.Name}
    caps=[];springs=[]
    for name,x,w,h in[('Left',-22,14,10),('Center',0,16,9),('Right',22,14,10)]:
        b,ignored=cap(doc,prefix+name+'Cap',w,h,params);b.Placement.Base.x=x;caps.append(b)
        springs.append(spring(doc,prefix+name+'Spring',65.8,4.5,x))
    doc.recompute()
    return {'caps':caps,'springs':springs,'parameters':sheet,'fixed_features':fixed_features()}

def coupon_screw(doc,name,diameter,length,head,height,x,y,z,invert=False):
    b=doc.addObject('PartDesign::Body',name)
    sk=b.newObject('Sketcher::SketchObject',name+'PrimaryProfile')
    sk.Placement.Rotation=App.Rotation(V(1,0,0),90)
    r,rh=diameter/2,head/2;rim=height-(rh-r)
    pts=[(0,0),(rh,0),(rh,-rim),(r,-height),(r,-length),(0,-length)]
    for p,q in zip(pts,pts[1:]+pts[:1]):
        i=sk.addGeometry(Part.LineSegment(V(*p),V(*q)),False)
        sk.addConstraint(Sketcher.Constraint('Block',i))
    doc.recompute()
    rev=b.newObject('PartDesign::Revolution',name+'ExternalRevolution')
    rev.Profile=sk;rev.ReferenceAxis=(sk,['V_Axis']);rev.Angle=360;doc.recompute()
    assert rev.Shape.isValid()and len(rev.Shape.Solids)==1
    b.Placement=App.Placement(V(x,y,z),App.Rotation(V(1,0,0),180)if invert else App.Rotation())
    b.addProperty('App::PropertyString','ModelBasis');b.ModelBasis='Manufacturer external dimensions; cosmeticthreads/PHrecess omitted, not a strength or torque proof.'
    return b

def save_exports(doc,bodies,freecaps):
    OUT.mkdir(parents=True,exist_ok=True);printdir=OUT/'print';printdir.mkdir(exist_ok=True)
    for body in bodies+freecaps:
        assert body.Shape.isValid()and len(body.Shape.Solids)==1,body.Name
        # Free cap bodies are translated for the native build sheet only;
        # their print export is recentered to a convenient build datum.
        shape=body.Shape.copy()
        if body in freecaps:shape.translate(V(-body.Placement.Base.x,-body.Placement.Base.y,0))
        mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=.06,AngularDeflection=.18,Relative=False)
        mesh.write(str(printdir/(body.Name+'.stl')))
        shape.exportStep(str(OUT/(body.Name+'.step')))
    doc.recompute();doc.saveAs(str(OUT/'ButtonMechanicsTrial.FCStd'))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--board-z',type=float,default=60.5);ap.add_argument('--gap',type=float,default=.2)
    ap.add_argument('--switch-height',type=float,default=3.1);ap.add_argument('--solder',type=float,default=.05);a=ap.parse_args()
    assert 60<=a.board_z<=61 and .15<=a.gap<=.25 and 2.9<=a.switch_height<=3.3 and 0<=a.solder<=.15
    assert sha(SWITCH)==SWITCH_SHA
    OUT.mkdir(parents=True,exist_ok=True)
    doc=App.newDocument('ButtonMechanicsTrial');doc.Label='Retained blue button / inert force coupon / NOT QUALIFIED'
    sheet=doc.addObject('Spreadsheet::Sheet','Parameters')
    for i,(name,value)in enumerate([('BoardZ',a.board_z),('SolderStandOff',a.solder),('RestGap',a.gap),('CapStroke',1.0),('SpringInstalledLength',4.5),('MeasuredSwitchHeight',a.switch_height)],1):
        sheet.set('A'+str(i),name);sheet.set('B'+str(i),str(value)+' mm');sheet.setAlias('B'+str(i),name)
    params={'board_z':a.board_z,'gap':a.gap,'solder':a.solder,'switch_height':a.switch_height}
    roof,ret=stationary(doc);clear_rail_pockets(doc,roof);base=support(doc,a.board_z)
    installed=doc.addObject('App::Part','InstalledCoupon')
    for b in(roof,ret,base):installed.addObject(b)
    screws=[]
    for x in(-32,32):
        for y in(45,63):
            b=coupon_screw(doc,'Accu_M2x6_'+str(x).replace('-','N')+'_'+str(y),2,6,3.8,1.2,x,y,70.5)
            b.Label='Accu SIK-M2-6-A2 / coupon only';installed.addObject(b);screws.append(b)
    for x in(-38,38):
        for y in(45,63):
            b=coupon_screw(doc,'Accu_M3x12_'+str(x).replace('-','N')+'_'+str(y),3,12,5.5,1.65,x,y,a.board_z-3,True)
            b.Label='Accu SIK-M3-12-A2 / coupon only';installed.addObject(b);screws.append(b)
    source=Part.Shape();source.read(str(SWITCH));assert source.isValid()
    freecaps=[];pose_caps=[];springparts=[];returns=[]
    for i,(name,x,w,h)in enumerate([('Left',-22,14,10),('Center',0,16,9),('Right',22,14,10)]):
        capbody,rd=cap(doc,name+'CapInstalled',w,h,params);capbody.Placement.Base.x=x
        installed.addObject(capbody);pose_caps.append(capbody);returns.extend(rd)
        sw=doc.addObject('PartDesign::Body',name+'SelectedB3FS1002P')
        feature(doc,sw,name+'DetailedSelectedSwitch',source,'Detailed selectedKiCadmodel; notOEMCAD; actuatorinternals/overtravelnotasserted.')
        sw.Placement.Base=V(x,54,a.board_z+a.solder)
        sw.setExpression('Placement.Base.z','Parameters.BoardZ + Parameters.SolderStandOff')
        installed.addObject(sw)
        sp=spring(doc,name+'LC014B02S',65.8,4.5,x);installed.addObject(sp);springparts.append(sp)
        free,ignored=cap(doc,name+'CapFREE_PRINT',w,h,params,lift=.5,free=True)
        free.Placement.Base=V(x,-30,0);freecaps.append(free)
    # Keep a recoverable native checkpoint before the illustrative pressed pose.
    doc.recompute();doc.saveAs(str(OUT/'ButtonMechanicsTrial.FCStd'))
    pressed_caps=[]
    for name,x,w,h in [('Left',-22,14,10),('Center',0,16,9),('Right',22,14,10)]:
        pressed,rd=cap(doc,name+'CapPressedPose',w,h,params,press=1,lift=.55)
        pressed.Placement.Base=V(x,30,0);pressed_caps.append(pressed)
    # Tooling puck is a real printed bench anvil, never an electronic-part proxy.
    puck=doc.addObject('PartDesign::Body','InertForceProbePuck')
    feature(doc,puck,'PrintedAnvil',union([Part.makeCylinder(4,2),Part.makeCylinder(1.5,12,V(0,0,1.99))]),
            'Useonlywithunpoweredcoupon and external calibratedloadcell/micrometer; not a switchmodel.')
    puck.Placement.Base=V(38,20,0)
    doc.recompute()
    # Individual parts valid, cap shoes captive and FFC clearance checked on
    # actual native solids. Soft contacts/stops are explicitly distinguished.
    ffc=box(-7.5,57.4,61.5,7.5,66,68.2)
    for o in[roof,ret,base,pose_caps[1],springparts[1]]:
        assert o.Shape.common(ffc).Volume<1e-6,(o.Name,'FFCkeepout')
    assert all(abs(r['toe_lowest_Z_mm']-64)<1e-6 for r in returns)
    # Board-height expressions are live native constraints, not a box fit.
    stack=[]
    for z in(60,60.5,61):
        sheet.set('B1',str(z)+' mm');doc.recompute()
        for o in pose_caps+freecaps+pressed_caps:assert o.Shape.isValid()and len(o.Shape.Solids)==1
        tipz=z+a.solder+a.switch_height+a.gap
        stack.append({'board_F_Z_mm':z,'released_switch_nominal_Z_mm':z+a.solder+3.1,
            'loaded_shoe_tip_Z_mm':tipz,'nominal_gap_mm':a.gap,'tip_projection_below_shoe_mm':65-tipz})
    sheet.set('B1',str(a.board_z)+' mm');doc.recompute()
    save_exports(doc,[roof,ret,base,puck],freecaps)
    spring_manifest=dict(SPRING);spring_manifest.update({'installed_length_mm':4.5,'nominal_preload_N':SPRING['rate_N_per_mm']*(7.95-4.5),
        'nominal_max_force_at_additional0p9mm_N':SPRING['rate_N_per_mm']*(7.95-3.6),
        'deflection_fraction_at3p6mm':(7.95-3.6)/(7.95-1.96),'solid_reference_plus5percent_mm':1.96*1.05,
        'received_required':True,'catalog_tolerances_alone_guarantee_minimum_preload':False,
        'incoming_assembled_preload_accept_N':[2.20,2.35],'guide_reaction_abs_max_N':.15,
        'net_engagement_minimum_from_acceptance_N':2.20-.15,'maximum_transmitted_force_accept_N':3.2})
    (OUT/'spring-selection.json').write_text(json.dumps(spring_manifest,indent=2)+'\n')
    report={'status':'first native inert/buttoncoupon; no print,receivedpart,force,strength orpoweredresult',
       'builder_sha256':sha(Path(__file__)),'native_sha256':sha(OUT/'ButtonMechanicsTrial.FCStd'),
       'selected_switch_model_sha256':SWITCH_SHA,'selected_spring':SPRING['mpn'],
       'parameters':params,'cap_centers_mm':[[-22,54],[0,54],[22,54]],'visible_heads_mm':[[14,10,2.7],[16,9,2.7],[14,10,2.7]],
       'cap_face_rest_Z_mm':[70.3,73],'cap_stroke_mm':1.0,'upstop_ring_top_Z_mm':66.2,'downstop_lands_Z_mm':64,
       'hidden_roof_pocket_each_mm':[20.8,9.5],'hidden_pocket_Y_mm':[47.6,57.1],
       'moving_ring_X_local_mm':[-8.8,8.8],'moving_low_geometry_center_Y_max_mm':56.8,
       'return_arm_nominal':{'length_mm':10.4,'width_mm':.8,'thickness_mm':.6,'predeflection_mm':.7,
           'assumed_E_MPa':[1200,2000],'strain_is_analytical_not_strength_proof':True,'installed_geometry':returns},
       'stack_parameter_checks':stack,'native_print_bodies':[b.Name for b in[roof,ret,base,puck]+freecaps],
       'exact_switch_internal_motion_modelled':False,'spring_turn_distribution_is_cosmetic':True,
       'FFC_reserved_volume_intersection_mm3':0,'order_or_full_product_release':False}
    (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'native':str(OUT/'ButtonMechanicsTrial.FCStd'),'print_bodies':len(report['native_print_bodies']),'status':report['status']}))
    App.closeDocument(doc.Name)

if __name__=='__main__':main()
