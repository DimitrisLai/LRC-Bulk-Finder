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


class StopContext:
    """Retain the original observed tree across STOP retries.

    Windows handles refer to process objects, so a reused numeric PID can
    never cause a retry to terminate somebody else's process.
    """
    def __init__(self):
        self.captured = False
        self.owned = None
        self.handles = {}
        self.table = None
        self.safe_owned = set()

    def close(self):
        if self.handles:
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
            for handle in self.handles.values():
                kernel.CloseHandle(handle)
            self.handles.clear()


def _pin_windows_children(pids, table):
    """Open observed descendants before cancellation, while the tree exists."""
    try:
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetProcessTimes.argtypes = (wintypes.HANDLE,) + (ctypes.POINTER(wintypes.FILETIME),) * 4
        kernel.GetProcessTimes.restype = wintypes.BOOL
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        handles = {}
        for pid in pids:
            # A numeric PID may have been reused since the snapshot. Only
            # retain a handle whose creation time matches that observation.
            expected = getattr(table, 'birth_times', {}).get(pid)
            if expected is None:
                continue
            handle = kernel.OpenProcess(0x1000 | 0x100000 | 0x0001, False, pid)
            if not handle:
                continue
            created, exited, cpu, user = (wintypes.FILETIME() for _ in range(4))
            if (kernel.GetProcessTimes(handle, ctypes.byref(created), ctypes.byref(exited),
                                       ctypes.byref(cpu), ctypes.byref(user)) and
                    ((created.dwHighDateTime << 32) | created.dwLowDateTime) == expected):
                handles[pid] = handle
            else:
                kernel.CloseHandle(handle)
        return handles
    except (OSError, AttributeError):
        return {}


def _pinned_windows_children_running(handles, terminate=False):
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.TerminateProcess.argtypes = (wintypes.HANDLE, wintypes.UINT)
    kernel.TerminateProcess.restype = wintypes.BOOL
    if terminate:
        for handle in handles.values():
            if kernel.WaitForSingleObject(handle, 0) != 0:
                kernel.TerminateProcess(handle, 1)
    # One shared wait budget, never one second per child on a large tree.
    deadline = time.monotonic() + (3 if terminate else 0)
    while True:
        running = {pid for pid, handle in handles.items()
                   if kernel.WaitForSingleObject(handle, 0) != 0}
        if not running or time.monotonic() >= deadline:
            return running
        time.sleep(.03)


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


def _prune_reused_windows_parents(pairs,creation_times):
    """A child cannot predate its parent; sever stale PPIDs after Windows PID reuse.

    Windows retains the numeric inherited PPID of an orphan, even if that old
    parent has exited and the PID has since been assigned to a new process.
    Never classify an older orphan as a child of the newer worker.
    Missing/inaccessible creation times leave the edge intact, conservatively.
    """
    return {pid:(0 if pid in creation_times and ppid in creation_times
                     and creation_times[pid] < creation_times[ppid] else ppid)
            for pid,ppid in pairs.items()}


def _windows_process_table_toolhelp():
    """Fast, dependency-free Windows PID/PPID snapshot using the native API.

    Avoid starting PowerShell/Win32_Process CIM for every STOP: on busy
    Windows machines that extra process occasionally timed out and falsely
    made an otherwise successful taskkill impossible to verify.
    """
    try:
        import ctypes
        from ctypes import wintypes
        MAX_PATH = 260
        TH32CS_SNAPPROCESS = 0x00000002

        class PROCESSENTRY32W(ctypes.Structure):
            _fields_ = [
                ('dwSize', wintypes.DWORD),
                ('cntUsage', wintypes.DWORD),
                ('th32ProcessID', wintypes.DWORD),
                ('th32DefaultHeapID', ctypes.c_size_t),
                ('th32ModuleID', wintypes.DWORD),
                ('cntThreads', wintypes.DWORD),
                ('th32ParentProcessID', wintypes.DWORD),
                ('pcPriClassBase', wintypes.LONG),
                ('dwFlags', wintypes.DWORD),
                ('szExeFile', wintypes.WCHAR * MAX_PATH),
            ]

        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
        kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
        kernel32.Process32FirstW.argtypes = (wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W))
        kernel32.Process32FirstW.restype = wintypes.BOOL
        kernel32.Process32NextW.argtypes = (wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W))
        kernel32.Process32NextW.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL

        handle = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if handle in (None, ctypes.c_void_p(-1).value):
            return None
        try:
            entry = PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
            if not kernel32.Process32FirstW(handle, ctypes.byref(entry)):
                return None
            pairs = {}
            while True:
                pairs[int(entry.th32ProcessID)] = int(entry.th32ParentProcessID)
                if not kernel32.Process32NextW(handle, ctypes.byref(entry)):
                    break
            if not pairs:
                return None
            # Disambiguate reused parent PIDs without extra PowerShell calls.
            # Querying process creation times is native, fast and read-only.
            kernel32.OpenProcess.argtypes=(wintypes.DWORD,wintypes.BOOL,wintypes.DWORD)
            kernel32.OpenProcess.restype=wintypes.HANDLE
            kernel32.GetProcessTimes.argtypes=(
                wintypes.HANDLE,ctypes.POINTER(wintypes.FILETIME),
                ctypes.POINTER(wintypes.FILETIME),ctypes.POINTER(wintypes.FILETIME),
                ctypes.POINTER(wintypes.FILETIME))
            kernel32.GetProcessTimes.restype=wintypes.BOOL
            born={}
            for pid in pairs:
                if pid<=0:continue
                ph=kernel32.OpenProcess(0x1000,False,pid)  # QUERY_LIMITED_INFORMATION
                if not ph:continue
                try:
                    created=wintypes.FILETIME()
                    exited=wintypes.FILETIME()
                    kernel=wintypes.FILETIME()
                    user=wintypes.FILETIME()
                    if kernel32.GetProcessTimes(ph,ctypes.byref(created),
                                               ctypes.byref(exited),ctypes.byref(kernel),
                                               ctypes.byref(user)):
                        born[pid]=(created.dwHighDateTime<<32)|created.dwLowDateTime
                finally:
                    kernel32.CloseHandle(ph)
            class ProcessTable(dict):
                pass
            table = ProcessTable(_prune_reused_windows_parents(pairs,born))
            table.birth_times = born
            return table
        finally:
            kernel32.CloseHandle(handle)
    except (OSError, ValueError, TypeError, AttributeError):
        return None


def _windows_process_table_cim():
    """Slower PowerShell/CIM fallback if the native Windows API fails."""
    cmd=['powershell.exe','-NoProfile','-NonInteractive','-Command',
         'Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId | ConvertTo-Json -Compress']
    try:
        r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                         text=True,timeout=3,
                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        if r.returncode:return None
        rows=json.loads(r.stdout.strip().lstrip('\ufeff'))
        if isinstance(rows,dict):rows=[rows]
        if not isinstance(rows,list):return None
        pairs={int(row['ProcessId']):int(row['ParentProcessId'])
               for row in rows if isinstance(row,dict)}
        return pairs if pairs else None
    except (OSError,ValueError,KeyError,TypeError,subprocess.TimeoutExpired):
        return None


def _windows_process_table():
    """Return PID:parent-PID, or None when BOTH discovery routes fail."""
    result=_windows_process_table_toolhelp()
    return result if result is not None else _windows_process_table_cim()


def _windows_snapshot_with_retry(attempts=3):
    """Retry transient snapshots; never treat an unavailable view as success."""
    for attempt in range(attempts):
        result=_windows_process_table()
        if result is not None:
            return result
        if attempt+1<attempts:
            time.sleep(.12)
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


def kill_search_process(process, platform=None, *, context=None, request_stop=None):
    """Return (all observed children verified stopped, explanation).

    The actual stop is always attempted even if process enumeration fails.
    No PIDs other than the root worker/process group are targets. PIDs in a
    pre-stop snapshot cannot catch children created after enumeration, so the
    message explicitly says 'observed' rather than guaranteeing all possible
    future descendants are known.
    """
    if process is None:return False,'No worker process.'
    platform=platform or os.name
    # Capture BEFORE writing the cooperative marker: the worker can exit as
    # soon as it sees it, leaving stdout-holding descendants behind.
    if context is not None and not context.captured:
        if process.poll() is None:
            table = (_windows_snapshot_with_retry() if platform == 'nt'
                     else _posix_process_table())
            context.owned = _descendants(table, process.pid) if table is not None and process.pid in table else None
            context.table = table
            if platform == 'nt' and context.owned:
                born = getattr(table, 'birth_times', {})
                # Every edge, including the original root, needs known
                # chronological identity before a child may be terminated.
                safe_pairs = {pid:ppid for pid,ppid in table.items()
                              if pid in born and ppid in born and born[pid] >= born[ppid]}
                context.safe_owned = _descendants(safe_pairs, process.pid)
                context.handles = _pin_windows_children(context.safe_owned, table)
        context.captured = True
    elif platform == 'nt' and context is not None and context.table is not None:
        context.handles.update(_pin_windows_children(context.safe_owned - set(context.handles), context.table))
    if request_stop is not None:
        request_stop()
    if platform == 'nt' and context is not None and process.poll() is None:
        # Popen.kill uses its original Windows process handle. Do not use
        # taskkill /T's numeric-PPID traversal for a captured GUI STOP: stale
        # orphan PPIDs can name an unrelated process after PID reuse.
        try:
            process.kill()
        except (OSError, ValueError) as error:
            if process.poll() is None:
                return False,'Direct worker termination failed: '+str(error)
        if not _confirm_exit(process, 3):
            return False,'Direct worker exit could not be verified. Retry STOP.'
    if process.poll() is not None:
        if context is None or context.owned is None:
            return False,'Worker already exited; original child tree could not be verified.'
        if platform == 'nt':
            after = _windows_snapshot_with_retry()
            if after is None:
                return False,'Worker exited; child verification unavailable. Retry STOP.'
            pinned = _pinned_windows_children_running(context.handles, terminate=True) if context.handles else set()
            lingering = (context.owned - set(context.handles)).intersection(after) | pinned
        else:
            # Never signal a recycled POSIX PID/group after its leader exited.
            lingering = {pid for pid in context.owned if _posix_child_still_running(pid)}
        if lingering:
            return False,'Worker exited but observed child PID(s) remain: '+', '.join(map(str,sorted(lingering)))
        return True,f'Worker exited; {len(context.owned)} original observed child process(es) confirmed stopped.'
    if platform=='nt':
        before=_windows_snapshot_with_retry() if context is None else None
        owned=(_descendants(before,process.pid) if before is not None else None) if context is None else context.owned
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
            after=_windows_snapshot_with_retry()
            if root_gone and owned is not None and after is not None:
                lingering=owned.intersection(after)
                if context is not None and context.handles:
                    lingering = (owned - set(context.handles)).intersection(after) | _pinned_windows_children_running(context.handles)
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

    before=_posix_process_table() if context is None else None
    owned=(_descendants(before,process.pid) if before is not None else None) if context is None else context.owned
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
