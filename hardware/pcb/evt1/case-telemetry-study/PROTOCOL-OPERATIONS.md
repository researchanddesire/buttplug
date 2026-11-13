# BLE v1 operation notes

The wire layouts are frozen in `protocol-v1.json`, SHA256
`4678caf5112116f93fc80a013288c87fad0e0572ccb57d29b35e8bd2dbe971a5`.
These notes specify acquisition, replay and causality without changing those
six 20-byte layouts. They do not establish thermal Ready limits or confirmed
charge completion.

The plug owns sensor acquisition and its 64-attempt history. The case owns its
clock anchor and cached views. A transport callback identifies the connection
epoch so queued notifications from an older connection cannot attach to a new
one. Original acquisition ticks survive notification delays and replay.

## Commands and replay

1. `request_snapshot` requests the latest actual thermal attempt and charge
   observations, plus the latest retained automatic loss event when available.
   Missing hardware or failed observations remain explicitly invalid. It does
   not create new measurements by relabeling old data as fresh.
2. `time_anchor_request` returns the plug's actual command receipt and result
   completion ticks. The case retains the full offset interval; neither side
   claims UTC or a fixed BLE latency. Receipt of an ATT write response alone
   completes no application operation.
3. `request_baseline_capture` replays the latest real automatic loss record.
   It does not manufacture a removal, a post-loss sample, or a new physiological
   baseline on request. If none is retained, report `history_unavailable`.
4. `read_source_event_by_sequence` replays the retained automatic event and its
   copied thermal attempts: last fresh docked attempt, first post-loss attempt
   including an invalid result, and first valid post-loss temperature when one
   exists. Match by boot/event/loss identity and original start/completion ticks.
   If required records have expired, report that gap instead of substituting
   the current temperature.

Application result `accepted` confirms that the operation was processed or its
records queued; notifications can still be lost or reordered. The case checks
that the required records actually arrive and match. Repeated records are
idempotent and do not refresh data age. Retained historical samples must not
replace the live sample merely because their notifications arrived later.

The same case-session nonce and request ID identify retries of one operation.
The plug must preserve bounded idempotency history. Repeating an evicted old
request cannot create a replacement baseline; it returns a history gap. The
case never reuses a request ID within a session and changes its qualified
session nonce before exhaustion. A previous retained result cannot satisfy a
new request without the matching echoed session nonce.

## Source-loss causality

PGOOD loss is an observed loss of valid charger input, not confirmation that the
plug was physically removed. The source-event record preserves that distinction.

Before invoking an NTC acquisition, the main task captures its current internal
loss-event sequence and detach generation. For a first post-loss attempt, the
captured loss sequence must match the event already observed before acquisition.
The producer also checks that source absence was stable at acquisition start and
end, with the same detach generation; a brief intervening bounce is not hidden.

This causal proof permits equal millisecond loss/start ticks when the loss was
already observed before the new acquisition began. Timestamp equality by itself
does not establish that order. Cached data and an acquisition straddling the
loss cannot populate a new first-after-loss record. The producer's
`sample_follows_observed_source_loss` flag certifies this acquisition relationship.

The first attempt and first valid temperature are separate records. An invalid
first attempt stays invalid; a later valid attempt does not overwrite it.
Reconnection before any new attempt and reconnection before the first valid
temperature remain distinguishable interruptions. Missing, contradictory or
ambiguous cross-stream records cannot become a complete baseline.

## Acquisition and validity

One plug I2C owner serializes the original pulsed tip conversion with any future
charge ADC measurements. The new charge circuit is still a candidate: until its
hardware and estimator are integrated, current/TS/CE fields are invalid, rather
than simulated or inferred from CHG high. Valid charge fields must belong to an
actual acquisition bundle no longer than 250 ms. CHG's approximately 2 Hz fault
history is sampled and retained locally at 25 ms intervals or faster.

The optional thermistor ratio has its own validity flag. A missing ratio does
not invalidate an otherwise valid temperature; a ratio alone does not establish
a calibrated temperature. ADC/sensor faults and source changes remain visible
to the eventual state machine. A fresh cached number alone does not mean Ready.

Do not interpret an old attempt completing after a newer attempt as a new
latest sample without checking sequence/time consistency. After an excessive
gap or half-range ambiguity, earlier tick mappings remain untrusted until a new
snapshot and anchor establish a new timing generation. Old raw history may be
retained for diagnostics without acquiring fresh validity from the new anchor.

PC native USB and physical Power/Mode ROM recovery remain independent of this
link. The present radio power candidate operates only with a qualified case
source; it does not add a second USB controller to D+/D-.
