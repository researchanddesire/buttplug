# EVT base and lid UV driver candidates

base/dock-uv-base.kicad_sch and lid/dock-uv-lid.kicad_sch are identical after
reference and BASE/LID renaming. Each has TPS61165DBVR, two series Vishay
VLMU35CB20-275-120 LEDs,3.65Ω1%100ppm/K CRCW08053R65FKEA sense resistor
and DMN62D2U-7 cathode disconnect. Nominal current54.795mA; feedback196–204mV
and additive1% initial plus1% TCR over100K give52.646–57.031mA modeled bounds.
Long-term resistance drift requires separate qualification.

Selected DBV driver pins:1VIN,2CTRL,3SW,4GND,5COMP,6FB. CTRL is static,
without EasyScale/PWM. The220nF compensation capacitor is populated.
Bourns SRP4020TA-100M is10µH20%,243mΩ max DCR,2.3A saturation reference.
PMEG6010CEH is60V1A,1K at VOUT and2A at SW; match its cathode bar.
Measure switch overshoot and inductor/diode heating. DC ratings alone do
not qualify the switching node.

Input/output capacitors are TDK C3225X7R1H475K250AB4.7µF50VX7R1210,
**2.8mm maximum body height**. Require>=1µF effective over voltage,
temperature and aging, including39V output OVP. TI recommends1–10µF output.
Nominal capacitance alone is not acceptance. Stability and bias remain tests.

Vishay's primary drawing defines two solder lands with outer shoulders,
**no separate ground thermal pad**. Custom pad1 is marked cathode;2anode.
Match the actual cathode mark before assembly. Both lands carry current/heat.
Published thermal measurements use20×20×1.7mm Al MCPCB; ordinary FR4 does
not inherit that thermal result. Design/test the actual metal heat path.

Local FET gate has1k series and100k pull-down; source FB/RSET, drain LED
cathode. CTRL low interrupts the string independently of both upstream cuts.
The driver takes2.5ms to enter shutdown and retains an inductor/diode DC
path; it is not an output isolator. Measure optical tail for each fault path.

100k bleeder and1M/68k divider discharge output charge. Voltage can persist
after light stops; firmware makes no safe-voltage claim. FB and divider
monitors each use10k/100nF filters before GH8; divider about2.48V at39V.
Controller owns ADS1115 without duplicate filters on these four channels.

Remote NTCLE413E2103F524A is10k1%,B25/85=3435K1%; use manufacturer Table3
curve. Controller owns10k0.1%3V3_ANALOG pull-up and1k/100nF ADC filter.
Independent remote Sensata67L045 opens45±5°C. Its10mA@5V reference does
not guarantee4.5–5.25V use; dock-safety/DESIGN.md defines acceptance.

GH8:1UV_5V_SW,2GND,3UV_CTRL,4side_FB,5side_VOUT_DIV,6NTC_side,
7side_THERM_SEND,8LOOP_A_RAW(base)/LOOP_B_RAW(lid); reinforcement GND.
Keep boosted nodes local, SW/diode/cap loops short and sense returns Kelvin.
Remote NTC/thermostat wires use actual solder lands and need restraint.

The current power budget uses4.10V and70% assumed efficiency. Exact input
current, limiter margin and complete path allocation are generated in
../dock-safety/power-budget.json, including bleeders/dividers and4.6mA
driver-Iq allocation. The50mΩ common PCB allowance is applied at full source
current; switch and per-driver branch drops use their UV currents. Efficiency,
the typical-Iq allocation, LED voltage, FET drop, path resistance
and current remain measurements. Native XML/ERC are digital circuit
evidence only; layout, physical fit, optical leakage/dose/efficacy and aging
remain open. No sterilization claim or full-product order release follows.

Primary references: [TI driver](https://www.ti.com/lit/ds/symlink/tps61165.pdf),
[Vishay LED](https://www.vishay.com/docs/80232/vlmu35cb2x-275-120.pdf),
[resistor selection/encoding](https://www.vishay.com/docs/20035/dcrcwe3.pdf),
[Bourns inductor](https://www.bourns.com/docs/Product-Datasheets/SRP4020TA.pdf),
[Nexperia diode](https://assets.nexperia.com/documents/data-sheet/PMEG6010CEH.pdf),
[TDK capacitor](https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no=C3225X7R1H475K250AB),
[Vishay NTC](https://www.vishay.com/docs/29078/ntcle413.pdf).
