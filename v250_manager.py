"""v2.5.0 Library Manager: read-only search reports, exact selective retries,
creation-only undo journal. Does not modify audio, metadata or existing lyrics.

Security invariants:
* Selected-track manifest is bound to a resolved library root and an exact list
  of eligible audio paths, fails closed on missing/replaced/outside paths.
* Undo only deletes new .lrc or .candidate*.lrc files recorded on successful
  exclusive creation in THIS run, and only if size, mtime and SHA256 still match.
* Historical reports are untrusted/stale diagnostic hints, not verification.
"""
from __future__ import annotations
import csv
import hashlib
import json
import os
import re
import secrets
import tempfile
import time
from pathlib import Path
from typing import Iterable

SCHEMA = 1
MAX_SELECTION = 2500
MAX_JOURNAL_BYTES = 1_000_000
MAX_REPORT_BYTES = 30_000_000
MAX_REASON_LENGTH = 1200
AUDIO_EXTS = frozenset({'.mp3','.flac','.m4a','.mp4','.ogg','.opus','.wav'})
CANDIDATE_RE = re.compile(r'^.+\.candidate(?:\.[2-9]\d*)?\.lrc$', re.I)
SESSION_RE = re.compile(r'^[a-f0-9]{32}$')


def settings_dir(appdata=None):
    base = Path(appdata) if appdata is not None else Path(os.environ.get('APPDATA') or Path.home()/'.config')
    return base/'LRCBulkFinder'/'manager_sessions'


def _inside(child, root):
    try: return child.is_relative_to(root)
    except (ValueError, TypeError): return False


def _file_digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(65536),b''):h.update(chunk)
    return h.hexdigest()


def _session_path(session_id, appdata=None):
    if not SESSION_RE.fullmatch(str(session_id)):
        raise ValueError('Invalid session identifier')
    return settings_dir(appdata)/('session_'+session_id+'.jsonl')


def start_session(folder, *, appdata=None, label='Search'):
    root=Path(folder).resolve(strict=True)
    if not root.is_dir() or Path(folder).is_symlink():
        raise ValueError('Choose an existing non-symlink music folder')
    base=settings_dir(appdata);base.mkdir(parents=True,exist_ok=True)
    for _ in range(5):
        sid=secrets.token_hex(16)
        path=_session_path(sid,appdata)
        try:
            with path.open('x',encoding='utf-8',newline='\n') as f:
                f.write(json.dumps({'schema':SCHEMA,'kind':'session','id':sid,'root':str(root),
                    'label':str(label)[:64],'created':time.time()},ensure_ascii=False)+'\n')
                f.flush();os.fsync(f.fileno())
            return sid
        except FileExistsError:continue
    raise OSError('Could not create a unique session')


def _records(session_id, appdata=None):
    path=_session_path(session_id,appdata)
    if path.is_symlink():raise ValueError('Session journal cannot be a symlink')
    if path.stat().st_size>MAX_REPORT_BYTES:raise ValueError('Session journal is unexpectedly large')
    events=[]
    with path.open(encoding='utf-8') as f:
        for line in f:
            if not line.endswith('\n'):break # ignore crash-truncated final line
            try:entry=json.loads(line)
            except (ValueError,TypeError):break
            if not isinstance(entry,dict) or entry.get('schema')!=SCHEMA:break
            events.append(entry)
    if not events or events[0].get('kind')!='session' or events[0].get('id')!=session_id:
        raise ValueError('Session journal invalid')
    root=Path(events[0]['root'])
    if not root.is_absolute():raise ValueError('Session root invalid')
    return root,events


def record_created_file(file_path, *, session_id=None, root=None, appdata=None):
    """Only invoked AFTER a successful exclusive create. Never used for old files."""
    sid=session_id or os.environ.get('LRC_SESSION_ID','')
    if not sid:return False
    saved_root,events=_records(sid,appdata)
    if root is not None and Path(root).resolve(strict=True)!=saved_root:
        raise ValueError('Session folder differs from saved root')
    path=Path(file_path)
    if path.is_symlink() or not path.is_file():raise ValueError('Cannot journal a symlink or missing file')
    canonical=path.resolve(strict=True)
    if not _inside(canonical,saved_root) or canonical.parent==saved_root.parent:
        raise ValueError('Cannot journal files outside the library')
    if canonical.suffix.casefold()!='.lrc':raise ValueError('Only .lrc sidecars can be journaled')
    if not (CANDIDATE_RE.fullmatch(canonical.name) or canonical.name.casefold().endswith('.lrc')):
        raise ValueError('Unsupported candidate filename')
    stat=canonical.stat()
    if stat.st_size>MAX_JOURNAL_BYTES:raise ValueError('File too large for safe session undo')
    event={'schema':SCHEMA,'kind':'create','path':str(canonical.relative_to(saved_root)),
           'size':stat.st_size,'mtime_ns':stat.st_mtime_ns,'digest':_file_digest(canonical)}
    if any(e.get('kind')=='create' and e.get('path')==event['path'] for e in events):
        raise ValueError('File already recorded for this session')
    journal=_session_path(sid,appdata)
    with journal.open('a',encoding='utf-8',newline='\n') as f:
        f.write(json.dumps(event,ensure_ascii=False,separators=(',',':'))+'\n')
        f.flush();os.fsync(f.fileno())
    return True


def session_entries(session_id, *, expected_root=None, appdata=None):
    root,events=_records(session_id,appdata)
    if expected_root is not None and root!=Path(expected_root).resolve(strict=True):
        raise ValueError('Session belongs to another library')
    undone={e.get('path') for e in events if e.get('kind')=='undo'}
    result=[]
    seen=set()
    for e in events:
        if e.get('kind')!='create':continue
        rel=e.get('path')
        if not isinstance(rel,str) or rel in seen:continue
        seen.add(rel)
        path=root/rel
        reason='Eligible'
        if rel in undone:reason='Previously undone'
        elif (Path(rel).is_absolute() or '..' in Path(rel).parts or
              path.suffix.casefold()!='.lrc' or path.is_symlink()):reason='Unsafe path'
        elif not path.is_file():reason='Already missing'
        else:
            try:
                resolved=path.resolve(strict=True)
                stat=path.stat()
                if not _inside(resolved,root):reason='Outside library'
                elif stat.st_size!=e.get('size') or stat.st_mtime_ns!=e.get('mtime_ns'):
                    reason='File changed since creation'
                elif _file_digest(path)!=e.get('digest'):
                    reason='File contents changed'
            except OSError:reason='Cannot read file'
        result.append({'path':path,'reason':reason,'eligible':reason=='Eligible'})
    return result


def latest_session(folder, *, appdata=None):
    root=Path(folder).resolve(strict=True)
    base=settings_dir(appdata)
    if not base.is_dir():return None
    candidates=sorted(base.glob('session_*.jsonl'),key=lambda p:p.stat().st_mtime_ns,reverse=True)
    for path in candidates[:150]:
        if path.is_symlink():continue
        sid=path.stem.removeprefix('session_')
        try:
            actual,events=_records(sid,appdata)
            if actual==root and any(e.get('kind')=='create' for e in events):return sid
        except (OSError,ValueError,KeyError):continue
    return None


def undo_session(session_id, *, expected_root, appdata=None):
    """Never delete modified files. Confirm in caller; revalidate just before unlink."""
    items=session_entries(session_id,expected_root=expected_root,appdata=appdata)
    removed=[];skipped=[]
    journal=_session_path(session_id,appdata)
    root, events=_records(session_id,appdata)
    original={str(root/e['path']):e for e in events if e.get('kind')=='create' and isinstance(e.get('path'),str)}
    for entry in items:
        if not entry['eligible']:
            skipped.append((entry['path'],entry['reason']))
            continue
        path=entry['path']
        # Revalidate this exact file immediately before removal without
        # re-hashing every other library sidecar for each single deletion.
        recorded=original.get(str(path))
        try:
            stat=path.stat()
            safe=(recorded is not None and not path.is_symlink() and
                  _inside(path.resolve(strict=True),root) and
                  stat.st_size==recorded.get('size') and
                  stat.st_mtime_ns==recorded.get('mtime_ns') and
                  _file_digest(path)==recorded.get('digest'))
        except OSError:safe=False
        if not safe:
            skipped.append((path,'Changed during undo'))
            continue
        try:
            path.unlink()
            with journal.open('a',encoding='utf-8',newline='\n') as f:
                f.write(json.dumps({'schema':SCHEMA,'kind':'undo','path':str(path.relative_to(Path(expected_root).resolve(strict=True))),
                                    'at':time.time()},ensure_ascii=False)+'\n')
                f.flush();os.fsync(f.fileno())
            removed.append(path)
        except OSError as ex:
            skipped.append((path,'Cannot remove: '+type(ex).__name__))
    return {'removed':removed,'skipped':skipped}


def make_selection_manifest(root, tracks, *, directory=None):
    """Create immutable-by-convention, exact allowlist in a local private temp file."""
    folder=Path(root).resolve(strict=True)
    if not folder.is_dir() or Path(root).is_symlink():raise ValueError('Invalid music root')
    chosen=list(tracks)
    if not 1<=len(chosen)<=MAX_SELECTION:raise ValueError('Choose 1 to 2500 songs for selective retry')
    relative=[];seen=set()
    for track in chosen:
        p=Path(track)
        if not p.is_file() or p.is_symlink() or p.suffix.casefold() not in AUDIO_EXTS:
            raise ValueError('Selection contains missing, unsupported or symlink audio')
        resolved=p.resolve(strict=True)
        if not _inside(resolved,folder):raise ValueError('Selection contains a track outside this library')
        if resolved.with_suffix('.lrc').exists():raise ValueError('Selection already contains a finished .lrc')
        rel=resolved.relative_to(folder).as_posix()
        if rel in seen:raise ValueError('Duplicate song in selection')
        stat=resolved.stat()
        seen.add(rel);relative.append({'path':rel,'size':stat.st_size,'mtime_ns':stat.st_mtime_ns})
    fd,name=tempfile.mkstemp(prefix='LRC_Select_',suffix='.json',dir=directory)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump({'schema':SCHEMA,'folder':str(folder),'tracks':relative},stream,ensure_ascii=False)
            stream.flush();os.fsync(stream.fileno())
    except BaseException:
        Path(name).unlink(missing_ok=True)
        raise
    return Path(name)


def filter_selected_tracks(root, eligible, manifest_path):
    """Fail closed on ANY mismatch. Strict subset; never silently search all."""
    manifest=Path(manifest_path)
    if not manifest.is_file() or manifest.is_symlink() or manifest.stat().st_size>200_000:
        raise ValueError('Selective retry allowlist is missing, unsafe or oversized')
    data=json.loads(manifest.read_text(encoding='utf-8'))
    folder=Path(root).resolve(strict=True)
    if data.get('schema')!=SCHEMA or data.get('folder')!=str(folder):
        raise ValueError('Selected library folder does not match current search')
    names=data.get('tracks')
    if not isinstance(names,list) or not 1<=len(names)<=MAX_SELECTION:
        raise ValueError('No valid tracks selected')
    audio_by_rel={}
    for audio in eligible:
        p=Path(audio)
        if p.is_symlink() or p.suffix.casefold() not in AUDIO_EXTS:continue
        try:
            resolved=p.resolve(strict=True)
            if _inside(resolved,folder) and not resolved.with_suffix('.lrc').exists():
                audio_by_rel[resolved.relative_to(folder).as_posix()]=p
        except (OSError,ValueError):pass
    out=[];seen=set()
    for item in names:
        if not isinstance(item,dict):raise ValueError('Invalid selection entry')
        rel=item.get('path')
        if not isinstance(rel,str) or rel in seen or Path(rel).is_absolute() or '..' in Path(rel).parts:
            raise ValueError('Unsafe or duplicate path in selective retry')
        seen.add(rel)
        if rel not in audio_by_rel:raise ValueError('Selected track is missing or no longer eligible: '+rel[:80])
        stat=audio_by_rel[rel].stat()
        if stat.st_size!=item.get('size') or stat.st_mtime_ns!=item.get('mtime_ns'):
            raise ValueError('Selected audio changed after confirmation: '+rel[:80])
        out.append(audio_by_rel[rel])
    return out


def load_rejection_explanations(root, selected=None):
    """Read current engine's detailed CSVs; reports may be stale, and say so.

    Only per-track reason fields produced by the engine, not inferred verification.
    Avoid following symlinked reports, reading huge or untrusted CSV files.
    """
    folder=Path(root).resolve(strict=True)
    paths=(('LRC_Finder_Report_v2_1_15.csv','report'),('LRC_Finder_Review_v2_1_15.csv','review'))
    selected_paths={str(Path(x).resolve()) for x in selected} if selected else None
    result={}
    for basename,kind in paths:
        filename=folder/basename
        if not filename.is_file() or filename.is_symlink() or filename.stat().st_size>MAX_REPORT_BYTES:continue
        read=0
        try:
            with filename.open(encoding='utf-8-sig',newline='') as stream:
                for row in csv.DictReader(stream):
                    read+=1
                    if read>250_000:break
                    path=row.get('MP3 path','')
                    if not path:continue
                    match=Path(path)
                    if not match.is_absolute() or not _inside(match.resolve(),folder):continue
                    canonical=str(match.resolve())
                    if selected_paths is not None and canonical not in selected_paths:continue
                    entry=result.setdefault(canonical,{'status':'','reason':'','provider_outcomes':'',
                                                        'rejections':[],'last_reported':None})
                    if kind=='report':
                        entry['status']=str(row.get('status',''))[:80]
                        entry['reason']=str(row.get('reason',''))[:MAX_REASON_LENGTH]
                        entry['provider_outcomes']=str(row.get('provider outcomes',''))[:2500]
                    else:
                        why=str(row.get('rejected because','')).strip()
                        if why and len(entry['rejections'])<12:
                            entry['rejections'].append({'provider':str(row.get('provider',''))[:80],
                                'reason':why[:MAX_REASON_LENGTH],
                                'title':str(row.get('candidate title',''))[:100]})
                    entry['last_reported']=filename.stat().st_mtime
        except (OSError, UnicodeError, csv.Error):continue
    return result


def reason_for_row(row, outcomes):
    path=str(Path(row['path']).resolve())
    info=outcomes.get(path)
    if not info:
        if row['status']=='Has LRC':return 'An LRC sidecar exists; its content and timing have not been independently verified.'
        if row['status']=='Ambiguous audio':return 'Several audio formats share the same filename stem; safe automatic sidecar matching is ambiguous.'
        return 'No current per-song reason was found. Run a search, then refresh this dashboard.'
    parts=['Historical search report (may be stale; not a fresh provider check).']
    if info['status']:parts.append('Last recorded status: '+info['status'])
    if info['reason']:parts.append('Reason: '+info['reason'])
    for item in info['rejections'][:7]:
        parts.append(f"Candidate rejected / review only — {item['provider']}: {item['reason']}")
    if info['provider_outcomes']:parts.append('Provider outcomes: '+info['provider_outcomes'][:800])
    return '\n'.join(parts)
