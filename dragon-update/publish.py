#!/usr/bin/env python3
"""Puts the current Dragon pages into the update channel (this folder).

Both apps check https://raw.githubusercontent.com/valdekluik5-ui/Valdek/main/dragon-update/version.json,
so an update goes live when this folder reaches the main branch.

    python3 dragon-update/publish.py [--min-native 5.9]

--min-native is the oldest installed app (Dragon-Setup.exe / Dragon.apk) that can run these pages; raise it
only when a change also needs a new native app, so older installs wait for a reinstall instead of breaking.
"""
import hashlib, json, re, shutil, sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
here = root / 'dragon-update'
files = [root / 'launchpad/index.html', root / 'dragon-windows/browser.html', root / 'dragon-windows/newtab.html']
min_native = sys.argv[sys.argv.index('--min-native') + 1] if '--min-native' in sys.argv else '5.9'

version = re.search(r"const APP_VERSION='([\d.]+)'", files[0].read_text()).group(1)
sums = {}
for f in files:
    shutil.copyfile(f, here / f.name)
    sums[f.name] = hashlib.sha256(f.read_bytes()).hexdigest()
(here / 'version.json').write_text(json.dumps({'version': version, 'minNative': min_native, 'files': sums}, indent=2) + '\n')
print(f'update channel now holds Dragon {version} (needs app {min_native} or newer)')
