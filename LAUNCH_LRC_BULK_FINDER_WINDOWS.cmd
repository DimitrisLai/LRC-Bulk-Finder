@echo off
setlocal
title LRC Bulk Finder v2.9.3 - Windows Launcher
set "APP=%~dp0LRC_Control_Center.exe"
if not exist "%APP%" (
    echo ERROR: LRC_Control_Center.exe is missing.
    echo.
    echo Please extract the ENTIRE official Windows Standalone ZIP into ONE folder.
    echo This launcher, the GUI EXE, and LRC_Bulk_Finder_Worker.exe must be together.
    pause
    exit /b 2
)
if not exist "%~dp0LRC_Bulk_Finder_Worker.exe" (
    echo ERROR: LRC_Bulk_Finder_Worker.exe is missing from the same folder.
    echo.
    echo Please extract the ENTIRE official Windows Standalone ZIP.
    pause
    exit /b 2
)
start "" "%APP%"
exit /b 0
