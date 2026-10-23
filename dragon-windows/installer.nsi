; Dragon setup: installs for the current user (no admin), adds Desktop and Start menu shortcuts with the eye icon,
; and registers an uninstaller in Settings > Apps. Progress data in %LOCALAPPDATA%\Dragon is left alone.
; Build: makensis -DSRC=bin/Release -DOUT=Dragon-Setup.exe installer.nsi
Unicode true
!include "MUI2.nsh"

!define APP "Dragon"
!define VERSION "5.6.0"
!define UNINST "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP}"

Name "${APP}"
OutFile "${OUT}"
InstallDir "$LOCALAPPDATA\Programs\${APP}"
RequestExecutionLevel user
SetCompressor /SOLID lzma
BrandingText "${APP} ${VERSION}"

!define MUI_ICON "dragon.ico"
!define MUI_UNICON "dragon.ico"
!define MUI_FINISHPAGE_RUN "$INSTDIR\Dragon.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Start Dragon now"
!define MUI_FINISHPAGE_TEXT "Dragon is on your desktop and in the Start menu.$\r$\n$\r$\nTo keep it on the taskbar: start Dragon, right-click its eye icon in the taskbar and choose Pin to taskbar."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"

Section "Install"
  ; close a running Dragon so its files can be replaced on an update
  nsExec::Exec 'taskkill /IM Dragon.exe /F'
  Sleep 500
  SetOutPath "$INSTDIR"
  File /r "${SRC}\*.*"
  File "dragon.ico"
  CreateShortCut "$DESKTOP\${APP}.lnk" "$INSTDIR\Dragon.exe" "" "$INSTDIR\dragon.ico" 0
  CreateShortCut "$SMPROGRAMS\${APP}.lnk" "$INSTDIR\Dragon.exe" "" "$INSTDIR\dragon.ico" 0
  WriteUninstaller "$INSTDIR\Uninstall Dragon.exe"
  WriteRegStr HKCU "${UNINST}" "DisplayName" "${APP}"
  WriteRegStr HKCU "${UNINST}" "DisplayVersion" "${VERSION}"
  WriteRegStr HKCU "${UNINST}" "Publisher" "Valdek"
  WriteRegStr HKCU "${UNINST}" "DisplayIcon" "$INSTDIR\dragon.ico"
  WriteRegStr HKCU "${UNINST}" "InstallLocation" "$INSTDIR"
  WriteRegStr HKCU "${UNINST}" "UninstallString" '"$INSTDIR\Uninstall Dragon.exe"'
  WriteRegDWORD HKCU "${UNINST}" "NoModify" 1
  WriteRegDWORD HKCU "${UNINST}" "NoRepair" 1
SectionEnd

Section "Uninstall"
  nsExec::Exec 'taskkill /IM Dragon.exe /F'
  Sleep 500
  Delete "$DESKTOP\${APP}.lnk"
  Delete "$SMPROGRAMS\${APP}.lnk"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKCU "${UNINST}"
SectionEnd
