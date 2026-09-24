#!/usr/bin/env python3
"""Android synchronous geometry submission, after repair_workload.py."""
from pathlib import Path
import re,shutil,sys
root=Path(sys.argv[1]);base=Path(__file__).parent;ntr=root/'subprojects/libntr';sim=ntr/'libraries/sim'
def edit(p,old,new,count=1):
 s=p.read_text();assert s.count(old)==count,(p,old[:70],s.count(old));p.write_text(s.replace(old,new))
total=0
for rel in ('include/nitro/gx/g3imm.h','libraries/gx/src/g3imm.c','libraries/gx/src/g3_util.c'):
 p=ntr/rel;s=p.read_text()
 # Immediate commands are executed synchronously, including recursive Direct/Vtx
 # decoding. Their stack lifetime covers every consumer of the message.
 pattern=r'draw_msg_t \* msg;\s*msg = (?:\(draw_msg_t\*\))?malloc\( sizeof\( draw_msg_t \) \);'
 s,n=re.subn(pattern,lambda m: '#ifdef SDK_BUILD_ANDROID\n    draw_msg_t localMessage;\n    draw_msg_t *msg=&localMessage;\n#else\n    '+m[0]+'\n#endif',s)
 assert n>0,(p,n)
 assert s.count('free( msg );')==n,(p,n,s.count('free( msg );'))
 s=s.replace('free( msg );','#ifndef SDK_BUILD_ANDROID\n    free( msg );\n#endif')
 p.write_text(s);total+=n
p=ntr/'include/simulator/drawmsg.h'
edit(p,'void SIM_HandleG3Command(draw_msg_t * msg);','''void SIM_HandleG3Command(draw_msg_t * msg);
#ifdef SDK_BUILD_ANDROID
void SIM_HandleG3CommandList(const void *data,u32 size);
#endif''')
p=ntr/'libraries/mi/src/mi_dma_gxcommand.c'
s=p.read_text()
for name,params,async_ in [('MI_SendGXCommand','u32 dmaNo, const void * src, u32 commandLength',False),('MI_SendGXCommandAsync','u32 dmaNo, const void * src, u32 commandLength, MIDmaCallback callback, void * arg',True),('MI_SendGXCommandFast','u32 dmaNo, const void * src, u32 commandLength',False),('MI_SendGXCommandAsyncFast','u32 dmaNo, const void * src, u32 commandLength, MIDmaCallback callback, void * arg',True)]:
 start='void '+name+' ('+params+')\n{';assert s.count(start)==1
 body='\n#ifdef SDK_BUILD_ANDROID\n    SIM_HandleG3CommandList(src,commandLength);\n'
 if async_:body+='    MIi_CallCallback(callback,arg);\n'
 body+='    return;\n#endif\n'
 s=s.replace(start,start+body)
p.write_text(s)
shutil.copyfile(base/'performance/android_commands.inc',sim/'include/android_commands.inc')
p=sim/'src/sim_main.cpp'
edit(p,'static xyz_s_t prevXYZ;','''#ifdef SDK_BUILD_ANDROID
#define AD_COMMAND_PROFILE
#include "android_commands.inc"
#endif
static xyz_s_t prevXYZ;''')
# Measure actual application and GX submission time. These overlap and are
# deliberately named separately, not summed as independent frame costs.
p=root/'src/main.c'
edit(p,'            RunApplication();','''#ifdef SDK_BUILD_ANDROID
            extern void SIM_AndroidApplicationBegin(void);
            extern void SIM_AndroidApplicationEnd(void);
            SIM_AndroidApplicationBegin();
#endif
            RunApplication();
#ifdef SDK_BUILD_ANDROID
            SIM_AndroidApplicationEnd();
#endif''')
p=sim/'src/sim_main.cpp'
edit(p,'static xyz_s_t prevXYZ;','''#ifdef SDK_BUILD_ANDROID
static uint64_t s_androidAppStart=0,s_androidAppNs=0;
static unsigned s_androidApps=0;
extern uint64_t s_androidG3FlushNs;
extern unsigned s_androidG3FlushCount;
extern "C" void SIM_AndroidApplicationBegin(void) {s_androidAppStart=AndroidNowNs();}
extern "C" void SIM_AndroidApplicationEnd(void) {
    s_androidAppNs+=AndroidNowNs()-s_androidAppStart;++s_androidApps;
}
static uint64_t s_androidProfileStart=0;
static void AndroidApplicationReport() {
    uint64_t now=AndroidNowNs();
    if(!s_androidProfileStart) s_androidProfileStart=now;
    if(now-s_androidProfileStart<2000000000ULL) return;
    char line[256];
    snprintf(line,sizeof(line),"Android app: updates=%u app=%.2fms gx_lists=%.2fms gx_flush=%.2fms flushes=%u lists_cached=%u lists_decoded=%u",s_androidApps,
        s_androidApps?s_androidAppNs/1e6/s_androidApps:0.0,
        s_androidApps?s_androidListNs/1e6/s_androidApps:0.0,
        s_androidApps?s_androidG3FlushNs/1e6/s_androidApps:0.0,
        s_androidG3FlushCount,s_androidListHits,s_androidListMisses);
    AndroidTimingWrite(line);
    s_androidAppNs=0;s_androidApps=0;s_androidListHits=s_androidListMisses=0;s_androidProfileStart=now;
    s_androidListNs=s_androidG3FlushNs=0;s_androidG3FlushCount=0;
}
#endif
static xyz_s_t prevXYZ;''')
edit(p,'    AndroidPresent(window);','    AndroidPresent(window);\n    AndroidApplicationReport();')
p=sim/'src/g3_draw.cpp'
edit(p,'void G3SIM_FlushArray()','''#ifdef SDK_BUILD_ANDROID
#include <time.h>
uint64_t s_androidG3FlushNs=0;
unsigned s_androidG3FlushCount=0;
static uint64_t AndroidGXNow() {struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint64_t)t.tv_sec*1000000000ULL+t.tv_nsec;}
struct AndroidGXTimer {uint64_t begin=AndroidGXNow();~AndroidGXTimer(){s_androidG3FlushNs+=AndroidGXNow()-begin;++s_androidG3FlushCount;}};
#endif
void G3SIM_FlushArray()''')
edit(p,'\tTracyCZone(FlushArrayZone, 1);','\tTracyCZone(FlushArrayZone, 1);')
edit(p,'\tu8 * texBuf = nullptr;','''#ifdef SDK_BUILD_ANDROID
    AndroidGXTimer androidGXTimer;
#endif
\tu8 * texBuf = nullptr;''')
print('Android: eliminated',total,'immediate GX heap allocation sites; borrowed DMA lists and exact decoded cache')
