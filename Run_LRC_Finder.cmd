@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
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
  echo ERROR: Python 3.10+ not found. Install from https://www.python.org/downloads/
  exit /b 10
)
echo Python:
%PY% --version
if errorlevel 1 exit /b 11
%PY% -c "import mutagen, unidecode, syncedlyrics" >nul 2>&1
if errorlevel 1 (
  echo Installing required Python packages: mutagen Unidecode syncedlyrics
  %PY% -m pip install --user --disable-pip-version-check --timeout 15 --retries 1 mutagen Unidecode syncedlyrics
  if errorlevel 1 (
    echo ERROR: Required package installation failed.
    exit /b 12
  )
)
echo Checking program syntax...
%PY% -m py_compile "%~dp0LRC_Bulk_Finder.py" "%~dp0g2g_integration.py"
if errorlevel 1 exit /b 13
echo.
echo Optional Greek AI: install once using SETUP_GREEK_AI.cmd
%PY% -u "%~dp0LRC_Bulk_Finder.py"
set "RESULT=%errorlevel%"
exit /b %RESULT%
