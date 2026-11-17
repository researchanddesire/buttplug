# Compass EVT1 Hall lid interlock worksheet

Record results from the assembled EVT dock and copy them to the Compass
review log with the actual board, enclosure and firmware revisions. The
[product Hall stations](../evt1-wired/README.md#hall-board-fit) define the
mounts. The [Main receiver pin contract](../../../pcb/evt1/dock-safety/wired-hall-head/README.md#main-integration-pin-contract)
defines the pending electrical integration. Keep both UV modules physically
disconnected during field and electrical checks.

| Record | Value |
| --- | --- |
| Reference repo commit | `135199ace3d0852f9f2bf7daba9d414b573e2304` |
| Reference native | `evt1-wired/DockAssembly.FCStd` `c8748a4365db`, Hall package centers X ±50.5 / Y 37.55, PCB top Z34.85 mm |
| Assembled unit, Main and UV revisions | |
| Hall revision, lot/grade, sense direction, target lot/polarity, installed shims | |
| Enclosure revision, material/finish, hinge/latch condition, plug/carrier state | |
| Firmware profile and binary hash; J101 source mode, voltage and temperature | |
| Calibrated field, gap and optical instruments; calibration date and uncertainty | |

## Existing terminals and inert checks

For the current product circuit, use the fitted head's J1 pin 1 feed,
pin 2 signature and pin 3 dedicated return. Verify all three conductors at
each end before power. The Main's proposed J630 and J650 use the same
order. Record the receiver revision and its source allocations before
performing these checks. J601 and J602 belong to the dry-switch baseline.

| Function | A / base | B / lid | What to record |
| --- | --- | --- | --- |
| Hall head feed and receiver | Left J1 to proposed J630 | Right J1 to proposed J650 | Installed feed voltage/current, signature voltage, dedicated return current and receiver qualification before and after opening. Loss of any conductor must deassert that Hall channel. |
| Qualified thermostat send | J621.7 `BASE_THERM_SEND` | J622.7 `LID_THERM_SEND` | Thermal branch supply and cold contact current. Exercise thermostat opening independently of Hall opening. |
| Real normally closed thermostat and raw loop | J621.7–8, `LOOP_A_RAW` on pin 8, R614 | J622.7–8, `LOOP_B_RAW` on pin 8, R615 | Exercise each switch path separately with series thermostat, both cold and individually open. Record true cold loop current over input and temperature corners. |
| NTC and separate monitor | J621.6–2; TP606 | J622.6–2; TP607 | Test an open and a short on one NTC at a time; log monitor response separately from the thermostat path. |
| Main veto and UV outputs | `LOOP_A`, J621.1 `UV_5V_SW`, .3 `UV_CTRL`, .2 GND | `LOOP_B`, J622.1 `UV_5V_SW`, .3 `UV_CTRL`, .2 GND | Scope Hall qualifier, thermostat, channel permit, UV run, switched rail and control on the same timebase. Verify direct shutoff and fresh user rearm. |

| Inert trial | Expected observable | Capture / result |
| --- | --- | --- |
| Default Rp and power-up with lid open / closed | `LOOP_5V`, UV rail and UV control stay off. Verify the wired board's default-current allocation and no Hall backfeed. | |
| Source advertising 1.5 A, 4.50/5.25 V at J101 | Independently log each allowed output state and cold loop load. Apply the qualified-source and current limits for the actual build. | |
| Source downgrade/reset/brownout and connector interruptions | All UV output paths clear. Test Hall supply, ground and output open individually, including power-order and recovery behavior. Resolve any false-safe transient before emitting. | |
| A only releases; B only releases; one Hall input stuck closed then the other releases | Either channel permit must clear UV permission and the outputs. Verify the faulted state cannot restart with Center held. | |
| Thermostat A opened; thermostat B opened; actual heat trip/reset of each | Either path clears UV. For real thermostats record local sensor temperature, loop current and actual trip/reset against the baseline procedure. | |
| Short faults for the chosen interface | Log OUT-to-return, OUT-to-supply, cross-channel and branch-power cases. Identify any single fault holding both indications closed before optical energization. | |

The saved 40.2 kΩ Main R107 and 4.22 Ω R401/R501 apply to the wired
baseline. Qualify the actual Hall receiver population against the source
budget with both thermal branches, short faults and startup. The
[receiver calculation](../../../pcb/evt1/dock-safety/wired-hall-head/check_receiver_feed.py)
records which static budget applies to each proposed population.

## Field and motion screen

Use the two separated cutoff stations as coordinate references. A dedicated keyed lid target at each station gives a candidate to compare against using the two closely spaced front latch pairs. Make shared false-closure and fixed latch field part of the comparison. Label each sensing axis and measure the signed field component at the actual Hall die plane through assembly tolerance and motion. Keep the existing magnet, carrier and finished-material configurations identified.

| Row | Required corners | A field and output | B field and output |
| --- | --- | --- | --- |
| Qualified fully closed | Weak target, largest gap / lateral shift, worn and new hinge, cold / hot, plug in / out | | |
| Opening below earliest accessible emission | Strong target, smallest gap, both directions, hinge play / twist, expected opening speeds, cold / hot | | |
| Lid open across motion sweep | Stationary latch field, adjacent lid target, dock-carrier magnet field and mounted plug/keeper, empty dock | | |
| Incorrect assembly and magnetic environment | Individual targets omitted / reversed / shifted, relevant nearby accessories and misalignment including one raised front corner | | |

For each channel, the conservative closed-field lower bound must exceed its specified maximum operate threshold. The field upper bound by the last safe opening must be below its specified minimum release threshold. Include gauge error and threshold tolerances. Screen the sensor grade from measured margins. For example, DRV5021A2 has a 12.5 mT maximum operate threshold and a 3.6 mT minimum release threshold over its rated temperature range. Treat unqualified thresholds or common magnetic faults as open design findings.

## Contained optical qualification and finished-unit QA

Run in independently qualified light-tight UV-C containment with remote instruments and disconnect as in the existing bench procedure. Power the real finished assembly at worst qualified emitter output. Establish an exposure-based leakage limit, measurement distance, spectral response, detection floor/uncertainty and validated fixture before setting a production pass criterion. Use a calibrated UV-C radiometer for leakage and a fast optical witness for shutoff timing. Verify spectral response against the actual assembly. The selected Vishay VLMU35CB20-275-120 lists 270–280 nm peak wavelength at its datasheet test current. Record emission limit and timebase as revision-controlled test parameters.

| Row | Record |
| --- | --- |
| Finished closed seam scan | Meter background and source-on, peak reading and uncertainty by front grip/returns, entire perimeter, hinge and USB/apertures. Include representative material/finish, real wiring/plastic joints, seating and plug state. |
| Opening, channel A credited | Keep B in its closed indication within contained single-fault validation. Capture angle/front gap, A raw release, UV control and rail dropout, string current, emitter optical tail, and earliest externally accessible UV. |
| Opening, channel B credited | Repeat with A held in its closed indication. Confirm tail ends before the exposure limit can be exceeded, including during fast opening, slow drift, hinge play and one-corner opening. |
| Closure / startup at partial lid | Confirm no enable outside the measured safely closed window. Repeat after representative wear and environmental variation for qualification. |
| Each finished unit after qualification | Log serial, closed-leakage readings/judgment and independent interlock release checks in the qualified QA fixture. Recheck after assembly repair that changes the shell, baffle or lid sensing. |

## Source references

- [JST dock lid cutoff reference](cutoff-commissioning.md)
- [Front magnetic closure coupon](../front-closure-trial/README.md) and [carrier magnets](../recentered-carrier-trial/README.md)
- [Wired Main native terminal export](../../../pcb/evt1/case-telemetry-study/wired-main/native.xml) and [wired power contract](../../../pcb/evt1/case-telemetry-study/wired-main/circuit-contract.json)
- [Direct Main baseline cutoff hardware](../../../pcb/evt1/dock-safety/DESIGN.md)
- [Passive bench fixture](../../../design/evt1-bench-ordering/dock-logic-fixture.md) and [contained bring-up](../../../design/evt1-bench-ordering/pre-radio-bringup.md)
- [Seam geometry and ray trial](../uv-seam-trial/README.md)
- [Vishay UV-C emitter datasheet](https://www.vishay.com/docs/80232/vlmu35cb2x-275-120.pdf)
- [TI DRV5021 datasheet](https://www.ti.com/lit/ds/symlink/drv5021.pdf#page=4) and [IEC 62471-6 scope and optical safety framework](https://webstore.iec.ch/en/publication/59543)
