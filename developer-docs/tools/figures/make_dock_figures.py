"""Compose the raw dock renders (render_dock.py) into labelled docs figures.

Run (system python): python3 make_dock_figures.py [shot ...]
Writes docs/assets/dock/*.jpg and assembly-docs/assets/assembly/dock-d*.jpg.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import annotate

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.abspath(os.path.join(HERE, '..', '..'))
RAW = os.path.join(DOCS, '.cache', 'figures', 'raw')
DOCK = os.path.join(DOCS, 'docs', 'assets', 'dock')
ASM = os.path.join(os.path.dirname(DOCS), 'assembly-docs', 'assets', 'assembly')
os.makedirs(DOCK, exist_ok=True); os.makedirs(ASM, exist_ok=True)

def L(anchor, text, side):
    return {'anchor': anchor, 'text': text, 'side': side}

FIGS = {
    ('hero', DOCK, 'dock-hero.jpg', (0, 0, 0, 0)): [
        L('screen', 'Screen', 'top'), L('center', 'Three buttons', 'right'), L('lid', 'Lid', 'right'),
        L('base', 'Base', 'right'), L('latch', 'Magnetic latch', 'left'), L('usb', 'USB-C', 'left')],
    ('open', DOCK, 'dock-open.jpg', (0, 0, 0, 0)): [
        L('contacts', 'Contact head', 'left'), L('seat', 'Device seat', 'right'), L('hinge', 'Hinge', 'right')],
    ('base-inside', DOCK, 'dock-base-inside.jpg', (60, 0, 140, 0)): [
        L('spreader', 'UV heat spreader', 'left'), L('hall', 'Lid sensor', 'left'), L('carrier', 'Contact head', 'left'),
        L('harness', 'Contact wires', 'left'), L('usb', 'USB-C', 'left'),
        L('uvbase', 'Base UV board', 'right'), L('j401', 'UV harness', 'right'), L('main', 'Main board', 'right')],
    ('lid-inside', DOCK, 'dock-lid-inside.jpg', (140, 0, 140, 0)): [
        L('ui', 'Lid UI board', 'left'), L('magnet', 'Hall magnet', 'left'), L('uv', 'Lid UV board', 'right')],
    ('contact-head', DOCK, 'dock-contact-head.jpg', (0, 0, 120, 0)): [
        L('carrier', 'Carrier', 'left'), L('foot', 'Carrier foot', 'left'),
        L('pogo', 'Four spring pins', 'right'), L('pinboard', 'Pin board', 'right'), L('magnet', 'Magnet', 'right'),
        L('retainer', 'Retainer', 'right'), L('wires', 'Wires to Main', 'right')],
    ('d1', ASM, 'dock-d1.jpg', (100, 0, 100, 0)): [
        L('usb', 'USB-C port', 'left'), L('bosses', 'Bosses: drill Ø1.6, tap M2', 'left'),
        L('screws', '6× M2 × 4', 'right'), L('main', 'Main board', 'right'), L('shell', 'Lower shell', 'right')],
    ('d2', ASM, 'dock-d2.jpg', (100, 0, 100, 0)): [
        L('pogo', 'Spring pins', 'left'), L('pinboard', 'Pin board', 'left'), L('magnet', 'Magnets and springs', 'left'),
        L('carrier', 'Carrier and retainer', 'right'), L('foot', '2× M3 × 12 from below', 'right')],
    ('d3', ASM, 'dock-d3.jpg', (100, 0, 100, 0)): [
        L('spreader', 'Aluminium spreader', 'left'), L('harness', 'J401 harness', 'left'),
        L('screws', '4× M2 × 6', 'right'), L('leds', 'UV-C LEDs', 'right'), L('board', 'Base UV board', 'right')],
    ('d4', ASM, 'dock-d4.jpg', (0, 0, 140, 0)): [
        L('liner', 'Lower liner', 'right'), L('screws', '4× M2 × 6 countersunk', 'right'), L('pocket', 'Pocket over J401', 'right')],
    ('d5', ASM, 'dock-d5.jpg', (120, 0, 0, 0)): [
        L('j94', 'Pin board J94', 'left'), L('wires', 'GND, D−, D+, 5 V', 'left'), L('j102', 'Main J102', 'left')],
    ('d6', ASM, 'dock-d6.jpg', (0, 0, 0, 0)): [
        L('hallL', 'Hall sensor, left', 'left'), L('hallR', 'Hall sensor, right', 'right')],
    ('d7', ASM, 'dock-d7.jpg', (0, 0, 120, 0)): [
        L('caps', 'Button caps', 'right'), L('springs', 'Springs', 'right'), L('bezel', 'Bezel', 'left'), L('lid', 'Lid', 'right')],
    ('d8', ASM, 'dock-d8.jpg', (140, 0, 140, 0)): [
        L('ui', 'UI board on 1.5 mm shims', 'left'), L('magnet', 'Hall magnet carrier', 'left'), L('uv', 'Lid UV module', 'right')],
    ('d9', ASM, 'dock-d9.jpg', (0, 0, 0, 0)): [
        L('pin', 'Hinge pin', 'left'), L('washer', 'Washer and M2 screw', 'right'), L('flex', 'Hinge flex', 'right')],
}

if __name__ == '__main__':
    only = set(sys.argv[1:])
    for (shot, folder, name, ext), labels in FIGS.items():
        if only and shot not in only:
            continue
        raw = os.path.join(RAW, 'dock-' + shot + '.png')
        if not os.path.exists(raw):
            print('missing', raw); continue
        annotate.compose(raw, os.path.join(folder, name), labels=labels, font_px=30, extend=ext)
        print('wrote', name)
