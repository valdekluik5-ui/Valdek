# Dragon update channel

Both apps (Windows and Android) read `version.json` here from the **main** branch when they start
(Windows also checks every 6 hours). When it names a newer version, they download the listed pages in the
background, check each one against its SHA-256 sum, and switch to them at the next start. The pages keep the
same address inside the app, so progress, notes, PIN and sync settings are untouched.

To publish an update:

1. Change `launchpad/index.html` (and raise `APP_VERSION`) and/or `dragon-windows/browser.html`, `newtab.html`.
2. Run `python3 dragon-update/publish.py`.
3. Merge to `main`. The apps pick it up on their next start.

Only the pages update this way. A change to the Windows or Android app itself (C#/Java) still needs a new
Dragon-Setup.exe or Dragon.apk; give `publish.py --min-native X` so older installs skip pages they cannot run.
