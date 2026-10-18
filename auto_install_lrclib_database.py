"""Optional, consent-based installer of a public LRCLIB SQLite dump.

Not run during normal application launch.  Large datasets are never silently
installed.  The official page is the only link-discovery authority; a complete
snapshot is not part of LRC Bulk Finder's redistributed ZIP.
"""
from __future__ import annotations

import gzip
import json
from html import unescape
import os
from pathlib import Path
import re
import shutil
import sys
import time
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from lrclib_local import LocalLRCLIB, load_local_config

BASE = Path(__file__).resolve().parent
INDEX = 'https://lrclib.net/db-dumps'
# JSON listing used by independently maintained LRCLIB client pylrclib.
# We only construct download URLs on the LRCLIB-controlled hostname below.
CATALOG = 'https://lrclib-db-dumps.bu3nnyut4y9jfkdg.workers.dev'
DUMP_HOST = 'https://db-dumps.lrclib.net'
AGENT = 'LRCBulkFinder/2.1.14 (https://github.com/DimitrisLai/LRC-Bulk-Finder)'
# Deliberately conservative: Aug 2026 snapshot was nearly 250 GB unpacked.
# Actual future dumps can exceed this preflight limit: keep monitoring disk space.
MIN_FREE_BYTES = 350 * (1024 ** 3)
CHUNK = 8 * 1024 * 1024


def discover_snapshot(html_text: str, base: str = INDEX) -> str:
    """Choose the newest visible .sqlite3.gz URL advertised on official page.

    Supports hyperlinks, absolute URLs, and common escaped URLs in site scripts.
    Does not invent endpoints or use untrusted third-party search results.
    """
    text = unescape(html_text).replace('\\/', '/').replace('\\u002F', '/').replace('\\u002f', '/')
    choices = []
    # href first, then any embedded fully-qualified or relative dump URL.
    candidates = re.findall(r'''href\s*=\s*["']([^"']+\.sqlite3\.gz(?:\?[^"']*)?)["']''', text, flags=re.I)
    candidates += re.findall(r'''https?://[^\s"'<>\\]+?\.sqlite3\.gz(?:\?[^\s"'<>\\]+)?''', text, flags=re.I)
    for item in candidates:
        full = urljoin(base, unescape(item))
        parsed = urlparse(full)
        if parsed.scheme != 'https' or not parsed.netloc:
            continue
        name = unquote(parsed.path.rsplit('/', 1)[-1])
        if not re.fullmatch(r'[A-Za-z0-9._-]+\.sqlite3\.gz', name, re.I):
            continue
        stamp = re.search(r'(20\d{6}T\d{6}Z)', name)
        choices.append((stamp.group(1) if stamp else '', name, full))
    if not choices:
        raise ValueError('No direct SQLite dump link was found on the official page. The page format may have changed.')
    return max(set(choices))[2]


def discover_snapshot_json(payload: str) -> tuple[str, int | None]:
    """Extract latest official .sqlite3.gz snapshot from JSON listing.

    Catalog object layout: {"objects": [{"key": ..., "size": ..., "uploaded": ...}]}.
    Download URL is constructed by this client; arbitrary URLs in the JSON
    are *never* followed. Select by timestamp in filename (or upload date).
    """
    try:
        document = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError('The snapshot catalog was not valid JSON') from exc
    objects = document.get('objects') if isinstance(document, dict) else None
    if not isinstance(objects, list):
        raise ValueError('Snapshot catalog has no objects list')
    choices = []
    for record in objects:
        if not isinstance(record, dict):
            continue
        key = record.get('key')
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9._/-]+\.sqlite3\.gz', key, re.I):
            continue
        # reject empty, traversal, unusual separators, query strings, and directories
        if any(segment in ('', '.', '..') for segment in key.split('/')):
            continue
        name = key.rsplit('/', 1)[-1]
        stamp = re.search(r'(20\d{6}T\d{6}Z)', name)
        uploaded = str(record.get('uploaded') or '')
        size = record.get('size')
        try:
            size = int(size) if size is not None else None
        except (ValueError, TypeError):
            size = None
        if size is not None and size < 0:
            size = None
        choices.append((stamp.group(1) if stamp else uploaded, uploaded, key, size))
    if not choices:
        raise ValueError('No official SQLite .sqlite3.gz snapshots in the JSON catalog')
    from urllib.parse import quote
    _, _, key, size = max(choices)
    return DUMP_HOST + '/' + quote(key, safe='/'), size


def fetch_catalog(url=CATALOG, opener=urlopen) -> str:
    """Read bounded public JSON listing with HTTPS-only redirects."""
    with opener(Request(url, headers={'User-Agent': AGENT, 'Accept': 'application/json'}), timeout=30) as reply:
        final_url = reply.geturl() if hasattr(reply, 'geturl') else url
        parsed = urlparse(final_url)
        if parsed.scheme != 'https':
            raise ValueError('The dump catalog redirected away from HTTPS')
        data = reply.read(4 * 1024 * 1024 + 1)
        if len(data) > 4 * 1024 * 1024:
            raise ValueError('Dump catalog exceeds 4 MiB safety limit')
        return data.decode('utf-8-sig')


def discover_official_snapshot() -> tuple[str, int | None, str]:
    """Prefer JSON catalog; retain safe HTML discovery as secondary fallback."""
    try:
        url, size = discover_snapshot_json(fetch_catalog())
        return url, size, 'LRCLIB JSON catalog'
    except (HTTPError, URLError, OSError, ValueError) as json_error:
        print('JSON catalog unavailable:', json_error)
        print('Checking the official webpage as a fallback ...')
        try:
            return discover_snapshot(fetch_index()), None, 'official LRCLIB webpage'
        except (HTTPError, URLError, OSError, ValueError) as html_error:
            raise ValueError(
                'Could not locate a verified database download from either source. '
                f'Catalog: {json_error}; webpage: {html_error}. '
                'No files were downloaded or changed.'
            ) from html_error


def fetch_index(index=INDEX) -> str:
    with urlopen(Request(index, headers={'User-Agent': AGENT}), timeout=30) as reply:
        if reply.geturl().startswith('http://'):
            raise ValueError('Refusing an insecure database listing redirect')
        data = reply.read(8 * 1024 * 1024 + 1)
        if len(data) > 8 * 1024 * 1024:
            raise ValueError('Database listing unusually large; refusing to parse')
    return data.decode('utf-8', errors='replace')


def get_disk_free(destination: Path) -> int:
    return shutil.disk_usage(destination).free


def progress(prefix, bytes_count, total, start):
    seconds = max(time.monotonic() - start, 0.001)
    mb = bytes_count / 1048576
    speed = mb / seconds
    percent = f'{(bytes_count / total * 100):.1f}%' if total else 'unknown %'
    print(f'\r  {prefix}: {mb:,.0f} MiB ({percent}), avg {speed:.1f} MiB/s   ', end='', flush=True)


def download_resume(url: str, target: Path, opener=urlopen, chunk: int = CHUNK) -> Path:
    """Resume only if server explicitly honors Range. Preserve .part on failure."""
    part = target.with_name(target.name + '.part')
    resume = part.stat().st_size if part.is_file() else 0
    headers = {'User-Agent': AGENT}
    if resume:
        headers['Range'] = f'bytes={resume}-'
    with opener(Request(url, headers=headers), timeout=90) as reply:
        code = getattr(reply, 'status', 200)
        if code not in (200, 206):
            raise OSError(f'Dump download HTTP {code}')
        redirected = reply.geturl() if hasattr(reply, 'geturl') else url
        if urlparse(redirected).scheme != 'https':
            raise OSError('Dump download redirected away from HTTPS')
        if resume and code == 206:
            content_range = reply.headers.get('Content-Range', '')
            if not content_range.startswith(f'bytes {resume}-'):
                raise OSError('Server responded with an unexpected Content-Range; preserving partial file')
            mode = 'ab'
            done = resume
        else:
            mode = 'wb'  # server ignored Range; start afresh, never append duplicated data
            done = 0
        value = reply.headers.get('Content-Length')
        left = int(value) if value and value.isdecimal() else None
        total = done + left if left is not None else None
        start = time.monotonic()
        with part.open(mode) as output:
            while True:
                data = reply.read(chunk)
                if not data:
                    break
                output.write(data)
                done += len(data)
                if done % (128 * 1048576) < chunk:
                    progress('Downloaded', done, total, start)
        print()
        if total is not None and done != total:
            raise OSError(f'Incomplete download: {done} of {total} bytes; keep .part to resume')
    os.replace(part, target)
    return target


def install_from_downloaded_gzip(source: Path, target: Path, config=BASE / 'LRCLIB_LOCAL_DB.txt') -> Path:
    """Stream decompress + atomic activation. Keep gzip if validation fails."""
    tmp = target.with_name(target.name + '.sqlite3') if not target.suffix.lower() in ('.sqlite3', '.db', '.sqlite') else target
    if tmp.is_file():
        LocalLRCLIB(tmp)
    else:
        # validate with valid .sqlite3 suffix, preserving .partial during extract
        partial = tmp.with_name(tmp.stem + '.partial.sqlite3')
        partial.unlink(missing_ok=True)
        start = time.monotonic()
        written = 0
        try:
            with gzip.open(source, 'rb') as inp, partial.open('xb') as out:
                magic = inp.read(16)
                if magic != b'SQLite format 3\0':
                    raise ValueError('Invalid SQLite magic bytes in downloaded dump')
                out.write(magic)
                written += 16
                while True:
                    data = inp.read(CHUNK)
                    if not data: break
                    out.write(data)
                    written += len(data)
                    if written % (512 * 1048576) < CHUNK:
                        progress('Extracted', written, None, start)
            print('\nValidating SQLite schema read-only ...')
            LocalLRCLIB(partial)
            os.replace(partial, tmp)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
    config.write_text('# Offline LRCLIB SQLite snapshot. Configured by official one-click installer\n'+str(tmp)+'\n', encoding='utf-8')
    return tmp


def choose_folder() -> Path:
    """Use a GUI directory picker instead of requiring users to paste a path."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        chosen = filedialog.askdirectory(title='Choose a drive/folder with at least 350 GiB FREE for LRCLIB')
        root.destroy()
        if chosen:
            return Path(chosen).resolve()
        raise SystemExit('Canceled folder selection; no changes.')
    except (ImportError, RuntimeError, OSError):
        pass
    # Accessible fallback if GUI disabled.
    print('Cannot open folder picker. Enter a destination directory (Enter to cancel):')
    entered = input('Folder: ').strip().strip('"')
    if not entered:
        raise SystemExit('Canceled.')
    return Path(entered).expanduser().resolve()


def offer_destination_cleanup_launcher(folder: Path) -> None:
    """Add optional shortcut beside the huge database, never overwriting a file.

    The real guarded deletion happens in the app's cleanup tool, not in the
    generated BAT. The installed application folder must remain available.
    """
    program_launcher = BASE / 'CLEANUP_LRCLIB_DATABASE.cmd'
    target = folder / 'CLEANUP_LRCLIB_DATABASE.cmd'
    if not program_launcher.is_file() or target.exists():
        return
    value = str(program_launcher.resolve())
    # Shell metacharacters in a path should not be interpolated into BAT source.
    if any(char in value for char in ('%', '!', '"', '\n', '\r')):
        print('Cleanup launcher available in the app folder (destination shortcut not created).')
        return
    try:
        target.write_bytes(('@echo off\r\n'
                            'rem Delegates to the guarded application cleanup tool.\r\n'
                            'call "' + value + '"\r\n').encode('utf-8'))
        print('Cleanup shortcut also created beside the database:', target)
    except OSError as exc:
        print('Could not create optional destination shortcut:', exc)
        print('Cleanup remains available from the application folder.')


def main():
    print('=' * 70)
    print('LRC BULK FINDER v2.1.14 - OPTIONAL OFFLINE LRCLIB AUTO INSTALLER')
    print('=' * 70)
    print('The complete LRCLIB database is NOT bundled in this application.')
    print('A 2026-10-12 official snapshot was observed extracting to 249,344 MiB (243.5 GiB).')
    print('Download size may also be very large; use a fast, stable connection.')
    print('This is a one-time, optional download. It is not needed for normal searches.')
    print('Source: https://lrclib.net/db-dumps')
    print('The installer retrieves a public snapshot directly; no account is needed.')
    print('If it cannot discover a valid link it will STOP, not guess a URL.')
    print()
    if input('Find the newest official LRCLIB snapshot online? [y/N]: ').strip().lower() != 'y':
        print('Canceled; no changes.'); return
    print('Reading LRCLIB database JSON catalog ...')
    link, advertised_size, discovered_from = discover_official_snapshot()
    print('Found via:', discovered_from)
    print('Official snapshot:', link)
    if advertised_size:
        print(f'Compressed download size: {advertised_size / (1024**3):,.1f} GiB')
    if input('Continue with this LARGE download and local installation? [y/N]: ').strip().lower() != 'y':
        print('Canceled; no changes.'); return
    folder = choose_folder()
    folder.mkdir(parents=True, exist_ok=True)
    free = get_disk_free(folder)
    print(f'Space available: {free/(1024**3):,.1f} GiB')
    if free < MIN_FREE_BYTES:
        raise SystemExit('Insufficient free space: installer requires at least 350 GiB free on the selected drive. No download started.')
    name = unquote(urlparse(link).path.rsplit('/', 1)[-1])
    if not re.fullmatch(r'[A-Za-z0-9._-]+\.sqlite3\.gz', name, re.I):
        raise SystemExit('Unrecognized snapshot filename. Nothing downloaded.')
    gz = folder / name
    db = gz.with_suffix('')
    if db.is_file():
        print('Found extracted file; validating ...')
        LocalLRCLIB(db)
    else:
        if not gz.is_file():
            print('Downloading (a partially downloaded file can be resumed on a later run) ...')
            download_resume(link, gz)
        print('Unpacking the database. This may take hours ...')
        install_from_downloaded_gzip(gz, db)
    config = BASE / 'LRCLIB_LOCAL_DB.txt'
    config.write_text('# Official offline LRCLIB SQLite snapshot; lyrics were not bundled with the application\n'+str(db)+'\n', encoding='utf-8')
    print('\nSUCCESS: database ready:', db)
    print('Run START_HERE.cmd and choose 1 (SEARCH) or 3 (LRCLIB catch-up).')
    print(f'Extracted database size: {db.stat().st_size / (1024**3):,.1f} GiB')
    print(f'Compressed archive size: {gz.stat().st_size / (1024**3):,.1f} GiB' if gz.is_file() else 'Compressed archive: not present')
    print(f'Free disk space remaining: {get_disk_free(folder) / (1024**3):,.1f} GiB')
    print('The compressed download was retained. You can safely remove it after verifying the database.')
    print('To delete the downloaded .gz, extracted SQLite database, or BOTH:')
    print('   Run CLEANUP_LRCLIB_DATABASE.cmd from this application folder.')
    offer_destination_cleanup_launcher(folder)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nCanceled safely; partial downloads may be resumed.')
        raise SystemExit(130)
    except (HTTPError, URLError, OSError, ValueError, EOFError) as exc:
        print('\nINSTALLATION NOT COMPLETED:', exc)
        print('The original program and existing database configuration are unchanged.')
        print('If both official discovery sources fail, the LRCLIB service or its listing may be unavailable.')
        raise SystemExit(1)
