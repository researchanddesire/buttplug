# EVT dock hardware interlock candidate

dock-safety.kicad_sch is editable native KiCad source. Selected parts, actual
package footprints, exported XML and native10.0.8 ERC results are bound by
native-checks.json. Circuit validation does not establish PCB layout, powered
operation or optical qualification. The separate dock-system project integrates
source/controller/UV leaves.

Each independent loop is HOST5 → U602 qualified-source switch → Omron D2F-01L
normally-open lid contact → respective remote Sensata67L045 normally-closed
thermostat →430Ω return to GND. Lid actuators must open independently before
an accessible light path exists. Broken wiring holds its loop low.
SN74LVC2G17 Schmitt inputs translate the5V loops to3V3.

The Sensata primary reference is **0.010A at5VDC**,100000cycles; this does not
guarantee4.5–5.25V use. The430Ω loads provide10.35–12.34mA reference loading.
Actual contact resistance, leakage, switching and life across that range
remain acceptance gates. No dry-circuit rating is inferred. U602 disables both
loops unless SOURCE_OK is hardware qualified; their24.67mA maximum is outside
the legacy10mA UI allocation.

U612 forms RAW_SAFE from both loops, SOURCE_OK and SAFE_RESETn. U616 adds
180–420ms recovery delay. CLEARn additionally requires MCU_STOPn. A fault
asynchronously clears both U609 latches. MAX6816 filters both button edges
20–80ms; recovery delay exceeds that maximum. A subsequent physical release
clocks RELEASE_SEEN, then a later physical press captures RELEASE_SEEN AND
MCU_ARM into UV_RUN. Local U614 clock buffers have Schmitt inputs. The source
U114 output drives U614 **input pin3**, not another output. Firmware cannot
generate either physical clock. Recovery cannot recreate a clock.
MCU_ARM/MCU_STOPn/WDI default low with external pulls.

U606 TPS3431SDRBR is always enabled in170–230ms watchdog mode. WDO and ENOUT
share SAFE_RESETn with U607's3.07V supervisor. R6061k separates MCU_NRSTn and
its controller100nF capacitor from the supervisor output. MCU falling
heartbeat edges follow completed healthy main loops. Physically observe
startup/reset levels, finite supervisor response and partially powered states.

U610/U611 TPS22992RXPR are cascaded independent input cuts. GateA requires
loopA and SOURCE_OK; gateB requires UV_RUN and loopB. Each has100k default
pull-down,1nF CT and330Ω output discharge. Both VBIAS pins use HOST5.
Final PG gates UV_CTRL with UV_RUN; PG does not gate the UV_RUN latch and
cannot deadlock startup. UV modules also interrupt their LED cathodes on
UV_CTRL low. These provisions are not measured shutdown latency or
single-fault certification.

J621/J622 are JST SM08B-GHS-TB(LF)(SN), straight1:1 to J401/J501:

|Pin|Signal|
|---|---|
|1|UV_5V_SW after both input cuts|
|2|GND|
|3|UV_CTRL|
|4|BASE_FB / LID_FB|
|5|BASE_VOUT_DIV / LID_VOUT_DIV|
|6|NTC_BASE / NTC_LID|
|7|BASE_THERM_SEND / LID_THERM_SEND|
|8|LOOP_A_RAW / LOOP_B_RAW|
|MP|GND reinforcement|

Mating housing GHR-08V-S, SSHL-002T-P0.2 contacts;26AWG power within the
manufacturer26–30AWG range. No boosted high-voltage node crosses the hinge.
J601/J602 connect remote lid switches with GH2. Actual UV-board solder lands
terminate remote sensors; provide wire restraint. Controller owns NTC pulls.

power-budget.json supersedes older architecture allocations in dock-ui
without changing its stable source schematic. Qualified worst allocation is
1484.444mA on1.5A advertised sources, including both contact loops. Legacy
allocation is70mA device plus10mA UI; UV and loops disabled. The10mA UI total
requires actual measurement; TUSB maximum current and LCD overtemperature
current are not published guarantees.

For UV, common switch resistance is0.165Ω; common PCB supply/return copper
must be<=0.050Ω and each complete supply/return branch<=0.290Ω. Conservatively
apply the entire common PCB allowance at the full1.315280A source current,
including the device, UI and both contact loops. This covers shared HOST/GND
copper from USB input pads to UV branch lands; semiconductor resistance and
each branch remain separate. Apply switch resistance at650.614905mA UV total
and branch resistance at325.307453mA per driver. That branch
includes all four mated GH contacts, crimps, wires, local copper, temperature
and aging. Allocate0.200Ω to four mated contacts,0.010Ω to four crimp joints,
0.020Ω to hot PCB supply/return copper including vias, and0.060Ω to wire.
Use26AWG wire with incoming resistance<=0.135Ω/m at20°C, conductor<=80°C,
and each power/return leg<=175mm. The350mm total loop models0.0584Ω hot;
actual wires/crimps still require qualification. The normal-current model
uses a4.10V driver floor and70% efficiency. Required UV current is650.614905mA,
leaving31.929771mA below the minimum limiter threshold. At4.5V dock input the
conservative DC path yields4.232545V at each driver,132.545mV above that floor.
Shared PCB, switch and branch drops are65.764mV,107.351mV and94.339mV respectively.
The4.10V floor is within [TPS61165 RevE's published3–18V input range](https://www.ti.com/lit/ds/symlink/tps61165.pdf),
and remains a measured acceptance condition. The70% efficiency and the
two2.3mA typical-Iq allocation require measurement over actual voltage, load
and temperature; they are not guaranteed minima/maxima. The limiter-bound
efficiency break-even at4.10V is66.703%, not a release target. DC headroom is
not measured ripple or startup margin. UV_VBUS_MON is digital and cannot
measure this floor. Check both drivers during validated normal transients,
at minimum input and maximum regulated load. Do not credit the floor during
current-limit faults. The1484.444mA fault-limit source allocation is unchanged.
Effective capacitors, switch ringing, source changes, USB suspend/inrush,
watchdog faults, cutoff timing, optical tail/leakage, temperature, dose,
efficacy and aging remain required. No sterilization/product release claim.

Primary references: [TI watchdog](https://www.ti.com/lit/ds/symlink/tps3431.pdf),
[supervisor](https://www.ti.com/lit/ds/symlink/tps3808.pdf),
[debouncer](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX6816-MAX6818.pdf),
[load switches](https://www.ti.com/lit/ds/symlink/tps22992.pdf),
[Omron contacts](https://omronfs.omron.com/en_US/ecb/products/pdf/en-d2f.pdf),
[Sensata thermostat](https://www.sensata.com/sites/default/files/a/sensata-6700-series-subminiature-bimetal-disc-thermostats-datasheet.pdf),
[JST GH](https://www.jst-mfg.com/product/pdf/eng/eGH.pdf).
