"""Native shell supports and liner openings for the selected routed dock PCBs.

Board shapes remain external StepUp components. These are real printed-part
features, not PCB fit proxies. M2 taps/torque and received tolerances still
need trials. The UI board has a documented adjustable shim trial; its starting
height is not a qualified loaded LCD-contact datum.
"""
UV_HOLES=((-45,89),(45,89),(-45,132),(45,132))
UPPER_LINER_HOLES=((-50,80),(50,80),(-25,144),(25,144))
UI_HOLES=((-30,65),(30,65),(-32,115),(32,105))
UI_F_PLANE=60.5
UI_BOSS_SEAT=61.5
BEZEL_HOLES=((-34.5,69),(34.5,69),(-13,105),(13,105))
UV_CLEARANCE_OUTLINE=((-49.5,85.5),(-34.5,85.5),(-34.5,127.5),
                      (34.5,127.5),(34.5,85.5),(49.5,85.5),
                      (49.5,135.5),(-49.5,135.5))


def add(doc,base,lid,lower,upper,helpers,bezel=None):
    import FreeCAD as App
    import Part
    import Sketcher
    circle=helpers['circle'];pad=helpers['pad'];pocket=helpers['pocket']
    loft=helpers['loft'];rr=helpers['rr'];note=helpers['note']

    def polygon(body,name,points,z):
        sketch=body.newObject('Sketcher::SketchObject',name)
        sketch.Placement.Base=App.Vector(0,0,z)
        for p,q in zip(points,points[1:]+points[:1]):
            i=sketch.addGeometry(Part.LineSegment(App.Vector(p[0],p[1],0),App.Vector(q[0],q[1],0)),False)
            sketch.addConstraint(Sketcher.Constraint('Block',i))
        doc.recompute();assert sketch.FullyConstrained,name
        return sketch

    # The four front USB bosses already match the common base PCB. Two rear
    # supports prevent the enlarged board relying on a long unsupported span.
    for i,(x,y)in enumerate(((-44,64),(44,55.7))):
        pad(base,'MainRearBoardBoss'+str(i),circle(base,'MainRearBoardBossProfile'+str(i),2.6,(x,y,3)),2.4)
        pocket(base,'MainRearBoardPilot'+str(i),circle(base,'MainRearBoardPilotProfile'+str(i),.5,(x,y,5.4)),4)

    # Apertures clear actual one-millimetre U boards and their back-side parts.
    # Small corner reliefs accommodate the board's router-made R1 concave
    # corners without relying on the sharp polygon's diagonal clearance.
    for body,prefix,top,depth in ((lower,'LowerUVBoard',13.1,2.2),
                                  (upper,'UpperUVBoard',57.6,2.3)):
        pocket(body,prefix+'Aperture',polygon(body,prefix+'ApertureProfile',UV_CLEARANCE_OUTLINE,top),depth)
        for i,x in enumerate((-35,35)):
            pocket(body,prefix+'RouterCorner'+str(i),circle(body,prefix+'RouterCornerProfile'+str(i),1.75,(x,128,top)),depth)

    for i,(x,y)in enumerate(UV_HOLES):
        pad(base,'LowerUVBoardBoss'+str(i),circle(base,'LowerUVBoardBossProfile'+str(i),2.6,(x,y,3)),9.2)
        pocket(base,'LowerUVBoardPilot'+str(i),circle(base,'LowerUVBoardPilotProfile'+str(i),.5,(x,y,12.2)),8.2)
        pad(lid,'UpperUVBoardBoss'+str(i),circle(lid,'UpperUVBoardBossProfile'+str(i),2.6,(x,y,56.3)),7.8)
        pocket(lid,'UpperUVBoardPilot'+str(i),circle(lid,'UpperUVBoardPilotProfile'+str(i),.5,(x,y,56.2)),7,True)
        # Rear screw heads otherwise clip the chamber's sloping side wall
        # below the board-front plane; the roof-only U aperture is too shallow.
        if y==132:
            pocket(upper,'UpperUVHeadClearance'+str(i),
                   circle(upper,'UpperUVHeadClearanceProfile'+str(i),2.2,(x,y,55.4)),2.3)

    # The upper cream chamber now has a removable four-screw attachment too.
    # Its two front/two rear datums avoid UV boards and the central hinge loom.
    for i,(x,y)in enumerate(UPPER_LINER_HOLES):
        pad(lid,'UpperLinerBoss'+str(i),circle(lid,'UpperLinerBossProfile'+str(i),2.6,(x,y,57.5)),6.6)
        pocket(lid,'UpperLinerPilot'+str(i),circle(lid,'UpperLinerPilotProfile'+str(i),.5,(x,y,57.4)),6.1,True)
        pocket(upper,'UpperLinerScrewBore'+str(i),circle(upper,'UpperLinerScrewBoreProfile'+str(i),1.1,(x,y,55.4)),2.2,True)
        pocket(upper,'UpperLinerHeadRim'+str(i),circle(upper,'UpperLinerHeadRimProfile'+str(i),2.15,(x,y,55.4)),.45,True)
        loft(upper,'UpperLinerCountersink'+str(i),[
            circle(upper,'UpperLinerSinkOuter'+str(i),2.15,(x,y,55.8)),
            circle(upper,'UpperLinerSinkInner'+str(i),1.1,(x,y,56.85))],subtract=True,ruled=True)

    # Equal 0.5..1.5mm insulating shims set the UI F plane to61.0..60.0.
    # Four coplanar seats stay fixed; jig drill/tap after receiving the board.
    for i,(x,y)in enumerate(UI_HOLES):
        pad(lid,'UIBoardBoss'+str(i),circle(lid,'UIBoardBossProfile'+str(i),2.6,(x,y,UI_BOSS_SEAT)),2.6)
        pocket(lid,'UIBoardPilot'+str(i),circle(lid,'UIBoardPilotProfile'+str(i),.5,(x,y,61.4)),5.8,True)
        # The board screws enter from below. Recesses preserve access and
        # allow the full trial interval without their2mm heads hitting liner.
        pocket(upper,'UIBoardHeadClearance'+str(i),circle(upper,'UIBoardHeadClearanceProfile'+str(i),2.2,(x,y,57.6)),.8)
    # Only the four1206 flying capacitors need extra depth at the low trial
    # endpoint. Their selected1.95mm mounted allowance is checked separately
    # from the nominal KiCad component BReps.
    pocket(upper,'UIFlyingCapacitorClearance',
           rr(upper,'UIFlyingCapacitorClearanceProfile',12,6,1,57.6,(.25,111.2)),.8)

    if bezel is not None:
        native=helpers['native_extrusions']
        native(lid,'BezelSupportSeats',[
            Part.makeCylinder(2,3.7,App.Vector(x,y,64))for x,y in BEZEL_HOLES])
        native(lid,'BezelScrewClearances',[
            Part.makeCylinder(1.1,4,App.Vector(x,y,63.8))for x,y in BEZEL_HOLES],True)
        native(bezel,'BezelTapPilots',[
            Part.makeCylinder(.5,2.5,App.Vector(x,y,67.6))for x,y in BEZEL_HOLES],True)
        note(bezel,'Retention','Four inside-access NBK SNSS-M2-6 screws: underheadZ64, nominal2.3mm engagement in back of bezel. Jig-drill1.6/tapM2x0.4 printed1mm pilots; verify receivedlength, thread strength and nofront breakthrough. Install bluecaps/springs andfastenbezel BEFORE UIboard. This retains buttonupstops; LCD compliant support is a separate integration task.')

    note(lower,'UVBoardInterface','U aperture clears1mm basePCB atFZ13.2/back12.2 with B-side parts. Shell bosses support actual four board holes. Mount hardware, thermal backing, strain relief and opacity remain to integrate/qualify.')
    note(upper,'MountingInterface','Four M2x6 countersunk attachment candidates from chamber side into lid bosses. Actual UVPCB Fplane55.3/normal-Z; Ry180 proper rigid placement preserves shared U outlineY. UI Fplane60.5 is an adjustable trial, not a qualified socket mating datum.')
    note(base,'PCBMountFinishing','New board-mount pilots are printed1mm, then jig-drilled1.6mm and tappedM2x0.4 using received boards as alignment reference. Qualify process/strength/torque; do not credit as-received print positions.')
    return {'lower_UV_Fplane_Z_mm':13.2,'upper_UV_Fplane_Z_mm':55.3,
            'UV_holes_dock_xy_mm':UV_HOLES,
            'upper_liner_holes_dock_xy_mm':UPPER_LINER_HOLES,
            'UI_holes_dock_xy_mm':UI_HOLES,'UI_trial_Fplane_Z_mm':UI_F_PLANE,
            'UI_fixed_boss_seat_Z_mm':UI_BOSS_SEAT,'UI_equal_shim_trial_range_mm':[.5,1.5],
            'bezel_inside_access_holes_xy_mm':BEZEL_HOLES,
            'radial_board_aperture_clearance_mm':.5,'router_corner_relief_radius_mm':1.75,
            'UV_boards_actual_fit_checked':False,'physical_validation':False}
