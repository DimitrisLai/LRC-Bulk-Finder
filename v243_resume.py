"""Local, explicit previous-run profile marker. Checkpoints stay authoritative."""
from __future__ import annotations
import json
import os
from pathlib import Path
from datetime import datetime, timezone


def marker_path():
    return (Path(os.environ.get('APPDATA') or (Path.home()/'.config')) /
            'LRCBulkFinder' / 'last_run_v243.json')


def mark_run(profile, folder, status='running', path=None):
    p = Path(path) if path else marker_path()
    p.parent.mkdir(parents=True,exist_ok=True)
    record = {'schema':1, 'profile':str(profile), 'folder':str(folder),
              'status':status, 'at':datetime.now(timezone.utc).isoformat()}
    t=p.with_suffix('.json.tmp')
    with t.open('w',encoding='utf-8') as fh:
        json.dump(record,fh,ensure_ascii=False)
        fh.flush(); os.fsync(fh.fileno())
    os.replace(t,p)
    return record


def last_run(path=None):
    p=Path(path) if path else marker_path()
    try:
        data=json.loads(p.read_text(encoding='utf-8'))
        if data.get('schema')!=1 or data.get('status') not in ('running','stopped','finished'):
            return None
        if not isinstance(data.get('profile'),str) or not isinstance(data.get('folder'),str):
            return None
        return data
    except (OSError,ValueError,AttributeError,TypeError):
        return None
