"""Minimal SVG engineering-drawing toolkit (mm units on the sheet).

Views map model 2D coordinates to the sheet with a scale and an orientation.
Dimensions, leaders, centre lines, section hatching, title block and notes follow
ISO 128/129 conventions loosely: thick visible lines, thin dimension lines,
filled arrowheads, text above the dimension line.
"""
import math, html

FONT = "'Helvetica Neue', Helvetica, Arial, sans-serif"
THICK, THIN, XTHIN = 0.45, 0.18, 0.13
TXT = 3.0          # dimension text height (mm)
ARW_L, ARW_W = 2.6, 0.45


def esc(t):
    return html.escape(str(t))


class Sheet:
    def __init__(self, w=420, h=297, title='', border=10):
        self.w, self.h, self.border = w, h, border
        self.el = []
        self.defs = []
        self._hatches = set()

    # ------------------------------------------------------------ primitives (sheet mm)
    def line(self, x1, y1, x2, y2, w=THIN, color='#000', dash=None, cap='butt'):
        d = ' stroke-dasharray="%s"' % dash if dash else ''
        self.el.append('<line x1="%.3f" y1="%.3f" x2="%.3f" y2="%.3f" stroke="%s" stroke-width="%.3f" stroke-linecap="%s"%s/>'
                       % (x1, y1, x2, y2, color, w, cap, d))

    def polyline(self, pts, w=THIN, color='#000', dash=None, close=False, fill='none'):
        if len(pts) < 2:
            return
        d = ' stroke-dasharray="%s"' % dash if dash else ''
        tag = 'polygon' if close else 'polyline'
        self.el.append('<%s points="%s" fill="%s" stroke="%s" stroke-width="%.3f" stroke-linejoin="round" stroke-linecap="round"%s/>'
                       % (tag, ' '.join('%.3f,%.3f' % p for p in pts), fill, color, w, d))

    def path(self, loops, fill='none', stroke='#000', w=THICK, opacity=1.0):
        d = ' '.join('M' + ' L'.join('%.3f,%.3f' % p for p in loop) + ' Z' for loop in loops if len(loop) > 2)
        self.el.append('<path d="%s" fill="%s" fill-rule="evenodd" stroke="%s" stroke-width="%.3f" stroke-linejoin="round" fill-opacity="%.2f"/>'
                       % (d, fill, stroke, w, opacity))

    def text(self, x, y, t, size=TXT, anchor='middle', rot=0, weight='normal', color='#000', baseline='alphabetic', italic=False):
        tr = ' transform="rotate(%.2f %.3f %.3f)"' % (rot, x, y) if rot else ''
        st = ' font-style="italic"' if italic else ''
        self.el.append('<text x="%.3f" y="%.3f" font-family="%s" font-size="%.2f" text-anchor="%s" font-weight="%s" fill="%s" dominant-baseline="%s"%s%s>%s</text>'
                       % (x, y, FONT, size, anchor, weight, color, baseline, tr, st, esc(t)))

    def rect(self, x, y, w, h, stroke='#000', sw=THIN, fill='none'):
        self.el.append('<rect x="%.3f" y="%.3f" width="%.3f" height="%.3f" fill="%s" stroke="%s" stroke-width="%.3f"/>' % (x, y, w, h, fill, stroke, sw))

    def circle(self, x, y, r, stroke='#000', sw=THIN, fill='none', dash=None):
        d = ' stroke-dasharray="%s"' % dash if dash else ''
        self.el.append('<circle cx="%.3f" cy="%.3f" r="%.3f" fill="%s" stroke="%s" stroke-width="%.3f"%s/>' % (x, y, r, fill, stroke, sw, d))

    def arrowhead(self, x, y, ang, l=ARW_L, w=ARW_W, color='#000'):
        """Filled arrowhead with its tip at (x, y), pointing along `ang` (radians)."""
        ca, sa = math.cos(ang), math.sin(ang)
        bx, by = x - l * ca, y - l * sa
        p = [(x, y), (bx - w * sa, by + w * ca), (bx + w * sa, by - w * ca)]
        self.el.append('<polygon points="%s" fill="%s" stroke="none"/>' % (' '.join('%.3f,%.3f' % q for q in p), color))

    def hatch(self, name, angle=45, spacing=1.2, w=XTHIN, color='#000', bg='none', cross=False):
        if name in self._hatches:
            return 'url(#%s)' % name
        self._hatches.add(name)
        lines = '<line x1="0" y1="0" x2="0" y2="%.3f" stroke="%s" stroke-width="%.3f"/>' % (spacing, color, w)
        if cross:
            lines += '<line x1="0" y1="0" x2="%.3f" y2="0" stroke="%s" stroke-width="%.3f"/>' % (spacing, color, w)
        bgr = '<rect width="%.3f" height="%.3f" fill="%s"/>' % (spacing, spacing, bg) if bg != 'none' else ''
        self.defs.append('<pattern id="%s" patternUnits="userSpaceOnUse" width="%.3f" height="%.3f" patternTransform="rotate(%.1f)">%s%s</pattern>'
                         % (name, spacing, spacing, angle, bgr, lines))
        return 'url(#%s)' % name

    # ------------------------------------------------------------ sheet furniture
    def frame(self):
        b = self.border
        self.rect(b, b, self.w - 2 * b, self.h - 2 * b, sw=0.5)

    def title_block(self, fields, x=None, y=None, w=180, h=48):
        """fields: dict with title, number, material, finish, scale, units, projection, rev, date, sheet, source, note."""
        b = self.border
        x = self.w - b - w if x is None else x
        y = self.h - b - h if y is None else y
        self.rect(x, y, w, h, sw=0.5)
        # rows
        r1 = y + 16; r2 = y + 26; r3 = y + 36
        self.line(x, r1, x + w, r1, 0.3); self.line(x, r2, x + w, r2, 0.3); self.line(x, r3, x + w, r3, 0.3)
        self.text(x + 3, y + 7.5, fields.get('title', ''), size=5.2, anchor='start', weight='bold')
        self.text(x + 3, y + 13.2, fields.get('subtitle', ''), size=3.0, anchor='start', color='#333')
        cols = [x, x + 45, x + 90, x + 125, x + w]
        def cell(c0, c1, row_y, label, value, vsize=3.1):
            self.text(c0 + 1.5, row_y + 3.0, label, size=1.9, anchor='start', color='#555')
            self.text(c0 + 1.5, row_y + 8.0, value, size=vsize, anchor='start')
        for cx in cols[1:-1]:
            self.line(cx, r1, cx, r3, 0.3)
        cell(cols[0], cols[1], r1, 'PART NUMBER', fields.get('number', ''))
        cell(cols[1], cols[2], r1, 'MATERIAL', fields.get('material', ''), 2.6)
        cell(cols[2], cols[3], r1, 'SCALE', fields.get('scale', ''))
        cell(cols[3], cols[4], r1, 'REV', fields.get('rev', ''))
        cell(cols[0], cols[1], r2, 'UNITS', fields.get('units', 'mm'))
        cell(cols[1], cols[2], r2, 'FINISH', fields.get('finish', ''), 2.6)
        cell(cols[2], cols[3], r2, 'DATE', fields.get('date', ''))
        cell(cols[3], cols[4], r2, 'SHEET', fields.get('sheet', '1 / 1'))
        self.text(x + 1.5, r3 + 3.0, 'SOURCE', size=1.9, anchor='start', color='#555')
        self.text(x + 1.5, r3 + 8.2, fields.get('source', ''), size=2.4, anchor='start')
        # projection symbol (third angle) in the scale cell corner
        if fields.get('projection', 'third') == 'third':
            self.projection_symbol(cols[2] + 26, r1 + 5.2, third=True)
        else:
            self.projection_symbol(cols[2] + 26, r1 + 5.2, third=False)

    def projection_symbol(self, x, y, third=True, s=0.9):
        # truncated cone side view + circles (ISO 5456-2)
        cone = [(x, y - 2.0 * s), (x + 4.5 * s, y - 3.2 * s), (x + 4.5 * s, y + 3.2 * s), (x, y + 2.0 * s)]
        cx = x - 4.2 * s if third else x + 8.7 * s
        if third:
            cone = [(p[0] + 0, p[1]) for p in cone]
        self.polyline(cone, w=0.25, close=True)
        self.line(x - 1 * s, y, x + 5.5 * s, y, 0.13, dash='1.2,0.6,0.2,0.6')
        self.circle(cx, y, 3.2 * s, sw=0.25); self.circle(cx, y, 2.0 * s, sw=0.25)

    def notes(self, x, y, title, items, width=170, size=2.7, lh=4.2):
        self.text(x, y, title, size=3.4, anchor='start', weight='bold')
        yy = y + 5.5
        for i, it in enumerate(items, 1):
            for j, line in enumerate(wrap(it, int(width / (size * 0.52)))):
                self.text(x + (0 if j == 0 else 4.5), yy, ('%d. ' % i if j == 0 else '') + line, size=size, anchor='start')
                yy += lh
        return yy

    def table(self, x, y, headers, rows, widths, size=2.5, rh=5.0, header_fill='#eef0f2'):
        tw = sum(widths)
        self.rect(x, y, tw, rh, fill=header_fill, sw=0.25)
        cx = x
        for hdr, w in zip(headers, widths):
            self.text(cx + 1.2, y + rh * 0.68, hdr, size=size * 0.92, anchor='start', weight='bold')
            cx += w
        yy = y + rh
        for r in rows:
            self.rect(x, yy, tw, rh, sw=0.2)
            cx = x
            for v, w in zip(r, widths):
                self.text(cx + 1.2, yy + rh * 0.68, v, size=size, anchor='start')
                cx += w
            yy += rh
        cx = x
        for w in widths[:-1]:
            cx += w
            self.line(cx, y, cx, yy, 0.2)
        return yy

    def svg(self):
        head = ('<svg xmlns="http://www.w3.org/2000/svg" width="%gmm" height="%gmm" viewBox="0 0 %g %g">' % (self.w, self.h, self.w, self.h))
        return '\n'.join([head, '<defs>' + ''.join(self.defs) + '</defs>', '<rect width="%g" height="%g" fill="white"/>' % (self.w, self.h)] + self.el + ['</svg>'])


def wrap(text, n):
    words, lines, cur = text.split(), [], ''
    for w in words:
        if len(cur) + len(w) + 1 > n and cur:
            lines.append(cur); cur = w
        else:
            cur = (cur + ' ' + w).strip()
    if cur:
        lines.append(cur)
    return lines


class View:
    """Model (u, v) -> sheet. `axes` picks/negates model coords: function (x, y) -> (h, v) in model mm,
    h to the right and v up on the sheet."""
    def __init__(self, sheet, ox, oy, scale, axes=lambda x, y: (x, y), clip=None):
        self.s, self.ox, self.oy, self.k, self.axes = sheet, ox, oy, scale, axes
        self.clip = clip      # (h0, v0, h1, v1) model window for detail views

    def P(self, x, y):
        h, v = self.axes(x, y)
        return (self.ox + self.k * h, self.oy - self.k * v)

    def Phv(self, h, v):
        return (self.ox + self.k * h, self.oy - self.k * v)

    def _clip_poly(self, pts, closed):
        if not self.clip:
            return [[self.P(*p) for p in pts]]
        h0, v0, h1, v1 = self.clip
        hv = [self.axes(*p) for p in pts]
        # Sutherland-Hodgman for closed polygons; segment clipping for polylines
        if closed:
            poly = hv
            for axis, bound, keep_greater in ((0, h0, True), (0, h1, False), (1, v0, True), (1, v1, False)):
                res = []
                for a, b in zip(poly, poly[1:] + poly[:1]):
                    ain = a[axis] >= bound if keep_greater else a[axis] <= bound
                    bin_ = b[axis] >= bound if keep_greater else b[axis] <= bound
                    if ain:
                        res.append(a)
                    if ain != bin_:
                        t = (bound - a[axis]) / (b[axis] - a[axis])
                        res.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
                poly = res
                if not poly:
                    return []
            return [[self.Phv(*p) for p in poly]]
        out, cur = [], []
        def inside(p):
            return h0 <= p[0] <= h1 and v0 <= p[1] <= v1
        for a, b in zip(hv, hv[1:]):
            # Liang-Barsky
            t0, t1 = 0.0, 1.0
            dx, dy = b[0] - a[0], b[1] - a[1]
            ok = True
            for p_, q_ in ((-dx, a[0] - h0), (dx, h1 - a[0]), (-dy, a[1] - v0), (dy, v1 - a[1])):
                if abs(p_) < 1e-12:
                    if q_ < 0:
                        ok = False
                        break
                else:
                    t = q_ / p_
                    if p_ < 0:
                        t0 = max(t0, t)
                    else:
                        t1 = min(t1, t)
            if not ok or t0 > t1:
                if cur:
                    out.append(cur); cur = []
                continue
            pa = (a[0] + t0 * dx, a[1] + t0 * dy); pb = (a[0] + t1 * dx, a[1] + t1 * dy)
            if not cur:
                cur = [self.Phv(*pa)]
            cur.append(self.Phv(*pb))
            if t1 < 1.0:
                out.append(cur); cur = []
        if cur:
            out.append(cur)
        return out

    def section(self, loops, fill, stroke='#000', w=THICK):
        polys = []
        for l in loops:
            polys += self._clip_poly(l, True)
        self.s.path(polys, fill=fill, stroke=stroke, w=w)

    def edges(self, polylines, w=THICK, color='#000', dash=None):
        for pl in polylines:
            for seg in self._clip_poly(pl, False):
                self.s.polyline(seg, w=w, color=color, dash=dash)

    def centerline(self, p1, p2, ext=3.0):
        a = self.P(*p1); b = self.P(*p2)
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
        ux, uy = (b[0] - a[0]) / L, (b[1] - a[1]) / L
        self.s.line(a[0] - ux * ext, a[1] - uy * ext, b[0] + ux * ext, b[1] + uy * ext, XTHIN, dash='6,1.2,1,1.2')

    # ------------------------------------------------------------ dimensions
    def dim(self, p1, p2, offset, text, orient='h', tol=None, text_shift=0.0, inside_arrows=True, ext_gap=0.8, ext_over=1.5, at=None):
        """Linear dimension between model points p1, p2. orient 'h' measures the sheet-horizontal
        distance (dimension line horizontal, offset in sheet mm, + is up); 'v' measures vertical
        (offset + is right)."""
        a = self.P(*p1); b = self.P(*p2); S = self.s
        if orient == 'h':
            y = at if at is not None else (min(a[1], b[1]) - offset if offset > 0 else max(a[1], b[1]) - offset)
            for p in (a, b):
                sgn = -1 if y < p[1] else 1
                S.line(p[0], p[1] + sgn * ext_gap, p[0], y + sgn * ext_over, XTHIN)
            x1, x2 = sorted((a[0], b[0]))
            L = x2 - x1
            if L > 2.4 * ARW_L or not inside_arrows:
                S.line(x1, y, x2, y, XTHIN)
                S.arrowhead(x1, y, math.pi); S.arrowhead(x2, y, 0)
            else:
                S.line(x1 - ARW_L * 2.2, y, x2 + ARW_L * 2.2, y, XTHIN)
                S.arrowhead(x1, y, 0); S.arrowhead(x2, y, math.pi)
            tx = (x1 + x2) / 2 + text_shift
            S.text(tx, y - 0.9, text, size=TXT)
            if tol:
                S.text(tx + len(text) * TXT * 0.29 + 0.6, y - 2.4, tol, size=TXT * 0.62, anchor='start')
        else:
            x = at if at is not None else (max(a[0], b[0]) + offset if offset > 0 else min(a[0], b[0]) + offset)
            for p in (a, b):
                sgn = 1 if x > p[0] else -1
                S.line(p[0] + sgn * ext_gap, p[1], x + sgn * ext_over, p[1], XTHIN)
            y1, y2 = sorted((a[1], b[1]))
            L = y2 - y1
            if L > 2.4 * ARW_L or not inside_arrows:
                S.line(x, y1, x, y2, XTHIN)
                S.arrowhead(x, y1, -math.pi / 2); S.arrowhead(x, y2, math.pi / 2)
            else:
                S.line(x, y1 - ARW_L * 2.2, x, y2 + ARW_L * 2.2, XTHIN)
                S.arrowhead(x, y1, math.pi / 2); S.arrowhead(x, y2, -math.pi / 2)
            ty = (y1 + y2) / 2 + text_shift
            S.text(x - 0.9, ty, text, size=TXT, rot=-90)

    def leader(self, p, dx, dy, text, size=TXT, shelf=None, dot=False, lines=None):
        """Leader from model point p to a text at sheet offset (dx, dy) mm; arrow at p."""
        S = self.s
        a = self.P(*p)
        tx, ty = a[0] + dx, a[1] + dy
        ang = math.atan2(a[1] - ty, a[0] - tx)
        S.line(tx, ty, a[0], a[1], XTHIN)
        if dot:
            S.circle(a[0], a[1], 0.45, fill='#000', sw=0)
        else:
            S.arrowhead(a[0], a[1], ang)
        txt_lines = lines or [text]
        wmax = max(len(t) for t in txt_lines) * size * 0.5 + 1.0
        if shelf is None:
            shelf = 1 if dx >= 0 else -1
        S.line(tx, ty, tx + shelf * wmax, ty, XTHIN)
        for i, t in enumerate(txt_lines):
            S.text(tx + shelf * 0.8, ty - 0.9 + i * (size * 1.35), t, size=size, anchor='start' if shelf > 0 else 'end')

    def label(self, p, text, dx=0, dy=0, size=TXT, anchor='middle', weight='normal'):
        a = self.P(*p)
        self.s.text(a[0] + dx, a[1] + dy, text, size=size, anchor=anchor, weight=weight)

    def section_arrows(self, p1, p2, letter, look_dir):
        """Cutting-plane line from p1 to p2 (model) with view arrows pointing along look_dir (sheet unit vector)."""
        S = self.s
        a = self.P(*p1); b = self.P(*p2)
        S.line(a[0], a[1], b[0], b[1], 0.18, dash='8,1.5,1.5,1.5')
        for p in (a, b):
            S.line(p[0], p[1], p[0], p[1], 0.7)
            ex, ey = p[0] + look_dir[0] * 6, p[1] + look_dir[1] * 6
            S.line(p[0], p[1], ex, ey, 0.35)
            S.arrowhead(ex, ey, math.atan2(look_dir[1], look_dir[0]), l=2.6, w=0.8)
            S.text(ex + look_dir[0] * 3, ey + look_dir[1] * 3 + 1.4, letter, size=4.2, weight='bold')

    def frame_detail(self, letter, scale_text, h0, v0, h1, v1):
        a = self.Phv(h0, v1); b = self.Phv(h1, v0)
        self.s.text((a[0] + b[0]) / 2, b[1] + 6.5, 'DETAIL %s  (%s)' % (letter, scale_text), size=3.6, weight='bold')

    def detail_circle(self, c, r, letter):
        a = self.P(*c)
        self.s.circle(a[0], a[1], r * self.k, sw=0.25, dash='3,1')
        self.s.text(a[0] + r * self.k * 0.75, a[1] - r * self.k * 0.85, letter, size=4.0, weight='bold')
