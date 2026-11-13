#include "evt_math.h"
#include <math.h>
#include <stddef.h>
#include <stdlib.h>

bool evt_ntc_temperature(int16_t tip, int16_t rb, int16_t ra, int *millic) {
    /* TDK B57540G1103F000 curve8307, manufacturer table p7, R25=Rpull=10k.
     * Interpolate ln(R/R25); never extrapolate a fault. Nominal curve only.
     */
    static const float ratio[] = {
        7.2181f, 5.6332f, 4.4308f, 3.5112f, 2.8024f, 2.252f, 1.8216f,
        1.4827f, 1.2142f, 1.f, .82818f, .68954f, .57703f, .48525f,
        .41000f, .34798f, .29663f, .25392f, .21824f, .18830f, .16307f,
        .14174f, .12362f, .10818f, .094973f
    };
    if (!millic || rb < 11200 || rb > 14400 || ra < 11200 || ra > 14400)
        return false; /* Excitation outside 2.8..3.6V, wrong gain or missing ADC. */
    if (abs((int)ra - (int)rb) > 80) return false; /* >20mV excitation drift. */
    int32_t excitation = (int32_t)rb + ra;
    if (tip < 32 || tip >= excitation - 32) return false; /* Short / open. */
    float r = (float)tip / (float)(excitation - tip);
    size_t count = sizeof(ratio) / sizeof(ratio[0]);
    if (r > ratio[0] || r < ratio[count - 1]) return false;
    for (size_t i = 1; i < count; i++) {
        if (r >= ratio[i]) {
            float f = (logf(ratio[i - 1]) - logf(r)) /
                      (logf(ratio[i - 1]) - logf(ratio[i]));
            *millic = (int)lroundf(-20000.f + 5000.f * ((float)(i - 1) + f));
            return true;
        }
    }
    return false;
}
static float dot(const float a[3], const float b[3]) {
    return a[0]*b[0] + a[1]*b[1] + a[2]*b[2];
}
static bool finite3(const float a[3]) {
    return isfinite(a[0]) && isfinite(a[1]) && isfinite(a[2]);
}
static void transform(const float m[9], const float v[3], float out[3]) {
    for (unsigned i = 0; i < 3; i++) out[i] = dot(&m[3*i], v);
}
static bool matrix_valid(const float m[9], bool rotation) {
    for (unsigned i = 0; i < 9; i++) if (!isfinite(m[i])) return false;
    float det = m[0]*(m[4]*m[8]-m[5]*m[7]) -
                m[1]*(m[3]*m[8]-m[5]*m[6]) + m[2]*(m[3]*m[7]-m[4]*m[6]);
    if (!isfinite(det) || fabsf(det) < .1f || fabsf(det) > 10.f) return false;
    for (unsigned i = 0; i < 3; i++) {
        float n = dot(&m[3*i], &m[3*i]);
        if (rotation ? fabsf(n - 1.f) > .01f : n < .04f || n > 25.f) return false;
        if (rotation)
            for (unsigned j = i + 1; j < 3; j++)
                if (fabsf(dot(&m[3*i], &m[3*j])) > .01f) return false;
    }
    return true;
}
bool evt_compass_cal_valid(const evt_compass_cal_t *c) {
    if (!c || c->version != 1 || !matrix_valid(c->accel_to_flange, true) ||
        !matrix_valid(c->mag_to_flange, false) || !finite3(c->mag_offset_ut) ||
        !finite3(c->arrow)) return false;
    for (unsigned i = 0; i < 3; i++) if (fabsf(c->mag_offset_ut[i]) > 4000.f) return false;
    return fabsf(dot(c->arrow, c->arrow) - 1.f) <= .01f;
}
bool evt_heading(const float accel[3], const float magnetic[3],
                 const evt_compass_cal_t *c, bool docked, bool motor, int *mdeg) {
    if (!mdeg || !accel || !magnetic || docked || motor || !evt_compass_cal_valid(c) ||
        !finite3(accel) || !finite3(magnetic)) return false;
    float a[3], m[3], corrected[3];
    for (unsigned i = 0; i < 3; i++) corrected[i] = magnetic[i] - c->mag_offset_ut[i];
    transform(c->accel_to_flange, accel, a);
    transform(c->mag_to_flange, corrected, m);
    float an = sqrtf(dot(a, a)), mn = sqrtf(dot(m, m));
    if (an < 850.f || an > 1150.f || mn < 10.f || mn > 100.f) return false;
    float up[3], north[3], east[3], arrow[3];
    for (unsigned i = 0; i < 3; i++) up[i] = a[i] / an;
    float vertical_m = dot(m, up), vertical_arrow = dot(c->arrow, up);
    for (unsigned i = 0; i < 3; i++) {
        north[i] = m[i] - vertical_m * up[i];
        arrow[i] = c->arrow[i] - vertical_arrow * up[i];
    }
    float nn = sqrtf(dot(north, north)), fn = sqrtf(dot(arrow, arrow));
    if (nn < 5.f || fn < .2f) return false; /* Pole / near-vertical arrow. */
    for (unsigned i = 0; i < 3; i++) north[i] /= nn;
    east[0] = north[1]*up[2] - north[2]*up[1];
    east[1] = north[2]*up[0] - north[0]*up[2];
    east[2] = north[0]*up[1] - north[1]*up[0];
    float heading = atan2f(dot(arrow, east), dot(arrow, north)) * (180000.f / 3.14159265358979323846f);
    int value = (int)lroundf(heading);
    *mdeg = (value % 360000 + 360000) % 360000;
    return true;
}
