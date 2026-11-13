#pragma once
#include <stddef.h>
#include <stdint.h>
#include "esp_err.h"
typedef uint32_t nvs_handle_t;
#define NVS_READONLY 0
#define NVS_READWRITE 1
esp_err_t nvs_open(const char *name,int mode,nvs_handle_t *handle);
esp_err_t nvs_get_blob(nvs_handle_t handle,const char *name,void *data,size_t *length);
esp_err_t nvs_erase_key(nvs_handle_t handle,const char *name);
esp_err_t nvs_set_blob(nvs_handle_t handle,const char *name,const void *data,size_t length);
esp_err_t nvs_commit(nvs_handle_t handle);
void nvs_close(nvs_handle_t handle);
