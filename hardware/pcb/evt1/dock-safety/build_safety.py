"""Build the editable hardware interlock, latch and dual-cut safety circuit."""
from pathlib import Path
from native_helpers import Project, g

HERE = Path(__file__).resolve().parent
p = Project(HERE, 'dock-safety', 'EVT dock hardware safety',
            '66e7ca04-c7b0-4359-9939-37f9883e3a60', 'DockSafety')
p.sheet.paper = 'A1'
ti = lambda name: 'https://www.ti.com/lit/ds/symlink/' + name + '.pdf'
g.ic('TPS3431SDRBR', [(1,'VDD','power_in'),(3,'EN_HARD_HIGH','input'),(5,'SET1_HIGH','input'),(6,'WDI','input'),(2,'CWD','passive')],
     [(7,'WDO_N','open_collector'),(8,'ENOUT','open_collector'),(4,'GND','power_in'),(9,'EP_GND','power_in')],ti('tps3431'),
     'Falling-edge watchdog. EN/SET1 hardhigh; CWD10k selects170..230ms. EP grounded.')
g.ic('TPS3808G33DBVR', [(6,'VDD','power_in'),(5,'SENSE','input'),(3,'MR_N','input')],
     [(1,'RESET_N','open_collector'),(4,'CT','passive'),(2,'GND','power_in')],ti('tps3808'),
     '3.07V supervisor. CTopen=12..28ms; CT100ktoVDD=180..420ms.')
g.ic('MAX6816EUS_T',[(2,'IN_RAW','input'),(1,'GND','power_in')],[(3,'OUT_DEBOUNCED','output'),(4,'VCC','power_in')],
     'https://www.analog.com/media/en/technical-documentation/data-sheets/MAX6816-MAX6818.pdf',
     'Both-edge20..80ms debounce; UV delay minimum180ms exceedspendingtransition.')
g.ic('SN74LVC2G17DCKR',[(1,'1A_LOOP_A','input'),(3,'2A_LOOP_B','input'),(2,'GND','power_in')],
     [(6,'1Y_LOOP_A','output'),(4,'2Y_LOOP_B','output'),(5,'VCC','power_in')],ti('sn74lvc2g17'),
     '5.5V-tolerant Schmitt inputs translate drycontactloops to3V3.')
g.ic('SN74HCS21PWR',[(1,'1A','input'),(2,'1B','input'),(4,'1C','input'),(5,'1D','input'),
                       (9,'2A','input'),(10,'2B','input'),(12,'2C','input'),(13,'2D','input')],
     [(6,'1Y_RAW_SAFE','output'),(8,'2Y_CLEAR_N','output'),(14,'VCC','power_in'),(7,'GND','power_in'),(3,'NC','no_connect'),(11,'NC','no_connect')],
     ti('sn74hcs21'),'Schmitt dual4AND; accepts filteredSOURCE_OK and supervisor release edges.')
g.ic('SN74HCS08PWR',[(1,'1A','input'),(2,'1B','input'),(4,'2A','input'),(5,'2B','input'),
                       (9,'3A','input'),(10,'3B','input'),(12,'4A','input'),(13,'4B','input')],
     [(3,'1Y_ARM_D','output'),(6,'2Y_CUT_A','output'),(8,'3Y_CUT_B','output'),(11,'4Y_UV_CTRL','output'),(14,'VCC','power_in'),(7,'GND','power_in')],
     ti('sn74hcs08'),'FourSchmittANDs: armdata, independentcutA/B, boostCTRLafterpostcutPG.')
g.ic('SN74LVC74APWR',[(1,'1CLR_N','input'),(2,'1D','input'),(3,'1CLK_RELEASE','input'),(4,'1PRE_N','input'),
                        (10,'2PRE_N','input'),(11,'2CLK_PRESS','input'),(12,'2D_ARM','input'),(13,'2CLR_N','input')],
     [(5,'1Q_RELEASE_SEEN','output'),(6,'1Q_N','output'),(9,'2Q_UV_RUN','output'),(8,'2Q_N','output'),(14,'VCC','power_in'),(7,'GND','power_in')],
     ti('sn74lvc74a'),'Asyncclear bothlatches. Release armsfirstFF; laterfreshpress capturesMCU_ARM intoUV_RUN.')
g.ic('TPS22992RXPR',[(1,'VBIAS','power_in'),(2,'VIN','power_in'),(8,'ON','input'),(7,'CT','passive')],
     [(6,'VOUT','power_out'),(5,'QOD','passive'),(3,'PG','open_collector'),(4,'GND','power_in')],
     ti('tps22992'),'LowresistanceRXP8 asymmetriclandpattern. VBIASHOST5, VIN<=VBIAS. ON hasexternalpulldown.')
g.ic('TPS22919DCKR',[(1,'VIN','power_in'),(3,'ON','input')],
     [(6,'VOUT','power_out'),(5,'QOD','passive'),(2,'GND','power_in'),(4,'NC','no_connect')],
     ti('tps22919'),'Qualified-source-only lowlevelcontactloop supply; separate fromlimitedUVrail.')
g.ic('D2F_01L', [('C','COM','passive')],[('NO','NO_LID_CLOSED','passive'),('NC','NC_UNUSED','passive')],
     'https://omronfs.omron.com/en_US/ecb/products/pdf/en-d2f.pdf',
     'RemoteOmronD2F-01L goldmicroload hinge-lever. NCunused; independentmechanicalactuator.')
for n in (2,8):
    g.ic('GH'+str(n),[(i,str(i),'passive') for i in range(1,n+1)],[('MP','MOUNT_GND','passive')],
         'https://www.jst-mfg.com/product/pdf/eng/eGH.pdf','JSTGH keyedwireconnector; groundbothreinforcementpads.')

sc70=p.stock('Package_TO_SOT_SMD','SOT-363_SC-70-6')
sot6=p.stock('Package_TO_SOT_SMD','SOT-23-6')
sot143=p.stock('Package_TO_SOT_SMD','SOT-143')
tssop=p.stock('Package_SO','TSSOP-14_4.4x5mm_P0.65mm')
r0603=p.stock('Resistor_SMD','R_0603_1608Metric')
r0805=p.stock('Resistor_SMD','R_0805_2012Metric')
c0402=p.stock('Capacitor_SMD','C_0402_1005Metric')
c0603=p.stock('Capacitor_SMD','C_0603_1608Metric')
gh2=p.stock('Connector_JST','JST_GH_SM02B-GHS-TB_1x02-1MP_P1.25mm_Horizontal')
gh8=p.stock('Connector_JST','JST_GH_SM08B-GHS-TB_1x08-1MP_P1.25mm_Horizontal')
drb_pads=[(str(i+1),-1.4,-.975+.65*i,.6,.31,'rect') for i in range(4)]
drb_pads += [(str(8-i),1.4,-.975+.65*i,.6,.31,'rect') for i in range(4)]
drb_pads += [('9',0,0,1.5,1.75,'rect')]
drb_pads += [('9',x,y,.23,.825,'rect') for x in (-.325,.325) for y in (-1.2875,1.2875)]
drb=p.custom('Texas_DRB0008A_3x3mm_P0.65_EP_Fingers',drb_pads,(3,3),(3.9,3.9),ti('tps3431')+'#page=29')
rxp_pads=[('1',-.6,-.5,.45,.25,'rect'),('2',-.475,0,.7,.25,'rect'),('3',-.6,.5,.45,.25,'rect'),
          ('4',0,.6625,.25,.575,'rect'),('5',.6,.5,.45,.25,'rect'),('6',.475,0,.7,.25,'rect'),
          ('7',.6,-.5,.45,.25,'rect'),('8',0,-.6625,.25,.575,'rect')]
rxp=p.custom('Texas_RXP0008A_1.25x1.5mm_Asymmetric',rxp_pads,(1.25,1.5),(2.15,2.4),ti('tps22992')+'#page=27')
P=p.part
P('MAX6816EUS_T','U608','MAX6816EUS+T',75,75,{1:'GND',2:'BTN_CENTERn_RAW',3:'BTN_CENTERn_DEBOUNCED',4:'3V3'},sot143,'Analog Devices','MAX6816EUS+T')
P('TPS22919DCKR','U602','TPS22919DCKR',540,260,{1:'HOST_5V',2:'GND',3:'SOURCE_OK',4:None,5:'LOOP_5V',6:'LOOP_5V'},sc70,'Texas Instruments','TPS22919DCKR','Bothloopsrequire10mAminimumreference; disabledwithoutqualifiedRp. QODdirecttoVOUT.')
P('TPS3431SDRBR','U606','TPS3431SDRBR',230,75,{1:'3V3',2:'WDT_CWD',3:'3V3',4:'GND',5:'3V3',6:'WDI',7:'SAFE_RESETn',8:'SAFE_RESETn',9:'GND'},drb,'Texas Instruments','TPS3431SDRBR')
P('TPS3808G33DBVR','U607','TPS3808G33DBVR',385,75,{1:'SAFE_RESETn',2:'GND',3:'3V3',4:None,5:'3V3',6:'3V3'},sot6,'Texas Instruments','TPS3808G33DBVR','CTintentionallyopen selects20msnominal.')
P('TPS3808G33DBVR','U616','TPS3808G33DBVR',540,75,{1:'UV_DELAYn',2:'GND',3:'RAW_SAFE',4:'UV_DELAY_CT',5:'3V3',6:'3V3'},sot6,'Texas Instruments','TPS3808G33DBVR','MRincludesSAFE_RESETn so watchdogrecovery also requalifiesUV.')
P('SN74LVC2G17DCKR','U613','SN74LVC2G17DCKR',75,175,{1:'LOOP_A_RAW',2:'GND',3:'LOOP_B_RAW',4:'LOOP_B',5:'3V3',6:'LOOP_A'},sc70,'Texas Instruments','SN74LVC2G17DCKR')
P('SN74LVC2G17DCKR','U614','SN74LVC2G17DCKR',75,110,{1:'BTN_CENTERn_DEBOUNCED',2:'GND',3:'BTN_CENTER_PRESSED',4:'CLOCK_PRESS',5:'3V3',6:'CLOCK_RELEASE'},sc70,'Texas Instruments','SN74LVC2G17DCKR','LocalSchmittclockconditioning keepsLVC74clockedgesfast evenifinterboardclockwireisdisconnected.')
P('SN74HCS21PWR','U612','SN74HCS21PWR',230,175,{1:'LOOP_A',2:'LOOP_B',3:None,4:'SOURCE_OK',5:'SAFE_RESETn',6:'RAW_SAFE',7:'GND',8:'CLEARn',9:'RAW_SAFE',10:'MCU_STOPn',11:None,12:'UV_DELAYn',13:'3V3',14:'3V3'},tssop,'Texas Instruments','SN74HCS21PWR','Pins3/11 are manufacturerNC, not tiedtoanything.')
P('SN74LVC74APWR','U609','SN74LVC74APWR',385,175,{1:'CLEARn',2:'3V3',3:'CLOCK_RELEASE',4:'3V3',5:'RELEASE_SEEN',6:None,7:'GND',8:None,9:'UV_RUN',10:'3V3',11:'CLOCK_PRESS',12:'ARM_D',13:'CLEARn',14:'3V3'},tssop,'Texas Instruments','SN74LVC74APWR','Complementoutputs6/8 deliberatelyunused; bothPREtiedhigh.')
P('SN74HCS08PWR','U615','SN74HCS08PWR',540,175,{1:'RELEASE_SEEN',2:'MCU_ARM',3:'ARM_D',4:'LOOP_A',5:'SOURCE_OK',6:'UV_GATE_A',7:'GND',8:'UV_GATE_B',9:'UV_RUN',10:'LOOP_B',11:'UV_CTRL',12:'UV_RUN',13:'UV_POWER_GOOD',14:'3V3'},tssop,'Texas Instruments','SN74HCS08PWR','UV_CTRL waitsforpostcutPG; UV_RUN alreadyasynchronouslyclearedbyCLEARn.')
P('TPS22992RXPR','U610','TPS22992RXPR',230,270,{1:'HOST_5V',2:'UV_5V_LIMITED',3:None,4:'GND',5:'CUT_A_QOD',6:'UV_5V_MID',7:'CUT_A_CT',8:'UV_GATE_A'},rxp,'Texas Instruments','TPS22992RXPR','OptionalPGunused. BiasHOST5keepsVIN<=VBIAS innormaloperation.')
P('TPS22992RXPR','U611','TPS22992RXPR',385,270,{1:'HOST_5V',2:'UV_5V_MID',3:'UV_POWER_GOOD',4:'GND',5:'CUT_B_QOD',6:'UV_5V_SW',7:'CUT_B_CT',8:'UV_GATE_B'},rxp,'Texas Instruments','TPS22992RXPR','PGholdsboostCTRLlowuntilfinalrailready; PGdoesnotgateUV_RUN orstartwoulddeadlock.')
for ref,x,net in [('S601',75,'BASE_THERM_SEND'),('S602',75,'LID_THERM_SEND')]:
    y=270 if ref=='S601' else 330
    P('D2F_01L',ref,'D2F-01L remote',x,y,{'C':'LOOP_5V','NO':net,'NC':None},None,'Omron','D2F-01L','MechanicallymountedoffsafetyPCB; solder/crimpwires viaGH2. TerminalC/NO/NC markingsareauthoritative.',offboard=True)
for ref,y,net in [('J601',390,'BASE_THERM_SEND'),('J602',455,'LID_THERM_SEND')]:
    P('GH2',ref,'SM02B-GHS-TB',75,y,{1:'LOOP_5V',2:net,'MP':'GND'},gh2,'JST','SM02B-GHS-TB(LF)(SN)')
for ref,x,side,loop in [('J621',230,'BASE','A'),('J622',385,'LID','B')]:
    P('GH8',ref,'SM08B-GHS-TB',x,450,{1:'UV_5V_SW',2:'GND',3:'UV_CTRL',4:side+'_FB',5:side+'_VOUT_DIV',6:'NTC_'+side,7:side+'_THERM_SEND',8:'LOOP_'+loop+'_RAW','MP':'GND'},gh8,'JST','SM08B-GHS-TB(LF)(SN)','Straight1:1toUVmoduleGH8; onlylowvoltage rails andmonitors crosshinge.')
resistors=[('R601','10k 1%','3V3','SAFE_RESETn','RC0603FR-0710KL',r0603),
 ('R602','100k 1%','WDI','GND','RC0603FR-07100KL',r0603),
 ('R603','10k 1%','3V3','WDT_CWD','RC0603FR-0710KL',r0603),
 ('R604','100k 1%','MCU_ARM','GND','RC0603FR-07100KL',r0603),
 ('R605','100k 1%','MCU_STOPn','GND','RC0603FR-07100KL',r0603),
 ('R606','1k 1%','SAFE_RESETn','MCU_NRSTn','RC0603FR-071KL',r0603),
 ('R607','10k 1%','3V3','UV_DELAYn','RC0603FR-0710KL',r0603),
 ('R608','100k 1%','3V3','UV_DELAY_CT','RC0603FR-07100KL',r0603),
 ('R610','330R 1%','UV_5V_MID','CUT_A_QOD','CRCW0805330RFKEA',r0805),
 ('R611','330R 1%','UV_5V_SW','CUT_B_QOD','CRCW0805330RFKEA',r0805),
 ('R612','100k 1%','UV_GATE_A','GND','RC0603FR-07100KL',r0603),
 ('R613','100k 1%','UV_GATE_B','GND','RC0603FR-07100KL',r0603),
 ('R614','430R 1%','LOOP_A_RAW','GND','CRCW0805430RFKEA',r0805),
 ('R615','430R 1%','LOOP_B_RAW','GND','CRCW0805430RFKEA',r0805),
 ('R616','10k 1%','3V3','UV_POWER_GOOD','RC0603FR-0710KL',r0603),
 ('R617','100k 1%','3V3','BTN_CENTERn_RAW','RC0603FR-07100KL',r0603),
 ('R618','1M 1%','SOURCE_OK','GND','RC0603FR-071ML',r0603),
 ('R619','47k 1%','BTN_CENTER_PRESSED','GND','RC0603FR-0747KL',r0603)]
for i,(ref,val,a,b,mpn,foot) in enumerate(resistors):
    x,y=(520+70*(i%4),280+60*(i//4)) if i<15 else(145,[340,400,485][i-15])
    P('R',ref,val,x,y,{1:a,2:b},foot,'Vishay' if mpn.startswith('CRCW') else'Yageo',mpn)
caps=[('C606','3V3'),('C607','3V3'),('C608','3V3'),('C609','3V3'),('C612','3V3'),('C613','3V3'),('C614','3V3'),('C615','3V3'),('C616','3V3'),('C610','HOST_5V'),('C611','HOST_5V'),('C602','HOST_5V')]
for i,(ref,net) in enumerate(caps):
    P('C',ref,'100nF16V',490+55*(i%4),500+25*(i//4),{1:net,2:'GND'},c0402,'Murata','GRM155R71C104KA88D')
for ref,x,net in [('C620',230,'UV_5V_LIMITED'),('C621',300,'UV_5V_MID'),('C622',370,'UV_5V_SW')]:
    P('C',ref,'1uF25V',x,355,{1:net,2:'GND'},c0603,'TDK','C1608X7R1E105K080AB')
for ref,x,net in [('C623',450,'CUT_A_CT'),('C624',450,'CUT_B_CT')]:
    y=340 if ref=='C623' else 400
    P('C',ref,'1nF50V C0G',x,y,{1:net,2:'GND'},c0603,'TDK','C1608C0G1H102J080AA')
for i,net in enumerate(('3V3','GND','HOST_5V','UV_5V_LIMITED')):p.flag('#FLG'+str(601+i),net,680+100*(i%2),65+45*(i//2))
g.connector('TestLand',1)
tp=p.stock('TestPoint','TestPoint_Pad_D1.0mm')
for i,net in enumerate(('MCU_NRSTn','BASE_FB','LID_FB','BASE_VOUT_DIV','LID_VOUT_DIV','NTC_BASE','NTC_LID')):
    P('TestLand','TP'+str(601+i),net,680+100*(i//4),155+30*(i%4),{1:net},tp,'manual copper','Cu_D1.0mm_test_land','Realprobeaccessforinterboardreset/ADCsignals; no purchasedconnector.')
p.note('HARDWARE INTERFACES: inputs3V3/HOST5/UV5LIMITED/SOURCE_OK fromdocksource. MCUinputsARM,STOPn,WDI defaultLOW.\nCENTERdebouncedOUT goes tosourceU114pin3; sourceU114pin4returnsBTN_CENTER_PRESSED.\nMCU_NRSTn isseparatefromSAFE_RESETn byR6061k tolimit100nF localresetcapdischarge.',40,25)
p.note('DUALPHYSICALLOOPS: qualifiedHOST5 -> D2F NO -> respectiveUVmodule67L045NC -> LOOP_RAW ->430RGND.\nThermostatlowlevelreference10mA: eachloop10.35mAmin/12.34mAmax. U602turnsloopsoff onlegacyUSB.\nDisconnectedwirepreventsUV. Bothlatchesclear onfault/STOP; watchdogrecoverygetsUVdelay. Release,thenfreshpressrequired.',40,510)
p.note('UV powercutsuseTPS22992lowRON insteadTPS22919. QOD330R ispopulated. PGonlygatesboostCTRL, notUV_RUN.\nFullsource/cablelossbudget, hardwaretiming/shutdown opticaltail andsinglefaulttests remainunqualified.\nPWR_FLAGs identifyexternalrails inthisstandalonecandidate; theyarenotboardcomponents. NO sterilizationclaim.',40,555)
p.save()
