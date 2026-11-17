"""Render review views from the exact FreeCAD fixture mesh export."""
import argparse
from html import escape
import json
from math import sqrt
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("package", type=Path, help="Builder output containing review-mesh.json.")
args = parser.parse_args()
HERE = args.package
mesh = json.loads((HERE / "review-mesh.json").read_text())
svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="1200" viewBox="0 0 1500 1200">',
       '<rect width="1500" height="1200" fill="#f1f5f8"/>',
       '<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0 L7 3.5 L0 7Z" fill="#304b64"/></marker></defs>']
colors = {
    "BenchSaddle": (50, 124, 158),
    "PreloadBar": (22, 84, 113),
    "PogoRetainer": (97, 167, 194),
    "RevisedContinuousSkin": (137, 110, 176),
    "MetalBody": (158, 181, 194),
    "MotorThermistorCap": (174, 192, 204),
    "J94PinBoard": (83, 156, 110),
}

def vector_add(a, b):
    return tuple(x + y for x, y in zip(a, b))

def subtract(a, b):
    return tuple(x - y for x, y in zip(a, b))

def dot(a, b):
    return sum(x*y for x, y in zip(a, b))

def normalize(a):
    length = sqrt(dot(a, a))
    return tuple(n / length for n in a) if length else a

def cross(a, b):
    ax, ay, az = a
    bx, by, bz = b
    return ay*bz-az*by, az*bx-ax*bz, ax*by-ay*bx

def line(x, y, value, size=25, fill="#193349", weight=400):
    svg.append(f'<text x="{x}" y="{y}" fill="{fill}" font-family="sans-serif" font-weight="{weight}" font-size="{size}">{escape(value)}</text>')

def panel(ident, box, title, subtitle, camera, names, offsets=None, crop=None):
    x, y, width, height = box
    svg.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="22" fill="#ffffff" stroke="#dbe6ee"/>')
    line(x+29, y+44, title, 28, weight=700)
    line(x+29, y+78, subtitle, 21, "#49647b")
    eye = normalize(camera)
    horiz = normalize(cross((0,0,1), eye))
    vert = normalize(cross(eye, horiz))
    records = {name:[vector_add(p, (offsets or {}).get(name,(0,0,0)))
                     for p in mesh[name]["nodes"]] for name in names}
    points = crop or [p for v in records.values() for p in v]
    u = [dot(p,horiz) for p in points]
    v = [dot(p,vert) for p in points]
    scale = min((width-100)/(max(u)-min(u)),(height-142)/(max(v)-min(v)))
    tx = x+width/2 - ((min(u)+max(u))/2)*scale
    ty = y+101+(height-111)/2 + ((min(v)+max(v))/2)*scale
    def project(point):
        return tx+dot(point,horiz)*scale, ty-dot(point,vert)*scale
    svg.append(f'<clipPath id="{ident}"><rect x="{x+12}" y="{y+93}" width="{width-24}" height="{height-105}"/></clipPath>')
    svg.append(f'<g clip-path="url(#{ident})">')
    light = normalize((-.35, -.6, 1))
    polygons = []
    for name in names:
        shade = colors.get(name, (218,171,61) if name.startswith("CT") else (228,184,82))
        points = records[name]
        for a,b,c in mesh[name]["faces"]:
            tri = points[a], points[b], points[c]
            normal = normalize(cross(subtract(tri[1],tri[0]),subtract(tri[2],tri[0])))
            if dot(normal,eye)<=0:
                continue
            luminance=.56+.44*max(dot(normal,light),0)
            xyz = (sum(dot(p,eye) for p in tri))/3
            color = '#'+''.join(f'{int(s*luminance):02x}' for s in shade)
            xy = " ".join(f"{px:.1f},{py:.1f}" for px,py in map(project,tri))
            polygons.append((xyz,color,xy))
    for _,color,xy in sorted(polygons):
        svg.append(f'<polygon points="{xy}" fill="{color}" stroke="{color}" stroke-width="0.55" stroke-linejoin="round"/>')
    svg.append("</g>")
    return project

def label(project, ptr, start, text, width):
    px,py=project(ptr)
    x,y=start
    ex=x+width/2
    svg.append(f'<path d="M{ex} {y+14} L{px:.1f} {py:.1f}" fill="none" stroke="#304b64" stroke-width="2" marker-end="url(#arrow)"/>')
    svg.append(f'<rect x="{x}" y="{y}" width="{width}" height="33" rx="7" fill="#fff" stroke="#bbcddd"/>')
    line(x+10,y+23,text,18,weight=650)

line(52,60,"Compass EVT1 · Direct PC contact fixture",40,weight=700)
line(52,98,"The removable fixture and dock use the same four contacts. The plug seats in one at a time.",23,"#48637a")
n = list(mesh)
installed = panel("seated",(48,128,1404,490),"Seated first article",
    "Lower the plug with the bar removed. Slide 3 mm toward the pin rail, then close the bar.",
    (0.8,-1.05,.83),n)
label(installed,(9,19,43),(235,240),"Fixed contact rail",168)
label(installed,(-24,54,51),(535,536),"Removable preload bar",218)
label(installed,(-41,36,20),(141,532),"Keyed saddle",144)

off = {"PogoRetainer":(0,-13,0),"J94PinBoard":(0,-7,0),
       **{role:(0,6,0) for role in n if role.startswith("CT") or role=="RevisedContinuousSkin"}}
close = panel("contacts",(48,642,1404,501),"Rear contact stack · exploded",
    "GND, D−, D+ and protected 5 V on 6 mm centers. The Ø2.4 mm stops set 0.60 mm spring travel.",
    (-.10,-1,.05), [role for role in n if role not in ("MetalBody","MotorThermistorCap","PreloadBar")], off,
    [(x,y,z) for x in (-38,25) for y in (1,36) for z in (21,54)])
label(close,(-18,5,42),(90,945),"Wire exit / retainer",193)
label(close,(4,10.9,45.3),(936,791),"Existing J94 pin PCB",209)
label(close,(-34,23.4,32),(93,1055),"Anti-flip key",134)
for center in (-17, -9):
    x,y=close((center,29.4,32))
    svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="none" stroke="#f7d168" stroke-width="2.5"/>')
label(close,(-9,29.4,32),(1061,1038),"Power and Mode access",224)
line(55,1175,"Nominal CAD. Physical fit, contact travel, strain relief and USB remain to be measured.",19,"#48637a")
svg.append("</svg>")
path = HERE / "pc-contact-fixture.svg"
path.write_text("\n".join(svg))
subprocess.run(["rsvg-convert",str(path),"-o",str(HERE/"pc-contact-fixture.png")],check=True)
