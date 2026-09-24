#!/usr/bin/env python3
"""Applied once to the prepared runtime, after repair_display.py."""
from pathlib import Path
import re, sys, shutil
root=Path(sys.argv[1]); lib=root/'subprojects/libntr'
shutil.copyfile(Path(__file__).parent/'display/android_screen_policy.h', lib/'libraries/sim/include/android_screen_policy.h')
def edit(path,old,new,count=1):
    s=path.read_text(); assert s.count(old)==count,(path,old[:90],s.count(old)); path.write_text(s.replace(old,new))
hook='''
#ifdef SDK_BUILD_ANDROID
extern void SIM_AndroidScreenHint(int screen);
extern void SIM_AndroidResetScreen(void);
#define ANDROID_SCREEN(screen) SIM_AndroidScreenHint(screen)
#define ANDROID_SCREEN_RESET() SIM_AndroidResetScreen()
#else
#define ANDROID_SCREEN(screen) ((void)0)
#define ANDROID_SCREEN_RESET() ((void)0)
#endif
'''
def game(path):
    p=root/path; p.write_text(hook+p.read_text()); return p
main=lib/'libraries/sim/src/sim_main.cpp'
s=main.read_text(); s='#include <atomic>\n#include "android_screen_policy.h"\n'+s
old='extern "C" void SIM_AndroidToggleTouchScreen(void) { s_SIM_showTouchOverlay=!s_SIM_showTouchOverlay; }'
assert old in s
s=s.replace(old,'''/* Game thread publishes policy; render/input thread owns manual selection.
   -1 follows the physical display carrying the main DS engine. */
static std::atomic<int> s_androidScreenHint{-1};
static std::atomic<unsigned> s_androidScreenGeneration{0};
static ADScreenPolicy s_androidPolicy={0xffffffffu,-1};
extern "C" void SIM_AndroidResetScreen(void) { s_androidScreenHint.store(-1); s_androidScreenGeneration.fetch_add(1); }
extern "C" void SIM_AndroidScreenHint(int screen) { s_androidScreenHint.store(screen); }
static int AndroidAutomaticScreen() {
  int hint=s_androidScreenHint.load();
  return hint<0 ? ((s_reg_GX_POWCNT & 0x8000)?0:1) : hint;
}
extern "C" int SIM_AndroidSelectedScreen(void) {
  int screen=AndroidAutomaticScreen();
  int selected=ad_selected_screen(&s_androidPolicy,screen,s_androidScreenGeneration.load());
  static int logged=-1;
  if(selected!=logged) { SDL_Log("Android screen: %s",selected?"touch":"top"); logged=selected; }
  return selected;
}
extern "C" void SIM_AndroidToggleTouchScreen(void) {
  s_androidPolicy.manual=!SIM_AndroidSelectedScreen();
}
extern "C" void SIM_AndroidResumeAutomatic(void) { s_androidPolicy.manual=-1; }
''')
s=s.replace('!s_SIM_config.swapScreens && s_SIM_config.widescreenMode!=2;', 's_SIM_config.widescreenMode!=2;')
main.write_text(s)
quad=lib/'libraries/sim/src/sim_screenquads.c'
edit(quad,'extern void SIM_AndroidSetAspect(float aspect);','extern void SIM_AndroidSetAspect(float aspect);\nextern int SIM_AndroidSelectedScreen(void);')
edit(quad,'    ADLayout a=ad_layout(viewWidth,viewHeight,layout,isSwapped,isOverworld,showTouchOverlay,','    BOOL single=(layout==1 || layout==4);\n    BOOL bottom=single?SIM_AndroidSelectedScreen():isSwapped;\n    ADLayout a=ad_layout(viewWidth,viewHeight,layout,bottom,isOverworld,showTouchOverlay,')
edit(quad,'ADLayout next=ad_layout(viewWidth,viewHeight,layout,isSwapped,TRUE,showTouchOverlay,','ADLayout next=ad_layout(viewWidth,viewHeight,layout,FALSE,TRUE,showTouchOverlay,')
# Lifecycle reset prevents a child menu's selection leaking into its caller.
p=game('src/overlay_manager.c')
edit(p,'    case OVERLAY_EXEC_LOAD:\n','    case OVERLAY_EXEC_LOAD:\n        ANDROID_SCREEN_RESET();\n')
edit(p,'        if (appMan->template.exit(appMan, &appMan->procState) == TRUE) {','        if (appMan->template.exit(appMan, &appMan->procState) == TRUE) {\n            ANDROID_SCREEN_RESET();')
# Rowan explicitly requests the touch panel for the ball and Yes/No tutorial.
p=game('src/applications/rowan_intro/rowan_intro_app.c')
edit(p,'static BOOL RowanIntro_Run(RowanIntro *manager)\n{','''static BOOL RowanIntro_Run(RowanIntro *manager)
{
    int touch = manager->state==RI_STATE_CONTROL_INFO_SHOW_YESNO ||
        manager->state==RI_STATE_CONTROL_INFO_WAIT_INPUT ||
        manager->state==RI_STATE_CONTROL_INFO_PROCESS_YESNO ||
        manager->state==RI_STATE_PKBL_WAIT_INPUT ||
        manager->state==RI_STATE_PKBL_ANIM_PUSH_IN ||
        (manager->state>=RI_STATE_PKBL_ANIM_FLASH_0 &&
         manager->state<=RI_STATE_PKBL_ANIM_SPAWN_PKM_AND_FLASH_4);
    ANDROID_SCREEN(touch?1:0);''')
p=game('src/applications/naming_screen.c')
edit(p,'static BOOL NamingScreen_Main(ApplicationManager *appMan, int *state)\n{','static BOOL NamingScreen_Main(ApplicationManager *appMan, int *state)\n{\n    ANDROID_SCREEN(1);')
# The player's battle input tasks own the bottom screen until their input ends.
# Bag and party manage their own applications/main-engine display routing.
p=game('src/battle/battle_display.c');s=p.read_text()
for name in ('SetCommandSelection','ShowMoveSelectMenu','ShowTargetSelectMenu','ShowYesNoMenu'):
    marker=f'static void Task_Player{name}(SysTask *task, void *data)\n{{'
    start=s.index(marker);end=s.index('\nstatic ',start+len(marker));body=s[start:end]
    body=body.replace(marker,marker+'\n    ANDROID_SCREEN(1);',1)
    body=body.replace('SysTask_Done(task);','ANDROID_SCREEN(0);\n            SysTask_Done(task);')
    s=s[:start]+body+s[end:]
p.write_text(s)
# Avoid querying GL_CURRENT_PROGRAM and rebinding for every material uniform.
# Both draw entry points explicitly bind the 3D program once, so local bound-
# program uniforms are safe. Other users retain the preserving compatibility API.
p=lib/'libraries/sim/src/g3_draw.cpp';s=p.read_text()
marker='\t\tu8 * texBuf = nullptr;'
# FlushArray has returned already when there are no vertices.
marker='\tu8 * texBuf = nullptr;'; assert s.count(marker)==1
s=s.replace(marker,'#ifdef SDK_BUILD_ANDROID\n    glUseProgram(g3shaderProgramID);\n#endif\n'+marker)
# DrawItems already binds g3shaderProgramID before its loop.
s=s.replace('glProgramUniform1i(g3shaderProgramID,','G3_UNIFORM1I(').replace('glProgramUniform1fv(g3shaderProgramID,','G3_UNIFORM1FV(').replace('glProgramUniform4f(g3shaderProgramID,','G3_UNIFORM4F(')
s='''#ifdef SDK_BUILD_ANDROID
#define G3_UNIFORM1I(...) glUniform1i(__VA_ARGS__)
#define G3_UNIFORM1FV(...) glUniform1fv(__VA_ARGS__)
#define G3_UNIFORM4F(...) glUniform4f(__VA_ARGS__)
#else
#define G3_UNIFORM1I(...) glProgramUniform1i(g3shaderProgramID, __VA_ARGS__)
#define G3_UNIFORM1FV(...) glProgramUniform1fv(g3shaderProgramID, __VA_ARGS__)
#define G3_UNIFORM4F(...) glProgramUniform4f(g3shaderProgramID, __VA_ARGS__)
#endif
'''+s
p.write_text(s)
print('Single-screen game hooks and bound-program 3D uniforms applied')
