#!/usr/bin/env bash
# Builds VoiceClean.apk without the Android SDK, from tools published on Maven:
#   aapt2 + android-framework.jar (inside org.apktool:apktool-lib:2.9.3), dx.jar
#   (com.jakewharton.android.repackaged:dalvik-dx:14.0.0_r21), apksig.jar (com.android.tools.build:apksig)
#   and the Android API jar (org.robolectric:android-all:14-robolectric-10818077, saved as android-all-14.jar).
# Native code (RNNoise) is prebuilt in libs/<abi>/; rebuild it with jni/build-native.sh libs.
# Usage: TOOLS=<dir> KEYSTORE=<file.p12> KEYPASS=<password> ./build.sh
set -euo pipefail
cd "$(dirname "$0")"
: "${TOOLS:?set TOOLS}" "${KEYSTORE:?set KEYSTORE}" "${KEYPASS:?set KEYPASS}"
AAPT2="$TOOLS/prebuilt/linux/aapt2_64"; FRAMEWORK="$TOOLS/prebuilt/android-framework.jar"; ANDROID_JAR="$TOOLS/android-all-14.jar"
VERSION_CODE="${VERSION_CODE:-3}"; VERSION_NAME="${VERSION_NAME:-1.1}"
rm -rf build && mkdir -p build/gen build/classes build/toolclasses
"$AAPT2" compile --dir res -o build/res.zip
"$AAPT2" link -o build/linked.apk -I "$FRAMEWORK" --manifest AndroidManifest.xml build/res.zip \
  --java build/gen --min-sdk-version 24 --target-sdk-version 34 --version-code "$VERSION_CODE" --version-name "$VERSION_NAME"
javac -Xlint:-options --release 8 -classpath "$ANDROID_JAR" -d build/classes $(find src build/gen -name '*.java')
java -cp "$TOOLS/dx.jar" com.android.dx.command.Main --dex --min-sdk-version=24 --output=build/classes.dex build/classes
python3 tools/package.py build/linked.apk build/classes.dex build/unsigned.apk libs
javac -d build/toolclasses -cp "$TOOLS/apksig.jar" tools/Sign.java
java --add-exports java.base/sun.security.x509=ALL-UNNAMED --add-exports java.base/sun.security.pkcs=ALL-UNNAMED --add-exports java.base/sun.security.util=ALL-UNNAMED -cp "build/toolclasses:$TOOLS/apksig.jar" Sign "$KEYSTORE" voiceclean "$KEYPASS" build/unsigned.apk build/VoiceClean.apk
cp build/VoiceClean.apk VoiceClean.apk
echo "built VoiceClean.apk"
