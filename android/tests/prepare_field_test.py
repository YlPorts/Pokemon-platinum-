#!/usr/bin/env python3
"""Test-only hooks added AFTER source packaging; never included in ARM64 APK."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
p=root/'src/main.c';s=p.read_text();s='#include <stdio.h>\nint gAndroidFieldTest=0;\n'+s
key='    ANDROID_STAGE("Preparando pantalla inicial");'
assert s.count(key)==1
s=s.replace(key,key+'''\n    FILE *testFile=fopen("android_field_test", "r");
    gAndroidFieldTest=testFile!=NULL;
    if(testFile) fclose(testFile);
    if(gAndroidFieldTest) {
        EnqueueApplication(FS_OVERLAY_ID_NONE, &gGameStartNewSaveAppTemplate);
    } else
''');p.write_text(s)
p=root/'src/game_start.c';s=p.read_text();key='    InitializeNewSave(HEAP_ID_GAME_START, saveData, 1);';assert s.count(key)==1
s=s.replace(key,'''    extern int gAndroidFieldTest;
    if(gAndroidFieldTest) StartNewSave(HEAP_ID_GAME_START,saveData);
'''+key);p.write_text(s)
p=root/'src/field_system.c';s=p.read_text();key='    FieldSystem_SetLoadNewGameSpawnTask(sFieldSystem);';assert s.count(key)==1
s='#include "location.h"\n#include <stdio.h>\n'+s
s=s.replace(key,'''    extern int gAndroidFieldTest;
    if(gAndroidFieldTest) {
        SetPlayerFirstRespawnLocation(sFieldSystem->location);
        fprintf(stderr,"Android field test: Twinleaf Town\\n");
    }
'''+key);p.write_text(s)
