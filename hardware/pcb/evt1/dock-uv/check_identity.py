"""Full routed geometry/part identity after explicit BASE/LID renaming."""
from pathlib import Path
import hashlib
import json
import re
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=json.loads((HERE/'base/pcb/pcb-checks.json').read_text())
b=json.loads((HERE/'lid/pcb/pcb-checks.json').read_text())
def norm(x):
    if isinstance(x,str):return x.replace('LID','BASE').replace('LOOP_B_RAW','LOOP_A_RAW')
    if isinstance(x,list):return[norm(v)for v in x]
    if isinstance(x,dict):
        out={k:norm(v)for k,v in x.items()}
        if 'reference'in out:out['reference']=re.sub(r'\d+$',lambda m:str(int(m.group())-100),out['reference'])
        return out
    return x
canonical=lambda rows:sorted(json.dumps(v,sort_keys=True)for v in rows)
assert canonical(a['routes'])==canonical(norm(b['routes']))
assert canonical(a['placements'])==canonical(norm(b['placements']))
result={'status':'pass: complete routed geometry and selected placements identical after net/ref normalization',
    'routes_compared':len(a['routes']),'positions_compared':len(a['placements']),
    'source_checks_sha256':{side:sha(HERE/side/'pcb/pcb-checks.json')for side in('base','lid')},
    'checker_sha256':sha(Path(__file__)),'physical_fit':False}
(HERE/'pcb-identity.json').write_text(json.dumps(result,indent=2)+'\n')
print(result['status'])
