"""Crash-tolerant, append-only per-song stage checkpoints for v2.1.21.

Only local metadata/diagnostics; no lyrics, audio or ID3 bytes are changed.
A partial final JSONL line is ignored, and all entries require unchanged
song size + nanosecond modification time and identical search configuration.
"""
from __future__ import annotations
import hashlib
import json
import os
import uuid
from pathlib import Path
from startup_io import read_jsonl_snapshot, StartupBudgetExceeded


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
        self.run_id=uuid.uuid4().hex  # stable on restart; new after journal reset
        self.entries={}
        self.loaded=0
        self.invalid_lines=0
        def consume(data,record):
            if record.get('signature')!=signature or record.get('schema')!=1:
                return
            path=str(record['path'])
            stage=int(record['round'])
            if stage not in (1,2,3):return
            data['entries'][(path,stage)]=record
            if isinstance(record.get('run_id'),str):data['run_id']=record['run_id']
        try:
            data=read_jsonl_snapshot(self.path,lambda:{'entries':{},'run_id':self.run_id,'invalid':0},consume,
                label='PREFLIGHT CHECKPOINT',progress=lambda msg:print(msg,flush=True),
                max_record_bytes=4*1024*1024,on_invalid=lambda data:data.update(invalid=data['invalid']+1))
            self.entries=data['entries']
            self.run_id=data['run_id']
            self.loaded=len(self.entries)
            self.invalid_lines=data['invalid']
        except (OSError,StartupBudgetExceeded) as error:
            print('Resume cache unavailable this run; original checkpoint preserved:',error,flush=True)

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

    def _repair_incomplete_tail(self):
        """Do not append to half-written JSON that would corrupt the next event.

        Keep intact newline-delimited records. The interrupted final fragment
        is discarded only when it cannot parse; valid no-newline JSON is kept.
        """
        if not self.path.is_file():
            return
        with self.path.open("rb+") as stream:
            stream.seek(0,os.SEEK_END)
            size=stream.tell()
            if not size:
                return
            stream.seek(-1,os.SEEK_END)
            if stream.read(1)==b"\n":
                return
            chunk=min(size,1024*1024)
            stream.seek(-chunk,os.SEEK_END)
            tail=stream.read(chunk)
            cut=tail.rfind(b"\n")
            last=tail[cut+1:]
            try:
                json.loads(last.decode("utf-8"))
            except (ValueError,UnicodeError):
                if cut<0 and size>chunk:
                    # Oversize final line: don't risk wiping valid history.
                    raise OSError("checkpoint has an oversized unterminated line")
                stream.truncate(size-len(last))
            else:
                stream.seek(0,os.SEEK_END)
                stream.write(b"\n")

    def save(self, song, stage, status, detail, retry_targets, reviewed,
             row, review_rows, provider_rows, http_rows):
        path=Path(song).resolve()
        stat=path.stat()
        record={
            'schema':1,'signature':self.signature,'run_id':self.run_id,
            'path':str(path),
            'round':int(stage),'file_size':stat.st_size,
            'file_mtime_ns':stat.st_mtime_ns,
            'status':status,'detail':detail,
            'retry_targets':sorted(retry_targets),'reviewed':bool(reviewed),
            'row':row,'review_rows':review_rows,
            'provider_rows':provider_rows,'http_rows':http_rows,
        }
        try:
            self._repair_incomplete_tail()
            with self.path.open('a',encoding='utf-8',newline='\n') as output:
                output.write(json.dumps(record,ensure_ascii=False,separators=(',',':'))+'\n')
                output.flush()
                os.fsync(output.fileno())
        except OSError as error:
            print('WARNING: per-song checkpoint write failed:',error)
            return False
        self.entries[(str(path),int(stage))]=record
        return True
