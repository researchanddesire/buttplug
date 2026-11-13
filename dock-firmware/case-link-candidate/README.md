# Case link decoder/cache candidate

This is an isolated C11 module for the STM32L071 case controller. It implements
the six 20-byte values in
`hardware/pcb/evt1/case-telemetry-study/protocol-v1.json`, frozen at SHA256
`4678caf5112116f93fc80a013288c87fad0e0572ccb57d29b35e8bd2dbe971a5`.
It has no transport, registers, flash writes, RNG, charger/UV outputs or changes
to the existing dock application. It decodes observations; it creates no
thermal-readiness, Done, SOC or charge-completion state.

`case_link_decode(kind, bytes, length, &frame)` accepts characteristic suffixes
1 through 6. Reads are bytewise little-endian, including unaligned charge
fields. Wrong length/version/reserved bits reject the entire value. A malformed
numeric field clears only that field's validity and returns `CL_PARTIAL` with
`field_faults`; prior valid values retain their original acquisition time.
Conflicting current/TS valid and saturated/input-fault bits also invalidate
that field. Temperature and raw ratio validity are independent. Zero ticks,
zero sequences and zero correlation IDs are values, not missing sentinels.

Initialize one statically allocated `case_link` with a caller-selected nonce
and complete `cl_policy`. The host structure is 6280 bytes. The policy contains
freshness windows, maximum conversion/gap/anchor/round-trip spans, sequence
advance limit, combined timer-resolution error and a positive combined clock
drift bound. These are explicit integration assumptions. The tests' 1000 ppm
and 2 ms values are examples, not measured MSI/ESP clock bounds. Qualification
must select real bounds before the reported age intervals are relied on.
Freshness windows are not temperature or charge thresholds.

Use `case_link_connect(now64)` to get a connection epoch. Capture that epoch in
transport callbacks and pass it to `case_link_feed`; old queued callbacks are
rejected before they can affect the new clock/cache. Feed complete values with
a monotonically increasing case service/receive timestamp. Delayed processing
can widen the measured round trip; it must not substitute an earlier unproven
receive time. `cl_tick32_update` extends a polled case SysTick across 32-bit
wrap, requiring every delta to be less than half-range. Reset/reinitialize on
an unknown local timebase; do not silently treat a reboot as tick wrap.
The state has one main-task owner. Interrupt/transport callbacks queue complete
values with their epoch; these functions provide no locking or ISR contract.

The handshake is a snapshot request/result followed by a time-anchor request/
result. `case_link_command` creates one pending request and a 20-byte packet;
ATT write success does not complete it. The result must match request ID,
exact caller session nonce echo and known plug boot. IDs are never reused
under the same nonce, including across disconnects. At exhaustion, supply a
fresh logical nonce through `case_link_new_session`; the caller must provide
qualified nonreuse across resets too. Boot IDs/nonces are correlation values,
not authentication. Link security remains a transport/server requirement.
Opcode 3 replays the latest real automatic source-loss record; it cannot
manufacture a removal event. Opcode 4 requests a retained event sequence.

`case_link_poll` applies the explicit maximum round-trip policy. A timed-out
non-anchor operation can be retried with `case_link_retry`: the exact original
ID/nonce/payload is retained, so a baseline capture is not recreated under a
new ID. An anchor retry needs a fresh command/ID; a cached idempotent result
does not establish a new clock observation. Starting a different command
explicitly discards the prior retry context. Disconnect, session or plug boot
change clears pending state. Unmatched/overdue results never establish an
anchor. Check `resync_needed` after receives/polls; an accepted frame may be
cached while a new snapshot/anchor is still required.

For T0 case send, T1 plug receive, T2 plug completion and T3 case receive, the
anchor retains the complete plug-minus-case offset interval
`[T2−T3, T1−T0]`, expanded by caller timer-resolution error. It rejects reversed
or ambiguous intervals and overdue results. Mapping acquisition ticks adds a
conservative drift allowance as time passes. Charge field ages include the
full extra 250 ms acquisition-bundle window, including digital observations.
A delayed notification therefore cannot make an old reading fresh. An age
interval straddling the freshness boundary is unknown; its midpoint is not
used to claim freshness. Ticks are monotonic time, not UTC.

The fixed rings hold 64 thermal attempts, 8 charge observations and 16 source
events. Invalid attempts are retained. Duplicate data does not restamp it;
older completed data can fill history without replacing the newest value.
An unfinished thermal attempt can receive its one completion update. Source
event stages can add information monotonically; reordered older stages are
ignored. Sequence/tick half-range ambiguity, inconsistent ordering, excessive
gaps or boot changes invalidate timing and request resynchronization. Timing
generations prevent a new anchor from reinterpreting pre-gap mapped records.
The gap-triggering value returns `CL_RESYNC`; the fresh snapshot republishes
current data. Completion updates receive the same chronology checks as new
records, so an older attempt cannot finish after a newer attempt and replace
its current value. Missing
records cannot silently become a continuous history. Cache eviction means an
unavailable match, not a synthetic baseline.

`case_link_temperature`, `case_link_ratio` and each `case_link_charge` field
return independent fresh/aged/unknown/invalid status, value availability and
age bounds. A failed latest attempt remains invalid even if an older value is
retained for diagnosis. `case_link_event` keeps first post-loss attempt and
first valid post-loss temperature separate. It links the two event records by
boot/event sequence/loss identity, then matches each to thermal history by
boot and exact start/completion pair. Matching also requires the producer's
follows-loss flag and stable absent source at start/end with no source-change
flag. Equal millisecond timestamps alone certify nothing; equality is allowed
when the producer supplies the causal flag. Missing or
ambiguous matches remain false. Interruption/overflow remain explicit; a
PGOOD-loss record is not proof of physical removal or an accepted baseline.

Run `python3 validate.py` here. It checks the frozen schema, independent Python
struct golden vectors, host behavior with UBSan, and a freestanding Cortex-M0+
compile/link against 128 KiB Flash/20 KiB RAM with 2 KiB reserved stack. The
compile-only ELF deliberately has no hardware startup/vector table or BIN/HEX.
`validation.json` binds sources/artifacts and proves existing dock runtime
sources stayed unchanged. A separate UBSan host roundtrip links the actual C3
pure sender/history with this decoder, checks all six golden values and
exercises the command/anchor and event-replay flow. This proves software wire
compatibility for those source hashes. Runtime scheduling, radio driver/queues,
hardware interoperability, pairing/security, real nonce generation, clocks and powered
behavior remain integration/bench gates.
