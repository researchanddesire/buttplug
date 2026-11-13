/* Vishay NTCLE413E2103F524A; manufacturer29078 Table3 (2026-10-15).
 * Nominal R/T values at -10..60C in5C steps, converted to 12bitADC counts
 * for10k0.1% pullup to VDDA. Interpolation is not per-part calibration. */
#include "dock_app.h"
static const uint16_t ntc_adc[] = {3317, 3165, 2999, 2820, 2631, 2438, 2242, 2048, 1859, 1678, 1507, 1349, 1203, 1070, 950};
bool dock_ntc_centi_c(uint16_t raw, int16_t *out) {
    if (!out || raw<ntc_adc[14] || raw>ntc_adc[0]) return false;
    for (unsigned j=0;j<14;++j) {
        if (raw<=ntc_adc[j] && raw>=ntc_adc[j+1]) {
            *out=(int16_t)(-1000+(int)j*500+
                 (int)(ntc_adc[j]-raw)*500/(ntc_adc[j]-ntc_adc[j+1]));
            return true;
        }
    }
    return false;
}
