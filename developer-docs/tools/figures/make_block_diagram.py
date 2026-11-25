"""Device electronics block diagram (hand-placed SVG, same style as the dock diagram).
Run: python3 make_block_diagram.py  -> docs/assets/device/device-blocks.svg
Connections follow the compass-one-board schematic netlist."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'docs', 'assets', 'device', 'device-blocks.svg')
W, H = 1200, 690
P, D, C = '#bd671c', '#2563a6', '#377964'
boxes = [  # x, y, w, h, title, sub
    (30, 80, 200, 226, 'Dock contacts', ''),
    (290, 80, 180, 86, 'F1 + D1', 'PTC fuse, diode'),
    (530, 80, 200, 86, 'U1 BQ24074', 'charger, power path'),
    (800, 80, 200, 86, 'Battery (J2)', '1S LiPo, PCM, NTC'),
    (290, 220, 180, 86, 'U75 USBLC6', 'USB ESD clamp'),
    (530, 220, 200, 86, 'Charge permit', 'U9 + JP1 + Q1'),
    (800, 220, 200, 86, 'U2 TPS63070', '3.3 V logic rail'),
    (30, 360, 200, 86, 'SW1 / SW2', 'power, mode'),
    (290, 360, 180, 86, 'U71 TPS3422', 'hold 7.5 s: reset'),
    (530, 360, 200, 86, 'U6 ESP32-C3', 'MCU, BLE, native USB'),
    (800, 360, 200, 86, 'U3 TPS63070', '3.7 V motor rail'),
    (30, 500, 200, 86, 'Tip NTC (J5)', 'in the nose cap'),
    (290, 500, 180, 86, 'U7 ADS1115', 'ADC: tip + pack NTC'),
    (530, 500, 200, 86, 'U81 LSM303AGR', 'accel + compass'),
    (800, 500, 200, 86, 'U4 + U5', 'interlock, DRV8212'),
    (1050, 500, 120, 86, 'Motor', 'J3'),
]
s = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d" role="img" aria-labelledby="t d">' % (W, H, W, H),
     '<title id="t">Compass device electronics</title>',
     '<desc id="d">Dock power charges the battery through the BQ24074 power path; two buck-boost converters make the 3.3 V logic rail and the 3.7 V motor rail; the ESP32-C3 talks USB through the dock contacts and reads the ADC and compass over I2C; a logic gate only lets the motor run when armed and off the dock.</desc>',
     '<defs>' + ''.join('<marker id="m%s" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="%s"/></marker>' % (k, v) for k, v in (('p', P), ('d', D), ('c', C))) + '</defs>',
     '<rect width="%d" height="%d" rx="16" fill="#f6f8fb"/>' % (W, H),
     '<g font-family="Arial,Helvetica,sans-serif" fill="#213246">',
     '<text x="30" y="48" font-size="25" font-weight="700">Device electronics on the 52 × 20 mm board</text>']
for x, y, w, h, t, sub in boxes:
    s.append('<rect x="%d" y="%d" width="%d" height="%d" rx="12" fill="#fff" stroke="#c6d2de" stroke-width="2"/>' % (x, y, w, h))
    s.append('<text x="%d" y="%d" text-anchor="middle" font-size="19" font-weight="700">%s</text>' % (x + w / 2, y + 37, t))
    if sub:
        s.append('<text x="%d" y="%d" text-anchor="middle" font-size="15.5">%s</text>' % (x + w / 2, y + 62, sub))
s.append('<text x="130" y="145" text-anchor="middle" font-size="15.5">5 V, GND</text>')
s.append('<text x="130" y="268" text-anchor="middle" font-size="15.5">D−, D+</text>')
s.append('<text x="130" y="190" text-anchor="middle" font-size="13" fill="#5b6b7b">four Mill-Max targets</text>')
def arrow(d, col, mk, both=False, w=3.2):
    s.append('<path d="%s" fill="none" stroke="%s" stroke-width="%.1f" marker-end="url(#%s)"%s/>' % (d, col, w, mk, (' marker-start="url(#%s)"' % mk) if both else ''))
def label(x, y, t, col, anchor='middle'):
    s.append('<text x="%d" y="%d" font-size="15" fill="%s" text-anchor="%s">%s</text>' % (x, y, col, anchor, t))
# power
arrow('M230 123H284', P, 'mp'); arrow('M470 123H524', P, 'mp')
arrow('M736 108H794', P, 'mp', both=True); label(765, 100, 'BAT', P)
arrow('M630 80V60H1040V403H1006', P, 'mp'); arrow('M1040 263H1006', P, 'mp'); label(1048, 56, 'SYS', P, 'start')
arrow('M800 285H765V395H736', P, 'mp'); label(770, 340, '3.3 V', P, 'start')
arrow('M900 446V494', P, 'mp'); label(910, 476, '3.7 V', P, 'start')
arrow('M1000 543H1044', P, 'mp')
# data
arrow('M230 263H284', D, 'md')
arrow('M470 263H500V378H524', D, 'md'); label(492, 340, 'USB', D, 'end')
arrow('M630 446V494', D, 'md'); arrow('M630 470H380V494', D, 'md'); label(640, 476, 'I²C', D, 'start')
arrow('M230 543H284', D, 'md')
# control
arrow('M630 220V172', C, 'mc'); label(640, 200, 'CE', C, 'start')
arrow('M230 403H284', C, 'mc'); arrow('M470 418H524', C, 'mc'); label(497, 440, 'EN', C)
arrow('M736 430H770V520H794', C, 'mc'); label(752, 470, 'PWM, arm', C, 'end')
arrow('M690 80V66H1150V543H1176', C, 'mc', w=0) if False else None
s.append('<text x="30" y="628" font-size="15.5">Orange: power. Blue: data. Green: control. U4 passes the motor command only when the firmware has armed the motor and the device is off the dock.</text>')
s.append('<text x="30" y="654" font-size="15.5">The pack NTC feeds the charger TS pin (hardware charge-temperature cutoff) and ADC input AIN2. JP1 is open on the bench build.</text>')
s.append('</g></svg>')
open(OUT, 'w').write('\n'.join(s))
print(OUT)
