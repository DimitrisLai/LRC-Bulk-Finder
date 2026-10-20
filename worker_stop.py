"""Terminate ONLY the running lyrics worker process tree.

Never kill the GUI itself. On Windows, PyInstaller --onefile creates a
bootloader child process: taskkill /T is required to avoid an orphan.
The call must run on a background thread when initiated from Tkinter.
Hard stop keeps already fsynced checkpoints; an in-flight song is retried.
"""
from __future__ import annotations
import os
import signal
import subprocess


def kill_search_process(process,platform=None):
    """Return (success, explanation), without ever terminating our GUI."""
    if process is None:
        return False,"No worker process."
    if process.poll() is not None:
        return True,"Worker already exited."
    platform=platform or os.name
    if platform=="nt":
        try:
            result=subprocess.run(
                ["taskkill","/PID",str(process.pid),"/T","/F"],
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                text=True,timeout=15,
                creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            if result.returncode==0 or process.poll() is not None:
                return True,"Worker process tree terminated."
            # Fall back to killing the direct worker when taskkill is denied.
            process.kill()
            return True,"Direct worker terminated; taskkill tree failed: "+result.stderr.strip()[:140]
        except (OSError,subprocess.TimeoutExpired) as exc:
            try:
                process.kill()
                return True,"Direct worker terminated; tree tool unavailable: "+str(exc)[:140]
            except (OSError,ValueError) as fallback:
                return False,"Could not terminate worker: "+str(fallback)
    try:
        # Only safe if the caller created worker with start_new_session=True.
        os.killpg(process.pid,signal.SIGKILL)
        return True,"Worker process group terminated."
    except (ProcessLookupError,OSError):
        try:
            process.kill()
            return True,"Worker process terminated."
        except (OSError,ValueError) as error:
            return False,"Could not terminate worker: "+str(error)
