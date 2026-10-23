# Dragon for Windows

A small Windows app (C#, WinForms, Edge WebView2, .NET Framework 4.8; all built into Windows 10/11):

- left: the Dragon app from `../launchpad/index.html`, served as `https://dragon.example` so its storage persists
- right: a training browser. Links from Dragon open here, sign-ins persist, and it reopens the last page
  on the next start. Ctrl+T hides or shows it.

Window size, split position and the last training page are saved in `%LOCALAPPDATA%\Dragon\window.json`.

Build (works on Linux too, thanks to `EnableWindowsTargeting`):

    cp ../launchpad/index.html ../launchpad/favicon-32.png ../launchpad/apple-touch-icon.png app/
    dotnet build -c Release

Ship `bin/Release` (without the .pdb) as a zip.
