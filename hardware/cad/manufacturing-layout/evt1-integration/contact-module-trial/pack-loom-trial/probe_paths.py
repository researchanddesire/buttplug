"""Diagnostic curve sampling; final proof uses native solids and source bodies."""
from pathlib import Path
import json, math
import numpy as np
from scipy.spatial import cKDTree
import sys, importlib
pp=importlib.import_module(sys.argv[1] if len(sys.argv)>1 else "pack_paths")
import curve_utils as c
P = Path(__file__).resolve().parent
plans = pp.interboard()+pp.power()+pp.ntcs()
data = []; summaries = []
for p in plans:
    w = c.path(p['sections']); chk = c.path_checks(w,samples=101)
    sample = []; ods = []
    for sections, od in [(p.get('factory_sections',[]), p.get('factory_OD_mm',p['OD_mm'])), (p['sections'],p['OD_mm'])]:
        for e in c.path(sections).Edges if sections else []:
            pts = e.discretize(Number=max(3,math.ceil(e.Length/.08)+1))
            sample.extend([list(v) for v in pts]); ods.extend([od]*len(pts))
    data.append((p,np.array(sample),np.array(ods)))
    summaries.append(dict(wire=p['name'],length_mm=w.Length,**chk))
bad = []
for i,(p,a,ao) in enumerate(data):
    for q,b,bo in data[i+1:]:
        ds, ix = cKDTree(b).query(a)
        gaps = ds-(ao+bo[ix])/2
        k = int(np.argmin(gaps))
        if gaps[k] < .015:
            bad.append({'a':p['name'],'b':q['name'],'sampled_gap_mm':float(gaps[k]),
                        'a_point_mm':a[k].tolist(),'b_point_mm':b[ix[k]].tolist()})
report={'diagnostic_only':True,'wires':summaries,'near_or_colliding_pairs':bad}
(P/('path-diagnostic-vnext.json' if len(sys.argv)>1 else 'path-diagnostic.json')).write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2),flush=True)
