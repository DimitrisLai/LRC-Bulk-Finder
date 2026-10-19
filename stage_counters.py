"""Per-stage live counts and run-wide unique-track totals.

A stage's counters reset to zero on entry; totals retain tracks found
through all stages. Checkpoint-replayed results count once. "Not found"
means no verified lyrics AND no candidate at the end of that track/stage;
errors/timeouts are not misrepresented as definite NOT_FOUND.
"""
from __future__ import annotations
from pathlib import Path

class StageCounters:
    def __init__(self):
        self.total_found=set()
        self.total_candidates=set()
        self.stage=None
        self.found=set()
        self.candidates=set()
        self.not_found=set()

    def start(self,stage):
        self.stage=str(stage)
        self.found=set()
        self.candidates=set()
        self.not_found=set()
        return self.line()

    def add(self,track,status,*,reviewed=False):
        name=str(Path(track).resolve())
        if status=="SAVED":
            self.found.add(name)
            self.total_found.add(name)
            self.not_found.discard(name)
        if reviewed or status in {"REVIEW","REVIEW_AVAILABLE"}:
            self.candidates.add(name)
            self.total_candidates.add(name)
            self.not_found.discard(name)
        if (status in {"NO_MATCH","NOT_FOUND","NOT_FOUND_PARTIAL","NO_METADATA","REVIEW_PARTIAL"} and
                name not in self.candidates and name not in self.found):
            self.not_found.add(name)
        return self.line()

    def values(self):
        return {
            "stage":self.stage,
            "found":len(self.found),
            "candidate":len(self.candidates),
            "not_found":len(self.not_found),
            "total_found":len(self.total_found),
            "total_candidate":len(self.total_candidates),
        }

    def line(self):
        s=self.values()
        return ("STAGE COUNTERS: stage={stage} found={found} candidate={candidate} "
                "not_found={not_found} total_found={total_found} "
                "total_candidate={total_candidate}").format(**s)
