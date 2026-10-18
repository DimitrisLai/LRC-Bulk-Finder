"""Deliberate, safe cleanup of an AUTO-INSTALLED LRCLIB database.

Never searches drives for candidate files, never accepts an arbitrary filename,
never deletes outside the exact auto-installer configuration. Standard-library only.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import sys

BASE = Path(__file__).resolve().parent
CONFIG = BASE / 'LRCLIB_LOCAL_DB.txt'
AUTO_MARKER = '# Official offline LRCLIB SQLite snapshot; lyrics were not bundled with the application'
PREVIOUS_MARKER = '# Offline LRCLIB SQLite snapshot. Configured by official one-click installer'
AUTO_NAME = re.compile(r'lrclib-db-dump-20\d{6}T\d{6}Z\.sqlite3', re.IGNORECASE)


def locate_managed_files(config: Path = CONFIG) -> tuple[Path, Path]:
    """Locate only the precise auto-installer targets. Reject custom/manual DBs."""
    if not config.is_file() or config.is_symlink():
        raise ValueError('No valid offline database configuration was found.')
    raw = config.read_text(encoding='utf-8-sig').splitlines()
    if not raw or raw[0].strip() not in (AUTO_MARKER, PREVIOUS_MARKER):
        raise ValueError('This database was not confirmed as auto-installed. Cleanup will not delete manually configured files.')
    entries = [line.strip() for line in raw if line.strip() and not line.lstrip().startswith('#')]
    if len(entries) != 1:
        raise ValueError('Configuration does not contain exactly one database path. Nothing will be deleted.')
    path = Path(entries[0].strip('"'))
    if not path.is_absolute() or not AUTO_NAME.fullmatch(path.name):
        raise ValueError('Unexpected database path or filename. Nothing will be deleted.')
    # Windows absolute paths are recognized by Path on Windows (target platform).
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError('Symbolic-link paths are not allowed for cleanup.')
    gz = path.with_name(path.name + '.gz')
    if gz.is_symlink():
        raise ValueError('Symbolic-link archives are not allowed for cleanup.')
    return path, gz


def file_info(path: Path) -> str:
    if not path.is_file():
        return f'{path}\n  Status: NOT PRESENT'
    n = path.stat().st_size
    return f'{path}\n  Size: {n / (1024**3):,.2f} GiB'


def clear_config(config: Path) -> None:
    """Deactivate offline database lookup after the extracted DB is removed."""
    tmp = config.with_name(config.name + '.cleanup.tmp')
    try:
        tmp.write_text('# Offline LRCLIB database was removed by the cleanup tool.\n'
                       '# Run SETUP_LRCLIB_DATABASE.cmd to install again.\n', encoding='utf-8')
        os.replace(tmp, config)
    finally:
        tmp.unlink(missing_ok=True)


def remove_managed_files(option: str, config: Path = CONFIG) -> list[Path]:
    """Called only after deliberate interactive confirmation in main()."""
    if option not in ('1', '2', '3'):
        raise ValueError('Choose 1 (archive), 2 (database), or 3 (both)')
    db, gz = locate_managed_files(config)
    removed = []
    if option in ('2', '3'):
        if db.is_file():
            db.unlink()
            removed.append(db)
        clear_config(config)
    if option in ('1', '3') and gz.is_file():
        gz.unlink()
        removed.append(gz)
    return removed


def main():
    print('=' * 70)
    print('LRC BULK FINDER - OFFLINE LRCLIB CLEANUP')
    print('=' * 70)
    print('This tool does NOT delete any MP3, LRC, or music folder.')
    print('It deletes ONLY the exact auto-installed LRCLIB database files listed below.')
    print()
    db, gz = locate_managed_files(CONFIG)
    print('COMPRESSED DATABASE DOWNLOAD (.sqlite3.gz)')
    print(' ', file_info(gz).replace('\n', '\n  '))
    print('EXTRACTED OFFLINE DATABASE (.sqlite3)')
    print(' ', file_info(db).replace('\n', '\n  '))
    print()
    print('  1 - DELETE compressed download ONLY  [Recommended after successful setup]')
    print('      Keeps offline LRCLIB searching fully functional.')
    print('  2 - DELETE extracted database ONLY  [Disables offline LRCLIB]')
    print('      Retains compressed download for potential future reinstall.')
    print('  3 - DELETE BOTH download and extracted database  [Disables offline LRCLIB]')
    print('  4 - CANCEL (default)')
    print()
    option = input('Choose [1/2/3/4] (default 4): ').strip() or '4'
    if option == '4':
        print('Canceled. No files changed.'); return 0
    if option not in ('1', '2', '3'):
        print('Unknown choice. Canceled.'); return 1
    if option in ('2', '3'):
        print('\nWARNING: Removing the extracted database DISABLES offline LRCLIB searches!')
        print('Normal online searching and the queued lyrics files are not deleted.')
    requested = [x for x in ((gz if option in ('1','3') else None), (db if option in ('2','3') else None)) if x]
    if not any(x.is_file() for x in requested):
        print('Selected file(s) are not present. No deletion needed.'); return 0
    phrase = 'DELETE BOTH' if option == '3' else ('DELETE DATABASE' if option == '2' else 'DELETE DOWNLOAD')
    reply = input(f'Type {phrase} exactly to permanently delete the selected file(s): ').strip()
    if reply != phrase:
        print('Canceled. Nothing was deleted.'); return 0
    # Check configuration a second time before unlinking anything.
    current_db, current_gz = locate_managed_files(CONFIG)
    if (db, gz) != (current_db, current_gz):
        raise ValueError('Configuration changed during confirmation; aborted.')
    removed = remove_managed_files(option, CONFIG)
    print('\nFINISHED. Deleted files:', len(removed))
    for path in removed:
        print(' -', path)
    if option in ('2', '3'):
        print('Offline configuration disabled. Re-run the installer to enable it again.')
    else:
        print('Offline LRCLIB database remains installed and usable.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        print('CLEANUP NOT COMPLETED:', error)
        print('If the database is in use, close LRC Bulk Finder before trying again.')
        raise SystemExit(1)
    except (KeyboardInterrupt, EOFError):
        print('\nCanceled; no additional action requested.')
        raise SystemExit(130)
