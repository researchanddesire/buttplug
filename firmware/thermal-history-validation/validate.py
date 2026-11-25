#!/usr/bin/env python3
"""Run and bind the thermal-history/USB checks. Never flash or qualify hardware."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, os, re, subprocess, sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BUILD=Path('/private/tmp/compass-thermal-build')
TOOLS=Path('/Users/lucianchapar/.platformio/packages/toolchain-riscv32-esp/bin')
SDK=Path('/Users/lucianchapar/.platformio/packages/framework-espidf')
AUDIT=ROOT/'hardware/pcb/evt1/offdock-usb-audit/implementation/validation.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def entry(p):
    return {'path':str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p),'SHA256':sha(p),'bytes':p.stat().st_size}

def main():
    paths=[p for folder in ('main','tests') for p in (ROOT/'firmware'/folder).rglob('*') if p.is_file()]
    paths += [ROOT/'firmware'/name for name in ('CMakeLists.txt','platformio.ini','sdkconfig.defaults','sdkconfig.evt1','sdkconfig.prototype-r0','partitions.csv','version.txt')]
    paths.append(Path(__file__))
    before={str(p.relative_to(ROOT)):sha(p) for p in paths}
    (HERE/'source-snapshot.json').write_text(json.dumps(before,indent=2)+'\n')
    logs=[]
    for command,name in ((['sh','firmware/tests/run_host_tests.sh'],'host.log'),(['sh','firmware/tests/run_evt_console_tests.sh'],'console.log'),(['pio','run','-d','firmware','-e','evt1','-e','prototype-r0'],'build.log')):
        env=dict(os.environ,PLATFORMIO_BUILD_DIR=str(BUILD))
        with (HERE/name).open('w') as out:
            result=subprocess.run(command,cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT)
        if result.returncode:
            print((HERE/name).read_text()[-5000:]);raise SystemExit(result.returncode)
        logs.append(entry(HERE/name))
    assert before=={str(p.relative_to(ROOT)):sha(p) for p in paths},'Source changed during validation'
    log=(HERE/'build.log').read_text()
    assert re.search(r'evt1\s+SUCCESS',log) and re.search(r'prototype-r0\s+SUCCESS',log)
    assert not re.search(r'\b(?:warning|error):',log,re.I)
    main_source=(ROOT/'firmware/main/main.c').read_text()
    assert main_source.index('ESP_ERROR_CHECK(r0_radio_init())') < main_source.index('wear_boot_id = esp_random()')
    config=(ROOT/'firmware/sdkconfig.evt1').read_text()
    assert '# CONFIG_BT_CTRL_MODEM_SLEEP is not set' in config
    assert '# CONFIG_PM_ENABLE is not set' in config
    host=(HERE/'host.log').read_text()
    assert 'Thermal history:' in host and 'ring' in host and '1680 known tilted' in host
    assert 'console/PHY boundary:' in (HERE/'console.log').read_text()
    previous=json.loads(AUDIT.read_text())
    assert (SDK/'version.txt').read_text().strip()=='5.5.3'
    for row in previous['SDK']['primary_byte_comparisons']:
        assert sha(SDK/row['IDF_relative_path'])==row['official_SHA256']
    def tool(name,*args):
        return subprocess.check_output([str(TOOLS/name),*map(str,args)],text=True)
    elf=BUILD/'evt1/firmware.elf'
    symbols=tool('riscv32-esp-elf-objdump','-t',elf)
    required=('pad_off_locked','dock_detached','vPortEnterCritical','vPortExitCritical','gpio_intr_service','gpio_isr_loop','xPortSetInterruptMaskFromISR','vPortClearInterruptMaskFromISR')
    functions={}
    for line in symbols.splitlines():
        f=line.split()
        if len(f)>=6 and f[-1] in required:functions[f[-1]]={'address':f[0],'section':f[-3],'size_hex':f[-2]}
    assert set(functions)==set(required) and all(v['section']=='.iram0.text' for v in functions.values())
    disassembly=''.join(tool('riscv32-esp-elf-objdump','-d','--disassemble='+n,elf) for n in required)
    (HERE/'isr-disassembly.txt').write_text(disassembly)
    pad=tool('riscv32-esp-elf-objdump','-d','--disassemble=pad_off_locked',elf)
    assert not re.search(r'\b(?:jal|jalr|call)\b',pad)
    isr=tool('riscv32-esp-elf-objdump','-d','--disassemble=dock_detached',elf)
    calls=re.findall(r'\bjal\s+[^\n]*<([^>]+)>',isr)
    assert set(calls)=={'pad_off_locked','vPortEnterCritical','vPortExitCritical'}
    legacy=tool('riscv32-esp-elf-nm','-a',BUILD/'prototype-r0/firmware.elf')
    assert not re.search(r'thermal_history_source|evt_console_transport|dock_detached|pad_off_locked',legacy)
    data={}
    for line in symbols.splitlines():
        f=line.split()
        if len(f)>=6 and f[-1] in ('detach_generation','gpio_context','port_uxCriticalNesting','port_uxOldInterruptState'):
            data[f[-1]]={'address':f[0],'section':f[-3]}
    assert len(data)==4 and all(row['section'] in ('.dram0.data','.dram0.bss') for row in data.values())
    (HERE/'symbols.txt').write_text(symbols)
    artifacts=[entry(BUILD/profile/name) for profile in ('evt1','prototype-r0') for name in ('firmware.elf','firmware.bin','bootloader.bin','partitions.bin','config/sdkconfig.h')]
    report={'scope':'Thermal RAM history, USB source snapshot/debug command, host boundaries and two cross-builds; no flashed/powered result',
        'recorded_UTC':datetime.now(timezone.utc).isoformat(),'pass':True,'source_sha256':before,
        'host_tests':'PASS with UBSan; actual console LL/GPIO/driver/NVS boundary stubs plus existing control/compass/thermistor/wear and new timing/history tests',
        'cross_build':{'evt1':'PASS','prototype-r0':'PASS','warnings':0,'build_directory':str(BUILD)},
        'ISR':{'functions':functions,'direct_calls':calls,'data':data,'pad_off_no_calls':True},
        'inherited_USB_SDK_audit':entry(AUDIT),'SDK_primary_hashes_rechecked':True,
        'boot_tag_entropy':{'generated_after_NimBLE_init':True,'BT_modem_sleep_disabled':True,'PM_disabled':True,'width_bits':32,'global_uniqueness_guaranteed':False,'source':'https://docs.espressif.com/projects/esp-idf/en/v5.5.3/esp32c3/api-reference/system/random.html'},
        'build_artifacts':artifacts,'evidence':[entry(HERE/'source-snapshot.json'),*logs,entry(HERE/'isr-disassembly.txt'),entry(HERE/'symbols.txt')],
        'limits':['RAM history resets at boot/deep sleep; no UTC or durable baseline','Raw PGOOD loss is not physical removal; unobserved edges can coalesce','Charge/UV state remains unknown; no Ready threshold or wear classifier','Case BLE, charge instrumentation, full history transfer and UI remain separate integration work','No physical USB/pin latency, leakage, sensor timing, thermal or powered validation'],
        'flash_performed':False,'physical_validation':False,'full_product_order_ready':False}
    (HERE/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('PASS: frozen current sources, host timing/USB suites, two warning-free builds and linked normal-path ISR audit bound.')

if __name__=='__main__':main()
