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


# Android uses LP64: long and pointers are 64 bits, but Nitro's binary data,
# registers and fixed-point maths require u32/s32 to stay exactly 32 bits.
types = root / "subprojects/libntr/include/nitro/types.h"
source = types.read_text()
old = "#if defined(SDK_BUILD_LINUX) || defined(SDK_BUILD_NX)"
assert source.count(old) == 2
source = source.replace(old, old + " || defined(SDK_BUILD_ANDROID)")
source = source.replace("typedef volatile u8 vu8;", """#ifdef SDK_BUILD_ANDROID
typedef char Nitro_u32_must_be_4_bytes[(sizeof(u32) == 4) ? 1 : -1];
typedef char Nitro_s32_must_be_4_bytes[(sizeof(s32) == 4) ? 1 : -1];
typedef char Nitro_u64_must_be_8_bytes[(sizeof(u64) == 8) ? 1 : -1];
#endif

typedef volatile u8 vu8;""")
types.write_text(source)

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
  FILE *trace = fopen("android_startup.log", "a");
  if (trace) { fprintf(trace, "%s\\n", stage); fclose(trace); }
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

# The SDL callback uses DS sound globals while NitroMain initializes them.
# Do not let that callback run concurrently with the initial sound setup.
audio = root / "subprojects/libntr/libraries/sim/src/sim_audio.cpp"
replace(audio, "    SDL_PauseAudio(0);\n}",
        """#ifndef SDK_BUILD_ANDROID
    SDL_PauseAudio(0);
#endif
}

#ifdef SDK_BUILD_ANDROID
extern \"C\" void SIM_AndroidStartAudio(void) {
    SDL_PauseAudio(0);
}
#endif""")
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
  FILE *trace = fopen("android_startup.log", "w");
  if (trace) fclose(trace);
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

sound = root / "src/sound_system.c"
replace(sound, '#include "sound_system.h"', '#include "sound_system.h"\n#include <stdlib.h>\n\n' + stage_macro)
replace(sound, "    NNS_SndInit();\n\n    SoundSystem_InitMic();",
        """    ANDROID_STAGE("Sonido: inicializar motor");
    NNS_SndInit();

    ANDROID_STAGE("Sonido: micrófono");
    SoundSystem_InitMic();""")
replace(sound, "    SoundSystem_InitHeapStates(soundSys);\n\n    soundSys->heap = NNS_SndHeapCreate(&soundSys->heapBuffer, sizeof(soundSys->heapBuffer));",
        """    ANDROID_STAGE("Sonido: preparar memoria");
    SoundSystem_InitHeapStates(soundSys);

    soundSys->heap = NNS_SndHeapCreate(&soundSys->heapBuffer, sizeof(soundSys->heapBuffer));
    ANDROID_STAGE(soundSys->heap ? "Sonido: memoria lista" : "Sonido: sin memoria");""")
replace(sound, '    NNS_SndArcInit(&soundSys->arc, "data/sound/pl_sound_data.sdat", soundSys->heap, 0);\n    NNS_SndArcPlayerSetup(soundSys->heap);',
        """    ANDROID_STAGE("Sonido: abrir archivo SDAT");
    NNS_SndArcInit(&soundSys->arc, "data/sound/pl_sound_data.sdat", soundSys->heap, 0);
#ifdef SDK_BUILD_ANDROID
    if (NNS_SndArcGetCurrent() != &soundSys->arc || soundSys->arc.info == NULL) {
        // Keep the precise failure recorded by NNS_SndArcInit/Setup.
        abort();
    }
#endif
    ANDROID_STAGE("Sonido: preparar reproductores");
    if (!NNS_SndArcPlayerSetup(soundSys->heap)) {
        ANDROID_STAGE("Sonido: sin memoria para reproductores");
        abort();
    }""")
replace(sound, "    SoundSystem_InitSoundHandles(soundSys);\n    SoundSystem_LoadPersistentGroup(soundSys);",
        """    ANDROID_STAGE("Sonido: preparar canales");
    SoundSystem_InitSoundHandles(soundSys);
    ANDROID_STAGE("Sonido: cargar sonidos comunes");
    SoundSystem_LoadPersistentGroup(soundSys);
    ANDROID_STAGE("Sonido: sonidos comunes listos");""")
replace(sound, "    Sound_SetPlaybackMode(options->soundMode);\n}",
        """    Sound_SetPlaybackMode(options->soundMode);
#ifdef SDK_BUILD_ANDROID
    // The SDL mixer must start only after the sound data and channels exist.
    extern void SIM_AndroidStartAudio(void);
    SIM_AndroidStartAudio();
#endif
    ANDROID_STAGE("Sonido: listo");
}""")

# libntrsystem is cloned by CI. Sound heap callbacks accept 64-bit user data
# on SDK_PORT; preserve the entire arc pointer on Android arm64.
arc = root / "subprojects/libntrsystem/libraries/snd/src/sndarc.c"
replace(arc, 'InfoDisposeCallback, (u32)arc, 0',
        'InfoDisposeCallback, (u64)arc, 0')
replace(arc, 'arc->header.fatSize*2, FatDisposeCallback, (u32)arc, 0',
        'arc->header.fatSize*2, FatDisposeCallback, (u64)arc, 0')
replace(arc, 'SymbolDisposeCallback, (u32)arc, 0',
        'SymbolDisposeCallback, (u64)arc, 0')
replace(arc, '#include <nnsys/snd/config.h>',
        '''#include <nnsys/snd/config.h>
#ifdef SDK_BUILD_ANDROID
extern void SIM_AndroidStartupStage(const char *stage);
#define ANDROID_ARC_STAGE(stage) SIM_AndroidStartupStage(stage)
#else
#define ANDROID_ARC_STAGE(stage) ((void)0)
#endif''')
replace(arc,
        '''    #ifdef SDK_PORT
    result = FS_OpenFile( &arc->file, filePath );
    NNS_ASSERTMSG( result, "Cannot open file %s\\n", filePath );
    if ( ! result ) return;
    #else''',
        '''    #ifdef SDK_PORT
    #ifndef SDK_BUILD_ANDROID
    result = FS_OpenFile( &arc->file, filePath );
    NNS_ASSERTMSG( result, "Cannot open file %s\\n", filePath );
    if ( ! result ) return;
    #endif
    #else''')
replace(arc,
        '''    FS_InitFile(&arc->file);

    #ifdef SDK_PORT
    result = FS_OpenFile(& arc->file, filePath);''',
        '''    FS_InitFile(&arc->file);

    #ifdef SDK_PORT
    ANDROID_ARC_STAGE("Sonido: SDAT abrir ruta");
    result = FS_OpenFile(& arc->file, filePath);''')
replace(arc,
        '''    NNS_ASSERTMSG(result, "Cannot open file %s\\n", filePath);
    if (!result) return;

    arc->file_open = TRUE;''',
        '''    NNS_ASSERTMSG(result, "Cannot open file %s\\n", filePath);
    if (!result) {
        ANDROID_ARC_STAGE("Sonido: SDAT archivo ausente");
        return;
    }

    arc->file_open = TRUE;''')
replace(arc,
        '''    result = FS_SeekFile(&arc->file, 0, FS_SEEK_SET);
    if (!result) return FALSE;

    readSize = FS_ReadFile(''',
        '''    ANDROID_ARC_STAGE("Sonido: SDAT leer cabecera");
    result = FS_SeekFile(&arc->file, 0, FS_SEEK_SET);
    if (!result) return FALSE;

    readSize = FS_ReadFile(''')
replace(arc,
        '''    if (heap != NNS_SND_HEAP_INVALID_HANDLE) {

        arc->info =''',
        '''    if (heap != NNS_SND_HEAP_INVALID_HANDLE) {

        ANDROID_ARC_STAGE("Sonido: SDAT reservar INFO");
        arc->info =''')
replace(arc,
        '''        if (arc->info == NULL) return FALSE;
        result = FS_SeekFile''',
        '''        if (arc->info == NULL) return FALSE;
        ANDROID_ARC_STAGE("Sonido: SDAT leer INFO");
        result = FS_SeekFile''')
replace(arc,
        '''        #ifdef SDK_PORT
        arc->fat = (NNSSndArcFat *)NNS_SndHeapAlloc''',
        '''        ANDROID_ARC_STAGE("Sonido: SDAT reservar FAT");
        #ifdef SDK_PORT
        arc->fat = (NNSSndArcFat *)NNS_SndHeapAlloc''')

replace(arc,
        '''        if (arc->fat == NULL) return FALSE;
        result = FS_SeekFile''',
        '''        if (arc->fat == NULL) return FALSE;
        ANDROID_ARC_STAGE("Sonido: SDAT leer FAT");
        result = FS_SeekFile''')
replace(arc,
        '''        WIN_NNSSndArcFat * arcFatWin;
        arcFatWin = malloc''',
        '''        ANDROID_ARC_STAGE("Sonido: SDAT convertir FAT");
        WIN_NNSSndArcFat * arcFatWin;
        arcFatWin = malloc''')
replace(arc,
        '''        arcFatWin = malloc( sizeof( WIN_NNSSndArcFat ) + ( sizeof( WIN_NNSSndArcFileInfo ) * arc->fat->count ));
        arcFatWin = memcpy''',
        '''        arcFatWin = malloc( sizeof( WIN_NNSSndArcFat ) + ( sizeof( WIN_NNSSndArcFileInfo ) * arc->fat->count ));
        if (arcFatWin == NULL) return FALSE;
        arcFatWin = memcpy''')
replace(arc,
        '''        free( arcFatWin );
        #endif''',
        '''        free( arcFatWin );
        ANDROID_ARC_STAGE("Sonido: SDAT estructura lista");
        #endif''')

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

save = root / "src/savedata.c"
replace(save, "static SaveData *sSaveDataPtr = NULL;",
        stage_macro + "\nstatic SaveData *sSaveDataPtr = NULL;")
for old, new in (
    ("    SaveData *saveData = Heap_Alloc(HEAP_ID_SAVE, sizeof(SaveData));",
     '    ANDROID_STAGE("Guardado: reservar memoria");\n    SaveData *saveData = Heap_Alloc(HEAP_ID_SAVE, sizeof(SaveData));'),
    ("    MI_CpuClearFast(saveData, sizeof(SaveData));",
     '    ANDROID_STAGE(saveData ? "Guardado: limpiar memoria" : "Guardado: sin memoria");\n    MI_CpuClearFast(saveData, sizeof(SaveData));'),
    ("    SavePageInfo_Init(saveData->pageInfo);",
     '    ANDROID_STAGE("Guardado: calcular tamaños");\n    SavePageInfo_Init(saveData->pageInfo);'),
    ("    SaveBlockInfo_Init(saveData->blockInfo, saveData->pageInfo);",
     '    ANDROID_STAGE("Guardado: preparar bloques");\n    SaveBlockInfo_Init(saveData->blockInfo, saveData->pageInfo);'),
    ("    int loadResult = SaveData_LoadCheck(saveData);",
     '    ANDROID_STAGE("Guardado: comprobar partida");\n    int loadResult = SaveData_LoadCheck(saveData);\n    ANDROID_STAGE("Guardado: partida comprobada");'),
    ("    case LOAD_RESULT_EMPTY:\n        SaveData_Clear(saveData);",
     '    case LOAD_RESULT_EMPTY:\n        ANDROID_STAGE("Guardado: crear partida nueva");\n        SaveData_Clear(saveData);'),
    ("    return saveData;\n}\n\nSaveData *SaveData_Ptr",
     '    ANDROID_STAGE("Guardado: listo");\n    return saveData;\n}\n\nSaveData *SaveData_Ptr'),
    ("    u8 *primaryBuffer = Heap_AllocAtEnd(HEAP_ID_APPLICATION, SAVE_SECTOR_SIZE * SAVE_PAGE_MAX);\n    u8 *backupBuffer = Heap_AllocAtEnd(HEAP_ID_APPLICATION, SAVE_SECTOR_SIZE * SAVE_PAGE_MAX);",
     '    ANDROID_STAGE("Guardado: reservar sectores");\n    u8 *primaryBuffer = Heap_AllocAtEnd(HEAP_ID_APPLICATION, SAVE_SECTOR_SIZE * SAVE_PAGE_MAX);\n    u8 *backupBuffer = Heap_AllocAtEnd(HEAP_ID_APPLICATION, SAVE_SECTOR_SIZE * SAVE_PAGE_MAX);\n    ANDROID_STAGE(primaryBuffer && backupBuffer ? "Guardado: sectores reservados" : "Guardado: sin memoria para sectores");'),
    ("    if (SaveData_CardLoad(PRIMARY_SECTOR_START * SAVE_SECTOR_SIZE, primaryBuffer, SAVE_SECTOR_SIZE * SAVE_PAGE_MAX)) {",
     '    ANDROID_STAGE("Guardado: leer sector principal");\n    if (SaveData_CardLoad(PRIMARY_SECTOR_START * SAVE_SECTOR_SIZE, primaryBuffer, SAVE_SECTOR_SIZE * SAVE_PAGE_MAX)) {'),
    ("    if (SaveData_CardLoad(BACKUP_SECTOR_START * SAVE_SECTOR_SIZE, backupBuffer, SAVE_SECTOR_SIZE * SAVE_PAGE_MAX)) {",
     '    ANDROID_STAGE("Guardado: leer sector respaldo");\n    if (SaveData_CardLoad(BACKUP_SECTOR_START * SAVE_SECTOR_SIZE, backupBuffer, SAVE_SECTOR_SIZE * SAVE_PAGE_MAX)) {'),
    ("    Heap_Free(primaryBuffer);\n    Heap_Free(backupBuffer);",
     '    ANDROID_STAGE("Guardado: liberar sectores");\n    Heap_Free(primaryBuffer);\n    Heap_Free(backupBuffer);'),
    ("    MI_CpuClearFast(body->data, sizeof(body->data));",
     '    ANDROID_STAGE("Guardado: limpiar partida nueva");\n    MI_CpuClearFast(body->data, sizeof(body->data));'),
    ("        saveTable[i].initFunc(page);",
     '''#ifdef SDK_BUILD_ANDROID
        char stage[80];
        snprintf(stage, sizeof(stage), "Guardado: iniciar sección %d", i);
        ANDROID_STAGE(stage);
#endif
        saveTable[i].initFunc(page);'''),
): 
    replace(save, old, new)

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

# Identify the exact player and heap allocation that fails on physical ARM64.
arc_player = root / "subprojects/libntrsystem/libraries/snd/src/sndarc_player.c"
replace(arc_player, '#include <nnsys/snd/sndarc_player.h>',
        '''#include <nnsys/snd/sndarc_player.h>
#ifdef SDK_BUILD_ANDROID
#include <stdio.h>
extern void SIM_AndroidStartupStage(const char *stage);
static void AndroidPlayerStage(int number, const char *phase) {
    char stage[96];
    snprintf(stage, sizeof(stage), "Sonido: reproductor %d: %s", number, phase);
    SIM_AndroidStartupStage(stage);
}
#define ANDROID_PLAYER_STAGE(number, phase) AndroidPlayerStage(number, phase)
#else
#define ANDROID_PLAYER_STAGE(number, phase) ((void)0)
#endif''')
replace(arc_player,
        '        playerInfo = NNS_SndArcGetPlayerInfo(playerNo);\n        if (playerInfo == NULL) continue;',
        '''        ANDROID_PLAYER_STAGE(playerNo, "leer datos");
        playerInfo = NNS_SndArcGetPlayerInfo(playerNo);
        if (playerInfo == NULL) continue;
        ANDROID_PLAYER_STAGE(playerNo, "configurar canales");''')
replace(arc_player,
        '                if (!NNS_SndPlayerCreateHeap(playerNo, heap, playerInfo->heapSize)) {\n                    return FALSE;\n                }',
        '''                ANDROID_PLAYER_STAGE(playerNo, "crear memoria");
                if (!NNS_SndPlayerCreateHeap(playerNo, heap, playerInfo->heapSize)) {
                    ANDROID_PLAYER_STAGE(playerNo, "sin memoria");
                    return FALSE;
                }
                ANDROID_PLAYER_STAGE(playerNo, "memoria lista");''')
replace(arc_player,
        '    return TRUE;\n}\n\nBOOL NNS_SndArcPlayerStartSeq',
        '    ANDROID_PLAYER_STAGE(NNS_SND_PLAYER_NUM, "todos listos");\n    return TRUE;\n}\n\nBOOL NNS_SndArcPlayerStartSeq')
