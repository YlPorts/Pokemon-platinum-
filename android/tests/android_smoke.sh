#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$1" && pwd)"
APK="$ROOT/android/app/build/outputs/apk/debug/app-debug.apk"
PACKAGE=org.pokeplatinum.android
mkdir -p smoke-results
capture() {
    adb exec-out screencap -p > smoke-results/final.png || true
    adb logcat -d > smoke-results/logcat.txt || true
    adb shell run-as "$PACKAGE" cat files/game/android_startup.log > smoke-results/startup.txt || true
}
trap capture EXIT
adb shell wm size 540x960
adb shell wm density 210
adb install -r "$APK"
# Seed the reproducible generated resource fixture into the debug app sandbox.
tar -C "$ROOT/build_android/android-assets" -cf /tmp/platinum-assets.tar .
adb push /tmp/platinum-assets.tar /data/local/tmp/platinum-assets.tar
adb shell run-as "$PACKAGE" mkdir -p files/game
adb shell run-as "$PACKAGE" tar --no-same-owner -xf /data/local/tmp/platinum-assets.tar -C files/game
adb shell run-as "$PACKAGE" touch files/game/.root_imported files/game/.android_assets_v027
adb shell settings put secure immersive_mode_confirmations confirmed
adb shell am start -n "$PACKAGE/.LauncherActivity"
sleep 8
adb shell uiautomator dump /sdcard/launcher.xml
adb pull /sdcard/launcher.xml /tmp/launcher.xml
cp /tmp/launcher.xml smoke-results/launcher.xml
python3 - <<'PY' > /tmp/platinum-tap.sh
import re
import xml.etree.ElementTree as ET
root = ET.parse('/tmp/launcher.xml')
for node in root.iter('node'):
    if node.get('text', '').casefold() == 'iniciar juego' and node.get('enabled') == 'true':
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
# Initial copyright artwork has only five colors; contrast detects it correctly.
# Resolve native control coordinates from the actual display dimensions.
read -r AX AY < <(python3 - <<'PYCOORD'
from PIL import Image
w, h = Image.open('smoke-results/game.png').size
size = w * .145 if w < h else h * .115
margin = size * .28
print(round(w - size * .5 - margin), round(h - size * 1.25 - margin))
PYCOORD
)
# Advance using a held A touch and check that the native menu is reachable.
for press in $(seq 1 6); do
    adb shell input swipe "$AX" "$AY" "$AX" "$AY" 1000
    sleep 1
done
sleep 20
adb exec-out screencap -p > smoke-results/game-input.png
adb shell pidof "$PACKAGE:game"
adb shell input swipe 40 40 40 40 500
sleep 2
adb exec-out screencap -p > smoke-results/menu.png
adb shell pidof "$PACKAGE:game"

# Close menu with Back, then give the software-rendered intro time to advance.
adb shell input keyevent 4
sleep 10
adb exec-out screencap -p > smoke-results/game-later.png
adb shell pidof "$PACKAGE:game"
python3 - <<'PYVERIFY'
from PIL import Image
from pathlib import Path
valid = []
for path in Path('smoke-results').glob('game*.png'):
    image = Image.open(path).convert('RGB')
    w, h = image.size
    crop = image.crop((w//5, h//5, w*4//5, h*3//5))
    colors = crop.getcolors(w*h)
    contrast = max(hi-lo for lo,hi in crop.getextrema())
    print(path.name, 'colors', len(colors or []), 'contrast', contrast)
    if colors and len(colors) >= 3 and contrast > 40: valid.append(path.name)
assert valid, 'No rendered game content across captured frames'
print('PASS: game process remains alive across startup, held touch and native menu')
PYVERIFY
