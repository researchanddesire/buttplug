# Wired Main package geometry

[Package report](package-models.json) binds the fourteen selected active devices
and crystal to their local KiCad footprints, manufacturer drawing limits and
sixteen valid STEP files. The number of models includes five package-family
passive models. Service lands are copper only. Passive MPN selection remains
open. KiCad models retain their embedded attribution and license. The local
RSV0016A STEP was reconstructed from TI drawing 4220314/C. The other models
are KiCad package-family geometry. Drawing limits and STEP sizes are separate
fields in the report.

- **U151, FSUSB42MUX.** Onsemi 846AP land example uses 1.40 × 0.30 mm lands
  on 4.40 mm row centers. The saved courtyard is 6.30 × 3.60 mm. Its
  lead-inclusive package outline is 4.90 × 3.10 × 1.10 mm before drawing
  exclusions. The exact courtyard fits at dock X2/Y17 with 1.35 mm nominal
  rigid clearance. The center trial intersects U114's reservation. The
  retained limiter-return via crosses both locations.
  [Onsemi 846AP](https://www.onsemi.com/download/package-drawing/pdf/846ap.pdf)
- **U155, TPS389033DSER.** TI DSE0006A has one longer land at pin 1 and
  different mask definitions on each side. The footprint uses −0.05 mm
  expansion for pins 1–3 and +0.05 mm for pins 4–6. Check mask registration and
  stencil in the assembly process. [TI DSE0006A](https://www.ti.com/lit/ds/symlink/tps3890.pdf)
- **U160, RP2040.** The land pattern agrees with the manufacturer's reduced
  3.20 × 3.20 mm PCB exposed land and 0.875 × 0.20 mm periphery lands on
  0.40 mm pitch. The device height is 0.90 mm.
  [Raspberry Pi package and footprint](https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf#page=608)
- **U161, W25Q16JVUXIQ.** The UX package is 3.00 × 2.00 × 0.55 mm nominal and
  0.60 mm maximum height. The footprint includes an isolated 0.20 × 1.60 mm
  center solder land and a smaller paste aperture. The symbol marks this
  physical pad 9 as unconnected. Keep it free of copper connections and vias.
  The Winbond UX drawing gives package terminal dimensions. The KiCad
  reference supplies the PCB land and paste design, which needs assembler
  review. [Winbond UX drawing](https://static.datasheets.com/doc/3906047-winbond-w25q16jvssiq-ds.pdf#page=67)
- **U152, TPD2EUSB30DRTR.** TI's DRT-3 package table gives a 0.45 mm maximum
  height. The KiCad DRT model measures 0.50 mm high, which the model clearance
  check uses. The planar allowance follows the product data sheet's 1 mm
  square package dimensions. [TI package table](https://www.ti.com/packaging/docs/searchtipackages.tsp?packageName=SO) · [TI product data sheet](https://www.ti.com/lit/ds/symlink/tpd2eusb30.pdf)

The saved underside volume at dock X−21/Y43 has 2.40 mm from the B.Cu seating
plane to its limiting shell floor. The tallest specified selected packages
are the 1.45 mm TI DBV parts. With a 0.05 mm assumed solder height, they leave
0.90 mm to the floor if placed wholly in that reservation. The KiCad DBV
package-family models are 1.55 mm high and leave 0.80 mm in the same check.
These are nominal height checks. Final component locations, board bow,
package/solder tolerances and loading remain to be verified on the populated
board. [Saved dock space check](../../../../cad/evt1-assembly/dock-harness-trial/wired-main-space-review/README.md)

From this directory, run `python check_package_models.py` with PythonOCC to
cold-read the local STEP files and validate numbered lands against the circuit
contract. Add `--stock-models <KiCad 10 3dmodels folder>` for byte comparison
with the KiCad package source. The `--install` option copies the identified
KiCad source models into this project and recreates the RSV model if absent.
All local model names match their footprint names. Use the `model_uri` values
in the package report when placing or exporting the PCB.
