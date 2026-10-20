"""Per-stage and cumulative song-level results for LRC Bulk Finder.

The first three counts reset for every search round. The lifetime totals
count unique tracks with at least one verified saved lyric or review candidate
during THIS run, including checkpoint-replayed work after a restart.
A track with three review variants counts as ONE candidate-bearing song.
"""
from __future__ import annotations
import json
from pathlib import Path

COUNTER_PREFIX="LRC_COUNTER "
NO_MATCH_STATES=frozenset(("NOT_FOUND","NOT_FOUND_PARTIAL","NO_MATCH",
                            "NO_METADATA","REVIEW_PARTIAL"))


class SearchCounters:
    def __init__(self):
        self.round=None
        self.round_saved=set()
        self.round_candidate=set()
        self.round_not_found=set()
        self.total_saved=set()
        self.total_candidate=set()

    def begin_round(self,round_name):
        self.round=str(round_name)
        self.round_saved.clear()
        self.round_candidate.clear()
        self.round_not_found.clear()
        return self.snapshot()

    def record(self,path,status,*,candidate=False):
        if self.round is None:
            raise RuntimeError("Begin a round before recording results")
        key=str(Path(path).resolve())
        if status=="SAVED":
            self.round_saved.add(key)
            self.total_saved.add(key)
        if candidate:
            self.round_candidate.add(key)
            self.total_candidate.add(key)
        # A prior stage's review is not a new candidate in the current stage.
        # Timeouts, provider faults and interrupted songs are NOT "not found".
        if status in NO_MATCH_STATES and not candidate:
            self.round_not_found.add(key)
        return self.snapshot()

    def end_round(self):
        """Completed stage: clear only current-round numbers, keep totals."""
        self.round_saved.clear()
        self.round_candidate.clear()
        self.round_not_found.clear()
        return self.snapshot()

    def snapshot(self):
        return {
            "round":self.round,
            "round_lrc":len(self.round_saved),
            "round_candidate":len(self.round_candidate),
            "round_not_found":len(self.round_not_found),
            "total_lrc":len(self.total_saved),
            "total_candidate":len(self.total_candidate),
        }

    def output(self):
        return COUNTER_PREFIX+json.dumps(self.snapshot(),separators=(",",":"))


def parse_counter_line(line):
    if not line.startswith(COUNTER_PREFIX):
        return None
    try:
        data=json.loads(line[len(COUNTER_PREFIX):])
        keys=("round_lrc","round_candidate","round_not_found",
              "total_lrc","total_candidate")
        if not isinstance(data,dict) or not isinstance(data.get("round"),str):
            return None
        if any(type(data.get(key)) is not int or data[key]<0 for key in keys):
            return None
        return {key:data[key] for key in keys}|{"round":data["round"]}
    except (TypeError,ValueError,KeyError):
        return None
