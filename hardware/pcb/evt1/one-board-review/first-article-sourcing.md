# EVT1 one-board first-article sourcing

Public catalog snapshot from 2026-11-16, Toronto, covering 102 SMT positions across 47 MPNs before the latest first-article substitutions. The counts are JLCPCB public inventory / available-to-order, followed by LCSC's separately listed component stock. Confirm the quantity plus placement loss and acceptable tape/reel format with the assembler. JLCPCB assembly availability can differ from LCSC cut-tape stock. A dash means no exact result or no field returned. [JLCPCB parts library](https://jlcpcb.com/parts)

The current schematics include 360 kΩ at R21 and the reduced SYS bank with
C12 and C22 left empty. Use the [selected-parts validation](selected-parts-validation.md)
for the electrical basis and the [current stock mapping](first-article-jlc-stock.json)
for the 100 populated SMT positions, exact JLC codes and parts requiring
allocation or local placement.

The candidate already selects ESP32-C3-MINI-1-H4X at U6, TPS3808G33QDBVRQ1 at U9 and MSASL21GBB5476MTNA01 at C83. Their earlier exact MPNs listed zero at JLCPCB. The engineering checks still apply to the selected changes. [Electrical equivalence and C83 qualification](jlc-and-pack-temperature.md)

The reviewed source snapshots had SHA-256 `454e1327a6b162ec160fc45b989a6f3eafa96612c10afbca64963b84ae568038` for SMT selections, `1128a8e7b0dc2eed511c92d6b3af4f4e5813257319c5143edbbc3bc596ce2460` for manual positions and `b0503b91eaee785cd43ac90713648a38f3f6cc82b28edabae9a4df866a5a06ec` for native schematic XML.

## First-article exceptions and alternatives for review

| Positions | First-article path |
| --- | --- |
| C1, C2 | Original Murata GRM21BR71A475KA73L is obsolete. GRM21BR71C475KE51L keeps 0805, 4.7 µF ±10% and X7R, with 16 V rating. JLCPCB C408144 listed 6,923 available. Check the candidate's 1.40 mm maximum against the 1.35 mm original, and confirm operating-bias capacitance at charger input and output. [JLCPCB](https://jlcpcb.com/partdetail/C408144) · [Murata capacitance curves](https://ds.murata.com/simsurfing/mlcc.html?partnumbers=%5B%22GRM21BR71C475KE51%22%5D) · [DigiKey original and substitutions](https://www.digikey.com/en/products/detail/murata-electronics/GRM21BR71A475KA73L/2546948) |
| C33 | Keep exact TDK C1608X7R1E105K080AB via DigiKey (97,200 on the US listing). For a single-source JLCPCB run, review Murata GRM188R71E105KA12D (C86020, 43,374 available), same 0603 nominal 1 µF ±10% / 25 V / X7R. Check body limit and biased performance. [DigiKey exact](https://www.digikey.com/en/products/detail/tdk/C1608X7R1E105K080AB/2443997) · [JLCPCB candidate](https://jlcpcb.com/partdetail/C86020) |
| C51–C54 | Exact TDK C1608X5R1A106K080AC shows zero current and 4,000 incoming at DigiKey Canada on 2026-11-17. Samsung CL10A106KP8NNNC (C19702, 8,890,497 JLCPCB available) keeps 0603, 10 µF ±10%, 10 V, X5R and has 0.90 mm maximum thickness. Check DC-bias performance and converter first-pulse/rail response before adopting it. [DigiKey exact and listed direct substitute](https://www.digikey.ca/en/products/detail/tdk-corporation/C1608X5R1A106K080AC/2732921) · [JLCPCB candidate](https://jlcpcb.com/partdetail/C19702) |
| R1, R2, R45, R46 | Keep the exact Vishay parts via authorized distribution. Exact R1 DigiKey Canada 9,483, R2 Mouser 12,301, R45 Mouser 109,154, R46 DigiKey Canada 30,479. JLCPCB showed three R46 available, which gives little placement margin. [R1](https://www.digikey.ca/en/products/detail/vishay-dale/TNPW04028K87BEED/1606418) · [R2](https://www.mouser.com/en/ProductDetail/Vishay/TNPW04023K24BEED?qs=wTZ%2FFzl837YMd8lB7%2FTnlg%3D%3D) · [R45](https://www.mouser.com/ProductDetail/Vishay/TNPW0603200KBEEA?qs=U8jWr0D8IJiDA54VKGDGcg%3D%3D) · [R46](https://www.digikey.ca/en/products/detail/vishay-dale/TNPW040211K0BEED/7354921) |
| R11 | YAGEO RT0603BRD07312KL preserves the nominal 312 kΩ, ±0.1% and ±25 ppm/°C in 0603. DigiKey Canada listed 3,069. Verify the slightly different dimensional specification against the KiCad land and the lower divider's ratio tolerance. [DigiKey](https://www.digikey.ca/en/products/detail/yageo/RT0603BRD07312KL/5927923) |
| R21 | No exact 362 kΩ stock verified. Panasonic ERA-6AEB364V is a 360 kΩ, 0805, ±0.1%, ±25 ppm/°C thin-film candidate. DigiKey US listed 2,031; its Canada catalog listed 4,131. With the retained 100 kΩ lower leg and TPS63070 nominal 0.800 V feedback, this sets 3.680 V compared with the 3.696 V design nominal. Review converter feedback tolerance, rail startup and loaded first-pulse voltage before choosing it. [DigiKey](https://www.digikey.com/en/products/detail/panasonic-industry/ERA-6AEB364V/1466008) · [TI TPS63070 feedback and limits](https://www.ti.com/lit/ds/symlink/tps63070.pdf) |
| R43 | Panasonic ERA-6AEB7153V keeps 715 kΩ ±0.1%, ±25 ppm/°C, 0805. DigiKey US listed 3,729 and JLCPCB C2087398 showed zero. Check guard-divider hot/cold thresholds and hold-open JP1 verification for the actual as-built resistor. [DigiKey alternate](https://www.digikey.com/en/products/detail/panasonic-electronic-components/ERA-6AEB7153V/2025921) · [JLCPCB alternate](https://jlcpcb.com/partdetail/C2087398) |
| R75, R76 | No exact 22 Ω Vishay TNPW040222R0BEED listing verified. Vishay's TNPW e3 0402 ±0.1% / ±25 ppm range begins at 47 Ω. YAGEO 22 Ω ±1% 0402 RC0402FR-0722RL (C114765, 8,222,493 available) is a same-value candidate for both series positions. Confirm USB recovery and transfers with the installed contacts. [Vishay data](https://www.vishay.com/docs/28758/tnpw_e3.pdf) · [JLCPCB candidate](https://jlcpcb.com/partdetail/C114765) |
| D71–D73 | LCSC lists 1,425 of exact Vishay BAT54WS-E3-08. JLCPCB available-to-order is zero even though it displays inventory. Confirm LCSC's tape minimum and the assembler's acceptance. [LCSC](https://www.lcsc.com/product-detail/C917483.html) |
| U5 | JLCPCB lists seven physical and four available-to-order, while LCSC lists seven exact parts with minimum one. Confirm placement loss for the first article. [Exact DRV8212 sourcing and variant review](motor-driver-first-article.md) |

## Exact product SMT list

| Reference | Qty / board | Exact selected MPN | JLCPCB code | JLCPCB inventory / available | LCSC stock | Treatment |
| --- | ---: | --- | --- | ---: | ---: | --- |
| C1, C2 | 2 | GRM21BR71A475KA73L | [C86039](https://jlcpcb.com/partdetail/C86039) | 0 / 0 | [0](https://www.lcsc.com/product-detail/C86039.html) | Obsolete |
| C3, C11, C12, C31, C21, C22 | 6 | GRM21BR61A106KE19L | [C77073](https://jlcpcb.com/partdetail/C77073) | 21,417 / 20,262 | [19,190](https://www.lcsc.com/product-detail/C77073.html) | Listed |
| C13, C14, C15, C23, C24, C25 | 6 | GRM31CR71A226KE15L | [C91604](https://jlcpcb.com/partdetail/C91604) | 22,053 / 18,836 | [15,910](https://www.lcsc.com/product-detail/C91604.html) | Listed |
| C16, C32, C34, C43, C44, C26, C27 | 7 | GRM188R71C104KA01D | [C45000](https://jlcpcb.com/partdetail/C45000) | 66,719 / 58,978 | [52,200](https://www.lcsc.com/product-detail/C45000.html) | Listed |
| C51, C52, C53, C54 | 4 | C1608X5R1A106K080AC | [C2167467](https://jlcpcb.com/partdetail/C2167467) | 0 / 0 | [0](https://www.lcsc.com/product-detail/C2167467.html) | No JLC/LCSC stock |
| L1, L2 | 2 | XFL4020-152MEC | [C3033018](https://jlcpcb.com/partdetail/C3033018) | 19,025 / 18,966 | [19,025](https://www.lcsc.com/product-detail/C3033018.html) | Listed |
| R1 | 1 | TNPW04028K87BEED | [C2089546](https://jlcpcb.com/partdetail/C2089546) | 0 / 0 | [0](https://www.lcsc.com/product-detail/C2089546.html) | No JLC/LCSC stock |
| R2 | 1 | TNPW04023K24BEED | [C1870337](https://jlcpcb.com/partdetail/C1870337) | 0 / 0 | [0](https://www.lcsc.com/product-detail/C1870337.html) | No JLC/LCSC stock |
| R3, R4, R5, R42, R71, R61, R62, R63, R88 | 9 | TNPW040210K0BEED | [C844452](https://jlcpcb.com/partdetail/C844452) | 67,648 / 61,983 | [56,340](https://www.lcsc.com/product-detail/C844452.html) | Listed |
| R11 | 1 | TNPW0603312KBEEA | — | — | — | No exact public match |
| R12, R22 | 2 | TNPW0603100KBEEA | [C844888](https://jlcpcb.com/partdetail/C844888) | 25,922 / 25,583 | [25,920](https://www.lcsc.com/product-detail/C844888.html) | Listed |
| R13, R31, R32, R33, R34, R35, R36, R26 | 8 | TNPW060310K0BEEA | [C844890](https://jlcpcb.com/partdetail/C844890) | 69,307 / 59,143 | [49,030](https://www.lcsc.com/product-detail/C844890.html) | Listed |
| U1 | 1 | BQ24074RGTR | [C54313](https://jlcpcb.com/partdetail/C54313) | 3,557 / 3,343 | [3,567](https://www.lcsc.com/product-detail/C54313.html) | Listed |
| U2, U3 | 2 | TPS63070RNMR | [C109322](https://jlcpcb.com/partdetail/C109322) | 17,907 / 17,418 | [17,232](https://www.lcsc.com/product-detail/C109322.html) | Listed |
| C33 | 1 | C1608X7R1E105K080AB | [C2170660](https://jlcpcb.com/partdetail/C2170660) | 3 / 0 | [0](https://www.lcsc.com/product-detail/C2170660.html) | No JLC/LCSC stock |
| J4 | 1 | SM06B-SRSS-TB(LF)(SN) | [C160405](https://jlcpcb.com/partdetail/C160405) | 18,064 / 17,382 | [16,883](https://www.lcsc.com/product-detail/C160405.html) | Listed |
| R37, R38 | 2 | TNPW06034K70BEEA | [C844460](https://jlcpcb.com/partdetail/C844460) | 2,628 / 2,470 | [2,315](https://www.lcsc.com/product-detail/C844460.html) | Listed |
| R39, R40 | 2 | TNPW08051M00BEEA | [C844679](https://jlcpcb.com/partdetail/C844679) | 36,793 / 35,536 | [34,290](https://www.lcsc.com/product-detail/C844679.html) | Listed |
| SW1, SW2 | 2 | B3U-1000P | [C231329](https://jlcpcb.com/partdetail/C231329) | 68,130 / 65,599 | [63,610](https://www.lcsc.com/product-detail/C231329.html) | Listed |
| U6 | 1 | ESP32-C3-MINI-1-H4X | [C41349510](https://jlcpcb.com/partdetail/C41349510) | 1,680 / 1,032 | [1,680](https://www.lcsc.com/product-detail/C41349510.html) | Selected change |
| Q1 | 1 | AO3400A | [C20917](https://jlcpcb.com/partdetail/C20917) | 1,215,829 / 1,056,411 | [611,015](https://www.lcsc.com/product-detail/C20917.html) | Listed |
| R43 | 1 | TNPW0805715KBEEA | [C4046575](https://jlcpcb.com/partdetail/C4046575) | 0 / 0 | [0](https://www.lcsc.com/product-detail/C4046575.html) | No JLC/LCSC stock |
| R44 | 1 | TNPW0603110KBEEA | [C2075212](https://jlcpcb.com/partdetail/C2075212) | 9,763 / 9,757 | [9,760](https://www.lcsc.com/product-detail/C2075212.html) | Listed |
| R45 | 1 | TNPW0603200KBEEA | [C844456](https://jlcpcb.com/partdetail/C844456) | 0 / 0 | [0](https://www.lcsc.com/product-detail/C844456.html) | No JLC/LCSC stock |
| R46 | 1 | TNPW040211K0BEED | [C2075276](https://jlcpcb.com/partdetail/C2075276) | 3 / 3 | [0](https://www.lcsc.com/product-detail/C2075276.html) | Small lot |
| R47 | 1 | TNPW04021K00BEED | [C843869](https://jlcpcb.com/partdetail/C843869) | 25,397 / 25,332 | [25,390](https://www.lcsc.com/product-detail/C843869.html) | Listed |
| R48, R23, R24, R25 | 4 | TNPW0402100KBEED | [C844674](https://jlcpcb.com/partdetail/C844674) | 13,634 / 13,528 | [13,630](https://www.lcsc.com/product-detail/C844674.html) | Listed |
| U8 | 1 | TPS3700DDCR | [C33002](https://jlcpcb.com/partdetail/C33002) | 7,817 / 7,450 | [7,120](https://www.lcsc.com/product-detail/C33002.html) | Listed |
| U9 | 1 | TPS3808G33QDBVRQ1 | [C414616](https://jlcpcb.com/partdetail/C414616) | 781 / 773 | [781](https://www.lcsc.com/product-detail/C414616.html) | Selected change |
| C71, C28, C29, C61, C82, C84 | 6 | GRM155R71C104KA88D | [C71629](https://jlcpcb.com/partdetail/C71629) | 1,107,405 / 1,001,757 | [904,100](https://www.lcsc.com/product-detail/C71629.html) | Listed |
| D71, D72, D73 | 3 | BAT54WS-E3-08 | [C917483](https://jlcpcb.com/partdetail/C917483) | 1,426 / 0 | [1,425](https://www.lcsc.com/product-detail/C917483.html) | LCSC cut tape |
| U71 | 1 | TPS3422EGDRYR | [C70288](https://jlcpcb.com/partdetail/C70288) | 3,799 / 3,628 | [3,466](https://www.lcsc.com/product-detail/C70288.html) | Listed |
| C30 | 1 | GRM32ER61A476KE20L | [C397312](https://jlcpcb.com/partdetail/C397312) | 388 / 42 | [0](https://www.lcsc.com/product-detail/C397312.html) | Listed |
| J3, J8 | 2 | SM02B-SRSS-TB(LF)(SN) | [C160402](https://jlcpcb.com/partdetail/C160402) | 47,064 / 45,293 | [43,550](https://www.lcsc.com/product-detail/C160402.html) | Listed |
| R21 | 1 | TNPW0805362KBEEA | — | — | — | No exact public match |
| U4 | 1 | SN74LVC1G11DBVR | [C22046](https://jlcpcb.com/partdetail/C22046) | 27,808 / 27,633 | [27,805](https://www.lcsc.com/product-detail/C22046.html) | Listed |
| U5 | 1 | DRV8212DSGR | [C2843766](https://jlcpcb.com/partdetail/C2843766) | 7 / 4 | [7](https://www.lcsc.com/product-detail/C2843766.html) | Small lot |
| C62, C63, C88 | 3 | GRM155R71H103KA88D | [C77019](https://jlcpcb.com/partdetail/C77019) | 517,135 / 482,764 | [449,100](https://www.lcsc.com/product-detail/C77019.html) | Listed |
| J5 | 1 | BM02B-SRSS-TB(LF)(SN) | [C160388](https://jlcpcb.com/partdetail/C160388) | 3,106 / 2,031 | [3,105](https://www.lcsc.com/product-detail/C160388.html) | Listed |
| U7 | 1 | ADS1115IDGSR | [C37593](https://jlcpcb.com/partdetail/C37593) | 8,645 / 5,532 | [5,495](https://www.lcsc.com/product-detail/C37593.html) | Listed |
| D1 | 1 | B140HW-7 | [C134429](https://jlcpcb.com/partdetail/C134429) | 5,194 / 5,079 | [5,190](https://www.lcsc.com/product-detail/C134429.html) | Listed |
| F1 | 1 | 1206L050YR | [C163512](https://jlcpcb.com/partdetail/C163512) | 9,312 / 9,082 | [9,310](https://www.lcsc.com/product-detail/C163512.html) | Listed |
| R75, R76 | 2 | TNPW040222R0BEED | — | — | — | No exact public match |
| U75 | 1 | USBLC6-2SC6 | [C7519](https://jlcpcb.com/partdetail/C7519) | 43,574 / 38,906 | [40,720](https://www.lcsc.com/product-detail/C7519.html) | Listed |
| C81 | 1 | GRM155R71C224KA12D | [C77011](https://jlcpcb.com/partdetail/C77011) | 34,141 / 31,922 | [29,700](https://www.lcsc.com/product-detail/C77011.html) | Listed |
| C83 | 1 | MSASL21GBB5476MTNA01 | [C386058](https://jlcpcb.com/partdetail/C386058) | 18,364 / 18,240 | [18,360](https://www.lcsc.com/product-detail/C386058.html) | Selected change |
| U81 | 1 | LSM303AGRTR | [C126671](https://jlcpcb.com/partdetail/C126671) | 9,866 / 9,749 | [9,668](https://www.lcsc.com/product-detail/C126671.html) | Listed |

## Manual items and the bench service harness

| Item | Per unit | Source and assembly treatment |
| --- | ---: | --- |
| CT1–CT4 | 4 per board | Exact Mill-Max 1946-0-00-15-00-00-03-0 is a manual installation after finished-hole and shoulder-fixture checks. DigiKey Canada listed 17,200. LCSC C17667984 listed zero. [DigiKey](https://www.digikey.ca/en/products/detail/mill-max-manufacturing-corp/1946-0-00-15-00-00-03-0/5176096) · [LCSC](https://www.lcsc.com/product-detail/C17667984.html) |
| J2 and JP1 | 1 each per board | Hand-solder the harness to J2 bare lands. JP1 is copper-only and starts open. [Manual positions](../one-board/manual-positions.csv) |
| TH1–TH3 | 3 per product | Vishay NTCLE413E2103F524A is a separate harness item, with LCSC C17608245 at zero and Mouser Canada previously listing 911. [Mouser](https://www.mouser.ca/en/ProductDetail/Vishay-BC-Components/NTCLE413E2103F524A?qs=vLWxofP3U2y0E8FFp8KP0w%3D%3D) · [LCSC](https://www.lcsc.com/product-detail/C17608245.html) |
| Tip NTC | 1 per product | TDK B57540G1103F000, LCSC C3153916 listed 1,040. [LCSC](https://www.lcsc.com/product-detail/C3153916.html) |
| J4 service mate | 1 bench harness | The installed J4 is JST SM06B-SRSS-TB(LF)(SN), 1.00 mm SH, side-entry. For one temporary service harness, use one SHR-06V-S-B housing (LCSC C394368, 6,220) and six SSH-003T-P0.2-H contacts (C263995, 340,500). The JST terminals specify 28–32 AWG. [JST SH series](https://www.jst-mfg.com/product/index.php?lang=en&series=231) · [Housing](https://www.lcsc.com/product-detail/C394368.html) · [Terminals](https://www.lcsc.com/product-detail/C263995.html) |

Native J4 pins 1–6 are GND, USB D−, USB D+, MCU_EN, BOOT_N and UART_TX. Bench service requires independent board power because J4 has no VBUS pin. Use a single USB host at a time. Verify continuity to these pin numbers at the fixture mate and establish access before closing the product. [Native schematic XML](../one-board/compass-one-board-native.xml) · [USB service-branch review](usb-stack-review.md)

The requested protected battery remains a supplier RFQ, with no accepted pack or allocation. Confirm the exact motor separately against the released sample and lead treatment. [Pack RFQ](../pack-lead-feasibility/RFQ.md)
