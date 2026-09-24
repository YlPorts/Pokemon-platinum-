#pragma once
#include <stdint.h>
#include <string.h>
// Per-frame scanline lists. Order remains 127..0, including window objects.
struct ADObjIndex {
    uint8_t sprites[4][192][128];
    uint16_t count[4][192];
    void build(const uint16_t *oam) {
        static const unsigned heights[16]={8,8,16,8,16,8,32,8,32,16,32,8,64,32,64,8};
        memset(count,0,sizeof(count));
        for(int n=127;n>=0;--n) {
            unsigned a=oam[n*4], b=oam[n*4+1];
            if((a&0x300)==0x200) continue; // disabled non-affine object
            unsigned height=heights[(a>>14)|((b&0xc000)>>12)];
            if((a&0x300)==0x300) height*=2;
            unsigned p=(oam[n*4+2]>>10)&3;
            for(unsigned y=0;y<height;++y) {
                unsigned line=((a&255)+y)&255;
                if(line<192) sprites[p][line][count[p][line]++]=(uint8_t)n;
            }
        }
    }
};
