# Dragon for Windows

A small Windows app (C#, WinForms, Edge WebView2, .NET Framework 4.8; all built into Windows 10/11):

- left: the Dragon app from `../launchpad/index.html`, served as `https://dragon.example` so its storage persists
- right: a training browser. Links from Dragon open here, sign-ins persist, and it reopens the last page
  on the next start. Ctrl+T hides or shows it.
- EN: shows a site in English through Google Translate; the choice is remembered per site.
- Price ₴: a price-check panel. It reads the product name from the page and searches new prices
  (Hotline.ua, Rozetka) and used ones (OLX, eBay sold items); a 60% rule calculator gives the max buy price.

Window size, split position and the last training page are saved in `%LOCALAPPDATA%\Dragon\window.json`.

Build (works on Linux too, thanks to `EnableWindowsTargeting`):

    cp ../launchpad/index.html ../launchpad/favicon-32.png ../launchpad/apple-touch-icon.png app/
    dotnet build -c Release

Installer (NSIS, also runs on Linux): copy `bin/Release` without the .pdb to a folder, then

    makensis -DSRC=<that folder> -DOUT=Dragon-Setup.exe installer.nsi

Setup installs to `%LOCALAPPDATA%\Programs\Dragon` without admin rights, adds Desktop and Start menu shortcuts
with the eye icon and an uninstaller. If the page does not appear within 12 s, Dragon offers safe graphics
mode (GPU off), remembered in `%LOCALAPPDATA%\Dragon\safe-graphics`. Errors go to `%LOCALAPPDATA%\Dragon\dragon.log`.
