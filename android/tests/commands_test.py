#!/usr/bin/env python3
"""Differential command decoder tests using the real legacy decoder and types."""
from pathlib import Path
import sys,subprocess,tempfile
root=Path(sys.argv[1]);ntr=root/'subprojects/libntr';base=Path(__file__).resolve().parent.parent
s=(ntr/'libraries/sim/src/sim_main.cpp').read_text()
a=s.index('static draw_command_type_t DecodeG3Op(u32 op) {');b=s.index('#ifdef SDK_BUILD_ANDROID\n#define AD_COMMAND_PROFILE',a)
helpers=s[a:b]
a=s.index('    // Process a command List');b=s.index('    free(msg->data.ptr);',a)
legacy=s[a:b].replace('draw_msg_t tempMsg;','draw_msg_t tempMsg;').replace('tempMsg.type = DecodeG3Op','memset(&tempMsg,0,sizeof(tempMsg));\n          tempMsg.type = DecodeG3Op')
pre=r'''
#include <nitro.h>
#include <simulator/drawmsg.h>
#include <vector>
#include <cstring>
#include <cassert>
#include <cstdio>
#include <random>
#include <chrono>
struct G3SIM_CommandBlock_t {u8 ops[4];};
#define SIM_assert_always() abort()
static std::vector<draw_msg_t> output;
static bool capture=true;
extern "C" void SIM_HandleG3Command(draw_msg_t *m) {
 if(capture) output.push_back(*m);
 // Match the real interpreter's mutability contract: cache must own a copy.
 memset(m,0,sizeof(*m));
}
'''
main=r'''
static std::vector<u8> makeList(std::mt19937 &rng,unsigned blocks) {
 const u8 ops[]={0x00,0x10,0x11,0x12,0x13,0x14,0x15,0x16,0x17,0x18,0x19,0x1a,0x1b,0x1c,0x20,0x21,0x22,0x23,0x24,0x25,0x26,0x27,0x28,0x29,0x2a,0x2b,0x30,0x31,0x32,0x33,0x40,0x41,0x50,0x60,0x70};
 std::vector<u8> b;
 for(unsigned block=0;block<blocks;++block) {
  u8 codes[4];for(auto &c:codes){c=ops[rng()%(sizeof(ops))];b.push_back(c);}
  for(auto c:codes) {
   auto type=DecodeG3Op(c);unsigned bytes=GetNumParamsFromCommandType(type)*GetParamSizeFromCommandType(type);
   for(unsigned j=0;j<bytes;++j)b.push_back(rng());
  }
 }
 return b;
}
static void compare(std::vector<u8> &b) {
 output.clear();Baseline(b.data(),b.size());auto expected=output;
 output.clear();SIM_HandleG3CommandList(b.data(),b.size());
 assert(output.size()==expected.size());
 assert(memcmp(output.data(),expected.data(),output.size()*sizeof(draw_msg_t))==0);
}
int main() {
 std::mt19937 rng(360);
 for(unsigned i=0;i<250;++i) {
  auto b=makeList(rng,1+rng()%200);compare(b);compare(b);compare(b);
  // Modify a payload in place, preserving the opcodes and buffer identity.
  if(b.size()>4 && GetNumParamsFromCommandType(DecodeG3Op(b[0]))) {b[4]^=0x80;compare(b);}
 }
 // Capacity fallback, eviction, reused addresses, and malformed/truncated data.
 auto big=makeList(rng,2000);compare(big);compare(big);
 for(unsigned i=0;i<100;++i){auto b=makeList(rng,10);compare(b);}
 unsigned emitted=0;u8 bad[]={0x16,0,0,0,1};
 assert(!AndroidDecodeCommands(bad,sizeof(bad),[&](draw_msg_t&){++emitted;return true;}));assert(emitted==0);
 auto b=makeList(rng,200);compare(b);capture=false;
 auto a=std::chrono::steady_clock::now();for(int i=0;i<4000;++i)Baseline(b.data(),b.size());auto c=std::chrono::steady_clock::now();
 for(int i=0;i<4000;++i)SIM_HandleG3CommandList(b.data(),b.size());auto d=std::chrono::steady_clock::now();
 printf("PASS: decoded commands identical for 250 mixed lists, replay mutation, edits, eviction and bounds; parse %.2fms replay %.2fms (host microbenchmark, not phone FPS)\n",std::chrono::duration<double,std::milli>(c-a).count(),std::chrono::duration<double,std::milli>(d-c).count());
}
'''
with tempfile.TemporaryDirectory() as tmp:
 p=Path(tmp)/'commands.cpp'
 p.write_text(pre+helpers+'\n#include "android_commands.inc"\nvoid Baseline(const void *p,u32 size){draw_msg_t message={};auto msg=&message;msg->data.ptr=(void*)p;msg->size=size;\n'+legacy+'}\n'+main)
 flags=['-O2','-w','-std=c++14','-DSDK_PORT','-DSDK_BUILD_ANDROID','-DSDK_ARM9','-DSDK_FINALROM','-DNNS_FINALROM','-DSDK_VERSION_MAJOR=4','-DSDK_TS','-DATTRIBUTE_ALIGN(x)=__attribute__((aligned(x)))','-I/tmp/platinum-display-tests/include','-I'+str(ntr/'include'),'-I'+str(base/'performance'),'-ffunction-sections','-fdata-sections','-Wl,--gc-sections']
 exe=Path(tmp)/'test';subprocess.run(['g++',*flags,str(p),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
