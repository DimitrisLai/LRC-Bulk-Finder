@echo off
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
set "LOG=%~dp0Startup_Diagnostics.txt"
echo Collecting Python diagnostics... 
(
 echo LRC Bulk Finder Public Edition v2.4.4
 echo ==== Python ==== 
 where py
 py -3 --version
 where python
 python --version
 echo ==== Packages ==== 
 py -3 -c "import sys;print(sys.executable);import mutagen,unidecode,syncedlyrics;print('Core packages OK')"
 echo ==== Optional G2G ==== 
 py -3 -c "import importlib.util;print('G2G installed:',importlib.util.find_spec('gr_nlp_toolkit') is not None)"
 echo ==== Syntax ==== 
 py -3 -m py_compile "LRC_Bulk_Finder.py" "g2g_integration.py"
) >"%LOG%" 2>&1
echo Diagnostics saved: %LOG%
type "%LOG%"
pause
endlocal
