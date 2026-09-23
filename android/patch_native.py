#!/usr/bin/env python3
"""Small, checked Android-only changes to the bundled PC port source."""
import sys
from pathlib import Path

root = Path(sys.argv[1])


def replace(path, old, new):
    source = path.read_text()
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one match, got {count}: {old[:80]!r}")
    path.write_text(source.replace(old, new, 1))


config = root / "subprojects/libntr/libraries/sim/src/config/sim_config.c"
replace(config,
        "#else\n    aConfig->internalResolutionScale = 10;\n",
        "#elif defined(SDK_BUILD_ANDROID)\n    aConfig->internalResolutionScale = 2;\n"
        "#else\n    aConfig->internalResolutionScale = 10;\n")

main = root / "subprojects/libntr/libraries/sim/src/sim_main.cpp"
replace(main, "// Simulator configuration\nSIM_config_type s_SIM_config = {};",
        """// Simulator configuration
SIM_config_type s_SIM_config = {};

#ifdef SDK_BUILD_ANDROID
extern "C" void SIM_AndroidStartupStage(const char *stage) {
  FILE *file = fopen("android_startup.txt", "w");
  if (file) {
    fprintf(file, "%s\\n", stage);
    fclose(file);
  }
  fprintf(stderr, "Platinum startup: %s\\n", stage);
}
#endif""")
replace(main,
        "  SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO | SDL_INIT_TIMER |\n           SDL_INIT_JOYSTICK);\n  SIM_Audio_Init(44100);",
        """  if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO | SDL_INIT_TIMER |
               SDL_INIT_JOYSTICK) != 0) {
#ifdef SDK_BUILD_ANDROID
    SIM_AndroidStartupStage(SDL_GetError());
#endif
    return nullptr;
  }
  SIM_Audio_Init(44100);""")
replace(main,
        "  context = SDL_GL_CreateContext(window);\n\n#ifndef SDK_BUILD_ANDROID",
        """  if (!window) {
#ifdef SDK_BUILD_ANDROID
    SIM_AndroidStartupStage(SDL_GetError());
#endif
    return nullptr;
  }
  context = SDL_GL_CreateContext(window);
  if (!context) {
#ifdef SDK_BUILD_ANDROID
    SIM_AndroidStartupStage(SDL_GetError());
#endif
    return nullptr;
  }
#ifdef SDK_BUILD_ANDROID
  SIM_AndroidStartupStage("Contexto OpenGL ES creado");
#endif

#ifndef SDK_BUILD_ANDROID""")
replace(main,
        "  SIM_GUI_Init(window, context);\n\n  clock_gettime",
        """  SIM_GUI_Init(window, context);
#ifdef SDK_BUILD_ANDROID
  SIM_AndroidStartupStage("Renderizador y menú listos");
#endif

  clock_gettime""")
replace(main,
        "  if (chdir(gamePath.c_str()) != 0) {\n    perror(\"Could not open the game data directory\");\n    return 1;\n  }",
        """  if (chdir(gamePath.c_str()) != 0) {
    perror("Could not open the game data directory");
    return 1;
  }
  SIM_AndroidStartupStage("Directorio del juego abierto");""")
replace(main,
        "  if (!SIM_Config_LoadConfigFile(&s_SIM_config)) {\n    // Config file does not exist. Save config file with defaults\n    SIM_Config_SaveConfigFile(&s_SIM_config);\n  }",
        """  if (!SIM_Config_LoadConfigFile(&s_SIM_config)) {
    // Config file does not exist. Save config file with defaults
    SIM_Config_SaveConfigFile(&s_SIM_config);
  }
#ifdef SDK_BUILD_ANDROID
  // Older APKs wrote the desktop 10x default; keep this within mobile GPU limits.
  if (s_SIM_config.internalResolutionScale < 1 ||
      s_SIM_config.internalResolutionScale > 4) {
    s_SIM_config.internalResolutionScale = 2;
    SIM_Config_SaveConfigFile(&s_SIM_config);
  }
  SIM_AndroidStartupStage("Configuración cargada");
#endif""")
replace(main,
        "  SIM_RenderInit(NULL);\n  G3SIM_DrawInit();",
        """#ifdef SDK_BUILD_ANDROID
  SIM_AndroidStartupStage("Iniciando renderizador");
#endif
  SIM_RenderInit(NULL);
#ifdef SDK_BUILD_ANDROID
  if (!window || !context) return 1;
#endif
  G3SIM_DrawInit();""")
replace(main,
        "  NitroMain();\n  return 0;",
        """#ifdef SDK_BUILD_ANDROID
  SIM_AndroidStartupStage("Entrando al juego");
#endif
  NitroMain();
  return 0;""")

# Keep the last completed startup step on disk so a crash on a physical phone
# can be narrowed down without adb or a native tombstone.
stage_macro = """#ifdef SDK_BUILD_ANDROID
extern void SIM_AndroidStartupStage(const char *stage);
#define ANDROID_STAGE(stage) SIM_AndroidStartupStage(stage)
#else
#define ANDROID_STAGE(stage) ((void)0)
#endif
"""

game = root / "src/main.c"
replace(game, "#define RESET_COMBO", stage_macro + "\n#define RESET_COMBO")
for old, new in (
    ("    SIM_Config_prj_init();", '    ANDROID_STAGE("Configuración del juego");\n    SIM_Config_prj_init();'),
    ("    InitSystem();", '    ANDROID_STAGE("Sistema: entrando");\n    InitSystem();\n    ANDROID_STAGE("Sistema: listo");'),
    ("    InitVRAM();", '    ANDROID_STAGE("Memoria de vídeo");\n    InitVRAM();'),
    ("    InitKeypadAndTouchpad();", '    ANDROID_STAGE("Controles");\n    InitKeypadAndTouchpad();'),
    ("    InitRTC();", '    ANDROID_STAGE("Reloj");\n    InitRTC();'),
    ("    InitApplication();", '    ANDROID_STAGE("Aplicación");\n    InitApplication();'),
    ("    Fonts_Init();", '    ANDROID_STAGE("Fuentes");\n    Fonts_Init();'),
    ("    sApplication.args.saveData = SaveData_Init();", '    ANDROID_STAGE("Datos guardados");\n    sApplication.args.saveData = SaveData_Init();'),
    ("    SoundSystem_Init(SaveData_GetChatotCry", '    ANDROID_STAGE("Sonido del juego");\n    SoundSystem_Init(SaveData_GetChatotCry'),
    ("    if (sub_02038FFC(HEAP_ID_APPLICATION)", '    ANDROID_STAGE("Red y configuración");\n    if (sub_02038FFC(HEAP_ID_APPLICATION)'),
    ("    if (SaveData_BackupExists(sApplication.args.saveData)", '    ANDROID_STAGE("Preparando pantalla inicial");\n    if (SaveData_BackupExists(sApplication.args.saveData)'),
    ("    gIgnoreCartridgeForWake = FALSE;\n\n    while (TRUE) {", '    gIgnoreCartridgeForWake = FALSE;\n\n    ANDROID_STAGE("Primer fotograma");\n    while (TRUE) {'),
):
    replace(game, old, new)

system = root / "src/system.c"
replace(system, "#define MAIN_TASK_MAX", stage_macro + "\n#define MAIN_TASK_MAX")
for old, new in (
    ("    OS_Init();", '    ANDROID_STAGE("Sistema: OS_Init");\n    OS_Init();'),
    ("    FX_Init();", '    ANDROID_STAGE("Sistema: gráficos");\n    FX_Init();'),
    ("    InitHeapSystem();", '    ANDROID_STAGE("Sistema: heaps");\n    InitHeapSystem();'),
    ("    gSystem.mainTaskMgr = SysTaskManager_Init", '    ANDROID_STAGE("Sistema: tareas");\n    gSystem.mainTaskMgr = SysTaskManager_Init'),
    ("    FS_Init(1);", '    ANDROID_STAGE("Sistema: FS_Init");\n    FS_Init(1);'),
    ("    CheckForMemoryTampering();", '    ANDROID_STAGE("Sistema: cabecera ROM");\n    CheckForMemoryTampering();'),
    ("    u32 fsTableSize = FS_GetTableSize();", '    ANDROID_STAGE("Sistema: tablas ROM");\n    u32 fsTableSize = FS_GetTableSize();'),
    ("    FS_LoadTable(fsTable, fsTableSize);", '    FS_LoadTable(fsTable, fsTableSize);\n    ANDROID_STAGE("Sistema: FS listo");'),
    ("    InitCRC16Table(HEAP_ID_SYSTEM);", '    ANDROID_STAGE("Sistema: CRC");\n    InitCRC16Table(HEAP_ID_SYSTEM);'),
):
    replace(system, old, new)

os_init = root / "subprojects/libntr/libraries/os/src/os_init.c"
replace(os_init, "#pragma profile off\n\nvoid OS_Init (void)",
        stage_macro + "\n#pragma profile off\n\nvoid OS_Init (void)")
for old, new in (
    ("    OS_InitArena();\n\n    PXI_Init();", '    ANDROID_STAGE("OS: arena");\n    OS_InitArena();\n\n    ANDROID_STAGE("OS: PXI");\n    PXI_Init();'),
    ("    OS_InitLock();\n    OS_InitArenaEx();", '    ANDROID_STAGE("OS: memoria y locks");\n    OS_InitLock();\n    OS_InitArenaEx();'),
    ("    OS_InitIrqTable();\n    OS_SetIrqStackChecker();", '    ANDROID_STAGE("OS: interrupciones");\n    OS_InitIrqTable();\n    OS_SetIrqStackChecker();'),
    ("    MI_Init();\n\n    OS_InitVAlarm();", '    ANDROID_STAGE("OS: memoria interna");\n    MI_Init();\n\n    OS_InitVAlarm();'),
    ("#ifndef SDK_NO_THREAD\n    OS_InitThread();", '#ifndef SDK_NO_THREAD\n    ANDROID_STAGE("OS: hilos");\n    OS_InitThread();'),
    ("#ifndef SDK_TEG\n    CTRDG_Init();\n#endif\n\n#ifndef SDK_SMALL_BUILD", '#ifndef SDK_TEG\n    ANDROID_STAGE("OS: cartucho");\n    CTRDG_Init();\n#endif\n\n#ifndef SDK_SMALL_BUILD'),
    ("    CARD_Init();", '    ANDROID_STAGE("OS: tarjeta ROM");\n    CARD_Init();'),
    ("    PM_Init();", '    ANDROID_STAGE("OS: energía");\n    PM_Init();'),
):
    replace(os_init, old, new)

gui = root / "subprojects/libntr/libraries/sim/src/gui/gui.c"
replace(gui,
        "    SIM_GUI_AndroidProcessTouchEvent(aEvent);\n    if (SIM_GUI_State) {",
        """    if (aEvent->type == SDL_FINGERDOWN && aEvent->tfinger.x < 0.19f &&
        aEvent->tfinger.y < 0.10f) {
        SIM_GUI_Toggle();
        return;
    }
    SIM_GUI_AndroidProcessTouchEvent(aEvent);
    if (SIM_GUI_State) {""")
replace(gui,
        "    SIM_GUI_AndroidButton(\"U\", padX + size, padY, size);",
        """    igSetCursorPos((ImVec2){margin, margin});
    igButton("MENU", (ImVec2){size * 1.3f, size * 0.72f});
    SIM_GUI_AndroidButton("U", padX + size, padY, size);""")

gui_config = root / "subprojects/libntr/libraries/sim/src/gui/gui_config.c"
replace(gui_config,
        '    "Vertical",\n    "Horizontal",\n    "Large Screen"',
        '    "Vertical",\n    "Widescreen",\n    "Horizontal",\n    "Large Screen"')
replace(gui_config,
        'igCombo_Str_arr("Layout", &sScreenLayout, ScreenLayoutStrings, 3, 3)',
        'igCombo_Str_arr("Layout", &sScreenLayout, ScreenLayoutStrings, 4, 4)')
