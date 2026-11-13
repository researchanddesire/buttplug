"""Concrete mounts for two independent drawing-based D2F-01L lid cutoffs.

The installed blade is a nominal actuated reference. Commission each received
switch using its electrical OP/RP and the actual adjuster; CAD does not prove
switch travel, shutdown timing, thread strength or optical containment.
"""
CENTRES=((-50.5,30,31),(50.5,30,31))
FORCE_POINT_Y=37.55
POST_BEARING_Z=43.1
NOMINAL_BACKOUT=2.0


def add(doc,lower,upper,helpers):
    import FreeCAD as App
    import Part
    native_extrusions=helpers['native_extrusions'];circle=helpers['circle']
    pocket=helpers['pocket'];pad=helpers['pad'];note=helpers['note']
    # A chorded outside edge stays inside the real rounded lower shell at
    # the front corner; it is not a rectangular wall protruding through it.
    outline=((53.4,23),(55.7,23),(57.6,27),(57.6,37),(53.4,37))
    walls=[]
    for sign in(-1,1):
        pts=[App.Vector(sign*x,y,12.9)for x,y in outline]
        if sign<0:pts.reverse()
        walls.append(Part.Face(Part.makePolygon(pts+[pts[0]])).extrude(App.Vector(0,0,21.1)))
    native_extrusions(lower,'IndependentLidCutoffMountWalls',walls)
    for side,sign in enumerate((-1,1)):
        rotation=App.Rotation(App.Vector(0,1,0),90*sign)
        for i,y in enumerate((26.75,33.25)):
            pocket(lower,'LidCutoffMountPilot'+str(side)+str(i),
                   circle(lower,'LidCutoffMountPilotProfile'+str(side)+str(i),.5,
                          (sign*53.3,y,31),rotation),5.2,True)
        # Two wired poles and the insulated unused NC tail have an explicit
        # installation/egress opening. Opacity and loom restraint follow.
        tool=Part.makeBox(3,14,2.2,App.Vector(sign*50.5-1.5,23,10.9))
        native_extrusions(lower,'LidCutoffTailEgress'+str(side),[tool],True)
        pad(upper,'LidCutoffActuatorPost'+str(side),
            circle(upper,'LidCutoffActuatorPostProfile'+str(side),2.6,
                   (sign*50.5,FORCE_POINT_Y,POST_BEARING_Z)),55.6-POST_BEARING_Z)
        pocket(upper,'LidCutoffActuatorPilot'+str(side),
               circle(upper,'LidCutoffActuatorPilotProfile'+str(side),.5,
                      (sign*50.5,FORCE_POINT_Y,POST_BEARING_Z-.1)),10.8,True)
    note(lower,'LidCutoffMounts','D2F-01L mountlineZ31 atX±50.5/Y30; length+Y,forcepointreferenceY37.55. Four M2x10 mounting screws enter from chamber side. Jig-drill1.6/tapM2x0.4 printed1mm pilots with received switch. Tail slots need an opaque restrained loom/grommet; optical safety is not established.')
    note(upper,'LidCutoffActuators','Two M2x10 downward adjusters/jamnuts against postsZ43.1. Nominal2mm backout yields faceZ37.5,0.3mm beyond nominalOP. Extra adjustment reserves head/nut/mount tolerance. Set each received switch electrically, verify remainingtravel and measuredRP, lock/retest independently. No restart/optical or strength qualification follows.')
    return {'case_centres_mm':CENTRES,'force_point_Y_mm':FORCE_POINT_Y,
            'post_bearing_Z_mm':POST_BEARING_Z,'adjuster_MPN':'SNSS-M2-10',
            'jamnut_MPN':'HPN-M2-A2-BL','nominal_backout_mm':NOMINAL_BACKOUT,
            'nominal_face_Z_mm':37.5,'nominal_OP_past_setting_mm':.3,
            'required_received_face_range_mm':[36,39],
            'mechanical_adjustment_allowance_mm':[0,4.2],
            'commissioned':False,'physical_validation':False}
