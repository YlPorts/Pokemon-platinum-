#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$1" && pwd)"
APK="$ROOT/android/app/build/outputs/apk/debug/app-debug.apk"
PACKAGE=org.pokeplatinum.android
mkdir -p smoke-results
capture() {
    adb exec-out screencap -p > smoke-results/game.png || true
    adb logcat -d > smoke-results/logcat.txt || true
    adb shell run-as "$PACKAGE" cat files/game/android_startup.log > smoke-results/startup.txt || true
}
trap capture EXIT
adb install -r "$APK"
# Seed the reproducible generated resource fixture into the debug app sandbox.
tar -C "$ROOT/build_android/android-assets" -cf /tmp/platinum-assets.tar .
adb push /tmp/platinum-assets.tar /data/local/tmp/platinum-assets.tar
adb shell run-as "$PACKAGE" mkdir -p files/game
adb shell run-as "$PACKAGE" tar --no-same-owner -xf /data/local/tmp/platinum-assets.tar -C files/game
adb shell run-as "$PACKAGE" touch files/game/.root_imported files/game/.android_assets_v027
adb shell am start -n "$PACKAGE/.LauncherActivity"
sleep 8
adb shell uiautomator dump /sdcard/launcher.xml
adb pull /sdcard/launcher.xml /tmp/launcher.xml
python3 - <<'PY' > /tmp/platinum-tap.sh
import re
import xml.etree.ElementTree as ET
root = ET.parse('/tmp/launcher.xml')
for node in root.iter('node'):
    if node.get('text') == 'Iniciar juego':
        bounds = list(map(int, re.findall(r'\d+', node.get('bounds'))))
        print('adb shell input tap', (bounds[0]+bounds[2])//2, (bounds[1]+bounds[3])//2)
        break
else:
    raise RuntimeError('Launcher play button not found')
PY
bash /tmp/platinum-tap.sh
sleep 35
mkdir -p smoke-results
adb exec-out screencap -p > smoke-results/game.png
adb logcat -d > smoke-results/logcat.txt
adb shell run-as "$PACKAGE" cat files/game/android_startup.log > smoke-results/startup.txt
adb shell pidof "$PACKAGE:game" | tr -d '\r' | rg '^[0-9]+$'
rg -q 'Primer fotograma' smoke-results/startup.txt
python3 - <<'PY'
from PIL import Image
image = Image.open('smoke-results/game.png').convert('RGB')
w, h = image.size
# Exclude system bars/control buttons; the game area must contain rendered content.
colors = image.crop((w//5, h//5, w*4//5, h*3//5)).getcolors(w*h)
assert colors and len(colors) > 20, 'Game viewport has no rendered scene'
print('PASS: Android game stays alive and renders a scene')
PY
