#!/usr/bin/env python3
"""Android VBlank clock independent of display caps, after repair_performance.py."""
from pathlib import Path
import shutil,sys
root=Path(sys.argv[1]);base=Path(__file__).parent
ntr=root/'subprojects/libntr'
for name in ('android_clock.h','android_clock.inc'):
    shutil.copyfile(base/'performance'/name,ntr/'libraries/sim/include'/name)
def edit(p,old,new,count=1):
    s=p.read_text();assert s.count(old)==count,(str(p),old[:70],s.count(old));p.write_text(s.replace(old,new))
p=ntr/'libraries/sim/src/sim_main.cpp'
edit(p,'static struct timespec s_SIM_lastFrameEnd;', '''#ifdef SDK_BUILD_ANDROID
#include "android_clock.inc"
#endif
static struct timespec s_SIM_lastFrameEnd;''')
s=p.read_text()
a=s.index('    // Framerate limiter respecting configured targetFPS')
b=s.index('    clock_gettime(CLOCK_MONOTONIC, &s_SIM_lastFrameEnd);',a)
old=s[a:b]
s=s[:a]+'''#ifdef SDK_BUILD_ANDROID
    AndroidPaceVBlank();
    AndroidPresent(window);
#else
'''+old+'#endif\n'+s[b:]
a=s.index('  // Delay for this 1/60s slice to maintain 30 FPS timing')
b=s.index('\n}\n',a)
s=s[:a]+'''#ifdef SDK_BUILD_ANDROID
  AndroidPaceVBlank();
#else
'''+s[a:b]+'\n#endif'+s[b:]
p.write_text(s)
# Native DS update rate. Old PC speed-hack settings must not halve animations
# or remove the field loop's second VBlank when restoring an existing config.
p=root/'src/port/sim_config_prj.c'
edit(p,'  return &s_SIM_config_prj;', '''#ifdef SDK_BUILD_ANDROID
  s_SIM_config_prj.enable60fps=FALSE;
  s_SIM_config_prj.enable60fpsSpeedFix=FALSE;
#endif
  return &s_SIM_config_prj;''')
p=root/'src/port/gui_configprj.c'
old='''    ConfigCheckBox("60 FPS", enable60fps);
    ConfigCheckBox("60 FPS Speed Fix", enable60fpsSpeedFix);'''
edit(p,old,'''#ifdef SDK_BUILD_ANDROID
    igTextWrapped("Velocidad original del juego. El limite de FPS solo afecta a la presentacion.");
#else
'''+old+'\n#endif')
p=ntr/'libraries/sim/include/android_config.inc'
edit(p,'igCombo_Str_arr("FPS",','igCombo_Str_arr("Limite de FPS",')
edit(p,'    bool sync=s_SIM_config.vsyncInterval!=0;', '''    igTextWrapped("El limite no acelera ni ralentiza a los personajes.");
    bool sync=s_SIM_config.vsyncInterval!=0;''')
print('Android: fixed VBlank deadlines, presentation-only cap, timing diagnostics')
# Avoid redundant 3D uniform uploads (fog arrays, texture switches, polygon mode).
shutil.copyfile(base/'performance/android_uniforms.inc',ntr/'libraries/sim/include/android_uniforms.inc')
p=ntr/'libraries/sim/src/g3_draw.cpp'
edit(p,'#include <stddef.h>','#include <stddef.h>\n#ifdef SDK_BUILD_ANDROID\n#include "android_uniforms.inc"\n#endif')
for suffix in ('1i','1fv','4f'):
    edit(p,f'glUniform{suffix}(__VA_ARGS__)',f'AndroidUniform{suffix}(__VA_ARGS__)')
edit(p,'void G3SIM_DrawInit()\n{','void G3SIM_DrawInit()\n{\n#ifdef SDK_BUILD_ANDROID\n    AndroidUniformReset();\n#endif')
