"""Offline DSN/SES exchange: preserve locked copper and ignore placement records."""
from pathlib import Path
import argparse,hashlib,json,re,shutil,sys
import wx
APP=wx.App(False)
import pcbnew as k
H=Path(__file__).resolve().parent;ROOT=H.parents[3];sys.path.insert(0,str(ROOT/'tools'));import kicad_sexp as s
P=H/'single-flange.kicad_pcb';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def close(a,b):return(a-b).EuclideanNorm()<=200

def export(prefix):
 m=json.loads((H/'pcb-state.json').read_text());assert sha(P)==m['board_sha256']and m['routing_started'];b=k.LoadBoard(str(P));folder=H/'routing';folder.mkdir(exist_ok=True)
 for z in list(b.Zones()):
  if not z.GetIsRuleArea()and not z.IsOnLayer(k.In1_Cu):b.Delete(z)
 dsn=folder/(prefix+'.dsn');assert k.ExportSpecctraDSN(b,str(dsn));raw=dsn.read_text()
 raw=re.sub(r'(\(layer (\S+)\s+\(type )signal(\))',lambda a:a[1]+('power'if a[2]=='In1.Cu'else'signal')+a[3],raw)
 settings='''(autoroute_settings (fanout off) (autoroute on) (postroute off) (vias on)
 (via_costs 20) (plane_via_costs 3) (start_ripup_costs 100)
 (layer_rule F.Cu (active on) (preferred_direction horizontal))
 (layer_rule In1.Cu (active off) (preferred_direction horizontal))
 (layer_rule In2.Cu (active on) (preferred_direction horizontal))
 (layer_rule B.Cu (active on) (preferred_direction vertical)))\n'''
 index=raw.index('(boundary');raw=raw[:index]+settings+raw[index:];dsn.write_text(raw);seed=folder/(prefix+'-seed.kicad_pcb');shutil.copyfile(P,seed)
 r={'board_sha256':sha(P),'DSN_sha256':sha(dsn),'fixed_copper_UUIDs':[t.m_Uuid.AsString()for t in b.GetTracks()if t.IsLocked()],'reserved_signal_layer':'In1.Cu','signal_layers':['F.Cu','In2.Cu','B.Cu'],'placement_records_imported':False,'native_outline_unchanged':True,'only_In1_reference_plane_in_exchange':True};(folder/(prefix+'-exchange.json')).write_text(json.dumps(r,indent=2)+'\n');print('Exported',dsn)

def import_ses(prefix):
 folder=H/'routing';meta=json.loads((H/'pcb-state.json').read_text());info=json.loads((folder/(prefix+'-exchange.json')).read_text());assert sha(P)==meta['board_sha256']==info['board_sha256'];project=H/'single-flange.kicad_pro';pro=project.read_bytes();r=s.parse((folder/(prefix+'.ses')).read_text());routes=s.child(r,'routes');unit,res=[q.value for q in s.child(routes,'resolution')[1:]];factor={'um':1000,'mm':1e6,'nm':1}[unit]/float(res);point=lambda x,y:k.VECTOR2I(round(float(x)*factor),round(-float(y)*factor));b=k.LoadBoard(str(P))
 for t in list(b.GetTracks()):
  if not t.IsLocked():b.Delete(t)
 fixed=list(b.GetTracks());added=0;skipped=0
 for net in s.children(s.child(routes,'network_out'),'net'):
  name=net[1].value;native=b.FindNet(name);assert native,name
  for item in net[2:]:
   if s.tag(item)=='wire':
    path=s.child(item,'path');layer=b.GetLayerID(path[1].value);assert layer in(k.F_Cu,k.In2_Cu,k.B_Cu),('signal on reserved plane',name);width=round(float(path[2].value)*factor);ps=[point(x.value,y.value)for x,y in zip(path[3::2],path[4::2])]
    for a,c in zip(ps,ps[1:]):
     duplicate=next((t for t in fixed if not isinstance(t,k.PCB_VIA)and t.GetNetname()==name and t.GetLayer()==layer and((close(t.GetStart(),a)and close(t.GetEnd(),c))or(close(t.GetStart(),c)and close(t.GetEnd(),a)))),None)
     if duplicate:skipped+=1;continue
     t=k.PCB_TRACK(b);t.SetStart(a);t.SetEnd(c);t.SetWidth(width);t.SetLayer(layer);t.SetNet(native);b.Add(t);added+=1
   elif s.tag(item)=='via':
    spec=re.fullmatch(r'Via\[0-\d+\]_(\d+):(\d+)_um',item[1].value);assert spec,item[1].value;pos=point(item[2].value,item[3].value);existing=[t for t in b.GetTracks()if isinstance(t,k.PCB_VIA)and close(t.GetPosition(),pos)]
    if existing:assert all(t.GetNetname()==name for t in existing);skipped+=1;continue
    v=k.PCB_VIA(b);v.SetPosition(pos);v.SetWidth(round(float(spec[1])*1000));v.SetDrill(round(float(spec[2])*1000));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(native);b.Add(v);added+=1
   else:raise ValueError('Unsupported SES copper '+s.tag(item))
 assert set(info['fixed_copper_UUIDs'])<={t.m_Uuid.AsString()for t in b.GetTracks()};k.SaveBoard(str(P),b);project.write_bytes(pro);meta['board_sha256']=sha(P);meta['general_routing_imported']=True;meta['last_router_prefix']=prefix;(H/'pcb-state.json').write_text(json.dumps(meta,indent=2)+'\n');info.update(result_board_sha256=sha(P),SES_sha256=sha(folder/(prefix+'.ses')),SES_unit=unit,SES_resolution=res,nm_per_SES_unit=factor,added_native_copper=added,protected_duplicates_skipped=skipped);(folder/(prefix+'-exchange.json')).write_text(json.dumps(info,indent=2)+'\n');print('Imported',added,'copper objects; placement ignored')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['export','import']);p.add_argument('--prefix',default='pass1');a=p.parse_args();assert re.fullmatch(r'[A-Za-z0-9_-]+',a.prefix)
 if a.action=='export':export(a.prefix)
 else:import_ses(a.prefix)
