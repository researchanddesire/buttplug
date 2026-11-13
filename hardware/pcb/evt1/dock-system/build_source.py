"""Assemble source-bound dock leaf snapshots into one reviewable native project.

Sibling schematics remain authoring sources. Project-instance paths are added
and redundant standalone supply flags removed where real drivers now exist.
All functional components and terminal nets are preserved.
Native full-system ERC and terminal comparison are separate checks.
"""
from pathlib import Path
import hashlib
import json
import sys
import uuid

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
BASE=HERE.parent
sys.path.insert(0,str(ROOT/'tools'))
import kicad_sexp as s

PROJECT='dock-system'
NS=uuid.UUID('0a3a6c39-8d84-48f4-a053-365c1e67cd41')
uid=lambda value:str(uuid.uuid5(NS,value))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
q=lambda value:json.dumps(str(value),ensure_ascii=False)
CONTEXT_FLAGS={
    'dock-controller':{'#FLG201','#FLG202'},
    'dock-safety':{'#FLG601','#FLG602','#FLG603','#FLG604'},
    'dock-uv-base':{'#FLG400','#FLG401','#FLG402'},
    'dock-uv-lid':{'#FLG500','#FLG501','#FLG502'},
}


def main():
    sources=[BASE/'dock-ui/dock-ui-source.kicad_sch',
             BASE/'dock-control/dock-controller.kicad_sch',
             BASE/'dock-control/dock-lid-ui.kicad_sch',
             BASE/'dock-safety/dock-safety.kicad_sch']
    uv=sorted(p for p in (BASE/'dock-uv').rglob('*.kicad_sch')
              if p.stem in ('dock-uv-base','dock-uv-lid'))
    assert len(uv)==2,'Both authored UV module sheets are required'
    sources+=uv
    (HERE/'sheets').mkdir(exist_ok=True)
    root_id=uid(PROJECT)
    sheets=[]
    inputs={}
    for source in sources:
        assert source.is_file(),source
        inputs[str(source.relative_to(ROOT))]=sha(source)
        tree=s.parse(source.read_text())
        assert not s.children(tree,'sheet'),'Expected leaf source '+str(source)
        removed=[];removed_uuids=[]
        for symbol in list(s.children(tree,'symbol')):
            ref=s.prop(symbol,'Reference')
            if ref in CONTEXT_FLAGS.get(source.stem,set()):
                assert s.prop(symbol,'Footprint') in ('',None),ref
                libid=s.value(symbol,'lib_id')
                lib=next(v for v in s.children(s.child(tree,'lib_symbols'),'symbol')if v[1].value==libid)
                pins=[p for section in s.children(lib,'symbol')for p in s.children(section,'pin')]
                assert len(pins)==1 and pins[0][1].value=='power_out',ref
                at=s.child(symbol,'at');pat=s.child(pins[0],'at')
                assert float(at[3].value)==0,ref
                pinxy=(round(float(at[1].value)+float(pat[1].value),4),round(float(at[2].value)-float(pat[2].value),4))
                coords=lambda point:tuple(round(float(v.value),4)for v in point[1:3])
                wires=[w for w in s.children(tree,'wire')if pinxy in [coords(p)for p in s.children(s.child(w,'pts'),'xy')]]
                assert len(wires)==1,ref
                wire=wires[0];ends=[coords(p)for p in s.children(s.child(wire,'pts'),'xy')]
                other=next(p for p in ends if p!=pinxy)
                labels=[v for v in s.children(tree,'global_label')if coords(s.child(v,'at'))==other]
                assert len(labels)==1,ref
                for node in (symbol,wire,labels[0]):
                    removed_uuids.append(s.value(node,'uuid'));tree.remove(node)
                removed.append(ref)
        assert set(removed)==CONTEXT_FLAGS.get(source.stem,set())
        instance=uid(source.stem)
        refs=[]
        for symbol in s.children(tree,'symbol'):
            ref=s.prop(symbol,'Reference')
            refs.append(ref)
            instances=s.child(symbol,'instances')
            assert instances is not None,(source,ref)
            original=next(iter(s.children(instances,'project')))
            original_path=s.child(original,'path')
            unit=s.value(original_path,'unit') or '1'
            # Preserve original project instances. Add this combined owner's
            # path without touching any source electrical content.
            instances[:]=[node for node in instances
                          if not(isinstance(node,list) and s.tag(node)=='project'
                                 and node[1].value==PROJECT)]
            instances.append(s.parse(f'(project {q(PROJECT)}(path {q("/"+root_id+"/"+instance)}(reference {q(ref)})(unit {unit})))'))
        destination=HERE/'sheets'/source.name
        s.write(destination,tree)
        sheets.append({'source':str(source.relative_to(ROOT)),
                       'snapshot':str(destination.relative_to(HERE)),
                       'snapshot_sha256':sha(destination),
                       'instance_uuid':instance,'references':refs,
                       'standalone_context_flags_removed':removed,
                       'standalone_context_node_uuids_removed':removed_uuids})

    effects='(effects(font(size 1.27 1.27))(justify left top))'
    top=[f'(kicad_sch(version 20230121)(generator build_evt1_dock_system)(uuid {root_id})(paper "A3")',
         '(title_block(title "EVT dock / complete circuit integration candidate")(date "2026-11-12")(rev "EVT1")(company "Research and Desire")(comment 1 "NATIVE CIRCUITS / LAYOUT AND POWERED VALIDATION REQUIRED"))',
         '(lib_symbols)',
         f'(text "Combined source power, controller, lid UI, independent safety and two UV drivers.\\nDerived leaf snapshots preserve electrical source; edit sibling source projects and regenerate.\\nNo routed-board, powered or optical result follows from this schematic."(at 25.4 20.32 0){effects}(uuid {uid("scope")}))',
         '(sheet_instances(path "/"(page "1")))']
    for i,item in enumerate(sheets):
        x=25.4+(i%2)*132.08;y=76.2+(i//2)*63.5
        top.append(f'(sheet(at {x} {y})(size 99.06 25.4)(fields_autoplaced)(stroke(width .1524)(type default))(fill(color 0 0 0 0))(uuid {item["instance_uuid"]})(property "Sheetname" {q(Path(item["source"]).stem)}(at {x} {y-.508} 0){effects})(property "Sheetfile" {q(item["snapshot"])}(at {x} {y+25.908} 0){effects}))')
    top.append(')')
    s.write(HERE/(PROJECT+'.kicad_sch'),s.parse('\n'.join(top)+'\n'))
    libraries=sorted({s.prop(o,'Footprint').split(':')[0]
                      for p in sources for o in s.children(s.parse(p.read_text()),'symbol')
                      if s.prop(o,'Footprint')})
    # Each leaf owns a distinct namespace and its attributed local geometry.
    mapping={}
    for folder in sorted({p.parent for p in sources}):
        for table in ('sym-lib-table','fp-lib-table'):
            path=folder/table
            if not path.exists():continue
            inputs[str(path.relative_to(ROOT))]=sha(path)
            for lib in s.children(s.parse(path.read_text()),'lib'):
                alias=s.value(lib,'name');uri=s.value(lib,'uri')
                resolved=Path(uri.replace('${KIPRJMOD}',str(folder))).resolve()
                assert resolved.exists(),resolved
                # Bind only the libraries named by this authoring leaf's
                # tables. Derived routed-board folders beneath a leaf are
                # independent outputs and must not become schematic inputs.
                library_files=sorted(resolved.rglob('*.kicad_mod')) if resolved.is_dir() else [resolved]
                for file in library_files:
                    assert file.is_file(),file
                    inputs[str(file.relative_to(ROOT))]=sha(file)
                entry=(table,alias)
                if entry in mapping and mapping[entry]!=resolved:
                    prior=mapping[entry]
                    if resolved.is_dir() and prior.is_dir():
                        inventory=lambda folder:{str(p.relative_to(folder)):sha(p)for p in folder.rglob('*')if p.is_file()}
                        assert inventory(prior)==inventory(resolved),entry
                    else:
                        assert resolved.is_file() and prior.is_file() and sha(prior)==sha(resolved),entry
                else:
                    mapping[entry]=resolved
    for table,kind in [('sym-lib-table','KiCad'),('fp-lib-table','KiCad')]:
        root='sym_lib_table' if table=='sym-lib-table' else 'fp_lib_table'
        # KiCad's table-type sniffer requires whitespace after the root token,
        # even though the generic S-expression parser accepts adjacent parens.
        rows=[f'({root} (version 7)']
        for (key,alias),path in sorted(mapping.items()):
            if key!=table:continue
            relative=Path(__import__('os').path.relpath(path,HERE)).as_posix()
            rows.append(f'(lib(name {q(alias)})(type {q(kind)})(uri {q("${KIPRJMOD}/"+relative)})(options "")(descr "Source-owned dock component library"))')
        rows.append(')');s.write(HERE/table,s.parse('\n'.join(rows)+'\n'))
    assert set(libraries)<={key[1]for key in mapping if key[0]=='fp-lib-table'}
    (HERE/(PROJECT+'.kicad_pro')).write_text(json.dumps({'meta':{'filename':PROJECT+'.kicad_pro','version':1},'erc':{'erc_exclusions':[]}},indent=2)+'\n')
    manifest={'status':'derived full-system circuit candidate; native checks required',
              'functional_terminal_changes':False,
              'context_annotation_changes':'Remove12 redundant standalone supply flags where connected real drivers exist; retain analog/UI flags behind zero-ohm links.',
              'inputs_sha256':inputs,
              'builder_sha256':sha(Path(__file__)),'sheets':sheets,
              'full_product_order_ready':False}
    (HERE/'source-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Combined',len(sheets),'source-bound circuit sheets')


if __name__=='__main__':main()
