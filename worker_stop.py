"""Stop the current search worker, not its GUI, and verify known descendants.

Windows: snapshot parent-child relationships with built-in PowerShell/WMI,
run taskkill /T /F, wait for direct exit, then independently inspect the
original worker and all descendants observed before the stop. If the
snapshot is unavailable, report tree verification as incomplete, not success.
On POSIX: terminate the separate worker process group and check whether
known descendants remain. An unreachable child is not proof of an intact
checkpoint: hard-stop can still interrupt current writes.
"""
from __future__ import annotations
import json
import os
import re
import signal
import subprocess
import time


def _confirm_exit(process, seconds=5):
    try:
        process.wait(timeout=seconds)
        return process.poll() is not None
    except (subprocess.TimeoutExpired, OSError, ValueError, AttributeError):
        return False


def _descendants(pairs, parent_pid):
    """All descendants observed at one instant, with cycle defense."""
    known={int(parent_pid)}
    for _ in range(len(pairs)+1):
        newer={pid for pid,ppid in pairs.items() if ppid in known and pid not in known}
        if not newer:break
        known.update(newer)
    known.discard(int(parent_pid))
    return known


def _windows_process_table():
    """Return PID:parent-PID, or None when Windows process enumeration fails."""
    cmd=['powershell.exe','-NoProfile','-NonInteractive','-Command',
         'Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId | ConvertTo-Json -Compress']
    try:
        r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                         text=True,timeout=9,
                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if r.returncode: return None
        rows=json.loads(r.stdout.strip().lstrip('\ufeff'))
        if isinstance(rows,dict):rows=[rows]
        if not isinstance(rows,list):return None
        return {int(row['ProcessId']):int(row['ParentProcessId'])
                for row in rows if isinstance(row,dict)}
    except (OSError,ValueError,KeyError,TypeError,subprocess.TimeoutExpired):
        return None


def _posix_process_table():
    try:
        r=subprocess.run(['ps','-e','-o','pid=,ppid='],capture_output=True,
                         text=True,timeout=5)
        if r.returncode:return None
        out={}
        for line in r.stdout.splitlines():
            vals=line.split()
            if len(vals)>=2 and all(re.fullmatch(r'\d+',x) for x in vals[:2]):
                out[int(vals[0])]=int(vals[1])
        return out
    except (OSError,subprocess.TimeoutExpired):
        return None


def _posix_child_still_running(pid):
    """On Linux treat a defunct zombie as already stopped, not as active."""
    status=f'/proc/{pid}/stat'
    try:
        with open(status,encoding='ascii') as fh:
            data=fh.read()
        state=data.rsplit(')',1)[1].strip().split()[0]
        return state not in ('Z','X')
    except FileNotFoundError:return False
    except (OSError,IndexError):
        try:
            os.kill(pid,0)
            return True
        except ProcessLookupError:return False
        except PermissionError:return True


def kill_search_process(process, platform=None):
    """Return (all observed children verified stopped, explanation).

    The actual stop is always attempted even if process enumeration fails.
    No PIDs other than the root worker/process group are targets. PIDs in a
    pre-stop snapshot cannot catch children created after enumeration, so the
    message explicitly says 'observed' rather than guaranteeing all possible
    future descendants are known.
    """
    if process is None:return False,'No worker process.'
    if process.poll() is not None:
        return True,'Worker already exited; no new termination performed.'
    platform=platform or os.name
    if platform=='nt':
        before=_windows_process_table()
        owned=_descendants(before,process.pid) if before is not None else None
        try:
            result=subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15,
                creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        except (OSError,subprocess.TimeoutExpired) as ex:
            result=None
            detail=str(ex)[:160]
        else:
            detail=(result.stderr or result.stdout or '').strip()[:160]
        if result is not None and result.returncode==0:
            root_gone=_confirm_exit(process)
            after=_windows_process_table()
            if root_gone and owned is not None and after is not None:
                lingering=owned.intersection(after)
                if not lingering:
                    return True,f'Worker exited; {len(owned)} observed child process(es) confirmed absent.'
                return False,'Worker exited but child PID(s) remain: '+', '.join(map(str,sorted(lingering)))
            return False,'Taskkill acknowledged, but independent worker/child verification unavailable.'
        if process.poll() is not None:
            return False,'Worker exited but tree termination could not be confirmed: '+detail
        try:
            process.kill()
            _confirm_exit(process,3)
        except (OSError,ValueError) as ex:
            return False,'Taskkill failed and direct worker could not be killed: '+str(ex)
        return False,'Direct worker killed after taskkill failed; CHILD PROCESSES MAY REMAIN: '+detail

    before=_posix_process_table()
    owned=_descendants(before,process.pid) if before is not None else None
    try:
        os.killpg(process.pid,signal.SIGKILL)
    except (OSError,ProcessLookupError) as ex:
        try:
            process.kill()
            _confirm_exit(process,3)
        except (OSError,ValueError) as fallback:
            return False,'Could not stop the worker: '+str(fallback)
        return False,'Direct worker killed; group members unverified: '+str(ex)
    root_gone=_confirm_exit(process)
    if not root_gone:return False,'Group signaled but direct worker exit was not verified.'
    if owned is None:return False,'Worker exited; child process enumeration was unavailable.'
    until=time.monotonic()+3
    while True:
        survivors=[p for p in owned if _posix_child_still_running(p)]
        if not survivors:
            return True,f'Worker exited; {len(owned)} observed child process(es) stopped.'
        if time.monotonic()>=until:break
        time.sleep(.1)
    return False,'Worker exited but observed child PID(s) still active: '+', '.join(map(str,sorted(survivors)))
