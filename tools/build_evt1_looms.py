"""EVT WireViz sources and engineering wire-stock worksheet, not product BOM.

Generate diagrams/child BOMs outside the repository using WireViz0.4.1.
Only verified wire forms receive a nominal installed free-span dimension.
"""
from pathlib import Path
import csv
import hashlib
import json
import textwrap
import xml.etree.ElementTree as ET
import yaml
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hardware/cables/evt1';PCB=ROOT/'hardware/pcb/evt1'
CAD=ROOT/'hardware/cad/manufacturing-layout/evt1-integration/loom'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
WIRE={'28':('100690',28,.6,4),'32':('113094',32,.55,2)}

def main():
    OUT.mkdir(exist_ok=True)
    pinmaps={};source_hashes={}
    for domain in ('system','body','flange','sensor','dock','pins'):
        path=PCB/'system-native.xml' if domain=='system' else PCB/domain/(domain+'-native.xml');source_hashes[str(path.relative_to(ROOT))]=sha(path);root=ET.parse(path).getroot();m={}
        for n in root.findall('nets/net'):
            for v in n.findall('node'):m[(v.get('ref'),v.get('pin'))]=n.get('name')
        pinmaps[domain]=m
    loom=json.loads((CAD/'review.json').read_text()) if (CAD/'review.json').exists() else {}
    spans_verified=(loom.get('geometry_checks',{}).get('pass',False)
        and sha(CAD/'EVT1Loom.FCStd')==loom['native_sha256']
        and sha(ROOT/'tools/build_evt1_loom_cad.py')==loom['builder_sha256']
        and sha(ROOT/'tools/evt1_loom_paths.py')==loom['path_builder_sha256']
        and sha(CAD.parent/'EVT1Product.FCStd')==loom['source_product_native_sha256']
        and all(sha(PCB/domain/'mcad.json')==digest for domain,digest in loom['source_mcad_sha256'].items())
        and sha(ROOT/'tools/verify_evt1_loom_cad.py')==loom['geometry_checks']['verifier_sha256'])
    lengths={v['name']:v['insulated_path_length_mm'] for v in loom['wires']} if spans_verified else {}
    documents={};contracts=[];stock=[]
    def doc(name,title):
        d={'metadata':{'title':title,'notes':'EVT first article. Native numeric pin map; verify mating marks/continuity. Free-span dimensions are between modeled wire-exit datums; stock blanks are longer and are not finished cut lengths. No physical crimp/current/fit acceptance.'},
           'options':{'fontname':'Arial','color_mode':'FULL'},'connectors':{},'cables':{},'connections':[],'additional_bom_items':[]}
        documents[name]=d;return d
    def connector(d,name,pins,labels,type,mpn=None,ignore=True):
        item={'type':type,'pins':pins,'pinlabels':labels,'ignore_in_bom':ignore}
        if mpn:item.update({'manufacturer':'JST','mpn':mpn})
        d['connectors'][name]=item
    def wire(d,harness,name,a,ap,b,bp,net,gauge='28',blank=120,span=None,included=False):
        mpn,awg,od,radius=WIRE[gauge]
        d['cables'][name]={'category':'bundle','type':'Included OEM lead' if included else 'Individual stranded Kapton wire / trim on first article',
            'wirecount':1,'colors':['BN'],'wirelabels':[net],'gauge':awg,'gauge_unit':'AWG','length':blank/1000,'length_unit':'m',
            'ignore_in_bom':included,'notes':('Included with factory assembly; not a separate wire purchase.' if included else
                f'{blank}mm starting stock. Model OD limit{od}mm.\nCentreline bend at least{radius}mm.\n'+(f'Nominal free insulated path{span:.3f}mm,\nbefore terminal take-up.\n' if span is not None else 'Installed route/free length not yet fixed.\n')+
                'Do not pre-tin strands before ordinary crimping.\nSupplier sets strip/crimp from controlled tooling data.')}
        if not included:d['cables'][name].update({'manufacturer':'Accu-Glass','mpn':mpn})
        d['connections'].append([{a:[ap]},{name:[1]},{b:[bp]}])
        stock.append({'harness':harness,'wire':name,'net':net,'from':a+'.'+str(ap),'to':b+'.'+str(bp),'manufacturer':'OEM' if included else 'Accu-Glass','MPN':'included' if included else mpn,
            'AWG':awg,'stock_blank_mm':blank,'nominal_free_span_mm':'–' if span is None else round(span,3),'stock_included':included})
    def native(domain,ref,pin):return pinmaps[domain][(ref,str(pin))]
    def contract(harness,a,ap,b,bp):
        an=native(a[0],a[1],ap);bn=native(b[0],b[1],bp);assert an==bn,(harness,an,bn)
        contracts.append({'harness':harness,'from':[a[0],a[1],str(ap)],'to':[b[0],b[1],str(bp)],'net':an});return an
    for ntc,pad in (('TH1','3'),('TH2','4')):
        contract('W-PACK-EVT1',('body','J2'),pad,('system',ntc),'1')
        contract('W-PACK-EVT1',('body','J2'),'2',('system',ntc),'2')
    for pin in ('1','2'):contract('W-TIP-EVT1',('body','J5'),pin,('system','TH101'),pin)
    d=doc('interboard-evt1','EVT1 body J6 to flange J7 / ten independent conductors')
    labels=[native('body','J6',i) for i in range(1,11)]
    for name in ('J6','J7'):connector(d,name,list(range(1,11)),labels,'JST SH10 without protrusions','SHR-10V-S',False)
    d['connectors']['J7']['notes']='Supply finished crimp terminals in numbered order with this housing loose. Insert only after the cap/body module is threaded; do not feed the11mm housing alongside the other neck conductors.'
    for i in range(1,11):
        # A nominal installed path does not qualify terminal take-up, forming
        # or rework allowance. Keep the original first-article stock blank.
        net=contract('W-INTERBOARD-EVT1',('body','J6'),i,('flange','J7'),i);span=lengths.get('IB'+str(i).zfill(2));blank=120
        wire(d,'W-INTERBOARD-EVT1','IB'+str(i).zfill(2),'J6',i,'J7',i,net,blank=blank,span=span)
    d['additional_bom_items'].append({'description':'SH socket crimp terminal','qty':20,'unit':'pcs','manufacturer':'JST','mpn':'SSH-003T-P0.2-H'})

    d=doc('compass-evt1','EVT1 fixed compass / body J81 to sensor J82')
    labels=[native('body','J81',i) for i in range(1,5)]
    connector(d,'J81',[1,2,3,4],labels,'Body hand-solder lands');connector(d,'J82',[1,2,3,4],labels,'Sensor hand-solder lands')
    for i in range(1,5):wire(d,'W-COMPASS-EVT1','CS'+str(i),'J81',i,'J82',i,contract('W-COMPASS-EVT1',('body','J81'),i,('sensor','J82'),i),'32',150)

    d=doc('pack-evt1','EVT1 protected pack / disconnect and two independent NTC pairs')
    connector(d,'J2',[1,'2P','2S',3,4],['PACK_P','GND power','GND sensors','PACK_NTC','PACK_GUARD'],'Body four-net five-land solder interface')
    d['connectors']['J2']['notes']='2P/2S are separate physical lands on native logical pin2. Both32AWG sensor returns join at2S; power return lands only at2P. No pack-side shared return.'
    connector(d,'BODY_PWR',[1,2],['PACK_P','GND'],'JST ACH body plug','ACHTP-02V-S',False)
    connector(d,'PACK_PWR',[1,2],['PACK_P','GND'],'Factory pack socket; included in custom protected-pack request','ACHTR-02V-S',True)
    connector(d,'PACK',[1,2],['Protected P+','Protected P-'],'Factory-protected1S pack; no bare cell tabs')
    for i,pin in enumerate(('1','2P'),1):
        wire(d,'W-PACK-EVT1','PB'+str(i),'J2',pin,'BODY_PWR',i,'PACK_P' if i==1 else 'GND','28',150)
        wire(d,'W-PACK-EVT1','PM'+str(i),'BODY_PWR',i,'PACK_PWR',i,'mated contact',blank=0,included=True)
        wire(d,'W-PACK-EVT1','PF'+str(i),'PACK_PWR',i,'PACK',i,'Protected P+' if i==1 else 'Protected P-','28',8.283185307,8.283185307,True)
    for n,signal in ((1,'3'),(2,'4')):
        name='TH'+str(n);connector(d,name,[1,2],['10k NTC signal','Independent return'],'Factory-leaded external NTC')
        d['connectors'][name].update({'manufacturer':'Vishay','mpn':'NTCLE413E2103F524A','ignore_in_bom':False,'notes':'Factory52+/-5mm leads are included. Trim/extend with insulated solder laps; do not ordinary-crimp the overall-tinned E2 leads. Keep head dry; no direct casting/potting.'})
        for j,pin in ((1,signal),(2,'2S')):wire(d,'W-PACK-EVT1',name+'EXT'+str(j),'J2',pin,name,j,'PACK_NTC' if n==1 and j==1 else 'PACK_GUARD' if j==1 else name+' separate GND','32',150)
    d['additional_bom_items'].append({'description':'ACH body plug crimp contact','qty':2,'unit':'pcs','manufacturer':'JST','mpn':'SACHP-003G-P0.2'})
    d['metadata']['notes']+=' Pack socket, two SACH contacts and short factory power leads belong to BC-PACK-EVT1-001; do not buy/count them again as loose cable parts. Four NTC extension joints remain separately insulated.'

    for name,title,ref,device,mpn,gauge in (
        ('motor-evt1','EVT1 local motor / both bridge outputs','J3','MOTOR','NFP-E1015 3.7V','28'),
        ('tip-evt1','EVT1 local two-wire tip thermistor','J5','TIP_NTC','B57540G1103F000','32')):
        d=doc(name,title);labels=[native('body',ref,i) for i in (1,2)]
        connector(d,ref,[1,2],labels,'JST SH2 socket','SHR-02V-S',False)
        connector(d,device,[1,2],labels,'OEM leaded component')
        d['connectors'][device].update({'manufacturer':'NFP' if ref=='J3' else 'TDK','mpn':mpn,'ignore_in_bom':False})
        for i in (1,2):wire(d,'W-MOTOR-EVT1' if ref=='J3' else 'W-TIP-EVT1',('M' if ref=='J3' else 'T')+str(i),ref,i,device,i,labels[i-1],gauge,80)
        d['additional_bom_items'].append({'description':'SH socket crimp contact; crimp ordinary pigtail then solder to OEM lead','qty':2,'unit':'pcs','manufacturer':'JST','mpn':'SSH-003T-P0.2-H'})
        d['metadata']['notes']+=' OEM leads are supplied with the component, not separate wire stock. Solder/insulate the pigtail transition, inspect and strain-relieve. MOTOR_N is not system ground.'

    d=doc('contacts-evt1','EVT1 four fixed feedthrough targets to flange J1')
    labels=[native('flange','J1',i) for i in range(1,5)]
    connector(d,'TARGET',[1,2,3,4],labels,'Fixed contact tails; X-38/-32/-26/-20')
    connector(d,'J1',[1,2,3,4],labels,'Flange B.Cu hand-solder lands')
    for i in range(1,5):wire(d,'W-CONTACTS-EVT1','CT'+str(i),'TARGET',i,'J1',i,labels[i-1],'28',80)
    d['metadata']['notes']+=' D-/D+ are an adjacent short pair. Route together with controlled lay and minimal end fanout; no90ohm or USB signal-integrity qualification follows from this logical drawing. Solder/clean/cool posts before fitting their inner rings.'

    d=doc('dock-evt1','EVT1 cradle USB board J93 to spring-pin board J94')
    labels=[native('dock','J93',i) for i in range(1,5)]
    connector(d,'J93',[1,2,3,4],labels,'USB board hand-solder lands, F.Cu');connector(d,'J94',[1,2,3,4],labels,'Pin board rear hand-solder lands, B.Cu')
    for i in range(1,5):wire(d,'W-DOCK-EVT1','DK'+str(i),'J93',i,'J94',i,contract('W-DOCK-EVT1',('dock','J93'),i,('pins','J94'),i),'28',150)
    d['metadata']['notes']+=' Keep D-/D+ paired. Route rear J94 joints through the open retainer window/downward channel. Pin-board thickness remains1mm; verify USB/power/strain relief in the real cradle.'

    files=[]
    for name,d in documents.items():
        for c in d['connectors'].values():
            for key,width in (('type',44),('notes',65)):
                if key in c:c[key]='\n'.join(textwrap.fill(line,width=width,break_long_words=False,break_on_hyphens=False) for line in c[key].splitlines())
        file=OUT/(name+'.yml');file.write_text(yaml.safe_dump(d,sort_keys=False,allow_unicode=True));files.append(file)
    with (OUT/'wire-stock.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(stock[0]));w.writeheader();w.writerows(stock)
    report={'scope':'Seven native-pin-map WireViz sources; starting stock only unless interboard_spans_verified is true. Unfinished routes and physical qualification do not become released lengths.',
        'native_netlist_sha256':source_hashes,'interboard_spans_verified':spans_verified,
        'loom_native_sha256':loom['native_sha256'] if spans_verified else None,'loom_review_sha256':sha(CAD/'review.json') if spans_verified else None,
        'builder_sha256':sha(Path(__file__)),'pin_contracts':contracts,'files':{v.name:sha(v) for v in files},
        'wire_stock_sha256':sha(OUT/'wire-stock.csv'),'physical_validation':False,'full_product_order_ready':False}
    (OUT/'logical-source.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'harness_sources':len(files),'native_connector_contracts':len(contracts),'wire_stock_rows':len(stock)}))

if __name__=='__main__':main()
