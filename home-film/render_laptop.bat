@echo off
rem Home - render scenes on the laptop with EEVEE (frames that already exist are skipped, so you can stop and resume).
rem Usage:  render_laptop.bat 01 02 03      (no arguments = all 16 scenes)
rem Change BLENDER below if Blender is installed somewhere else. PERCENT 67 = 720x1280.
set BLENDER="C:\Program Files\Blender Foundation\Blender 5.3\blender.exe"
set PERCENT=67
set STEP=1
cd /d "%~dp0"
set LIST=%*
if "%LIST%"=="" set LIST=01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16
for %%S in (%LIST%) do (
  for %%F in (scene%%S_*.py) do (
    echo === scene %%S: %%F ===
    %BLENDER% -b --python %%F -- --engine eevee --percent %PERCENT% --frames 1-9999x%STEP% --out renders\scene%%S --nosave
  )
)
echo Done. Make the video with:  python make_preview.py film out\home_film.mp4 renders --song "path\to\song.mp3"
pause
