"""Shared native KiCad authoring for the new safety and UV candidates only."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools'))
import electronics_r0_generate as g
import build_evt1_electrical as e
import kicad_sexp as s

STOCK = Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


class Project:
    def __init__(self, out, stem, title, namespace, library):
        self.out = Path(out); self.out.mkdir(parents=True, exist_ok=True)
        self.stem = stem; self.lib = library; self.rows = []; self.fp_sources = {}
        g.OUT = self.out; g.PROJECT = stem; g.NS = uuid.UUID(namespace)
        g.LIB.clear(); g.PARTS.clear(); e.initialise_symbols()
        g.ic('PWR_FLAG', [(1, 'EXTERNAL_RAIL', 'power_out')], [], '',
             'Explicit external supply contract; annotation only, not a component')
        self.sheet = g.Sheet(stem, title); self.sheet.paper = 'A2'
        self.sheet.sheet_path = '/' + self.sheet.id
        self.fp_dir = self.out / (library + '.pretty'); self.fp_dir.mkdir(exist_ok=True)

    def stock(self, family, name):
        src = STOCK / (family + '.pretty') / (name + '.kicad_mod')
        assert src.exists(), src
        shutil.copy2(src, self.fp_dir / src.name)
        self.fp_sources[name] = {'source': str(src), 'sha256': sha(src)}
        return self.lib + ':' + name

    def custom(self, name, pads, body, courtyard, source, tht=False):
        lines = [f'(footprint {g.q(name)} (version 20221018) (generator dock_candidate) (layer "F.Cu") (attr {"through_hole" if tht else "smd"})',
                 '(fp_text reference "REF**" (at 0 -2.5) (layer "F.SilkS") (effects (font (size .8 .8) (thickness .12))))',
                 f'(fp_text value {g.q(name)} (at 0 2.5) (layer "F.Fab") (effects (font (size .8 .8) (thickness .12))))']
        for layer, box, width in [('F.Fab', body, .1), ('F.CrtYd', courtyard, .05)]:
            points = [(-box[0]/2, -box[1]/2), (box[0]/2, -box[1]/2),
                      (box[0]/2, box[1]/2), (-box[0]/2, box[1]/2)]
            for a, b in zip(points, points[1:]+points[:1]):
                lines.append(f'(fp_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (layer "{layer}") (width {width}))')
        for pad in pads:
            number, x, y, w, h, shape = pad[:6]
            if len(pad) == 7:
                lines.append(f'(pad {g.q(number)} thru_hole {shape} (at {x} {y}) (size {w} {h}) (drill {pad[6]}) (layers "*.Cu" "*.Mask"))')
            else:
                lines.append(f'(pad {g.q(number)} smd {shape} (at {x} {y}) (size {w} {h}) (layers "F.Cu" "F.Paste" "F.Mask"))')
        lines.append(')')
        path = self.fp_dir / (name + '.kicad_mod'); path.write_text('\n'.join(lines)+'\n')
        self.fp_sources[name] = {'manufacturer_drawing': source, 'sha256': sha(path)}
        return self.lib + ':' + name

    def part(self, symbol, ref, value, x, y, nets, footprint, manufacturer, mpn, note='', offboard=False):
        x=round(round(x/2.54)*2.54,4); y=round(round(y/2.54)*2.54,4)
        nets = {str(k): v for k, v in nets.items()}
        self.sheet.part(symbol, ref, value, x, y, nets, footprint or '', note,
                        domain='REMOTE_SAFETY' if offboard else 'MAIN_T')
        source=g.LIB[symbol]['source']
        if not source:
            if manufacturer=='TDK':
                source='https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no='+mpn
            elif manufacturer=='Murata':
                source='https://www.murata.com/en-global/api/pdfdownloadapi?cate=luCeramicCapacitorsSMD&partno='+mpn
            elif manufacturer=='Yageo':
                source='https://www.yageogroup.com/component-documentation/download/specsheet/'+mpn
            elif manufacturer=='Vishay':
                source='https://www.vishay.com/docs/20035/dcrcwe3.pdf'
            elif manufacturer=='manual copper':
                source='Native footprint geometry in local library; manual PCB feature'
        self.rows.append({'reference': ref, 'value': value, 'manufacturer': manufacturer,
                          'mpn': mpn, 'footprint': footprint, 'offboard': offboard,
                          'pins': nets, 'primary_source': source, 'note': note})

    def flag(self, ref, net, x, y):
        x=round(round(x/2.54)*2.54,4); y=round(round(y/2.54)*2.54,4)
        self.sheet.part('PWR_FLAG', ref, 'EXTERNAL_' + net, x, y, {'1': net}, note='External supply contract')

    def port(self, net, direction, x, y):
        """Typed hierarchical boundary, to be wired in the full dock parent."""
        x=round(round(x/2.54)*2.54,4); y=round(round(y/2.54)*2.54,4)
        ex=round(x+7.62,4)
        self.sheet.label(net,x,y,180)
        self.sheet.content.append(f'(wire (pts (xy {x} {y}) (xy {ex} {y})) (stroke (width 0) (type default)) (uuid {g.uid("boundary-wire-"+net)}))')
        self.sheet.content.append(f'(hierarchical_label {g.q(net)} (shape {direction}) (at {ex} {y} 0) {g.effects(1.016,"(justify left)")} (uuid {g.uid("boundary-label-"+net)}))')

    def note(self, text, x, y):
        self.sheet.note(text, x, y, 1.27)

    def save(self):
        self.sheet.save(); path = self.out / (self.stem + '.kicad_sch')
        tree = s.parse(path.read_text().replace('PrototypeR0:', self.lib + ':'))
        s.child(tree, 'generator')[1] = s.atom('dock_candidate')
        title = s.child(tree, 'title_block')
        s.child(title, 'date')[1] = s.string('2026-11-12')
        s.child(title, 'rev')[1] = s.string('EVT1')
        s.child(title, 'comment')[2] = s.string('NATIVE CIRCUIT CANDIDATE - NO PCB OR PHYSICAL VALIDATION')
        for node in s.children(tree, 'symbol'):
            ref = s.prop(node, 'Reference')
            if ref.startswith('#'): continue
            row = next(r for r in self.rows if r['reference'] == ref)
            for key in ('manufacturer', 'mpn'):
                node.append(s.parse(f'(property {g.q("Manufacturer" if key == "manufacturer" else "MPN")} {g.q(row[key])} (at 0 0 0) {g.effects(extra="hide")})'))
        s.write(path, tree)
        lib = [s.atom('kicad_symbol_lib'), s.parse('(version 20220914)'), s.parse('(generator dock_candidate)')]
        for name in sorted(self.sheet.used): lib.append(s.parse(g.LIB[name]['text']))
        s.write(self.out / (self.lib + '.kicad_sym'), lib)
        (self.out/'sym-lib-table').write_text(f'(sym_lib_table (version 7) (lib (name "{self.lib}") (type "KiCad") (uri "${{KIPRJMOD}}/{self.lib}.kicad_sym") (options "") (descr "Selected manufacturer pin contracts")))\n')
        (self.out/'fp-lib-table').write_text(f'(fp_lib_table (version 7) (lib (name "{self.lib}") (type "KiCad") (uri "${{KIPRJMOD}}/{self.lib}.pretty") (options "") (descr "Selected native footprints")))\n')
        (self.out/(self.stem+'.kicad_pro')).write_text(json.dumps({'meta': {'filename': self.stem+'.kicad_pro', 'version': 1}, 'erc': {'erc_exclusions': []}}, indent=2)+'\n')
        manifest = {'status': 'native circuit candidate; PCB and physical validation pending',
                    'schematic': path.name, 'library': self.lib, 'parts': self.rows,
                    'footprint_provenance': self.fp_sources, 'full_product_order_ready': False}
        (self.out/'parts-selection.json').write_text(json.dumps(manifest, indent=2)+'\n')
        print(json.dumps({'project': self.stem, 'positions': len(self.rows), 'out': str(self.out)}))

