"""Exact EVT1 PCB ordering worksheet from native netlists and reviewed parts.

The human-owned hardware/bom.csv is not edited. Copper-only interfaces and
the open charge-permission jumper are assembly operations, not bought parts.
This worksheet does not claim stock, supplier acceptance or physical tests.
"""
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as E

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'hardware/pcb/evt1'
DOMAINS=('body','flange','sensor','dock','pins')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
VISHAY='https://www.vishay.com/docs/28758/tnpw_e3.pdf'
SH='https://www.jst-mfg.com/product/pdf/eng/eSH.pdf'
MURATA='https://www.murata.com/en-global/api/pdfdownloadapi?cate=luCeramicCapacitorsSMD&partno='
TDK='https://product.tdk.com/en/search/capacitor/ceramic/mlcc/info?part_no='

def murata(number):return MURATA+number[:-1]+'%23'
def part(mpn,maker,source,height,**extra):
    return {'mpn':mpn,'manufacturer':maker,'manufacturer_source':source,'maximum_height_mm':height,**extra}

CAPS={
 ('0402',1e-7):part('GRM155R71C104KA88D','Murata',murata('GRM155R71C104KA88D'),.55,capacitance_F=1e-7,rated_voltage_V=16,tolerance_percent=10,dielectric='X7R',maximum_body_xy_mm=[1.05,.55]),
 ('0402',2.2e-7):part('GRM155R71C224KA12D','Murata',murata('GRM155R71C224KA12D'),.55,capacitance_F=2.2e-7,rated_voltage_V=16,tolerance_percent=10,dielectric='X7R',maximum_body_xy_mm=[1.05,.55]),
 ('0402',1e-8):part('GRM155R71H103KA88D','Murata',murata('GRM155R71H103KA88D'),.55,capacitance_F=1e-8,rated_voltage_V=50,tolerance_percent=10,dielectric='X7R',maximum_body_xy_mm=[1.05,.55]),
 ('0603',1e-7):part('GRM188R71C104KA01D','Murata',murata('GRM188R71C104KA01D'),.9,capacitance_F=1e-7,rated_voltage_V=16,tolerance_percent=10,dielectric='X7R',maximum_body_xy_mm=[1.7,.9]),
 ('0603',1e-6):part('C1608X7R1E105K080AB','TDK',TDK+'C1608X7R1E105K080AB',.9,capacitance_F=1e-6,rated_voltage_V=25,tolerance_percent=10,dielectric='X7R',maximum_body_xy_mm=[1.7,.9]),
 ('0603',1e-5):part('C1608X5R1A106K080AC','TDK',TDK+'C1608X5R1A106K080AC',.9,capacitance_F=1e-5,rated_voltage_V=10,tolerance_percent=10,dielectric='X5R',maximum_body_xy_mm=[1.7,.9]),
 ('0805',4.7e-6):part('GRM21BR71A475KA73L','Murata',murata('GRM21BR71A475KA73L'),1.4,capacitance_F=4.7e-6,rated_voltage_V=10,tolerance_percent=10,dielectric='X7R',maximum_body_xy_mm=[2.1,1.35]),
 ('0805',1e-5):part('GRM21BR61A106KE19L','Murata',murata('GRM21BR61A106KE19L'),1.35,capacitance_F=1e-5,rated_voltage_V=10,tolerance_percent=10,dielectric='X5R',maximum_body_xy_mm=[2.1,1.35]),
 ('0805',2.2e-5):part('C2012X5R1E226M125AC','TDK',TDK+'C2012X5R1E226M125AC',1.45,capacitance_F=2.2e-5,rated_voltage_V=25,tolerance_percent=20,dielectric='X5R',maximum_body_xy_mm=[2.2,1.45],assembly_note='C83 incoming/process acceptance: >=10uF effective at3.3V over intended temperature/age. Nominal22uF and voltage rating alone are not acceptance; manufacturer curves are reference data.'),
 ('1206',2.2e-5):part('GRM31CR71A226KE15L','Murata',murata('GRM31CR71A226KE15L'),2.7,capacitance_F=2.2e-5,rated_voltage_V=10,tolerance_percent=10,dielectric='X7R',maximum_body_xy_mm=[3.4,1.8]),
 ('1210',4.7e-5):part('GRM32ER61A476KE20L','Murata',murata('GRM32ER61A476KE20L'),2.7,capacitance_F=4.7e-5,rated_voltage_V=10,tolerance_percent=10,dielectric='X5R',maximum_body_xy_mm=[3.4,2.7]),
}
RESISTANCE_CODES={1000:'1K00',3240:'3K24',4700:'4K70',5100:'5K10',8870:'8K87',10000:'10K0',11000:'11K0',22:'22R0',100000:'100K',110000:'110K',200000:'200K',312000:'312K',362000:'362K',715000:'715K',1000000:'1M00'}
FEATURES={'body:J2':'Five copper lands; solder protected-pack power and two independently returned NTC channels.',
          'body:J81':'Four hand-solder sensor-loom lands; ground land intentionally includes a plated via.',
          'body:JP1':'Leave copper solder jumper OPEN until charge-guard commissioning passes.',
          'flange:J1':'Four hand-solder fixed-contact loom lands.',
          'sensor:J82':'Four hand-solder sensor-loom lands; no plug/header.',
          'dock:J93':'Four hand-solder pin-board loom lands.',
          'dock:TP91':'Copper fault test pad; no purchased test pin.',
          'pins:J94':'Four B.Cu hand-solder loom lands; solder before fitting the rear retainer.'}
ICS={
 'body:U1':('BQ24074RGTR','Texas Instruments','bq24074',1),
 'body:U2':('TPS63070RNMR','Texas Instruments','tps63070',1),
 'body:U3':('TPS63070RNMR','Texas Instruments','tps63070',1),
 'body:U4':('SN74LVC1G11DBVR','Texas Instruments','sn74lvc1g11',1.45),
 'body:U5':('DRV8212DSGR','Texas Instruments','drv8212',.8),
 'body:U7':('ADS1115IDGSR','Texas Instruments','ads1115',1.1),
 'body:U8':('TPS3700DDCR','Texas Instruments','tps3700',1.1),
 'body:U9':('TPS3808G33DBVR','Texas Instruments','tps3808',1.45),
 'flange:U71':('TPS3422EGDRYR','Texas Instruments','tps3422',.65),
 'dock:U92':('TPS2553DBVR','Texas Instruments','tps2553',1.45),
}

def case(footprint):
    for size in ('0402','0603','0805','1206','1210'):
        if size in footprint:return size
    raise AssertionError(('Unknown passive case',footprint))

def select(domain,ref,value,footprint):
    key=domain+':'+ref
    if key in FEATURES:return {'mpn':None,'manufacturer':None,'purchase':False,'assembly_note':FEATURES[key],'maximum_height_mm':0}
    if ref.startswith('R'):
        m=re.match(r'([\d.]+)([kKM]?)',value);ohms=round(float(m[1])*{'':1,'k':1000,'K':1000,'M':1000000}[m[2]],8);size=case(footprint)
        if key=='dock:R93':return part('CRCW0402210KFKED','Vishay','https://www.vishay.com/docs/20035/dcrcwe3.pdf',.4,resistance_ohm=210000,tolerance_percent=1,maximum_body_xy_mm=[1.05,.6])
        mpn='TNPW'+size+RESISTANCE_CODES[ohms]+('BEED' if size=='0402' else 'BEEA')
        return part(mpn,'Vishay',VISHAY,.55,resistance_ohm=ohms,tolerance_percent=.1,maximum_body_xy_mm={'0402':[1.1,.6],'0603':[1.7,.95],'0805':[2.1,1.4]}[size])
    if ref.startswith('C'):
        m=re.match(r'([\d.]+)([unp])F',value);assert m,(key,value)
        capacitance=float(m[1])*{'u':1e-6,'n':1e-9,'p':1e-12}[m[2]]
        return next(v.copy() for (size,number),v in CAPS.items() if size==case(footprint) and abs(number/capacitance-1)<1e-8)
    if key in ICS:
        mpn,maker,doc,h=ICS[key];return part(mpn,maker,'https://www.ti.com/lit/ds/symlink/'+doc+'.pdf',h)
    if ref.startswith('L'):return part('XFL4020-152MEC','Coilcraft','https://www.coilcraft.com/getmedia/50632d43-da1b-4cdb-8ab4-3029cab51df3/xfl4020.pdf',2.1,inductance_H=1.5e-6,tolerance_percent=20,maximum_body_xy_mm=[4.3,4.3],DCR_max_ohm=.0158,Isat_10percent_drop_A=4.1,assembly_note='Isat is specified at25C. Check transient/current/thermal behavior on assembled regulators; use manufacturer land pattern.')
    if key=='body:Q1':return part('AO3400A','Alpha and Omega Semiconductor','https://www.aosmd.com/sites/default/files/res/datasheets/AO3400A.pdf',1.25)
    if key=='flange:D1':return part('B140HW-7','Diodes Incorporated','https://www.diodes.com/datasheet/download/B140HW.pdf',1.35,assembly_note='Custom footprint uses logical pad1 ANODE /pad2 CATHODE. Physical cathode stripe goes at the CAD cathode bar/pad2; do not assume generic diode pad1 numbering.')
    if key=='flange:F1':return part('1206L050YR','Littelfuse','https://www.littelfuse.com/assetdocs/resettable-ptcs-1206l-datasheet?assetguid=2b6a1515-d4ee-4c83-8bd4-152b4901b8f5',.75,assembly_note='500mA hold PTC, not a precise current limiter. Use6V variant matching this exact part/height, not a taller alternate.')
    if key=='flange:U6':return part('ESP32-C3-MINI-1-N4X','Espressif','https://documentation.espressif.com/esp32-c3-mini-1_datasheet_en.html',2.55,assembly_note='Preserve four-layer copper/antenna keepout. Quote stencil/ground-pad process using the native custom53-pad footprint.')
    if key in ('flange:U75','dock:U91'):return part('USBLC6-2SC6','STMicroelectronics','https://www.st.com/resource/en/datasheet/usblc6-2.pdf',1.45)
    if ref in ('D71','D72','D73'):return part('BAT54WS-E3-08','Vishay','https://www.vishay.com/docs/86465/bat54ws.pdf',1.25)
    if key=='sensor:U81':return part('LSM303AGRTR','STMicroelectronics','https://www.st.com/resource/en/datasheet/lsm303agr.pdf',1.1,assembly_note='Pin1 and fixed package orientation must match the native footprint. Do not rotate for convenience; board registers to the molded back arrow.')
    if key in ('flange:SW1','flange:SW2'):return part('B3U-1000P','Omron','https://omronfs.omron.com/en_US/ecb/products/pdf/en-b3u.pdf',1.75)
    if key=='dock:J91':return part('USB4105-GF-A-120','GCT','https://gct.co/files/drawings/usb4105.pdf',3.41)
    if domain=='pins' and ref in ('P91','P92','P93','P94'):return part('0906-2-15-20-75-14-11-0','Mill-Max','https://www.mill-max.com/products/spring-loaded/0906',None,assembly_note='Spring pin through1mm board; height/stroke are set by the carrier/retainer, not a generic component-height box.')
    headers={'body:J3':'SM02B-SRSS-TB','body:J5':'BM02B-SRSS-TB','body:J6':'SM10B-SRSS-TB','flange:J7':'SM10B-SRSS-TB','flange:J4':'SM06B-SRSS-TB'}
    if key in headers:return part(headers[key]+'(LF)(SN)','JST',SH,2.9 if key=='body:J5' else 2.95,assembly_note='Board header only. Order matching SHR housings/SSH terminals or qualified precrimp leads separately; flange ends are housed only after feeding free terminals through the neck.')
    raise AssertionError(('No exact purchase selection',key,value,footprint))


def main():
    rows=[];bindings={};groups=defaultdict(list)
    for domain in DOMAINS:
        path=BASE/domain/(domain+'-native.xml');bindings[str(path.relative_to(ROOT))]=sha(path)
        mcad=json.loads((BASE/domain/'mcad.json').read_text());height={c['ref']:c['height_budget_mm'] for c in mcad['components']}
        for comp in E.parse(path).getroot().findall('./components/comp'):
            ref=comp.get('ref');value=comp.findtext('value');footprint=comp.findtext('footprint');p=select(domain,ref,value,footprint)
            p.update({'domain':domain,'ref':ref,'schematic_value':value,'footprint':footprint,'purchase':p.get('purchase',True)})
            if p['purchase'] and p['maximum_height_mm'] is not None:
                assert p['maximum_height_mm']<=height[ref]+1e-8,(domain,ref,'Selected part exceeds CAD height',p['maximum_height_mm'],height[ref])
            rows.append(p)
            if p['purchase']:groups[(p['manufacturer'],p['mpn'])].append(p)
    assert len({(r['domain'],r['ref']) for r in rows})==len(rows)
    report={'scope':'Exact PCB component selections for EVT assembly quoting; human-owned product BOM unchanged',
            'source_netlist_sha256':bindings,'builder_sha256':sha(Path(__file__)),'components':rows,
            'purchased_positions':sum(r['purchase'] for r in rows),'PCB_features_not_purchased':sum(not r['purchase'] for r in rows),
            'unique_purchase_lines':len(groups),'stock_or_supplier_acceptance':False,'physical_validation':False,
            'full_product_order_ready':False,'process_acceptance_after_purchase':['C83 effective capacitance >=10uF at3.3V over intended temperature/age',
                'Regulator effective capacitance, startup/transient/thermal behavior','Paste/reflow and polarized-part orientation','Incoming dimensions/received parts, soldering and actual fit']}
    (BASE/'parts-selection.json').write_text(json.dumps(report,indent=2)+'\n')
    with (BASE/'pcb-ordering.csv').open('w',newline='') as f:
        out=csv.writer(f);out.writerow(['Manufacturer','MPN','Qty_per_complete_device_and_dock','References','Value','Footprints','Manufacturer_source','Assembly_note'])
        for (maker,mpn),parts in sorted(groups.items()):
            out.writerow([maker,mpn,len(parts),' '.join(p['domain']+':'+p['ref'] for p in parts),'; '.join(sorted({p['schematic_value'] for p in parts})),'; '.join(sorted({p['footprint'] for p in parts})),parts[0]['manufacturer_source'],'; '.join(sorted({p.get('assembly_note','') for p in parts if p.get('assembly_note')}))])
    print(json.dumps({k:report[k] for k in ('purchased_positions','PCB_features_not_purchased','unique_purchase_lines','full_product_order_ready')}))


if __name__=='__main__':main()
