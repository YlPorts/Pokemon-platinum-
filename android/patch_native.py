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
static void SIM_AndroidStartupStage(const char *stage) {
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
