@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title LRC Bulk Finder - Official Offline Database Installer
chcp 65001 >nul 2>&1
echo ===========================================
echo  LRCLIB OFFLINE DATABASE - AUTO INSTALLER
echo ===========================================
where py >nul 2>&1
if not errorlevel 1 (
  py -3 "%~dp0auto_install_lrclib_database.py"
) else (
  python "%~dp0auto_install_lrclib_database.py"
)
echo.
pause
endlocal
