"""Compose the raw device renders (render_device.py) into labelled docs figures.

Run (system python): python3 make_device_figures.py
Reads .cache/figures/raw/<shot>.png(+.json); writes docs/assets/device/*.jpg and assembly-docs/assets/assembly/*.jpg.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import annotate

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.abspath(os.path.join(HERE, '..', '..'))
RAW = os.path.join(DOCS, '.cache', 'figures', 'raw')
DEV = os.path.join(DOCS, 'docs', 'assets', 'device')
ASM = os.path.join(os.path.dirname(DOCS), 'assembly-docs', 'assets', 'assembly')
os.makedirs(DEV, exist_ok=True); os.makedirs(ASM, exist_ok=True)

def L(anchor, text, side):
    return {'anchor': anchor, 'text': text, 'side': side}

def B(anchor, n, dx, dy):
    return {'anchor': anchor, 'text': str(n), 'side': (dx, dy), 'style': 'balloon'}

FIGS = {
    ('hero', DEV, 'device-hero.jpg'): [],
    ('part-body', DEV, 'part-body.jpg'): [],
    ('part-cap', DEV, 'part-cap.jpg'): [],
    ('part-tray', DEV, 'part-tray.jpg'): [],
    ('part-cover', DEV, 'part-cover.jpg'): [],
    ('part-plunger', DEV, 'part-plunger.jpg'): [],
    ('part-cradle', DEV, 'part-cradle.jpg'): [],
    ('part-skin', DEV, 'part-skin.jpg'): [],
    ('dockface', DEV, 'device-dockface.jpg'): [
        L('arrow', 'Calibration arrow (points up)', 'left'), L('sw1', 'Power button', 'left'), L('sw2', 'Mode button', 'left'),
        L('skin', 'Silicone skin', 'left'), L('window', 'Contact window', 'left'),
        L('ct1', 'GND', 'bottom'), L('ct2', 'D−', 'bottom'), L('ct3', 'D+', 'bottom'), L('ct4', '5 V', 'bottom'),
        L('icon', 'R+D logo', 'right'), L('body', 'Stainless steel body', 'right')],
    ('exploded', DEV, 'device-exploded.jpg'): [
        B('body', 1, 0, 150), B('tray', 2, 0, -170), B('nut', 3, 0, 140), B('cap', 4, 40, 150), B('motor', 5, 90, -40),
        B('pack', 6, -60, -110), B('cradle', 7, -120, 40), B('guide', 8, -110, -70), B('screws_guide', 9, 70, -60),
        B('oring', 10, 0, 170), B('buttons', 11, 0, -170), B('cover', 12, 40, 140), B('pcb', 13, 0, -190),
        B('screws_pcb', 14, 30, 150), B('screws_cover', 15, -40, 100), B('skin', 16, 0, -130)],
    ('cutaway', DEV, 'device-cutaway.jpg'): [
        L('skin', 'Silicone skin', 'left'), L('cover', 'Rear cover', 'left'), L('tray', 'Flange tray', 'left'),
        L('pcb', 'PCB', 'left'), L('nut', 'Rear nut', 'left'),
        L('neck', 'Ø12 neck bore', 'left'), L('wires', 'Motor and sensor wires', 'left'), L('contacts', 'Dock contacts', 'left'),
        L('cradle', 'Battery cradle', 'right'), L('body', 'Stainless steel body', 'right'), L('pack', 'Battery', 'right'),
        L('guide', 'Wire guide', 'right'), L('motor', 'Vibration motor', 'right'), L('cap', 'Nose cap', 'right'),
        L('thread', 'M30 thread', 'right'), L('tip', 'Tip temperature sensor', 'right'), L('oring', 'Nose O-ring', 'right')],
    ('step01', ASM, 'step01-tray-nut.jpg'): [
        L('nut', 'Thin nut M18×1', 'left'), L('tray', 'Flange tray', 'left'), L('socket', 'Keyed socket', 'left'),
        L('collar', 'Collar flats', 'left'), L('stub', 'M18×1 stub', 'left'), L('body', 'Metal body', 'right')],
    ('step02', ASM, 'step02-cap.jpg'): [
        L('motor', 'Vibration motor', 'left'), L('pocket', 'Motor pocket', 'right'), L('stop', 'Pocket floor = motor stop', 'right'),
        L('tip', 'Tip sensor, potted in its drill', 'right'), L('cap', 'Nose cap (shown cut in half)', 'right')],
    ('step03', ASM, 'step03-battery-module.jpg'): [
        L('guide', 'Wire guide', 'left'), L('cradle', 'Battery cradle', 'left'), L('screws', '4× M1.4×5', 'right'),
        L('pack', 'Battery', 'right'), L('leads', 'Pack leads exit here', 'right'), L('stop', 'Motor rear stop', 'right')],
    ('step04', ASM, 'step04-module-into-body.jpg'): [
        L('tray', 'Flange tray', 'left'), L('neck', 'Wires run down the neck', 'left'), L('body', 'Body (shown cut)', 'left'),
        L('module', 'Battery module', 'right'), L('oring', 'O-ring 32 × 1', 'right'), L('gland', 'Face gland', 'right')],
    ('step05', ASM, 'step05-close-cap.jpg'): [
        L('thread', 'M30 × 1.5 thread', 'right'), L('oring', 'O-ring in the gland', 'right'), L('cap', 'Nose cap', 'right')],
    ('step06', ASM, 'step06-cover-pcb.jpg'): [
        L('esp', 'ESP32-C3 module', 'left'), L('pcb', 'PCB, back side up', 'left'), L('plungers', 'Plungers in their bores', 'left'),
        L('screws', '2× M1.4×4', 'right'), L('connectors', 'J4 J3 J2 J5', 'right'), L('cover', 'Rear cover, outer face down', 'right')],
    ('step07', ASM, 'step07-connect.jpg'): [
        L('neck', 'Wires from the neck', 'left'), L('j4', 'J4 service (bench only)', 'left'),
        L('pack_wires', 'Pack leads', 'right'), L('j3', 'J3 motor', 'right'), L('j2', 'J2 battery', 'right'), L('j5', 'J5 tip sensor', 'right')],
    ('step08', ASM, 'step08-close-flange.jpg'): [
        L('tray', 'Flange tray', 'left'), L('cover', 'Cover with PCB', 'left'), L('contacts', 'Dock contacts', 'left'),
        L('screws', '2× M2×6', 'left')],
    ('step09', ASM, 'step09-skin.jpg'): [
        L('arrow', 'Calibration arrow', 'left'), L('domes', 'Button domes', 'left'), L('icon', 'R+D logo', 'left'),
        L('ramp', 'Skin bonds to the neck', 'left'), L('window', 'Contact window', 'left'), L('skin', 'Silicone skin', 'left')],
}

# Extra canvas (px) where labels would otherwise sit on the part: (left, top, right, bottom)
EXTEND = {'dockface': (220, 0, 120, 60), 'cutaway': (120, 0, 120, 0), 'step01': (200, 0, 60, 0), 'step02': (120, 0, 160, 0),
          'step03': (120, 0, 140, 0), 'step04': (120, 0, 120, 0), 'step05': (0, 0, 160, 0), 'step06': (220, 0, 160, 0),
          'step07': (220, 0, 120, 0), 'step08': (200, 0, 0, 0), 'step09': (240, 0, 0, 0)}

if __name__ == '__main__':
    only = set(sys.argv[1:])
    for (shot, folder, name), labels in FIGS.items():
        if only and shot not in only:
            continue
        raw = os.path.join(RAW, shot + '.png')
        annotate.compose(raw, os.path.join(folder, name), labels=labels, font_px=30, extend=EXTEND.get(shot, (0, 0, 0, 0)))
        print('wrote', name)
