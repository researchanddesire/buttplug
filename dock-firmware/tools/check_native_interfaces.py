#!/usr/bin/env python3
"""Independent firmware/interface audit of source-bound native KiCad XML.

Checks endpoint identities and the selected physical package contract. This is
not a replacement for system ERC, board DRC, cable continuity or powered tests.
"""
import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from check_contract import ROOT,check

REPO=ROOT.parent
BASE=REPO/'hardware/pcb/evt1'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def current(folder):
    report=folder/'native-checks.json';j=json.loads(report.read_text())
    for rel,value in j['source_sha256'].items():assert sha(folder/rel)==value,('stale source',folder/rel)
    for rel,value in j.get('shared_source_sha256',{}).items():assert sha(REPO/rel)==value,('stale shared source',rel)
    for rel,value in j['reports_sha256'].items():assert sha(folder/rel)==value,('stale report',folder/rel)
    return report

def graph(path):
    root=ET.parse(path).getroot();pins={};nodes={}
    for n in root.findall('./nets/net'):
        for t in n.findall('node'):
            key=(t.get('ref'),t.get('pin'));assert key not in pins,key
            pins[key]=n.get('name');nodes[key]=t.attrib
    values={c.get('ref'):c.findtext('value')for c in root.findall('./components/comp')}
    return pins,nodes,values

def audit():
    check()
    reports=[current(BASE/d)for d in ('dock-control','dock-safety','dock-ui','dock-uv/base','dock-uv/lid')]
    c,cn,cv=graph(BASE/'dock-control/dock-control-native.xml')
    s,sn,sv=graph(BASE/'dock-safety/native.xml')
    p,pn,pv=graph(BASE/'dock-ui/source-native.xml')
    checks=[]
    def pin(g,ref,number,want):
        actual=g.get((ref,str(number)))
        if want is None:assert actual is None or actual.startswith('unconnected-'),(ref,number,actual)
        else:assert actual==want,(ref,number,want,actual)
        checks.append({'reference':ref,'physical_pin':str(number),'net':want})
    # Use our independently declared GPIO map, not the designer's generated
    # terminal manifest. Resolve the actual series-filter/signal aliases.
    mapping=json.loads((ROOT/'pin-map.json').read_text())['pins']
    alias={'NTC_BASE':'NTC_BASE_ADC','NTC_LID':'NTC_LID_ADC','DEVICE_LIMIT_FAULTn':'DEVICE_FAULTn'}
    for signal,point in mapping.items():
        want=alias.get(signal,signal)
        if signal.startswith('LCD_'):want+='_MCU'
        pin(c,'U201',point['physical_pin'],want)
        assert cn[('U201',str(point['physical_pin']))]['pinfunction'].split('_')[0]==point['gpio']
    for number,net in {1:'3V3',7:'MCU_NRSTn',8:'GND',9:'3V3_ANALOG',23:'GND',24:'3V3',35:'GND',36:'3V3',44:'BOOT0',47:'GND',48:'3V3',5:None,6:None}.items():pin(c,'U201',number,net)
    for number,net in {1:'GND',2:None,3:'GND',4:'BASE_FB',5:'LID_FB',6:'BASE_VOUT_DIV',7:'LID_VOUT_DIV',8:'3V3_ANALOG',9:'MON_I2C_SDA',10:'MON_I2C_SCL'}.items():pin(c,'U202',number,net)
    # Entire write-only LCD path, including each33ohm source resistor, the
    # straight20way hinge contract and the direct27way LCD mate. Native PCB
    # y maps to dock-Y, so an unrotated mouth+y footprint faces dock-Y while
    # pad1 remains-X, matching pin1 after the LCD's X-axis fold.
    bus=[f'LCD_DB{n}'for n in range(8)]+['LCD_A0','LCD_WRn','LCD_CSn','LCD_RESETn']
    for n,net in enumerate(bus,201):
        pin(c,'R'+str(n),1,net+'_MCU');pin(c,'R'+str(n),2,net);assert cv['R'+str(n)]=='33 ohm'
    hinge=['GND','3V3_UI']+[f'LCD_DB{n}'for n in range(8)]+['LCD_A0','LCD_WRn','LCD_CSn','LCD_RESETn','BTN_LEFTn','BTN_CENTERn_RAW','BTN_RIGHTn','GND','GND','GND']
    for n,net in enumerate(hinge,1):pin(c,'J201',n,net);pin(c,'J301',n,net)
    lcd={n:'LCD_V'+str(n-1)for n in range(1,6)}
    lcd.update({6:None,7:'LCD_C2M',8:'LCD_C2P',9:'LCD_C1P',10:'LCD_C1M',11:'LCD_C3P',12:'LCD_VOUT',13:'3V3_UI',14:'GND'})
    lcd.update({15+n:'LCD_DB'+str(7-n)for n in range(8)})
    lcd.update({23:'3V3_UI',24:'LCD_WRn',25:'LCD_A0',26:'LCD_RESETn',27:'LCD_CSn'})
    for n,net in lcd.items():pin(c,'LCD301',n,net);pin(c,'J302',n,net)
    for n in range(5):pin(c,'C'+str(301+n),1,'LCD_V'+str(n));pin(c,'C'+str(301+n),2,'GND')
    for ref,a,b in [('C306','LCD_C2M','LCD_C2P'),('C307','LCD_C1P','LCD_C1M'),('C308','LCD_C3P','LCD_C1M'),('C309','LCD_VOUT','GND')]:pin(c,ref,1,a);pin(c,ref,2,b)
    for ref,net in [('S301','BTN_LEFTn'),('S302','BTN_CENTERn_RAW'),('S303','BTN_RIGHTn')]:pin(c,ref,1,net);pin(c,ref,2,'GND')
    for ref,net in [('R225','BTN_LEFTn'),('R226','BTN_RIGHTn')]:
        pin(c,ref,1,'3V3');pin(c,ref,2,net);assert cv[ref]=='10k ohm'
    for ref,a,b in [('R218','3V3_ANALOG','NTC_BASE'),('R219','3V3_ANALOG','NTC_LID'),('R220','NTC_BASE','NTC_BASE_ADC'),('R221','NTC_LID','NTC_LID_ADC'),('R222','UV_5V_SW','UV_VBUS_MON'),('R223','UV_VBUS_MON','GND')]:pin(c,ref,1,a);pin(c,ref,2,b)
    assert cv['R218']==cv['R219']=='10k0.1 ohm'
    assert cv['R220']==cv['R221']=='1k ohm'
    assert cv['R222']=='100k ohm' and cv['R223']=='150k ohm'
    for ref,net in [('C208','NTC_BASE_ADC'),('C209','NTC_LID_ADC')]:pin(c,ref,1,net);pin(c,ref,2,'GND')
    for n,net in {1:'3V3',2:'SWDIO',3:'MCU_NRSTn',4:'SWCLK',5:'GND',6:None}.items():pin(c,'J202',n,net)
    pin(c,'C207',1,'MCU_NRSTn');pin(c,'C207',2,'GND');pin(s,'R606',1,'SAFE_RESETn');pin(s,'R606',2,'MCU_NRSTn')
    # Hardware owns the two physical edge clocks and asynchronous permissions.
    for n,net in {1:'GND',2:'BTN_CENTERn_RAW',3:'BTN_CENTERn_DEBOUNCED',4:'3V3'}.items():pin(s,'U608',n,net)
    pin(p,'U114',3,'BTN_CENTERn_DEBOUNCED');pin(p,'U114',4,'BTN_CENTER_PRESSED')
    for n,net in {1:'BTN_CENTERn_DEBOUNCED',3:'BTN_CENTER_PRESSED',4:'CLOCK_PRESS',6:'CLOCK_RELEASE'}.items():pin(s,'U614',n,net)
    for n,net in {1:'CLEARn',2:'3V3',3:'CLOCK_RELEASE',4:'3V3',5:'RELEASE_SEEN',9:'UV_RUN',10:'3V3',11:'CLOCK_PRESS',12:'ARM_D',13:'CLEARn',14:'3V3',7:'GND'}.items():pin(s,'U609',n,net)
    for n,net in {1:'RELEASE_SEEN',2:'MCU_ARM',3:'ARM_D',4:'LOOP_A',5:'SOURCE_OK',6:'UV_GATE_A',9:'UV_RUN',10:'LOOP_B',8:'UV_GATE_B',12:'UV_RUN',13:'UV_POWER_GOOD',11:'UV_CTRL'}.items():pin(s,'U615',n,net)
    for n,net in {1:'LOOP_A',2:'LOOP_B',4:'SOURCE_OK',5:'SAFE_RESETn',6:'RAW_SAFE',9:'RAW_SAFE',10:'MCU_STOPn',12:'UV_DELAYn',13:'3V3',8:'CLEARn'}.items():pin(s,'U612',n,net)
    for n,net in {2:'WDT_CWD',3:'3V3',5:'3V3',6:'WDI',7:'SAFE_RESETn',8:'SAFE_RESETn',9:'GND'}.items():pin(s,'U606',n,net)
    pin(s,'R603',1,'3V3');pin(s,'R603',2,'WDT_CWD');assert sv['R603']=='10k 1%'
    for ref,net in [('R604','MCU_ARM'),('R605','MCU_STOPn'),('R602','WDI')]:pin(s,ref,1,net);pin(s,ref,2,'GND')
    for ref,on,vin,vout in [('U610','UV_GATE_A','UV_5V_LIMITED','UV_5V_MID'),('U611','UV_GATE_B','UV_5V_MID','UV_5V_SW')]:pin(s,ref,8,on);pin(s,ref,2,vin);pin(s,ref,6,vout)
    pin(s,'U611',3,'UV_POWER_GOOD')
    pin(p,'U103',7,'CC_OUT1');pin(p,'U103',8,'CC_OUT2');pin(p,'U104','A2','DEVICE_FAULTn');pin(p,'U105',4,'UV_LIMIT_FAULTn')
    # Read both actual UV leaf netlists: current conversion must follow their
    # selected RSET, not an earlier architecture-only resistor value.
    header=(ROOT/'include/dock_app.h').read_text()
    assert re.search(r'^#define DOCK_UV_SENSE_MILLIOHM 3650u$',header,re.M)
    for side,base,loop,safety_ref in [('BASE',400,'A','J621'),('LID',500,'B','J622')]:
        u,un,uv=graph(BASE/'dock-uv'/side.lower()/'native.xml')
        ref=lambda letter,n=1:letter+str(base+n)
        local=lambda name:side+'_'+name
        for n,net in {1:'UV_5V_SW',2:'UV_CTRL',3:local('SW'),4:'GND',5:local('COMP'),6:local('FB_RAW')}.items():pin(u,ref('U'),n,net)
        link=['UV_5V_SW','GND','UV_CTRL',local('FB'),local('VOUT_DIV'),'NTC_'+side,local('THERM_SEND'),'LOOP_'+loop+'_RAW']
        for n,net in enumerate(link,1):pin(u,ref('J'),n,net);pin(s,safety_ref,n,net)
        for part,n1,a,n2,b in [(ref('L'),1,'UV_5V_SW',2,local('SW')),
             (ref('D'),1,local('VOUT'),2,local('SW')),
             (ref('D',2),2,local('VOUT'),1,local('LED_MID')),
             (ref('D',3),2,local('LED_MID'),1,local('LED_K')),
             (ref('Q'),2,local('FB_RAW'),3,local('LED_K')),
             (ref('R'),1,local('FB_RAW'),2,'GND'),
             (ref('R',5),1,local('VOUT'),2,local('VOUT_SENSE')),
             (ref('R',6),1,local('VOUT_SENSE'),2,'GND'),
             (ref('R',7),1,local('VOUT_SENSE'),2,local('VOUT_DIV')),
             (ref('R',8),1,local('FB_RAW'),2,local('FB')),
             (ref('TH'),1,'NTC_'+side,2,'GND'),
             (ref('S'),1,local('THERM_SEND'),2,'LOOP_'+loop+'_RAW')]:pin(u,part,n1,a);pin(u,part,n2,b)
        assert uv[ref('R')]=='3.65R1%100ppm'
        assert uv[ref('R',5)]=='1M1%' and uv[ref('R',6)]=='68k1%'
        pin(u,ref('Q'),1,local('CATHODE_GATE'))
        pin(u,ref('R',2),1,'UV_CTRL');pin(u,ref('R',2),2,local('CATHODE_GATE'))
        pin(u,ref('C',2),1,local('VOUT'));pin(u,ref('C',2),2,'GND');assert uv[ref('C',2)]=='4.7uF50VX7R'
        for cap,net in [(ref('C',4),local('FB')),(ref('C',5),local('VOUT_DIV'))]:pin(u,cap,1,net);pin(u,cap,2,'GND')
    sources={str(path.relative_to(REPO)):sha(path)for path in reports}
    paths=[BASE/'dock-control/dock-control-native.xml',BASE/'dock-safety/native.xml',BASE/'dock-ui/source-native.xml']
    paths.extend(BASE/'dock-uv'/side/'native.xml'for side in ('base','lid'))
    sources.update({str(path.relative_to(REPO)):sha(path)for path in paths})
    result={'status':'pass: independent firmware/native endpoint audit','pass':True,
      'terminal_checks':len(checks),'GPIOs_checked':len(mapping),'source_sha256':sources,
      'native_endpoint_checks':checks,
      'timing_review':[
        {'issue':'Falling-edge watchdog would see two loops between edges when simply toggled','fix':'One high/low WDI pulse per completed healthy loop;100ms work limit plus10ms cadence stays below170ms watchdog minimum'},
        {'issue':'Post-cut rail is absent before UV_RUN and may still be rising immediately after it','fix':'Check PB2 digital presence after300ms start grace, alongside LED current/voltage; no analog4.3V measurement claimed'},
        {'issue':'Fault acknowledgement release could precede420ms UV supervisor recovery','fix':'Require500ms continuously healthy inputs before accepting a fresh acknowledgement press'},
        {'issue':'Compiler-dependent busy delay inflated LCD full-frame runtime','fix':'Use SysTick core-clock counting for conservative bus delays; scope/loop timing remains a hardware gate'},
        {'issue':'Previous J302 reversal double-flipped the installed LCD contact order','fix':'Manufacturer topview pin1left/mouthdown matches unrotated nativefootprint after boardy-to-dockminusY mapping; direct1:1 mate preserves LCDpin1-X after X-axis fold'}],
      'boundaries':['Independent endpoint audit is not full-system native ERC or PCB pad/net parity.',
                    'LCD socket1:1 and hinge1:1 contracts still need physical continuity/mating qualification.',
                    'PB2 is digital rail presence, not voltage-floor telemetry.',
                    'Actual supervisor/PG/watchdog/ADC/filter/clock timing, source budget and optical shutdown remain unpowered.'],
      'physical_validation':False,'full_product_order_ready':False}
    (ROOT/'interface-review.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
if __name__=='__main__':
    r=audit();print(json.dumps({k:r[k]for k in ('status','terminal_checks','GPIOs_checked','pass')},indent=2))
