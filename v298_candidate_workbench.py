"""Candidate Review Workbench v2.9.8: read-only lists and confirmed batch actions.

Batch actions delegate to the existing strict marked-LRC promotion, which uses
exclusive writes and never modifies audio or ID3 tags. Numbered alternatives
cannot be directly promoted; they are renumbered only by the existing routine.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from review_candidates_gui import candidate_index, explicitly_promote


STATUSES=("All statuses","Primary eligible","Primary needs review",
          "Alternative","Already has LRC","Missing / ambiguous audio")
ORDER=("track","candidate","kind","status","number","folder")


def status_for(item):
    if not item["has_mp3"]:
        return "Missing / ambiguous audio"
    if item["has_lrc"]:
        return "Already has LRC"
    if item["index"]==1:
        return "Primary needs review"
    return "Alternative"


def can_promote(item):
    return (item["index"]==1 and item["has_mp3"] and
            not item["has_lrc"] and item["path"].is_file())


def summarize(items):
    rows=list(items)
    primary=sum(row["index"]==1 for row in rows)
    alternative=len(rows)-primary
    eligible=sum(can_promote(row) for row in rows)
    blocked=primary-eligible
    return {"total":len(rows),"primary":primary,"alternative":alternative,
            "eligible":eligible,"blocked_primary":blocked}


def filtered(items,choice="All statuses",query=""):
    if choice not in STATUSES:
        raise ValueError("Unknown candidate filter")
    query=str(query or "").strip().casefold()
    result=[]
    for item in items:
        status=status_for(item)
        if choice=="Primary eligible" and not can_promote(item):continue
        if choice=="Primary needs review" and item["index"]!=1:continue
        if choice=="Alternative" and item["index"]==1:continue
        if choice=="Already has LRC" and status!="Already has LRC":continue
        if choice=="Missing / ambiguous audio" and status!="Missing / ambiguous audio":continue
        if query and query not in (
            str(item["mp3"].name)+" "+str(item["path"].name)+" "+
            str(item["path"].parent)+" "+status).casefold():continue
        result.append(item)
    return result


def sort_items(items,column="track",descending=False):
    if column not in ORDER:
        raise ValueError("Unsupported sort column")
    def key(item):
        values={
            "track":item["mp3"].name,
            "candidate":item["path"].name,
            "kind":"Primary" if item["index"]==1 else "Alternative",
            "status":status_for(item),
            "number":item["index"],
            "folder":str(item["path"].parent),
        }
        val=values[column]
        return (val.casefold(),str(item["path"]).casefold()) if isinstance(val,str) else (val,str(item["path"]).casefold())
    return sorted(items,key=key,reverse=bool(descending))


def primary_paths(items):
    """Only actual primary candidates with exactly one audio file, no LRC."""
    return [row["path"] for row in items if can_promote(row)]


def bulk_promote(paths,root,recursive=True,*,approved=False,report=None,stop=None):
    """Promote chosen primaries one at a time with explicit GUI confirmation.

    Result statuses are from the existing exclusive-write engine. Batch input
    gets validated before file writes; files are rechecked at promotion time.
    Calling with approved=False is always non-destructive.
    """
    if not approved:
        raise PermissionError("Explicit confirmation is required for batch promotion")
    folder=Path(root).resolve(strict=True)
    if not folder.is_dir():raise ValueError("Music folder does not exist")
    selected=[Path(p) for p in paths]
    if len(selected)!=len(set(selected)):
        raise ValueError("Candidate selection contains duplicates")
    for path in selected:
        if candidate_index(path)!=1:
            raise ValueError("Numbered alternatives cannot be promoted directly")
        actual=path.resolve(strict=False)
        if not actual.is_relative_to(folder):
            raise ValueError("Candidate is outside the chosen music folder")
        if not recursive and actual.parent!=folder:
            raise ValueError("Candidate is outside the nonrecursive search scope")
    counts=Counter()
    detail=[]
    for path in selected:
        if stop is not None and stop():
            counts["STOPPED"]+=len(selected)-len(detail)
            break
        try:
            status,message=explicitly_promote(path,approved=True)
        except (OSError,ValueError,PermissionError,UnicodeError) as err:
            status,message="ERROR",str(err)
        counts[status]+=1
        detail.append((path,status,message))
        if report is not None:
            report(len(detail),len(selected),path,status,message)
    return dict(counts),detail
