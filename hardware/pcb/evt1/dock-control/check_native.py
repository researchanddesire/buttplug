"""Sequential native KiCad exports/ERC plus independent terminal/footprint checks."""
from pathlib import Path
import argparse,datetime,hashlib,json,subprocess,sys,xml.etree.ElementTree as ET
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import kicad_sexp as s
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def sources():
 return{str(p.relative_to(HERE)):sha(p)for p in sorted(HERE.rglob('*'))if p.is_file()and(p.suffix in('.kicad_sch','.kicad_sym','.kicad_pro','.kicad_mod')or p.name in('sym-lib-table','fp-lib-table','build_source.py','check_native.py','circuit-parts.json','pin-contract.json','parts-selection.json'))}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--kicad-cli',required=True);args=ap.parse_args();cli=args.kicad_cli
 version=subprocess.check_output([cli,'--version'],text=True).strip();assert int(version.split('.')[0])>=10
 before=sources();manifest=json.loads((HERE/'circuit-parts.json').read_text());runs=[];findings={};native={}
 names=['dock-controller','dock-lid-ui','dock-control']
 for name in names:
  project=json.loads((HERE/(name+'.kicad_pro')).read_text());assert project['erc']['erc_exclusions']==[]
  for suffix,cmd in [('xml',['sch','export','netlist','--format','kicadxml','-o',str(HERE/(name+'-native.xml')),str(HERE/(name+'.kicad_sch'))]),('erc',['sch','erc','--format','json','--exit-code-violations','-o',str(HERE/(name+'-erc.json')),str(HERE/(name+'.kicad_sch'))])]:
   r=subprocess.run([cli]+cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
   (HERE/(name+'-'+suffix+'.log')).write_text(r.stdout);runs.append({'name':name,'phase':suffix,'returncode':r.returncode})
  erc=json.loads((HERE/(name+'-erc.json')).read_text());findings[name]=[v for sheet in erc['sheets']for v in sheet['violations']]
  assert erc['kicad_version']==version and erc['included_severities']==['error','warning']
  xml=ET.parse(HERE/(name+'-native.xml')).getroot();nets={};pins={}
  for net in xml.findall('./nets/net'):
   for node in net.findall('node'):nets[(node.get('ref'),node.get('pin'))]=net.get('name');pins[(node.get('ref'),node.get('pin'))]=node.attrib
  native[name]=(xml,nets,pins)
 print(json.dumps({'runs':runs,'ERC_findings':{n:[{'type':v['type'],'severity':v['severity'],'items':[i['description']for i in v['items']]}for v in vs]for n,vs in findings.items()}},indent=2))
 expected={p['ref']:p for p in manifest['generated_pin_manifest']if p['assembly_domain']!='ANNOTATION'}
 combined=native['dock-control'];checks=[]
 for ref,item in expected.items():
  for pin,p in item['pins'].items():
   actual=combined[1].get((ref,pin));want=p['net']
   if want is None:assert actual is None or actual.startswith('unconnected-'),(ref,pin,want,actual)
   else:assert actual==want,(ref,pin,want,actual)
   checks.append({'reference':ref,'pin':pin,'expected':want,'native':actual})
 for name in names[:2]:
  for ref,item in expected.items():
   if item['sheet']!=name:continue
   for pin,p in item['pins'].items():assert native[name][1].get((ref,pin))==combined[1].get((ref,pin)),(name,ref,pin)
 components={c.get('ref'):c for c in combined[0].findall('./components/comp')}
 footprint_checks=[]
 for row in manifest['parts']:
  ref=row['reference']
  if row['item_type']=='annotation':continue
  assert ref in components,ref
  fields={f.get('name'):f.text for f in components[ref].findall('./fields/field')}
  assert fields.get('MPN')==row['mpn'],(ref,fields)
  if row['footprint']:
   fpfile=HERE/'DockControl.pretty'/(row['footprint'].split(':')[1]+'.kicad_mod');assert fpfile.exists(),fpfile
   tree=s.parse(fpfile.read_text());pads={p[1].value for p in s.children(tree,'pad')if p[1].value}
   expected_pins=set(expected[ref]['pins'])
   assert pads==expected_pins,(ref,pads,expected_pins)
   footprint_checks.append({'ref':ref,'source':fpfile.name,'unique_pad_numbers':sorted(pads),'sha256':sha(fpfile)})
 lid_context=findings['dock-lid-ui']
 assert len(lid_context)==2 and all(v['type']=='power_pin_not_driven'for v in lid_context),lid_context
 assert not findings['dock-control'] and not findings['dock-controller'],'Native ERC findings remain; see reports'
 assert all(r['returncode']==0 or (r['name']=='dock-lid-ui' and r['phase']=='erc' and r['returncode']==5)for r in runs)
 assert sources()==before,'Sources changed during checks'
 reports={str(p.name):sha(p)for p in sorted(HERE.glob('*-native.xml'))};reports.update({str(p.name):sha(p)for p in sorted(HERE.glob('*-erc.json'))})
 out={'status':'pass: native controller/lid-UI schematic terminal and selected-footprint checks','checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'kicad_version':version,'source_sha256':before,'reports_sha256':reports,'schematics':names,'ERC_errors':0,'ERC_warnings':0,'ERC_exclusions':[],'standalone_lid_power_context':lid_context,'terminal_count':len(checks),'native_terminal_checks':checks,'selected_footprint_checks':footprint_checks,'scope':'Controller and lidUI only; sourcepower/safety/UV sibling circuits need full-system integration. No layout/routing/powered result.','physical_mating_qualified':False,'full_product_order_ready':False}
 (HERE/'native-checks.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:out[k]for k in('status','kicad_version','terminal_count','ERC_errors','ERC_warnings','full_product_order_ready')},indent=2))
if __name__=='__main__':main()
