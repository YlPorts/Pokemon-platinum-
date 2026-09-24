#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>
#include <string.h>
#include <simulator/sim_crc32.h>
extern u32 baseline_crc32buf(u8 *,size_t);
static double now(void) { struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9; }
int main(void) {
 unsigned char *buf=malloc(131072+32);unsigned state=1234567;
 for(int i=0;i<131104;i++) { state=state*1664525u+1013904223u;buf[i]=(unsigned char)(state>>24); }
 assert(SIM_crc32buf((u8*)"123456789",9)==0xcbf43926u);
 assert(SIM_crc32buf(buf,0)==0);
 for(int offset=0;offset<16;offset++) {
  for(size_t n=0;n<1024;n++) assert(SIM_crc32buf(buf+offset,n)==baseline_crc32buf(buf+offset,n));
  for(size_t n=1024;n<=131072;n+=1024) assert(SIM_crc32buf(buf+offset,n)==baseline_crc32buf(buf+offset,n));
 }
 volatile u32 sink=0; const int repeats=8192;
 double t=now();for(int i=0;i<repeats;i++) sink^=baseline_crc32buf(buf+(i&7),32768);double old=now()-t;
 t=now();for(int i=0;i<repeats;i++) sink^=SIM_crc32buf(buf+(i&7),32768);double fast=now()-t;
 printf("PASS: CRC bit-identical, lengths 0..128 KiB, 16 alignments; benchmark 256 MiB old=%.3fs new=%.3fs ratio=%.2fx (%u)\n",old,fast,old/fast,sink);
 free(buf);
}
