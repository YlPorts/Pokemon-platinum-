#!/usr/bin/env python3
"""Apply after repair_single_screen.py; preserve display quality and DS timing."""
from pathlib import Path
import shutil,sys
root=Path(sys.argv[1]);lib=root/'subprojects/libntr';base=Path(__file__).parent
inc=lib/'libraries/sim/include'
for name in ('android_vertex_stream.inc','android_visibility.h'):
    shutil.copyfile(base/'performance'/name,inc/name)
def edit(p,old,new,count=1):
    s=p.read_text();assert s.count(old)==count,(p,old[:70],s.count(old));p.write_text(s.replace(old,new))
quad=lib/'libraries/sim/src/sim_screenquads.c'
edit(quad,'#include "android_layout.h"','''#include "android_layout.h"
#include "android_visibility.h"
static int s_androidSingle=0, s_androidBottom=0;
BOOL sim_AndroidEngineVisible(BOOL isSub,BOOL mainOnTop) {
    return ad_engine_visible(s_androidSingle,s_androidBottom,mainOnTop,isSub);
}''')
edit(quad,'    SIM_GUI_AndroidSetLayout(&a);','''    s_androidSingle=a.single;
    s_androidBottom=a.touch.w>0;
    SIM_GUI_AndroidSetLayout(&a);''')
h=inc/'screenquads.h'
edit(h,'G3SIM_Vertex_t * sim_GetScreenQuadArray','BOOL sim_AndroidEngineVisible(BOOL isSub,BOOL mainOnTop);\n\nG3SIM_Vertex_t * sim_GetScreenQuadArray')
main=lib/'libraries/sim/src/sim_main.cpp'
edit(main,'static void DrawEngine(BOOL isSub) {','''static void DrawEngine(BOOL isSub) {
#ifdef SDK_BUILD_ANDROID
  if(!sim_AndroidEngineVisible(isSub,(s_reg_GX_POWCNT & 0x8000)!=0)) return;
#endif''')
# Reuse the screen-quad VBO unless geometry actually changes (rotation/layout).
edit(main,'''  glBufferData(GL_ARRAY_BUFFER, sizeof(G3SIM_Vertex_t) * arrayCount, quadArray,
               GL_STATIC_DRAW);''','''#ifdef SDK_BUILD_ANDROID
  static G3SIM_Vertex_t previousQuads[12];
  static int previousCount=-1;
  if(previousCount!=arrayCount || memcmp(previousQuads,quadArray,sizeof(*quadArray)*arrayCount)) {
    glBufferData(GL_ARRAY_BUFFER,sizeof(*quadArray)*arrayCount,quadArray,GL_DYNAMIC_DRAW);
    memcpy(previousQuads,quadArray,sizeof(*quadArray)*arrayCount);
    previousCount=arrayCount;
  }
#else
  glBufferData(GL_ARRAY_BUFFER, sizeof(G3SIM_Vertex_t) * arrayCount, quadArray,
               GL_STATIC_DRAW);
#endif''')
g3=lib/'libraries/sim/src/g3_draw.cpp'
edit(g3,'static GLuint s_G3DrawVertexBuffer;','''static GLuint s_G3DrawVertexBuffer;
#ifdef SDK_BUILD_ANDROID
#include "android_vertex_stream.inc"
#endif''')
for count,data in [('s_G3DrawCurVertIdx','s_G3DrawVerts'),('item->vertsCount','item->verts')]:
    comma=' ' if count.startswith('item') else ''
    old=f'''\t\tglBindVertexArray(s_G3DrawVertexArray);
\t\tglBindBuffer(GL_ARRAY_BUFFER, s_G3DrawVertexBuffer);
\t\tglBufferSubData(GL_ARRAY_BUFFER, 0, sizeof(G3SIM_Vertex_t) * {count}, {data});
\t\tglDrawArrays(GL_TRIANGLES,0,{comma}{count});'''
    edit(g3,old,f'''#ifdef SDK_BUILD_ANDROID
        AndroidDrawVertices({data},{count});
#else
{old}
#endif''')
# Eight bytes per CRC iteration; same polynomial, initial value and final XOR.
# Static tables avoid runtime initialization/races and preserve the exact keys.
crc=lib/'libraries/sim/src/sim_crc32.c';s=crc.read_text()
(root/'tools/android/reference_crc32.c').write_text(s)
tables=[]
row=[]
for n in range(256):
    c=n
    for k in range(8): c=(c>>1)^(0xedb88320 if c&1 else 0)
    row.append(c)
tables.append(row)
for n in range(7): tables.append([(x>>8)^tables[0][x&255] for x in tables[-1]])
table='static const u32 android_crc[8][256] = {\n'+',\n'.join('{\n'+',\n'.join(','.join(f'0x{x:08x}u' for x in row[i:i+8]) for i in range(0,256,8))+'\n}' for row in tables)+'\n};\n'
func='''u32 SIM_crc32buf(u8 *buf, size_t len)
{
    u32 crc=0xffffffffu;
    while(len>=8) {
        u32 a=crc ^ ((u32)buf[0]|((u32)buf[1]<<8)|((u32)buf[2]<<16)|((u32)buf[3]<<24));
        u32 b=(u32)buf[4]|((u32)buf[5]<<8)|((u32)buf[6]<<16)|((u32)buf[7]<<24);
        crc=android_crc[7][a&255]^android_crc[6][(a>>8)&255]^android_crc[5][(a>>16)&255]^android_crc[4][a>>24]
           ^android_crc[3][b&255]^android_crc[2][(b>>8)&255]^android_crc[1][(b>>16)&255]^android_crc[0][b>>24];
        buf+=8;len-=8;
    }
    while(len--) crc=UPDC32(*buf++,crc);
    return ~crc;
}
'''
a=s.index('u32 SIM_crc32buf(');s=s[:a]+'#ifdef SDK_BUILD_ANDROID\n'+table+func+'#else\n'+s[a:]+'\n#endif\n';crc.write_text(s)
# Port the non-destructive localized resource fallback from the supplied PC ZIP.
# Native USA IDs/ROM validation remain unchanged: this is not full multilingual support.
fs=lib/'libraries/fs/src/fs_file.c'
old='''\tif (p_file->pcFilePtr == NULL) {
\t\tp_file->pcFilePtr = fopen(path, "rb");
\t}'''
edit(fs,old,old+'''
#ifdef SDK_BUILD_ANDROID
    if(p_file->pcFilePtr==NULL && strncmp(path,"resource/eng/",13)==0) {
        char localized[512];
        int length=snprintf(localized,sizeof(localized),"resource/spa/%s",path+13);
        if(length>0 && (size_t)length<sizeof(localized)) p_file->pcFilePtr=fopen(localized,"rb");
    }
    if(p_file->pcFilePtr==NULL && strcmp(path,"graphic/box.narc")==0)
        p_file->pcFilePtr=fopen("resource/spa/box/box.narc","rb");
    if(p_file->pcFilePtr==NULL && strcmp(path,"graphic/pl_bag_gra.narc")==0)
        p_file->pcFilePtr=fopen("resource/spa/bag/pl_bag_gra.narc","rb");
#endif''')
print('Android rendering work reduced; PC localized resource lookup adapted')
