import FreeCAD as App, Part
M='/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/mech/'
O='/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board/build/mech/sections/'
s=Part.Shape(); s.read(M+'FlangeTray.step')
keep_x=Part.makeBox(42, 40, 40, App.Vector(-30, -30, -20))      # keep X < 12: section through the trough and the bowl sides
keep_z=Part.makeBox(60, 40, 23, App.Vector(-30, -30, -20))      # keep Z < 3: section along the length through the floor and ends
s.common(keep_x).exportStep(O+'TraySectionX.step')
s.common(keep_z).exportStep(O+'TraySectionZ.step')
