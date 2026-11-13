#include "dock_app.h"
#include "radio_schedule.h"
#include <assert.h>
#include <stdio.h>

int main(void)
{
    uint32_t value;
    /* 12800 counts is 200 mV. Both branches in the radio schematic are 4.22 ohm. */
    assert(dock_ads_decode(0, 12800, &value) && value == 47393);
    assert(dock_ads_decode(1, 12800, &value) && value == 47393);
    assert(radio_slot_available(0, 0));
    assert(radio_slot_available(0, 6));
    assert(!radio_slot_available(0, 7));
    assert(radio_slot_available(UINT32_MAX - 2, 3));
    assert(!radio_slot_available(UINT32_MAX - 2, 4));
    puts("PASS: radio UV monitor conversion and slot admission including tick wrap");
}
