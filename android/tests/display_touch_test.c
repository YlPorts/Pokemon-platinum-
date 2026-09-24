#include <assert.h>
#include <nitro.h>
#include <simulator/sim.h>
#include <simulator/gui.h>
#include "android_layout.h"
static bool SIM_GUI_State;
SIM_config_type s_SIM_config;
static int saves,toggles;
void SIM_GUI_Toggle(void) { SIM_GUI_State=!SIM_GUI_State; }
void SIM_Config_SaveConfigFile(SIM_config_type *p) { saves++; }
void SIM_AndroidToggleTouchScreen(void) { toggles++; }
#include "android_controls.inc"
static void finger(int type,int id,float x,float y) {
 SDL_Event e={0}; e.type=type;e.tfinger.fingerId=id;e.tfinger.x=x/s_androidLayout.width;e.tfinger.y=y/s_androidLayout.height;
 SIM_GUI_AndroidProcessTouchEvent(&e);
}
int main(void) {
 ADLayout a=ad_layout(540,960,4,0,0,1,0,100); SIM_GUI_AndroidSetLayout(&a);
 ADRect b=a.keys[AD_B],r=a.keys[AD_R],t=a.touch; int x,y;
 finger(SDL_FINGERDOWN,1,b.x+b.w/2,b.y+b.h/2);
 assert(SIM_GUI_AndroidGetInputMask()==(1<<AD_B));
 finger(SDL_FINGERDOWN,2,t.x+t.w/2,t.y+t.h/2);
 assert(SIM_GUI_AndroidStylus(&x,&y) && abs(x-128)<=1 && abs(y-96)<=1);
 assert(SIM_GUI_AndroidGetInputMask()==(1<<AD_B));
 finger(SDL_FINGERUP,1,b.x,b.y);
 assert(SIM_GUI_AndroidGetInputMask()==0 && SIM_GUI_AndroidStylus(&x,&y));
 finger(SDL_FINGERMOTION,2,b.x+b.w/2,b.y+b.h/2);
 assert(!SIM_GUI_AndroidStylus(&x,&y) && SIM_GUI_AndroidGetInputMask()==0);
 finger(SDL_FINGERUP,2,b.x,b.y);
 finger(SDL_FINGERDOWN,3,r.x+r.w/2,r.y+r.h/2);
 assert(SIM_GUI_AndroidGetInputMask()==(1<<AD_R) && toggles==0);
 finger(SDL_FINGERMOTION,3,t.x+t.w/2,t.y+t.h/2);
 assert(!SIM_GUI_AndroidStylus(&x,&y));
 ADLayout landscape=ad_layout(960,540,4,0,0,1,0,100);SIM_GUI_AndroidSetLayout(&landscape);
 assert(!SIM_GUI_AndroidGetInputMask() && !SIM_GUI_AndroidStylus(&x,&y));
 a=landscape;ADRect k=a.keys[AD_SWAP];finger(SDL_FINGERDOWN,4,k.x+k.w/2,k.y+k.h/2);
 assert(s_SIM_config.swapScreens && saves==1 && !SIM_GUI_AndroidStylus(&x,&y));
 k=a.keys[AD_TOUCH];finger(SDL_FINGERDOWN,5,k.x+k.w/2,k.y+k.h/2);assert(toggles==1);
 puts("PASS: simultaneous pad/stylus, finger ownership, real R, rotation cancellation, toolbar");
}
