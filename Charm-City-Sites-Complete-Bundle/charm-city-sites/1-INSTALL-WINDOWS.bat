@echo off
title Charm City Sites - Windows Installer
cd /d "%~dp0"

echo ============================================================
echo  CHARM CITY SITES - INSTALL ON WINDOWS
echo  Puts the whole factory inside your laptop's built-in Linux
echo  side - WSL. Windows may restart ONCE for this. After that,
echo  the same kit that runs on a Mac runs here, unchanged.
echo ============================================================
echo.

if not exist "%~dp0windows\wsl-install.sh" (
  echo This file must run from the extracted kit folder.
  echo Extract charm-city-sites-kit.zip fully first, then run this again.
  pause
  exit /b 1
)

REM ---- ask for Administrator once, for the Linux-layer setup ----
net session >nul 2>&1
if %errorlevel% neq 0 goto elevate
goto main

:elevate
echo Asking for Administrator permission once - it turns on the
echo built-in Linux layer of Windows. A new window will open;
echo this one closes.
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b 0

:main
REM ---- 1. does Windows know WSL at all? ----
where wsl >nul 2>&1
if %errorlevel% neq 0 goto legacy_enable
goto distro_check

:legacy_enable
echo The Linux layer is not enabled yet. Turning it on now -
echo Windows will want to RESTART afterwards. Once, ever.
dism /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
echo.
echo 1. Restart the laptop if Windows asks.
echo 2. Run this file again.
echo.
echo If the messages above mention virtualization being disabled in
echo firmware: enable VT-x - Intel - or SVM - AMD - in your BIOS first,
echo then restart and re-run.
pause
exit /b 0

:distro_check
set "DISTRO="
for %%D in (Ubuntu-24.04 Ubuntu-22.04 Ubuntu) do (
  if not defined DISTRO wsl -d %%D -u root -- /bin/true >nul 2>&1 && set "DISTRO=%%D"
)
if defined DISTRO goto ready
echo No Linux distro installed yet. Installing Ubuntu now - this can
echo take a few minutes. A purple window may open and ask for a Linux
echo username: you can simply CLOSE it with the X - the installer sets
echo up its own hidden user automatically.
wsl --install -d Ubuntu-24.04
echo.
echo If Windows asked to restart: restart, then run this file again.
echo If it did not: wait about a minute for Ubuntu to finish setting up,
echo then run this file again.
pause
exit /b 0

:ready
echo Linux side detected: %DISTRO%
echo.
echo Step 1 of 3 - staging the kit inside Linux, about a minute...
wsl -d %DISTRO% -u root -- bash -c "useradd -m ccs 2>/dev/null; SRC=$(wslpath '%~dp0'); mkdir -p /home/ccs/charm-city-sites && cp -a \"$SRC/windows\" /home/ccs/charm-city-sites/ && echo KIT_STAGED"
if %errorlevel% neq 0 goto stage_fail
echo Step 2 of 3 - copying the full kit inside Linux...
wsl -d %DISTRO% -u root -- bash /home/ccs/charm-city-sites/windows/sync_kit.sh "%~dp0"
echo Step 3 of 3 - installing the factory inside Linux, 10 to 15 minutes.
echo Mostly downloads. One question may appear - your Google Sheet URL.
echo Press Enter to skip it if you are unsure; it can be wired later.
echo ................................................................
wsl -d %DISTRO% -u root -- bash /home/ccs/charm-city-sites/windows/wsl-install.sh
echo ................................................................
echo.
echo INSTALL FINISHED - opening the control panel.
echo First visit: create the n8n owner login - any email + password,
echo it stays on your laptop.
echo Next: open WINDOWS.md in this folder for the remaining one-time
echo paste-ins - same as OPERATIONS.md Part 1, about 45 minutes.
start "" http://localhost:5678
echo The first page load can take up to a minute - refresh once.
pause
exit /b 0

:stage_fail
echo Staging failed. The usual cause: running from inside the zip
echo preview, or the kit folder was moved while installing.
echo Extract charm-city-sites-kit.zip fully, then run this file again.
pause
exit /b 1
