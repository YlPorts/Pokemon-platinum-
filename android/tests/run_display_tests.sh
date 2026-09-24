#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$1" && pwd)"
TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT="${TMPDIR:-/tmp}/platinum-display-tests"
NTR="$ROOT/subprojects/libntr"
mkdir -p "$OUT/include/nitro/fx"
ln -sfn "$ROOT/third_party/SDL/include" "$OUT/include/SDL2"
python3 "$NTR/gen/nitro/fx/gen_fx_const.py" "$NTR/gen/nitro/fx/fx_const.csv" "$OUT/include/nitro/fx/fx_const.h"
gcc -std=c11 -I"$TEST_DIR/../display" "$TEST_DIR/display_layout_test.c" -lm -o "$OUT/layout"
"$OUT/layout"
gcc -std=gnu11 -w -DSDK_PORT -DSDK_BUILD_ANDROID -DSDK_ARM9 -DSDK_FINALROM -DNNS_FINALROM -DSDK_VERSION_MAJOR=4 -DSDK_TS \
 '-DATTRIBUTE_ALIGN(x)=__attribute__((aligned(x)))' -ffunction-sections -fdata-sections \
 -I"$OUT/include" -I"$NTR/include" -I"$TEST_DIR/../display" \
 "$TEST_DIR/display_touch_test.c" -Wl,--gc-sections -lm -o "$OUT/touch"
"$OUT/touch"
gcc -std=c11 -I"$TEST_DIR/../display" "$TEST_DIR/display_policy_test.c" -o "$OUT/policy"
"$OUT/policy"
g++ -std=c++11 -I"$TEST_DIR/../display" "$TEST_DIR/display_cache_test.cpp" -o "$OUT/cache"
"$OUT/cache"
