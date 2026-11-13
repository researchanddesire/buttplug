"""Candidate-only host/Cortex-M0+ proof with frozen protocol/source bindings."""
from pathlib import Path
import argparse,datetime,hashlib,json,re,subprocess
H=Path(__file__).resolve().parent;R=H.parents[1];PIN='4678caf5112116f93fc80a013288c87fad0e0572ccb57d29b35e8bd2dbe971a5'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def run(cmd):
    p=subprocess.run(cmd,cwd=H,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if p.returncode:raise RuntimeError(' '.join(cmd)+'\n'+p.stdout)
    return p.stdout
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--cross',default='/private/tmp/dock-arm-toolchain/arm-gnu-toolchain-13.3.rel1-darwin-arm64-arm-none-eabi/bin/arm-none-eabi-');a=ap.parse_args()
    protocol=R/'hardware/pcb/evt1/case-telemetry-study/protocol-v1.json';assert sha(protocol)==PIN
    peer=json.loads((H/'peer-review.json').read_text())
    assert peer['core_sha256']==sha(H/'case_link.c') and peer['header_sha256']==sha(H/'case_link.h') and peer['frozen_protocol_sha256']==PIN
    assert peer['repro_source_sha256']==sha(H/'peer-regression.c')
    own_before={p.name:sha(p)for p in H.iterdir()if p.is_file()and p.name!='validation.json'}
    baseline=list((H.parent/'src').glob('*.c'))+list((H.parent/'include').glob('*.h'))+[H.parent/'Makefile',H.parent/'stm32l071cb.ld']
    producer=[R/'firmware/main'/n for n in ['case_telemetry.c','case_telemetry.h','thermal_history.c','thermal_history.h']]
    before={str(p.relative_to(R)):sha(p)for p in baseline+producer}
    output=run(['make','test','roundtrip','peer-review','compile-only','CROSS='+a.cross]);(H/'build/validation.log').write_text(output)
    assert '20 behavior scenarios passed' in output
    assert 'Actual C3 sender/STM32 candidate roundtrip passed' in output
    assert peer['resolved_repro_stdout'] in output
    gatt=run(['make','-f','nina-gatt.mk','nina-gatt-test','nina-gatt-compile','CROSS='+a.cross])
    assert 'discovery, five subscriptions, reads, actual C3 sender roundtrip and fail-closed traces passed' in gatt
    (H/'build/nina-gatt-validation.log').write_text(gatt)
    state_size=int(re.search(r'sizeof\(case_link\)=(\d+) bytes',output)[1])
    version=run([a.cross+'gcc','--version']).splitlines()[0];assert '13.3.1' in version
    size=run([a.cross+'size','build/compile-only.elf']).splitlines()[-1].split();text,data,bss=map(int,size[:3])
    assert text+data<131072 and data+bss+2048<=20480
    undefined=run([a.cross+'nm','-u','build/compile-only.elf']);assert not undefined.strip()
    assert before=={str(p.relative_to(R)):sha(p)for p in baseline+producer}
    assert own_before=={p.name:sha(p)for p in H.iterdir()if p.is_file()and p.name!='validation.json'}
    vectors=json.loads((H/'golden-vectors.json').read_text());assert vectors['protocol_sha256']==PIN and len(vectors['vectors'])==6
    for v in vectors['vectors']:assert len(bytes.fromhex(v['wire_hex']))==20
    files=[p for p in H.iterdir()if p.is_file()and p.name!='validation.json']
    result={'status':'pass: isolated decoder/cache candidate; not integrated/flashed or hardware enabled','checked_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protocol':str(protocol.relative_to(R)),'protocol_sha256':PIN,'host_behavior_groups':20,'bounded_malformed_decoder_cases':5000,'independent_Python_struct_golden_frames':6,'actual_C3_sender_host_roundtrip_pass':True,'host_sanitizer':'undefined behavior','state_size_bytes_host':state_size,'compiler':version,'compiler_binary_sha256':sha(Path(a.cross+'gcc')),'target':'Cortex-M0+ freestanding compile/link proof only; no vectors/startup/peripheral IO, no BIN/HEX','target_text_bytes':text,'target_data_bytes':data,'target_bss_bytes':bss,'target_reserved_stack_bytes':2048,'target_undefined_symbols':[],'existing_dock_runtime_and_read_only_sender_sources_unchanged':before,'source_sha256':{p.name:sha(p)for p in files},'artifacts_sha256':{n:sha(H/'build'/n)for n in ['case_link.o','compile-only.elf','compile-only.map','test-case-link','test-sender-roundtrip','validation.log']},'nonce_generation_clock_bounds_and_transport_qualified':False,'integrated_with_existing_safety_runtime':False,'hardware_sender_interoperability_qualified':False}
    result['nina_gatt']={'host_uart_roundtrip':True,'receiver_Cortex_M0_plus_object':True,
                        'post_authentication_only':True,'in_scheduled_runtime':False,
                        'artifact_sha256':{n:sha(H/'build'/n) for n in ('nina_gatt.o','test-nina-gatt','nina-gatt-validation.log')}}
    (H/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k]for k in ['status','host_behavior_groups','state_size_bytes_host','target_text_bytes','target_bss_bytes','protocol_sha256']},indent=2))
if __name__=='__main__':main()
