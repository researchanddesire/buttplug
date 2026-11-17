# Wired CDC telemetry

The dock uses the plug's existing USB serial interface. It sends one command
at a time over CDC. The wire payloads are the existing 20-byte case telemetry
records, with tagged ASCII framing to coexist with diagnostic output.

- Request: `case-v1 <40 hex digits>\n`.
- Response: `case-v1 <kind> <8 hex session digits> <4 hex request digits> <40 hex digits>\n`.
  Hex numbers in the header are printed most-significant digit first. The
  payload is the existing byte order. CR and LF delimit incoming response
  lines. The response ends in kind 5, whose embedded session and request
  must match the header.
- Snapshot returns thermal, charge, source, first-valid, then result. Anchor
  returns result only. Replay returns up to three distinct thermal records,
  source, first-valid, then result. An unsuccessful request returns only
  its result. Unavailable readings retain the native validity indicators.

The dock receiver buffers one batch and rejects missing snapshot fields,
invalid reply ordering and missing causally matched samples advertised by
a replay. The result binds the batch to its original request and connection.
USB packets may split a line and diagnostic lines can arrive between replies.
A disconnect, timeout or malformed matching batch clears the live cache.
Samples skipped by an explicit snapshot poll remain visible as gaps. They
do not alter the original sequence or acquisition tick, and they do not
invalidate an otherwise valid clock anchor. The strict sequence checks
remain in place for the earlier asynchronous transport.

The USB host must validate the expected interface, preserve attach epochs,
and supply a non-reused logical session ID. It must honor USB TX acceptance
and close the reader on detach or mode switch. Leave a failed or stale link
out of the displayed live values. The wire reader has no CDC host driver or
GPIO control. It does not set charge completion or Ready.

Run the host roundtrip with the actual C3 record producer and compile the
receiver for Cortex-M0+.

```sh
make -C dock-firmware/case-link-candidate -f wired-cdc.mk wired-cdc-test wired-cdc-compile
python3 dock-firmware/case-link-candidate/validate.py
```

The validator also captures replies from the plug's actual console in the
host harness and feeds those bytes through the dock receiver. The separate
[Pico bench target](../wired-host-bench/README.md) uses the receiver with
the RP2040's native full-speed host.
