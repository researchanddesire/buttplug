# Pre-radio dock Main bench quote

Use `dock-main-fabrication-quote.zip` to request bare-board pricing and `dock-main-assembly-quote.zip` to request fabrication and assembly pricing. Both packages bind to frozen board SHA-256 `e10043f2fa456c4a88848a612f13ad501c49fdee64e4a509484fa86a7a5c674b`. The exact parts table covers 138 placements on the front, grouped into 45 manufacturer part lines. The separately listed 12 copper-only features remain in the artwork and have no purchased placements. The boards and cable assemblies outside Main are separate quotes.

This revision retains Main R107 at 34.8 kΩ, Yageo `RT0603BRD0734K8L`. Its matching UV base R401 and UV lid R501 are 3.65 Ω, Vishay `CRCW08053R65FKEA`, with nominal LED current about 54.8 mA. Use the corresponding [UV base quote](../../dock-uv/base/pcb/fabrication-review/uv-base-supplier-review.zip) and [UV lid quote](../../dock-uv/lid/pcb/fabrication-review/uv-lid-supplier-review.zip) for that bench configuration. The case radio and its coupled power-budget changes belong to the separate radio study.

## Quote notes

- Use the exact manufacturer and MPN for every purchased position. Return availability, lead times and any proposed substitutions for review. Use front assembly coordinates as exported by KiCad in millimetres, with KiCad Y inverted and the board's native origin preserved. Confirm the assembler's rotation convention against the front assembly drawing.
- Fit GCT J101 `USB4105-GF-A-120` as an SMT receptacle with four plated shell stake slots. Include their attachment in the process quote. Preserve the two nonplated J101 locating holes, the three nonplated Tag-Connect tooling holes and all six Ø2.30 mm mounts. J102–J104 are unpopulated solder lands. J202 is a direct programming contact pattern.
- Return the finished stackup, finished copper, via bore and wall-plating minima, copper/drill tolerances, and proposed solderable surface finish. The Gerber job lists the finish as unspecified. Confirm the exact J101 plated slots and the local 0.10 mm annular-ring and 0.15 mm hole-to-copper capability before releasing fabrication. See the packaged manufacturing specification and constraints for the 1.00 mm four-layer stack, other dimensional limits and the required hot/aged ≤50 mΩ four-wire copper measurement for each UV supply/return path.
- Supplier acceptance, installed fit, USB and source transients, power/temperature, UV leakage and cleaning efficacy require bench qualification. This package is for quotes. It contains no physical test results.

The assembly package includes the editable native board, project, custom rules and referenced local libraries/models. The native centroid is retained with the audit evidence. Send `dock-main-assembly-positions.csv` to the assembler, because KiCad also exports three of the manual lands in its raw centroid. Each archive includes the relevant file hashes and native electrical/export check counts.

Regenerate with `python3 export_quote.py --kicad-cli /path/to/kicad-cli` using KiCad 10.0.8.
