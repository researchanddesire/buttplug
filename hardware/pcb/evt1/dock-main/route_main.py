"""Offline router exchange retaining all selected footprints and locked copper.

No GUI session importer is used. Only supported SES wire/via records become
native copper. In1 ground remains unavailable to signal routing. In2 low-speed
routes may share the separated native power regions, which are refilled later.
"""
from pathlib import Path
import argparse,hashlib,json,math,re,shutil,sys
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;ROOT=H.parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import kicad_sexp as s
P=H/'dock-main.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def point(x,y):return k.VECTOR2I(round(float(x)*100),round(-float(y)*100))
def close(a,b):return (a-b).EuclideanNorm()<=200 # explicit0.2um SES roundtrip bound
def export(prefix,critical_only=False,residual_report=None):
 meta=json.loads((H/'placement.json').read_text());assert sha(P)==meta['native_board_sha256']
 assert meta.get('routing_started');b=k.LoadBoard(str(P))
 folder=H/'routing';folder.mkdir(exist_ok=True);dsn=folder/(prefix+'.dsn')
 scope=None;complete=set();retained=[]
 if residual_report:
  report=H/residual_report;d=json.loads(report.read_text())
  scope={re.search(r'\[([^]]+)\]',item['description'])[1]for row in d['unconnected_items']for item in row['items']}
  assert scope,'No native residual nets remain'
  allnets={q.GetNetname()for f in b.GetFootprints()for q in f.Pads()if q.GetNetname()}
  complete=allnets-scope
  for item in b.GetTracks():
   if item.GetNetname()in complete:
    retained.append(item.m_Uuid.AsString());item.SetLocked(True) # exchange only

 # Surface ground pours are restored/refilled natively. They must not stand
 # in for real ground connectivity during general routing.
 for z in list(b.Zones()):
  if not z.GetIsRuleArea() and not z.IsOnLayer(k.In1_Cu):b.Delete(z)
 omitted=0
 if critical_only:
  # Keep full native checkpoints, but do not feed a pathological prior
  # general-route normalization graph back into this offline search.
  for t in list(b.GetTracks()):
   if not t.IsLocked():b.Delete(t);omitted+=1
 assert k.ExportSpecctraDSN(b,str(dsn))
 raw=dsn.read_text()
 raw=re.sub(r'(\(layer (\S+)\s+\(type )signal(\))',lambda m:m[1]+('power'if m[2]=='In1.Cu'else'signal')+m[3],raw)
 # Place settings after layer declarations and before any plane/keepout.
 # The primary1.9.0 reader resolves active flags against these exact names.
 settings='''(autoroute_settings (fanout off) (autoroute on) (postroute off) (vias on)
      (via_costs 30) (plane_via_costs 5) (start_ripup_costs 100)
      (layer_rule F.Cu (active on) (preferred_direction horizontal))
      (layer_rule In1.Cu (active off) (preferred_direction horizontal))
      (layer_rule In2.Cu (active on) (preferred_direction vertical))
      (layer_rule B.Cu (active on) (preferred_direction vertical)))
    '''
 index=raw.index('(boundary');raw=raw[:index]+settings+raw[index:]
 # Conservative boundary exchange inset; the actual native outline is intact.
 def inset(match):
  values=[float(v)for v in match[1].split()];ps=list(zip(values[::2],values[1::2]))
  if ps[0]==ps[-1]:ps.pop()
  sign=1 if sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(ps,ps[1:]+ps[:1]))>0 else -1
  shifted=[]
  for a,b,c in zip(ps[-1:]+ps[:-1],ps,ps[1:]+ps[:1]):
   u=(b[0]-a[0],b[1]-a[1]);v=(c[0]-b[0],c[1]-b[1]);lu=math.hypot(*u);lv=math.hypot(*v)
   n=(-sign*u[1]/lu,sign*u[0]/lu);m=(-sign*v[1]/lv,sign*v[0]/lv)
   scale=220/(1+n[0]*m[0]+n[1]*m[1]);shifted.append((b[0]+scale*(n[0]+m[0]),b[1]+scale*(n[1]+m[1])))
  return '(boundary (path pcb 0 '+' '.join(f'{q:.3f}'for p in shifted+[shifted[0]]for q in p)+'))'
 raw,count=re.subn(r'\(boundary\s+\(path pcb 0\s+([^()]*)\)\s*\)',inset,raw);assert count==1
 # Carrier opening edges need the same native0.30mm copper separation as
 # the outer edge. Router keepouts otherwise use only ordinary0.15mm spacing.
 def expand_cutout(match):
  values=[float(v)for v in match[1].split()];ps=list(zip(values[::2],values[1::2]))
  if ps[0]==ps[-1]:ps.pop()
  sign=1 if sum(a[0]*b[1]-b[0]*a[1]for a,b in zip(ps,ps[1:]+ps[:1]))>0 else -1;vs=[]
  for a,b,c in zip(ps[-1:]+ps[:-1],ps,ps[1:]+ps[:1]):
   u=(b[0]-a[0],b[1]-a[1]);v=(c[0]-b[0],c[1]-b[1]);lu=math.hypot(*u);lv=math.hypot(*v)
   n=(-sign*u[1]/lu,sign*u[0]/lu);m=(-sign*v[1]/lv,sign*v[0]/lv)
   scale=-200/(1+n[0]*m[0]+n[1]*m[1]);vs.append((b[0]+scale*(n[0]+m[0]),b[1]+scale*(n[1]+m[1])))
  return '(keepout "" (polygon signal 0 '+' '.join(f'{v:.3f}'for p in vs+[vs[0]]for v in p)+'))'
 raw,count=re.subn(r'\(keepout "" \(polygon signal 0\s+([^()]*)\)\)',expand_cutout,raw);assert count==2
 power={'HOST_POWER':(['HOST_5V'],600),'UI_POWER':(['3V3','3V3_ANALOG'],300),
        'LOOP_POWER':(['LOOP_5V','BASE_THERM_SEND','LID_THERM_SEND'],300),
        'UV_POWER':(['UV_5V_LIMITED','UV_5V_MID','UV_5V_SW','CONTACT_5V'],600)}
 begin=raw.index('(class kicad_default');end=raw.index('(circuit',begin);header=raw[begin:end]
 for nets,width in power.values():
  for net in nets:header=re.sub(r'(?<!\S)'+re.escape(net)+r'(?=\s)','',header)
 if scope is not None:
  for net in complete:header=re.sub(r'(?<!\S)'+re.escape(net)+r'(?=\s)','',header)
 raw=raw[:begin]+header+raw[end:]
 index=raw.rfind('\n  )',0,raw.index('\n  (wiring'))
 via=re.search(r'\(via\s+"?(Via\[[^\s)"]+)',raw)[1]
 classes=''
 for name,(nets,width)in power.items():
  if scope is not None:nets=[net for net in nets if net in scope]
  if not nets:continue
  classes+='\n    (class '+name+' '+' '.join(nets)+'\n      (circuit (use_via '+via+'))\n      (rule (width '+str(width)+') (clearance 150.2)))'
 if complete:
  classes+='\n    (class PRESERVED_COMPLETE '+' '.join(json.dumps(n)for n in sorted(complete))+' (circuit (use_via '+via+')) (rule(width 200)(clearance 150.2)))'
 raw=raw[:index]+classes+raw[index:]
 dsn.write_text(raw)
 seed=folder/(prefix+'-seed.kicad_pcb');shutil.copyfile(P,seed)
 info={'input_board_sha256':sha(P),'dsn_sha256':sha(dsn),'seed':seed.name,
       'locked_objects':sum(t.IsLocked()for t in b.GetTracks()),'forbidden_signal_layers':['In1.Cu'],
       'search_from_protected_copper_only':critical_only,'prior_unlocked_items_omitted_from_exchange_only':omitted,
       'router_only_cutout_outset_mm':.2,
       'primary_router_source':'https://github.com/freerouting/freerouting/tree/v1.9.0',
       'cli_analytics_disabled':True,'source_circuit_unchanged':True,'residual_only_target_nets':sorted(scope)if scope is not None else None,'native_DRC_input_sha256':sha(H/residual_report)if residual_report else None,'completed_native_nets_retained_verbatim':sorted(complete),'untargeted_native_copper_UUIDs':retained}
 (folder/(prefix+'-exchange.json')).write_text(json.dumps(info,indent=2)+'\n')
 print('Exported',dsn,sha(dsn))
def import_session(prefix):
 folder=H/'routing';info=json.loads((folder/(prefix+'-exchange.json')).read_text())
 meta=json.loads((H/'placement.json').read_text())
 assert sha(P)==meta['native_board_sha256']==info['input_board_sha256'],'Native board changed after router export'
 assert sha(folder/(prefix+'-seed.kicad_pcb'))==sha(P)
 ses=folder/(prefix+'.ses');root=s.parse(ses.read_text());routes=s.child(root,'routes')
 unit,resolution=[x.value for x in s.child(routes,'resolution')[1:]]
 assert unit in('um','mm','nm')and float(resolution)>0
 conversion={'um':1000,'mm':1e6,'nm':1}[unit]/float(resolution)
 def sespoint(x,y):return k.VECTOR2I(round(float(x)*conversion),round(-float(y)*conversion))
 b=k.LoadBoard(str(P));layers={n:b.GetLayerID(n)for n in('F.Cu','In1.Cu','In2.Cu','B.Cu')}
 # A residual exchange preserves every native item on already-complete nets.
 scope=set(info['residual_only_target_nets'])if info.get('residual_only_target_nets')is not None else None
 for t in list(b.GetTracks()):
  if not t.IsLocked()and(scope is None or t.GetNetname()in scope):b.Delete(t)
 protected=list(b.GetTracks());added=0;skipped=0
 for net in s.children(s.child(routes,'network_out'),'net'):
  name=net[1].value
  if scope is not None and name not in scope:continue
  native=b.FindNet(name);assert native,name
  for item in net[2:]:
   if s.tag(item)=='wire':
    path=s.child(item,'path');layer=layers[path[1].value];width=round(float(path[2].value)*conversion)
    ps=[sespoint(x.value,y.value)for x,y in zip(path[3::2],path[4::2])]
    for a,c in zip(ps,ps[1:]):
     match=next((t for t in protected if not isinstance(t,k.PCB_VIA) and t.GetNetname()==name and t.GetLayer()==layer and
        ((close(t.GetStart(),a)and close(t.GetEnd(),c))or(close(t.GetStart(),c)and close(t.GetEnd(),a)))),None)
     if match:skipped+=1;continue
     assert layer in(k.F_Cu,k.In2_Cu,k.B_Cu),('router tried signal on reserved plane',name,path[1].value)
     t=k.PCB_TRACK(b);t.SetStart(a);t.SetEnd(c);t.SetWidth(width);t.SetLayer(layer);t.SetNet(native);b.Add(t);added+=1
   elif s.tag(item)=='via':
    match=re.fullmatch(r'Via\[0-\d+\]_(\d+):(\d+)_um',item[1].value);assert match,item[1].value
    p=sespoint(item[2].value,item[3].value)
    existing=[t for t in b.GetTracks()if isinstance(t,k.PCB_VIA)and close(t.GetPosition(),p)]
    if existing:
     assert all(t.GetNetname()==name for t in existing);skipped+=1;continue
    v=k.PCB_VIA(b);v.SetPosition(p);v.SetWidth(round(float(match[1])*1000));v.SetDrill(round(float(match[2])*1000))
    v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(native);b.Add(v);added+=1
   else:raise ValueError('Unsupported SES item '+s.tag(item))
 if scope is not None:
  assert set(info['untargeted_native_copper_UUIDs'])<={t.m_Uuid.AsString()for t in b.GetTracks()}
 k.SaveBoard(str(P),b)
 meta['native_board_sha256']=sha(P);meta['general_routing_imported']=True;meta['last_router_prefix']=prefix
 (H/'placement.json').write_text(json.dumps(meta,indent=2)+'\n')
 info.update(ses_sha256=sha(ses),SES_units=unit,SES_resolution=resolution,nm_per_SES_unit=conversion,imported_native_objects=added,protected_duplicates_skipped=skipped,result_board_sha256=sha(P))
 (folder/(prefix+'-exchange.json')).write_text(json.dumps(info,indent=2)+'\n')
 print(json.dumps({'imported_native_objects':added,'protected_duplicates_skipped':skipped,'native_DRC_pending':True}))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('action',choices=['export','import']);ap.add_argument('--prefix',default='main-pass1');ap.add_argument('--critical-only',action='store_true');ap.add_argument('--residual-report');a=ap.parse_args()
 assert re.fullmatch(r'[a-zA-Z0-9_-]+',a.prefix)
 if a.action=='export':export(a.prefix,a.critical_only,a.residual_report)
 else:import_session(a.prefix)
