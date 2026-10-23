"""v2.4.5 optional usability utilities. No changes to the search/matching engine.

All library inspection is read-only. Corrected LRCs are *unverified candidates*
written exclusively with 'x'; existing source LRCs and audio are never modified.
"""
from __future__ import annotations
import csv
import json
import math
import os
import platform
import re
import sys
import urllib.request
from pathlib import Path

AUDIO_EXTS = frozenset(('.mp3', '.flac', '.m4a', '.mp4', '.ogg', '.opus', '.wav'))
VERSION = '2.9.4'
MAX_TRACKS = 100_000
MAX_LRC_BYTES = 150_000
STAMP = re.compile(r'\[(\d{1,4}):([0-5]\d)\.(\d{2,3})\]')
SUPPORTED_LRC = re.compile(r'^\[[^\]]+\]', re.M)


def scan_library(folder, recursive=True, limit=MAX_TRACKS):
    """Build an inventory using only filenames and sidecar existence.

    'Has LRC' means a sidecar exists, NOT that the lyrics are verified.
    Avoid following symlinks (including folders) and enforce a track limit.
    """
    root = Path(folder)
    if not root.is_dir() or root.is_symlink():
        raise ValueError('Choose an existing, non-symlink music folder')
    if not isinstance(limit, int) or not 1 <= limit <= MAX_TRACKS:
        raise ValueError('Invalid library inventory limit')
    def audio_paths():
        if not recursive:
            yield from root.iterdir()
            return
        for base, dirs, files in os.walk(root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not (Path(base) / d).is_symlink())
            for name in sorted(files):
                yield Path(base) / name
    paths = audio_paths()
    rows = []
    for p in paths:
        if p.is_symlink() or p.suffix.casefold() not in AUDIO_EXTS or not p.is_file():
            continue
        if len(rows) >= limit:
            raise ValueError('Library exceeds the 100,000-track dashboard limit; select a smaller folder')
        lrc = p.with_suffix('.lrc')
        candidate = p.with_suffix('.candidate.lrc')
        candidates = [candidate] if candidate.is_file() and not candidate.is_symlink() else []
        candidates += sorted(x for x in p.parent.glob(p.stem + '.candidate.*.lrc')
                             if x.is_file() and not x.is_symlink()
                             and re.fullmatch(r'\.candidate\.\d+\.lrc', x.name[len(p.stem):]))
        same_stem = [p.with_suffix(ext) for ext in AUDIO_EXTS
                     if ext != p.suffix.casefold() and p.with_suffix(ext).exists()]
        if same_stem:
            status = 'Ambiguous audio'
        elif lrc.is_file() and not lrc.is_symlink():
            status = 'Has LRC'
        elif candidates:
            status = 'Needs review'
        else:
            status = 'Missing LRC'
        rows.append({'path': str(p), 'name': p.name, 'folder': str(p.parent),
                     'status': status, 'candidates': len(candidates)})
    rows.sort(key=lambda r: r['path'].casefold())
    return rows


def inventory_counts(rows):
    labels = ('Has LRC', 'Needs review', 'Missing LRC', 'Ambiguous audio')
    return {'Total': len(rows), **{k: sum(r['status'] == k for r in rows) for k in labels}}


def export_inventory(rows, destination):
    """User-initiated export, exclusive create; no existing report is replaced."""
    path = Path(destination)
    with path.open('x', encoding='utf-8-sig', newline='') as out:
        w = csv.writer(out)
        w.writerow(('Audio file', 'Folder', 'LRC status', 'Candidates'))
        for r in rows:
            # Spreadsheet viewers may interpret attacker-controlled music
            # filenames as formulas. Prefix dangerous CSV cells with an
            # apostrophe; no source filename is changed.
            def cell(value):
                string = str(value)
                return "'" + string if string.lstrip().startswith(('=', '+', '-', '@')) else string
            w.writerow(tuple(cell(v) for v in (r['name'], r['folder'], r['status'], r['candidates'])))
    return path


def parse_version(tag):
    m = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', str(tag or '').strip())
    return tuple(map(int, m.groups())) if m else None


def check_github_update(current=VERSION, opener=None):
    """Manual, opt-in request to official repository; no file data transmitted."""
    if parse_version(current) is None:
        raise ValueError('Current application version is invalid')
    url = 'https://api.github.com/repos/DimitrisLai/LRC-Bulk-Finder/releases/latest'
    req = urllib.request.Request(url, headers={'Accept': 'application/vnd.github+json',
                                                 'User-Agent': 'LRC-Bulk-Finder-update-check/2.7.0'})
    fetch = opener or urllib.request.urlopen
    with fetch(req, timeout=7) as response:
        raw = response.read(64_001)
    if len(raw) > 64_000:
        raise ValueError('Update response is too large')
    data = json.loads(raw.decode('utf-8'))
    version = str(data.get('tag_name', ''))
    parsed = parse_version(version)
    if parsed is None:
        raise ValueError('GitHub returned an unexpected version')
    link = str(data.get('html_url', ''))
    if not link.startswith('https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/'):
        raise ValueError('GitHub returned an unexpected release URL')
    return {'latest': version, 'newer': parsed > parse_version(current), 'url': link}


def diagnostic_text(*, frozen=False, worker_exists=None, profiles=None):
    """No paths, environment variables, filenames, usernames or lyric text."""
    lines = ['LRC Bulk Finder — local diagnostic summary', 'Application version: ' + VERSION,
             'OS: ' + platform.system(), 'Architecture: ' + platform.machine(),
             'Python: ' + platform.python_version(), 'Standalone build: ' + ('yes' if frozen else 'no')]
    if worker_exists is not None:
        lines.append('Standalone worker beside GUI: ' + ('yes' if worker_exists else 'no'))
    if profiles is not None:
        lines.append('Saved profile count: ' + str(int(profiles)))
    lines += ['No personal paths, music titles, tags, lyrics or credentials are included.',
              'Generated on request; never uploaded automatically.']
    return '\n'.join(lines) + '\n'


def save_diagnostics(path, **kwargs):
    target = Path(path)
    with target.open('x', encoding='utf-8', newline='\n') as f:
        f.write(diagnostic_text(**kwargs))
    return target


def shift_lrc_timestamps(text, offset):
    """Shift timestamp tags, preserve lyric text & metadata, refuse negative times.

    The leading candidate-marker line is always retained without time shifting.
    An existing marker is removed from the input then restored once on output.
    """
    if not isinstance(text, str) or len(text.encode('utf-8')) > MAX_LRC_BYTES:
        raise ValueError('LRC file exceeds the 150 KB timing-repair limit')
    try:
        offset = float(offset)
    except (TypeError, ValueError):
        raise ValueError('Offset must be a number of seconds') from None
    if not math.isfinite(offset) or abs(offset) > 300:
        raise ValueError('Offset must be between -300 and +300 seconds')
    lines = text.replace('\r\n', '\n').replace('\r', '\n').splitlines()
    lines = [line for line in lines if line.strip() != '[00:00.00] candidate']
    changed = 0
    shifted = []
    for line in lines:
        def substitute(match):
            nonlocal changed
            minutes, seconds, frac = match.groups()
            centis = int(round(int(frac) / (10 ** len(frac)) * 100))
            original = (int(minutes) * 60 + int(seconds)) * 100 + centis
            result = original + round(offset * 100)
            if result < 0:
                raise ValueError('Offset would create a negative timestamp; choose a smaller shift')
            if result > 36_000 * 100:
                raise ValueError('Timestamp exceeds the supported 10-hour range')
            m, rest = divmod(result, 6000)
            sec, c = divmod(rest, 100)
            changed += 1
            return f'[{m:02d}:{sec:02d}.{c:02d}]'
        shifted.append(STAMP.sub(substitute, line))
    if changed < 1:
        raise ValueError('No supported [mm:ss.xx] timestamps found')
    return '[00:00.00] candidate\n' + '\n'.join(shifted).rstrip() + '\n', changed


def save_shifted_candidate(audio_file, original_lrc, shifted_text):
    """Exclusive write of unverified numbered candidate. Even existing .lrc safe."""
    audio, src = Path(audio_file), Path(original_lrc)
    if (not audio.is_file() or audio.is_symlink() or
        audio.suffix.casefold() not in AUDIO_EXTS):
        raise ValueError('Choose an existing supported non-symlink audio track')
    if not src.is_file() or src.is_symlink() or src.parent != audio.parent:
        raise ValueError('Choose an LRC in the same folder as its audio track')
    permitted = {audio.with_suffix('.lrc').name, audio.with_suffix('.candidate.lrc').name}
    if not (src.name in permitted or re.fullmatch(re.escape(audio.stem) + r'\.candidate\.\d+\.lrc', src.name)):
        raise ValueError('Selected LRC does not belong to that audio track')
    if not shifted_text.startswith('[00:00.00] candidate\n'):
        raise ValueError('Unverified candidate marker must be the first line')
    if len(shifted_text.encode('utf-8')) > MAX_LRC_BYTES:
        raise ValueError('Candidate LRC exceeds 150 KB')
    if not STAMP.search(shifted_text.split('\n', 1)[1]):
        raise ValueError('No valid timestamped lyrics in candidate')
    # Prevent ambiguous sidecar association when different audio formats share stem.
    if any(audio.with_suffix(ext).exists() for ext in AUDIO_EXTS if ext != audio.suffix.casefold()):
        raise FileExistsError('More than one audio file has this name; rename before saving')
    base = audio.with_suffix('.candidate.lrc')
    candidates = [base] + [audio.with_suffix(f'.candidate.{n}.lrc') for n in range(2, 1000)]
    for dest in candidates:
        try:
            with dest.open('x', encoding='utf-8', newline='\n') as f:
                f.write(shifted_text)
            return dest
        except FileExistsError:
            continue
    raise FileExistsError('No candidate filename available')
