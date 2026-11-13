from pathlib import Path
import json,hashlib
folder=Path(__file__).resolve().parent
source_path=folder.parent/'dock-ui/power-budget.json'
source=json.loads(source_path.read_text())
tol=.001+25e-6*100
imin=25230/(34.8*(1+tol))**1.016
imax=22980/(34.8*(1-tol))**.94
iled=.204/(3.65*(1-.01-100e-6*100))
vout=2*7.5+1+.204
pload=2*iled*vout
pmon=2*vout*vout*(1/99000+1/(1068000*.99))
vin_floor=4.10
efficiency=.70
common_pcb=.050
common_switch=.165
each_branch=.290
iuv=(pload+pmon)/(efficiency*vin_floor)*1000+4.6
loopmin=4.5/(430*1.01)*1000
loopmax=5.25/(430*.99)*1000
other_current=630+10+2*loopmax
source_current=iuv+other_current
drop_pcb=source_current/1000*common_pcb
drop_switch=iuv/1000*common_switch
drop_branch=iuv/2000*each_branch
driver_voltage=4.5-drop_pcb-drop_switch-drop_branch
efficiency_break_even=(pload+pmon)/(vin_floor*((imin-4.6)/1000))
assert iuv<imin and driver_voltage>=vin_floor
assert 630+10+imax+2*loopmax<1500
items=[('MCU Flash workload and active peripheral allocation at4.2MHz',2.0),('LCD including contrast chargepump allocation',1.5),('three button loads including source R127/MAX6816,rawCENTER and clock pulls',1.3),('LCD eight data100k pulldowns',.28),('two NTC10k pullups',.35),('statusLED including resistor tolerance',.60),('ADS1115 published continuousconversion max',.30),('source TUSB/LDO and safety logic/supervisors/watchdog allocation',1.5),('fault/PG/CC and logic/output pulls including UVFET gates',1.0),('dynamic/leakage reserve',1.17)]
assert abs(sum(v for _,v in items)-10)<1e-10
budget={'status':'prototype circuit arithmetic; full PVT/suspend/inrush and physical acceptance pending',
 'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'stable_source_budget_sha256':hashlib.sha256(source_path.read_bytes()).hexdigest(),
 'steady_state_only':True,'source_power_budget_json_unchanged':True,
 'supersedes_fields_in_dock_ui_power_budget':['dock_overhead.allocated_items','UV_modules.minimum_driver_input_V','qualified_total_including_contactloops'],
 'device_default_allocation_mA':70,'device_qualified_allocation_mA':630,'dock_UI_overhead_allocation_mA':10,
 'dock_UI_items':[{'name':n,'allocation_mA':v} for n,v in items],
 'not_vendor_guaranteed':['TUSB320 max Icc not published','LCD max specified only25C','complete10mA allocation requires actual assembledmeasurement','TPS61165 2.3mA Iq is typical, not a published maximum','70percent boost efficiency requires qualification at actual voltage/load/temperature'],
 'contact_loops':{'source':'HOST_5V through U602TPS22919 enabledonlySOURCE_OK','legacy_disabled':True,'series_pull_ohm':430,'tolerance':.01,'each_min_at4p5V_mA':loopmin,'each_max_at5p25V_mA':loopmax,'qualified_total_max_mA':2*loopmax,
 'primary_rating':'Sensata6700 lowlevel0.010A at5VDC for100000cycles; not a4.5..5.25V guarantee',
 'qualification_pending':'Actual4.5..5.25V switching/contact resistance/leakage/life must be qualified; no vendor drycircuit guarantee claimed'},
 'UV_limiter_min_mA':imin,'UV_limiter_max_mA':imax,
 'qualified_source_worst_sum_mA':630+10+imax+2*loopmax,'margin_to1p5A_mA':1500-(630+10+imax+2*loopmax),
 'normal_qualified_source_total_at_UV_floor_mA':source_current,
 'UV_normal_design':{'RSET_mpn':'CRCW08053R65FKEA','RSET_ohm':3.65,'LED_current_min_mA':.196/(3.65*1.02)*1000,'LED_current_nominal_mA':.2/3.65*1000,'LED_current_max_mA':iled*1000,'Vout_ceiling_V':vout,'LED_power_total_W':pload,'bleeder_and_divider_power_total_W':pmon,'VIN_floor_V':vin_floor,'efficiency_floor_assumption':efficiency,'driver_Iq_total_mA':4.6,'driver_Iq_basis':'Two2.3mA datasheettypicals; actualworstcase requiresqualification','input_required_mA':iuv,'minimum_limiter_margin_mA':imin-iuv,'minimum_efficiency_to_stay_below_limiter_at_floor':efficiency_break_even,'primary_driver_input_range_V':[3,18],'primary_driver_source':'https://www.ti.com/lit/ds/symlink/tps61165.pdf RevE sections7.4/10','efficiency_Vf_and_FETdrop_require_measurement':True},
 'UV_path_resistance':{'common_switch_Rmax_ohm':common_switch,'common_PCB_supply_plus_return_max_ohm':common_pcb,'each_branch_supply_plus_return_max_ohm':each_branch,
 'common_PCB_boundary':'Full supply+return PCB copper fromUSBinputVBUS/GND pads through externalsource/UVswitch copper toJ621/J622 branchlands, including sharedHOST/GND necks/planes/vias overtemperature; excludes semiconductorRON and branchconnectors/harness/localUVPCB',
 'common_PCB_current_boundary':'Conservatively apply the entire50mOhm commonPCB allowance at full qualified source current: UV plus630mA device,10mA UI and bothcontactloops; a measured segment split may refine thisbound',
 'branch_includes':['all four mated GH electrical contacts, total up to0.200ohm after testing','crimps','supply and return wire','local PCB copper','temperature and aging'],
 'branch_resistance_allocations_ohm':{'four_mated_contacts_aftertest':.200,'four_crimp_joints':.010,'PCB_supply_and_return_including_vias_attemperature':.020,'wire_supply_and_return_attemperature':.060},
 'wire':{'gauge':'26AWG stranded','incoming_max_resistance_ohm_per_m_at20C':.135,'conductor_max_C':80,'copper_TCR_per_K':.00393,'power_wire_each_leg_max_mm':175,'supply_plus_return_max_length_mm':350,'calculated_hot_wire_max_ohm':.135*(1+.00393*(80-20))*.350,'actual_wire_and_crimp_qualification':False},
 'qualification_current_total_mA':iuv,'qualification_current_total_boundary':'UV-only total; sharedPCBusesfullsourcecurrentbelow','qualification_current_each_mA':iuv/2,
 'common_PCB_qualification_current_mA':source_current,'UV_switch_qualification_current_mA':iuv,'each_branch_qualification_current_mA':iuv/2,
 'DC_drop_V':{'common_PCB_at_full_source_current':drop_pcb,'switches_at_UV_current':drop_switch,'each_branch_at_half_UV_current':drop_branch,'sum':drop_pcb+drop_switch+drop_branch},
 'floor_from4p5V_V':driver_voltage,'normal_maximum_load_floor_from4p5V_V':driver_voltage,'DC_headroom_above_driver_floor_V':driver_voltage-vin_floor,
 'not_maintained_at_fault_currentlimit':True,'no_wire_only_allocation':True,'branch_symmetry_required_or_recalculate':True,
 'acceptance':'Measure actual hot-aged commonPCB supply+return path and each complete branch. Require bothdriverVIN>=4.10V throughout validatednormaloperation/transients atminimum4.5V dockinput; measureboostefficiency>=70percent andactualIq/Vf/currentlimits. DCheadroom isnot ripple/startupmargin. DefaultRp disablesUV.'},
 'release_gates':['PCB layout/nativeDRC and actualpad/netlist parity','effective Cout>=1uF at39V,temp,age andloop stability','full UI10mA,currentlimit,USBsuspend/inrush/sourcechanges','actualcontactloop load range and thermal attachment','UV opticaltail/leakage/dose/efficacy and thermal/materialaging'],
 'physical_validation':False,'full_product_order_ready':False}
(folder/'power-budget.json').write_text(json.dumps(budget,indent=2)+'\n')
print(json.dumps({k:budget[k] for k in ('qualified_source_worst_sum_mA','margin_to1p5A_mA','UV_normal_design','UV_path_resistance')},indent=2))
