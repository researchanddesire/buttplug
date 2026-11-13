"""Separate source-qualified BLE/bridge circuit with real retained dock context.

No original leaf, routedMain150 or human BOM is modified. The new Main feed is
an additional circuit partition; physical placement/routing and MCAD follow.
"""
from pathlib import Path
import copy,hashlib,json,math,os,shutil,sys,uuid
H=Path(__file__).resolve().parent;ROOT=H.parents[3];E=H.parent
O=H/'case-radio';PROJECT='case-radio-system'
sys.path.insert(0,str(ROOT/'tools'))
import electronics_r0_generate as g
import kicad_sexp as s
NS=uuid.UUID('6ead9e47-2065-4819-a75a-9f4105996e77')
uid=lambda x:str(uuid.uuid5(NS,x));sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
TI=lambda x:'https://www.ti.com/lit/ds/symlink/'+x+'.pdf'


def main():
    (O/'context').mkdir(parents=True,exist_ok=True)
    (O/'new').mkdir(exist_ok=True)
    source=E/'dock-system';inputs={};trees={};entries=[]
    for p in sorted((source/'sheets').glob('*.kicad_sch')):
        inputs[str(p.relative_to(ROOT))]=sha(p);t=s.parse(p.read_text())
        trees[O/'context'/p.name]=t;entries.append((p.stem,'context/'+p.name,uid(p.stem)))
    assert len(entries)==6
    # Retained resistor footprints/poses are unchanged; only values/MPN metadata
    # differ in this unpublished circuit candidate, coupled with radio load.
    value_changes={
      'R107':('39.2k0.1%25ppm','RT0603BRD0739K2L','Yageo'),
      'R401':('4.22ohm1%100ppm','CRCW08054R22FKEA','Vishay'),
      'R501':('4.22ohm1%100ppm','CRCW08054R22FKEA','Vishay')}
    found=set()
    for tree in trees.values():
        for sy in s.children(tree,'symbol'):
            ref=s.prop(sy,'Reference')
            if ref not in value_changes:continue
            val,mpn,mfr=value_changes[ref];found.add(ref)
            next(p for p in s.children(sy,'property')if p[1].value=='Value')[2]=s.string(val)
            for name,value in [('MPN',mpn),('Manufacturer',mfr)]:
                item=next((p for p in s.children(sy,'property')if p[1].value==name),None)
                if item:item[2]=s.string(value)
                else:sy.append(s.parse(f'(property {g.q(name)} {g.q(value)} (at 0 0 0) {g.effects(extra="hide")})'))
    assert found==set(value_changes)
    # Connect only the two previously unconnected HSE-capable GPIOs. MSI/SWD
    # remain unchanged. Find actual cached-symbol pin geometry, not guessed XY.
    control=next(t for p,t in trees.items()if p.name=='dock-controller.kicad_sch')
    mcu=next(z for z in s.children(control,'symbol')if s.prop(z,'Reference')=='U201')
    lib=next(z for z in s.children(s.child(control,'lib_symbols'),'symbol')if z[1].value==s.value(mcu,'lib_id'))
    at=s.child(mcu,'at');x,y,rotation=map(lambda a:float(a.value),at[1:4]);assert rotation==0
    for number,net in [(5,'RADIO_IRQn'),(6,'PH1_RADIO_REQUEST')]:
        pin=next(p for unit in s.children(lib,'symbol')for p in s.children(unit,'pin')if s.value(p,'number')==str(number))
        pa=s.child(pin,'at');px=x+float(pa[1].value);py=y-float(pa[2].value);angle=float(pa[3].value)
        nc=[n for n in s.children(control,'no_connect')if abs(float(s.child(n,'at')[1].value)-px)<1e-6 and abs(float(s.child(n,'at')[2].value)-py)<1e-6]
        assert len(nc)==1,(number,nc);control.remove(nc[0])
        ex=round(px-5.08*math.cos(math.radians(angle)),4);ey=round(py+5.08*math.sin(math.radians(angle)),4)
        control.append(s.parse(f'(wire (pts(xy {px} {py})(xy {ex} {ey}))(stroke(width 0)(type default))(uuid {uid("MCUwire"+str(number))}))'))
        control.append(s.parse(f'(global_label {g.q(net)} (shape input)(at {ex} {ey} {180 if angle==0 else 0}){g.effects(1.016,"(justify right)"if angle==0 else"(justify left)")}(uuid {uid("MCUlabel"+str(number))}))'))
    g.LIB.clear();g.PARTS.clear();g.OUT=O/'new';g.PROJECT=PROJECT
    g.passive('R','R');g.passive('C','C');g.connector('Conn6',6)
    g.ic('TPS22950_YBH', [('B1','VIN','power_in'),('A1','ON','input'),('C2','ILIM','passive')],
         [('B2','VOUT','power_out'),('C1','GND','power_in'),('A2','FLTn','open_collector')],TI('tps22950'),'ActualYBH6WCSP pin map; fixed19.2k setting; FLT is not an ordinarycurrent-limitindicator')
    g.ic('SN74LVC1G97_DCK',[(1,'In1_tiedLOW','input'),(3,'In0_PH1request','input'),(6,'In2_SOURCE_OK','input')],
         [(4,'Y_AND','output'),(5,'VCC','power_in'),(2,'GND','power_in')],TI('sn74lvc1g97'),'SchmittAND: In1LOW =>Y=In2ANDIn0; accepts existingfilteredSOURCE_OK')
    g.ic('TLV70033_DDC',[(1,'IN','power_in'),(3,'EN','input')],[(5,'OUT','power_out'),(2,'GND','power_in'),(4,'NC','no_connect')],TI('tlv700'),'Localradio3V3LDO; neverburden theoldUI10mArail withmoduleload')
    g.ic('TPS3808G33_DBV',[(6,'VDD','power_in'),(5,'SENSE','input'),(3,'MRn','input')],[(1,'RESETn','open_collector'),(4,'CT','passive'),(2,'GND','power_in')],TI('tps3808'),'CTopen gives12..28msresetdelay; waitrealmodule startupURC')
    names={1:'SEL1',2:'S1',3:'D1',4:'SEL2',5:'S2',6:'D2',7:'NC7',8:'GND',9:'D3',10:'S3',11:'SEL3',12:'NC12',13:'D4',14:'S4',15:'SEL4',16:'VDD'}
    kinds=lambda n:'no_connect'if n in(7,12)else'power_in'if n in(8,16)else'input'if n in(1,4,11,15)else'passive'
    g.ic('TMUX1511_RSV',[(n,names[n],kinds(n))for n in range(1,9)],[(n,names[n],kinds(n))for n in range(9,17)],TI('tmux1511'),'ActualRSV16UQFN; powered-offprotection<=3.6V; threecontrols usehardwarequalifiedactiveEN')
    scnames={1:'RESETn',2:'XTAL1',3:'XTAL2',4:'VDD',5:'I2C_SPI',6:'A0',7:'A1',8:'NC',9:'SCL',10:'SDA',11:'IRQn',12:'GPIO0',13:'GPIO1',14:'GPIO2',15:'GPIO3',16:'VSS',17:'GPIO4',18:'GPIO5',19:'GPIO6',20:'GPIO7',21:'RTSn',22:'CTSn',23:'TX',24:'RX',25:'EP_GND'}
    def sckind(n):
        if n==8:return'no_connect'
        if n in(4,16,25):return'power_in'
        if n in(3,21,23):return'output'
        if n==11:return'open_collector'
        return'bidirectional'if n in(10,12,13,14,15,17,18,19,20)else'input'
    g.ic('SC16IS750_IBS',[(n,scnames[n],sckind(n))for n in range(1,14)],[(n,scnames[n],sckind(n))for n in range(14,26)],
         'https://www.nxp.com/docs/en/data-sheet/SC16IS740_750_760.pdf','HVQFN24SOT616-3,notTSSOPpinmap; exposedpad25isphysicalGNDland')
    ninanames={1:'RED',2:'IO2',3:'IO3',4:'IO4',5:'IO5',6:'GND6',7:'GREEN_SWITCH1',8:'BLUE',9:'VCC_IO',10:'VCC',11:'SWDCLK',12:'GND12',13:'ANT_B111_ONLY_NC',14:'GND14',15:'SWDIO',16:'UART_DTR',17:'UART_DSR',18:'SWITCH2',19:'RESETn',20:'UART_RTSn',21:'UART_CTSn',22:'UART_TX',23:'UART_RX',24:'IO24',25:'IO25',26:'GND26',27:'IO27',28:'NFC1',29:'NFC2',30:'GND30'}
    def nkind(n):
        if n in(6,9,10,12,14,26,30):return'power_in'
        if n in(1,8,16,20,22):return'output'
        if n in(11,17,18,19,21,23):return'input'
        return'bidirectional'
    g.ic('NINA_B112_05B',[(n,ninanames[n],nkind(n))for n in range(1,16)],[(n,ninanames[n],nkind(n))for n in range(16,31)],
         'https://content.u-blox.com/sites/default/files/NINA-B1_DataSheet_UBX-15019243.pdf','B112integratedPIFA/hardware02/u-connectXpress7.0; B111/1Uantenna variants not substituted',
         hidden=[(n,'GND','power_in',6)for n in range(31,43)])
    g.ic('ABM8G',[(1,'XTAL1','passive'),(3,'XTAL2','passive')],[(2,'CASE_GND2','passive'),(4,'CASE_GND4','passive')],
         'https://abracon.com/Resonators/ABM8G.pdf','ABM8G14.7456MHz,CL10pF,80ohmESR; oscillatorqualificationpending')
    parts=[]
    def P(sh,lib,ref,mpn,xy,nets,fp,partition,mfr,note=''):
        sh.part(lib,ref,mpn,*xy,{str(n):v for n,v in nets.items()},fp,note,domain='MAIN_T')
        parts.append(dict(ref=ref,mpn=mpn,manufacturer=mfr,footprint=fp,partition=partition,
                          pins={str(n):v for n,v in nets.items()},note=note))
    def R(sh,ref,value,xy,a,b,partition,mpn=None,prec=False):
        mpn=mpn or {'10k':'CRCW040210K0FKED','100k':'CRCW0402100KFKED','47k':'CRCW040247K0FKED','1k':'CRCW04021K00FKED','4k7':'CRCW04024K70FKED'}[value]
        P(sh,'R',ref,value,xy,{1:a,2:b},'Radio:R_0402_1005Metric',partition,'Vishay',mpn)
        parts[-1]['mpn']=mpn
    def C(sh,ref,value,xy,net,partition,mpn='C1005X7R1C104K050BC',fp='Radio:C_0402_1005Metric'):
        P(sh,'C',ref,value,xy,{1:net,2:'GND'},fp,partition,'TDK',mpn);parts[-1]['mpn']=mpn
    header='Radio:JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal'
    headernets={1:'RADIO_5V',2:'GND',3:'MON_I2C_SDA',4:'MON_I2C_SCL',5:'RADIO_IRQn',6:'RADIO_ACTIVE_EN'}
    sh=g.Sheet('10-radio-main-feed','Qualified radio branch / additions to retainedMain150');sh.paper='A2'
    P(sh,'SN74LVC1G97_DCK','U151','SN74LVC1G97DCKR',(101.6,78.74),{1:'GND',2:'GND',3:'PH1_RADIO_REQUEST',4:'RADIO_ACTIVE_EN',5:'3V3',6:'SOURCE_OK'},'DockUI:SOT-363_SC-70-6','Main additions','Texas Instruments')
    P(sh,'TPS22950_YBH','U150','TPS22950YBHR',(279.4,78.74),{'B1':'LOOP_5V','A1':'RADIO_ACTIVE_EN','C2':'RADIO_ILIM','B2':'RADIO_5V','C1':'GND','A2':None},'DockUI:Texas_YBH0006-C02_DSBGA-6_1.106x0.706mm_P0.4mm','Main additions','Texas Instruments')
    P(sh,'Conn6','J150','SM06B-GHS-TB(LF)(SN)',(457.2,78.74),headernets,header,'Main additions','JST','Limiter sitsbefore addedharness; connectorphysicalposeunqualified')
    for row in [('R150','19k1',(63.5,170.18),'RADIO_ILIM','RADIO_ILIM_RETURN','TNPW040219K1BEED'),('R151','100R',(190.5,170.18),'RADIO_ILIM_RETURN','GND','TNPW0402100RBEED'),('R152','100k',(317.5,170.18),'PH1_RADIO_REQUEST','GND',None),('R153','10k',(444.5,170.18),'3V3','RADIO_IRQn',None),('R154','100k',(63.5,243.84),'RADIO_ACTIVE_EN','GND',None)]:
        ref,val,xy,a,b,mpn=row;R(sh,ref,val,xy,a,b,'Main additions',mpn)
    C(sh,'C150','2u2/16V X5R',(190.5,243.84),'LOOP_5V','Main additions','C1608X5R1C225K080AB','Radio:C_0603_1608Metric')
    C(sh,'C151','100nF16V',(317.5,243.84),'RADIO_5V','Main additions')
    C(sh,'C152','100nF16V',(444.5,243.84),'3V3','Main additions')
    sh.note('SOURCE_OK ownsqualification. SchmittAND gatesrawPH1 anddisablesradio+bus immediatelyonsourceloss.\nDefaultPH1 request andACTIVE_ENpulldowns; fixed19.2kbranchlimit34..66mA beforeaddedharness.\nNoD+/D−connection, secondUSBPHY, chargerCEcontrol orUVsafetyoverride.\nR10739.2k and bothUVRSET4.22ohm are coupledunpublishedcandidates, not frozenbudgetchanges.',25.4,15.24,1.27)
    sh.save();entries.append(('Main radio feed','new/'+sh.name+'.kicad_sch',uid(sh.name)))
    sh=g.Sheet('11-radio-power-isolation','Radio supply / reset / powered-off bus isolation');sh.paper='A2'
    P(sh,'Conn6','J901','SM06B-GHS-TB(LF)(SN)',(76.2,81.28),headernets,header,'Radio addon','JST')
    P(sh,'TLV70033_DDC','U904','TLV70033DDCR',(228.6,81.28),{1:'RADIO_5V',3:'RADIO_5V',5:'RADIO_3V3',2:'GND',4:None},'DockUI:TSOT-23-5','Radio addon','Texas Instruments')
    P(sh,'TPS3808G33_DBV','U905','TPS3808G33DBVR',(406.4,81.28),{6:'RADIO_3V3',5:'RADIO_3V3',3:'RADIO_3V3',1:'RADIO_RESETn',4:None,2:'GND'},'DockUI:SOT-23-6','Radio addon','Texas Instruments')
    tmuxnets={1:'RADIO_ACTIVE_EN',2:'MON_I2C_SDA',3:'RADIO_I2C_SDA',4:'RADIO_ACTIVE_EN',5:'MON_I2C_SCL',6:'RADIO_I2C_SCL',7:None,8:'GND',9:'RADIO_IRQn',10:'SC16_IRQn',11:'RADIO_ACTIVE_EN',12:None,13:'GND',14:'GND',15:'GND',16:'RADIO_3V3'}
    P(sh,'TMUX1511_RSV','U903','TMUX1511RSVR',(101.6,220.98),tmuxnets,'Radio:TI_RSV0016A','Radio addon','Texas Instruments')
    R(sh,'R901','10k',(279.4,190.5),'RADIO_3V3','RADIO_RESETn','Radio addon')
    R(sh,'R905','1k',(406.4,190.5),'RADIO_3V3','SC16_IRQn','Radio addon')
    R(sh,'R906','4k7',(279.4,248.92),'RADIO_3V3','RADIO_I2C_SDA','Radio addon')
    R(sh,'R907','4k7',(406.4,248.92),'RADIO_3V3','RADIO_I2C_SCL','Radio addon')
    caps=[('C901','2u2/16V X5R',(63.5,330.2),'RADIO_5V','C1608X5R1C225K080AB','Radio:C_0603_1608Metric'),('C902','22uF25V X5R',(165.1,330.2),'RADIO_3V3','C2012X5R1E226M125AC','Radio:C_0805_2012Metric'),('C905','100nF16V',(266.7,330.2),'RADIO_3V3','C1005X7R1C104K050BC','Radio:C_0402_1005Metric'),('C906','100nF16V',(368.3,330.2),'RADIO_3V3','C1005X7R1C104K050BC','Radio:C_0402_1005Metric')]
    for ref,val,xy,net,mpn,fp in caps:C(sh,ref,val,xy,net,'Radio addon',mpn,fp)
    sh.note('Independentlocal3V3;NINA andSC16 reset together. CTopen12..28ms doesnotguaranteeBluetoothstartup.\nTMUXRSV16pinmap, notRWB12: powered-offsignals<=3.6V. SELfollowsSOURCE_OKANDPH1.\nSourcefall disconnectsI2C/IRQ whilecapacitorsdischarge; nonewUSBwirepath.\nIRQlocal1k ismanufacturerrequired; host10k andbothI2Cpullgroups countinaddedradio70mAallocation.',25.4,15.24,1.27)
    sh.save();entries.append(('Radio power and isolation','new/'+sh.name+'.kicad_sch',uid(sh.name)))
    sh=g.Sheet('12-radio-UART-GATT','NINA-B11205B / hardware-flow-controlled SC16 bridge');sh.paper='A2'
    nn={n:None for n in range(1,43)}
    nn.update({6:'GND',7:'NINA_SWITCH1',9:'RADIO_3V3',10:'RADIO_3V3',11:'NINA_SWDCLK',12:'GND',14:'GND',15:'NINA_SWDIO',16:'NINA_DTR',17:'NINA_DSR',18:'NINA_SWITCH2',19:'RADIO_RESETn',20:'NINA_RTSn',21:'NINA_CTSn',22:'NINA_TX',23:'NINA_RX',26:'GND',30:'GND'})
    nn.update({n:'GND'for n in range(31,43)})
    P(sh,'NINA_B112_05B','U901','NINA-B112-05B-00',(101.6,111.76),nn,'Radio:NINA-B112_OEM','Radio addon','u-blox')
    sc={n:None for n in range(1,26)};sc.update({1:'RADIO_RESETn',2:'SC16_XTAL1',3:'SC16_XTAL2',4:'RADIO_3V3',5:'RADIO_3V3',6:'GND',7:'GND',9:'RADIO_I2C_SCL',10:'RADIO_I2C_SDA',11:'SC16_IRQn',12:'NINA_DSR',13:'NINA_DTR',16:'GND',21:'NINA_CTSn',22:'NINA_RTSn',23:'NINA_RX',24:'NINA_TX',25:'GND'})
    P(sh,'SC16IS750_IBS','U902','SC16IS750IBS,128',(304.8,111.76),sc,'Radio:HVQFN-24-1EP_4x4mm_P0.5mm_EP2.5x2.5mm','Radio addon','NXP')
    P(sh,'ABM8G','Y901','ABM8G-14.7456MHZ-B4Y-T',(482.6,73.66),{1:'SC16_XTAL1',3:'SC16_XTAL2',2:'GND',4:'GND'},'Radio:Crystal_SMD_Abracon_ABM8G-4Pin_3.2x2.5mm','Radio addon','Abracon','CL10pF,ESR80ohm,−20..70C;12pFstartingcapsrequireoscillatorqualification')
    C(sh,'C907','12pF50V C0G',(431.8,152.4),'SC16_XTAL1','Radio addon','C1005C0G1H120J050BA')
    C(sh,'C908','12pF50V C0G',(533.4,152.4),'SC16_XTAL2','Radio addon','C1005C0G1H120J050BA')
    for ref,xy,net,val in [('R902',(63.5,238.76),'NINA_SWITCH1','10k'),('R903',(190.5,238.76),'NINA_SWITCH2','10k'),('R904',(317.5,238.76),'NINA_DSR','47k')]:R(sh,ref,val,xy,'RADIO_3V3',net,'Radio addon')
    C(sh,'C903','100nF16V',(63.5,304.8),'RADIO_3V3','Radio addon')
    C(sh,'C904','100nF16V',(190.5,304.8),'RADIO_3V3','Radio addon')
    P(sh,'Conn6','J902','TC2030-CTX-NL SWD CONTACT PATTERN',(406.4,304.8),{1:'RADIO_3V3',2:'NINA_SWDIO',3:'RADIO_RESETn',4:'NINA_SWDCLK',5:'GND',6:None},'DockControl:Tag-Connect_TC2030-IDC-NL_2x03_P1.27mm_Vertical','Radio manual copper','manual copper','NINAserviceonly; accessibleboot-switchpadsandSWD; notasecondUSBcontroller')
    sh.note('Sevenbit0x4D(A1/A0GND),actualHVQFNpinmap. FourUARTwiresincludeRTS/CTS.\nConfigureTCRhalt48/resume24BEFOREautoRTS;initializeDLL8/DLH0for14.7456MHz/115200.\nFactoryUMRSusesRTS/CTS;verifyreceivedpersistentsettings. DSRiscontrolledGPIO,notleftfloating.\nNoSPSassumption: NINAcentralGATTclientusesfrozen20Bservice; plugC3remainsnativeUSBendpoint.',25.4,15.24,1.27)
    sh.save();entries.append(('Radio module and UART','new/'+sh.name+'.kicad_sch',uid(sh.name)))
    # Namespace new cached definitions; all physical terminal mappings retained.
    for p in sorted((O/'new').glob('*.kicad_sch')):
        text=p.read_text().replace('PrototypeR0:','CaseRadio:');t=s.parse(text)
        for sy in s.children(t,'symbol'):
            ref=s.prop(sy,'Reference');d=next(v for v in parts if v['ref']==ref)
            for name,value in [('Manufacturer',d['manufacturer']),('MPN',d['mpn']),('BoardPartition',d['partition'])]:
                sy.append(s.parse(f'(property {g.q(name)} {g.q(value)} (at 0 0 0) {g.effects(extra="hide")})'))
        trees[p]=t
    root=s.parse(f'(kicad_sch (version 20230121)(generator case_telemetry_candidate)(uuid {uid(PROJECT)})(paper "A2")(title_block(title "Case BLE telemetry / retained USB and hardware safety")(date "2026-11-12")(rev "UNPUBLISHED CANDIDATE")(company "Research and Desire")(comment 1 "ORIGINAL ARTWORK UNCHANGED / NO POWERED OR RF ACCEPTANCE"))(lib_symbols)(sheet_instances(path "/"(page "1"))))')
    for i,(label,filename,identity)in enumerate(entries):
        x=25.4+(i%3)*190.5;y=76.2+(i//3)*63.5
        root.append(s.parse(f'(sheet(at {x} {y})(size 152.4 25.4)(fields_autoplaced)(stroke(width .15)(type default))(fill(color 0 0 0 0))(uuid {identity})(property "Sheetname" {g.q(label)}(at {x} {y-.5} 0){g.effects(1.27,"(justify left bottom)")})(property "Sheetfile" {g.q(filename)}(at {x} {y+25.9} 0){g.effects(1.016,"(justify left top)")}))'))
    trees[O/(PROJECT+'.kicad_sch')]=root
    for i,(label,file,identity)in enumerate(entries):
        t=trees[O/file]
        for sy in s.children(t,'symbol'):
            inst=s.child(sy,'instances')
            if inst is None:inst=s.parse('(instances)');sy.append(inst)
            inst.append(s.parse(f'(project {g.q(PROJECT)}(path {g.q("/"+uid(PROJECT)+"/"+identity)}(reference {g.q(s.prop(sy,"Reference"))})(unit {s.value(sy,"unit")or"1"})))'))
    # Existing libraries keep read-only ownership. New cached definitions are
    # independently provided underCaseRadio, and footprints underRadio.
    for table in ('sym-lib-table','fp-lib-table'):
        original=s.parse((source/table).read_text());inputs[str((source/table).relative_to(ROOT))]=sha(source/table)
        for lib in s.children(original,'lib'):
            uri=s.value(lib,'uri');target=Path(uri.replace('${KIPRJMOD}',str(source))).resolve()
            s.child(lib,'uri')[1]=s.string('${KIPRJMOD}/'+os.path.relpath(target,O))
        alias='CaseRadio'if table=='sym-lib-table'else'Radio';target='CaseRadio.kicad_sym'if table=='sym-lib-table'else'Radio.pretty'
        original.append(s.parse(f'(lib(name {g.q(alias)})(type "KiCad")(uri {g.q("${KIPRJMOD}/"+target)})(options "")(descr "Selected source-bound radio candidate"))'));s.write(O/table,original)
    libroot=s.parse('(kicad_symbol_lib(version 20220914)(generator case_telemetry_candidate))')
    for key in sorted(g.LIB):libroot.append(s.parse(g.LIB[key]['text']))
    s.write(O/'CaseRadio.kicad_sym',libroot)
    for p,t in trees.items():s.write(p,t)
    settings=json.loads((source/'dock-system.kicad_pro').read_text());settings.setdefault('erc',{})['erc_exclusions']=[]
    settings['erc']['rule_severities']={k:'warning'for k in('single_global_label','four_way_junction','simulation_model_issue','footprint_filter')}
    (O/(PROJECT+'.kicad_pro')).write_text(json.dumps(settings,indent=2)+'\n')
    report={'status':'Native complete-context case-radio circuit candidate; no sourcepromotion or routedPCBclaim',
            'builder_sha256':sha(Path(__file__)),'source_inputs_sha256':inputs,
            'retained_context_refs':234,'retained_Main_poses':150,'new_parts':parts,
            'intended_existing_pin_delta':{'U201.5':'previousNC→RADIO_IRQn','U201.6':'previousNC→PH1_RADIO_REQUEST'},
            'intended_existing_value_changes':value_changes,'new_supply_flags':False,
            'original_Main_board_sha256':sha(E/'dock-main/dock-main.kicad_pcb'),
            'frozen_protocol_sha256':sha(H/'protocol-v1.json'),
            'outputs_sha256':{str(p.relative_to(O)):sha(p)for p in trees},
            'standalone_radio_RF_and_clock_qualification':False,'physical_validation':False}
    (O/'source-bindings.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'retained_context_refs':234,'new_parts':len(parts),'new_Main_parts':sum(p['partition']=='Main additions'for p in parts),'new_radio_parts':sum(p['partition']!='Main additions'for p in parts)}))


if __name__=='__main__':main()
