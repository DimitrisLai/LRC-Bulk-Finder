"""One-time Windows command-line assistant for configuring an optional LRCLIB dump."""
from pathlib import Path
import gzip
import os
import shutil
from lrclib_local import LocalLRCLIB

base=Path(__file__).resolve().parent
print('LRC Bulk Finder - optional OFFLINE LRCLIB SQLite database setup')
print('Get an official database snapshot from: https://lrclib.net/db-dumps')
print('You may download the .sqlite3.gz snapshot yourself; the ZIP does not contain lyrics.')
print('The database may be large. Ensure enough free disk space before extracting.')
print('Press Enter to cancel without changing the existing configuration.\n')
raw=input('Paste the full path to your .sqlite3 or .sqlite3.gz file: ').strip().strip('"')
if not raw:
    raise SystemExit('Canceled: existing configuration was not changed.')
path=Path(raw).expanduser().resolve()
if not path.is_file():
    raise SystemExit(f'File not found: {path}')
if path.name.lower().endswith('.gz'):
    destination=path.with_suffix('')
    if destination.exists():
        print('Decompressed file already exists:',destination)
        print('Will validate the existing file, not overwrite it.')
    else:
        print('Streaming extraction to:',destination)
        tmp=destination.with_name(destination.name+'.partial')
        try:
            with gzip.open(path,'rb') as source, tmp.open('xb') as target:
                shutil.copyfileobj(source,target,length=2*1024*1024)
            os.replace(tmp,destination)
        except BaseException:
            try:tmp.unlink(missing_ok=True)
            except OSError:pass
            raise
    path=destination
print('Validating SQLite format and schema (read-only)...')
LocalLRCLIB(path)
config=base/'LRCLIB_LOCAL_DB.txt'
config.write_text('# Absolute path to an independently downloaded LRCLIB SQLite snapshot\n'+str(path)+'\n',encoding='utf-8')
print('SUCCESS. Offline database configured:',path)
print('Next: run START_HERE.cmd and choose SEARCH (1) or LRCLIB catch-up (3).')
