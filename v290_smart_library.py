"""v2.9 Smart Library: incremental local SQLite inventory + conservative LRC QC.

Read-only access to source audio/ID3/LRC, never repair or promote automatically.
Only the app's private SQLite cache is modified. Full scans use one transaction,
and Cancel/exception rollback both row updates and stale-row deletion.
"""
from __future__ import annotations
from pathlib import Path
from collections import Counter
from dataclasses import dataclass
import csv
import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import unicodedata

from v260_studio import AUDIO_EXTENSIONS, MAX_LRC_BYTES, read_lyric_file
from v270_precision import validate_timing

INDEX_VERSION = 1
MAX_TRACKS = 100_000
MAX_REPORT_ROWS = 100_000
PAGE_SIZE = 200
MIN_SCAN_INTERVAL = 0
ALLOWED_STATUSES = ("All", "Issues only", "Missing LRC", "Needs review", "Has LRC", "Ambiguous audio")
LRC_HEADERS = re.compile(r"^\[(ti|title|ar|artist|al|album|offset):([^\]]*)\]\s*$", re.I)
STAMP_LIKE = re.compile(r"^\[\d{1,4}:[^\]]+\]")
EXT_PRIORITY = tuple(sorted(AUDIO_EXTENSIONS))

class ScanCancelled(RuntimeError):
    """Cancellation is not a successful, partially committed scan."""

@dataclass(frozen=True)
class IndexResult:
    total: int
    audited: int
    cached: int
    issues: int
    elapsed: float
    root: str

def private_db_path():
    base = Path(os.environ.get("APPDATA") or Path.home()/".config")/"LRCBulkFinder"
    return base/"smart_library_v290.sqlite3"

def canonical_root(folder):
    p = Path(folder)
    if not p.is_dir() or p.is_symlink():
        raise ValueError("Choose an existing non-symlink music folder")
    return str(p.resolve())

def root_id(folder):
    return hashlib.sha256(folder.casefold().encode("utf-8","surrogatepass")).hexdigest()

def _open_db(path=None):
    target=Path(path) if path else private_db_path()
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.is_symlink() or target.parent.is_symlink():
        raise ValueError("Unsafe Smart Library cache path")
    db=sqlite3.connect(str(target),timeout=15,isolation_level=None)
    try:
        db.execute("PRAGMA busy_timeout=15000")
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA journal_mode=WAL")
        version=int(db.execute("PRAGMA user_version").fetchone()[0])
        if version>INDEX_VERSION:
            raise ValueError("Smart Library database was created by a newer version")
        if version<1:
            db.execute("BEGIN IMMEDIATE")
            try:
                db.executescript("""CREATE TABLE IF NOT EXISTS tracks (
                    root_key TEXT NOT NULL, rel_path TEXT NOT NULL,
                    audio_path TEXT NOT NULL, audio_name TEXT NOT NULL,
                    status TEXT NOT NULL, flags TEXT NOT NULL,
                    detail TEXT NOT NULL, lrc_path TEXT NOT NULL,
                    search_text TEXT NOT NULL,
                    audio_size INTEGER NOT NULL, audio_mtime INTEGER NOT NULL,
                    lrc_size INTEGER NOT NULL, lrc_mtime INTEGER NOT NULL,
                    deep INTEGER NOT NULL, inspected REAL NOT NULL,
                    PRIMARY KEY(root_key,rel_path)
                );
                CREATE INDEX IF NOT EXISTS tracks_by_status
                    ON tracks(root_key,status,audio_name);
                CREATE INDEX IF NOT EXISTS tracks_by_root
                    ON tracks(root_key,audio_name);
                CREATE TABLE IF NOT EXISTS review_state (root_key TEXT NOT NULL, rel_path TEXT NOT NULL, decision TEXT NOT NULL, PRIMARY KEY(root_key,rel_path));
                CREATE TABLE IF NOT EXISTS scan_history (root_key TEXT NOT NULL, scanned REAL NOT NULL, total INTEGER NOT NULL, issues INTEGER NOT NULL, audited INTEGER NOT NULL, cached INTEGER NOT NULL);""")
                db.execute("PRAGMA user_version=1")
                db.commit()
            except BaseException:
                db.rollback()
                raise
        return db
    except BaseException:
        db.close()
        raise

def _decode_audit(path):
    """No lyrics are persisted in database; only summaries and issue codes."""
    raw=path.read_bytes()
    if not raw:
        return None,["Empty LRC"],"Empty timed-lyrics sidecar"
    if len(raw)>MAX_LRC_BYTES:
        return None,["Oversized LRC"],"File exceeds 512 KiB safety limit"
    flags=[]
    try:
        if raw.startswith((b"\xff\xfe",b"\xfe\xff")):
            flags.append("Encoding: UTF-16")
            return None,flags,"UTF-16 is not supported in Lyrics Studio"
        text=raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text=raw.decode("cp1253")
            flags.append("Encoding: Greek CP1253")
        except UnicodeDecodeError:
            return None,["Encoding invalid"],"Unable to decode LRC with UTF-8 or CP1253"
    offset=0
    title=""
    for line in text.splitlines()[:2000]:
        meta=LRC_HEADERS.fullmatch(line.strip())
        if meta:
            key=meta.group(1).lower()
            if key=="offset":
                try:
                    offset=int(meta.group(2).strip())
                    if abs(offset)>=5000:
                        flags.append("Large global offset")
                except ValueError:
                    flags.append("Malformed offset")
            elif key in ("ti","title") and not title:
                title=meta.group(2).strip()
        elif STAMP_LIKE.match(line.strip()) and re.search(r"\[\d+:[^\]]+\]",line):
            if not re.match(r"^\[(?:\d{1,3}):[0-5]\d(?:\.\d{1,3})?\]",line.strip()):
                flags.append("Malformed timestamp")
    try:
        lines=read_lyric_file(path)
    except (ValueError,OSError,UnicodeError) as ex:
        flags.append("Invalid or untimed LRC")
        return None,list(dict.fromkeys(flags)),str(ex)[:180]
    if len(lines)<2:
        flags.append("Very few lyric lines")
    return (lines,title),list(dict.fromkeys(flags)),f"{len(lines)} timestamped lines"

def _norm_title(s):
    s=unicodedata.normalize("NFKC",s).casefold()
    s=re.sub(r"[^-\w]+"," ",s,flags=re.U)
    return " ".join(s.split())

def audit_lrc(audio,lrc,deep=False):
    """Return (issues, detail); informational flags are conservative suggestions."""
    p=Path(lrc)
    if not p.is_file() or p.is_symlink():
        return ["Missing LRC"],"No regular timed lyric sidecar"
    try:
        decoded,flags,detail=_decode_audit(p)
    except (OSError,ValueError) as ex:
        return ["Unreadable LRC"],str(ex)[:180]
    if decoded:
        lines,title=decoded
        duration=0.0
        if deep:
            from v260_player import duration_seconds
            duration=duration_seconds(audio)
        warnings=validate_timing(lines,duration)
        for w in warnings:
            mapped={"duplicate":"Duplicate timestamps","order":"Out-of-order timestamps",
                    "duration":"Beyond audio duration","gap":"Long lyric gap",
                    "close":"Very close lyric lines","range":"Invalid timestamp"}
            if w.code in mapped and mapped[w.code] not in flags:
                flags.append(mapped[w.code])
        if title:
            stem=_norm_title(Path(audio).stem)
            t=_norm_title(title)
            if t and t not in stem:
                flags.append("Title metadata differs")
        if len(lines)>1 and lines[0].seconds>=90:
            flags.append("Late first lyric")
        if len(lines)>1 and lines[-1].seconds<=5:
            flags.append("Very early last lyric")
    return flags,"; ".join(dict.fromkeys([detail,*flags]))[:450]

def _folder_audio(folder):
    files=[]
    names=os.listdir(folder)
    for name in names:
        p=Path(folder)/name
        if p.suffix.casefold() in AUDIO_EXTENSIONS and p.is_file() and not p.is_symlink():
            files.append(p)
    return files,names

def _candidate_exists(audio_name,names):
    stem=Path(audio_name).stem.casefold()
    return any(x.casefold()==stem+".candidate.lrc" or
           bool(re.fullmatch(re.escape(stem)+r"\.candidate\.\d+\.lrc",x.casefold()))
           for x in names)

def _collect_paths(root,recursive,stop):
    if recursive:
        for folder, dirs, names in os.walk(root,followlinks=False):
            if stop.is_set():raise ScanCancelled("Library scan safely cancelled")
            dirs[:]=sorted(d for d in dirs if not (Path(folder)/d).is_symlink())
            yield Path(folder),names
    else:
        if stop.is_set():raise ScanCancelled("Library scan safely cancelled")
        yield Path(root),os.listdir(root)

def _read_existing(db,key):
    return {row[0]:row[1:] for row in db.execute(
        "SELECT rel_path,audio_size,audio_mtime,lrc_size,lrc_mtime,deep FROM tracks WHERE root_key=?",(key,))}

def scan_index(folder,*,recursive=True,deep=False,cancel=None,progress=None,db_path=None,track_limit=MAX_TRACKS):
    start=time.monotonic()
    stop=cancel or threading.Event()
    root=canonical_root(folder)
    if not 1<=track_limit<=MAX_TRACKS:
        raise ValueError("Invalid track limit")
    key=root_id(root)
    db=_open_db(db_path)
    audited=cached=total=issues=0
    try:
        known=_read_existing(db,key)
        # All updates, including deletes, are atomic. Callback may request cancel.
        db.execute("BEGIN IMMEDIATE")
        present=set()
        for folder_path,names in _collect_paths(root,recursive,stop):
            tracks=[folder_path/n for n in sorted(names,key=str.casefold)
                    if Path(n).suffix.casefold() in AUDIO_EXTENSIONS
                    and (folder_path/n).is_file() and not (folder_path/n).is_symlink()]
            stems=Counter(p.stem.casefold() for p in tracks)
            candidate_names=[n for n in names if n.lower().endswith(".lrc")]
            for audio in tracks:
                if stop.is_set():raise ScanCancelled("Library scan safely cancelled")
                total+=1
                if total>track_limit:raise ValueError("Library exceeds selected maximum; choose smaller folder")
                rel=str(audio.relative_to(root))
                present.add(rel)
                lrc=audio.with_suffix(".lrc")
                has_lrc=lrc.is_file() and not lrc.is_symlink()
                if has_lrc and lrc.stat().st_size>MAX_LRC_BYTES:
                    # Audit will mark Oversized LRC instead of reading it.
                    pass
                ac=audio.stat()
                lc=lrc.stat() if has_lrc else None
                sig=(ac.st_size,ac.st_mtime_ns,lc.st_size if lc else -1,
                     lc.st_mtime_ns if lc else -1,int(bool(deep)))
                ambiguous=stems[audio.stem.casefold()]>1
                candidate=_candidate_exists(audio.name,candidate_names)
                status=("Ambiguous audio" if ambiguous else
                        "Has LRC" if has_lrc else
                        "Needs review" if candidate else "Missing LRC")
                previous=known.get(rel)
                # If filename/status changed without changed stat, must recompute.
                if previous==sig:
                    row=db.execute("SELECT status,flags FROM tracks WHERE root_key=? AND rel_path=?",(key,rel)).fetchone()
                    if row and row[0]==status:
                        cached+=1
                        if json.loads(row[1]):issues+=1
                        continue
                if has_lrc:
                    flags,detail=audit_lrc(audio,lrc,deep=deep)
                else:
                    flags,detail=(["Candidate needs review"] if candidate else ["Missing LRC"],
                                  "Unverified candidate available" if candidate else "No LRC present")
                if ambiguous:
                    flags.insert(0,"Ambiguous audio stem")
                flags=list(dict.fromkeys(flags))
                if flags:issues+=1
                db.execute("""INSERT INTO tracks
                   (root_key,rel_path,audio_path,audio_name,status,flags,detail,lrc_path,
                    search_text,audio_size,audio_mtime,lrc_size,lrc_mtime,deep,inspected)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(root_key,rel_path) DO UPDATE SET
                   audio_path=excluded.audio_path,audio_name=excluded.audio_name,status=excluded.status,
                   flags=excluded.flags,detail=excluded.detail,lrc_path=excluded.lrc_path,
                   search_text=excluded.search_text,audio_size=excluded.audio_size,audio_mtime=excluded.audio_mtime,
                   lrc_size=excluded.lrc_size,lrc_mtime=excluded.lrc_mtime,
                   deep=excluded.deep,inspected=excluded.inspected""",
                   (key,rel,str(audio),audio.name,status,json.dumps(flags,ensure_ascii=False),
                    detail,str(lrc) if has_lrc else "",(audio.name+" "+str(audio)).casefold(),*sig,time.time()))
                audited+=1
                if progress and total%250==0:
                    progress(total,audited,cached)
        if stop.is_set():raise ScanCancelled("Library scan safely cancelled")
        # Recursive and non-recursive inventories have different coverage:
        # when non-recursive, do not delete previously indexed deeper paths.
        stale=set(known)-present
        if not recursive:
            stale={p for p in stale if len(Path(p).parts)==1}
        for rel in stale:
            db.execute("DELETE FROM tracks WHERE root_key=? AND rel_path=?",(key,rel))
        db.execute('INSERT INTO scan_history(root_key,scanned,total,issues,audited,cached) VALUES(?,?,?,?,?,?)',(key,time.time(),total,issues,audited,cached))
        db.execute('DELETE FROM scan_history WHERE rowid IN (SELECT rowid FROM scan_history WHERE root_key=? ORDER BY scanned DESC LIMIT -1 OFFSET 25)',(key,))
        db.commit()
        if progress:progress(total,audited,cached)
        return IndexResult(total,audited,cached,issues,time.monotonic()-start,root)
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()

def _where(root,status,query):
    key=root_id(canonical_root(root))
    sql=" WHERE tracks.root_key=?"
    args=[key]
    if status not in ALLOWED_STATUSES:
        raise ValueError("Invalid status filter")
    if status=="Issues only":
        sql+=" AND tracks.flags!='[]'"
    elif status!="All":
        sql+=" AND tracks.status=?"
        args.append(status)
    if query:
        # Escaped LIKE literals, parameterized; no user-controlled SQL syntax.
        escaped=query.casefold().replace("\\","\\\\").replace("%","\\%").replace("_","\\_")
        sql+=" AND tracks.search_text LIKE ? ESCAPE '\\'"
        args.append("%"+escaped+"%")
    return sql,args

def read_page(root,*,status="All",query="",page=0,page_size=PAGE_SIZE,db_path=None):
    if not 0<=page<=MAX_TRACKS or not 1<=page_size<=PAGE_SIZE or len(query)>160:
        raise ValueError("Invalid page or search")
    db=_open_db(db_path)
    try:
        where,args=_where(root,status,query)
        count=db.execute("SELECT COUNT(*) FROM tracks"+where,args).fetchone()[0]
        rows=db.execute("""SELECT tracks.audio_path,tracks.audio_name,tracks.status,tracks.flags,tracks.detail,tracks.lrc_path, COALESCE(review_state.decision, '')
                         FROM tracks LEFT JOIN review_state ON tracks.root_key=review_state.root_key AND tracks.rel_path=review_state.rel_path"""+where+
                         " ORDER BY tracks.audio_name COLLATE NOCASE,tracks.rel_path LIMIT ? OFFSET ?",
                         (*args,page_size,page*page_size)).fetchall()
        return count,[{"path":x[0],"name":x[1],"status":x[2],
                       "flags":json.loads(x[3]),"detail":x[4],"lrc":x[5],"review":x[6]} for x in rows]
    finally:db.close()

def counts(root,db_path=None):
    db=_open_db(db_path)
    try:
        key=root_id(canonical_root(root))
        total,issues=db.execute("SELECT COUNT(*),SUM(CASE WHEN flags!='[]' THEN 1 ELSE 0 END) FROM tracks WHERE root_key=?",(key,)).fetchone()
        return {"total":total or 0,"issues":issues or 0,
                "missing":db.execute("SELECT COUNT(*) FROM tracks WHERE root_key=? AND status='Missing LRC'",(key,)).fetchone()[0]}
    finally:db.close()

def _csv_safe(value):
    string=str(value)
    return "'"+string if string.lstrip().startswith(("=","+","-","@","\t","\r","\n")) else string

def export_issues(root,destination,*,status="Issues only",query="",db_path=None):
    """Only user-confirmed export, exclusive create; streaming and formula-safe."""
    target=Path(destination)
    if target.exists():
        raise FileExistsError("Refusing to overwrite an existing CSV")
    db=_open_db(db_path)
    try:
        where,args=_where(root,status,query)
        # Prevent accidentally dumping a very large unfiltered report.
        count=db.execute("SELECT COUNT(*) FROM tracks"+where,args).fetchone()[0]
        if count>MAX_REPORT_ROWS:raise ValueError("Too many rows for CSV export")
        fd=os.open(target,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        try:
            with os.fdopen(fd,"w",encoding="utf-8-sig",newline="") as handle:
                writer=csv.writer(handle)
                writer.writerow(("Audio filename","Audio path","Status","QC warnings","Details","Sidecar LRC"))
                for row in db.execute("SELECT audio_name,audio_path,status,flags,detail,lrc_path FROM tracks"+where+" ORDER BY audio_name COLLATE NOCASE,rel_path",args):
                    items=(row[0],row[1],row[2],"; ".join(json.loads(row[3])),row[4],row[5])
                    writer.writerow(tuple(_csv_safe(x) for x in items))
                handle.flush();os.fsync(handle.fileno())
        except BaseException:
            target.unlink(missing_ok=True)
            raise
        return count
    finally:db.close()


def set_review_state(root,audio_path,decision,db_path=None):
    if decision not in ("bookmarked","reviewed","clear"):
        raise ValueError("Invalid review state")
    resolved=canonical_root(root)
    audio=Path(audio_path)
    try:rel=str(audio.relative_to(resolved))
    except ValueError as ex:raise ValueError("Track is outside chosen library") from ex
    db=_open_db(db_path)
    key=root_id(resolved)
    try:
        db.execute("BEGIN IMMEDIATE")
        if not db.execute("SELECT 1 FROM tracks WHERE root_key=? AND rel_path=?",(key,rel)).fetchone():
            raise ValueError("Choose an indexed track")
        if decision=="clear":
            db.execute("DELETE FROM review_state WHERE root_key=? AND rel_path=?",(key,rel))
        else:
            db.execute("INSERT INTO review_state(root_key,rel_path,decision) VALUES(?,?,?) ON CONFLICT(root_key,rel_path) DO UPDATE SET decision=excluded.decision",(key,rel,decision))
        db.commit()
    except BaseException:
        db.rollback();raise
    finally:db.close()

def history(root,db_path=None):
    db=_open_db(db_path)
    try:
        key=root_id(canonical_root(root))
        return [{"scanned":row[0],"total":row[1],"issues":row[2],"audited":row[3],"cached":row[4]}
                for row in db.execute("SELECT scanned,total,issues,audited,cached FROM scan_history WHERE root_key=? ORDER BY scanned DESC LIMIT 25",(key,))]
    finally:db.close()
