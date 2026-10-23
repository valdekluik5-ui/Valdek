#!/usr/bin/env bash
# Builds Launchpad.apk without the Android SDK, using tools published on Maven Central:
#   aapt2 + framework resources (org.apktool:apktool-lib), dx (com.jakewharton.android.repackaged:dalvik-dx
#   or com.google.android.tools:dx), apksig, and the Android API jar (org.robolectric:android-all).
# Usage: TOOLS=<dir with those jars> KEYSTORE=<file.p12> KEYPASS=<password> ./build.sh
set -euo pipefail
cd "$(dirname "$0")"
: "${TOOLS:?set TOOLS}" "${KEYSTORE:?set KEYSTORE}" "${KEYPASS:?set KEYPASS}"
AAPT2="$TOOLS/prebuilt/linux/aapt2"; FRAMEWORK="$TOOLS/prebuilt/android-framework.jar"; ANDROID_JAR="$TOOLS/android-all-14.jar"
VERSION_CODE="${VERSION_CODE:-1}"; VERSION_NAME="${VERSION_NAME:-1.0}"
rm -rf build && mkdir -p build/assets build/gen build/classes build/toolclasses
cp ../launchpad/index.html ../launchpad/favicon-32.png ../launchpad/apple-touch-icon.png build/assets/
"$AAPT2" compile --dir res -o build/res.zip
"$AAPT2" link -o build/linked.apk -I "$FRAMEWORK" --manifest AndroidManifest.xml -A build/assets build/res.zip \
  --java build/gen --min-sdk-version 24 --target-sdk-version 34 --version-code "$VERSION_CODE" --version-name "$VERSION_NAME"
javac -nowarn --release 8 -classpath "$ANDROID_JAR" -d build/classes \
  $(find src build/gen -name '*.java') 2>&1 | grep -v '^warning' || true
java -cp "$TOOLS/dx.jar" com.android.dx.command.Main --dex --min-sdk-version=24 --output=build/classes.dex build/classes
python3 tools/package.py build/linked.apk build/classes.dex build/unsigned.apk
javac -d build/toolclasses -cp "$TOOLS/apksig.jar" tools/Sign.java
java --add-exports java.base/sun.security.x509=ALL-UNNAMED --add-exports java.base/sun.security.pkcs=ALL-UNNAMED --add-exports java.base/sun.security.util=ALL-UNNAMED -cp "build/toolclasses:$TOOLS/apksig.jar" Sign "$KEYSTORE" launchpad "$KEYPASS" build/unsigned.apk build/Launchpad.apk
echo "built build/Launchpad.apk"
