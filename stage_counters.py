"""Counters for v2.4.3-dev. Unique tracks per stage, unique findings per run.

No search with missing metadata is classified as a confirmed no-match.
"""
from __future__ import annotations
from pathlib import Path


class StageCounters:
    SKIPPED_STATUSES = frozenset({'NO_METADATA', 'LIVE_SKIPPED', 'SKIPPED', 'UNSEARCHABLE', 'AMBIGUOUS'})
    MISS_STATUSES = frozenset({'NO_MATCH', 'NOT_FOUND', 'NOT_FOUND_PARTIAL', 'REVIEW_PARTIAL'})

    def __init__(self):
        self.total_found = set()
        self.total_candidates = set()
        self.stage = None
        self.found = set()
        self.candidates = set()
        self.not_found = set()
        self.skipped = set()

    def start(self, stage):
        self.stage = str(stage)
        self.found = set()
        self.candidates = set()
        self.not_found = set()
        self.skipped = set()
        return self.line()

    def add(self, track, status, *, reviewed=False):
        name = str(Path(track).resolve())
        if status == 'SAVED':
            self.found.add(name)
            self.total_found.add(name)
            self.not_found.discard(name)
            self.skipped.discard(name)
        if reviewed:
            self.candidates.add(name)
            self.total_candidates.add(name)
            self.not_found.discard(name)
            self.skipped.discard(name)
        if status in self.SKIPPED_STATUSES and name not in self.found and name not in self.candidates:
            self.skipped.add(name)
            self.not_found.discard(name)
        if status in self.MISS_STATUSES and name not in self.candidates and name not in self.found and name not in self.skipped:
            self.not_found.add(name)
        return self.line()

    def values(self):
        return {'stage': self.stage, 'found': len(self.found),
                'candidate': len(self.candidates), 'not_found': len(self.not_found),
                'skipped': len(self.skipped), 'total_found': len(self.total_found),
                'total_candidate': len(self.total_candidates)}

    def line(self):
        return ('STAGE COUNTERS: stage={stage} found={found} candidate={candidate} '
                'not_found={not_found} total_found={total_found} '
                'total_candidate={total_candidate} skipped={skipped}').format(**self.values())
