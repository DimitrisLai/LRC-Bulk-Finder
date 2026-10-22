"""Windows frozen GUI regression: verify the exact visible v2.9.1 title.

Historical issue: the Control Center set the new title then language refresh
silently restored v2.7.0. The previous frozen check validated liveness only.
No music or user files are accessed or changed.
"""
from __future__ import annotations
import ctypes
from ctypes import wintypes
from pathlib import Path
import subprocess
import sys
import time


def visible_control_center_titles():
    user32=ctypes.windll.user32
    callback=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    seen=[]
    def collect(hwnd,lparam):
        if user32.IsWindowVisible(hwnd):
            n=user32.GetWindowTextLengthW(hwnd)
            if n:
                buf=ctypes.create_unicode_buffer(n+1)
                user32.GetWindowTextW(hwnd,buf,n+1)
                if 'LRC Bulk Finder' in buf.value:
                    seen.append(buf.value)
        return True
    user32.EnumWindows(callback(collect),0)
    return seen

def main():
    if sys.platform!="win32":
        raise SystemExit("This frozen executable check requires Windows")
    if len(sys.argv)!=2:
        raise SystemExit("Usage: python QA_V291_FROZEN_GUI_TITLE.py path/to/LRC_Control_Center.exe")
    exe=Path(sys.argv[1]).resolve()
    if not exe.is_file():
        raise SystemExit("Frozen GUI executable not found")
    proc=subprocess.Popen([str(exe)],cwd=str(exe.parent))
    try:
        # PyInstaller onefile may need several seconds to extract on CI.
        deadline=time.monotonic()+20
        seen=[]
        while time.monotonic()<deadline:
            if proc.poll() is not None:
                raise AssertionError(f"Frozen GUI exited early, status={proc.returncode}")
            # PyInstaller --onefile runs the GUI in a child process, not the launcher PID.
            seen=visible_control_center_titles()
            if "LRC Bulk Finder v2.9.1 — Control Center" in seen:
                print("PASS frozen Control Center visible title is v2.9.1 after language initialization.")
                return 0
            time.sleep(.4)
        raise AssertionError(f"Expected v2.9.1 Control Center title not seen. Visible titles: {seen!r}")
    finally:
        proc.terminate()
        try:proc.wait(timeout=8)
        except subprocess.TimeoutExpired:proc.kill()

if __name__=="__main__":
    sys.exit(main())
