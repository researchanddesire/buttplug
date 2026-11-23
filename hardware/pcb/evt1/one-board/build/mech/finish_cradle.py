from pathlib import Path
import os,sys,json,hashlib,subprocess,shutil
r=Path('/Users/lucianchapar/Backplane/buttplug-compass/hardware/pcb/evt1/one-board')
os.chdir(r)
fc='/Applications/FreeCAD.app/Contents/MacOS/FreeCAD'
fcc='/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd'
env=os.environ.copy();env['QT_QPA_PLATFORM']='offscreen'
def run(cmd):
 subprocess.run(cmd,check=True,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=300)
run([fcc,'-c',"exec(open('build/mech/cradle-independent-check.py').read())"])
a=json.loads((r/'build/mech/cradle-independent-report.json').read_text())
assert all(hashlib.sha256((r/'mech'/(n+'.step')).read_bytes()).hexdigest()==h for n,h in a['inputs_sha256'].items())
assert all(not v.get('hits') for v in a['checks'].values() if isinstance(v,dict))
shutil.copy2(r/'build/mech/cradle-independent-report.json',r/'mech/cradle-installation-fit.json')
run([fc,'mech/internals.py'])
j=json.loads((r/'mech/internals-fit.json').read_text());assert not j['overlaps']
run([fc,'mech/device_assembly.py'])
j=json.loads((r/'mech/device-fit.json').read_text());assert not j['hard_part_overlaps'] and not j['internals']['overlaps']
run([fcc,'-c',"exec(open('build/mech/cradle_final_readback.py').read())"])
assert json.loads((r/'mech/cradle-saved-readback.json').read_text())['pass']
run(['/Users/lucianchapar/.local/share/backplane/builds/v0.16.4/backplane-hub','--render','mech/compass-device-cutaway.step','mech/compass-internal-module.step','build/mech/cradle-exploded.step'])
for n in ['InternalCradle','CradleWireGuide']:
 assert json.loads((r/'build/mech/cradle-print'/(n+'-mesh.json')).read_text())['watertight']
print('PASS: source-bound installation sweep, guided wires, linked assembly readback, printable meshes and renders.',flush=True)
