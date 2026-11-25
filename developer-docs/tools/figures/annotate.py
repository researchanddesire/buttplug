"""Compose a raw Blender render (RGBA PNG + anchors JSON) into a docs figure:
flat background, optional labels with leader lines or numbered balloons, then
rasterise with Inkscape and save as JPEG (sips) or PNG.

Usage from Python:  annotate.compose(raw_png, out_path, labels=[...], background='#f4f5f7')
Label dict: {'anchor': name, 'text': str, 'side': 'left'|'right'|'top'|'bottom'|(dx, dy),
             'style': 'label'|'balloon'}
"""
import base64, json, os, subprocess, html

INKSCAPE = '/Applications/Inkscape.app/Contents/MacOS/inkscape'
FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"
INK = '#1f2933'
LEAD = '#4a5560'
ACCENT = '#e4572e'


def _png_size(path):
    with open(path, 'rb') as f:
        head = f.read(24)
    import struct
    return struct.unpack('>II', head[16:24])


def compose(raw_png, out_path, labels=(), background='#f4f5f7', font_px=None, crop=None, title=None,
            balloon_r=None, scale_out=1.0, extend=(0, 0, 0, 0)):
    W, H = _png_size(raw_png)
    meta = {}
    if os.path.exists(raw_png + '.json'):
        meta = json.load(open(raw_png + '.json'))
    anchors = meta.get('anchors', {})
    fs = font_px or round(W / 58)
    br = balloon_r or round(fs * 0.85)
    x0, y0, x1, y1 = crop or (0, 0, W, H)
    x0 -= extend[0]; y0 -= extend[1]; x1 += extend[2]; y1 += extend[3]
    cw, ch = x1 - x0, y1 - y0
    b64 = base64.b64encode(open(raw_png, 'rb').read()).decode()
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           'width="%d" height="%d" viewBox="%d %d %d %d">' % (cw, ch, x0, y0, cw, ch)]
    svg.append('<rect x="%d" y="%d" width="%d" height="%d" fill="%s"/>' % (x0, y0, cw, ch, background))
    svg.append('<image x="0" y="0" width="%d" height="%d" xlink:href="data:image/png;base64,%s"/>' % (W, H, b64))
    # --- labels
    groups = {'left': [], 'right': [], 'top': [], 'bottom': [], 'free': []}
    for lab in labels:
        a = anchors.get(lab['anchor'])
        if a is None:
            raise KeyError('anchor not projected: %s' % lab['anchor'])
        side = lab.get('side', 'right')
        if isinstance(side, (list, tuple)):
            groups['free'].append((lab, a, side))
        else:
            groups[side].append((lab, a, None))
    pad = fs * 0.9
    gap = fs * 1.75
    def spread(items, key, lo, hi):
        items.sort(key=lambda t: t[1][key])
        pos = [t[1][key] for t in items]
        for i in range(1, len(pos)):
            pos[i] = max(pos[i], pos[i - 1] + gap)
        over = (pos[-1] - hi) if pos else 0
        if over > 0:
            pos = [p - over for p in pos]
            for i in range(len(pos) - 2, -1, -1):
                pos[i] = min(pos[i], pos[i + 1] - gap)
        return pos
    def dot(x, y):
        svg.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="white" stroke-width="%.1f"/>' % (x, y, fs * 0.22, LEAD, fs * 0.08))
    def text(x, y, t, anchor='start', weight='normal', size=None, color=INK):
        svg.append('<text x="%.1f" y="%.1f" font-family="%s" font-size="%.1f" font-weight="%s" fill="%s" text-anchor="%s" dominant-baseline="central">%s</text>'
                   % (x, y, FONT, size or fs, weight, color, anchor, html.escape(t)))
    def balloon(x, y, t):
        svg.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="white" stroke="%s" stroke-width="%.1f"/>' % (x, y, br, INK, fs * 0.09))
        text(x, y + fs * 0.03, t, anchor='middle', weight='bold', size=fs * 0.9)
    for side in ('left', 'right'):
        items = groups[side]
        if not items:
            continue
        ys = spread(items, 1, y0 + pad, y1 - pad)
        for (lab, (ax, ay), _), ty in zip(items, ys):
            if lab.get('style') == 'balloon':
                bx = x0 + pad + br if side == 'left' else x1 - pad - br
                svg.append('<polyline points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="none" stroke="%s" stroke-width="%.1f"/>'
                           % (bx + (br if side == 'left' else -br), ty, (bx + ax) / 2, ty, ax, ay, LEAD, fs * 0.07))
                dot(ax, ay); balloon(bx, ty, lab['text'])
                continue
            tx = x0 + pad if side == 'left' else x1 - pad
            tw = len(lab['text']) * fs * 0.56
            ex = tx + tw + fs * 0.4 if side == 'left' else tx - tw - fs * 0.4
            kx = ex + (fs * 1.2 if side == 'left' else -fs * 1.2)
            svg.append('<polyline points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="none" stroke="%s" stroke-width="%.1f"/>'
                       % (ex, ty, kx, ty, ax, ay, LEAD, fs * 0.07))
            dot(ax, ay)
            text(tx, ty, lab['text'], anchor='start' if side == 'left' else 'end')
    for side in ('top', 'bottom'):
        items = groups[side]
        if not items:
            continue
        items.sort(key=lambda t: t[1][0])
        base = y0 + pad + fs * 0.6 if side == 'top' else y1 - pad - fs * 0.6
        step = fs * 1.5 * (1 if side == 'top' else -1)
        last_right, row = -1e9, 0
        for lab, (ax, ay), _ in items:
            tw = len(lab['text']) * fs * 0.56
            row = row + 1 if ax - tw / 2 < last_right + fs * 0.4 else 0
            ty = base + row * step
            last_right = ax + tw / 2
            if lab.get('style') == 'balloon':
                svg.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.1f"/>' % (ax, ty, ax, ay, LEAD, fs * 0.07))
                dot(ax, ay); balloon(ax, ty, lab['text'])
            else:
                svg.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.1f"/>' % (ax, ty + (fs * 0.7 if side == 'top' else -fs * 0.7), ax, ay, LEAD, fs * 0.07))
                dot(ax, ay); text(ax, ty, lab['text'], anchor='middle')
    for lab, (ax, ay), (dx, dy) in groups['free']:
        bx, by = ax + dx, ay + dy
        if lab.get('style') == 'balloon':
            import math
            d = math.hypot(dx, dy) or 1
            svg.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.1f"/>' % (bx - dx / d * br, by - dy / d * br, ax, ay, LEAD, fs * 0.07))
            dot(ax, ay); balloon(bx, by, lab['text'])
        else:
            anchor = 'start' if dx >= 0 else 'end'
            svg.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%.1f"/>' % (bx - (fs * 0.3 if dx >= 0 else -fs * 0.3), by, ax, ay, LEAD, fs * 0.07))
            dot(ax, ay); text(bx, by, lab['text'], anchor=anchor)
    if title:
        text(x0 + pad, y0 + pad + fs * 0.3, title, weight='bold', size=fs * 1.15)
    svg.append('</svg>')
    tmp_svg = out_path + '.svg'
    with open(tmp_svg, 'w') as f:
        f.write('\n'.join(svg))
    tmp_png = out_path + '.tmp.png'
    subprocess.run([INKSCAPE, tmp_svg, '--export-type=png', '--export-filename=' + tmp_png,
                    '--export-width=%d' % round(cw * scale_out)], check=True, capture_output=True)
    if out_path.lower().endswith(('.jpg', '.jpeg')):
        subprocess.run(['sips', '-s', 'format', 'jpeg', '-s', 'formatOptions', '88', tmp_png, '--out', out_path],
                       check=True, capture_output=True)
        os.remove(tmp_png)
    else:
        os.replace(tmp_png, out_path)
    os.remove(tmp_svg)
    return out_path
