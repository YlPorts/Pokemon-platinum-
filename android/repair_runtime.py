#!/usr/bin/env python3
"""Checked LP64, resource and Android lifecycle repairs after patch_native.py."""
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
ntr = root / 'subprojects/libntr'
nns = root / 'subprojects/libntrsystem'

def edit(path, old, new, count=1):
    source = path.read_text()
    if source.count(old) != count:
        raise RuntimeError(f'{path}: expected {count} matches for {old[:90]!r}')
    path.write_text(source.replace(old, new))

# DS requested alignment is 4, but native allocator headers contain pointers.
# Round both the payload size and its alignment so following headers stay aligned.
for name in ('expheap.c', 'frameheap.c', 'unitheap.c'):
    path = nns / 'libraries/fnd/src' / name
    source = path.read_text()
    source, count = re.subn(r'#define MIN_ALIGNMENT\s+4',
        '#ifdef SDK_BUILD_ANDROID\n#define MIN_ALIGNMENT 8\n#else\n#define MIN_ALIGNMENT 4\n#endif', source)
    assert count == 1
    marker = '    NNS_ASSERT(alignment % MIN_ALIGNMENT == 0);'
    source = source.replace(marker, '''#ifdef SDK_BUILD_ANDROID
    if (alignment == 4) alignment = 8;
    if (alignment == -4) alignment = -8;
#endif
''' + marker)
    if name == 'unitheap.c':
        source = source.replace('u32 NNS_FndCalcHeapSizeForUnitHeap (u32 memBlockSize, u32 memBlockNum, int alignment)\n{', 'u32 NNS_FndCalcHeapSizeForUnitHeap (u32 memBlockSize, u32 memBlockNum, int alignment)\n{\n    if (alignment < MIN_ALIGNMENT) alignment = MIN_ALIGNMENT;')
    path.write_text(source)
edit(nns / 'libraries/snd/src/heap.c',
     'startAddressRounded = ROUNDUP64( startAddressRounded, 4 );',
     'startAddressRounded = ROUNDUP64( startAddressRounded, sizeof(void *) );')

# Keep pointer payloads intact when a music bank or streaming player is freed.
loader = nns / 'libraries/snd/src/sndarc_loader.c'
edit(loader, '(u32)NNS_SndArcGetCurrent()', '(u64)NNS_SndArcGetCurrent()', 5)
edit(loader, '(u32)waveArc,', '(u64)waveArc,')
edit(nns / 'libraries/snd/src/sndarc_stream.c',
     'DisposeCallback, (u32)player, 0', 'DisposeCallback, (u64)player, 0')

# Reject invalid binary lengths before they reach the heap or conversion loops.
arc = nns / 'libraries/snd/src/sndarc.c'
edit(arc, '    if (readSize != sizeof(arc->header)) return FALSE;', '''    if (readSize != sizeof(arc->header)) return FALSE;
#ifdef SDK_BUILD_ANDROID
    const u32 fileSize = arc->header.fileHeader.fileSize;
    if (memcmp(arc->header.fileHeader.signature, "SDAT", 4) != 0 ||
        arc->header.fileHeader.byteOrder != 0xfeff ||
        arc->header.infoSize < sizeof(NNSSndArcInfo) ||
        arc->header.infoOffset > fileSize ||
        arc->header.infoSize > fileSize - arc->header.infoOffset ||
        arc->header.fatSize < sizeof(WIN_NNSSndArcFat) ||
        arc->header.fatOffset > fileSize ||
        arc->header.fatSize > fileSize - arc->header.fatOffset ||
        arc->header.fatSize > 0x7fffffff / 2) {
        ANDROID_ARC_STAGE("Sonido: cabecera SDAT inválida");
        return FALSE;
    }
#endif''')
edit(arc, '        WIN_NNSSndArcFat * arcFatWin;', '''#ifdef SDK_BUILD_ANDROID
        if (arc->fat->count > (arc->header.fatSize - sizeof(WIN_NNSSndArcFat)) /
                              sizeof(WIN_NNSSndArcFileInfo)) {
            ANDROID_ARC_STAGE("Sonido: tabla FAT inválida");
            return FALSE;
        }
#endif
        WIN_NNSSndArcFat * arcFatWin;''')

# A freshly initialized DS file must not carry an uninitialized native FILE*.
fs = ntr / 'libraries/fs/src/fs_file.c'
edit(fs, 'void FS_InitFile (FSFile *p_file)\n{', '''void FS_InitFile (FSFile *p_file)
{
#ifdef SDK_BUILD_ANDROID
    memset(p_file, 0, sizeof(*p_file));
#endif''')
edit(fs, 'return fread( dst, 1, old_len, p_file->pcFilePtr );', '''size_t got = fread(dst, 1, (size_t)old_len, p_file->pcFilePtr);
            p_file->prop.file.pos = (u32)ftell(p_file->pcFilePtr);
            return (s32)got;''')

# Correct channel selection precedence and preserve stereo + transitions to silence.
audio = ntr / 'libraries/sim/src/sim_audio.cpp'
edit(audio, 'if((s_SIM_sndcnt[chNo]>>29)&0x3 == 3)',
     'if (((s_SIM_sndcnt[chNo] >> 29) & 0x3) == 3)')
edit(audio, '        right = left;\n', '')
edit(audio, '        if(left != 0) {', '        if(left != s_outputLastLeftSample) {')
edit(audio, '        if(right != 0) {', '        if(right != s_outputLastRightSample) {')

main = ntr / 'libraries/sim/src/sim_main.cpp'
edit(main, '  SDL_GL_SetSwapInterval(s_SIM_config.vsyncInterval);\n\n  u32 windowHeight;', '\n  u32 windowHeight;')
edit(main, '  SIM_AndroidStartupStage("Contexto OpenGL ES creado");',
     '  SDL_GL_SetSwapInterval(s_SIM_config.vsyncInterval);\n  SIM_AndroidStartupStage("Contexto OpenGL ES creado");')
# The old error path queried a different, not-yet-created shader for log length.
edit(main, 'glGetShaderiv(g2FragmentShader, GL_INFO_LOG_LENGTH, &logSize);',
     'glGetShaderiv(_id, GL_INFO_LOG_LENGTH, &logSize);')

# Isolate native state so a failed/closed game can be launched again cleanly.
manifest = root / 'android/app/src/main/AndroidManifest.xml'
edit(manifest, 'android:name="org.pokeplatinum.android.GameActivity"',
     'android:name="org.pokeplatinum.android.GameActivity"\n            android:process=":game"')
edit(manifest, '@android:style/Theme.Material.Light.NoActionBar',
     '@android:style/Theme.Material.NoActionBar')

# Native menu must be usable with fingers and must not leave game buttons held.
gui = ntr / 'libraries/sim/src/gui/gui.c'
edit(gui, '\tigStyleColorsDark(NULL);', '''\tigStyleColorsDark(NULL);
#ifdef SDK_BUILD_ANDROID
    int w = 0, h = 0;
    SDL_GetWindowSize(aWindow, &w, &h);
    float uiScale = (float)(w < h ? w : h) / 480.0f;
    if (uiScale < 1.25f) uiScale = 1.25f;
    if (uiScale > 2.5f) uiScale = 2.5f;
    ImGuiStyle_ScaleAllSizes(igGetStyle(), uiScale);
    ioptr->FontGlobalScale = uiScale;
    s_btnSize = (ImVec2){150.0f * uiScale, 32.0f * uiScale};
#endif''')
edit(gui, 'void SIM_GUI_AndroidTouchMain(void)\n{',
     'void SIM_GUI_AndroidTouchMain(void)\n{\n    if (SIM_GUI_State) return;')
edit(gui, '    SIM_GUI_AndroidProcessTouchEvent(aEvent);', '''    if (aEvent->type == SDL_APP_WILLENTERBACKGROUND ||
        (aEvent->type == SDL_WINDOWEVENT && aEvent->window.event == SDL_WINDOWEVENT_FOCUS_LOST)) {
        memset(s_androidFingers, 0, sizeof(s_androidFingers));
        s_androidTouchButtons = 0;
    }
    if (!SIM_GUI_State) SIM_GUI_AndroidProcessTouchEvent(aEvent);
    else {
        memset(s_androidFingers, 0, sizeof(s_androidFingers));
        s_androidTouchButtons = 0;
    }''')
edit(gui, 'width - size * 2.7f - margin', 'width - size * 3.0f - margin', 2)
# DS face buttons: X top, Y left, A right, B bottom (hitboxes and labels).
source = gui.read_text()
mapping = {'Y': 'X', 'X': 'Y', 'B': 'A', 'A': 'B'}
source = re.sub(r'SIM_ANDROID_([YXBA])\);', lambda m: f'SIM_ANDROID_{mapping[m[1]]});', source)
source = re.sub(r'SIM_GUI_AndroidButton\("([YXBA])"', lambda m: f'SIM_GUI_AndroidButton("{mapping[m[1]]}"', source)
gui.write_text(source)
edit(gui, '    if (aEvent->type == SDL_FINGERDOWN && aEvent->tfinger.x < 0.19f &&',
     '    if (!SIM_GUI_State && aEvent->type == SDL_FINGERDOWN && aEvent->tfinger.x < 0.19f &&')
edit(gui, 'bool SIM_GUI_IsGameLogicPaused(void)\n{\n    return s_pauseGameLogic;', '''bool SIM_GUI_AndroidMenuOpen(void) { return SIM_GUI_State; }

bool SIM_GUI_IsGameLogicPaused(void)
{
#ifdef SDK_BUILD_ANDROID
    return s_pauseGameLogic || SIM_GUI_State;
#else
    return s_pauseGameLogic;
#endif''')
edit(ntr / 'include/simulator/gui.h', 'void SIM_GUI_AndroidTouchMain(void);',
     'void SIM_GUI_AndroidTouchMain(void);\nbool SIM_GUI_AndroidMenuOpen(void);')
edit(main, '    SIM_GUI_ProcessEvent(&Event);\n    if (Event.type == SDL_WINDOWEVENT)', '''    SIM_GUI_ProcessEvent(&Event);
#ifdef SDK_BUILD_ANDROID
    if (SIM_GUI_AndroidMenuOpen()) {
      isMouseDown = 0;
      s_tpData.touch = 0;
      s_reg_PAD_KEYINPUT |= 0x3ff;
      *(vu16 *)HW_BUTTON_XY_BUF |= 0x0c00;
      if (Event.type == SDL_KEYDOWN && SIM_Pad_IsListening() && !Event.key.repeat)
        SIM_GUI_HandleKeyDown(Event.key.keysym.sym);
      continue;
    }
#endif
    if (Event.type == SDL_WINDOWEVENT)''')

# A second ABI is used only for an automated Android emulator boot test.
native = root / 'tools/android/build-native.sh'
edit(native, 'if [[ "$ABI" != "arm64-v8a" ]]; then',
     'if [[ "$ABI" != "arm64-v8a" && "$ABI" != "x86_64" ]]; then')
edit(native, 'TRIPLE=aarch64-linux-android', '''TRIPLE=aarch64-linux-android
CPU_FAMILY=aarch64
if [[ "$ABI" == "x86_64" ]]; then
    TRIPLE=x86_64-linux-android
    CPU_FAMILY=x86_64
fi''')
edit(native, "cpu_family = 'aarch64'\ncpu = 'aarch64'",
     "cpu_family = '$CPU_FAMILY'\ncpu = '$CPU_FAMILY'")
edit(native, '[properties]\nneeds_exe_wrapper',
     "c_link_args = ['-Wl,-z,max-page-size=16384']\ncpp_link_args = ['-Wl,-z,max-page-size=16384']\n\n[properties]\nneeds_exe_wrapper")
edit(native, '-DANDROID_ABI="$ABI" -DANDROID_PLATFORM="android-$API"',
     '-DANDROID_ABI="$ABI" -DANDROID_PLATFORM="android-$API" -DANDROID_SUPPORT_FLEXIBLE_PAGE_SIZES=ON', 2)
edit(root / 'meson.build', "shared_args = ['-DPOKEPLATINUM_GENERATED_ENUM', '-g']",
     "shared_args = ['-DPOKEPLATINUM_GENERATED_ENUM', '-g']\nif build_target == 'android'\n    shared_args += ['-O2', '-fno-strict-aliasing']\nendif")
