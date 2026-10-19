"""Where v2.3 stores editable settings versus packaged read-only resources."""
from __future__ import annotations
import sys
from pathlib import Path


def program_folder():
    """Editable config files live beside the EXE in the standalone variant."""
    if getattr(sys,"frozen",False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def data_folder():
    """Bundled static dictionaries (PyInstaller sys._MEIPASS when frozen)."""
    if getattr(sys,"frozen",False):
        return Path(getattr(sys,"_MEIPASS",Path(sys.executable).parent)).resolve()
    return Path(__file__).resolve().parent
