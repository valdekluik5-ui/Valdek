# Dragon for Android

A full-screen Android app (Dragon) around `../launchpad/index.html`. The page ships inside the APK, and progress,
notes and the PIN are kept in the app's own storage on the phone.

Build (no Android SDK needed; the tools come from Maven Central, see `build.sh`):

    TOOLS=<tools dir> KEYSTORE=launchpad.p12 KEYPASS=<password> ./build.sh

Updates must be signed with the same keystore, or Android refuses to install them over the old app.
Bump `VERSION_CODE` for each update.
