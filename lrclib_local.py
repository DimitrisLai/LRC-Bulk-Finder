"""Read-only, bounded lookups in independently downloaded LRCLIB SQLite dumps.

No download, network, database writes, or changing MP3 tags. The returned
rows go through LRC Bulk Finder's existing strict recording matcher.
"""
from __future__ import annotations
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import quote
import re


def load_local_config(config: Path) -> Path | None:
    if not config.is_file():
        return None
    raw=next((x.strip() for x in config.read_text(encoding='utf-8-sig').splitlines()
              if x.strip() and not x.lstrip().startswith('#')), '')
    if not raw:
        return None
    path=Path(raw.strip('"')).expanduser()
    if not path.is_absolute():
        path=config.parent / path
    return path.resolve()


class LocalLRCLIB:
    def __init__(self, filename):
        self.path=Path(filename).expanduser().resolve()
        if not self.path.is_file():
            raise ValueError(f'SQLite snapshot not found: {self.path}')
        if self.path.suffix.lower() not in ('.sqlite3','.sqlite','.db'):
            raise ValueError('A decompressed .sqlite3 or .db file is required (not .gz)')
        self._validate()

    def _connect(self):
        url='file:'+quote(self.path.as_posix(),safe='/:')+'?mode=ro'
        conn=sqlite3.connect(url,uri=True,timeout=5)
        conn.row_factory=sqlite3.Row
        conn.execute('PRAGMA query_only=ON')
        conn.execute('PRAGMA busy_timeout=5000')
        return conn

    def _validate(self):
        try:
            with closing(self._connect()) as conn:
                t={r[1] for r in conn.execute('PRAGMA table_info(tracks)')}
                l={r[1] for r in conn.execute('PRAGMA table_info(lyrics)')}
                required_t={'id','name','name_lower','artist_name','artist_name_lower','duration','last_lyrics_id'}
                required_l={'id','synced_lyrics'}
                if not required_t.issubset(t) or not required_l.issubset(l):
                    raise ValueError('Not a compatible LRCLIB tracks/lyrics SQLite database')
                # Prepare the real query to catch incompatible schema before the run.
                conn.execute('SELECT t.name, l.synced_lyrics FROM tracks t '
                             'JOIN lyrics l ON l.id=t.last_lyrics_id LIMIT 0')
        except sqlite3.DatabaseError as ex:
            raise ValueError(f'Cannot read LRCLIB SQLite database: {ex}') from ex

    def search(self, variants, duration=0.0):
        """Seek likely rows via indexed title; bound result count for huge dumps.

        No full-table scans, FTS syntax dependency, or unbounded searches.
        Exact artist/title is preferred; title-prefix handles punctuation / edits.
        Strict validation is performed by the caller, not here.
        """
        out=[];seen=set()
        sql_exact=('SELECT t.id, t.name, t.artist_name, t.duration, l.synced_lyrics '
                   'FROM tracks t JOIN lyrics l ON l.id=t.last_lyrics_id '
                   'WHERE t.name_lower=? AND t.artist_name_lower=? '
                   'AND l.synced_lyrics IS NOT NULL LIMIT 100')
        sql_prefix=('SELECT t.id, t.name, t.artist_name, t.duration, l.synced_lyrics '
                    'FROM tracks t JOIN lyrics l ON l.id=t.last_lyrics_id '
                    'WHERE t.name_lower>=? AND t.name_lower<? '
                    'AND t.artist_name_lower=? '
                    'AND l.synced_lyrics IS NOT NULL LIMIT 100')
        with closing(self._connect()) as conn:
            for title,artist in list(variants)[:2]:
                title=str(title or '').strip().lower()
                artist=str(artist or '').strip().lower()
                if len(title)<3 or len(artist)<2:continue
                # Indexed exact lookup, plus bounded title-prefix for remix variants.
                stripped=re.split(r'\s+[\[(]|\s+[-–—]\s+',title,maxsplit=1)[0].strip()
                queries=[(sql_exact,(title,artist))]
                if len(stripped)>=5:
                    queries.append((sql_prefix,(stripped,stripped+chr(0x10ffff),artist)))
                for sql,args in queries:
                    for row in conn.execute(sql,args):
                        if row[0] in seen:continue
                        seen.add(row[0])
                        out.append({'id':row[0], 'trackName':row[1], 'artistName':row[2],
                                    'duration':row[3], 'syncedLyrics':row[4]})
                        if len(out)>=160:return out
        return out
