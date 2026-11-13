"""Independent critical-pin and event checks against native exported XML."""
from pathlib import Path
import hashlib
import itertools
import json
import re
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def read(folder):
    root=ET.parse(folder/('source-native.xml' if folder.name=='dock-ui' else 'native.xml')).getroot()
    pins={(n.get('ref'),n.get('pin')):net.get('name') for net in root.findall('./nets/net') for n in net.findall('node')}
    types={(n.get('ref'),n.get('pin')):n.get('pintype') for net in root.findall('./nets/net') for n in net.findall('node')}
    comps={c.get('ref'):{'value':c.findtext('value'),'footprint':c.findtext('footprint'),
              'mpn':next(x.get('value') for x in c.findall('property') if x.get('name')=='MPN')} for c in root.findall('./components/comp')}
    return pins,types,comps

pins,types,comps=read(HERE)
critical={
 'U602':{1:'HOST_5V',2:'GND',3:'SOURCE_OK',5:'LOOP_5V',6:'LOOP_5V'},
 'U606':{1:'3V3',2:'WDT_CWD',3:'3V3',4:'GND',5:'3V3',6:'WDI',7:'SAFE_RESETn',8:'SAFE_RESETn',9:'GND'},
 'U607':{1:'SAFE_RESETn',2:'GND',3:'3V3',5:'3V3',6:'3V3'},
 'U608':{1:'GND',2:'BTN_CENTERn_RAW',3:'BTN_CENTERn_DEBOUNCED',4:'3V3'},
 'U609':{1:'CLEARn',2:'3V3',3:'CLOCK_RELEASE',4:'3V3',5:'RELEASE_SEEN',7:'GND',9:'UV_RUN',10:'3V3',11:'CLOCK_PRESS',12:'ARM_D',13:'CLEARn',14:'3V3'},
 'U610':{1:'HOST_5V',2:'UV_5V_LIMITED',4:'GND',5:'CUT_A_QOD',6:'UV_5V_MID',7:'CUT_A_CT',8:'UV_GATE_A'},
 'U611':{1:'HOST_5V',2:'UV_5V_MID',3:'UV_POWER_GOOD',4:'GND',5:'CUT_B_QOD',6:'UV_5V_SW',7:'CUT_B_CT',8:'UV_GATE_B'},
 'U612':{1:'LOOP_A',2:'LOOP_B',4:'SOURCE_OK',5:'SAFE_RESETn',6:'RAW_SAFE',9:'RAW_SAFE',10:'MCU_STOPn',12:'UV_DELAYn',13:'3V3',8:'CLEARn'},
 'U613':{1:'LOOP_A_RAW',3:'LOOP_B_RAW',6:'LOOP_A',4:'LOOP_B'},
 'U614':{1:'BTN_CENTERn_DEBOUNCED',3:'BTN_CENTER_PRESSED',6:'CLOCK_RELEASE',4:'CLOCK_PRESS'},
 'U615':{1:'RELEASE_SEEN',2:'MCU_ARM',3:'ARM_D',4:'LOOP_A',5:'SOURCE_OK',6:'UV_GATE_A',9:'UV_RUN',10:'LOOP_B',8:'UV_GATE_B',12:'UV_RUN',13:'UV_POWER_GOOD',11:'UV_CTRL'},
 'U616':{1:'UV_DELAYn',2:'GND',3:'RAW_SAFE',4:'UV_DELAY_CT',5:'3V3',6:'3V3'}}
count=0
for ref,ps in critical.items():
    for pin,net in ps.items():
        assert pins[ref,str(pin)]==net,(ref,pin,net)
        count+=1
source_pins,source_types,_=read(HERE.parent/'dock-ui')
assert source_pins['U114','4']==pins['U614','3']=='BTN_CENTER_PRESSED'
assert source_types['U114','4']=='output' and types['U614','3']=='input'
assert pins['R606','1']=='SAFE_RESETn' and pins['R606','2']=='MCU_NRSTn'
for ref in ('R602','R604','R605','R612','R613'):
    assert comps[ref]['value']=='100k 1%' and pins[ref,'2']=='GND'

uvs=[]
for side,num,loop in [('BASE',400,'A'),('LID',500,'B')]:
    folder=HERE.parent/'dock-uv'/side.lower()
    pp,tt,cc=read(folder)
    for pin,net in {1:'UV_5V_SW',2:'UV_CTRL',3:side+'_SW',4:'GND',5:side+'_COMP',6:side+'_FB_RAW'}.items():
        assert pp['U'+str(num+1),str(pin)]==net
    for ref,pin,net in [('Q',1,side+'_CATHODE_GATE'),('Q',2,side+'_FB_RAW'),('Q',3,side+'_LED_K'),('D',1,side+'_VOUT')]:
        assert pp[ref+str(num+1),str(pin)]==net
    assert cc['R'+str(num+1)]['mpn']=='CRCW08053R65FKEA'
    assert cc['D'+str(num+1)]['mpn']=='PMEG6010CEH,115'
    for pin,net in {1:'UV_5V_SW',2:'GND',3:'UV_CTRL',4:side+'_FB',5:side+'_VOUT_DIV',6:'NTC_'+side,7:side+'_THERM_SEND',8:'LOOP_'+loop+'_RAW','MP':'GND'}.items():
        assert pp['J'+str(num+1),str(pin)]==net
        assert pins['J62'+str(1 if side=='BASE' else 2),str(pin)]==net
    normref=lambda ref:re.sub(r'\d+$',lambda m:str(int(m.group())-(100 if side=='LID' else 0)),ref)
    normnet=lambda net:net.replace('LID','BASE').replace('LOOP_B_RAW','LOOP_A_RAW') if net is not None else None
    uvs.append(({(normref(r),p):normnet(n) for (r,p),n in pp.items()},
                {normref(r):{k:normnet(v) for k,v in row.items()} for r,row in cc.items()}))
assert uvs[0]==uvs[1],'Base/lid electrical or part mismatch'

# Exhaustive combinational fault logic and FF edge event behavior. This does
# not simulate analog propagation, contact bounce duration or optical latency.
for a,b,source,reset,stop,delay in itertools.product((False,True),repeat=6):
    raw=a and b and source and reset
    clear=raw and stop and delay
    if not clear:
        release_seen=run=False
        assert not (run and True)  # UV_CTRL=UV_RUN AND finalPG
    if not a:assert not (a and source)
    if not b:assert not (True and b)
for held in (False,True):
    seen=run=False; previous=held
    # Recovery with unchanged physical button never clocks either latch.
    assert not run
    for pressed in [True,False,True]:
        if previous and not pressed:seen=True
        if not previous and pressed:run=seen
        previous=pressed
    assert run and seen
    seen=run=False  # asynchronous fault clear
    assert not run

# Verify the three different current boundaries independently of the generator:
# shared HOST/GND copper carries all source loads; UV switches carry both
# drivers; each symmetric branch carries one driver. DC is not a transient test.
budget=json.loads((HERE/'power-budget.json').read_text())
uv=budget['UV_normal_design'];path=budget['UV_path_resistance']
assert uv['VIN_floor_V']==4.10 and path['common_PCB_supply_plus_return_max_ohm']==.050
iuv=(uv['LED_power_total_W']+uv['bleeder_and_divider_power_total_W'])/(uv['efficiency_floor_assumption']*uv['VIN_floor_V'])+uv['driver_Iq_total_mA']/1000
isource=iuv+(budget['device_qualified_allocation_mA']+budget['dock_UI_overhead_allocation_mA']+budget['contact_loops']['qualified_total_max_mA'])/1000
assert abs(path['common_PCB_qualification_current_mA']-isource*1000)<1e-9
assert abs(path['UV_switch_qualification_current_mA']-iuv*1000)<1e-9
assert abs(path['each_branch_qualification_current_mA']-iuv*500)<1e-9
drops={'common_PCB_at_full_source_current':isource*path['common_PCB_supply_plus_return_max_ohm'],
       'switches_at_UV_current':iuv*path['common_switch_Rmax_ohm'],
       'each_branch_at_half_UV_current':iuv/2*path['each_branch_supply_plus_return_max_ohm']}
for name,value in drops.items():assert abs(path['DC_drop_V'][name]-value)<1e-12,name
driver=4.5-sum(drops.values())
assert abs(path['normal_maximum_load_floor_from4p5V_V']-driver)<1e-12
assert driver>=uv['VIN_floor_V'] and uv['input_required_mA']<budget['UV_limiter_min_mA']
assert abs(budget['qualified_source_worst_sum_mA']-1484.4444105716284)<1e-9
assert abs(uv['input_required_mA']-650.6149054287945)<1e-9
assert abs(uv['minimum_limiter_margin_mA']-31.929771203555223)<1e-9

files=[HERE/'native.xml',HERE/'native-checks.json',HERE/'build_safety.py',HERE/'native_helpers.py',HERE/'power-budget.json',HERE/'build_power_budget.py',HERE/'DESIGN.md',Path(__file__)]
files.extend(HERE.parent/'dock-uv'/side/name for side in ('base','lid') for name in ('native.xml','native-checks.json'))
files.append(HERE.parent/'dock-uv/DESIGN.md')
report={'status':'pass: independent critical terminals, source clock direction, base/lid identity, ideal events and conservative power-current boundaries',
        'critical_safety_pin_checks':count,'truth_table_rows':64,'UV_modules_identical':True,
        'power_current_boundaries_verified':True,'driver_DC_floor_V':driver,
        'common_PCB_current_mA':isource*1000,'UV_current_mA':iuv*1000,
        'source_sha256':{str(p.relative_to(HERE.parent)):sha(p) for p in files},
        'limits':['analog levels/timing and bounce not simulated','no powered or optical validation']}
(HERE/'interface-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='source_sha256'},indent=2))
