"""v2.4 incremental library manifest and conservative metadata reuse.

Metadata files only. No changes to audio, tags, lyrics, or search history.
Never use stale metadata after the file's size/mtime change.
"""
from __future__ import annotations
from contextlib import closing
from pathlib import Path
import sqlite3

AUDIO_EXTENSIONS=frozenset({".mp3",".flac",".m4a",".mp4",".ogg",".opus",".wav"})

def audio_files(folder,recursive=True):
    path=Path(folder)
    iterator=path.rglob("*") if recursive else path.iterdir()
    return sorted((p for p in iterator if p.is_file() and p.suffix.casefold() in AUDIO_EXTENSIONS),
                  key=lambda p:str(p).casefold())

def safe_audio_files(folder,recursive=True):
    """Do not guess which audio file should own a colliding .lrc sidecar."""
    candidates=audio_files(folder,recursive)
    counts={}
    for path in candidates:
        key=str(path.with_suffix("")).casefold()
        counts[key]=counts.get(key,0)+1
    safe=[p for p in candidates if counts[str(p.with_suffix("")).casefold()]==1]
    collisions=[p for p in candidates if counts[str(p.with_suffix("")).casefold()]>1]
    return safe,collisions

class IncrementalLibrary:
    def __init__(self,folder):
        self.folder=Path(folder).resolve()
        self.database=self.folder/"LRC_Incremental_Library_v2_4.sqlite3"
        # Standalone optional: failing to create index must NOT abort lyrics search.
        self.connection=sqlite3.connect(self.database,timeout=15)
        self.connection.execute("PRAGMA busy_timeout=15000")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY, size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL,
            has_lrc INTEGER NOT NULL, title TEXT, artist TEXT, album TEXT,
            duration REAL, metadata_ready INTEGER NOT NULL DEFAULT 0)""")
        self.connection.commit()
        self.stats={"new":0,"changed":0,"unchanged":0,"removed":0,
                    "metadata_hits":0,"metadata_misses":0}
        self._inventoried=set()

    def inventory(self,paths):
        self._inventoried=set()
        for p in paths:
            path=Path(p)
            try:stat=path.stat()
            except OSError:continue
            key=str(path.resolve())
            self._inventoried.add(key)
            sidecar=int(path.with_suffix(".lrc").is_file())
            old=self.connection.execute(
                "SELECT size,mtime_ns,has_lrc FROM files WHERE path=?",(key,)).fetchone()
            if old is None:
                self.stats["new"]+=1
                self.connection.execute(
                    "INSERT INTO files(path,size,mtime_ns,has_lrc) VALUES(?,?,?,?)",
                    (key,stat.st_size,stat.st_mtime_ns,sidecar))
            elif old!=(stat.st_size,stat.st_mtime_ns,sidecar):
                self.stats["changed"]+=1
                self.connection.execute(
                    """UPDATE files SET size=?,mtime_ns=?,has_lrc=?,
                        metadata_ready=CASE WHEN size=? AND mtime_ns=?
                        THEN metadata_ready ELSE 0 END WHERE path=?""",
                    (stat.st_size,stat.st_mtime_ns,sidecar,
                     stat.st_size,stat.st_mtime_ns,key))
            else:
                self.stats["unchanged"]+=1
        self.connection.commit()
        # Removed files only within the folder; don't erase another subfolder
        # that was intentionally excluded by recursive=False.
        return dict(self.stats)

    def metadata(self,path,parser):
        path=Path(path)
        stat=path.stat()
        key=str(path.resolve())
        row=self.connection.execute(
            """SELECT title,artist,album,duration,size,mtime_ns,metadata_ready
               FROM files WHERE path=?""",(key,)).fetchone()
        if row and row[6] and row[4]==stat.st_size and row[5]==stat.st_mtime_ns:
            self.stats["metadata_hits"]+=1
            return row[0],row[1],row[2],row[3]
        value=parser(path)
        self.stats["metadata_misses"]+=1
        self.connection.execute(
            """INSERT INTO files(path,size,mtime_ns,has_lrc,title,artist,album,duration,metadata_ready)
               VALUES(?,?,?,?,?,?,?,?,1)
               ON CONFLICT(path) DO UPDATE SET size=excluded.size,mtime_ns=excluded.mtime_ns,
                   has_lrc=excluded.has_lrc,title=excluded.title,artist=excluded.artist,
                   album=excluded.album,duration=excluded.duration,metadata_ready=1""",
            (key,stat.st_size,stat.st_mtime_ns,int(path.with_suffix(".lrc").exists()),*value))
        self.connection.commit()
        return value

    def close(self):
        self.connection.close()
