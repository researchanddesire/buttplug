"""Independently check saved EVT WireViz graphs, native pins and child BOMs."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import xml.etree.ElementTree as ET
import yaml

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'hardware/cables/evt1';PCB=ROOT/'hardware/pcb/evt1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--exports',type=Path,required=True);args=ap.parse_args()
    source=json.loads((SOURCE/'logical-source.json').read_text())
    for file,digest in source['native_netlist_sha256'].items():assert sha(ROOT/file)==digest,file
    assert sha(ROOT/'tools/build_evt1_looms.py')==source['builder_sha256']
    assert sha(SOURCE/'wire-stock.csv')==source['wire_stock_sha256']
    pinmaps={}
    for domain in ('body','flange','sensor','dock','pins'):
        root=ET.parse(PCB/domain/(domain+'-native.xml')).getroot();mapping={}
        for net in root.findall('nets/net'):
            for node in net.findall('node'):mapping[(node.get('ref'),node.get('pin'))]=net.get('name')
        pinmaps[domain]=mapping
    def net(domain,ref,pin):return pinmaps[domain][(ref,str(pin))]
    inter=['GND','VBUS_CHG','3V3','PACK_P','MOTOR_ARM','MOTOR_PWM','DOCK_PRESENT_N','I2C_SDA','I2C_SCL','TIP_EXC_EN']
    assert [net('body','J6',p) for p in range(1,11)]==inter
    assert [net('flange','J7',p) for p in range(1,11)]==inter
    assert [net('body','J2',p) for p in range(1,5)]==['PACK_P','GND','PACK_NTC','PACK_GUARD']
    assert [net('body','J3',p) for p in (1,2)]==['MOTOR_P','MOTOR_N']
    assert [net('body','J5',p) for p in (1,2)]==['TIP_NTC','GND']
    assert [net('flange','J1',p) for p in range(1,5)]==['GND','USB_DM_CONTACT','USB_DP_CONTACT','DOCK_5V']
    expected={
        'interboard-evt1':{f'IB{p:02}':('J6',str(p),'J7',str(p)) for p in range(1,11)},
        'compass-evt1':{f'CS{p}':('J81',str(p),'J82',str(p)) for p in range(1,5)},
        'motor-evt1':{f'M{p}':('J3',str(p),'MOTOR',str(p)) for p in (1,2)},
        'tip-evt1':{f'T{p}':('J5',str(p),'TIP_NTC',str(p)) for p in (1,2)},
        'contacts-evt1':{f'CT{p}':('TARGET',str(p),'J1',str(p)) for p in range(1,5)},
        'dock-evt1':{f'DK{p}':('J93',str(p),'J94',str(p)) for p in range(1,5)},
        'pack-evt1':{
            'PB1':('J2','1','BODY_PWR','1'),'PB2':('J2','2P','BODY_PWR','2'),
            'PM1':('BODY_PWR','1','PACK_PWR','1'),'PM2':('BODY_PWR','2','PACK_PWR','2'),
            'PF1':('PACK_PWR','1','PACK','1'),'PF2':('PACK_PWR','2','PACK','2'),
            'TH1EXT1':('J2','3','TH1','1'),'TH1EXT2':('J2','2S','TH1','2'),
            'TH2EXT1':('J2','4','TH2','1'),'TH2EXT2':('J2','2S','TH2','2')},
    }
    labels={
        'interboard-evt1':{k:('body','J6') for k in ('J6','J7')},
        'compass-evt1':{'J81':('body','J81'),'J82':('sensor','J82')},
        'motor-evt1':{k:('body','J3') for k in ('J3','MOTOR')},
        'tip-evt1':{k:('body','J5') for k in ('J5','TIP_NTC')},
        'contacts-evt1':{k:('flange','J1') for k in ('TARGET','J1')},
        'dock-evt1':{'J93':('dock','J93'),'J94':('pins','J94')},
    }
    with (SOURCE/'wire-stock.csv').open(newline='') as f:stock=list(csv.DictReader(f))
    assert len(stock)==36 and len({v['wire'] for v in stock})==36
    stock_by_name={v['wire']:v for v in stock}
    cad=ROOT/'hardware/cad/manufacturing-layout/evt1-integration/loom'
    length_by_name={}
    if source['interboard_spans_verified']:
        report=json.loads((cad/'review.json').read_text())
        assert report['geometry_checks']['pass'] and sha(cad/'EVT1Loom.FCStd')==source['loom_native_sha256']==report['native_sha256']
        assert sha(cad/'review.json')==source['loom_review_sha256']
        assert sha(cad.parent/'EVT1Product.FCStd')==report['source_product_native_sha256']
        assert sha(ROOT/'tools/build_evt1_loom_cad.py')==report['builder_sha256']
        assert sha(ROOT/'tools/evt1_loom_paths.py')==report['path_builder_sha256']
        assert sha(ROOT/'tools/verify_evt1_loom_cad.py')==report['geometry_checks']['verifier_sha256']
        for domain,digest in report['source_mcad_sha256'].items():assert sha(PCB/domain/'mcad.json')==digest
        length_by_name={n:v['free_insulated_path_mm'] for n,v in report['geometry_checks']['checks'].items()}
    else:assert source['loom_native_sha256'] is None and source['loom_review_sha256'] is None
    checks={};output_hashes={}
    for name,graph in expected.items():
        file=SOURCE/(name+'.yml');assert sha(file)==source['files'][file.name]
        doc=yaml.safe_load(file.read_text());actual={}
        for row in doc['connections']:
            assert len(row)==3
            cells=[]
            for cell in row:
                assert len(cell)==1
                ref,pins=next(iter(cell.items()));assert len(pins)==1;cells.append((ref,str(pins[0])))
            (a,ap),(wire,wp),(b,bp)=cells
            assert wp=='1' and wire not in actual
            actual[wire]=(a,ap,b,bp)
        assert actual==graph,(name,'Wrong, missing or duplicate graph endpoints',actual)
        assert set(doc['cables'])==set(graph)
        for ref,(domain,native_ref) in labels.get(name,{}).items():
            c=doc['connectors'][ref]
            assert c['pinlabels']==[net(domain,native_ref,p) for p in c['pins']],(name,ref,'Pin labels differ from native')
        expected_bom={}
        for wire,c in doc['cables'].items():
            s=stock_by_name[wire]
            assert float(c['length'])==float(s['stock_blank_mm'])/1000
            assert bool(c.get('ignore_in_bom',False))==(s['stock_included']=='True')
            assert str(c['gauge'])==s['AWG']
            if not c.get('ignore_in_bom',False):
                assert c['mpn']==s['MPN']
                expected_bom[c['mpn']]=expected_bom.get(c['mpn'],0)+float(c['length'])
            if name=='interboard-evt1':
                if wire in length_by_name:
                    span=length_by_name[wire];assert abs(float(s['nominal_free_span_mm'])-span)<.00051
                    assert float(s['stock_blank_mm'])>=span+10
                else:assert s['nominal_free_span_mm']=='–' and float(s['stock_blank_mm'])==120
                assert c['gauge']==28 and c['mpn']=='100690'
        for c in doc['connectors'].values():
            if not c.get('ignore_in_bom',False):expected_bom[c['mpn']]=expected_bom.get(c['mpn'],0)+1
        for c in doc['additional_bom_items']:expected_bom[c['mpn']]=expected_bom.get(c['mpn'],0)+c['qty']
        bom_path=args.exports/(name+'.bom.tsv')
        with bom_path.open(newline='') as f:rows=list(csv.DictReader(f,delimiter='\t'))
        actual_bom={}
        for row in rows:
            mpn=row['MPN'];assert mpn and mpn not in actual_bom,(name,'Unspecified or duplicate MPN')
            actual_bom[mpn]=float(row['Qty'])
        assert set(actual_bom)==set(expected_bom),(name,'Child BOM MPN inventory',actual_bom,expected_bom)
        for mpn,qty in expected_bom.items():assert math.isclose(actual_bom[mpn],qty,abs_tol=.00051),(name,mpn,qty,actual_bom[mpn])
        for suffix in ('.svg','.png','.bom.tsv'):
            p=args.exports/(name+suffix);assert p.is_file() and p.stat().st_size>100;output_hashes[p.name]=sha(p)
        checks[name]={'conductors':len(graph),'purchased_MPNs':len(expected_bom),'child_BOM_matches_source':True}
    result={'pass':True,'scope':'Saved logical graph/native labels and generated child BOMs. Installed interboard spans are checked only when interboard_spans_verified is true; all other routes and all physical/process qualification remain open',
        'harnesses':checks,'conductors':sum(v['conductors'] for v in checks.values()),'interboard_spans_verified':source['interboard_spans_verified'],'logical_source_sha256':sha(SOURCE/'logical-source.json'),
        'source_review_sha256':sha(SOURCE/'source-review.json'),'verifier_sha256':sha(Path(__file__)),
        'export_directory':str(args.exports),'generated_files_sha256':output_hashes,'physical_validation':False,'full_product_order_ready':False}
    (SOURCE/'logical-review.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'pass':True,'harnesses':len(checks),'conductors':result['conductors']}))

if __name__=='__main__':main()
