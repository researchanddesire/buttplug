#pragma once
typedef struct cJSON {double valuedouble;} cJSON;
cJSON *cJSON_GetObjectItemCaseSensitive(const cJSON *root,const char *name);
int cJSON_IsArray(const cJSON *value);
int cJSON_GetArraySize(const cJSON *value);
cJSON *cJSON_GetArrayItem(const cJSON *value,int index);
int cJSON_IsNumber(const cJSON *value);
cJSON *cJSON_ParseWithOpts(const char *text,const char **end,int require_end);
int cJSON_IsObject(const cJSON *value);
void cJSON_Delete(cJSON *value);
