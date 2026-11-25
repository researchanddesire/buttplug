# Plug templates and Rad integration

The main Rad surface is **Plug templates** at `/app/plug`. Compass is a secondary
tab. The implementation lives in `researchanddesire/rad-app`. This page describes
the candidate integration and its activation requirements; a local preview is
not evidence of production behavior.

The full-dashboard walkthrough is `/app/plug/preview`, guarded by the server
flag `PLUG_INTEGRATION_PREVIEW_ENABLED=true` and the normal dashboard sign-in.
It reuses the existing sidebar, headings, settings layout and Lockbox session
summary. The flow is session overview → plug requirement → template editor;
the wearer view hides the editor. Its sample personas never change the signed-in
account. Draft edits become assigned rules only after saving in the preview.
The wear simulator changes browser memory and the sample countdown only. It
does not use a device, save an assignment or mutate a real Lockbox timer.
Verify the target app revision and deployment separately when reviewing this flow.
The requirement card uses an editable plug icon based on the current turned
body, narrow neck and wide rounded flange.

## Inputs, outputs and responses

Templates choose inputs and outputs independently. The first catalog contains
movement, tilt, tip temperature, confirmed wear time, Mode-button events and
direction error. Outputs include vibration strength, pulse interval, a pulse,
next pattern, pause and an approved Lockbox contribution.

Numeric inputs can follow a configured range, including a reversed response.
Thresholds and button presses produce edge-triggered actions. One input can
drive several outputs; rule order resolves numeric-output conflicts. The editor
has a simulated preview that cannot command hardware or change a lock.

`PlugTemplate` JSON is schema-validated before saving and on reads. The generated
Rad migration provides owner-scoped RLS storage. Saving does not apply a template
to the device. Full template transfer/application and persistent runtime settings
remain to integrate; `firmware/main/plug_runtime.c` currently supplies tested
scaling, clamp, threshold and wear-accounting primitives, not a complete template
executor.

## Keyholder-assigned requirements

A keyholder can require plug use as a condition of a wearer's Lockbox release.
The main wearer view must show the keyholder's instructions, the assigned rule
and confirmed progress. The wearer cannot change that assignment's target,
mappings or credit rate. Personal template saves never edit an assigned rule.
Pause/stop controls do not remove the requirement or bypass existing release
and break rules.

Required wear and time credit are separate criteria: earning a reduction does
not satisfy a wear target by itself, and reaching the target does not unlock a
box. Each assignment needs a session-owned, versioned rule snapshot and a
verified progress origin. Server authorization must check the current Lockbox
session's keyholders, rather than trusting selected-account access or a browser
role. Existing timer visibility and release permissions still apply.

Rad's `AssignedByKeyholder` story implements the read-only wearer presentation.
The production assignment store, session-authorized read/write actions,
cross-session progress aggregation and release-condition enforcement remain
**unimplemented**. The story's wear and Lockbox progress are simulated.

## Countdown only while worn

The assignment can select `timerMode: "wear-only"` instead of normal countdown
plus bonus wear credit. Verified wear advances the timer at 1:1; removal,
unqualified/stale readings, lost connectivity or pausing wear stops its progress.
Bonus Lockbox-credit mappings are inactive in this mode, avoiding double credit.
Other sensory mappings remain configurable.

| Situation | Wear-only timer policy |
| --- | --- |
| Fresh, qualified wear while locked | Count verified wear duration |
| Removed, paused or unknown wear | Request the plug's own hold |
| Break requested but not confirmed | Keep evaluating wear; no break exemption yet |
| Confirmed allowed break, including waiting for physical relock | Exempt wear and follow the existing session/provider break countdown policy |
| Chaster, keyholder, acceptance or another independent freeze | Preserve that hold, even during wear or a break |
| Physical relock confirmed | Recheck current wear before resuming |

Break permissions, cooldowns, hygiene deadlines and relock confirmation remain
with the existing Lockbox/Chaster lifecycle. Break deadlines use wall time even
when the main countdown is frozen. Reaching a wear target does not unlock a box.

`wearTimer.ts` supplies pure policy, bounded interval accounting and proposed
freeze intents. These are not a live mutation service. Its Chaster planner is
observe-only without a qualified adapter, and cannot propose releasing an
external, approval, ambiguous or shared hold. The existing approval coordinator
is deliberately unchanged: it owns initial acceptance freezes, not repeated
wear/removal cycles. Chaster's lock-level freeze API has no atomic ownership
compare-and-set; checking history alone cannot eliminate the final request race.

Live activation still requires a server watchdog, verified device receipts,
an atomic receipt/remaining-time ledger, session-authorized rule versions and a
reason-scoped hold broker coordinated with the existing ownership lease. It must
reconcile ambiguous provider outcomes, preserve manual overrides, respect Chaster
timer visibility/date/release rules and distinguish a requested hold from a
provider-confirmed freeze. No browser clock may claim the upstream timer stopped.
The preview simulates removal/offline readings, independent Chaster freezes and
the allowed-break/relock sequence; it sends no Chaster actions.

[Chaster freeze actions](https://docs.chaster.app/api/extensions-api/create-your-extension/lock-actions/)
and [lock-status semantics](https://docs.chaster.app/locks/status/) are the provider
reference. No live Chaster compatibility or physical wear result is claimed.

## Wear time and Lockbox credit

Elapsed session time, confirmed wear time and server-applied reduction are
separate counters. An example rule is 15 confirmed wear minutes → 5 lock minutes,
with a configured session cap, in addition to the normal countdown. This is a
configurable example, not a required relationship or wear-duration recommendation.

The candidate ledger calculation uses cumulative counters, credits only the
increment, rejects conflicting replays and different device/session/boot IDs,
and excludes partial intervals during ineligible periods. It caps removal by
remaining lock time. `createWearCreditBoundary()` refuses all timer mutations
without an independent device verifier and an atomic transaction implementation.
Those bindings, keyholder/session approval storage and Chaster outbox delivery
are **not implemented or activated**. The current dashboard does not shorten
an actual Lockbox session.

The device has no qualified wear classifier. Current firmware explicitly reports
`detector_qualified:false` and zero confirmed wear; temperature or motion alone
does not become proof of wear. Device credential provisioning, authenticated
receipt delivery, classifier qualification and durable/offline accounting remain
required before enabling credit.

## EVT Bluetooth contract

The existing private service remains `931496e0-2d94-4f8c-9546-52164c52f000`.
Reads/writes require authenticated encryption and the prototype's USB-console
pairing passkey. This is distinct from the shared Arduino RAD BLE v1 service.

| Suffix | Contract |
| --- | --- |
| `f001` | Existing engineering JSON status |
| `f002` | Command write with response; delivery is not an execution acknowledgment |
| `f003` | Bounded `compass-v1` snapshot; verify the app bearing against the current flange-arrow transform |
| `f004` | `plug-v1` snapshot: boot/session IDs, active/state, elapsed and confirmed milliseconds, classifier qualification |

Two-byte commands: `00 00` stops/disarms the motor, `01 NN` requests legacy
bench duty, `05 01` starts/resumes wear tracking, `06 01` pauses it and disarms,
and `07 01` ends it and disarms. Tracking is independent of the motor connection
lease. Current counters are RAM-only and reset on reboot.

Direction start is six bytes: `03 01 targetLo targetHi tolerance strength`.
Target is an integer degree 0–359, tolerance 5–45 and strength 1–25. `04` is the
same settings packet for renewal only; it must never start a stopped/expired
session. Direction mode uses fresh samples, bounded pulses and a candidate
one-second magnetic settling interval, under the existing local-arm, fault,
dock, lease and PWM limits. The default motor build remains locked off.

Run `sh firmware/tests/run_host_tests.sh` and build the matching PlatformIO
profile (`evt1-one-board` for the current compact PCB).
Rad's focused tests cover template editing, source/output compatibility,
response inversion, triggers, receipt accounting, Bluetooth and lifecycle rules.
No physical wear, radio, motor, sensor-classifier or Lockbox reward result follows.
