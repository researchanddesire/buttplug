import FreeCAD as App, Part, json, os, hashlib
root='/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board'
def stage(text):
    with open(root+'/build/mech/saved-icon-stage.log','a') as f:f.write(text+'\n')
try:
    stage('opening skin native')
    d=App.openDocument(root+'/mech/FlangeSkin.FCStd')
    stage('skin native restored')
    pocket=d.getObject('IconDeboss'); profile=d.getObject('RDIconProfile')
    assert pocket is not None and profile is not None and profile.GeometryCount==184
    assert pocket.Shape.isValid() and len(pocket.Shape.Solids)==1
    assert abs(pocket.Length.Value-.25)<1e-8
    sh=Part.Shape(); sh.read(root+'/mech/FlangeSkin.step')
    assert sh.isValid() and len(sh.Solids)==1
    assert abs(sh.Volume-pocket.Shape.Volume)<.01
    stage('skin native and STEP checked')
    App.closeDocument(d.Name)
    stage('opening assembly native')
    asm=App.openDocument(root+'/mech/compass-device.FCStd')
    stage('assembly native restored')
    seals=[o for o in asm.Objects if o.TypeId=='App::Link' and o.Label=='CapFaceSeal']
    assert len(seals)==1
    seal=seals[0].getLinkedObject()
    assert os.path.realpath(seal.Document.FileName)==root+'/mech/CapFaceSeal.FCStd'
    assert seal.Shape.isValid() and len(seal.Shape.Solids)==1
    candidates=list(asm.getObjectsByLabel('FlangeSkin'))
    visited=set(); skins=[]
    while candidates:
        o=candidates.pop()
        if o.Name in visited:continue
        visited.add(o.Name)
        if hasattr(o,'Shape') and not o.Shape.isNull() and abs(o.Shape.Volume-sh.Volume)<.01:skins.append(o)
        candidates.extend(o.OutList)
    stage('assembly seal link and stamped skin checked')
    assert skins and any(o.Shape.isValid() and len(o.Shape.Solids)==1 for o in skins)
    report=json.load(open(root+'/mech/skin-icon.json'))
    report['saved_native_reopened']=True
    report['saved_step_volume_mm3']=round(sh.Volume,6)
    report['assembly_saved_native_reopened']=True
    report['assembly_stamped_skin_present']=True
    report['assembly_nose_seal_link']=seal.Document.FileName
    report['assembly_source_sha256']=hashlib.sha256(open(root+'/mech/device_assembly.py','rb').read()).hexdigest()
    with open(root+'/mech/skin-icon.json','w') as f:json.dump(report,f,indent=2);f.write('\n')
    # Exact same skin oriented like the owner's image: buttons at top,
    # contacts down the left; this is a view export only.
    turned=sh.copy();turned.rotate(App.Vector(),App.Vector(0,1,0),90)
    turned.exportBrep(root+'/build/mech/skin-icon-owner-view.brep')
    with open(root+'/build/mech/saved-icon-check.log','w') as f:json.dump(report,f,indent=2);f.write('\nOK\n')
except Exception:
    import traceback
    with open(root+'/build/mech/saved-icon-check.log','w') as f:f.write(traceback.format_exc())
finally:os._exit(0)
