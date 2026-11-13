"""Generate the two identical, selected-part UV driver candidates."""
from pathlib import Path
import sys
import uuid

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'dock-safety'))
from native_helpers import Project,g

TI='https://www.ti.com/lit/ds/symlink/tps61165.pdf'
LED='https://www.vishay.com/docs/80232/vlmu35cb2x-275-120.pdf'

def build(side,base,loop):
    stem='dock-uv-'+side.lower()
    p=Project(HERE/side.lower(),stem,'EVT '+side+' UV driver',
              str(uuid.uuid5(uuid.NAMESPACE_URL,'compass-'+stem)), 'DockUV')
    p.sheet.paper='A1'
    g.ic('TPS61165DBVR',[(1,'VIN','power_in'),(2,'CTRL_STATIC','input'),(6,'FB','input')],
         [(3,'SW','passive'),(4,'GND','power_in'),(5,'COMP','passive')],TI,
         'Static CTRL; 200mV feedback; 37..39V openLED OVP. CTRL low2.5ms shutdown; cathodeFET separate interrupt.')
    g.ic('PMEG6010CEH',[(2,'A','passive')],[(1,'K','passive')],
         'https://assets.nexperia.com/documents/data-sheet/PMEG6010CEH.pdf','60V1A Schottky; physical bar identifies K pin1.')
    g.ic('VLMU35CB20',[(2,'A','passive')],[(1,'K_MARKED','passive')],LED,
         'Two electrical terminals only; cathode mark identifies1. Both large pads carry LED current and heat.')
    g.ic('DMN62D2U',[(1,'G','input')],[(3,'D','passive'),(2,'S','passive')],
         'https://www.diodes.com/datasheet/download/DMN62D2U.pdf','60V NMOS, gateUVCTRL, sourceFB, drainLEDcathode.')
    g.ic('PowerInductor',[(1,'1','passive')],[(2,'2','passive')],
         'https://www.bourns.com/docs/Product-Datasheets/SRP4020TA.pdf','10uH20%;DCR243mOhmmax;Isat2.3A; actual recommended lands.')
    g.ic('NTC413',[(1,'NTC','passive')],[(2,'RETURN','passive')],
         'https://www.vishay.com/docs/29078/ntcle413.pdf','Remote10k1%B25/85 3435K1%; controller owns pullup/filter.')
    g.ic('THERM67L',[(1,'NC_CONTACT','passive')],[(2,'NC_CONTACT','passive')],
         'https://www.sensata.com/sites/default/files/a/sensata-6700-series-subminiature-bimetal-disc-thermostats-datasheet.pdf',
         '67L045 opens45+/-5C. Published lowlevel reference10mA@5V;4.5..5.25V use NOT vendor qualified.')
    g.ic('GH8',[(i,str(i),'passive') for i in range(1,9)],[('MP','MOUNT_GND','passive')],
         'https://www.jst-mfg.com/product/pdf/eng/eGH.pdf','Straight1:1toJ621/J622; no highvoltage across hinge.')
    g.connector('SolderLand',1)
    f=lambda family,name:p.stock(family,name)
    r0603=f('Resistor_SMD','R_0603_1608Metric');r0805=f('Resistor_SMD','R_0805_2012Metric')
    c0603=f('Capacitor_SMD','C_0603_1608Metric');c1210=f('Capacitor_SMD','C_1210_3225Metric')
    sot6=f('Package_TO_SOT_SMD','SOT-23-6');sot3=f('Package_TO_SOT_SMD','SOT-23')
    diode=f('Diode_SMD','D_SOD-123F');gh=f('Connector_JST','JST_GH_SM08B-GHS-TB_1x08-1MP_P1.25mm_Horizontal')
    land=f('TestPoint','TestPoint_Pad_D1.5mm')
    coil=p.custom('Bourns_SRP4020TA_Actual_Lands',[('1',-1.85,0,1.5,2.4,'rect'),('2',1.85,0,1.5,2.4,'rect')],
                  (4.45,4.06),(5.7,4.9),'https://www.bourns.com/docs/Product-Datasheets/SRP4020TA.pdf#page=1')
    # Manufacturer two-terminal openings with outer shoulders: K right, A left.
    lp=[]
    for number,sign in [('1',1),('2',-1)]:
        lp.extend([(number,sign*.9125,0,1.325,3.15,'rect'),(number,sign*1.8,0,.45,.5,'rect')])
    led=p.custom('Vishay_VLMU35CB2_Actual_TwoTerminal',lp,(3.45,3.45),(4.6,4.0),LED+'#page=4')
    ref=lambda s,n=1:s+str(base+n)
    local=lambda name:side+'_'+name
    P=p.part
    P('TPS61165DBVR',ref('U'),'TPS61165DBVR',95,100,{1:'UV_5V_SW',2:'UV_CTRL',3:local('SW'),4:'GND',5:local('COMP'),6:local('FB_RAW')},sot6,'Texas Instruments','TPS61165DBVR')
    P('PowerInductor',ref('L'),'10uH20% shielded',255,75,{1:'UV_5V_SW',2:local('SW')},coil,'Bourns','SRP4020TA-100M')
    P('PMEG6010CEH',ref('D'),'PMEG6010CEH,115',410,75,{1:local('VOUT'),2:local('SW')},diode,'Nexperia','PMEG6010CEH,115','Exact orderable12NC934061056115,SOD123F_115,3000/reel: https://www.nexperia.com/product/PMEG6010CEH')
    P('VLMU35CB20',ref('D',2),'VLMU35CB20-275-120',570,75,{1:local('LED_MID'),2:local('VOUT')},led,'Vishay','VLMU35CB20-275-120','Cathode mark must match pad1. Heatspreader/AlMCPCB must be qualified.')
    P('VLMU35CB20',ref('D',3),'VLMU35CB20-275-120',570,150,{1:local('LED_K'),2:local('LED_MID')},led,'Vishay','VLMU35CB20-275-120')
    P('DMN62D2U',ref('Q'),'DMN62D2U-7',680,270,{1:local('CATHODE_GATE'),2:local('FB_RAW'),3:local('LED_K')},sot3,'Diodes Incorporated','DMN62D2U-7','Cathode disconnect separate from input cuts; source is FB, not GND.')
    P('GH8',ref('J'),'SM08B-GHS-TB',95,300,{1:'UV_5V_SW',2:'GND',3:'UV_CTRL',4:local('FB'),5:local('VOUT_DIV'),6:'NTC_'+side,7:local('THERM_SEND'),8:'LOOP_'+loop+'_RAW','MP':'GND'},gh,'JST','SM08B-GHS-TB(LF)(SN)')
    P('NTC413',ref('TH'),'NTCLE413E2103F524A remote',255,450,{1:'NTC_'+side,2:'GND'},None,'Vishay','NTCLE413E2103F524A','Offboard dry thermistor on heatspreader; do not pot/overmold/immerse.',offboard=True)
    P('THERM67L',ref('S'),'67L045 remote NC45C',410,450,{1:local('THERM_SEND'),2:'LOOP_'+loop+'_RAW'},None,'Sensata','67L045','Offboard cutoff;10mA@5V reference only;actual voltage/contact life qualification pending.',offboard=True)
    rs=[(1,'3.65R1%100ppm',local('FB_RAW'),'GND',r0805,'Vishay','CRCW08053R65FKEA'),
        (2,'1k1%','UV_CTRL',local('CATHODE_GATE'),r0603,'Yageo','RC0603FR-071KL'),
        (3,'100k1%',local('CATHODE_GATE'),'GND',r0603,'Yageo','RC0603FR-07100KL'),
        (4,'100k1%',local('VOUT'),'GND',r0805,'Yageo','RC0805FR-07100KL'),
        (5,'1M1%',local('VOUT'),local('VOUT_SENSE'),r0805,'Yageo','RC0805FR-071ML'),
        (6,'68k1%',local('VOUT_SENSE'),'GND',r0603,'Yageo','RC0603FR-0768KL'),
        (7,'10k1%',local('VOUT_SENSE'),local('VOUT_DIV'),r0603,'Yageo','RC0603FR-0710KL'),
        (8,'10k1%',local('FB_RAW'),local('FB'),r0603,'Yageo','RC0603FR-0710KL')]
    for i,val,a,b,fp,mfr,mpn in rs:
        P('R',ref('R',i),val,255+155*((i-1)%3),170+65*((i-1)//3),{1:a,2:b},fp,mfr,mpn)
    caps=[(1,'4.7uF50VX7R','UV_5V_SW',c1210,'C3225X7R1H475K250AB'),
          (2,'4.7uF50VX7R',local('VOUT'),c1210,'C3225X7R1H475K250AB'),
          (3,'220nF25VX7R',local('COMP'),c0603,'C1608X7R1E224K080AC'),
          (4,'100nF25VX7R',local('FB'),c0603,'C1608X7R1E104K080AA'),
          (5,'100nF25VX7R',local('VOUT_DIV'),c0603,'C1608X7R1E104K080AA')]
    for i,val,net,fp,mpn in caps:
        P('C',ref('C',i),val,95+155*((i-1)%4),390 if i<5 else 455,{1:net,2:'GND'},fp,'TDK',mpn,
          'Require >=1uF effective over VIN4.3..5.25V/input or VOUT0..39V/output,temp,age. TI output recommendation1..10uF.' if i<3 else '')
    for i,net in enumerate(('NTC_'+side,'GND',local('THERM_SEND'),'LOOP_'+loop+'_RAW'),1):
        P('SolderLand',ref('TP',i),net,95+155*((i-1)%4),520,{1:net},land,'manual copper','Cu_D1.5mm_solder_land','Assembly wire termination for remote NTC/cutoff; restraint required.')
    for i,net in enumerate(('UV_5V_SW','GND','UV_CTRL')):p.flag('#FLG'+str(base+i),net,680,75+50*i)
    p.note('UV DRIVER: two series Vishay LEDs,200mV/3.65R=54.79mA nominal. CTRL static; no EasyScale/PWM.\nEach LED has only two electrical terminals. Cathode mark must match pin1. Local SW loop short; no HV hinge wires.\nCathode FET interrupts LED current on CTRL low; input cuts are on safety board.',40,25)
    p.note('OUTPUT:4.7uF50V,100k bleeder,1M/68k monitor. Output can remain charged after light stops.\nRequire >=1uF effective output at39V/temp/age. OVP37..39V; measure switch ringing. FB/VOUT filters10k/100nF.\nNTC controller owns pullup/filter. 67L045 thermal cutoff plus separate gold lid contact form hardware loop.',40,555)
    p.save()

if __name__=='__main__':
    build('BASE',400,'A')
    build('LID',500,'B')
