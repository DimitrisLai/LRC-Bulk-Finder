#!/usr/bin/env python3
"""Connect an existing LRCLIB SQLite snapshot by saving its path, no copying."""
from pathlib import Path
from lrclib_local import LocalLRCLIB, load_local_config


def link_existing_folder(script_dir=None, *, choose=None, reply=input):
    program=Path(script_dir or Path(__file__).resolve().parent)
    config=program/'LRCLIB_LOCAL_DB.txt'
    current=load_local_config(config)
    print('\nCONNECT AN EXISTING OFFLINE LRCLIB DATABASE')
    print('No download, extraction, or copying will occur.')
    if current:
        print('Current database:',current)
    print('Select your existing .sqlite3 database (not .gz).')
    if choose is None:
        try:
            import tkinter as tk
            from tkinter import filedialog
            root=tk.Tk();root.withdraw()
            chosen=filedialog.askopenfilename(
                title='Choose EXISTING LRCLIB .sqlite3 database',
                filetypes=[('LRCLIB SQLite database','*.sqlite3 *.sqlite *.db'),('All files','*.*')])
            root.destroy()
        except Exception:
            chosen=''
    else:
        chosen=choose()
    if not chosen:
        chosen=reply('Paste full existing .sqlite3 file path (Enter to cancel): ').strip().strip('"')
    if not chosen:
        print('Canceled; existing configuration unchanged.')
        return False
    try:
        path=Path(chosen).expanduser().resolve(strict=True)
        LocalLRCLIB(path)
        temp=config.with_suffix('.txt.tmp')
        try:
            temp.write_text(str(path)+'\n',encoding='utf-8')
            temp.replace(config)
        finally:
            temp.unlink(missing_ok=True)
        print('\nSUCCESS: LOCAL LRCLIB DATABASE CONNECTED')
        print('Database:',path)
        print('Only the small text configuration was written:',config)
        print('You can now choose 4 (OFFLINE ONLY), or 1 (offline-first with other sources).')
        return True
    except (OSError,ValueError,RuntimeError) as ex:
        print('FAILED: Database was not connected:',ex)
        print('Existing configuration unchanged.')
        return False


if __name__=='__main__':
    try:link_existing_folder()
    except KeyboardInterrupt:print('\nCanceled.')
