"""Crash-tolerant, append-only per-song stage checkpoints for v2.1.21.

Only local metadata/diagnostics; no lyrics, audio or ID3 bytes are changed.
A partial final JSONL line is ignored, and all entries require unchanged
song size + nanosecond modification time and identical search configuration.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path


def checkpoint_signature(version, settings, config_files=(), snapshot=None):
    inputs=[]
    for filename in config_files:
        path=Path(filename)
        if path.is_file():
            inputs.append((path.name, hashlib.sha256(path.read_bytes()).hexdigest()))
        else:
            inputs.append((path.name, None))
    dbinfo=None
    if snapshot:
        db=Path(snapshot)
        try:
            info=db.stat()
            dbinfo=(str(db.resolve()), info.st_size, info.st_mtime_ns)
        except OSError:
            dbinfo=(str(db), 'missing')
    source=json.dumps([version,settings,inputs,dbinfo],
                      sort_keys=True,ensure_ascii=False,default=str)
    return hashlib.sha256(source.encode('utf-8')).hexdigest()


class SearchCheckpoint:
    """The newest fully written event for a particular MP3 and stage wins."""
    def __init__(self, folder, version, signature):
        self.path=Path(folder)/('LRC_Run_Checkpoint_v'+version.replace('.','_')+'.jsonl')
        self.signature=signature
        self.entries={}
        self.loaded=0
        if self.path.is_file():
            try:
                with self.path.open(encoding='utf-8') as source:
                    for line in source:
                        try:
                            record=json.loads(line)
                            if (record.get('signature')!=signature or
                                    record.get('schema')!=1):
                                continue
                            path=str(record['path'])
                            stage=int(record['round'])
                            if stage not in (1,2,3):continue
                            self.entries[(path,stage)]=record
                        except (ValueError,KeyError,TypeError,AttributeError):
                            continue  # tolerate truncated final lines
                self.loaded=len(self.entries)
            except OSError as error:
                print('Warning: cannot load search checkpoint:',error)

    def get(self, song, stage):
        path=Path(song)
        record=self.entries.get((str(path.resolve()),stage))
        if record is None:return None
        try:
            stat=path.stat()
            if (record.get('file_size')!=stat.st_size or
                    record.get('file_mtime_ns')!=stat.st_mtime_ns):
                return None
            if record.get('status') in ('SAVED','EXISTS') and not path.with_suffix('.lrc').is_file():
                return None
            if record.get('status') in ('INTERRUPTED','SERVER_ERROR'):
                return None
        except OSError:
            return None
        return record

    def save(self, song, stage, status, detail, retry_targets, reviewed,
             row, review_rows, provider_rows, http_rows):
        path=Path(song).resolve()
        stat=path.stat()
        record={
            'schema':1,'signature':self.signature,'path':str(path),
            'round':int(stage),'file_size':stat.st_size,
            'file_mtime_ns':stat.st_mtime_ns,
            'status':status,'detail':detail,
            'retry_targets':sorted(retry_targets),'reviewed':bool(reviewed),
            'row':row,'review_rows':review_rows,
            'provider_rows':provider_rows,'http_rows':http_rows,
        }
        try:
            with self.path.open('a',encoding='utf-8',newline='\n') as output:
                output.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
        except OSError as error:
            print('WARNING: per-song checkpoint write failed:',error)
            return False
        self.entries[(str(path),int(stage))]=record
        return True
