"""Analyze *accepted* installs in the engine's final detailed CSV.

No candidate, duplicate provider attempts, or HTTP 200 response counts.
A resumed checkpoint may represent work from an earlier partial session;
label the report accordingly rather than pretending this launch saved it.
"""
from __future__ import annotations
import csv
from collections import defaultdict
from pathlib import Path


def export_contribution(folder):
    root=Path(folder)
    source=root/'LRC_Finder_Report_v2_1_15.csv'
    if not source.is_file():return None
    by_provider=defaultdict(set)
    with source.open('r',encoding='utf-8-sig',newline='') as fh:
        for row in csv.DictReader(fh):
            if row.get('status')!='SAVED':continue
            name=row.get('saved provider','').strip()
            path=Path(row.get('MP3 path',''))
            if not name or not path.is_file() or not path.with_suffix('.lrc').is_file():continue
            by_provider[name].add(str(path.resolve()))
    target=root/'LRC_Provider_Contribution_v2_4_3_DEV.csv'
    with target.open('w',encoding='utf-8-sig',newline='') as fh:
        writer=csv.writer(fh)
        writer.writerow(['provider','unique_tracks_with_verified_installs_in_report','note'])
        for provider,tracks in sorted(by_provider.items(),key=lambda x:(-len(x[1]),x[0])):
            writer.writerow([provider,len(tracks),'May include checkpoint-replayed work from an interrupted run'])
    return target
