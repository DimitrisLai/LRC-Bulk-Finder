#!/usr/bin/env python3
"""Build the optional SMALL public Greeklish vocabulary SQLite database.

Source of truth: Greek_Words_Expanded.csv followed by Greek_Words.csv.
Only independent Greeklish WORD mappings are included, never a music
library listing, MP3 filenames, or private user-specific full-title aliases.
Run: python BUILD_GREEK_LEXICON_DB.py
Optional: python BUILD_GREEK_LEXICON_DB.py --output <path>
The app can use its CSV files directly if SQLite is absent or corrupt.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import os
import re
import sqlite3
import tempfile
from pathlib import Path

SCHEMA_VERSION = 1
APPLICATION_ID = 0x4C524347  # "LRCG"
SOURCE_FILES = ('Greek_Words_Expanded.csv', 'Greek_Words.csv')


def source_rows(root: Path):
    all_words = {}
    sources = []
    for filename in SOURCE_FILES:
        path = root / filename
        data = path.read_bytes()
        sources.append((filename, hashlib.sha256(data).hexdigest()))
        for number, row in enumerate(csv.DictReader(data.decode('utf-8-sig').splitlines()), 2):
            key = (row.get('greeklish') or '').strip().casefold()
            greek = (row.get('greek') or '').strip()
            if not re.fullmatch(r'[a-z]+', key):
                raise ValueError(f'{filename}:{number}: invalid Latin word {key!r}')
            if not re.fullmatch(r"[\u0370-\u03ff\u1f00-\u1fff\s'’\-]+", greek):
                raise ValueError(f'{filename}:{number}: invalid Greek {greek!r}')
            if key in all_words and all_words[key][1] == filename:
                raise ValueError(f'{filename}:{number}: duplicate {key!r}')
            all_words[key] = (greek, filename)
    return all_words, sources


def build(root: Path | None = None, output: Path | None = None):
    root = (root or Path(__file__).resolve().parent).resolve()
    output = (output or root / 'Greek_Lexicon.sqlite3').resolve()
    if not output.parent.is_dir():
        output.parent.mkdir(parents=True, exist_ok=True)
    words, source_digests = source_rows(root)
    handle = None
    try:
        with tempfile.NamedTemporaryFile(prefix='.lrc_greeklex_',suffix='.sqlite3',
                                         dir=output.parent,delete=False) as temp:
            handle = Path(temp.name)
        # Use a fresh file, not a WAL snapshot or an in-place user mutation.
        with sqlite3.connect(handle) as db:
            db.execute(f'PRAGMA application_id={APPLICATION_ID}')
            db.execute(f'PRAGMA user_version={SCHEMA_VERSION}')
            db.execute('CREATE TABLE words (greeklish TEXT PRIMARY KEY,'
                       'greek TEXT NOT NULL, source TEXT NOT NULL)')
            db.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            db.executemany('INSERT INTO words VALUES (?,?,?)',
                           ((word, greek, source) for word,(greek,source)
                            in sorted(words.items())))
            db.executemany('INSERT INTO metadata VALUES (?,?)',
                           [(key,digest) for key,digest in source_digests]+
                           [('schema_version',str(SCHEMA_VERSION)),
                            ('word_count',str(len(words)))])
            assert db.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
            assert db.execute('SELECT COUNT(*) FROM words').fetchone()[0] == len(words)
        os.replace(handle, output)
        handle = None
        return output, len(words)
    finally:
        if handle is not None:
            try: handle.unlink()
            except OSError: pass


def main():
    parser = argparse.ArgumentParser(description='Rebuild the small public Greeklish SQLite lexicon')
    parser.add_argument('--output',type=Path,help='Optional output SQLite filename')
    args = parser.parse_args()
    db, count = build(output=args.output)
    print(f'Greeklish database ready: {db} ({count} curated word spellings)')
    print('Contains only standalone dictionary words, not user tracks or filenames.')


if __name__ == '__main__':
    main()
