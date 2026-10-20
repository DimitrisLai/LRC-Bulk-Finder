"""Opt-in SimpMusic experiment. The core acceptability gate is never bypassed.

The public search endpoint can return song/artist and line-synced text but
might omit resolved recording duration. In that case this provider produces
REVIEW CANDIDATES ONLY, regardless of title similarity.
"""
from __future__ import annotations

BASE='https://api-lyrics.simpmusic.org/v1/search'


def _duration(row):
    for key in ('duration','durationSeconds','trackDuration'):
        raw=row.get(key)
        try:
            value=float(raw)
            if 0 < value <= 24*3600:
                return value
        except (ValueError,TypeError):
            pass
    return None


def provider_simpmusic(title,artist,album,duration,review,*,direct_json,acceptable,Hit,
                       query_variants,label_for_query,plausible_lrc):
    seen=set()
    for variant_title,variant_artist in query_variants(title,artist)[:6]:
        data=direct_json('SimpMusic',BASE,{'q':variant_title+' '+variant_artist,'limit':8})
        if not isinstance(data,dict) or data.get('success') is not True:
            continue
        rows=data.get('data',[])
        if not isinstance(rows,list):
            continue
        for row in rows[:8]:
            if not isinstance(row,dict):continue
            synced=row.get('syncedLyrics')
            resolved_title=row.get('songTitle') or ''
            resolved_artist=row.get('artistName') or ''
            if not isinstance(synced,str) or len(synced)>200000 or not plausible_lrc(synced,0):
                continue
            ident=(str(row.get('id') or row.get('videoId') or ''),resolved_title,resolved_artist)
            if ident in seen:continue
            seen.add(ident)
            ok,note=acceptable(title,artist,duration,resolved_title,resolved_artist,
                               _duration(row),synced)
            if ok:
                return Hit(synced,'SimpMusic',note,
                           label_for_query(title,artist,variant_title,variant_artist),True)
            review.add('SimpMusic',resolved_title,resolved_artist,
                       'Experimental source — '+note,lyrics=synced)
    return None
