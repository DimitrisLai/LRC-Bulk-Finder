"""Run every shipped Windows .CMD/.BAT wrapper, stubbing dangerous installer targets.
Only executes against a temporary copy. No user folders, downloads or database writes.
"""
from __future__ import annotations
import os,sys,shutil,subprocess,tempfile,time
from pathlib import Path
SRC=Path(os.environ.get('LRC_QA_SOURCE') or Path(__file__).resolve().parent)
if sys.platform!='win32':
 print('SKIP: native batch wrapper probe requires Windows')
 raise SystemExit(0)
wrappers=sorted(list(SRC.glob('*.cmd'))+list(SRC.glob('*.bat')))
assert len(wrappers)>=9, [p.name for p in wrappers]
with tempfile.TemporaryDirectory(prefix='lrc_cmd_sandbox_') as raw:
 p=Path(raw)
 for f in wrappers:shutil.copy2(f,p/f.name)
 stubs=['LRC_Control_Center.py','LRC_Bulk_Finder.py','auto_install_lrclib_database.py',
 'connect_existing_lrclib_database.py','setup_lrclib_database.py','cleanup_lrclib_database.py',
 'g2g_integration.py','lrclib_local.py']
 for f in stubs:
  (p/f).write_text("from pathlib import Path\nprint('QA_SAFE_TARGET:'+Path(__file__).name)\n",encoding='utf-8')
 safe_env={**os.environ,'APPDATA':str(p/'settings'), 'PYTHONUTF8':'1', 'PYTHONDONTWRITEBYTECODE':'1'}
 for f in wrappers:
  if f.name=='Run_Diagnostics.cmd':
   # Captures real interpreter & dependency checks, with only disposable stub targets.
   pass
  # Use 9 to cancel the menu; use N for any optional setup confirmation.
  stdin='9\nn\n\n\n\n\n'
  if f.name=='SETUP_GREEK_AI.cmd':stdin='N\n\n\n'
  command=['cmd.exe','/d','/s','/c',str(p/f.name)]
  try:
   proc=subprocess.run(command,input=stdin,text=True,capture_output=True,timeout=35,env=safe_env,cwd=p)
  except subprocess.TimeoutExpired as exc:
   raise AssertionError('Timed out inside Windows launcher '+f.name) from exc
  output=proc.stdout+'\n'+proc.stderr
  if f.name=='Run_Diagnostics.cmd':
   assert (p/'Startup_Diagnostics.txt').exists(),'Diagnostics not written'
  elif f.name=='SETUP_GREEK_AI.cmd':
   assert 'OPTIONAL GREEKLISH' in output,'Setup title missing';assert 'SUCCESS: G2G' not in output,'Unsafe accidental install'
  elif f.name in ('START_HERE.cmd','Run_LRC_Finder.cmd','Start_LRC_Finder.bat'):
   assert 'QA_SAFE_TARGET:LRC_Bulk_Finder.py' in output, (f.name,output[-800:])
  else:
   expected={'OPEN_CONTROL_CENTER.cmd':'LRC_Control_Center.py',
   'CONNECT_EXISTING_LRCLIB_DATABASE.cmd':'connect_existing_lrclib_database.py',
   'CLEANUP_LRCLIB_DATABASE.cmd':'cleanup_lrclib_database.py',
   'SETUP_LRCLIB_DATABASE.cmd':'auto_install_lrclib_database.py',
   'SETUP_LRCLIB_DATABASE_FROM_FILE.cmd':'setup_lrclib_database.py'}.get(f.name)
   if expected:
    assert 'QA_SAFE_TARGET:'+expected in output,(f.name,output[-800:])
  if f.name=='LAUNCH_LRC_BULK_FINDER_WINDOWS.cmd':
   # This intentional standalone GUI launcher refuses unsafe/incomplete extraction.
   # The probe has NO real EXEs, so the correct behavior is a clear error and exit 2.
   assert proc.returncode==2,(f.name,proc.returncode,output[-700:])
   assert 'LRC_Control_Center.exe is missing' in output,(f.name,output[-700:])
   assert 'extract the ENTIRE official Windows Standalone ZIP' in output,(f.name,output[-700:])
  else:
   assert proc.returncode in (0,1), (f.name,proc.returncode,output[-700:])
  print('PASS',f.name,'exit',proc.returncode)
 print('PASS:',len(wrappers),'Windows launchers reached their expected safe targets')