#include <stddef.h>
void *memset(void *dst,int value,size_t n){unsigned char *d=dst;while(n--)*d++=(unsigned char)value;return dst;}
void *memcpy(void *dst,const void *src,size_t n){unsigned char *d=dst;const unsigned char *s=src;while(n--)*d++=*s++;return dst;}
void __aeabi_memclr4(void *dst,size_t n){(void)memset(dst,0,n);}
void __aeabi_memclr(void *dst,size_t n){(void)memset(dst,0,n);}
void __aeabi_memcpy(void *dst,const void *src,size_t n){(void)memcpy(dst,src,n);}
void __aeabi_memcpy4(void *dst,const void *src,size_t n){(void)memcpy(dst,src,n);}
