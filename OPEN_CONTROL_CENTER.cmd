@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title LRC Bulk Finder v2.4.3 - Control Center
set "PYTHONUTF8=1"
set "PY="
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
  if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
  where python >nul 2>&1
  if not errorlevel 1 (
    python -c "import sys; assert sys.version_info >= (3,10)" >nul 2>&1
    if not errorlevel 1 set "PY=python"
  )
)
if not defined PY (
  echo ERROR: Python 3.10+ is required. Install from https://www.python.org/downloads/
  pause
  exit /b 10
)
%PY% -c "import tkinter,mutagen,unidecode,syncedlyrics" >nul 2>&1
if errorlevel 1 (
  echo Installing or checking required packages...
  %PY% -m pip install --user --disable-pip-version-check --timeout 15 --retries 1 mutagen Unidecode syncedlyrics
  if errorlevel 1 (echo ERROR: Dependencies unavailable.&pause&exit /b 12)
)
echo Opening LRC Bulk Finder v2.4.3 Control Center...
%PY% -u "%~dp0LRC_Control_Center.py"
if errorlevel 1 (
  echo Control Center failed. Check Python installation and Run_Diagnostics.cmd.
  pause
  exit /b 13
)
endlocal
