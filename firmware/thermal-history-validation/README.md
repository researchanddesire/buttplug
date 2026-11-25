# Thermal-history candidate validation

Run `python3 firmware/thermal-history-validation/validate.py` from the product
repository. It snapshots the current firmware/test inputs, runs the host suites
with UBSan, builds both profiles in `/private/tmp/compass-thermal-build`, verifies
that inputs stayed unchanged, and checks the linked application USB detach ISR
against the preserved ESP-IDF5.5.3 audit. It does not flash a board. Generated
logs and `validation.json` describe this exact digital candidate; older USB
and firmware reports remain preserved historical snapshots.

`thermal-status` reports the latest candidate over qualified docked USB. The
64-attempt/16-event RAM rings retain the actual measurement timestamps, including
failed attempts. Source-loss records distinguish the first new attempt from the
first valid post-loss temperature. Reconnection before a valid sample interrupts
that baseline. `reconnected_before_attempt` separately records whether no new
attempt had completed before reconnection. Raw PGOOD edges can coalesce between
polls, so the ISR count is exposed without inventing individual event times.

The current USB command returns the latest summary, not the complete rings.
Case BLE transfer, charge/UV state, time anchoring, durable storage and Ready
criteria remain separate work. Boot/deep sleep discards the history. No value
here proves physical removal, charge completion, cleaning or wear.

The32-bit boot tag is sampled after NimBLE enables the RF entropy source; the
bound EVT1 configuration disables modem sleep/power management. It is a
probabilistic tag, not guaranteed globally unique. Receivers must invalidate
their mapping after connection/reset gaps and establish a fresh time anchor.
See [the pinned ESP-IDF RNG contract](https://docs.espressif.com/projects/esp-idf/en/v5.5.3/esp32c3/api-reference/system/random.html).
