/* Freestanding Cortex-M0+ link proof, not an image with vectors/startup/IO. */
#include "case_link.h"
case_link compile_only_state;
const unsigned case_link_state_size = sizeof(case_link);
volatile unsigned compile_only_result;
void _start(void) {
    cl_policy p={.thermal_fresh_ms=1500,.ratio_fresh_ms=1500,
      .charge_fresh_ms={2000,2000,2000,2000,2000,2000},.max_attempt_ms=500,
      .max_gap_ms=10000,.max_anchor_age_ms=60000,.max_round_trip_ms=1000,
      .combined_clock_drift_ppm=1000,.combined_timer_resolution_ms=2,.max_sequence_advance=4};
    compile_only_result=case_link_init(&compile_only_state,1,&p,0);
    for(;;){}
}
