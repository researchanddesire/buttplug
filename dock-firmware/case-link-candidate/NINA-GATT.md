# Case telemetry over the NINA command channel

The case transport starts with a commissioned peer and an authenticated,
encrypted ACL. It takes the connection handle from the caller. The plug's
NimBLE service requires authentication, encryption and a 16-byte key on reads,
writes and notifications. The caller still needs to verify the provisioned
peer identity and handle bond loss. A service UUID, connection event or
stored bond entry alone cannot establish an authenticated connection.

With the NINA in command mode and echo off, discover the Compass service by
UUID. Discover its six characteristics and check their value handles and
properties. Find and enable the five notification descriptors within their
respective characteristic ranges. Use a confirmed characteristic write for
commands. A successful write acknowledgement leaves the command pending
until the plug sends the matching result with the session ID and request ID.
Direct telemetry reads commit after the matching data and final acknowledgement.
Incoming values must be 20 bytes and belong to the active connection and a
discovered handle. The session cache keeps its existing clock, freshness
and result-correlation rules.
[u-blox AT Commands Manual R56, §§13.3, 13.5–13.7, 13.10–13.11 and 13.14](https://content.u-blox.com/sites/default/files/documents/u-connectXpress-ATCommands-Manual_UBX-14044127.pdf)
· [u-blox user guide, §4.5](https://content.u-blox.com/sites/default/files/u-connectXpress_UserGuide_UBX-16024251.pdf)

Each call reads at most 32 software RX bytes and never performs I²C itself.
The caller continues to schedule bridge I²C and checks the transport each
frame. A 5 s command/ack deadline bounds discovery and serial response. The
case policy separately bounds the plug result. A timeout before serial
enqueue cancels the unsent command. After enqueue, the operation may have
reached the plug. Disconnect, module reset, bridge fault, an invalid record
or an unexpected command response closes the case cache. The caller owns
resetting the UART and discarding remaining bytes before a new connection.

Run the host sender/receiver roundtrip and Cortex-M0+ compile from the repo.

```sh
make -C dock-firmware/case-link-candidate -f nina-gatt.mk nina-gatt-test nina-gatt-compile
```

The host traces split input across calls and test discovery, descriptor range,
response ordering, actual C3 snapshot and anchor responses, thermal freshness,
disconnect, unknown handles, stale epochs and wraparound. The alternate dock
image currently ends at UART profile verification. Next integration needs
provisioning and a powered trace for the exact NINA-B112-05B-00 firmware. Verify
central and keyboard-only profile, passkey entry, commissioned identity,
encrypted reconnect and rejection of an unpaired or wrong device. Measure
serial throughput and alert latency with ADS sampling and LCD writes active.
