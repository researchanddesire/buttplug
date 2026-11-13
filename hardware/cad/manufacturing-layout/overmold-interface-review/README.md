# Mold review for the single-board flange

The earlier two-part casting tool intersects the current closed rear cover
and completely encloses the current face mask. The rear cover's flat face
is at Y−28.7 mm, 2.2 mm beyond the earlier flat cavity wall at Y−26.5 mm.
The four metal target faces are at Y−30.0 mm, and the mask reaches Y−32.0 mm.
FreeCAD found 4,305 mm³ of overlap with the rigid rear half and 246 mm³
with the mask. The [intersection report](interference-check.json) records
both native source hashes and the overlap bounds. The [section traces](sections.json)
cut through the USB D− target at X−10 mm.

Keep the closed tray and rear half in their current positions for this
review. A revised two-half tool can add a removable rear insert that holds
the four-face mask. This gives the mask a straight exit along −Y before
the mold halves open along ±Z. Locate the flange from the rigid assembly
and support the mask from the tool so tool closure does not set contact
height through the PCB. Measure all four received face heights before
selecting the shutoff or defining an allowable clamp load. Give the insert
an external pull feature and check the entire pull, including clearance to
the rear wall, gate, dowels and clamp bolts.

A separate alternative is a full removable rear tool plate carrying the
contact shutoffs. It simplifies straight rear access and can include the
rear button and arrow details, with an additional parting seam and more
tool assembly. Show the new parting line and gate before selecting it.
Both options preserve the sequence of securing the lower metal body,
closing both rigid halves and casting one continuous skin.

The [small rear insert candidate](rear-insert-candidate/README.md) is now
saved as an editable FreeCAD model. Its opening reaches the parting plane,
and the gate moves to X20 mm to clear that opening. The sampled insert
pull and side opening pass against the current flange geometry.

The closed-cup and contact sleeve insert is already modeled. Its Ø1.60 mm
sleeves must stretch over Ø3.175 mm heads and seal around Ø1.702 mm necks.
Try the existing insert on an inert closed assembly and inspect the
sleeves after installation. Establish flash, fill and leakage on dummy
parts before modeling an assumed seal or casting over electronics.
The earlier [solid-dummy casting tool](../overmold-trial/README.md) remains
available for its original fill and demolding trial.
