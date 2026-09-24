#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$1" && pwd)"
TEST_DIR="$(cd "$(dirname "$0")" && pwd)"
NTR="$ROOT/subprojects/libntr"
OUT="${TMPDIR:-/tmp}/platinum-display-tests"
mkdir -p "$OUT"
args=(-O2 -w -DSDK_PORT -DSDK_BUILD_ANDROID -DSDK_ARM9 -DSDK_FINALROM -DNNS_FINALROM -DSDK_VERSION_MAJOR=4 -DSDK_TS '-DATTRIBUTE_ALIGN(x)=__attribute__((aligned(x)))' -I"$OUT/include" -I"$NTR/include" -I"$NTR/libraries/sim/include" -I"$TEST_DIR/../performance")
gcc -std=gnu11 "${args[@]}" -DSIM_crc32buf=baseline_crc32buf -DSIM_updateCRC32=baseline_updateCRC32 -c "$ROOT/tools/android/reference_crc32.c" -o "$OUT/crc-old.o"
gcc -std=gnu11 "${args[@]}" -c "$NTR/libraries/sim/src/sim_crc32.c" -o "$OUT/crc-fast.o"
gcc -std=gnu11 "${args[@]}" "$TEST_DIR/performance_crc_test.c" "$OUT/crc-old.o" "$OUT/crc-fast.o" -o "$OUT/crc"
"$OUT/crc"
g++ -std=c++11 "${args[@]}" "$TEST_DIR/performance_stream_test.cpp" -o "$OUT/stream"
"$OUT/stream"
gcc -std=c11 "${args[@]}" "$TEST_DIR/performance_visibility_test.c" -o "$OUT/visibility"
"$OUT/visibility"
# Compile the real Android quad implementation, including the PC code below its branch.
gcc -std=gnu11 "${args[@]}" -fsyntax-only "$NTR/libraries/sim/src/sim_screenquads.c"
