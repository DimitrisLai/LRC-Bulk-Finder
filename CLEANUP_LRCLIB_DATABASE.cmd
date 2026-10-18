@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title LRC Bulk Finder - Offline LRCLIB Database Cleanup
chcp 65001 >nul 2>&1
echo ======================================================
echo  OFFLINE LRCLIB CLEANUP - SAFE, CONFIRMATION REQUIRED
 echo ======================================================
where py >nul 2>&1
if not errorlevel 1 (
  py -3 "%~dp0cleanup_lrclib_database.py"
) else (
  python "%~dp0cleanup_lrclib_database.py"
)
echo.
pause
endlocal
