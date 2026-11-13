"""Build the native dock qualified-source/current-path schematic candidate.

Owned output is this folder only. Existing five EVT boards are read-only.
Run with ordinary Python; native KiCad export/ERC are separate validation steps.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import uuid

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
import electronics_r0_generate as g
import build_evt1_electrical as e
import kicad_sexp as s

STOCK = Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
g.OUT = HERE
g.PROJECT = 'dock-ui-source'
g.NS = uuid.UUID('22e0d735-9fb4-49e8-aafb-2ccaeabf34b5')
g.LIB.clear(); g.PARTS.clear()
e.initialise_symbols()
for count in (3,10):
    g.connector('Conn'+str(count),count)
g.ic('TUSB320HAIRWBR',
     [(1,'CC1','passive'),(2,'CC2','passive'),(3,'PORT_UFP_LOW','input'),
      (4,'VBUS_DET','input'),(5,'ADDR_GPIO_FLOAT','input'),(11,'EN_PG','input')],
     [(12,'VDD','power_in'),(10,'GND','power_in'),(7,'OUT1','open_collector'),
      (8,'OUT2','open_collector'),(6,'OUT3','open_collector'),(9,'ID','open_collector')],
     'https://www.ti.com/lit/ds/symlink/tusb320lai.pdf',
     'Hard UFP/GPIO mode. Active-high EN after qualified3V3 delay. OUT1low=1.5Aor3A. No discreteCCRd.')
g.ic('TPS3808G33DBVR',[(6,'VDD','power_in'),(5,'SENSE_3V3','input'),(3,'MR_N','input')],
     [(1,'RESET_N','open_collector'),(4,'CT','passive'),(2,'GND','power_in')],
     'https://www.ti.com/lit/ds/symlink/tps3808.pdf',
     'HOST5V-powered3V3 supervisor. CT through100k toVDD selects180..420ms. MRisHOST5Vlogic.')
g.ic('TS5A3159DBVR',[(1,'NO','passive'),(3,'NC_GND','passive'),(6,'IN','input')],
     [(4,'COM','passive'),(5,'VCC','power_in'),(2,'GND','power_in')],
     'https://www.ti.com/lit/ds/symlink/ts5a3159.pdf',
     'HOST5V-powered SPDT. INlow groundsCOM throughNC; INhigh connectsNO. No MOSFETthresholdclamp credit.')
g.ic('TPS22950YBHR',
     [('B1','VIN','power_in'),('A1','ON','input'),('C2','ILIM','passive')],
     [('B2','VOUT','power_out'),('C1','GND','power_in'),('A2','FLT_N','open_collector')],
     'https://www.ti.com/lit/ds/symlink/tps22950.pdf',
     'YBH6 balls0.4mm pitch, not the0.5mm-pitch TPS22946 package. Default34/50/66mA at19.1k+100R.')
g.ic('TLV70033DDCR',[(1,'IN','power_in'),(3,'EN','input')],
     [(5,'OUT_3V3','power_out'),(2,'GND','power_in'),(4,'NC','no_connect')],
     'https://www.ti.com/lit/ds/symlink/tlv700.pdf',
     '3.3V/2percent LDO.1uF recommended;>=0.1uF effective required.')
g.ic('SN74LVC2G14DCKR',[(1,'1A_CC_OUT1','input'),(3,'2A_CENTER_RELEASE','input'),(2,'GND','power_in')],
     [(6,'1Y_SOURCE_OK','output'),(4,'2Y_CENTER_PRESS','output'),(5,'VCC','power_in')],
     'https://www.ti.com/lit/ds/symlink/sn74lvc2g14.pdf',
     'Schmitt inputs accept slow open-drain edges. Channel1 invertsCCOUT1; channel2 invertsCENTER. R127forcesreleaseddefault.')
g.ic('DMN62D2U_7',[(1,'G','input')],[(3,'D','passive'),(2,'S','passive')],
     'https://www.diodes.com/datasheet/download/DMN62D2U.pdf',
     '60V logic NMOS. Qualified-source-only parallel ILIM branch; open gate returns to low limit.')

sh = g.Sheet(g.PROJECT, 'EVT dock USB and source power')
sh.paper = 'A2'
sh.sheet_path = '/'+sh.id
rows=[]
def part(lib,ref,mpn,x,y,nets,footprint,manufacturer,note=''):
    sh.part(lib,ref,mpn,x,y,{str(k):v for k,v in nets.items()},footprint,note,domain='MAIN_T')
    rows.append({'reference':ref,'manufacturer':manufacturer,'mpn':mpn,'footprint':footprint,'note':note})
fp=lambda name:'DockUI:'+name
part('USB4105','J101','USB4105-GF-A-120',76.2,76.2,
     {'A1':'GND','A4':'HOST_5V','A5':'CC1','A6':'USB_DP','A7':'USB_DM','A8':None,'A9':'HOST_5V','A12':'GND',
      'B1':'GND','B4':'HOST_5V','B5':'CC2','B6':'USB_DP','B7':'USB_DM','B8':None,'B9':'HOST_5V','B12':'GND','S1':'GND'},
     fp('USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal'),'GCT')
part('TUSB320HAIRWBR','U103','TUSB320HAIRWBR',231.14,63.5,
     {1:'CC1',2:'CC2',3:'GND',4:'VBUS_DET',5:None,6:'CC_OUT3',7:'CC_OUT1',8:'CC_OUT2',9:None,10:'GND',11:'CC_ENABLE',12:'3V3'},
     fp('Texas_X2QFN-12_1.6x1.6mm_P0.4mm'),'Texas Instruments')
part('SN74LVC2G14DCKR','U114','SN74LVC2G14DCKR',383.54,50.8,
     {1:'CC_OUT1',2:'GND',3:'BTN_CENTERn_DEBOUNCED',4:'BTN_CENTER_PRESSED',5:'3V3',6:'SOURCE_REQUEST'},
     fp('SOT-363_SC-70-6'),'Texas Instruments')
part('USBLC6_2SC6','U121','USBLC6-2SC6',520.7,50.8,
     {1:'USB_DM',2:'GND',3:'USB_DP',4:'USB_DP',5:'HOST_5V',6:'USB_DM'},
     fp('SOT-23-6'),'STMicroelectronics')
part('TLV70033DDCR','U102','TLV70033DDCR',231.14,160.02,
     {1:'HOST_5V',2:'GND',3:'HOST_5V',4:None,5:'3V3'},fp('TSOT-23-5'),'Texas Instruments')
part('TPS22950YBHR','U104','TPS22950YBHR',383.54,137.16,
     {'A1':'HOST_5V','A2':'DEVICE_FAULTn','B1':'HOST_5V','B2':'CONTACT_5V','C1':'GND','C2':'DEVICE_ILIM'},
     fp('Texas_YBH0006-C02_DSBGA-6_1.106x0.706mm_P0.4mm'),'Texas Instruments')
part('TPS2553DBVR','U105','TPS2553DBVR',520.7,137.16,
     {1:'HOST_5V',2:'GND',3:'SOURCE_OK',4:'UV_LIMIT_FAULTn',5:'UV_ILIM',6:'UV_5V_LIMITED'},
     fp('SOT-23-6'),'Texas Instruments')
part('DMN62D2U_7','Q103','DMN62D2U-7',450.85,228.6,
     {1:'SOURCE_OK',2:'GND',3:'DEVICE_ILIM_HIGH_RETURN'},fp('SOT-23'),'Diodes Incorporated')
part('TPS3808G33DBVR','U120','TPS3808G33DBVR',76.2,177.8,
     {1:'CC_ENABLE',2:'GND',3:'HOST_5V',4:'CC_ENABLE_CT',5:'3V3',6:'HOST_5V'},
     fp('SOT-23-6'),'Texas Instruments','First delay; enablesHAI onlyafter3V3valid180..420ms.')
part('TPS3808G33DBVR','U123','TPS3808G33DBVR',152.4,177.8,
     {1:'CC_STATUS_READY',2:'GND',3:'CC_STATUS_MRn',4:'CC_STATUS_CT',5:'3V3',6:'HOST_5V'},
     fp('SOT-23-6'),'Texas Instruments','Second delay starts afterU124 translatesCC_ENABLE tofullHOST5V MRhigh.')
part('TS5A3159DBVR','U122','TS5A3159DBVR',383.54,93.98,
     {1:'SOURCE_DRIVE',2:'GND',3:'SOURCE_OFF_RETURN',4:'SOURCE_OK',5:'HOST_5V',6:'CC_STATUS_READY'},
     fp('SOT-23-6'),'Texas Instruments','NC activelygroundsSOURCE_OK throughout startup/brownout; not a weak gateclamp.')
part('TS5A3159DBVR','U124','TS5A3159DBVR',520.7,93.98,
     {1:'HOST_5V',2:'GND',3:'GND',4:'CC_STATUS_MRn',5:'HOST_5V',6:'CC_ENABLE'},
     fp('SOT-23-6'),'Texas Instruments','3V3CC_ENABLE selects0orHOST5V forU123MR; respects0.7VDD MRhigh requirement.')
res=[('R101',76.2,144.78,'887k 1%','HOST_5V','VBUS_DET','RC0603FR-07887KL'),
     ('R105',332.74,215.9,'19.1k 0.1%','DEVICE_ILIM','DEVICE_ILIM_LOW_RETURN','RT0603BRD0719K1L'),
     ('R108',332.74,304.8,'100R 0.1%','DEVICE_ILIM_LOW_RETURN','GND','RT0603BRD07100RL'),
     ('R106',391.16,215.9,'2.52k 0.1%','DEVICE_ILIM','DEVICE_ILIM_HIGH_RETURN','RT0603BRD072K52L'),
     ('R107',520.7,215.9,'34.8k 0.1%','UV_ILIM','GND','RT0603BRD0734K8L'),
     ('R120',165.1,259.08,'100k 1%','3V3','CC_OUT1','RC0603FR-07100KL'),
     ('R121',223.52,259.08,'100k 1%','3V3','CC_OUT2','RC0603FR-07100KL'),
     ('R122',281.94,259.08,'100k 1%','SOURCE_OK','GND','RC0603FR-07100KL'),
     ('R123',340.36,259.08,'100k 1%','3V3','DEVICE_FAULTn','RC0603FR-07100KL'),
     ('R124',398.78,259.08,'100k 1%','3V3','UV_LIMIT_FAULTn','RC0603FR-07100KL'),
     ('R125',457.2,259.08,'100k 1%','3V3','CC_OUT3','RC0603FR-07100KL'),
     ('R126',520.7,259.08,'100k 1%','SOURCE_OK','GND','RC0603FR-07100KL'),
     ('R127',157.48,304.8,'10k 1%','3V3','BTN_CENTERn_DEBOUNCED','RC0603FR-0710KL'),
     ('R128',398.78,304.8,'10k 1%','3V3','CC_ENABLE','RC0603FR-0710KL'),
     ('R129',457.2,304.8,'10k 1%','3V3','CC_STATUS_READY','RC0603FR-0710KL'),
     ('R130',274.32,213.36,'100k 1%','HOST_5V','CC_ENABLE_CT','RC0603FR-07100KL'),
     ('R131',520.7,304.8,'100k 1%','HOST_5V','CC_STATUS_CT','RC0603FR-07100KL'),
     ('R132',274.32,304.8,'2.52k 0.1%','SOURCE_REQUEST','SOURCE_DRIVE','RT0603BRD072K52L'),
     ('R133',457.2,350.52,'100R 0.1%','SOURCE_OFF_RETURN','GND','RT0603BRD07100RL')]
for ref,x,y,val,a,b,mpn in res:
    part('R',ref,val,x,y,{1:a,2:b},fp('R_0603_1608Metric'),'Yageo',mpn)
    rows[-1]['mpn']=mpn
# Four1uF plus four100nF local capacitors total nominal4.4uF at HOST5V. Output and
# downstream capacitance is separately counted in the pending inrush analysis.
caps=[('C101',40.64,213.36,'HOST_5V','1uF25V','C1608X7R1E105K080AB','C_0603_1608Metric'),
      ('C102',99.06,213.36,'HOST_5V','1uF25V','C1608X7R1E105K080AB','C_0603_1608Metric'),
      ('C103',157.48,213.36,'HOST_5V','1uF25V','C1608X7R1E105K080AB','C_0603_1608Metric'),
      ('C104',215.9,213.36,'HOST_5V','1uF25V','C1608X7R1E105K080AB','C_0603_1608Metric'),
      ('C105',274.32,350.52,'3V3','1uF25V','C1608X7R1E105K080AB','C_0603_1608Metric'),
      ('C106',40.64,259.08,'CONTACT_5V','100nF16V','GRM155R71C104KA88D','C_0402_1005Metric'),
      ('C107',99.06,259.08,'UV_5V_LIMITED','100nF16V','GRM155R71C104KA88D','C_0402_1005Metric'),
      ('C108',40.64,304.8,'3V3','100nF16V','GRM155R71C104KA88D','C_0402_1005Metric'),
      ('C109',99.06,304.8,'3V3','100nF16V','GRM155R71C104KA88D','C_0402_1005Metric'),
      ('C110',40.64,350.52,'HOST_5V','100nF16V','GRM155R71C104KA88D','C_0402_1005Metric'),
      ('C111',99.06,350.52,'HOST_5V','100nF16V','GRM155R71C104KA88D','C_0402_1005Metric'),
      ('C112',157.48,350.52,'HOST_5V','100nF16V','GRM155R71C104KA88D','C_0402_1005Metric'),
      ('C113',332.74,350.52,'HOST_5V','100nF16V','GRM155R71C104KA88D','C_0402_1005Metric'),
      ('C114',274.32,177.8,'SOURCE_OK','100nF16V','GRM155R71C104KA88D','C_0402_1005Metric')]
for ref,x,y,net,val,mpn,foot in caps:
    part('C',ref,val,x,y,{1:net,2:'GND'},fp(foot),'TDK' if mpn.startswith('C1608') else 'Murata',mpn)
    rows[-1]['mpn']=mpn
part('Conn4','J102','DEVICE CONTACT LOOM / GND DM DP 5V',383.54,337.82,
     {1:'GND',2:'USB_DM',3:'USB_DP',4:'CONTACT_5V'},fp('Contact_Loom_4Land'),'manual copper')
part('Conn3','J103','TO UV HARDWARE SAFETY / GND 5V SOURCE',520.7,337.82,
     {1:'GND',2:'UV_5V_LIMITED',3:'SOURCE_OK'},fp('Control_Loom_3Land'),'manual copper',
     'UV_5V_LIMITED is before both serial safety switches. Never connect LEDs directly.')
part('Conn10','J104','TO UI AND SAFETY / MANUAL CONTRACT PADS',231.14,330.2,
     {1:'GND',2:'3V3',3:'SOURCE_OK',4:'CC_OUT1',5:'CC_OUT2',6:'DEVICE_FAULTn',7:'UV_LIMIT_FAULTn',
      8:'BTN_CENTERn_DEBOUNCED',9:'BTN_CENTER_PRESSED',10:'CC_OUT3'},fp('Control_Loom_10Land'),'manual copper',
     'Contract connector for candidate sheet; final fullboard intersheet wiring can remove these pads.')
sh.note('USB DATA: one direct path to ESP32-C3. No dock MCU parallel USB PHY.\nNo discrete5.1k Rd alongside U103. SBU1/SBU2 and U103ADDR/ID are intentional NC.',35.56,30.48,1.27)
sh.note('HARD QUALIFICATION: OUT1/OUT2 H/H=unattached, H/L=default, L/H=1.5A,L/L=3A.\nSOURCE_REQUEST=NOT OUT1; SchmittU114 accepts100k pullup. R127 defaultsCENTERreleased.\nU120 enablesHAI after180..420ms; U123 waits another180..420ms. U122 groundsSOURCE_OKuntilready.\nBothPG supervisors poweredHOST5V; U124 translatesCC_ENABLE tofullHOST5V MRlogic.',165.1,109.22,1.27)
sh.note('CURRENT PATH SETTINGS\nU10419.1k+100R:34/50/66mA; defaultwhole-dock allocation80mA.\nSOURCE_OK adds2.52k:2.2276keffective,~500mA nominal.\nU10534.8k:682.5..819.8mA including100KresistorTCR. With630mAdevice+10mAdock,\nqualifiedupperDCsum1459.8mA<1.5A. Transients/suspend unqualified.',332.74,167.64,1.27)
sh.note('SOURCE/INTERFACE CANDIDATE ONLY\nFullcontroller, LCD, UVdrivers and hardwarelid/thermal/latchsheet are not yet connected.\nJ103 is a limitedsupply, NOT permission to illuminateUV. Keep UVmoduleunpopulatedforbenchsourcechecks.\nUSBsuspend, inrush, reversecurrent, depleted-pack behavior and nativePCB routing remain OPEN.',35.56,378.46,1.27)
sh.save()
path=HERE/(g.PROJECT+'.kicad_sch')
tree=s.parse(path.read_text().replace('PrototypeR0:', 'DockUI:'))
s.child(tree,'generator')[1]=s.atom('build_dock_ui_source')
title=s.child(tree,'title_block');s.child(title,'date')[1]=s.string('2026-11-12');s.child(title,'rev')[1]=s.string('EVT1')
s.child(title,'comment')[2]=s.string('SOURCE CIRCUIT CANDIDATE — NOT FULL DOCK FABRICATION')
s.write(path,tree)
# Add exact purchasable identities to native symbols; the display value remains
# electrically meaningful for passives.
for node in s.children(tree,'symbol'):
    ref=s.prop(node,'Reference');row=next(x for x in rows if x['reference']==ref)
    for field,val in [('Manufacturer',row['manufacturer']),('MPN',row['mpn'])]:
        node.append(s.parse(f'(property {g.q(field)} {g.q(val)} (at 0 0 0) {g.effects(extra="hide")})'))
s.write(path,tree)
lib=[s.atom('kicad_symbol_lib'),s.parse('(version 20220914)'),s.parse('(generator build_dock_ui_source)')]
for name in sorted(sh.used):lib.append(s.parse(g.LIB[name]['text']))
s.write(HERE/'DockUI.kicad_sym',lib)
(HERE/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "DockUI") (type "KiCad") (uri "${KIPRJMOD}/DockUI.kicad_sym") (options "") (descr "Manufacturer-pin snapshots for dock UI source candidate")))\n')
(HERE/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "DockUI") (type "KiCad") (uri "${KIPRJMOD}/DockUI.pretty") (options "") (descr "Selected source-circuit footprints")))\n')
(HERE/(g.PROJECT+'.kicad_pro')).write_text(json.dumps({'meta':{'filename':g.PROJECT+'.kicad_pro','version':1},'erc':{'erc_exclusions':[]}},indent=2)+'\n')
# Preserve selected library geometry without editing its source library.
local=HERE/'DockUI.pretty';local.mkdir(exist_ok=True)
copies={'Connector_USB':['USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal'],
        'Package_TO_SOT_SMD':['SOT-363_SC-70-6','SOT-23-6','SOT-23','TSOT-23-5'],
        'Resistor_SMD':['R_0603_1608Metric'],
        'Capacitor_SMD':['C_0603_1608Metric','C_0402_1005Metric']}
footprints={}
for folder,names in copies.items():
    for name in names:
        src=STOCK/(folder+'.pretty')/(name+'.kicad_mod')
        assert src.exists(),src
        shutil.copy2(src,local/src.name)
        footprints[name]={'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest()}
# Selected-package native footprint, explicitly different from installed0.5pitch
# TexasDSBGA6. Manufacturer YBH0006-C02 example pattern uses0.2mmlands/P0.4.
def package_foot(name,pads,body,courtyard,cx=0):
    lines=[f'(footprint {g.q(name)} (version 20221018) (generator build_dock_ui_source) (layer "F.Cu") (attr smd)',
           '(fp_text reference "REF**" (at 0 -2) (layer "F.SilkS") (effects (font (size .8 .8) (thickness .12))))',
           f'(fp_text value {g.q(name)} (at 0 2) (layer "F.Fab") (effects (font (size .8 .8) (thickness .12))))']
    for layer,box,width in [('F.Fab',body,.1),('F.CrtYd',courtyard,.05)]:
        pts=[(cx-box[0]/2,-box[1]/2),(cx+box[0]/2,-box[1]/2),(cx+box[0]/2,box[1]/2),(cx-box[0]/2,box[1]/2)]
        for a,b in zip(pts,pts[1:]+pts[:1]):lines.append(f'(fp_line (start {a[0]} {a[1]}) (end {b[0]} {b[1]}) (layer "{layer}") (width {width}))')
    for number,x,y,w,h,kind in pads:
        lines.append(f'(pad {g.q(number)} smd {kind} (at {x} {y}) (size {w} {h}) (layers "F.Cu" "F.Paste" "F.Mask"))')
    lines.append(')');(local/(name+'.kicad_mod')).write_text('\n'.join(lines)+'\n')
package_foot('Texas_YBH0006-C02_DSBGA-6_1.106x0.706mm_P0.4mm',
             [(row+str(col+1),x,y,.2,.2,'circle') for row,y in zip('ABC',[-.4,0,.4]) for col,x in enumerate([-.2,.2])],
             (.706,1.106),(1.23,1.63))
# CC controller officialRWB package has fourcornerL-shapedterminals; use full
# stock exactpackage footprint if available rather than approximate rectangles.
rwb=STOCK/'Package_DFN_QFN.pretty/Texas_X2QFN-12_1.6x1.6mm_P0.4mm.kicad_mod'
if not rwb.exists():
    matches=list(STOCK.rglob('*RWB*12*'))
    raise RuntimeError('ExactRWBfootprintnotinstalled:'+str(matches))
shutil.copy2(rwb,local/rwb.name)
footprints[rwb.stem]={'source':str(rwb),'sha256':hashlib.sha256(rwb.read_bytes()).hexdigest()}
for count,name in [(4,'Contact_Loom_4Land'),(3,'Control_Loom_3Land'),(10,'Control_Loom_10Land')]:
    package_foot(name,[(str(i+1),2.5*i,0,1.8,1.8,'circle') for i in range(count)],(2.5*(count-1)+2,2), (2.5*(count-1)+3,3),cx=1.25*(count-1))
# Above copper pads are manual features, not an invented purchasedconnector.
report={'status':'native schematic candidate; not routedPCB','parts':rows,
        'generated_pin_manifest':g.PARTS,'stock_footprint_snapshots':footprints,
        'custom_package_drawing':'https://www.ti.com/lit/ds/symlink/tps22950.pdf#page=21',
        'full_product_order_ready':False,'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
(HERE/'source-circuit-parts.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'schematic':str(path),'component_count':len(rows),'footprints':len(list(local.glob('*.kicad_mod')))}))
