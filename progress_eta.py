"""Time-based progress estimates for long v2.3 batch searches.

Separate per-round estimates are intentionally NOT presented as end-to-end ETAs,
because later rounds depend on hits and unavailable providers.
"""
from __future__ import annotations
import time


def format_seconds(seconds):
    if seconds is None:
        return "calculating"
    sec=max(0,int(round(seconds)))
    hours,part=divmod(sec,3600)
    minutes,secs=divmod(part,60)
    return f"{hours}h {minutes:02d}m" if hours else f"{minutes}m {secs:02d}s"


class RoundProgress:
    def __init__(self,total,round_no,label="",clock=None):
        self.total=max(0,int(total))
        self.round_no=round_no
        self.label=label
        self.clock=clock or time.monotonic
        self.start=self.clock()
        self.processed=0
        self.active=0
        self.duration=0.0

    def complete(self,elapsed,checkpoint=False):
        """Checkpointed songs count toward progress, not the timing sample."""
        self.processed+=1
        if not checkpoint:
            self.active+=1
            self.duration+=max(0.0,float(elapsed))
        return self.status()

    def status(self):
        count=min(self.total,self.processed)
        left=max(0,self.total-count)
        # Estimate only after 3 actual songs. Never guess about next round.
        eta=(left*self.duration/self.active if self.active>=3 else
             (0.0 if left==0 else None))
        return {
            "round":self.round_no,"count":count,"total":self.total,
            "percent":round(100*count/self.total,1) if self.total else 100.0,
            "elapsed":self.clock()-self.start,
            "remaining":eta,"samples":self.active,
        }

    def line(self):
        result=self.status()
        return (f"PROGRESS ROUND {self.round_no}: {result['count']}/{self.total} "
                f"({result['percent']:.1f}%) | elapsed "
                f"{format_seconds(result['elapsed'])} | THIS ROUND ETA: "
                f"{format_seconds(result['remaining'])}"
                f" | timed samples: {result['samples']}")
