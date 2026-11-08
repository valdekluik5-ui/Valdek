#!/usr/bin/env bash
# Builds libvoiceclean.so (RNNoise 0.2 + JNI bridge) for Android with plain clang + lld, no NDK:
# the code only needs a few libc/libm functions, declared in jni/sysroot, and links against stub
# libc.so/libm.so so the real ones on the phone are used at run time.
# Usage: RNNOISE=<rnnoise-0.2 source dir> JDK_INCLUDE=<jdk>/include ./jni/build-native.sh <out dir, e.g. $PWD/libs>
set -euo pipefail
cd "$(dirname "$0")"
: "${RNNOISE:?set RNNOISE}" "${JDK_INCLUDE:?set JDK_INCLUDE}"
OUT="$(mkdir -p "$1" && cd "$1" && pwd)"
SRC="denoise rnn pitch kiss_fft celt_lpc nnet nnet_default parse_lpcnet_weights rnnoise_data rnnoise_tables"
SYMS="malloc calloc realloc free abort abs memcpy memmove memset memcmp strlen strcmp fopen fclose fread fwrite fseek ftell printf fprintf"
MSYMS="sqrt sqrtf exp expf log logf log10 log10f pow powf sin sinf cos cosf tanh tanhf atan atanf floor floorf ceil ceilf fabs fabsf lrint lrintf fmax fmaxf fmin fminf"
build() {  # <abi> <clang target> <extra flags>
  local abi=$1 target=$2; shift 2
  local tmp; tmp=$(mktemp -d)
  local cflags=(--target="$target" -O3 -fPIC -fvisibility=hidden -ffunction-sections -fdata-sections -fno-stack-protector
    -nostdinc -isystem "$(clang -print-resource-dir)/include" -isystem sysroot/include -isystem "$JDK_INCLUDE" -isystem "$JDK_INCLUDE/linux"
    -I. -I"$RNNOISE/include" -I"$RNNOISE/src" "$@")
  for f in $SRC; do clang "${cflags[@]}" -c "$RNNOISE/src/$f.c" -o "$tmp/$f.o"; done
  clang "${cflags[@]}" -c voiceclean_jni.c -o "$tmp/jni.o"
  case "$abi" in armeabi-v7a) clang "${cflags[@]}" -fno-builtin -c aeabi.c -o "$tmp/aeabi.o" ;; esac
  # stub libraries: same names as the phone's, only so the linker records the dependency
  printf '%s\n' $SYMS | sed 's/.*/void &(void){}/' > "$tmp/c.c"
  printf '%s\n' $MSYMS | sed 's/.*/void &(void){}/' > "$tmp/m.c"
  clang --target="$target" -fno-builtin -nostdlib -shared -fuse-ld=lld -Wl,-soname,libc.so "$tmp/c.c" -o "$tmp/libc.so"
  clang --target="$target" -fno-builtin -nostdlib -shared -fuse-ld=lld -Wl,-soname,libm.so "$tmp/m.c" -o "$tmp/libm.so"
  mkdir -p "$OUT/$abi"
  clang --target="$target" -nostdlib -shared -fuse-ld=lld -Wl,-soname,libvoiceclean.so -Wl,--gc-sections \
    -Wl,--hash-style=both -Wl,-z,max-page-size=16384 -Wl,-z,noexecstack -Wl,--no-undefined -Wl,--build-id \
    "$tmp"/*.o -L"$tmp" -lm -lc ${EXTRA_LIBS:-} -o "$OUT/$abi/libvoiceclean.so"
  rm -rf "$tmp"
  echo "built $OUT/$abi/libvoiceclean.so"
}
build arm64-v8a aarch64-linux-android24
build armeabi-v7a armv7a-linux-androideabi24 -mfpu=neon -mfloat-abi=softfp -mthumb
# x86_64 (emulators) is left out to keep the APK small; the app falls back to the Java engine there
# build x86_64 x86_64-linux-android24
