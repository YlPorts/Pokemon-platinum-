/* Android touch ownership is fixed at finger-down: pad fingers never become a stylus. */
#include "android_layout.h"
extern SIM_config_type s_SIM_config;
extern void SIM_AndroidToggleTouchScreen(void);
extern void SIM_AndroidResumeAutomatic(void);
static ADLayout s_androidLayout;
static unsigned short s_androidTouchButtons;
static struct { SDL_FingerID id; float x,y; unsigned short button; int role; bool active; } s_androidFingers[10];

void SIM_GUI_AndroidResetInput(void) {
    memset(s_androidFingers,0,sizeof(s_androidFingers));
    s_androidTouchButtons=0;
}
void SIM_GUI_AndroidSetLayout(const ADLayout *layout) {
    if(memcmp(&s_androidLayout.touch,&layout->touch,sizeof(ADRect)) ||
       s_androidLayout.width!=layout->width || s_androidLayout.height!=layout->height ||
       s_androidLayout.unit!=layout->unit) SIM_GUI_AndroidResetInput();
    s_androidLayout=*layout;
}
bool SIM_GUI_AndroidStylus(int *x,int *y) {
    if(SIM_GUI_State) return false;
    for(int i=0;i<10;i++) if(s_androidFingers[i].active && s_androidFingers[i].role==2)
        return ad_stylus(&s_androidLayout,s_androidFingers[i].x,s_androidFingers[i].y,x,y)!=0;
    return false;
}
static void SIM_GUI_AndroidProcessTouchEvent(SDL_Event *e) {
    if(e->type!=SDL_FINGERDOWN && e->type!=SDL_FINGERUP && e->type!=SDL_FINGERMOTION) return;
    float x=e->tfinger.x*s_androidLayout.width,y=e->tfinger.y*s_androidLayout.height;
    int slot=-1,freeSlot=-1;
    for(int i=0;i<10;i++) {
        if(s_androidFingers[i].active && s_androidFingers[i].id==e->tfinger.fingerId) slot=i;
        if(!s_androidFingers[i].active && freeSlot<0) freeSlot=i;
    }
    if(e->type==SDL_FINGERDOWN && slot<0) {
        if(ad_inside(s_androidLayout.keys[AD_MENU],x,y)) { SIM_GUI_Toggle(); SIM_GUI_AndroidResetInput(); return; }
        if(ad_inside(s_androidLayout.keys[AD_SWAP],x,y)) {
            if(s_androidLayout.single) { SIM_AndroidToggleTouchScreen(); SIM_GUI_AndroidResetInput(); return; }
            s_SIM_config.swapScreens=!s_SIM_config.swapScreens;
            SIM_Config_SaveConfigFile(&s_SIM_config); SIM_GUI_AndroidResetInput(); return;
        }
        if(ad_inside(s_androidLayout.keys[AD_TOUCH],x,y)) {
            if(s_androidLayout.single) SIM_AndroidResumeAutomatic();
            SIM_GUI_AndroidResetInput(); return;
        }
        slot=freeSlot;
        if(slot<0) return;
        s_androidFingers[slot].active=true; s_androidFingers[slot].id=e->tfinger.fingerId;
        s_androidFingers[slot].role=ad_pad_region(&s_androidLayout,x,y)?1:
            ad_inside(s_androidLayout.touch,x,y)?2:0;
    }
    if(slot<0) return;
    s_androidFingers[slot].x=x; s_androidFingers[slot].y=y;
    s_androidFingers[slot].button=s_androidFingers[slot].role==1?ad_pad_hit(&s_androidLayout,x,y):0;
    if(e->type==SDL_FINGERUP) { s_androidFingers[slot].active=false; s_androidFingers[slot].button=0; }
    s_androidTouchButtons=0;
    for(int i=0;i<10;i++) if(s_androidFingers[i].active) s_androidTouchButtons|=s_androidFingers[i].button;
}
static ImU32 ad_color(int r,int g,int b,int alpha) { return (ImU32)r|((ImU32)g<<8)|((ImU32)b<<16)|((ImU32)alpha<<24); }
static void ad_label(ImDrawList *draw,ADRect r,const char *text,int alpha) {
    ImVec2 sz; igCalcTextSize(&sz,text,NULL,false,-1);
    ImDrawList_AddText_Vec2(draw,(ImVec2){r.x+(r.w-sz.x)/2,r.y+(r.h-sz.y)/2},ad_color(245,248,252,alpha),text,NULL);
}
void SIM_GUI_AndroidTouchMain(void) {
    if(SIM_GUI_State) return;
    ImDrawList *draw=igGetForegroundDrawList_ViewportPtr(igGetMainViewport());
    float opacity=(float)s_SIM_config.androidControlOpacity/100;
    const char *labels[15]={"A","B","X","Y","L","R","START","SELECT","","","","","MENU","SWAP","AUTO"};
    for(int i=0;i<15;i++) {
        ADRect r=s_androidLayout.keys[i];
        bool pressed=i<12 && (s_androidTouchButtons&(1<<i));
        int alpha=(int)(255*(pressed?fminf(.8f,opacity+.3f):opacity));
        ImU32 fill=pressed?ad_color(120,165,215,alpha):ad_color(100,110,124,alpha);
        ImU32 edge=ad_color(225,232,241,(int)(255*opacity));
        ImVec2 lo={r.x,r.y},hi={r.x+r.w,r.y+r.h};
        if(i<4) {
            ImVec2 center={r.x+r.w/2,r.y+r.h/2};
            ImDrawList_AddCircleFilled(draw,center,r.w/2,fill,32);
            ImDrawList_AddCircle(draw,center,r.w/2,edge,32,1.0f);
        } else {
            ImDrawList_AddRectFilled(draw,lo,hi,fill,i>=8 && i<12?2:r.h*.35f,0);
            if(i<8 || i>=12) ImDrawList_AddRect(draw,lo,hi,edge,r.h*.35f,0,1.0f);
        }
        ad_label(draw,r,labels[i],(int)(255*fminf(1,opacity+.35f)));
    }
    /* One continuous DS cross; arrow marks do not look like extra letter buttons. */
    ADRect up=s_androidLayout.keys[AD_UP]; float c=up.w,cx=up.x+c/2,cy=up.y+c*1.5f;
    ImDrawList_AddRectFilled(draw,(ImVec2){cx-c/2,cy-c/2},(ImVec2){cx+c/2,cy+c/2},ad_color(100,110,124,(int)(255*opacity)),0,0);
    for(int i=8;i<12;i++) {
        ADRect r=s_androidLayout.keys[i]; float x=r.x+r.w/2,y=r.y+r.h/2,t=c*.18f;
        ImVec2 p,q,z;
        if(i==AD_UP || i==AD_DOWN) { float s=i==AD_UP?-1:1; p=(ImVec2){x,y+s*t}; q=(ImVec2){x-t,y-s*t}; z=(ImVec2){x+t,y-s*t}; }
        else { float s=i==AD_LEFT?-1:1; p=(ImVec2){x+s*t,y}; q=(ImVec2){x-s*t,y-t}; z=(ImVec2){x-s*t,y+t}; }
        ImDrawList_AddTriangleFilled(draw,p,q,z,ad_color(245,248,252,(int)(255*(opacity+.2f))));
    }
}
unsigned short SIM_GUI_AndroidGetInputMask(void) { return s_androidTouchButtons; }
