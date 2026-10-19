@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title LRC Bulk Finder Public v2.1.18
chcp 65001 >nul 2>&1
echo ==========================================
echo  LRC BULK FINDER - PUBLIC EDITION v2.1.18
echo ==========================================
echo Keep this window open until the run finishes.
echo.
call "%~dp0Run_LRC_Finder.cmd"
set "RESULT=%errorlevel%"
echo.
echo ------------------------------------------
echo Finished. Exit code: %RESULT%
echo If anything failed, run Run_Diagnostics.cmd.
echo ------------------------------------------
pause
endlocal
