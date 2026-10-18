@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
chcp 65001 >nul 2>&1
title Link Existing LRCLIB Offline Database v2.1.15
echo ======================================================
echo  CONNECT EXISTING LRCLIB DATABASE - NO RE-DOWNLOAD
echo ======================================================
where py >nul 2>&1
if not errorlevel 1 (
  py -3 "%~dp0connect_existing_lrclib_database.py"
) else (
  python "%~dp0connect_existing_lrclib_database.py"
)
echo.
pause
endlocal
