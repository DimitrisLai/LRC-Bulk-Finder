"""Stop the *search worker*, never the Control Center (v2.4.3-dev).

Failure to kill a whole Windows process tree must not be advertised as success.
"""
from __future__ import annotations
import os
import signal
import subprocess


def _confirm_exit(process, seconds=5):
    try:
        process.wait(timeout=seconds)
        return process.poll() is not None
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return False


def kill_search_process(process, platform=None):
    """Return (verified_success, message). Never target the GUI process.

    On Windows, a successful taskkill /T /F is the only reliable tree-kill
    acknowledgement offered by built-in tools. If taskkill fails and the
    direct PID is killed, descendants remain unverified and success is False.
    """
    if process is None:
        return False, 'No worker process.'
    if process.poll() is not None:
        return True, 'Worker already exited; no termination was needed.'
    platform = platform or os.name
    if platform == 'nt':
        try:
            result = subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, timeout=15,
                                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except (OSError, subprocess.TimeoutExpired) as exc:
            result = None
            detail = str(exc)[:160]
        else:
            detail = (result.stderr or result.stdout or '').strip()[:160]
        if result is not None and result.returncode == 0 and _confirm_exit(process):
            return True, 'Windows acknowledged process-tree termination; worker exited.'
        if process.poll() is not None:
            return False, 'Worker exited, but process-tree termination could not be confirmed: ' + detail
        try:
            process.kill()
        except (OSError, ValueError) as exc:
            return False, 'Tree termination failed; could not kill direct worker: ' + str(exc)
        return False, ('Direct worker termination attempted after taskkill failed. '
                       'CHILD PROCESSES MAY REMAIN; check Task Manager. ' + detail)
    try:
        # Only safe for workers launched in their own session.
        os.killpg(process.pid, signal.SIGKILL)
        if _confirm_exit(process):
            return True, 'Worker process group signaled and parent exited.'
        return False, 'Process-group signal sent; worker exit not verified.'
    except (ProcessLookupError, OSError) as exc:
        try:
            process.kill()
        except (OSError, ValueError) as fallback:
            return False, 'Worker group termination failed: ' + str(fallback)
        return False, ('Direct worker was killed; other group members were not verified. '
                       + str(exc)[:120])
