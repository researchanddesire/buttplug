"""Engineering estimate from native copper sheets and explicit neck/via paths.

Not a measured resistance or a fabricator guarantee. Contact fractions use the
unit sheet-current trial flow; every barrel is conservatively full board height.
Surface trace widths include a separate20% process-loss sensitivity. The3mOhm
reserve is an engineering allowance, not a proven bound on discretization or
plating/annulus spreading. Actual hot/aged complete paths must meet50mOhm.
"""
from pathlib import Path
import argparse,hashlib,json,math
H=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=argparse.ArgumentParser();a.add_argument('--label',required=True);a=a.parse_args();folder=H/'power-study'/a.label;g=json.loads((folder/'grid-0.125.json').read_text());grids={x['name']:x for x in g['grids']};solutions={}
for name,row in grids.items():
 assert sha(folder/row['file'])==row['sha256'];solution=json.loads((folder/(name+'-solve.json')).read_text());assert solution['relative_residual']<1e-8
 def fractions(kind):
  flux=dict(solution[kind+'_current_fractions']);values=[sum(flux.get(cell,0)for cell in cells)for cells in row[('feed'if kind=='source'else'sink')+'_cell_groups']];assert abs(sum(values)-1)<1e-6;return values
 solution['feed_via_current_fractions']=fractions('source');solution['sink_via_current_fractions']=fractions('sink');solutions[name]=solution
rho20=1.7241e-5;alpha=.0039;temp=85;rho=rho20*(1+alpha*(temp-20));copper=.035;sheet=rho/copper
# Values below are selected endpoints in the protected source/critical records.
source=json.loads((H/'source-block/placement.json').read_text())['critical_copper'];critical=json.loads((H/'critical-routing.json').read_text())['critical_copper']
def length(row):return math.dist(row['start'],row['end'])
def squares(role,net=None):
 rows=[r for r in source+critical if r['kind']=='track'and r['role']==role and(net is None or r['net']==net)];assert rows,role
 return sum(length(r)/r['width']for r in rows)
fixed_squares={role:squares(role)for role in('UV limiter input loop','UV limiter input access','UV limited export','UV cut input trunk','cut A input neck','cut A output neck','two cut local link','cut B input neck','cut B output neck')}
# The limiter input loop/access are both HOST copper, the rest are UV copper.
fixed_F=sum(fixed_squares.values())*sheet
cases=[]
for branch in('BASE','LID'):
 host=solutions['HOST-VIN'];uv=solutions['UV-'+branch];ground=solutions['GND-'+branch]
 h=host['feed_via_current_fractions'];us=uv['feed_via_current_fractions'];ut=uv['sink_via_current_fractions'];gs=ground['feed_via_current_fractions'];gt=ground['sink_via_current_fractions']
 near_length=1.55 if branch=='BASE'else 1.15;far=0 if branch=='BASE'else 1
 surface_squares=sum(fixed_squares.values())+(1.145/.5)*sum(f*f for f in h)+(1.145/.4)*sum(f*f for f in gs)
 surface_squares+=(.2/.5)*us[0]**2+(.6/.5)*us[1]**2
 surface_squares+=2*(near_length/.6)+(.6/.6)*(ut[far]**2+gt[far]**2)
 plane_squares=host['sheet_squares']+uv['sheet_squares']+ground['sheet_squares']
 # HOST input1via; all other regions have two physical parallel feed/sink vias.
 via_energy_factor=1+sum(f*f for group in(h,us,ut,gs,gt)for f in group)
 for wall in(.025,.018):
  via_r=rho*1/(math.pi*.2*wall);nominal_surface=surface_squares*sheet;plane=plane_squares*sheet;vias=via_energy_factor*via_r
  width_loss_surface=nominal_surface/.8;reserve=.003
  estimate=width_loss_surface+plane+vias+reserve
  cases.append({'branch':branch,'finished_outer_inner_copper_min_mm':[copper,copper],'plated_via_wall_min_mm':wall,'full_via_length_mm':1,'via_finished_bore_mm':.2,'temperature_C':temp,'sheet_squares_sum':plane_squares,'native_sheet_resistance_ohm':plane,'surface_path_squares':surface_squares,'nominal_surface_path_R_ohm':nominal_surface,'surface_width_retention_sensitivity':.8,'surface_R_at80pct_width_ohm':width_loss_surface,'barrel_trial_flow_sum_f_squared':via_energy_factor,'barrel_R_sum_ohm':vias,'engineering_spreading_model_reserve_ohm':reserve,'estimated_path_R_with_width_loss_and_reserve_ohm':estimate,'margin_to50mOhm_ohm':.05-estimate,'sensitivity_R_at_0p15mm_finished_bore_ohm':estimate+vias*(.2/.15-1),'sensitivity_R_at_0p15mm_bore_and_0p030mm_inner_Cu_ohm':estimate+vias*(.2/.15-1)+plane*(.035/.030-1),'drop_if_entire_path_carries_full_qualified1p484444A_V':estimate*1.4844444105716284})
report={'status':'engineering copper study; source-bound stage, final-route refresh required'if a.label!='final'else'engineering saved-final-copper study; physical acceptance pending','native_board_sha256':g['board_sha256'],'grid_metadata_sha256':sha(folder/'grid-0.125.json'),'rho20_ohm_mm':rho20,'temperature_coefficient_per_K':alpha,'rho_at85C_ohm_mm':rho,'primary_reference':'https://www.ti.com/lit/pdf/slua236 DN71; commercially annealed copper constants and R=rho*L/(w*t)','reference_is_not_a_fabricator_guarantee':True,'sheet_solver_source_sha256':sha(H/'sheet_solver.cpp'),'analytic_rectangle_benchmark':'81x40 cell full-edge contacts gives exactly2.0squares, error<1e-8','fixed_surface_roles_and_squares':fixed_squares,'solutions':solutions,'cases':cases,'requested_fabrication_minimum_corner_cases':[{'branch':c['branch'],'outer_Cu_min_mm':.035,'inner_Cu_min_mm':.030,'via_finished_bore_min_mm':.15,'via_wall_min_mm':.025,'temperature_C':85,'surface_width_retention':.8,'engineering_model_reserve_ohm':.003,'estimated_common_PCB_R_ohm':c['sensitivity_R_at_0p15mm_bore_and_0p030mm_inner_Cu_ohm'],'margin_to50mOhm_ohm':.05-c['sensitivity_R_at_0p15mm_bore_and_0p030mm_inner_Cu_ohm']}for c in cases if c['plated_via_wall_min_mm']==.025],'supplier_acceptance':False,'boundary':'J101 VBUS/GND lands to J621/J622 supply+return lands, through U105/U610/U611 copper; excludes semiconductorRON and separately allocated matedGH/crimp/wire/UVboard branches','conservative_omissions':['Other parallel copper layers and explicit tracks parallel to filled planes are uncredited','Every via uses full1mm barrel despite intermediate-layer connection','Complete PCB R is charged at full qualified source current, including device/UI/contactloops, although downstream UV portions carry less'],'limitations':['Native plane retained-cell discretization and clamped via-contact approximations are engineering models, not certified upper bounds','3mOhm allowance is not a measured annular-spreading/process error bound','Finished Cu/width/plating and actual hot-aged complete path<=50mOhm require fabricator and physical qualification'],'physical_validation':False}
(folder/'resistance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'board_sha256':g['board_sha256'],'cases':[{'branch':c['branch'],'via_wall_um':1000*c['plated_via_wall_min_mm'],'R_mOhm':1000*c['estimated_path_R_with_width_loss_and_reserve_ohm'],'margin_mOhm':1000*c['margin_to50mOhm_ohm']}for c in cases]},indent=2))
