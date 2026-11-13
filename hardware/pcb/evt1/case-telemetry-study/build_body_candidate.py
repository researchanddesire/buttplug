"""New native instrumentation candidate; originals and frozen artwork read-only.

The retained body has69 positions. Two former grounded ADS inputs are reused;
all other existing endpoints and the complete independent charge guard remain.
"""
from pathlib import Path
import copy
import hashlib
import json
import os
import sys
import uuid

H = Path(__file__).resolve().parent
E = H.parent
ROOT = H.parents[3]
sys.path.insert(0, str(ROOT/'tools'))
import kicad_sexp as s
import electronics_r0_generate as g
from build_evt1_electrical import patch_pin_label, append_sheet

OUT = H/'body-instrumentation'
PROJECT = 'instrumented-device'
NS = uuid.UUID('dc1abcaa-5df1-453b-805e-0b4c1e6f2086')
uid = lambda x: str(uuid.uuid5(NS,x))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    (OUT/'body').mkdir(exist_ok=True)
    (OUT/'flange').mkdir(exist_ok=True)
    trees, inputs = {}, {}
    # Read-only current merged-flange circuit, not its fabrication artwork.
    src = E/'single-flange-routing'
    for p in sorted((src/'sheets').glob('*.kicad_sch')):
        inputs[str(p.relative_to(ROOT))] = sha(p)
        trees[OUT/'flange'/p.name] = s.parse(p.read_text())
    p = src/'single-flange.kicad_sch'
    inputs[str(p.relative_to(ROOT))] = sha(p)
    t = s.parse(p.read_text())
    for sh in s.children(t,'sheet'):
        prop = next(p for p in s.children(sh,'property') if p[1].value=='Sheetfile')
        prop[2] = s.string(Path(prop[2].value).name)
    trees[OUT/'flange/flange.kicad_sch'] = t
    for p in sorted((E/'body').glob('*.kicad_sch')):
        inputs[str(p.relative_to(ROOT))] = sha(p)
        trees[OUT/'body'/p.name] = s.parse(p.read_text())
    for name in ('external-04-sensors.kicad_sch','external-05-charge-guard.kicad_sch'):
        p = E/name
        inputs[str(p.relative_to(ROOT))] = sha(p)
        trees[OUT/name] = s.parse(p.read_text())
    patch_pin_label(trees[OUT/'body/04-sensors.kicad_sch'],'U7',6,'CHARGE_CURRENT_ADC')
    patch_pin_label(trees[OUT/'body/04-sensors.kicad_sch'],'U7',7,'CHARGE_TS_ADC')
    g.LIB.clear(); g.PARTS.clear(); g.OUT=OUT/'body'; g.PROJECT=PROJECT
    g.passive('R','R'); g.passive('C','C')
    g.ic('OPA391_DCK',[(1,'IN+','input'),(3,'IN-','input')],
         [(4,'OUT','output'),(5,'V+','power_in'),(2,'V-','power_in')],
         'https://www.ti.com/lit/ds/symlink/opa391.pdf',
         'Selected production SC70DCK pinout; DBV pinout/preview not used')
    g.ic('TCA9536_DTM',[(1,'P0','bidirectional'),(8,'P1','bidirectional'),(2,'P2','bidirectional'),(4,'P3/INT','bidirectional')],
         [(5,'SCL','input'),(6,'SDA','bidirectional'),(7,'VCC','power_in'),(3,'GND','power_in')],
         'https://www.ti.com/lit/ds/symlink/tca9536.pdf',
         'DTM-specific physical pinout;7bit0x41; pullups defaultON;P0/P1 are observations')
    g.ic('LVC1G14_DCK',[(2,'A','input'),(1,'NC','no_connect')],
         [(4,'Y','output'),(5,'VCC','power_in'),(3,'GND','power_in')],
         'https://www.ti.com/lit/ds/symlink/sn74lvc1g14.pdf',
         '5V-tolerant Schmitt inverter with Ioff; output never connects to chargerCE')
    parts=[]
    def part(sheet,lib,ref,value,x,y,nets,footprint,mpn,source,note=''):
        sheet.part(lib,ref,value,x,y,{str(k):v for k,v in nets.items()},footprint,note,domain='MAIN_T')
        parts.append(dict(ref=ref,mpn=mpn,value=value,footprint=footprint,manufacturer_source=source,
                          candidate_added_position=True,pins={str(k):v for k,v in nets.items()}))
    def resistor(sh,ref,value,x,y,n1,n2,mpn,note=''):
        part(sh,'R',ref,value,x,y,{1:n1,2:n2},'Telemetry:R_0402_1005Metric',mpn,
             'https://www.vishay.com/docs/20035/dcrcwe3.pdf',note)
    def cap(sh,ref,value,x,y,net,mpn,note=''):
        part(sh,'C',ref,value,x,y,{1:net,2:'GND'},'Telemetry:C_0402_1005Metric',mpn,
             'https://product.tdk.com/',note)
    for label,ref,net,adc,r1,r2,ro,ci,co,cd,icref in [
        ('07-current-observer','ISET','CHG_ISET','CHARGE_CURRENT_ADC','R801','R802','R805','C807','C805','C802','U802'),
        ('08-TS-observer','TS','PACK_NTC','CHARGE_TS_ADC','R803','R804','R806','C808','C806','C803','U803')]:
        sh=g.Sheet(label,'Read-only '+ref+' charger observation / retained hardware protection')
        resistor(sh,r1,'10M1%100ppm',63.5,63.5,net,ref+'_TAP_MID','CRCW040210M0FKED','First of two independent series tap resistors; no direct ADC loading')
        resistor(sh,r2,'10M1%100ppm',190.5,63.5,ref+'_TAP_MID',ref+'_FILTER','CRCW040210M0FKED')
        cap(sh,ci,'1nF50V C0G5%',317.5,63.5,ref+'_FILTER','C1005C0G1H102J050BA')
        part(sh,'OPA391_DCK',icref,'OPA391DCKR',63.5,142.24,{1:ref+'_FILTER',3:ref+'_BUF',4:ref+'_BUF',5:'3V3',2:'GND'},
             'Telemetry:SOT-353_SC-70-5','OPA391DCKR','https://www.ti.com/lit/ds/symlink/opa391.pdf')
        resistor(sh,ro,'1k1%',190.5,142.24,ref+'_BUF',adc,'CRCW04021K00FKED')
        cap(sh,co,'100nF16V X7R10%',317.5,142.24,adc,'C1005X7R1C104K050BC')
        cap(sh,cd,'100nF16V X7R10%',63.5,223.52,'3V3','C1005X7R1C104K050BC')
        sh.note('Original RISET/NTC/independent guard unchanged. Two10M taps bound downstream loading/faults.\nInput RC>=175ms settling before valid; serialize ADS single-shot/MUX with original tip acquisition.\nAn openTS can saturate this3V3 buffer: report INVALID; never interpret rail saturation as a valid temperature.\nNew candidate positions require native packing, contamination/leakage and trip-margin qualification.',25.4,15.24,1.27)
        sh.save();trees[g.OUT/(label+'.kicad_sch')]=s.parse((g.OUT/(label+'.kicad_sch')).read_text())
    sh=g.Sheet('09-status-observer','CHG and actualCE observations / no firmware charger control')
    part(sh,'TCA9536_DTM','U801','TCA9536DTMR',63.5,76.2,
         {1:'CHG_SENSE_N',8:'CE_ALLOWED_SENSE',2:None,4:None,5:'I2C_SCL',6:'I2C_SDA',7:'3V3',3:'GND'},
         'Telemetry:TI_DTM0008A','TCA9536DTMR','https://www.ti.com/lit/ds/symlink/tca9536.pdf')
    part(sh,'LVC1G14_DCK','U804','SN74LVC1G14DCKR',190.5,76.2,
         {1:None,2:'CE_FILTER_INPUT',3:'GND',4:'CE_ALLOWED_RAW',5:'3V3'},
         'Telemetry:SOT-353_SC-70-5','SN74LVC1G14DCKR','https://www.ti.com/lit/ds/symlink/sn74lvc1g14.pdf')
    resistor(sh,'R807','22k1%',317.5,76.2,'CHARGE_CE_N','CE_FILTER_INPUT','CRCW040222K0FKED','Weak input-only CE tap; original10k5V pullup and guardQ1 retained')
    resistor(sh,'R808','4.7k1%',63.5,162.56,'CE_ALLOWED_RAW','CE_ALLOWED_SENSE','CRCW04024K70FKED','Output contention limited; HIGH means observedCE low/charge permitted, not actual charge current')
    resistor(sh,'R809','4.7k1%',190.5,162.56,'CHARGE_STATUS_N','CHG_SENSE_N','CRCW04024K70FKED')
    cap(sh,'C801','100nF16V X7R10%',317.5,162.56,'3V3','C1005X7R1C104K050BC')
    cap(sh,'C804','100nF16V X7R10%',63.5,233.68,'3V3','C1005X7R1C104K050BC')
    sh.note('Readback/initialize TCA: output0x01=0x00,config0x03=0x03,P0/P1 inputs,P2/P3 unused low outputs;\nspecial0x50=0x40 disables port pullups, keeps P3 out ofINTmode. Verify all before VALID.\nDefault all-input/pullupON state is current-bounded but not accepted data. PollCHG at25ms for~2Hzfault.\nCE observation is inverted through a5V-tolerant Schmitt/Ioff buffer; no new control can enable charger.',25.4,15.24,1.27)
    sh.save();trees[g.OUT/'09-status-observer.kicad_sch']=s.parse((g.OUT/'09-status-observer.kicad_sch').read_text())
    body=trees[OUT/'body/body-evt1.kicad_sch'];s.child(body,'paper')[1]=s.string('A2')
    for i,name in enumerate(('07-current-observer','08-TS-observer','09-status-observer')):
        append_sheet(body,name,name+'.kicad_sch',uid(name),25.4+(i%2)*190.5,266.7+(i//2)*63.5)
    # Full-device context uses actual retained sources; no artificial power flags.
    root=s.parse((src/'single-flange-system.kicad_sch').read_text())
    s.child(root,'uuid')[1]=s.atom(uid(PROJECT))
    for sh in s.children(root,'sheet'):
        name=s.prop(sh,'Sheetfile')
        replacement = 'body/body-evt1.kicad_sch' if '/body/'in name else 'flange/flange.kicad_sch' if name=='single-flange.kicad_sch' else Path(name).name
        next(p for p in s.children(sh,'property')if p[1].value=='Sheetfile')[2]=s.string(replacement)
    trees[OUT/(PROJECT+'.kicad_sch')]=root
    for p,t in trees.items():
        title=s.child(t,'title_block')
        if title:
            for item in s.children(title,'comment'):
                if item[1].value=='1':item[2]=s.string('TELEMETRY STUDY / ORIGINAL ARTWORK UNCHANGED / NO RELEASE')
    def annotate(path,project,instance):
        tree=trees[path]
        for sy in s.children(tree,'symbol'):
            old=s.child(sy,'instances')
            if old is None:old=s.parse('(instances)');sy.append(old)
            old.append(s.parse(f'(project {g.q(project)} (path {g.q(instance)} (reference {g.q(s.prop(sy,"Reference"))}) (unit {s.value(sy,"unit")or"1"})))'))
        for sheet in s.children(tree,'sheet'):
            annotate((path.parent/s.prop(sheet,'Sheetfile')).resolve(),project,instance+'/'+s.value(sheet,'uuid'))
    trees={p.resolve():v for p,v in trees.items()}
    annotate((OUT/(PROJECT+'.kicad_sch')).resolve(),PROJECT,'/'+uid(PROJECT))
    library={}
    for tree in trees.values():
        for sy in s.children(s.child(tree,'lib_symbols'),'symbol'):
            name=sy[1].value.split(':',1)[-1];node=copy.deepcopy(sy);node[1]=s.string(name)
            if name in library:assert s.dump(library[name])==s.dump(node),('conflicting symbols',name)
            else:library[name]=node
    lib=s.parse('(kicad_symbol_lib (version 20220914) (generator telemetry_candidate))');lib.extend(library[k]for k in sorted(library));s.write(OUT/'PrototypeR0.kicad_sym',lib)
    s.write(OUT/'sym-lib-table',s.parse('(sym_lib_table (version 7) (lib (name "PrototypeR0") (type "KiCad") (uri "${KIPRJMOD}/PrototypeR0.kicad_sym") (options "") (descr "Cached actual retained symbols plus selected instrumentation")))'))
    # Explicit library paths keep source geometry read-only and make missing
    # selected footprint authoring visible; no wrong standard-part substitution.
    libs={'PrototypeR0':E/'body/PrototypeR0.pretty','PackPigtailR35':E/'body/PackPigtailR35.pretty',
          'EVT1':E/'EVT1.pretty','Selected':src/'Selected.pretty','Telemetry':OUT/'Telemetry.pretty'}
    fptable=s.parse('(fp_lib_table(version 7))')
    for name,path in libs.items():
        uri='${KIPRJMOD}/'+os.path.relpath(path,OUT)
        fptable.append(s.parse(f'(lib(name {g.q(name)})(type "KiCad")(uri {g.q(uri)})(options "")(descr "Source-bound selected geometry"))'))
    s.write(OUT/'fp-lib-table',fptable)
    for p,t in trees.items():s.write(p,t)
    settings=json.loads((src/'single-flange-system.kicad_pro').read_text())
    settings['erc']['erc_exclusions']=[]
    (OUT/(PROJECT+'.kicad_pro')).write_text(json.dumps(settings,indent=2)+'\n')
    assert len(parts)==21
    report={'status':'Native circuit candidate; original69 footprint poses/artwork preserved; placement/routing pending',
            'builder_sha256':sha(Path(__file__)), 'source_inputs_sha256':inputs,
            'retained_body_positions':69,'new_positions':21,'candidate_body_positions':90,
            'intended_existing_terminal_delta':{'U7.6':{'from':'GND','to':'CHARGE_CURRENT_ADC'},'U7.7':{'from':'GND','to':'CHARGE_TS_ADC'}},
            'new_tap_branches':['CHG_ISET','PACK_NTC','CHARGE_CE_N','CHARGE_STATUS_N','3V3','GND','I2C_SCL','I2C_SDA'],
            'original_body_artwork_sha256':sha(E/'body/body-evt1.kicad_pcb'),
            'frozen_flange_artwork_sha256':sha(src/'single-flange.kicad_pcb'),
            'new_parts':parts,'new_power_flags':False,'original_source_promotion':False,
            'outputs_sha256':{str(p.relative_to(OUT.resolve())):sha(p)for p in trees}}
    (OUT/'source-bindings.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Native body69+21instrumentation; two authorized ADC input changes; retained full-device context')


if __name__=='__main__':main()
