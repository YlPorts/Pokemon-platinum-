#!/usr/bin/env python3
"""Differential test of actual OBJ draw functions, plus byte-exact CRC reuse."""
from pathlib import Path
import subprocess,sys,tempfile
root=Path(sys.argv[1]); perf=Path(__file__).resolve().parent.parent/'performance'
source=(root/'subprojects/libntr/libraries/sim/src/sim_g2.cpp').read_text()
a=source.index('void G2SIM_DrawOBJ('); b=source.index('// Draws a pixel',a)
baseline=(root/'tools/android/reference_obj.cpp').read_text().replace('G2SIM_DrawOBJ','BaselineDrawOBJ')
harness=r'''
#include <cstdint>
#include <cstring>
#include <cassert>
#include <cstdio>
#include <vector>
#include <array>
#include <random>
#include <chrono>
#include "android_obj_index.h"
#include "android_crc_memo.h"
using u32=uint32_t;using u16=uint16_t;using u8=uint8_t;using s32=int32_t;
static u32 s_reg_GXS_DB_DISPCNT=0x1000,s_reg_GX_DISPCNT=0x1000;
static u16 s_HW_DB_OAM[512],s_HW_OAM[512];
static u8 s_SIM_DBG_OAMSenable=1,s_SIM_DBG_OAMenable=1;
static ADObjIndex s_androidObjIndex[2];
static std::vector<std::array<int,10>> calls;
static void DrawOBJ_Normal(int n,int w,int h,int x,int y,int sub,int win) {
 calls.push_back({0,n,w,h,x,y,sub,win,0,0});
}
static void DrawOBJ_RotScale(int n,int bw,int bh,int w,int h,int x,int y,int sub,int win) {
 calls.push_back({1,n,bw,bh,w,h,x,y,sub,win});
}
'''
main=r'''
int main() {
 std::mt19937 rng(357);
 unsigned long long draws=0,listed=0;
 for(unsigned f=0;f<400;++f) {
  for(int i=0;i<512;++i) {s_HW_OAM[i]=rng();s_HW_DB_OAM[i]=rng();}
  if(f%9==0) s_reg_GX_DISPCNT^=0x1000;
  if(f%11==0) s_SIM_DBG_OAMSenable^=1;
  for(unsigned sub=0;sub<2;++sub) {
   s_androidObjIndex[sub].build(sub?s_HW_DB_OAM:s_HW_OAM);
   for(unsigned y=0;y<192;++y) for(int p=0;p<4;++p) {
    calls.clear();BaselineDrawOBJ(y,sub,p*0x400);auto expected=calls;
    calls.clear();G2SIM_DrawOBJ(y,sub,p*0x400);
    assert(calls==expected);draws+=calls.size();
    listed+=s_androidObjIndex[sub].count[p][y];
    if(!s_androidObjIndex[sub].count[p][y]) assert(calls.empty());
   }
  }
 }
 ADCrcMemo memo;unsigned hashes=0;
 auto hash=[&](const uint8_t *p,size_t n){++hashes;uint32_t c=2166136261u;for(size_t i=0;i<n;++i)c=(c^p[i])*16777619u;return c;};
 std::vector<uint8_t> data(131073);for(auto &v:data)v=rng();
 for(size_t n: {size_t(0),size_t(512),size_t(4096),size_t(131072),size_t(131073)}) {
  uint32_t expected=hash(data.data(),n);assert(memo.get(data.data(),n,hash)==expected);
  auto before=hashes;for(int i=0;i<100;++i)assert(memo.get(data.data(),n,hash)==expected);
  assert(hashes-before==(n>131072?100u:0u));
  if(n) for(int i=0;i<25;++i) {data[rng()%n]^=1;expected=hash(data.data(),n);assert(memo.get(data.data(),n,hash)==expected);}
 }
 printf("PASS: %llu identical sprite draw calls across 400 randomized dual-screen OAM frames; %llu indexed entries instead of 78643200 scans; CRC exact reuse, writes, bounds\n",draws,listed);
}
'''
with tempfile.TemporaryDirectory() as tmp:
    p=Path(tmp)/'test.cpp'; p.write_text(harness+baseline+source[a:b]+main)
    exe=Path(tmp)/'test'
    subprocess.run(['g++','-std=c++11','-O2','-DSDK_BUILD_ANDROID','-fsanitize=address,undefined','-fno-sanitize=shift','-I'+str(perf),str(p),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
