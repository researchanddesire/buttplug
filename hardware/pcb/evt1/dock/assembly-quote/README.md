# Dock EVT1 PCB assembly quote

Exact parts, native KiCad positions, saved native board and the matching fabrication quote are included. This is an EVT assembly quote, not a complete device release or an order. Supplier acceptance and physical commissioning remain pending.

Use the purchased-positions file with the assembly-parts worksheet. Units are mm, rotation and side are exported by KiCad. Preserve native coordinates; do not independently recenter/mirror a file. Reconcile package zero angles and pin1/cathode markings with the native Fab drawing before programming placement. Review paste/stencil and reflow, including module/IC exposed pads.

Copper features and manual assembly operations are not bought parts:

- J93: Four hand-solder pin-board loom lands.
- TP91: Copper fault test pad; no purchased test pin.

D1 on the flange has custom logical numbering: physical cathode stripe at pad2/CAD cathode bar. Keep body JP1 open until the independent charge-guard tests pass. Solder the four pogo pins square to the1mm pin board in the carrier fixture; inspect pitch/height and the rear J94 wires before fitting its retainer. No connector or header is fitted to a hand-solder loom land.

C83 selection is22uF/25V X5R; the generic schematic10V marking is a minimum rating. Its lot/process acceptance is at least10uF effective at3.3V over the intended temperature/age. Verify regulator effective capacitance and electrical/thermal behavior in commissioning. Manufacturer reference curves do not guarantee the installed result.
