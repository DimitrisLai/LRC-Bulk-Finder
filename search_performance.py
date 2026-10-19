"""Search performance helpers for LRC Bulk Finder v2.2.

These files store lookup metadata, aggregate outcomes and opaque track IDs;
never MP3/audio bytes or lyrics text. All persistence is local and optional.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import time
from collections import defaultdict
from pathlib import Path


class MusicBrainzDiskCache:
    """Duration-aware, time-limited MusicBrainz spelling suggestions.

    Successful 'nothing found' lookups are cached briefly; network failures
    are deliberately not saved. Only exact key/mode/duration matches are reused.
    """
    def __init__(self, folder, ttl_days=30, miss_days=7, max_entries=10000):
        self.path=Path(folder)/"LRC_MusicBrainz_Cache_v2_2.jsonl"
        self.ttl=ttl_days*86400
        self.miss_ttl=miss_days*86400
        self.max_entries=max_entries
        self.data={}
        self.hits=0
        self.misses=0
        self._load()

    @staticmethod
    def key(title,artist,duration,greek_mode):
        text=json.dumps([str(title).casefold().strip(),str(artist).casefold().strip(),
                         round(float(duration or 0),1),bool(greek_mode)],ensure_ascii=False)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def _load(self):
        if not self.path.is_file():
            return
        now=time.time()
        try:
            with self.path.open(encoding="utf-8") as source:
                for line in source:
                    try:
                        row=json.loads(line)
                        key=row["key"]
                        value=row["value"]
                        when=float(row["at"])
                        if value is not None and (not isinstance(value,list) or len(value)!=2):
                            continue
                        age=now-when
                        limit=self.ttl if value else self.miss_ttl
                        if 0<=age<=limit:
                            self.data[key]=(when,tuple(value) if value else None)
                        elif key in self.data:
                            del self.data[key]
                    except (KeyError,TypeError,ValueError,AttributeError):
                        continue
        except OSError as error:
            print("Warning: MusicBrainz disk cache unavailable:",error)
        # Cap the in-memory data even if historical JSONL grows.
        if len(self.data)>self.max_entries:
            self.data=dict(sorted(self.data.items(),key=lambda p:p[1][0],reverse=True)[:self.max_entries])

    def lookup(self,title,artist,duration,greek_mode):
        key=self.key(title,artist,duration,greek_mode)
        entry=self.data.get(key)
        if entry is None:
            self.misses+=1
            return False,None
        at,value=entry
        ttl=self.ttl if value else self.miss_ttl
        if time.time()-at>ttl:
            self.data.pop(key,None)
            self.misses+=1
            return False,None
        self.hits+=1
        return True,value

    def save(self,title,artist,duration,greek_mode,value):
        if value is not None:
            if not isinstance(value,(tuple,list)) or len(value)!=2:
                raise ValueError("MusicBrainz suggestion must contain title and artist")
            value=tuple(str(x) for x in value)
        key=self.key(title,artist,duration,greek_mode)
        now=time.time()
        row={"key":key,"at":now,"value":list(value) if value else None}
        try:
            # One complete line per successful lookup; a truncated line is skipped on load.
            with self.path.open("a",encoding="utf-8",newline="\n") as output:
                output.write(json.dumps(row,ensure_ascii=False,separators=(",",":"))+"\n")
        except OSError as error:
            print("Warning: MusicBrainz cache could not be written:",error)
        self.data[key]=(now,value)
        if len(self.data)>self.max_entries:
            self.data=dict(sorted(self.data.items(),key=lambda p:p[1][0],reverse=True)[:self.max_entries])


class ProviderPerformance:
    """Verified-match-only provider outcome and timing statistics.

    A stable event ID means checkpoint replay or repeated report export cannot
    count the same provider/song/stage twice. Unavailable, skipped or cached
    NO_MATCH are excluded from denominators.
    """
    def __init__(self,folder,known_providers,days=90):
        self.folder=Path(folder)
        self.path=self.folder/"LRC_Provider_Performance_v2_2.jsonl"
        self.known=tuple(known_providers)
        self.events={}
        self.days=days
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        cutoff=time.time()-self.days*86400
        try:
            with self.path.open(encoding="utf-8") as source:
                for line in source:
                    try:
                        item=json.loads(line)
                        if (item["provider"] not in self.known or
                                float(item["at"])<cutoff or
                                item["kind"] not in ("SAVED","REVIEW","NO_MATCH","ERROR")):
                            continue
                        self.events[item["key"]]=item
                    except (ValueError,KeyError,TypeError):
                        continue
        except OSError as error:
            print("Warning: cannot read provider performance history:",error)

    @staticmethod
    def kind_from_result(result):
        result=str(result).split(" ",1)[0]
        if result.startswith("SAVED"):return "SAVED"
        if result.startswith("REVIEW"):return "REVIEW"
        if result.startswith("NO_MATCH"):return "NO_MATCH"
        if result.startswith("ERROR"):return "ERROR"
        return None

    def record_rows(self,stage_rows,signature,mp3_stat=None):
        """Rows are the existing 8-column per-provider diagnostic rows."""
        new=[]
        for row in stage_rows:
            if len(row)<8:
                continue
            mp3_path,stage,provider,result,queries,elapsed,summary,requests=row[:8]
            kind=self.kind_from_result(result)
            if kind is None or provider not in self.known:
                continue
            # Do not misrepresent library hidden HTTP status as zero searches.
            key_data=[signature,str(mp3_path),str(stage),provider,str(result),str(mp3_stat or "")]
            key=hashlib.sha256(json.dumps(key_data,ensure_ascii=False).encode()).hexdigest()
            if key in self.events:
                continue
            item={"key":key,"at":time.time(),"provider":provider,
                  "kind":kind,"seconds":max(0.0,float(elapsed or 0))}
            self.events[key]=item
            new.append(item)
        if new:
            try:
                with self.path.open("a",encoding="utf-8",newline="\n") as target:
                    for item in new:
                        target.write(json.dumps(item,separators=(",",":"))+"\n")
            except OSError as error:
                print("Warning: could not persist provider statistics:",error)
        return len(new)

    def statistics(self):
        counts={p:{"attempts":0,"saved":0,"review":0,"no_match":0,
                   "error":0,"seconds":0.0} for p in self.known}
        for row in self.events.values():
            data=counts[row["provider"]]
            data["attempts"]+=1
            data[{"SAVED":"saved","REVIEW":"review","NO_MATCH":"no_match","ERROR":"error"}[row["kind"]]]+=1
            data["seconds"]+=row["seconds"]
        return counts

    def sorted_smart(self,providers,minimum_attempts=10):
        """Keep LRCLIB priority, prefer verified saves per wall-clock second.

        Providers with insufficient samples preserve their original order.
        This only changes the order, never silently removes a provider.
        """
        sources=list(providers)
        totals=self.statistics()
        def score(provider):
            data=totals[provider]
            if data["attempts"]<minimum_attempts:
                return None
            return data["saved"]/max(data["seconds"],1.0)
        available=[p for p in sources if p!="LRCLIB"]
        familiar=[p for p in available if score(p) is not None]
        unfamiliar=[p for p in available if score(p) is None]
        familiar.sort(key=lambda p:-score(p))
        return (["LRCLIB"] if "LRCLIB" in sources else [])+familiar+unfamiliar

    def export_csv(self):
        target=self.folder/"LRC_Provider_Performance_v2_2.csv"
        data=self.statistics()
        try:
            with target.open("w",encoding="utf-8-sig",newline="") as handle:
                writer=csv.writer(handle)
                writer.writerow(["provider","completed attempts","verified saved","review only",
                                 "no match","error","verified success rate %",
                                 "elapsed seconds","seconds per verified save"])
                for provider in self.known:
                    row=data[provider]
                    attempts=row["attempts"]
                    verified=row["saved"]
                    writer.writerow([provider,attempts,verified,row["review"],row["no_match"],
                                     row["error"],round(100*verified/attempts,2) if attempts else 0,
                                     round(row["seconds"],2),
                                     round(row["seconds"]/verified,2) if verified else ""])
        except OSError as error:
            print("Warning: provider performance report not writable:",error)
        return target


def choose_provider_order(providers,choice,custom_value="",performance=None):
    """Return (ordered tuple, mode) with strict validation and no silent omissions."""
    original=tuple(providers)
    choice=str(choice or "").strip().lower()
    if choice in ("","d","default"):
        return original,"DEFAULT"
    if choice in ("s","smart"):
        if performance is None:
            return original,"DEFAULT (no statistics yet)"
        return tuple(performance.sorted_smart(original)),"SMART"
    if choice in ("c","custom"):
        names=[x.strip() for x in str(custom_value).split(",") if x.strip()]
        mapping={p.casefold():p for p in original}
        lower=[name.casefold() for name in names]
        if (len(lower)!=len(original) or len(set(lower))!=len(original)
                or set(lower)!=set(mapping)):
            raise ValueError("Custom order must contain every selected provider exactly once")
        return tuple(mapping[n] for n in lower),"CUSTOM"
    raise ValueError("Choose D (default), S (smart) or C (custom)")
