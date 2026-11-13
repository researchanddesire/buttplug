#!/usr/bin/env python3
"""Build actual target and host behavior tests; bind reports to exact sources."""
import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path
from check_contract import ROOT,check
from check_native_interfaces import audit

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args):
    result=subprocess.run(args,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print(result.stdout,end='')
    result.check_returncode()
    return result.stdout

def main():
    p=argparse.ArgumentParser();p.add_argument('--cross',default='arm-none-eabi-');a=p.parse_args()
    contract=check()
    interfaces=audit()
    host=run(['make','test'])
    build=run(['make','-j4','CROSS='+a.cross])
    version=run([a.cross+'gcc','--version']).splitlines()[0]
    size=run([a.cross+'size','build/dock-evt1.elf']).splitlines()[-1].split()
    binary=(ROOT/'build/dock-evt1.bin').read_bytes()
    elf=(ROOT/'build/dock-evt1.elf').read_bytes()
    assert elf[:6]==b'\x7fELF\x01\x01' and struct.unpack_from('<H',elf,18)[0]==40
    sp,reset=struct.unpack_from('<II',binary)
    assert sp==0x20005000 and reset&1 and 0x08000000<reset<0x08000000+len(binary)
    systick=struct.unpack_from('<I',binary,15*4)[0]
    assert systick&1 and 0x08000000<systick<0x08000000+len(binary)
    inventory={}
    for path in sorted(ROOT.rglob('*')):
        if not path.is_file() or path.name=='validation.json':continue
        rel=path.relative_to(ROOT)
        if any(x in rel.parts for x in ('build','.build','__pycache__')):continue
        inventory[str(rel)]=sha(path)
    report={'status':'Cross-compiled candidate with host behavior verification; no flashed/powered result',
      'pass':True,'hardware_validation':False,'optical_cleaning_validation':False,
      'toolchain':{'version':version,
        'download':'https://developer.arm.com/-/media/Files/downloads/gnu/13.3.rel1/binrel/arm-gnu-toolchain-13.3.rel1-darwin-arm64-arm-none-eabi.tar.xz',
        'inspected_archive_sha256':'fb6921db95d345dc7e5e487dd43b745e3a5b4d5c0c7ca4f707347148760317b4'},
      'contract':contract,'hardware_pin_contract_sha256':sha(ROOT.parent/contract['hardware_source']),
      'independent_native_interface_terminal_checks':interfaces['terminal_checks'],
      'host_behavior_scenarios':int(re.search(r'PASS: (\d+) behavior',host).group(1)),
      'host_sanitizers':'undefined behavior; address sanitizer runtime failed to initialize on this macOS host',
      'target':{'cpu':'Cortex-M0+','flash_origin':0x08000000,'flash_limit_bytes':131072,
         'RAM_limit_bytes':20480,'text_bytes':int(size[0]),'data_bytes':int(size[1]),'bss_bytes':int(size[2]),
         'initial_SP':hex(sp),'reset_vector':hex(reset),'systick_vector':hex(systick)},
      'artifacts':{n:sha(ROOT/'build'/n) for n in ['dock-evt1.elf','dock-evt1.bin','dock-evt1.hex']},
      'source_sha256':inventory,
      'limits':['Host traces do not simulate physical supervisor/lid/watchdog waveforms.',
                'GPIO/I2C/ADC/LCD initialization compiles against official CMSIS; board bring-up and timing remain pending.',
                'Temperature/electrical limits are conservative EVT candidates, not qualified optical or thermal acceptance.',
                'USB default/suspend/inrush and source budget require hardware qualification.']}
    (ROOT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('pass','host_behavior_scenarios','target')},indent=2))
if __name__=='__main__':main()
