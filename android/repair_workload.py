#!/usr/bin/env python3
"""Exact work reduction and durable Android performance logs; after repair_timing."""
from pathlib import Path
import shutil,sys
root=Path(sys.argv[1]); base=Path(__file__).parent
ntr=root/'subprojects/libntr'; sim=ntr/'libraries/sim'
def edit(p,old,new,count=1):
    s=p.read_text(); assert s.count(old)==count,(str(p),old[:80],s.count(old)); p.write_text(s.replace(old,new))
for name in ('android_obj_index.h','android_crc_memo.h','android_clock.inc'):
    shutil.copyfile(base/'performance'/name,sim/'include'/name)
p=sim/'src/sim_g2.cpp'
s=p.read_text(); a=s.index('void G2SIM_DrawOBJ('); b=s.index('// Draws a pixel',a)
# Retain the original callable implementation for differential tests. Fix its
# uninitialized mosaic scanline before comparison (mosaic is otherwise unchanged).
reference=s[a:b].replace('u32 sprline;','u32 sprline = line;')
(root/'tools/android/reference_obj.cpp').write_text(reference)
edit(p,'void G2SIM_DrawOBJ(','''#ifdef SDK_BUILD_ANDROID
#include "android_obj_index.h"
static ADObjIndex s_androidObjIndex[2];
void G2SIM_PrepareOBJ(u8 isSub) {
    s_androidObjIndex[isSub].build((const uint16_t *)(isSub?s_HW_DB_OAM:s_HW_OAM));
}
bool G2SIM_HasOBJ(u32 line,u8 isSub,int bgnum) {
    return s_androidObjIndex[isSub].count[bgnum>>10][line]!=0;
}
#endif
void G2SIM_DrawOBJ(''')
edit(p,'  for (int sprnum = 127; sprnum >= 0; sprnum--) {','''#ifdef SDK_BUILD_ANDROID
  const ADObjIndex &index=s_androidObjIndex[isSub];
  for(unsigned item=0;item<index.count[bgnum>>10][line];++item) {
    int sprnum=index.sprites[bgnum>>10][line][item];
#else
  for (int sprnum = 127; sprnum >= 0; sprnum--) {
#endif''')
edit(p,'    u32 sprline;','    u32 sprline = line;')
p=sim/'src/sim_main.cpp'
edit(p,'static void DrawEngine(BOOL isSub);','''#ifdef SDK_BUILD_ANDROID
extern void G2SIM_PrepareOBJ(u8);
extern bool G2SIM_HasOBJ(u32,u8,int);
#endif
static void DrawEngine(BOOL isSub);''')
edit(p,'u64 s_SIM_frameTime;','')
edit(p,'#ifdef SDK_BUILD_ANDROID\n#include "android_clock.inc"','u64 s_SIM_frameTime;\n#ifdef SDK_BUILD_ANDROID\n#include "android_clock.inc"')
edit(p,'  // Draw the Sprites','''#ifdef SDK_BUILD_ANDROID
  G2SIM_PrepareOBJ(isSub);
#endif
  // Draw the Sprites''')
edit(p,'      memset(OBJLine, 0, sizeof(OBJLine));','''#ifdef SDK_BUILD_ANDROID
      if(!G2SIM_HasOBJ(i,isSub,bgnum)) continue;
#endif
      memset(OBJLine, 0, sizeof(OBJLine));''')
# exit() runs process-global C++ destructors while Nitro/SDL workers still run.
# Android already isolates this runtime in :game; use process termination after
# flushing stdio, without racing global destruction against live worker threads.
edit(p,'      exit(0);\n    if (Event.type == SDL_KEYDOWN','''    {
      SDL_Log("Android game process: requested exit");
      fflush(NULL);
      _Exit(0);
    }
    if (Event.type == SDL_KEYDOWN''')
edit(p,'    // SIM_Net_Process();','''#ifdef SDK_BUILD_ANDROID
    uint64_t androidComposeStart=AndroidNowNs();
#endif
    // SIM_Net_Process();''')
edit(p,'    AndroidPaceVBlank();\n    AndroidPresent(window);','''    s_androidComposeNs+=AndroidNowNs()-androidComposeStart;
    ++s_androidComposes;
    AndroidPaceVBlank();
    AndroidPresent(window);''')
edit(p,'    s_SIM_frameTime = frameNs;','''#ifndef SDK_BUILD_ANDROID
    s_SIM_frameTime = frameNs;
#endif''')
p=sim/'src/g3_draw.cpp'
edit(p,'#include <simulator/sim_crc32.h>','''#include <simulator/sim_crc32.h>
#ifdef SDK_BUILD_ANDROID
#include "android_crc_memo.h"
static ADCrcMemo s_androidTextureCrc, s_androidPaletteCrc;
static u32 AndroidTextureCRC(ADCrcMemo &memo,const u8 *data,size_t size) {
    return memo.get(data,size,[](const uint8_t *p,size_t n){return SIM_crc32buf((u8*)p,n);});
}
#endif''')
edit(p,'u32 paletteCRC = SIM_crc32buf(vramPltt, 512);','''u32 paletteCRC;
#ifdef SDK_BUILD_ANDROID
        paletteCRC=AndroidTextureCRC(s_androidPaletteCrc,vramPltt,512);
#else
        paletteCRC=SIM_crc32buf(vramPltt,512);
#endif''')
edit(p,'u32 textureCRC = SIM_crc32buf(vramTex, vramTexBufSize);','''u32 textureCRC;
#ifdef SDK_BUILD_ANDROID
        textureCRC=AndroidTextureCRC(s_androidTextureCrc,vramTex,vramTexBufSize);
#else
        textureCRC=SIM_crc32buf(vramTex,vramTexBufSize);
#endif''')
print('Android: scanline sprite lists, byte-validated texture checksums, safe process exit, performance log')
