@echo off
title Charm City Sites - Dashboard
cd /d "%~dp0"

set "DISTRO="
for %%D in (Ubuntu-24.04 Ubuntu-22.04 Ubuntu) do (
  if not defined DISTRO wsl -d %%D -u root -- /bin/true >nul 2>&1 && set "DISTRO=%%D"
)
if not defined DISTRO (
  echo No Linux side found. Run 1-INSTALL-WINDOWS.bat first.
  pause
  exit /b 1
)

echo FACTORY STATUS
echo ------------------------------------------------------------
wsl -d %DISTRO% -u ccs -- bash -lc "bash /home/ccs/charm-city-sites/scripts/status.sh"
echo ------------------------------------------------------------
echo Opening the control panel...
start "" http://localhost:5678
echo.
echo If something shows DOWN, double-click "Start Factory (Windows).bat"
echo to wake everything, then check again.
pause
