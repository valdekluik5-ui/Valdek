# Valdek

Projects built with Claude.

- `quiet-moon/` — Quiet Moon app, live at https://valdekluik5-ui.github.io/Valdek/quiet-moon/
  (GitHub Pages: deploy from branch `main`, folder `/ (root)`)
- Suffler (teleprompter app) has moved to its own repository: https://github.com/valdekluik5-ui/V
  (live at https://valdekluik5-ui.github.io/V/)
- `launchpad/` — Dragon, a personal earning-path tracker (income, fix & sell, apps, Cyber Shift program)
- `launchpad-android/` — Dragon as an Android app (APK), built with `build.sh`
- `dragon-windows/` — Dragon for Windows: the app plus a training browser pane, built with `dotnet build`

## Sync, backups and updates (5.9)

- **Sync and backup:** Settings → Sync connects Dragon to a private GitHub repository of your own. Data is
  encrypted twice on the device (AES-256-GCM, two keys from your sync password) before upload; every sync
  is kept in that repository's history and can be restored from Settings → Backups.
- **Updates:** see [`dragon-update/`](dragon-update/README.md).
