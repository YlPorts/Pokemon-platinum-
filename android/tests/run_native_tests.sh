#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$1" && pwd)"
TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD="${TMPDIR:-/tmp}/platinum-native-tests"
mkdir -p "$BUILD"
NTR="$ROOT/subprojects/libntr"
NNS="$ROOT/subprojects/libntrsystem"
mkdir -p "$BUILD/include/nitro/fx"
if [[ -d "$ROOT/third_party/SDL/include" ]]; then
    ln -sfn "$ROOT/third_party/SDL/include" "$BUILD/include/SDL2"
fi
python3 "$NTR/gen/nitro/fx/gen_fx_const.py" "$NTR/gen/nitro/fx/fx_const.csv" "$BUILD/include/nitro/fx/fx_const.h"
SOURCES=("$TEST_DIR/native_runtime_test.c"
    "$NNS/libraries/snd/src/heap.c" "$NNS/libraries/snd/src/sndarc.c"
    "$NNS/libraries/snd/src/player.c" "$NNS/libraries/snd/src/sndarc_player.c"
    "$NNS/libraries/snd/src/fader.c"
    "$NNS/libraries/fnd/src/frameheap.c" "$NNS/libraries/fnd/src/list.c"
    "$NNS/libraries/fnd/src/expheap.c"
    "$NNS/libraries/fnd/src/heapcommon.c")
FLAGS=(-std=gnu11 -g -O1 -w -DSDK_PORT -DSDK_BUILD_ANDROID -DSDK_ARM9
    -DSDK_FINALROM -DNNS_FINALROM -DSDK_VERSION_MAJOR=4 -DSDK_TS
    '-DATTRIBUTE_ALIGN(x)=__attribute__((aligned(x)))'
    -ffunction-sections -fdata-sections -I"$BUILD/include" -I"$NTR/include" -I"$NNS/include" -I"$NNS/libraries/fnd/include")
"${CC:-gcc}" "${FLAGS[@]}" -fsanitize=address,undefined -fno-sanitize-recover=all \
    "${SOURCES[@]}" -Wl,--gc-sections -o "$BUILD/native-runtime-test"
ASAN_OPTIONS="${ASAN_OPTIONS:-detect_leaks=1}" "$BUILD/native-runtime-test" "${SDAT_PATH:-$ROOT/build_android/res/sound/pl_sound_data.sdat}"
if command -v aarch64-linux-gnu-gcc >/dev/null && command -v qemu-aarch64 >/dev/null; then
    aarch64-linux-gnu-gcc "${FLAGS[@]}" "${SOURCES[@]}" -Wl,--gc-sections -o "$BUILD/native-runtime-arm64"
    qemu-aarch64 -L /usr/aarch64-linux-gnu "$BUILD/native-runtime-arm64" "${SDAT_PATH:-$ROOT/build_android/res/sound/pl_sound_data.sdat}"
fi
