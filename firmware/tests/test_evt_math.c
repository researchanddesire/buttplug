#include "evt_math.h"
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

static evt_compass_cal_t identity(void) {
    return (evt_compass_cal_t){.version = 1, .accel_to_flange = {1,0,0,0,1,0,0,0,1},
        .mag_to_flange = {1,0,0,0,1,0,0,0,1}, .arrow = {1,0,0}};
}
static void thermistor(void) {
    /* Independent physical resistor fixtures and manufacturer table points,
     * exercised over different excitation voltages; no assumed 3.3V constant.
     */
    const double ohms[] = {10000., 5770.3, 6895.4, 18216.};
    const int expected[] = {25000, 40000, 35000, 10000};
    for (int reference = 11600; reference <= 14000; reference += 1200) {
        for (unsigned i = 0; i < sizeof(ohms)/sizeof(ohms[0]); i++) {
            int16_t tip = (int16_t)lround(2 * reference * ohms[i] / (10000. + ohms[i]));
            int result = 0;
            assert(evt_ntc_temperature(tip, reference, reference, &result));
            assert(abs(result - expected[i]) <= 20);
        }
    }
    int result;
    assert(!evt_ntc_temperature(0,13200,13200,&result));
    assert(!evt_ntc_temperature(26400,13200,13200,&result));
    assert(!evt_ntc_temperature(-1,13200,13200,&result));
    assert(!evt_ntc_temperature(13200,0,13200,&result));
    assert(!evt_ntc_temperature(13200,13200,13400,&result));
    assert(!evt_ntc_temperature(300,13200,13200,&result));
    assert(!evt_ntc_temperature(25000,13200,13200,&result));
    assert(!evt_ntc_temperature(13200,13200,13200,NULL));
    int last = 200000;
    for (int counts = 3000; counts < 23000; counts += 37) {
        if (evt_ntc_temperature(counts,13200,13200,&result)) {
            assert(result < last); last = result;
        }
    }
}
static void pack_thermistor(void) {
    /* Independent Vishay table 3 resistance points for resistor injection. */
    const double ohms[] = {27348., 10000., 5824.9, 4910.6, 2228.};
    const int expected[] = {0, 25000, 40000, 45000, 70000};
    for (int reference = 11600; reference <= 14000; reference += 1200) {
        for (unsigned i = 0; i < sizeof(ohms) / sizeof(ohms[0]); i++) {
            int16_t reading = (int16_t)lround(2 * reference * ohms[i] / (10000. + ohms[i]));
            int result = 0;
            assert(evt_pack_ntc_temperature(reading, reference - 8, reference + 8, &result));
            assert(abs(result - expected[i]) <= 20);
        }
    }
    int result = -1;
    assert(!evt_pack_ntc_temperature(0, 13200, 13200, &result));
    assert(!evt_pack_ntc_temperature(26400, 13200, 13200, &result));
    assert(!evt_pack_ntc_temperature(13200, 13200, 13400, &result));
    assert(!evt_pack_ntc_temperature(13200, 0, 13200, &result));
    assert(result == -1);
}
static double rad(int degrees) { return degrees * 3.14159265358979323846 / 180.; }
static int angular_error(int a, int b) {
    int d = abs(a - b) % 360000;
    return d > 180000 ? 360000 - d : d;
}
static void compass(void) {
    evt_compass_cal_t c = identity();
    unsigned count = 0;
    for (int yaw = 0; yaw < 360; yaw += 15)
        for (int pitch = -60; pitch <= 60; pitch += 30)
            for (int roll = -90; roll <= 90; roll += 30) {
                /* Body->world Rz(yaw) Ry(pitch) Rx(roll), with world E,N,Up.
                 * Reference heading comes directly from the known world pose.
                 */
                double cy=cos(rad(yaw)),sy=sin(rad(yaw)),cp=cos(rad(pitch)),sp=sin(rad(pitch));
                double cr=cos(rad(roll)),sr=sin(rad(roll));
                double north[3] = {sy*cp, sy*sp*sr+cy*cr, sy*sp*cr-cy*sr};
                double up[3] = {-sp, cp*sr, cp*cr};
                float a[3],m[3];
                for (int i=0; i<3; i++) {a[i]=(float)(1000*up[i]); m[i]=(float)(30*north[i]-35*up[i]);}
                int heading;
                assert(evt_heading(a,m,&c,false,false,&heading));
                int expected = ((90-yaw+360)%360)*1000;
                assert(angular_error(heading,expected) <= 2);
                /* Recover a known axis permutation, hard iron and unequal gains. */
                evt_compass_cal_t fitted = c;
                float measured[3] = {m[1]/2.f+100.f, m[2]/.5f-40.f, m[0]+25.f};
                const float matrix[9] = {0,0,1,2,0,0,0,.5f,0};
                for(unsigned i=0;i<9;i++) fitted.mag_to_flange[i]=matrix[i];
                fitted.mag_offset_ut[0]=100;fitted.mag_offset_ut[1]=-40;fitted.mag_offset_ut[2]=25;
                assert(evt_heading(a,measured,&fitted,false,false,&heading));
                assert(angular_error(heading,expected) <= 2);
                count += 2;
            }
    float a[3]={0,0,1000},m[3]={30,0,-35}; int h;
    assert(!evt_heading(a,m,&c,true,false,&h));
    assert(!evt_heading(a,m,&c,false,true,&h));
    a[2]=1500;assert(!evt_heading(a,m,&c,false,false,&h));a[2]=1000;
    m[0]=0;assert(!evt_heading(a,m,&c,false,false,&h));m[0]=300;
    assert(!evt_heading(a,m,&c,false,false,&h));m[0]=30;
    c.arrow[0]=0;c.arrow[2]=1;assert(!evt_heading(a,m,&c,false,false,&h));c=identity();
    c.version=0;assert(!evt_heading(a,m,&c,false,false,&h));c=identity();
    c.mag_to_flange[0]=NAN;assert(!evt_compass_cal_valid(&c));c=identity();
    c.accel_to_flange[0]=2;assert(!evt_compass_cal_valid(&c));c=identity();
    assert(!evt_heading(NULL,m,&c,false,false,&h));
    printf("EVT compass: %u known tilted poses and calibrations passed\n",count);
}
int main(void) {
    thermistor(); pack_thermistor(); compass();
    puts("EVT thermistor fixtures, rail/open/short/drift and compass rejection tests passed");
    return 0;
}
