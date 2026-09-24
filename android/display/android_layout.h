#ifndef PLATINUM_ANDROID_LAYOUT_H
#define PLATINUM_ANDROID_LAYOUT_H
/* Logical window pixels, top-left origin. Shared by drawing and hit testing. */
#include <math.h>
typedef struct { float x, y, w, h; } ADRect;
typedef struct {
    ADRect top, touch, keys[15];
    float width, height, unit, aspect;
    int landscape, expanded;
} ADLayout;
enum { AD_A, AD_B, AD_X, AD_Y, AD_L, AD_R, AD_START, AD_SELECT,
       AD_UP, AD_DOWN, AD_LEFT, AD_RIGHT, AD_MENU, AD_SWAP, AD_TOUCH };
static inline float ad_min(float a, float b) { return a < b ? a : b; }
static inline ADRect ad_rect(float x,float y,float w,float h) { ADRect r={x,y,w,h}; return r; }
static inline int ad_inside(ADRect r,float x,float y) {
    return r.w>0 && r.h>0 && x>=r.x && y>=r.y && x<r.x+r.w && y<r.y+r.h;
}
static inline ADRect ad_fit(ADRect box,float aspect) {
    float w=ad_min(box.w,box.h*aspect), h=w/aspect;
    return ad_rect(box.x+(box.w-w)/2,box.y+(box.h-h)/2,w,h);
}
static inline ADRect ad_circle(float x,float y,float d) { return ad_rect(x-d/2,y-d/2,d,d); }
static inline ADLayout ad_layout(float w,float h,int mode,int swapped,int field,int showTouch,
                                  int aspectMode,int sizePercent) {
    ADLayout a={0};
    if(w<1 || h<1) return a;
    a.width=w; a.height=h; a.landscape=w>h;
    float unit=ad_min(w,h)*(a.landscape?.135f:.145f)*(float)sizePercent/100;
    a.unit=unit;
    float margin=ad_min(w,h)*.025f;
    float cy=h-unit*1.85f, lx=unit*1.55f, rx=w-lx;
    float step=unit*.83f, d=unit*.82f;
    a.keys[AD_X]=ad_circle(rx,cy-step,d);
    a.keys[AD_Y]=ad_circle(rx-step,cy,d);
    a.keys[AD_A]=ad_circle(rx+step,cy,d);
    a.keys[AD_B]=ad_circle(rx,cy+step,d);
    float cell=unit*.65f;
    a.keys[AD_UP]=ad_rect(lx-cell/2,cy-cell*1.5f,cell,cell);
    a.keys[AD_DOWN]=ad_rect(lx-cell/2,cy+cell*.5f,cell,cell);
    a.keys[AD_LEFT]=ad_rect(lx-cell*1.5f,cy-cell/2,cell,cell);
    a.keys[AD_RIGHT]=ad_rect(lx+cell*.5f,cy-cell/2,cell,cell);
    a.keys[AD_L]=ad_rect(margin,cy-unit*1.9f,unit*1.5f,unit*.57f);
    a.keys[AD_R]=ad_rect(w-margin-unit*1.5f,cy-unit*1.9f,unit*1.5f,unit*.57f);
    a.keys[AD_SELECT]=ad_rect(w*.5f-unit*1.32f,h-unit*.53f,unit*1.18f,unit*.38f);
    a.keys[AD_START]=ad_rect(w*.5f+unit*.14f,h-unit*.53f,unit*1.18f,unit*.38f);
    float bar=ad_min(w,h)*.068f;
    a.keys[AD_MENU]=ad_rect(margin,margin,bar*1.6f,bar);
    a.keys[AD_SWAP]=ad_rect(w/2-bar*.8f,margin,bar*1.6f,bar);
    a.keys[AD_TOUCH]=ad_rect(w-margin-bar*1.6f,margin,bar*1.6f,bar);
    float y=margin+bar+margin, bottom=a.landscape?h-margin:cy-unit*2.07f;
    ADRect area=ad_rect(margin,y,w-2*margin,bottom-y);
    float gap=margin*.65f;
    a.expanded=field && !swapped && (mode==1 || mode==4);
    float aspect=4.0f/3.0f;
    if(a.expanded) {
        aspect=aspectMode==1?16.0f/9.0f:aspectMode==2?21.0f/9.0f:
            (a.landscape?fmaxf(4.0f/3.0f,fminf(8.0f/3.0f,area.w/area.h)):16.0f/9.0f);
    }
    if(a.expanded && a.landscape) {
        a.top=ad_fit(area,aspect);
        if(showTouch) {
            float tw=ad_min(w*.24f,(cy-unit*2.1f-y)*4/3);
            tw=fmaxf(tw,unit*1.5f);
            a.touch=ad_rect(w-margin-tw,y,tw,tw*.75f);
        }
    } else {
        int horizontal=(mode==2 || mode==3 || ((mode==1 || mode==4) && a.landscape));
        if(horizontal) {
            /* Leave thumb rails clear in landscape dual-screen scenes. */
            if(a.landscape) { area.x=unit*2.95f; area.w=w-area.x*2; }
            float ratio=mode==3?2.0f:1.0f;
            float sh=ad_min(area.h,(area.w-gap)/((ratio+1)*aspect));
            float pw=sh*aspect, sw=pw/ratio, ph=sh, sth=sh/ratio;
            if(mode==3) { pw=ad_min(area.w*.66f,area.h*aspect); ph=pw/aspect; sw=pw/2; sth=ph/2; }
            float left=area.x+(area.w-pw-sw-gap)/2;
            a.top=ad_rect(left,area.y+(area.h-ph)/2,pw,ph);
            a.touch=ad_rect(left+pw+gap,area.y+(area.h-sth)/2,sw,sth);
        } else {
            float sw=ad_min(area.w,(area.h-gap)/(1/aspect+.75f));
            float th=sw/aspect, bh=sw*.75f;
            float left=area.x+(area.w-sw)/2, top=area.y+(area.h-th-bh-gap)/2;
            a.top=ad_rect(left,top,sw,th);
            a.touch=ad_rect(left,top+th+gap,sw,bh);
        }
        if(swapped) { ADRect temp=a.top; a.top=a.touch; a.touch=temp; }
    }
    a.aspect=a.top.h>0?a.top.w/a.top.h:4.0f/3.0f;
    return a;
}
static inline unsigned short ad_pad_hit(const ADLayout *a,float x,float y) {
    ADRect up=a->keys[AD_UP];
    float cell=up.w, cx=up.x+cell/2, cy=up.y+cell*1.5f;
    float dx=(x-cx)/cell, dy=(y-cy)/cell;
    if(fabsf(dx)<1.65f && fabsf(dy)<1.65f) {
        unsigned short mask=0;
        if(dy<-.32f) mask|=1<<AD_UP;
        if(dy>.32f) mask|=1<<AD_DOWN;
        if(dx<-.32f) mask|=1<<AD_LEFT;
        if(dx>.32f) mask|=1<<AD_RIGHT;
        return mask;
    }
    for(int i=0;i<8;i++) {
        ADRect r=a->keys[i];
        if(i<4) { float dx=(x-r.x-r.w/2)/(r.w*.6f),dy=(y-r.y-r.h/2)/(r.h*.6f); if(dx*dx+dy*dy<=1) return 1<<i; }
        else if(ad_inside(r,x,y)) return 1<<i;
    }
    return 0;
}
static inline int ad_pad_region(const ADLayout *a,float x,float y) {
    ADRect up=a->keys[AD_UP]; float c=up.w;
    ADRect cross=ad_rect(up.x-c,up.y,c*3,c*3);
    return ad_inside(cross,x,y) || ad_pad_hit(a,x,y)!=0;
}
static inline int ad_stylus(const ADLayout *a,float x,float y,int *sx,int *sy) {
    if(!ad_inside(a->touch,x,y)) return 0;
    *sx=(int)((x-a->touch.x)*256/a->touch.w);
    *sy=(int)((y-a->touch.y)*192/a->touch.h);
    return 1;
}
#endif
