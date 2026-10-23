# Dragon for Windows

A small Windows app (C#, WinForms, Edge WebView2, .NET Framework 4.8; all built into Windows 10/11):

- left: the Dragon app from `../launchpad/index.html`, served as `https://dragon.example` so its storage persists
- right: a tabbed browser. Its bar (`browser.html`: tabs, address, price bar, styled in Dragon's current look)
  is a small page that talks to the app; new tabs open `newtab.html`. Links from Dragon open in tabs, sign-ins
  persist, and the tabs reopen on the next start. Ctrl+T new tab, Ctrl+W close, Ctrl+L address, Ctrl+B hide or show
  the browser, F11 full screen.
- EN: translates Cyrillic text inside the page to English (the app calls Google's translate endpoint), so the site
  keeps working; new text is translated as it appears. Remembered per site.
- Price bar: on a listing page a bar appears by itself with the asking price, the typical good-condition used
  price on OLX (cheapest quarter dropped), the new price on Hotline.ua, the 60% max buy and a verdict; euros use
  the National Bank of Ukraine rate. Lookups run in a hidden browser and are cached per product.

Window size, split position and the last training page are saved in `%LOCALAPPDATA%\Dragon\window.json`.

Build (works on Linux too, thanks to `EnableWindowsTargeting`):

    cp ../launchpad/index.html ../launchpad/favicon-32.png ../launchpad/apple-touch-icon.png browser.html newtab.html app/
    dotnet build -c Release

Installer (NSIS, also runs on Linux): copy `bin/Release` without the .pdb to a folder, then

    makensis -DSRC=<that folder> -DOUT=Dragon-Setup.exe installer.nsi

Setup installs to `%LOCALAPPDATA%\Programs\Dragon` without admin rights, adds Desktop and Start menu shortcuts
with the eye icon and an uninstaller. If the page does not appear within 12 s, Dragon offers safe graphics
mode (GPU off), remembered in `%LOCALAPPDATA%\Dragon\safe-graphics`. Errors go to `%LOCALAPPDATA%\Dragon\dragon.log`.
