"""Wired Main candidate terminals and independently replayable power budget."""
from hashlib import sha256
from itertools import product
import json
from pathlib import Path
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
EVT = HERE.parents[1]
ROOT = EVT.parents[2]


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def source_terminals(path):
    return {(node.get('ref'), node.get('pin')): net.get('name')
            for net in ET.parse(path).findall('./nets/net') for node in net.findall('node')}


def calculate_power():
    frozen = json.loads((EVT / 'dock-safety/power-budget.json').read_text())
    uv = frozen['UV_normal_design']
    paths = frozen['UV_path_resistance']
    rlim = 40.2
    rset = 4.22
    rlim_error = .001 + 25e-6 * 100
    hard_host = 104.0
    normal_host = 40.0
    off_host = 1.0
    imin = 25230 / (rlim * (1 + rlim_error)) ** 1.016
    imax = 22980 / (rlim * (1 - rlim_error)) ** .94
    led_ceiling = .204 / (rset * .98)
    vout = uv['Vout_ceiling_V']
    load_watts = 2 * (led_ceiling * vout + vout ** 2 * (1 / 99000 + 1 / (1068000 * .99)))
    iuv = load_watts / (uv['efficiency_floor_assumption'] * uv['VIN_floor_V']) * 1000 + uv['driver_Iq_total_mA']
    other = (frozen['device_qualified_allocation_mA'] + frozen['dock_UI_overhead_allocation_mA']
             + frozen['contact_loops']['qualified_total_max_mA'])
    hard_total = other + hard_host + imax
    normal_total = other + hard_host + iuv  # use the hard branch allowance even at the regulated UV corner
    vin = (4.5 - normal_total / 1000 * paths['common_PCB_supply_plus_return_max_ohm']
           - iuv / 1000 * paths['common_switch_Rmax_ohm']
           - iuv / 2000 * paths['each_branch_supply_plus_return_max_ohm'])
    contact_threshold = []
    for rt, rb, ref, bias in product((97600 * .9965, 97600 * 1.0035),
                                    (10500 * .9965, 10500 * 1.0035),
                                    (.405 * .98, .405 * 1.02), (-25e-9, 25e-9)):
        contact_threshold.append(ref * (1 + rt / rb) + bias * rt)
    assert 0 < hard_total < 1500 and iuv < imin and vin > uv['VIN_floor_V']
    return {
        'legacy_USB100': {'total_steady_mA': 70 + 10 + off_host, 'host_branch_enabled': False,
                          'suspend_inrush_and_depleted_battery_validated': False},
        'new_host_branch': {'limiter': 'TPS2553QDBVRQ1, ILIM directly to IN',
                            'DC_limit_min_typ_max_mA': [50, 75, 100], 'allocated_mA': hard_host,
                            'always_on_only_allocated_mA': off_host, 'normal_increment_target_mA': normal_host,
                            'normal_margin_to_min_limit_mA': 50 - normal_host,
                            'normal_current_and_inrush_verified': False},
        'wired_coexistence': {'R107_kohm': rlim, 'R107_mpn': 'RT0603BRD0740K2L',
                             'R401_R501_ohm_each': rset, 'R401_R501_mpn': 'CRCW08054R22FKEA',
                             'UV_current_nom_mA_per_string': .2 / rset * 1000,
                             'UV_current_max_mA_per_string': led_ceiling * 1000,
                             'UV_input_required_mA': iuv, 'UV_limiter_min_mA': imin,
                             'UV_limiter_max_mA': imax, 'UV_limiter_min_margin_mA': imin - iuv,
                             'normal_total_with_full_host_allocation_mA': normal_total,
                             'hard_source_total_mA': hard_total, 'hard_source_margin_mA': 1500 - hard_total,
                             'driver_input_conservative_V': vin, 'driver_floor_V': uv['VIN_floor_V'],
                             'frozen_UV_with_added_host_total_mA': frozen['qualified_source_worst_sum_mA'] + hard_host},
        'contact_voltage_monitor': {'falling_threshold_calc_min_max_V': [min(contact_threshold), max(contact_threshold)],
                                    'rising_estimated_upper_V': max(contact_threshold) + .405 * .03 * (1 + 97600 * 1.0035 / (10500 * .9965)),
                                    'note': 'Monitor at J102.4; physical contact-side VBUS, USB compliance and dynamic detach require test.'},
        'host_voltage_monitor': {'falling_spec_min_max_V': [3.17 * .99, 3.17 * 1.01],
                                 'rising_spec_min_max_V': [3.189 * .99, 3.189 * 1.01],
                                 'LDO_regulated_spec_min_max_V': [3.3 * .985, 3.3 * 1.015],
                                 'RP2040_USB_VDD_min_V': 3.135,
                                 'note': 'Check fast droops at USB_VDD directly. Supervisor response is finite.'},
    }


# Each device maps package pin numbers to (manufacturer function, net, ERC type).
PWR, OUT, IN, IO, PA, OD, NC = ('power_in', 'power_out', 'input', 'bidirectional', 'passive', 'open_collector', 'no_connect')
TI = 'https://www.ti.com/lit/ds/symlink/'
PI = 'https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf'
PI_DESIGN = 'https://pip-assets.raspberrypi.com/categories/814-rp2040/documents/RP-008279-DS-2-hardware-design-with-rp2040.pdf'
FLASH = 'https://www.winbond.com/export/sites/winbond/product-selection-guide/file/2025-Product-Selection-Guide-Winbond-Code-Storage-Flash-Memory.pdf'


def device(mpn, manufacturer, fp, source, pins):
    return dict(mpn=mpn, manufacturer=manufacturer, footprint=fp, source=source, pins=pins)


GPIO_PINS = [*range(2, 10), *range(11, 19), *range(27, 33), *range(34, 42)]
RP = {n: (f'GPIO{i}', None, IO) for i, n in enumerate(GPIO_PINS)}
RP.update({n: ('IOVDD', 'USB_HOST_3V3', PWR) for n in (1, 10, 22, 33, 42, 49)})
RP.update({2: ('GPIO0_I2C0_SDA', 'RP_SDA', IO), 3: ('GPIO1_I2C0_SCL', 'RP_SCL', IO),
           4: ('GPIO2', 'RP_LOCAL_READY', 'output'), 5: ('GPIO3', 'RP_USB_BREAK', 'output'),
           6: ('GPIO4', 'RP_CONTACT_OK', IN), 7: ('GPIO5', 'RP_LIMIT_FAULTn', IN),
           19: ('TESTEN', 'GND', IN), 20: ('XIN', 'RP_XIN', IN), 21: ('XOUT', 'RP_XOUT', 'output'),
           23: ('DVDD', 'USB_HOST_1V1', PWR), 24: ('SWCLK', 'RP_SWCLK', IN),
           25: ('SWD', 'RP_SWDIO', IO), 26: ('RUN', 'RP_RUN', IN),
           43: ('ADC_AVDD', 'USB_HOST_3V3', PWR), 44: ('VREG_VIN', 'USB_HOST_3V3', PWR),
           45: ('VREG_VOUT', 'USB_HOST_1V1', OUT), 46: ('USB_DM', 'RP_USB_DM', IO),
           47: ('USB_DP', 'RP_USB_DP', IO), 48: ('USB_VDD', 'USB_HOST_3V3', PWR),
           50: ('DVDD', 'USB_HOST_1V1', PWR), 51: ('QSPI_SD3', 'RP_QSPI_SD3', IO),
           52: ('QSPI_SCLK', 'RP_QSPI_SCK', 'output'), 53: ('QSPI_SD0', 'RP_QSPI_SD0', IO),
           54: ('QSPI_SD2', 'RP_QSPI_SD2', IO), 55: ('QSPI_SD1', 'RP_QSPI_SD1', IO),
           56: ('QSPI_CSn', 'RP_QSPI_CSn', 'output'), 57: ('GND_EP', 'GND', PWR)})
assert set(RP) == set(range(1, 58))

DEVICES = {
    'U151': device('FSUSB42MUX', 'onsemi', 'WiredMain:Onsemi_846AP_MSOP10',
                   'https://www.onsemi.com/pdf/datasheet/fsusb42-d.pdf', {
        1: ('VCC', '3V3', PWR), 2: ('SEL', 'USB_LOCAL_SEL', IN),
        3: ('D+', 'PLUG_USB_DP', PA), 4: ('D−', 'PLUG_USB_DM', PA), 5: ('GND', 'GND', PWR),
        6: ('HSD1−', 'USB_DM', PA), 7: ('HSD1+', 'USB_DP', PA),
        8: ('HSD2−', 'USB_LOCAL_DM', PA), 9: ('HSD2+', 'USB_LOCAL_DP', PA), 10: ('OE', 'USB_OEn', IN)}),
    'U152': device('TPD2EUSB30DRTR', 'Texas Instruments', 'Package_TO_SOT_SMD:Texas_DRT-3', TI + 'tpd2eusb30.pdf', {
        1: ('D+', 'PLUG_USB_DP', PA), 2: ('D−', 'PLUG_USB_DM', PA), 3: ('GND', 'GND', PWR)}),
    'U153': device('TPS2553QDBVRQ1', 'Texas Instruments', 'Package_TO_SOT_SMD:SOT-23-6', TI + 'tps2553-q1.pdf', {
        1: ('IN', 'HOST_5V', PWR), 2: ('GND', 'GND', PWR), 3: ('EN', 'USB_HOST_PWR_EN', IN),
        4: ('FAULTn', 'RP_LIMIT_FAULTn', OD), 5: ('ILIM', 'HOST_5V', PA), 6: ('OUT', 'USB_HOST_5V', OUT)}),
    'U154': device('TPS7A2033PDBVR', 'Texas Instruments', 'Package_TO_SOT_SMD:SOT-23-5', TI + 'tps7a20.pdf', {
        1: ('IN', 'USB_HOST_5V', PWR), 2: ('GND', 'GND', PWR), 3: ('EN', 'USB_HOST_5V', IN),
        4: ('NC', None, NC), 5: ('OUT', 'USB_HOST_3V3', OUT)}),
    'U155': device('TPS389033DSER', 'Texas Instruments', 'WiredMain:TI_DSE0006A', TI + 'tps3890.pdf', {
        1: ('SENSE', 'USB_HOST_3V3', IN), 2: ('GND', 'GND', PWR), 3: ('MRn', '3V3', IN),
        4: ('VDD', '3V3', PWR), 5: ('CT', 'RP_RST_CT', PA), 6: ('RESETn', 'RP_RUN', OD)}),
    'U156': device('TPS3808G01DBVR', 'Texas Instruments', 'Package_TO_SOT_SMD:SOT-23-6', TI + 'tps3808.pdf', {
        1: ('RESETn', 'CONTACT_VBUS_OK', OD), 2: ('GND', 'GND', PWR), 3: ('MRn', 'HOST_5V', IN),
        4: ('CT', None, PA), 5: ('SENSE', 'CONTACT_VBUS_SENSE', IN), 6: ('VDD', 'HOST_5V', PWR)}),
    'U157': device('SN74HCS21PWR', 'Texas Instruments', 'Package_SO:TSSOP-14_4.4x5mm_P0.65mm', TI + 'sn74hcs21.pdf', {
        1: ('1A', 'SOURCE_OK', IN), 2: ('1B', 'SAFE_RESETn', IN), 3: ('NC', None, NC),
        4: ('1C', 'PC_LOCKn', IN), 5: ('1D', 'CC_ENABLE', IN), 6: ('1Y', 'USB_HOST_PWR_EN', 'output'),
        7: ('GND', 'GND', PWR), 8: ('2Y', 'USB_LOCAL_SEL', 'output'),
        9: ('2A', 'USB_HOST_PWR_EN', IN), 10: ('2B', 'RP_READY_AON', IN), 11: ('NC', None, NC),
        12: ('2C', 'CONTACT_VBUS_OK', IN), 13: ('2D', 'RP_RUN_AON', IN), 14: ('VCC', '3V3', PWR)}),
    'U158': device('SN74HCS00PWR', 'Texas Instruments', 'Package_SO:TSSOP-14_4.4x5mm_P0.65mm', TI + 'sn74hcs00.pdf', {
        1: ('1A', 'USB_HOST_PWR_EN', IN), 2: ('1B', 'RP_BREAK_AON', IN), 3: ('1Y', 'USB_BREAKn', 'output'),
        4: ('2A', 'CC_ENABLE', IN), 5: ('2B', 'USB_BREAKn', IN), 6: ('2Y', 'USB_OEn', 'output'),
        7: ('GND', 'GND', PWR), 8: ('3Y', None, 'output'), 9: ('3A', 'GND', IN), 10: ('3B', 'GND', IN),
        11: ('4Y', None, 'output'), 12: ('4A', 'GND', IN), 13: ('4B', 'GND', IN), 14: ('VCC', '3V3', PWR)}),
    'U159': device('SN74LVC2G17DCKR', 'Texas Instruments', 'Package_TO_SOT_SMD:SOT-363_SC-70-6', TI + 'sn74lvc2g17.pdf', {
        1: ('1A', 'RP_LOCAL_READY', IN), 2: ('GND', 'GND', PWR), 3: ('2A', 'RP_USB_BREAK', IN),
        4: ('2Y', 'RP_BREAK_AON', 'output'), 5: ('VCC', '3V3', PWR), 6: ('1Y', 'RP_READY_AON', 'output')}),
    'U160': device('RP2040', 'Raspberry Pi', 'Package_DFN_QFN:QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm', PI, dict(sorted(RP.items()))),
    'U161': device('W25Q16JVUXIQ', 'Winbond', 'WiredMain:Winbond_USON-8_2x3mm_P0.5mm_UX', FLASH, {
        1: ('CSn', 'RP_QSPI_CSn', IN), 2: ('IO1', 'RP_QSPI_SD1', IO), 3: ('IO2', 'RP_QSPI_SD2', IO),
        4: ('GND', 'GND', PWR), 5: ('IO0', 'RP_QSPI_SD0', IO), 6: ('CLK', 'RP_QSPI_SCK', IN),
        7: ('IO3', 'RP_QSPI_SD3', IO), 8: ('VCC', 'USB_HOST_3V3', PWR),
        9: ('EP', None, NC)}),
    'U162': device('TMUX1511RSVR', 'Texas Instruments', 'Radio:TI_RSV0016A', TI + 'tmux1511.pdf', {
        1: ('SEL1', 'RP_RUN', IN), 2: ('S1', 'USB_HOST_SDA', PA), 3: ('D1', 'RP_SDA', PA),
        4: ('SEL2', 'RP_RUN', IN), 5: ('S2', 'USB_HOST_SCL', PA), 6: ('D2', 'RP_SCL', PA),
        7: ('NC', None, NC), 8: ('GND', 'GND', PWR), 9: ('D3', 'RP_CONTACT_OK', PA),
        10: ('S3', 'CONTACT_VBUS_OK', PA), 11: ('SEL3', 'RP_RUN', IN), 12: ('NC', None, NC),
        13: ('D4', 'GND', PA), 14: ('S4', 'GND', PA), 15: ('SEL4', 'GND', IN), 16: ('VDD', 'USB_HOST_3V3', PWR)}),
    'U163': device('SN74LVC2G17DCKR', 'Texas Instruments', 'Package_TO_SOT_SMD:SOT-363_SC-70-6', TI + 'sn74lvc2g17.pdf', {
        1: ('1A', 'RP_RUN', IN), 2: ('GND', 'GND', PWR), 3: ('2A', 'GND', IN),
        4: ('2Y', None, 'output'), 5: ('VCC', '3V3', PWR), 6: ('1Y', 'RP_RUN_AON', 'output')}),
    'Y151': device('ABM8-272-T3', 'Abracon', 'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm',
                   'https://abracon.com/datasheets/ABM8-272-T3.pdf', {
        1: ('X1', 'RP_XIN', PA), 2: ('GND', 'GND', PA), 3: ('X2', 'RP_XTAL_OUT', PA), 4: ('GND', 'GND', PA)}),
}

# Capacitor values and placement intent are candidate specifications. Source-verified
# IC MPNs are above. Passive purchasing and layout audits follow schematic capture.
PASSIVES = {
    'R151': ('27 ohm 1%, 0402', 'RP_USB_DP', 'USB_LOCAL_DP'),
    'R152': ('27 ohm 1%, 0402', 'RP_USB_DM', 'USB_LOCAL_DM'),
    'R153': ('97.6k 0.1% 25ppm/K, 0603', 'CONTACT_5V', 'CONTACT_VBUS_SENSE'),
    'R154': ('10.5k 0.1% 25ppm/K, 0603', 'CONTACT_VBUS_SENSE', 'GND'),
    'R155': ('47k 1%', '3V3', 'CONTACT_VBUS_OK'),
    'R156': ('100k 1%', '3V3', 'PC_LOCKn'),
    'R157': ('10k 1%', 'USB_HOST_3V3', 'RP_RUN'),
    'R158': ('100k 1%', 'RP_RUN', 'GND'),
    'R159': ('100k 1%', 'RP_LOCAL_READY', 'GND'),
    'R160': ('100k 1%', 'RP_USB_BREAK', 'GND'),
    'R161': ('100k 1%', 'USB_LOCAL_SEL', 'GND'),
    'R162': ('100k 1%', 'USB_OEn', '3V3'),
    'R163': ('100k 1%', 'USB_HOST_PWR_EN', 'GND'),
    'R164': ('4.7k 1%', 'USB_HOST_SCL', '3V3'),
    'R165': ('4.7k 1%', 'USB_HOST_SDA', '3V3'),
    'R166': ('47k 1%', 'RP_LIMIT_FAULTn', 'USB_HOST_3V3'),
    'R167': ('1k 1%', 'RP_XOUT', 'RP_XTAL_OUT'),
    'R168': ('1k 1%', 'RP_QSPI_CSn', 'RP_BOOTSEL_PAD'),
    'R169': ('100k 1%', 'RP_CONTACT_OK', 'GND'),
    'R170': ('10k 1%', 'USB_HOST_3V3', 'RP_QSPI_CSn', 'U161.1'),
    'C151': ('100nF 16V X7R', '3V3', 'GND', 'U151.1'),
    'C152': ('100nF 16V X7R', 'HOST_5V', 'GND', 'U153.1'),
    'C153': ('2.2uF 16V X5R', 'USB_HOST_5V', 'GND', 'U154.1'),
    'C154': ('10uF 16V X5R', 'USB_HOST_3V3', 'GND', 'U154.5'),
    'C155': ('100nF 16V X7R', '3V3', 'GND', 'U155.4'),
    'C156': ('10nF 16V X7R', 'RP_RST_CT', 'GND', 'U155.5'),
    'C157': ('100nF 16V X7R', 'HOST_5V', 'GND', 'U156.6'),
    'C158': ('1nF 16V C0G', 'CONTACT_VBUS_SENSE', 'GND', 'U156.5'),
    'C159': ('100nF 16V X7R', '3V3', 'GND', 'U157.14'),
    'C160': ('100nF 16V X7R', '3V3', 'GND', 'U158.14'),
    'C161': ('100nF 16V X7R', '3V3', 'GND', 'U159.5'),
    'C162': ('100nF 16V X7R', '3V3', 'GND', 'U163.5'),
    'C163': ('100nF 16V X7R', 'USB_HOST_3V3', 'GND', 'U162.16'),
    'C164': ('100nF 16V X7R', 'USB_HOST_3V3', 'GND', 'U161.8'),
    'C165': ('1uF 16V X5R', 'USB_HOST_3V3', 'GND', 'U160.44'),
    'C166': ('1uF 16V X5R', 'USB_HOST_1V1', 'GND', 'U160.45'),
    'C167': ('15pF 50V C0G 5%', 'RP_XIN', 'GND', 'U160.20'),
    'C168': ('15pF 50V C0G 5%', 'RP_XTAL_OUT', 'GND', 'Y151.3'),
}
for index, pin in enumerate((1, 10, 22, 33, 42, 49, 43, 48, 23, 50), start=169):
    PASSIVES[f'C{index}'] = ('100nF 16V X7R', RP[pin][1], 'GND', f'U160.{pin}')

RETAINED = {'J101.A6': 'USB_DP', 'J101.B6': 'USB_DP', 'J101.A7': 'USB_DM', 'J101.B7': 'USB_DM',
            'U121.1': 'USB_DM', 'U121.6': 'USB_DM', 'U121.3': 'USB_DP', 'U121.4': 'USB_DP',
            'U121.5': 'HOST_5V', 'J102.1': 'GND', 'J102.4': 'CONTACT_5V'}
CHANGED = {'J102.2': ('USB_DM', 'PLUG_USB_DM'), 'J102.3': ('USB_DP', 'PLUG_USB_DP'),
           'U201.5': (None, 'USB_HOST_SCL'), 'U201.6': (None, 'USB_HOST_SDA')}


def check_usb_logic():
    count = 0
    for rail, source, safe, unlocked, phy_run, ready, contact, blank in product((False, True), repeat=8):
        power = rail and source and safe and unlocked
        select_local = power and phy_run and ready and contact
        disabled = not rail or (power and blank)
        if not rail:
            assert disabled and not select_local and not power
        if not source or not safe or not unlocked:
            assert not power and not select_local and disabled == (not rail)
        if select_local:
            assert all((rail, source, safe, unlocked, phy_run, ready, contact))
        if power and blank:
            assert disabled
        count += 1
    return count


def main():
    source = EVT / 'dock-system/native.xml'
    pins = source_terminals(source)
    for terminal, net in RETAINED.items():
        assert pins[tuple(terminal.split('.'))] == net, (terminal, net)
    for terminal, (before, _) in CHANGED.items():
        actual = pins[tuple(terminal.split('.'))]
        assert actual == before if before else actual.startswith('unconnected-'), (terminal, actual)
    files = [source, EVT / 'dock-control/pin-contract.json', EVT / 'dock-ui/pin-contract.json',
             EVT / 'dock-safety/power-budget.json', EVT / 'dock-main/dock-main.kicad_pcb']
    manifest = {
        'status': 'Wired Main pin and power contract; see native-checks.json for schematic verification',
        'builder_sha256': digest(Path(__file__)),
        'source_sha256': {str(p.relative_to(ROOT)): digest(p) for p in files},
        'native_baseline_retained_terminals': RETAINED, 'native_baseline_terminal_changes': CHANGED,
        'devices': DEVICES, 'passives': PASSIVES, 'power': calculate_power(),
        'combinational_logic_vectors_checked': check_usb_logic(),
        'always_on_logic': {'USB_HOST_PWR_EN': 'SOURCE_OK & SAFE_RESETn & PC_LOCKn & CC_ENABLE',
                            'USB_LOCAL_SEL': 'USB_HOST_PWR_EN & RP_READY_AON & CONTACT_VBUS_OK & RP_RUN_AON',
                            'USB_OEn': '!CC_ENABLE | (USB_HOST_PWR_EN & RP_BREAK_AON)'},
        'service': {'PC_lock': 'short PC_LOCKn to GND before boot; 100k pull-up to 3V3; physical access open',
                    'RP_SWD': ['USB_HOST_3V3 VTREF', 'RP_SWDIO', 'RP_SWCLK', 'RP_RUN', 'GND'],
                    'RP_BOOTSEL': 'RP_QSPI_CSn via 1k to service pad; assert to ground at RP_RUN release',
                    'bridge_bus': 'U201 PH0 SCL / PH1 SDA, two-wire open-drain isolated from MON_I2C',
                    'bridge_target_address_7bit': '0x38', 'planned_USB_disconnect_ms': 100},
    }
    (HERE / 'circuit-contract.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest['power'], indent=2))


if __name__ == '__main__':
    main()
