"""Read saved actual geometry; exact distance separation and BRep contact checks."""
from pathlib import Path
import importlib.util,json,hashlib
R=Path(__file__).resolve().parents[6];spec=importlib.util.spec_from_file_location('m',R/'tools/build_evt1_flange_contact_module.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);P=m.OUT;A=m.App;V=m.V;Part=m.Part
# Do not use a surface-only separation shortcut on a contained solid.
a=Part.makeBox(1,1,1,V(.5,.5,.5));b=Part.makeBox(2,2,2);assert a.distToShape(b)[0]<1e-9 and m.volume_common(a,b)>.999
assert m.volume_common(a,Part.makeBox(1,1,1,V(4,0,0)))==0
N=P/'SingleFlangeBoardTrial.FCStd';d=A.openDocument(str(N));src=m.source()
mapnames={'FlangePCB':'ActualNativeFlangePCB','RearHalf':'ProposedRearHalf','Tray':'ProposedFlangeTray','ButtonDiaphragm':'PermanentSixOpeningDiaphragm','ContinuousSkin':'RevisedContinuousSkin','FaceMask':'ContactMoldingFaceMask','Switch0':'OmronB3U1000P_0','Switch1':'OmronB3U1000P_1'}
for name in ['BoardScrew'+str(i)for i in range(4)]+['IntegralSiliconeBoss'+str(i)for i in range(2)]+['DiaphragmMoldA','DiaphragmMoldB','MovedSteelKeeper0','MovedSteelKeeper1']+['Contact_'+n for n in m.NETS]:mapnames[name]=name
ps={k:d.getObject(n)for k,n in mapnames.items()};assert all(ps.values())
jp,data=m.active_mcaddata();assert m.sha(R/data['native_board'])==data['board_sha256'];actual={'json_path':str(jp.relative_to(R)),'json_sha256':m.sha(jp),'board_sha256':data['board_sha256'],'STEP_sha256':data['native_KiCad_STEP_sha256'],'finished_board_STEP':data['finished_board_local_STEP'],'finished_board_STEP_sha256':data['finished_board_local_STEP_sha256'],'parts':[],'shapes':{},'group':d.getObject('Actual39PositionPCBA')}
for c in data['components']:
 assert m.sha(R/c['model'])==c['model_sha256'];g=d.getObject('Actual_'+c['ref']);q=Part.makeCompound([o.Shape for o in g.Group if o.TypeId=='PartDesign::Body']);assert q.isValid();actual['shapes'][c['ref']]=q;actual['parts'].append({'ref':c['ref'],'source':c['model'],'sha256':c['model_sha256'],'solid_count':len(q.Solids),'volume_mm3':q.Volume,'bounds_mm':m.bnd(q),'model_to_product':c['model_to_product_matrix4']})
# Freeze visibility once; this is the final source used by the snapshot/checks.
for o in d.Objects:
 if o.Name in ('SingleFlangePCB','ContactMoldingFaceMask','DiaphragmMoldA','DiaphragmMoldB')or o.Name.startswith(('Contact_','OmronB3U1000P_','IntegralSiliconeBoss')):o.Visibility=False
ps['RearHalf'].Visibility=False;native_sha=m.sha(N)
# Root-ready portable nine-body exterior; no transitive external document links.
out=P/'exterior';ex=out/'SingleFlangeExterior.FCStd';assert m.sha(ex)=='4b9471fea1af7ace656350d1bc001c665d675ac7fe8014103637b7c204a3b7c5'
assert json.loads((out/'source-binding.json').read_text())['mechanical_native_sha256']==native_sha
print('EXTERIOR_READY',m.sha(ex),flush=True)
r=json.loads((P/'review-mechanical.json').read_text());assert r['sources']['product_sha256']==m.SOURCE_SHA
for entry in r['native_bodies']:
 q=ps[entry['name']].Shape;assert abs(q.Volume-entry['volume_mm3'])<1e-5;assert max(abs(a-b)for a,b in zip(m.bnd(q),entry['bounds_mm']))<1e-5
r['mechanical_source_native_sha256']=native_sha;print('MECHANICAL_CHECKS_REUSED_UNCHANGED_GEOMETRY',flush=True)
r['new_routed_PCB']='single-flange-routing' in str(jp);r['actual_PCBA']=m.check_actual_pcba(ps,actual,src);r['separation_precheck']='optimal native bounds and exact OCCT solid distance>1um; contained-solid benchmark passed; native BRep common for contact/interference';(P/'review.json').write_text(json.dumps(r,indent=2)+'\n');print('PCBA_CHECKS_DONE',flush=True)
for k in('FlangePCB','RearHalf','Tray','FaceMask','Contact_GND','ContinuousSkin','ButtonDiaphragm','DiaphragmMoldA','DiaphragmMoldB'):ps[k].Tip.Shape.exportStep(str(P/(k+'.step')))
print(json.dumps({'native_sha256':native_sha,'hard_clashes':r['source_hard_clashes'],'case_overlap':r['closed_rigid_halves_common_mm3'],'PCBA_clashes':r['actual_PCBA']['hard_clashes'],'package_pair_clashes':r['actual_PCBA']['actual_package_pair_clashes'],'loading_failures':sum(bool(x['collisions'])for x in r['actual_PCBA']['whole_PCBA_loading']),'closing_failures':sum(bool(x['collisions'])for x in r['actual_PCBA']['whole_PCBA_closing'])},indent=2),flush=True)
