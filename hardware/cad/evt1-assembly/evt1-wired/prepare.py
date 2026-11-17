from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import sys
from zipfile import ZipFile

repo=Path(sys.argv[1]).resolve()
work=Path(sys.argv[2]).resolve()
board=Path(sys.argv[3]).resolve()
sys.path.insert(0,str(repo/'tools'))
import kicad_sexp as sx


def sha(path):
    return sha256(path.read_bytes()).hexdigest()


def reference(footprint):
    for item in sx.children(footprint,'property'):
        if item[1].value=='Reference':return item[2].value
    for item in sx.children(footprint,'fp_text'):
        if item[1].value=='reference':return item[2].value
    raise RuntimeError('No footprint reference')


packet=repo/'hardware/cad/evt1-assembly/lid-jst-integration/DockAssembly-JST-Review.zip'
with ZipFile(packet) as z:
    for name in z.namelist():
        if name.endswith('.FCStd'):
            z.extract(name,work/'dock')
models={}; unmodeled=[]; uri_map={}
text=board.read_text()
for fp in sx.children(sx.parse(text),'footprint'):
    ref=reference(fp)
    refs=list(sx.children(fp,'model'))
    if not refs:
        unmodeled.append(ref)
        continue
    assert len(refs)==1,(ref,len(refs))
    uri=refs[0][1].value
    path=Path(uri.replace('${KIPRJMOD}',str(board.parent))).resolve()
    assert path.is_file() and path.is_relative_to(repo),(ref,path)
    local_model_path='models/'+path.parent.name+'/'+path.name
    assert uri_map.setdefault(uri,local_model_path)==local_model_path
    dest=work/'kicad'/local_model_path
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():assert sha(dest)==sha(path),(ref,path,dest)
    else:shutil.copyfile(path,dest)
    models[ref]={'model':str(path.relative_to(repo)),'sha256':sha(path),'staged':local_model_path}
assert len(models)==200 and len(unmodeled)==25,(len(models),unmodeled)
replaced,count=re.subn(r'\(model "([^"]+)"',lambda m:'(model "${KIPRJMOD}/'+uri_map[m[1]]+'"',text)
assert count==200
staged=work/'kicad/dock-main-wired.kicad_pcb';staged.write_text(replaced)
record={'pcb':str(board.relative_to(repo)),'pcb_sha256':sha(board),'staged_board_sha256':sha(staged),'reference_archive_sha256':sha(packet),'legacy_assembly_sha256':sha(work/'dock/DockAssembly.FCStd'),'models':models,'unmodeled_copper_or_mounts':sorted(unmodeled),'retained_dependency_hashes':{str(p.relative_to(work/'dock')):sha(p) for p in sorted((work/'dock').glob('*/*.FCStd')) if p.name!='MainPCB.FCStd'}}
(work/'inputs.json').write_text(json.dumps(record,indent=2)+'\n')
