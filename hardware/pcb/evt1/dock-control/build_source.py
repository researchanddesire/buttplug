"""Native controller and lid-UI circuit candidate; owned output is this folder.

Do not replace the existing five EVT boards. These sheets have actual selected
parts and physical pin contracts; placement, routing and full-system proof follow.
"""
from pathlib import Path
import hashlib,json,shutil,sys,uuid
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
sys.path.insert(0,str(ROOT/'tools'))
import electronics_r0_generate as g
import build_evt1_electrical as e
import kicad_sexp as s
STOCK=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
g.OUT=HERE;g.NS=uuid.UUID('8e5a0d2b-0c4a-4cde-826a-8164163c4a2b');g.LIB.clear();g.PARTS.clear()
e.initialise_symbols();g.passive('SW','SW');g.passive('LED','D')
# LED symbol physical pin1=cathode, pin2=anode, matching selected LED footprint.
a=g.LIB['LED'];a['text']=a['text'].replace('(number "1"','(number "swap"').replace('(number "2"','(number "1"').replace('(number "swap"','(number "2"')
a['pins'][0].update(number='2',name='A');a['pins'][1].update(number='1',name='K')
for n in (1,6):g.connector('Conn'+str(n),n)
BASE_PINS=json.loads((HERE.parent/'dock-ui/pin-contract.json').read_text())['MCU']['pins']
MCU_NETS={k:v['net'] for k,v in BASE_PINS.items()}
MCU_NETS.update({'5':None,'6':None,'7':'MCU_NRSTn','44':'BOOT0','32':'DEVICE_FAULTn'})
LCD_BUS=['LCD_DB'+str(i)for i in range(8)]+['LCD_A0','LCD_WRn','LCD_CSn','LCD_RESETn']
for p,net in list(MCU_NETS.items()):
    if net in LCD_BUS:MCU_NETS[p]=net+'_MCU'
left=[];right=[]
for n in range(1,49):
    p=BASE_PINS[str(n)]['gpio'];kind='power_in' if p in('VDD','VDDIO2','VDDA','VSS','VSSA') else ('input'if p in('BOOT0','NRST') else 'bidirectional')
    (left if n<=24 else right).append((n,p,kind))
g.ic('STM32L071CBT6',left,right,'https://www.st.com/resource/en/datasheet/stm32l071cb.pdf','ST DS10690 Rev7 LQFP48 Figure8 and Table15; MSI range6 4.2MHz, VOSRange3,0WS; physical pin36 VDDIO2 must be supplied.')
g.ic('ADS1115_DOCK',[(1,'ADDR_GND','input'),(4,'AIN0_BASE_FB','input'),(5,'AIN1_LID_FB','input'),(6,'AIN2_BASE_VOUT_DIV','input'),(7,'AIN3_LID_VOUT_DIV','input')],[(8,'VDD','power_in'),(3,'GND','power_in'),(9,'SDA','bidirectional'),(10,'SCL','input'),(2,'ALERT_RDY','open_collector')],'https://www.ti.com/lit/ds/symlink/ads1115.pdf','VSSOP10 DGS; 0x48. UV modules own10k/100nF filters; no duplicate filters here.')
HINGE={str(i):net for i,net in enumerate(['GND','3V3_UI']+['LCD_DB'+str(i)for i in range(8)]+['LCD_A0','LCD_WRn','LCD_CSn','LCD_RESETn','BTN_LEFTn','BTN_CENTERn_RAW','BTN_RIGHTn','GND','GND','GND'],1)}
g.ic('FH12_20_BOTTOM',[(i,'FFC_'+str(i),'passive')for i in range(1,11)],[(i,'FFC_'+str(i),'passive')for i in range(11,21)]+[('MP','METAL_HOLDDOWNS','passive')],'https://www.hirose.com/en/product/p/CL0586-0524-9-55','FH12-20S-0.5SH(55), bottomcontact,0.30mm FFC,2.0mm height; both mouths toward rear hinge in closed pose.')
LCD_PINS={1:('V0','LCD_V0'),2:('V1','LCD_V1'),3:('V2','LCD_V2'),4:('V3','LCD_V3'),5:('V4','LCD_V4'),6:('C4_PLUS_NC',None),7:('C2_MINUS','LCD_C2M'),8:('C2_PLUS','LCD_C2P'),9:('C1_PLUS','LCD_C1P'),10:('C1_MINUS','LCD_C1M'),11:('C3_PLUS','LCD_C3P'),12:('VOUT','LCD_VOUT'),13:('VDD','3V3_UI'),14:('VSS','GND')}
LCD_PINS.update({15+i:('DB'+str(7-i),'LCD_DB'+str(7-i))for i in range(8)})
LCD_PINS.update({23:('RD_N_WRITE_ONLY','3V3_UI'),24:('WR_N','LCD_WRn'),25:('A0','LCD_A0'),26:('RESET_N','LCD_RESETn'),27:('CS_N','LCD_CSn')})
def lcd_kind(i):return 'no_connect'if i==6 else('power_in'if i in(13,14)else('input'if i>=15 else'passive'))
CONTEXT_NETS=['SOURCE_OK', 'CC_OUT1', 'CC_OUT2', 'DEVICE_FAULTn', 'UV_LIMIT_FAULTn', 'LOOP_A', 'LOOP_B', 'MCU_NRSTn', 'UV_RUN', 'RELEASE_SEEN', 'BTN_CENTERn_DEBOUNCED', 'BTN_CENTERn_RAW', 'MCU_ARM', 'MCU_STOPn', 'WDI', 'UV_5V_SW', 'BASE_FB', 'LID_FB', 'BASE_VOUT_DIV', 'LID_VOUT_DIV', 'NTC_BASE', 'NTC_LID', '3V3', 'GND']
g.ic('BASE_CONTEXT_PORTS',[(i+1,n,'passive')for i,n in enumerate(CONTEXT_NETS[:12])],[(i+13,n,'passive')for i,n in enumerate(CONTEXT_NETS[12:])],'','Standalone intersheet context only; not purchased/PCBhardware. Remove when combining real sibling circuits.')
g.ic('NHD_C12864B2Z',[(i,LCD_PINS[i][0],lcd_kind(i))for i in range(1,15)],[(i,LCD_PINS[i][0],lcd_kind(i))for i in range(15,28)],'https://newhavendisplay.com/content/specs/NHD-C12864B2Z-RN-FBW.pdf','Purchased offboard reflective LCD; PDFp5 physical27pin contract. Read disabled; no discrete contrastpot/backlight.')
# Manufacturer top view: pin1-X, mouthnative+Y. NativeY mapsdock-Y,
# so the installed tail and socket both keep pin1-X; no electrical reversal.
SOCKET={str(p):LCD_PINS[p][1]for p in range(1,28)};SOCKET['MP']='GND'
g.ic('MOLEX_52437_2771',[(i,'MATES_LCD_'+str(i),'passive')for i in range(1,15)],[(i,'MATES_LCD_'+str(i),'passive')for i in range(15,28)]+[('MP','METAL_HOLDDOWNS','passive')],'https://www.molex.com/content/dam/molex/molex-dot-com/products/automated/en-us/salesdrawingpdf/524/52437/524373071_sd.pdf','Actual27-way bottomcontact. Installed pose preservesLCD numbering. LCD3mm exposedland differs4mm recommended: received matingtrial required.')
# Standard ERC annotation, not a purchased power source or PCB component.
g.LIB['PWR_FLAG']=dict(half=1.27,source='',pins=[dict(number='1',name='pwr',kind='power_out',x=0,y=0,angle=90,hide=False)],text=f'''(symbol "PWR_FLAG" (power) (pin_names hide) (in_bom no) (on_board no)
(property "Reference" "#FLG" (at 0 5.08 0) {g.effects(extra='hide')})
(property "Value" "PWR_FLAG" (at 0 3.81 0) {g.effects()})
(property "Footprint" "" (at 0 0 0) {g.effects(extra='hide')})
(property "Datasheet" "" (at 0 0 0) {g.effects(extra='hide')})
(symbol "PWR_FLAG_0_1" (polyline (pts (xy 0 0)(xy 0 1.27)(xy -1.27 1.905)(xy 0 2.54)(xy 1.27 1.905)(xy 0 1.27))(stroke(width .254)(type default))(fill(type none))))
(symbol "PWR_FLAG_1_1" (pin power_out line (at 0 0 90)(length 0)(name "pwr" {g.effects()})(number "1" {g.effects()}))))''')
rows=[];sheets=[]
fp=lambda n:'DockControl:'+n
C100='GRM155R71C104KA88D';C1U='C1608X7R1E105K080AB';CPUMP='C3216X7R1H225K160AB'
RMPN={'33':'RC0603FR-0733RL','0':'RC0603JR-070RL','1k':'RC0603FR-071KL','2k2':'RC0603FR-072K2L','4k7':'RC0603FR-074K7L','10k':'RC0603FR-0710KL','47k':'RC0603FR-0747KL','100k':'RC0603FR-07100KL','150k':'RC0603FR-07150KL','10k0.1':'RT0603BRD0710KL'}
def part(sh,lib,ref,value,x,y,nets,footprint,manufacturer,mpn,note='',kind='purchased',domain='MAIN_T'):
    sh.part(lib,ref,value,x,y,{str(k):v for k,v in nets.items()},footprint,note,domain=domain)
    rows.append(dict(reference=ref,value=value,manufacturer=manufacturer,mpn=mpn,footprint=footprint,note=note,item_type=kind,board='lid'if sh.name=='dock-lid-ui'else'controller'))
def res(sh,ref,x,y,value,a,b):part(sh,'R',ref,value+' ohm',x,y,{1:a,2:b},fp('R_0603_1608Metric'),'Yageo',RMPN[value])
def cap(sh,ref,x,y,a,b='GND',value='100nF',mpn=C100,foot='C_0402_1005Metric',note=''):
    part(sh,'C',ref,value,x,y,{1:a,2:b},fp(foot),'Murata'if mpn.startswith('GRM')else'TDK',mpn,note)
def flag(sh,ref,net,x,y):part(sh,'PWR_FLAG',ref,'PWR_FLAG',x,y,{1:net},'','annotation','–','Standalone supply context; not proof of external source.',kind='annotation',domain='ANNOTATION')
def sheet(name,title):
    g.PROJECT=name;sh=g.Sheet(name,title);sh.paper='A2';sh.sheet_path='/'+sh.id;sheets.append(sh);return sh
b=sheet('dock-controller','EVT dock controller / STM32L071 and monitors')
part(b,'STM32L071CBT6','U201','STM32L071CBT6',83.82,124.46,MCU_NETS,fp('LQFP-48_7x7mm_P0.5mm'),'STMicroelectronics','STM32L071CBT6')
part(b,'FH12_20_BOTTOM','J201','FH12-20S-0.5SH(55)',231.14,109.22,dict(HINGE,MP='GND'),fp('Hirose_FH12-20S-0.5SH_1x20-1MP_P0.50mm_Horizontal'),'Hirose','FH12-20S-0.5SH(55)')
part(b,'ADS1115_DOCK','U202','ADS1115IDGSR /0x48',383.54,68.58,{1:'GND',2:None,3:'GND',4:'BASE_FB',5:'LID_FB',6:'BASE_VOUT_DIV',7:'LID_VOUT_DIV',8:'3V3_ANALOG',9:'MON_I2C_SDA',10:'MON_I2C_SCL'},fp('VSSOP-10_3x3mm_P0.5mm'),'Texas Instruments','ADS1115IDGSR')
part(b,'Conn6','J202','TC2030-CTX-NL SWD CONTACT PATTERN',520.7,68.58,{1:'3V3',2:'SWDIO',3:'MCU_NRSTn',4:'SWCLK',5:'GND',6:None},fp('Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical'),'manual copper','–','Use Cortex TC2030-CTX-NL wiring:1VTREF,2SWDIO,3NRST,4SWCLK,5GND,6NC. NoSWO onthisM0+. Workshop tool, not populated connector.',kind='manual_copper')
part(b,'BASE_CONTEXT_PORTS','X201','BASE INTERSHEET CONTRACT / NO PCB',520.7,137.16,{i+1:n for i,n in enumerate(CONTEXT_NETS)},'','annotation','–','Global circuit interface; no invented connector. Real ports resolve in fullsystem.',kind='annotation',domain='INTERSHEET_CONTEXT')
for i,net in enumerate(LCD_BUS,201):
    x=40.64+((i-201)%6)*58.42;y=223.52+((i-201)//6)*43.18
    res(b,'R'+str(i),x,y,'33',net+'_MCU',net)
for ref,x,y,val,n1,n2 in [('R213',40.64,317.5,'10k','BOOT0','GND'),('R214',129.54,317.5,'0','3V3','3V3_ANALOG'),('R215',218.44,317.5,'0','3V3','3V3_UI'),('R216',307.34,137.16,'4k7','3V3_ANALOG','MON_I2C_SCL'),('R217',396.24,137.16,'4k7','3V3_ANALOG','MON_I2C_SDA'),('R218',307.34,180.34,'10k0.1','3V3_ANALOG','NTC_BASE'),('R219',396.24,180.34,'10k0.1','3V3_ANALOG','NTC_LID'),('R220',307.34,223.52,'1k','NTC_BASE','NTC_BASE_ADC'),('R221',396.24,223.52,'1k','NTC_LID','NTC_LID_ADC'),('R222',485.14,180.34,'100k','UV_5V_SW','UV_VBUS_MON'),('R223',485.14,223.52,'150k','UV_VBUS_MON','GND'),('R224',485.14,317.5,'2k2','STATUS_LED','STATUS_LED_A'),('R225',307.34,317.5,'10k','3V3','BTN_LEFTn'),('R226',396.24,317.5,'10k','3V3','BTN_RIGHTn')]:res(b,ref,x,y,val,n1,n2)
# ADC filtering is separate from the physical NTC divider node in the UV loom.
for p,net in [('18','NTC_BASE_ADC'),('19','NTC_LID_ADC')]:
    # Change generated labels and manifest only through the symbol instance nets
    # before native writing; pins remain physicalPB0/1 ADC8/9.
    for item in g.PARTS:
        if item['ref']=='U201':item['pins'][p]['net']=net
    # Locate the generated label by deterministic pin wire endpoint.
    old=BASE_PINS[p]['net'];lib=g.LIB['STM32L071CBT6'];pin=next(q for q in lib['pins']if q['number']==p)
    px,py=round(83.82+pin['x'],4),round(124.46-pin['y'],4)
    ex=round(px-5.08*__import__('math').cos(__import__('math').radians(pin['angle'])),4);ey=round(py+5.08*__import__('math').sin(__import__('math').radians(pin['angle'])),4)
    oldtext=f'(global_label {g.q(old)} (shape input) (at {ex} {ey} '
    for idx,text in enumerate(b.content):
        if text.startswith(oldtext):b.content[idx]=text.replace(g.q(old),g.q(net),1)
for ref,x,y,net in [('C201',40.64,360.68,'3V3'),('C202',99.06,360.68,'3V3'),('C203',157.48,360.68,'3V3'),('C204',215.9,360.68,'3V3'),('C205',274.32,360.68,'3V3_ANALOG'),('C207',391.16,360.68,'MCU_NRSTn'),('C208',307.34,266.7,'NTC_BASE_ADC'),('C209',396.24,266.7,'NTC_LID_ADC'),('C210',449.58,360.68,'3V3_ANALOG'),('C211',307.34,360.68,'BTN_LEFTn'),('C212',508.0,360.68,'BTN_RIGHTn')]:cap(b,ref,x,y,net)
cap(b,'C206',332.74,360.68,'3V3_ANALOG',value='1uF25V',mpn=C1U,foot='C_0603_1608Metric')
part(b,'LED','D201','LTST-C190KGKT GREEN',520.7,274.32,{1:'GND',2:'STATUS_LED_A'},fp('LED_0603_1608Metric'),'Lite-On','LTST-C190KGKT','Low-current status indication; confirm brightness at~0.5mA.')
part(b,'Conn1','TP201','BOOT0 WORKSHOP PAD',43.18,190.5,{1:'BOOT0'},fp('TestPoint_Pad_D1.0mm'),'manual copper','–',kind='manual_copper')
for ref,net,x in [('#FLG201','3V3',43.18),('#FLG202','GND',83.82),('#FLG203','3V3_ANALOG',124.46),('#FLG204','3V3_UI',165.1)]:flag(b,ref,net,x,393.7)
b.note('CONTROLLER CANDIDATE / ROUTING AND FULLSYSTEM ERC REQUIRED\nU201 all48physicalpins verified againstST DS10690 Rev7 Figure8/Table15.\n4.2MHz MSI range6; VOSRange3; Flash0WS. PH0/PH1 areNC.\nSafety sheet ownsRESETpullup/1kseries, ARM/STOP/WDI defaultpulls.\nADC18/19 connect throughR220/R221; MCU pin20 PB2 is digital only.',35.56,25.4,1.27)
b.note('LCD: twelve33ohm source resistors; preserve PA8STOP/PA9WDI while writingPA0..7.\nJ20120way hinge: paired FH12 bottomcontacts, TypeD opposite-side ultra-flex203mm.\nBothconnector mouths pointtowardrear+Y; both native180deg socketrotations put pin1 atdock+X in closedpose.\nCable routing/twist/continuity, signal integrity and hinge life remain unqualified.',165.1,165.1,1.27)
b.note('MONITORS: UVmoduleownsFB10k/100nF andVOUT1M/68k+10k/100nF.\nADS1115directinputs,0x48; no duplicatefilters. NTC10k0.1% pullups toVDDArail,\nVishay10k B3435 sensorstoGND;1k/100nF atADC8/9.\nUVVBUS divider100k/150k ratio0.6→PB2 digital; noADC onPB2.\nCurrent, settling, USB suspend/inrush and powered faults require hardware trials.',35.56,410.0,1.016)
l=sheet('dock-lid-ui','EVT lid UI / actual LCD charge pump and three switches')
part(l,'NHD_C12864B2Z','LCD301','NHD-C12864B2Z-RN-FBW',83.82,114.3,{i:v[1]for i,v in LCD_PINS.items()},'','Newhaven Display','NHD-C12864B2Z-RN-FBW','Purchased COGLCD, linked nativeMCAD inCADassembly. NoPCBfootprint: mates throughJ302.',domain='OFF_BOARD_LCD')
part(l,'MOLEX_52437_2771','J302','52437-2771 / DIRECT LCD MATE',231.14,114.3,SOCKET,fp('Molex_52437-2771_1x27-1MP_P0.50mm_Horizontal'),'Molex','52437-2771','Selected forEVTmatingtrial; LCD3mm exposedland vsrecommended4mm. Pin p mates LCD pin p in installed pose.')
part(l,'FH12_20_BOTTOM','J301','FH12-20S-0.5SH(55)',383.54,114.3,dict(HINGE,MP='GND'),fp('Hirose_FH12-20S-0.5SH_1x20-1MP_P0.50mm_Horizontal'),'Hirose','FH12-20S-0.5SH(55)')
for ref,x,net in [('S301',459.74,'BTN_LEFTn'),('S302',505.46,'BTN_CENTERn_RAW'),('S303',551.18,'BTN_RIGHTn')]:part(l,'SW',ref,'B3FS-1002P',x,114.3,{1:net,2:'GND'},fp('SW_SPST_Omron_B3FS-100xP'),'Omron / Aratas','B3FS-1002P','Stock footprint usesduplicatepads1upperrow and2lowerrow; eachrow is internally common.')
for i in range(5):cap(l,'C'+str(301+i),40.64+i*88.9,213.36,'LCD_V'+str(i),value='1uF25V',mpn=C1U,foot='C_0603_1608Metric',note='Datasheet0.1..1uF nominal bypass. Require>=0.1uF effective atintendedVLCD/temp/age.')
for ref,x,a,b in [('C306',40.64,'LCD_C2M','LCD_C2P'),('C307',129.54,'LCD_C1P','LCD_C1M'),('C308',218.44,'LCD_C3P','LCD_C1M'),('C309',307.34,'LCD_VOUT','GND')]:cap(l,ref,x,256.54,a,b,value='2.2uF50V',mpn=CPUMP,foot='C_1206_3216Metric',note='TDK2.2uF50VX7R1206; publishedDCbiascurve about-8% at10Vtyp. Require>=1uF effective atintendedvoltage/temp/age; no guaranteedbiascurveclaimed.')
cap(l,'C310',396.24,256.54,'3V3_UI',value='1uF25V',mpn=C1U,foot='C_0603_1608Metric')
cap(l,'C311',485.14,256.54,'3V3_UI')
for ref,x,y,value,a,b in [('R301',40.64,304.8,'47k','3V3_UI','LCD_CSn'),('R302',129.54,304.8,'47k','3V3_UI','LCD_WRn'),('R303',218.44,304.8,'100k','LCD_RESETn','GND'),('R304',307.34,304.8,'100k','LCD_A0','GND')]:res(l,ref,x,y,value,a,b)
for i in range(8):res(l,'R'+str(305+i),40.64+(i%6)*88.9,350.52+(i//6)*43.18,'100k','LCD_DB'+str(i),'GND')
# Lidpower is driven by controller flags in the combined hierarchy. Standalone
# lidERC power-context findings remain visible rather than adding duplicate sources.
l.note('ACTUAL 8080LCD / NO BACKLIGHT\n/RD tied3V3_UI. C4+(LCD6)NC. C1- is commonreturnfor bothC1+andC3+ flyingcaps.\nV0..4 eachbypass toGND. VOUT2.2uFtoGND. No invented externalcontrastpot;\nST7565R internalresistor/e-volumecommands25h/81h10h perNewhaven example.',35.56,25.4,1.27)
l.note('DIRECT 1:1 MATE: installedFFC returns+Y with contactsface-Z.\nManufacturer topview pin1-X/mouthnative+Y; boardnativeY mapsdock-Y.\nJ302pin1-X matches LCDpin1-X; 13=VDD,14=GND,22=DB0,27=CSn.\nNo180deg Z rotation. Physical continuity/mating trial required.\nLCDtailbare/stiffenerlengthdifferssocketrecommendation; noproductioncompatibilityclaim.',165.1,165.1,1.27)
l.note('S301/S302/S303 areLEFT/CENTER/RIGHT. CENTERgoestoindependentMAX6816 onsafetysheet;\nneverclockUVpermissionfrom MCU/softwaredebounce. LidUIboardhasnoUVLEDcurrentpath.\nOpaqueUVbarrier, caprest/overtravel and completeconnector/cablefit remainmechanicalgates.',35.56,410,1.016)
# Save two standalone leaf sheets and the combined native review hierarchy.
TOP=g.uid('dock-control');INST={sh.name:g.uid(sh.name+'-in-top')for sh in sheets}
for sh in sheets:
    g.PROJECT=sh.name;sh.save();path=HERE/(sh.name+'.kicad_sch');tree=s.parse(path.read_text().replace('PrototypeR0:','DockControl:'))
    s.child(tree,'generator')[1]=s.atom('build_dock_control')
    title=s.child(tree,'title_block');s.child(title,'date')[1]=s.string('2026-11-12');s.child(title,'rev')[1]=s.string('EVT1 controller candidate');s.child(title,'comment')[2]=s.string('NATIVE CIRCUIT CANDIDATE — NOT PCB FABRICATION')
    for node in s.children(tree,'symbol'):
        ref=s.prop(node,'Reference');row=next(x for x in rows if x['reference']==ref)
        for field,val in [('Manufacturer',row['manufacturer']),('MPN',row['mpn']),('ItemType',row['item_type'])]:node.append(s.parse(f'(property {g.q(field)} {g.q(val)} (at 0 0 0) {g.effects(extra="hide")})'))
        if row['item_type']!='purchased':s.child(node,'in_bom')[1]=s.atom('no')
        old=s.child(node,'instances');node.remove(old)
        node.append(s.parse(f'(instances(project {g.q(sh.name)}(path {g.q("/"+sh.id)}(reference {g.q(ref)})(unit 1)))(project "dock-control"(path {g.q("/"+TOP+"/"+INST[sh.name]+"/"+sh.id)}(reference {g.q(ref)})(unit 1))))'))
    s.write(path,tree)
    (HERE/(sh.name+'.kicad_pro')).write_text(json.dumps({'meta':{'filename':sh.name+'.kicad_pro','version':1},'erc':{'erc_exclusions':[]}},indent=2)+'\n')
g.PROJECT='dock-control';top=g.Sheet('dock-control','EVT dock controller and lid UI');top.paper='A3';top.sheet_path='/'+top.id;top.note('NATIVE CONTROLLER + LID UI CANDIDATE\nSourcepower, hardwareinterlock and UVdriver sheets are siblingprojects pendingfullsystemhierarchy.\nGlobal supplyflags are standalonecontextannotations; no powered/hardwareproof orPCBroutehere.',25.4,25.4,1.524);top.save();tree=s.parse((HERE/'dock-control.kicad_sch').read_text().replace('PrototypeR0:','DockControl:'))
for i,sh in enumerate(sheets):e.append_sheet(tree,sh.title,sh.name+'.kicad_sch',INST[sh.name],25.4,76.2+i*40.64)
s.write(HERE/'dock-control.kicad_sch',tree)
(HERE/'dock-control.kicad_pro').write_text(json.dumps({'meta':{'filename':'dock-control.kicad_pro','version':1},'erc':{'erc_exclusions':[]}},indent=2)+'\n')
lib=[s.atom('kicad_symbol_lib'),s.parse('(version 20220914)'),s.parse('(generator build_dock_control)')]
for name in sorted(set().union(*(sh.used for sh in sheets))):lib.append(s.parse(g.LIB[name]['text']))
s.write(HERE/'DockControl.kicad_sym',lib)
(HERE/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "DockControl") (type "KiCad") (uri "${KIPRJMOD}/DockControl.kicad_sym") (options "") (descr "Selected controller/LCD component pin snapshots")))\n')
(HERE/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "DockControl") (type "KiCad") (uri "${KIPRJMOD}/DockControl.pretty") (options "") (descr "Selected footprints and actual LCD socket land pattern")))\n')
local=HERE/'DockControl.pretty';local.mkdir(exist_ok=True)
copies={'Package_QFP':['LQFP-48_7x7mm_P0.5mm'],'Package_SO':['VSSOP-10_3x3mm_P0.5mm'],'Connector_FFC-FPC':['Hirose_FH12-20S-0.5SH_1x20-1MP_P0.50mm_Horizontal'],'Connector':['Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical'],'Resistor_SMD':['R_0603_1608Metric'],'Capacitor_SMD':['C_0402_1005Metric','C_0603_1608Metric','C_1206_3216Metric'],'Button_Switch_SMD':['SW_SPST_Omron_B3FS-100xP'],'TestPoint':['TestPoint_Pad_D1.0mm'],'LED_SMD':['LED_0603_1608Metric']}
footprints={}
for folder,names in copies.items():
    for name in names:
        src=STOCK/(folder+'.pretty')/(name+'.kicad_mod');assert src.exists(),src
        shutil.copy2(src,local/src.name);footprints[name]={'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest()}
# Molex SD-52437-019 RevF p2: exact recommended0.3x0.8signal lands,
# and nonrectangular L-shaped fitting-nail lands. Mouth+Y; pad1at-X.
name='Molex_52437-2771_1x27-1MP_P0.50mm_Horizontal'
lines=[f'(footprint {g.q(name)}(version 20221018)(generator build_dock_control)(layer "F.Cu")(attr smd)',f'(descr "Molex52437-2771 SD-52437-019 RevF p2; bottomcontact,27circuits; mouth+Y,pin1-X")', '(fp_text reference "REF**"(at 0 -2)(layer "F.SilkS")(effects(font(size 1 1)(thickness .15))))',f'(fp_text value {g.q(name)}(at 0 6.2)(layer "F.Fab")(effects(font(size .8 .8)(thickness .12))))']
for i in range(27):lines.append(f'(pad "{i+1}" smd rect(at {-6.5+.5*i} 0)(size .3 .8)(layers "F.Cu" "F.Paste" "F.Mask"))')
for sign in(-1,1):
    pts=[(sign*x,y)for x,y in[(7.75,.4),(10.15,.4),(10.15,2.6),(9.05,2.6),(9.05,3.45),(7.75,3.45)]]
    # Anchor containedinpolygon, with exact unscaled polygon relativetoanchor.
    ax,ay=sign*8.3,1.5
    poly=' '.join(f'(xy {x-ax} {y-ay})'for x,y in pts)
    lines.append(f'(pad "MP" smd custom(at {ax} {ay})(size .2 .2)(layers "F.Cu" "F.Paste" "F.Mask")(options(clearance outline)(anchor rect))(primitives(gr_poly(pts {poly})(width 0)(fill yes))))')
for layer,box,width in [('F.Fab',(-9.05,.1,9.05,4.6),.1),('F.CrtYd',(-10.65,-.9,10.65,5.1),.05)]:
    x1,y1,x2,y2=box;pts=[(x1,y1),(x2,y1),(x2,y2),(x1,y2)]
    for a,b in zip(pts,pts[1:]+pts[:1]):lines.append(f'(fp_line(start {a[0]} {a[1]})(end {b[0]} {b[1]})(layer "{layer}")(width {width}))')
lines+=['(fp_line(start -9.5 3.6)(end -9.05 4.1)(layer "F.SilkS")(width .15))', '(fp_line(start -9.05 4.1)(end -8.6 3.6)(layer "F.SilkS")(width .15))',')']
(local/(name+'.kicad_mod')).write_text('\n'.join(lines)+'\n')
# Bind stock external package geometry locally; no generic bounding-box fit bodies.
# Package models describe the selected standard case; received tolerances remain open.
models=HERE/'DockControl.3dshapes';models.mkdir(exist_ok=True)
model_sources={}
for f in local.glob('*.kicad_mod'):
    tree=s.parse(f.read_text());model=s.child(tree,'model')
    if model is None:continue
    path=Path(model[1].value.split('}/',1)[1]).with_suffix('.step')
    src=Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/3dmodels')/path
    if not src.exists() and f.stem=='SW_SPST_Omron_B3FS-100xP':
        src=ROOT/'hardware/cad/evt1-assembly/vendor/buttons/SW_SPST_Omron_B3FS-100xP.step'
    assert src.exists(),src
    target=models/src.name;shutil.copy2(src,target)
    model[1]=s.string('${KIPRJMOD}/DockControl.3dshapes/'+target.name)
    s.write(f,tree)
    model_sources[f.stem]={'source':str(src),'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'local_step':str(target.relative_to(HERE)),'license':'KiCad library CC-BY-SA4.0 with footprint/model exception; see KiCad upstream LICENSE','geometry_scope':'Selected standard external package, not maximum-tolerance proof or internal geometry'}
(HERE/'model-provenance.json').write_text(json.dumps(model_sources,indent=2)+'\n')
report={'status':'native controller and lid UI schematic candidate; placement is an unrouted shared-base subset','parts':rows,'generated_pin_manifest':g.PARTS,'stock_footprint_snapshots':footprints,'MCU_physical_pin_map':{n:dict(v,net=next(p['pins'][n]['net']for p in g.PARTS if p['ref']=='U201'))for n,v in BASE_PINS.items()},'MCU_native_terminal_nets':next(p['pins']for p in g.PARTS if p['ref']=='U201'),'LCD_physical_pin_map':{str(i):{'signal':a,'net':v}for i,(a,v)in LCD_PINS.items()},'LCD_socket_physical_pad_map':SOCKET,'hinge_link_pins':HINGE,'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'full_product_order_ready':False}
(HERE/'circuit-parts.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'schematics':[sh.name+'.kicad_sch'for sh in sheets],'parts':len(rows),'purchased_positions':len([r for r in rows if r['item_type']=='purchased']),'manual_copper':len([r for r in rows if r['item_type']=='manual_copper'])}))
