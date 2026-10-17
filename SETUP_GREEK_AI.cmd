@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title Optional Greeklish G2G AI Setup
chcp 65001 >nul 2>&1
set "PYTHONUTF8=1"
echo ==============================================
echo    OPTIONAL GREEKLISH-TO-GREEK AI MODEL
 echo ==============================================
echo.
echo This can download roughly 1.2 GB plus dependencies.
echo It uses the gr-nlp-toolkit package and the model cache.
echo The AI is NOT required for international/non-Greek music.
echo.
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
  echo ERROR: Python 3.10+ not found.
  goto finish
)
echo Selected Python:
%PY% --version
echo.
choice /C YN /N /M "Install or verify gr-nlp-toolkit and download/test G2G? [Y/N] "
if errorlevel 2 goto finish
echo.
echo Installing toolkit (already installed packages normally stay in place)...
%PY% -m pip install --disable-pip-version-check gr-nlp-toolkit
if errorlevel 1 (
  echo ERROR: Toolkit install failed. See message above.
  goto finish
)
echo.
echo Preparing the model. First run may take a long time...
%PY% -c "from gr_nlp_toolkit import Pipeline; nlp = Pipeline('g2g'); print(nlp('O Volos kai h Larisa einai sth Thessalia').text)"
if errorlevel 1 (
  echo ERROR: Model initialization/test failed. See message above.
  goto finish
)
echo.
echo SUCCESS: G2G sample completed. Enable Greek mode Y and AI Y.
:finish
echo.
echo You can copy the exact PowerShell commands from INSTALL_GREEK_AI_COMMANDS.txt.
pause
endlocal
