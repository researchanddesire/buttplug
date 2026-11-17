# Compass master bench and compact USB evaluation

The [Master Bench KiCad project](../../../pcb/evt1/one-board-dev/compass-one-board-dev.kicad_pro)
and [Compact KiCad project](../../../pcb/evt1/one-board/compass-one-board.kicad_pro)
run the same `evt1-one-board` firmware and keep the same charger, recovery and
independent thermal protection. The bench board replaces three loose host
jumpers with one shrouded **J112** selector. The compact keeps its existing
four pressure contacts and moves between the [direct PC contact fixture](../../../cad/evt1-assembly/direct-pc-fixture/README.md)
and the dock. Its [USB-C adapter PCB](../../../pcb/evt1/direct-pc-contact-adapter/compass-direct-pc-adapter.kicad_pro)
connects to the saddle's pin board. Both mates use the same contact row and seat, so they cannot mate
simultaneously. Moving between them starts a new USB session.

| Mode | Master Bench | Compact plug |
| --- | --- | --- |
| Plug alone | J112 empty; use a pack simulator at J2 with the J122 link fitted after inspection. | No contact mate. Power, Mode and motor on the simulated or qualified pack. |
| Plug to PC | `PC` key in J112. PC data cable into J110. | Fit the direct PC saddle, then attach USB-C. Verify charge after guard commissioning; verify CDC, flashing and hardware ROM recovery. |
| Plug to dock | `DOCK` key in J112. One dock host feed at J111. | Lift the plug out of the direct saddle before seating it in the dock. The dock or its PC passthrough owns the pair. |
| Dock alone | J112 empty; power the dock independently with its output unloaded. | Leave the plug out. Check dock display, buttons and no-plug reporting when the wired dock is available. |

The bench keys switch VBUS, D− and D+ as a group; signal ground remains
common. Change keys with both cables and pack power removed. Only after
checking the two shop-built keys unpowered should both upstream cables be
attached with a key fixed for isolation testing. Test that the open or
unselected port has no source backfeed or driven data. The bare selector
socket is deliberately OFF. The bench PCB emulates the plug, and a dock
main board and its display/safety modules connect separately.

## Sequence on received hardware

1. Begin with JP1 open, no motor, a current-limited supply and an inert pack
   simulator. Verify polarity and rails before adding logic or motor links.
   Confirm each guard independently with valid, open, short, hot and cold
   inputs. Use the existing pack simulator procedure before fitting a pack or
   enabling charging. Keep uncommissioned UV emitters disconnected.
2. With USB disconnected, check GND/D−/D+/5 V on J111 and the contact fixture,
   inactive port isolation and no adjacent shorts. Power the contact fixture
   into a dummy load first. Log contact voltage, inrush and current limit.
   Test one unattached, partially seated and fully seated position before
   USB transfers. Deliberately misoriented fitting is an unpowered test.
   Begin with the USB-C cable removed while seating the saddle. Use a known
   powered data port and measure `VBUS_CHG` at the charger, including the
   cable, contacts, and board input diode drop.
3. Test both USB-C cable orientations. Record enumeration, repeatable CDC
   reads, firmware flash and hardware ROM recovery. Power and Mode must be
   accessible with the compact fixture seated. Repeat the recovery path
   with the operational firmware unavailable. Never swap sources during a
   flash; check recovery separately after an intentionally interrupted test.
4. On a battery-simulated plug, capture VBUS, `DOCK_PRESENT_N`, 3V3, and USB
   disconnect/reattach on repeated PC-to-dock and dock-to-PC transfers.
   Remove the first mate completely. Verify new enumeration and absence of
   stale peer commands or motor enable while docking. Establish physical
   ground/data/power sequencing and bounce before relying on live insertion.
5. The [Pico H host fixture](../contact-interface/standalone-usb.md) can
   exercise dock-host data and recovery on the open bench before a finished
   dock exists. Keep its VSYS and the plug's current-limited 5 V separate,
   connect common ground, and leave the Pico USB VBUS wire open. It does not
   validate the dock's installed host switch, UI, charging states or UV.
   The [wired Main](../../../pcb/evt1/case-telemetry-study/wired-main/README.md)
   still has 13 opens in the checked KiCad source. Its manufacturing/safety
   sequence is separate; do not upload that PCB for this eval.

See [vendor operations](vendor-assembly.md) for what to include with the
Gerbers and BOM. Use [JLC's BOM/CPL guidance](https://jlcpcb.com/help/article/advice-for-bom-and-cpl-files-preparation)
to check layer, orientation and exact match on both sides before accepting
the assembly quote. The export is for prototype evaluation.
