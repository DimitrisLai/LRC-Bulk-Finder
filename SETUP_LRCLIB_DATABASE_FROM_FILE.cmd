@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title LRC Bulk Finder - Offline LRCLIB Setup
chcp 65001 >nul 2>&1
echo ==========================================
echo  OPTIONAL OFFLINE LRCLIB DATABASE SETUP
 echo ==========================================
where py >nul 2>&1
if not errorlevel 1 (
  py -3 "%~dp0setup_lrclib_database.py"
) else (
  python "%~dp0setup_lrclib_database.py"
)
echo.
pause
endlocal
