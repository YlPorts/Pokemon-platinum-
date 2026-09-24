void GUI_AppConfigMain(bool *p_open) {
    ImGuiIO *io=igGetIO_Nil();
    igSetNextWindowSize((ImVec2){io->DisplaySize.x*.88f,io->DisplaySize.y*.80f},ImGuiCond_Always);
    igSetNextWindowPos((ImVec2){io->DisplaySize.x*.5f,io->DisplaySize.y*.5f},ImGuiCond_Always,(ImVec2){.5f,.5f});
    igBegin("Pantallas y controles",p_open,ImGuiWindowFlags_NoCollapse);
    bool changed=false;
    int layout=s_SIM_config.screenLayout;
    const char *layouts[]={"Dos verticales","Panoramica","Dos horizontales","Principal + secundaria","Adaptativa"};
    if(igCombo_Str_arr("Pantallas",&layout,layouts,5,5)) { s_SIM_config.screenLayout=layout; changed=true; }
    bool swap=s_SIM_config.swapScreens;
    if(igCheckbox("Intercambiar pantallas",&swap)) { s_SIM_config.swapScreens=swap; changed=true; }
    bool wide=s_SIM_config.widescreenMode!=2;
    if(igCheckbox("Panoramica en el mundo 3D",&wide)) { s_SIM_config.widescreenMode=wide?0:2; changed=true; }
    const char *aspects[]={"Adaptado a pantalla","16:9","21:9"};
    if(igCombo_Str_arr("Formato",&s_SIM_config.androidWideAspect,aspects,3,3)) changed=true;
    const char *sizes[]={"Compactos","Medianos","Grandes"};
    int size=(s_SIM_config.androidControlSize-85)/15;
    if(igCombo_Str_arr("Botones",&size,sizes,3,3)) { s_SIM_config.androidControlSize=85+size*15; changed=true; }
    int alpha=s_SIM_config.androidControlOpacity;
    if(igSliderInt("Opacidad",&alpha,15,75,"%d %%",0)) { s_SIM_config.androidControlOpacity=alpha; changed=true; }
    const char *fpsNames[]={"30","60","90","120","Sin limite"};
    int fps=s_SIM_config.capFrameRate?(s_SIM_config.targetFPS==30?0:s_SIM_config.targetFPS==90?2:s_SIM_config.targetFPS==120?3:1):4;
    if(igCombo_Str_arr("FPS",&fps,fpsNames,5,5)) { const int values[]={30,60,90,120,60}; s_SIM_config.capFrameRate=fps!=4; s_SIM_config.targetFPS=values[fps]; changed=true; }
    bool sync=s_SIM_config.vsyncInterval!=0;
    if(igCheckbox("VSync",&sync)) { s_SIM_config.vsyncInterval=sync?1:0; SDL_GL_SetSwapInterval(sync?1:0); changed=true; }
    igTextWrapped("SWAP intercambia las pantallas. DS muestra u oculta la secundaria al explorar en horizontal. En menus y combates se conservan ambas pantallas.");
    igEnd();
    if(changed) { SIM_GUI_AndroidResetInput(); SIM_Config_SaveConfigFile(&s_SIM_config); }
}
