#!/usr/bin/env python3
from pathlib import Path
import sys, shutil
root=Path(sys.argv[1]); lib=root/'subprojects/libntr'; base=Path(__file__).parent

def edit(path,old,new,count=1):
    s=path.read_text(); assert s.count(old)==count,(path,str(old)[:80],s.count(old)); path.write_text(s.replace(old,new))
for name in ('android_layout.h','android_controls.inc','android_config.inc'):
    shutil.copyfile(base/'display'/name,lib/'libraries/sim/include'/name)
header=lib/'include/simulator/config/sim_config.h'
edit(header,'SIM_CONFIG_SCREEN_LAYOUT_LARGE         /*','SIM_CONFIG_SCREEN_LAYOUT_LARGE,\n    SIM_CONFIG_SCREEN_LAYOUT_ADAPTIVE      /*')
edit(header,'    u8 macAddr[6];','    int androidWideAspect; /* 0 display, 1 16:9, 2 21:9 */\n    int androidControlSize; /* percent */\n    int androidControlOpacity; /* percent */\n    u8 macAddr[6];')
config=lib/'libraries/sim/src/config/sim_config.c'
edit(config,'    // General section','''    if(MATCH("General", "AndroidWideAspect")) config->androidWideAspect = atoi(value);
    if(MATCH("General", "AndroidControlSize")) config->androidControlSize = atoi(value);
    if(MATCH("General", "AndroidControlOpacity")) config->androidControlOpacity = atoi(value);
    // General section''')
edit(config,'    aConfig->widescreenMode = 0;','''    aConfig->widescreenMode = 0;
    aConfig->androidWideAspect = 0;
    aConfig->androidControlSize = 100;
    aConfig->androidControlOpacity = 35;''')
edit(config,'    return (ini_parse(SIM_CONFIG_FILE_PATH, IniHandler, aConfig) >= 0);','''    BOOL loaded = ini_parse(SIM_CONFIG_FILE_PATH, IniHandler, aConfig) >= 0;
    if(aConfig->androidControlSize < 85 || aConfig->androidControlSize > 115) aConfig->androidControlSize=100;
    if(aConfig->androidControlOpacity < 15 || aConfig->androidControlOpacity > 75) aConfig->androidControlOpacity=35;
    if(aConfig->androidWideAspect < 0 || aConfig->androidWideAspect > 2) aConfig->androidWideAspect=0;
    return loaded;''')
edit(config,'        case SIM_CONFIG_SCREEN_LAYOUT_LARGE:\n            ret = "large";', '        case SIM_CONFIG_SCREEN_LAYOUT_ADAPTIVE:\n            ret = "adaptive";\n            break;\n        case SIM_CONFIG_SCREEN_LAYOUT_LARGE:\n            ret = "large";')
edit(config,'    if(strcmp(str, "vertical") == 0) {','    if(strcmp(str, "adaptive") == 0) {\n        ret = SIM_CONFIG_SCREEN_LAYOUT_ADAPTIVE;\n    } else if(strcmp(str, "vertical") == 0) {')
edit(config,'    fprintf(configFile, "[General]\\n");','''    fprintf(configFile, "[General]\\n");
    fprintf(configFile, "AndroidWideAspect=%d\\nAndroidControlSize=%d\\nAndroidControlOpacity=%d\\n",
            aConfig->androidWideAspect,aConfig->androidControlSize,aConfig->androidControlOpacity);''')
gui=lib/'libraries/sim/src/gui/gui.c'; s=gui.read_text()
a=s.index('#ifdef SDK_BUILD_ANDROID\nenum {'); b=s.index('\nvoid SIM_GUI_ProcessEvent',a)
s=s[:a]+'#ifdef SDK_BUILD_ANDROID\n#include "android_controls.inc"\n#endif\n'+s[b:]
a=s.index('    if (!SIM_GUI_State && aEvent->type == SDL_FINGERDOWN'); b=s.index('    if (SIM_GUI_State) {\n        ImGui_ImplSDL2_ProcessEvent',a)
s=s[:a]+'''    if (aEvent->type == SDL_APP_WILLENTERBACKGROUND ||
        (aEvent->type == SDL_WINDOWEVENT &&
         (aEvent->window.event == SDL_WINDOWEVENT_FOCUS_LOST || aEvent->window.event == SDL_WINDOWEVENT_SIZE_CHANGED)))
        SIM_GUI_AndroidResetInput();
    if (!SIM_GUI_State) SIM_GUI_AndroidProcessTouchEvent(aEvent);
    else SIM_GUI_AndroidResetInput();
'''+s[b:]
a=s.index('#ifdef SDK_BUILD_ANDROID\nvoid SIM_GUI_AndroidTouchMain'); b=s.index('\nvoid SIM_GUI_Render',a)
s=s[:a]+s[b:];gui.write_text(s)
guih=lib/'include/simulator/gui.h'
edit(guih,'void SIM_GUI_AndroidTouchMain(void);','void SIM_GUI_AndroidTouchMain(void);\nvoid SIM_GUI_AndroidResetInput(void);\nbool SIM_GUI_AndroidStylus(int *x,int *y);')
quad=lib/'libraries/sim/src/sim_screenquads.c'
edit(quad,'#include "screenquads.h"','#include "screenquads.h"\n#ifdef SDK_BUILD_ANDROID\n#include "android_layout.h"\n#include <simulator/gui.h>\nextern SIM_config_type s_SIM_config;\nextern void SIM_GUI_AndroidSetLayout(const ADLayout *layout);\nextern void SIM_AndroidSetAspect(float aspect);\n#endif')
edit(quad,'    if (layout != SIM_CONFIG_SCREEN_LAYOUT_WIDESCREEN || viewWidth <= 0 || viewHeight <= 0) {','''#ifdef SDK_BUILD_ANDROID
    ADLayout a=ad_layout(viewWidth,viewHeight,layout,isSwapped,isOverworld,showTouchOverlay,
                         s_SIM_config.androidWideAspect,s_SIM_config.androidControlSize);
    SIM_GUI_AndroidSetLayout(&a);
    /* Keep the desired wide aspect ready even in a dual-screen menu so the
       field camera has the correct projection on its first frame. */
    ADLayout next=ad_layout(viewWidth,viewHeight,layout,isSwapped,TRUE,showTouchOverlay,
                            s_SIM_config.androidWideAspect,s_SIM_config.androidControlSize);
    SIM_AndroidSetAspect(next.aspect);
    ADRect t=a.top, b=a.touch;
    SetQuad(&s_WidescreenAdaptiveQuad[0],t.x/viewWidth,t.y/viewHeight,(t.x+t.w)/viewWidth,(t.y+t.h)/viewHeight,.5f,1);
    SetQuad(&s_WidescreenAdaptiveQuad[6],b.x/viewWidth,b.y/viewHeight,(b.x+b.w)/viewWidth,(b.y+b.h)/viewHeight,0,.5f);
    s_WidescreenTouchBounds[0]=b.x/viewWidth; s_WidescreenTouchBounds[1]=b.y/viewHeight;
    s_WidescreenTouchBounds[2]=(b.x+b.w)/viewWidth; s_WidescreenTouchBounds[3]=(b.y+b.h)/viewHeight;
    return;
#endif
    if (layout != SIM_CONFIG_SCREEN_LAYOUT_WIDESCREEN || viewWidth <= 0 || viewHeight <= 0) {''')
edit(quad,'void sim_GetTouchBounds(SIM_config_screen_layout_type layout, BOOL isSwapped, float bounds[4])\n{','''void sim_GetTouchBounds(SIM_config_screen_layout_type layout, BOOL isSwapped, float bounds[4])
{
#ifdef SDK_BUILD_ANDROID
    for(int i=0;i<4;i++) bounds[i]=s_WidescreenTouchBounds[i];
    return;
#endif\n''')
edit(quad,'G3SIM_Vertex_t * sim_GetScreenQuadArray(SIM_config_screen_layout_type layout, BOOL isSwapped)\n{','''G3SIM_Vertex_t * sim_GetScreenQuadArray(SIM_config_screen_layout_type layout, BOOL isSwapped)
{
#ifdef SDK_BUILD_ANDROID
    return s_WidescreenAdaptiveQuad;
#endif\n''')
edit(quad,'int sim_GetScreenQuadVertexCount(SIM_config_screen_layout_type layout, BOOL isSwapped)\n{','''int sim_GetScreenQuadVertexCount(SIM_config_screen_layout_type layout, BOOL isSwapped)
{
#ifdef SDK_BUILD_ANDROID
    return 12;
#endif\n''')
main=lib/'libraries/sim/src/sim_main.cpp'
edit(main,'extern "C" BOOL SIM_IsFullscreenOrWidescreen(void) {','''extern "C" void SIM_AndroidSetAspect(float aspect) { s_SIM_effectiveAspectRatio=(fx32)(aspect*FX32_ONE); }
extern "C" void SIM_AndroidToggleTouchScreen(void) { s_SIM_showTouchOverlay=!s_SIM_showTouchOverlay; }
extern "C" BOOL SIM_IsFullscreenOrWidescreen(void) {
#ifdef SDK_BUILD_ANDROID
  return (s_SIM_config.screenLayout==SIM_CONFIG_SCREEN_LAYOUT_WIDESCREEN ||
          s_SIM_config.screenLayout==SIM_CONFIG_SCREEN_LAYOUT_ADAPTIVE) &&
         !s_SIM_config.swapScreens && s_SIM_config.widescreenMode!=2;
#endif\n''')
# Android R must remain a real DS key; the DS toolbar owns overlay visibility.
s=main.read_text()
s=s.replace('s_SIM_config.screenLayout == SIM_CONFIG_SCREEN_LAYOUT_WIDESCREEN &&\n      IsOverworldPresentationActive()',
'''s_SIM_config.screenLayout == SIM_CONFIG_SCREEN_LAYOUT_WIDESCREEN &&
#ifndef SDK_BUILD_ANDROID
      IsOverworldPresentationActive()
#else
      false
#endif\n''')
s=s.replace('s_SIM_config.screenLayout == SIM_CONFIG_SCREEN_LAYOUT_WIDESCREEN &&\n          IsOverworldPresentationActive()',
'''s_SIM_config.screenLayout == SIM_CONFIG_SCREEN_LAYOUT_WIDESCREEN &&
#ifndef SDK_BUILD_ANDROID
          IsOverworldPresentationActive()
#else
          false
#endif\n''')
# Full window logical coordinates for layout; drawable size only for GL.
a=s.index('    // Scale the viewport to the correct aspect ratio and center it.')
b=s.index('    sim_ConfigureScreenQuads',a)
s=s[:a]+'''#ifdef SDK_BUILD_ANDROID
    if(windowWidth<=0 || windowHeight<=0) continue;
    viewWidth=windowWidth; viewHeight=windowHeight;
    int drawableWidth,drawableHeight;
    SDL_GL_GetDrawableSize(window,&drawableWidth,&drawableHeight);
    glViewport(0,0,drawableWidth,drawableHeight);
#else
'''+s[a:b]+'''#endif
'''+s[b:]
# Discard synthetic mouse events: finger ownership handles both pad and stylus.
s=s.replace('    if (Event.type == SDL_MOUSEBUTTONDOWN) {','''#ifdef SDK_BUILD_ANDROID
    if ((Event.type==SDL_MOUSEBUTTONDOWN || Event.type==SDL_MOUSEBUTTONUP) && Event.button.which==SDL_TOUCH_MOUSEID) continue;
#endif
    if (Event.type == SDL_MOUSEBUTTONDOWN) {''')
a=s.index('#ifdef SDK_BUILD_ANDROID\n      if (SIM_GUI_AndroidGetInputMask() != 0)'); b=s.index('#endif',a)+len('#endif');s=s[:a]+s[b:]
s=s.replace('  SDL_GetMouseState(&x, &y);','''#ifdef SDK_BUILD_ANDROID
  int stylusX,stylusY;
  if(SIM_GUI_AndroidStylus(&stylusX,&stylusY)) {
    s_tpData.x=(u16)stylusX; s_tpData.y=(u16)stylusY;
    s_tpData.validity=0; s_tpData.touch=1; return;
  }
  s_tpData.touch=isMouseDown && !SIM_GUI_AndroidMenuOpen();
#endif
  SDL_GetMouseState(&x, &y);''')
s=s.replace('x <= s_TouchPanelCoords[2]', 'x < s_TouchPanelCoords[2]').replace('y <= s_TouchPanelCoords[3]', 'y < s_TouchPanelCoords[3]')
main.write_text(s)
# Android supports both sensor orientations independently from screen arrangement.
manifest=root/'android/app/src/main/AndroidManifest.xml'
edit(manifest,'android:screenOrientation="portrait"','android:screenOrientation="fullSensor"',2)

menu=lib/'libraries/sim/src/gui/gui_config.c'
s=menu.read_text();s=s.replace('void GUI_AppConfigMain(bool * p_open)','\n#ifdef SDK_BUILD_ANDROID\n#include "android_config.inc"\n#else\nvoid GUI_AppConfigMain(bool * p_open)');menu.write_text(s+'\n#endif\n')
# Explicitly leave field presentation when the field application starts exiting.
field=root/'src/overlay005/fieldmap.c'
edit(field,'static BOOL FieldMap_Exit(ApplicationManager *appMan, int *param1)\n{','static BOOL FieldMap_Exit(ApplicationManager *appMan, int *param1)\n{\n#ifdef SDK_BUILD_ANDROID\n    SIM_SetOverworldWidescreenActive(FALSE);\n#endif')
