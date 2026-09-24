#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$1" && pwd)"
APK="$ROOT/android/app/build/outputs/apk/debug/app-debug.apk"
PACKAGE=org.pokeplatinum.android
mkdir -p smoke-results
capture() {
    adb exec-out screencap -p > smoke-results/final.png || true
    adb logcat -d > smoke-results/logcat.txt || true
    adb shell run-as "$PACKAGE" cat files/game/android_runtime.log > smoke-results/runtime.txt || true
    adb shell run-as "$PACKAGE" cat files/game/android_performance.log > smoke-results/performance.txt || true
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
unit = min(w,h) * (.145 if w < h else .135)
print(round(w - unit*.72), round(h - unit*1.85))
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
# One-screen manual override and return to game-driven selection.
adb shell input tap 270 30
sleep 2
adb exec-out screencap -p > smoke-results/swapped.png
adb shell input tap 500 30
sleep 2
adb exec-out screencap -p > smoke-results/automatic.png
adb logcat -d > smoke-results/screen-policy.txt
rg -q 'Android screen: top' smoke-results/screen-policy.txt
rg -q 'Android screen: touch' smoke-results/screen-policy.txt

adb shell pidof "$PACKAGE:game"
# Rotate the actual running activity through the emulator accelerometer.
adb emu sensor set acceleration 9.8:0:0
sleep 12
adb exec-out screencap -p > smoke-results/landscape.png
adb shell pidof "$PACKAGE:game"
adb emu sensor set acceleration 0:9.8:0
sleep 12
adb exec-out screencap -p > smoke-results/portrait-return.png
adb shell pidof "$PACKAGE:game"
python3 - <<'PYROTATE'
from PIL import Image
p=Image.open('smoke-results/portrait-return.png'); l=Image.open('smoke-results/landscape.png')
assert p.height>p.width, ('portrait',p.size)
assert l.width>l.height, ('landscape',l.size)
print('PASS: rotation portrait -> landscape -> portrait in the same running game')
PYROTATE
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

# A separate file must survive the runtime log and contain actual timing samples.
adb shell run-as "$PACKAGE" cat files/game/android_performance.log > smoke-results/performance.txt
rg -q 'SESSION Android 0.3.6 GPU=' smoke-results/performance.txt
rg -q 'Android timing:.*compose=' smoke-results/performance.txt

# Enter the actual outdoor field in an isolated test build and fresh debug save.
adb shell am force-stop "$PACKAGE"
adb shell run-as "$PACKAGE" touch files/game/android_field_test
adb shell am start -n "$PACKAGE/.LauncherActivity"
sleep 5
bash /tmp/platinum-tap.sh
sleep 35
adb shell pidof "$PACKAGE:game"
adb exec-out screencap -p > smoke-results/field-before.png
adb shell input swipe 55 815 55 815 1500
sleep 8
adb exec-out screencap -p > smoke-results/field-after.png
adb shell run-as "$PACKAGE" cat files/game/android_runtime.log > smoke-results/field-runtime.txt
adb shell run-as "$PACKAGE" cat files/game/android_performance.log > smoke-results/field-performance.txt
rg -q 'Android field test: Twinleaf Town' smoke-results/field-runtime.txt
rg -q 'Android app:.*lists_cached=[1-9]' smoke-results/field-runtime.txt
python3 - <<'PYFIELD'
from PIL import Image
im=Image.open('smoke-results/field-before.png').convert('RGB')
w,h=im.size
area=im.crop((0,h//10,w,h*3//5))
green=sum(1 for r,g,b in area.getdata() if g>r*1.15 and g>b*1.05 and g>50)
assert green>3000, ('outdoor scene not rendered',green)
print('PASS: outdoor Twinleaf scene rendered with cached 3D commands')
PYFIELD
adb shell pidof "$PACKAGE:game"
