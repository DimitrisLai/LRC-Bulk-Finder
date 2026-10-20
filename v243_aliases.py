"""Explicit user-approved alias insertion, preserving the existing CSV schema.

Search runs re-read Greek_Aliases.csv; audio files are never modified.
"""
from __future__ import annotations
import csv
import os
import tempfile
from pathlib import Path


def approve_alias(csv_path, kind, greeklish, greek):
    if kind not in ('artist','title'):
        raise ValueError('Kind must be artist or title')
    greeklish,greek=greeklish.strip(),greek.strip()
    if not (2 <= len(greeklish) <= 160 and 2 <= len(greek) <= 160):
        raise ValueError('Both values must be between 2 and 160 characters')
    if any(c in greeklish+greek for c in '\r\n\x00'):
        raise ValueError('Control characters are not allowed')
    if not any('\u0370' <= c <= '\u03ff' or '\u1f00' <= c <= '\u1fff' for c in greek):
        raise ValueError('Approved Greek spelling must contain Greek letters')
    destination=Path(csv_path)
    records=[]
    if destination.is_file():
        with destination.open(encoding='utf-8-sig',newline='') as fh:
            reader=csv.DictReader(fh)
            if reader.fieldnames!=['type','greeklish','greek']:
                raise ValueError('Unrecognized Greek_Aliases.csv header; refusing to replace')
            records=list(reader)
    for rec in records:
        if rec['type']==kind and rec['greeklish'].casefold()==greeklish.casefold():
            if rec['greek']==greek:return False
            raise ValueError('Alias exists with different Greek spelling; edit manually')
    records.append({'type':kind,'greeklish':greeklish,'greek':greek})
    destination.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.lrc_aliases_',suffix='.tmp',dir=destination.parent)
    try:
        with os.fdopen(fd,'w',encoding='utf-8-sig',newline='') as fh:
            writer=csv.DictWriter(fh,fieldnames=['type','greeklish','greek'])
            writer.writeheader();writer.writerows(records)
            fh.flush();os.fsync(fh.fileno())
        os.replace(tmp,destination)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return True
