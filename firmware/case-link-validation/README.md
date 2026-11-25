# EVT1 case-link firmware validation

The [source-bound report](validation.json) records clean PlatformIO builds of
`evt1` and `prototype-r0` from a separate source snapshot. It binds the host
thermal/console/telemetry/runtime/GATT tests, C3 sender to STM32 decoder
roundtrip, protocol, toolchain and linked artifacts. Linked checks place the
case service in EVT1 only and verify the USB detach ISR in IRAM. Original
thermal-only evidence remains in `../thermal-history-validation/`.

Artifact paths in the report identify local build evidence. Rebuild with
`pio run -d firmware -e evt1 -e prototype-r0`. Nothing was flashed; over-air
pairing/transport, powered docking and the case-side runtime remain open.
