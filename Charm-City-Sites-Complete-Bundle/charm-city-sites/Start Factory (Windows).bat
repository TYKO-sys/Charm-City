@echo off
title Charm City Sites - Start Factory
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

echo Waking the factory - brain, spine and all. About 30 seconds...
wsl -d %DISTRO% -u root -- bash /home/ccs/charm-city-sites/scripts/keep_alive_wsl.sh
echo.
echo FACTORY STATUS
echo ------------------------------------------------------------
wsl -d %DISTRO% -u ccs -- bash -lc "bash /home/ccs/charm-city-sites/scripts/status.sh"
echo ------------------------------------------------------------
echo Opening the control panel - the first load may need one refresh.
start "" http://localhost:5678
echo.
echo The heartbeat task re-checks everything every 5 minutes on its own.
pause
