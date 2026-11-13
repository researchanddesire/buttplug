#pragma once
#include <stdbool.h>
struct ble_npl_event;
typedef void ble_npl_event_fn(struct ble_npl_event *);
struct ble_npl_event { ble_npl_event_fn *fn;void *arg;bool queued; };
struct ble_npl_eventq { unsigned unused; };
void ble_npl_event_init(struct ble_npl_event *event,ble_npl_event_fn *fn,void *arg);
void ble_npl_eventq_put(struct ble_npl_eventq *queue,struct ble_npl_event *event);
