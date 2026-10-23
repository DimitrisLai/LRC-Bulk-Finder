"""Opt-in provider benchmarking and per-profile exclusions (v2.9.7).

The benchmark deliberately never writes LRC/candidate/audio files. Only one
aggregate report is created under the user's application-data directory.
Existing source selection and strict provider identity checks are reused.
"""
from __future__ import annotations

import csv
import os
import time
from datetime import datetime
from pathlib import Path

from v296_provider_tiers import PACKS, LEGACY

ALL_SOURCES=tuple(dict.fromkeys(PACKS["6"]))


def available_sources(pack, legacy_sources):
    return tuple(legacy_sources) if pack == LEGACY else PACKS[pack]


def validate_exclusions(excluded, available, allow_all=False):
    """Fail closed on typos, wrong tiers and duplicates; normalize source casing."""
    if not isinstance(excluded, list):
        raise ValueError("Provider exclusions must be a JSON list")
    available=tuple(available)
    by_case={p.casefold():p for p in available}
    result=[]
    for item in excluded:
        if not isinstance(item,str) or item.casefold() not in by_case:
            raise ValueError("Provider exclusion is not part of the chosen source pack")
        value=by_case[item.casefold()]
        if value in result:
            raise ValueError("Duplicate provider exclusion")
        result.append(value)
    if not allow_all and len(result)==len(available) and available:
        raise ValueError("At least one online provider must remain enabled")
    return result


def effective_sources(pack, legacy_sources, exclusions):
    selected=available_sources(pack,legacy_sources)
    removed=set(validate_exclusions(exclusions,selected))
    return tuple(p for p in selected if p not in removed)


def benchmark_report_folder(env=None):
    environment=os.environ if env is None else env
    root=environment.get("APPDATA") or environment.get("LOCALAPPDATA")
    return (Path(root) if root else Path.home()/".config")/"LRCBulkFinder"/"benchmarks"


def select_sample(folder,count,recursive=True,*,files=None,read_info=None,skip_live=None):
    """Small deterministic metadata-valid sample, including existing-LRC songs.

    Do not create an incremental index or mutate ID3, metadata or sidecars.
    No paths, titles or artist names are written to the aggregate report.
    """
    import LRC_Bulk_Finder as finder
    from incremental_library import safe_audio_files
    from stop_control import check_stop
    base=Path(folder).expanduser()
    if not base.is_dir():raise ValueError("Selected music folder does not exist")
    source_files=files if files is not None else safe_audio_files(base,recursive)[0]
    # Sample across the entire library, not just the first alphabetic album.
    # Fixed seed makes Tier 1 versus Tier 2 benchmarks directly comparable.
    import random
    source_files=list(source_files)
    if files is None:
        random.Random(297).shuffle(source_files)
    reader=read_info if read_info is not None else finder._read_audio_info
    live=skip_live if skip_live is not None else finder.is_live_track
    result=[]
    for path in source_files:
        check_stop()
        p=Path(path)
        if live(p.name):continue
        try:
            title,artist,album,duration=reader(p)
        except (OSError,ValueError,TypeError):
            continue
        if not title or not artist or live(title):
            continue
        result.append((p,str(title),str(artist),str(album or ""),float(duration or 0)))
        if len(result)>=count:break
    return result


def classification(hit,status,calls,review_count):
    """Separate verified match, review-only, timeout, blocked, true no-match."""
    if hit is not None and getattr(hit,"verified",False) and status=="SAVED":
        return "verified"
    if review_count or status.startswith("REVIEW"):
        return "review"
    if any("=ERROR" in c and ("timed out" in c.lower() or "timeout" in c.lower())
           for c in calls) or status=="TIMEOUT":
        return "timeout"
    if any("=ERROR" in c for c in calls):
        return "error"
    if any("=UNAVAILABLE" in c or "=SKIPPED" in c for c in calls):
        return "skipped"
    if status in ("NOT_FOUND","NOT_FOUND_PARTIAL") or any("=NO_MATCH" in c for c in calls):
        return "no_match"
    return "skipped"


def empty_metrics(sources):
    return {p:{"attempts":0,"verified":0,"unique":0,"review":0,"no_match":0,
               "timeout":0,"error":0,"skipped":0,"seconds":0.0} for p in sources}


def report_csv(stats, source_count, completed_songs, elapsed, stopped=False, *, folder=None):
    """Atomically publish aggregate-only CSV, never any personal track metadata."""
    destination=Path(folder) if folder is not None else benchmark_report_folder()
    destination.mkdir(parents=True,exist_ok=True)
    timestamp=datetime.now().strftime("%Y%m%d_%H%M%S")
    path=destination/("LRC_Provider_Benchmark_"+timestamp+".csv")
    path=next((p for p in [path]+[destination/("LRC_Provider_Benchmark_"+timestamp+f"_{n}.csv")
                               for n in range(2,101)] if not p.exists()),None)
    if path is None:raise OSError("No free benchmark report filename")
    temporary=path.with_name(path.name+".tmp")
    try:
        with temporary.open("x",encoding="utf-8-sig",newline="") as handle:
            writer=csv.writer(handle)
            writer.writerow(["provider","attempts","verified_matches","unique_verified_matches",
                             "review_only","no_match","timeouts","errors","skipped",
                             "total_seconds","average_seconds","sample_songs",
                             "selected_sources","stopped_early","total_elapsed_seconds"])
            for provider,values in stats.items():
                attempts=values["attempts"]
                writer.writerow([provider,attempts,values["verified"],values["unique"],
                                 values["review"],values["no_match"],values["timeout"],
                                 values["error"],values["skipped"],round(values["seconds"],2),
                                 round(values["seconds"]/attempts,2) if attempts else "",
                                 completed_songs,source_count,int(stopped),round(elapsed,2)])
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary,path)
    finally:
        if temporary.exists():
            temporary.unlink()
    return path


def benchmark(folder,pack,mode,exclusions,limit=10,recursive=True,*,runner=None,
              source_files=None,read_info=None,report_folder=None,
              experimental_simpmusic=False):
    """Explicit online probe; only aggregates counts. No automatic LRC saves.

    Provider calls use exactly the same strict match functions as real searches.
    Every source is tested separately, including on songs matched by earlier
    sources, to capture genuine unique contribution instead of early stopping.
    """
    from stop_control import check_stop
    import LRC_Bulk_Finder as finder
    from search_profiles import PROVIDER_FAST,PROVIDER_FULL
    if limit not in (5,10,20):
        raise ValueError("Benchmark must use 5, 10 or 20 tracks")
    if mode not in ("fast","full"):raise ValueError("Unknown FAST/FULL mode")
    if pack not in {LEGACY,*PACKS}:raise ValueError("Unknown provider pack")
    if not isinstance(exclusions,list):
        raise ValueError("Provider exclusions must be a list")
    legacy=PROVIDER_FAST if mode=="fast" else PROVIDER_FULL
    if pack==LEGACY and mode=="full" and experimental_simpmusic:
        legacy=legacy+("SimpMusic",)
    sources=effective_sources(pack,legacy,exclusions)
    if not sources:raise ValueError("No providers enabled")
    check_stop()
    samples=select_sample(folder,limit,recursive,files=source_files,read_info=read_info)
    if not samples:raise ValueError("No eligible songs with title and artist in selected folder")
    # A benchmark must be a fresh real probe, not a replay of cached NO_MATCH.
    finder.HISTORY_ENABLED=False
    finder.MB_ENABLED=False
    finder.GREEK_MODE=False
    finder.G2G_ENABLED=False
    finder.LOCAL_LRCLIB=None
    finder.STAGED_ONLINE_MODE=False
    finder.COMPLETE_FIRST_PASS=False
    finder.ACTIVE_PROVIDERS=sources
    finder.blocked.clear()
    finder.load_provider_cooldowns(Path(folder)/"LRC_Provider_Cooldowns.json")
    from runtime_paths import program_folder
    finder.configure_lrclib_contact(program_folder())
    search=runner if runner is not None else finder.search_song
    metrics=empty_metrics(sources)
    began=time.monotonic()
    completed=0
    stopped=False
    print(f"BENCHMARK START: {len(samples)} songs, {len(sources)} sources; no lyrics or tags will be saved.",flush=True)
    print("BENCHMARK SOURCES: "+", ".join(sources),flush=True)
    try:
        for n,(_path,title,artist,album,duration) in enumerate(samples,1):
            check_stop()
            found_on_this_song=False
            for source in sources:
                check_stop()
                review=finder.CandidateReview()
                timers=[]
                calls=[]
                started=time.monotonic()
                try:
                    hit,status,_detail,calls=search(
                        title,artist,album,duration,review,only_providers=(source,),
                        retry_targets=set(),timings=timers,request_traces=[])
                    kind=classification(hit,status,calls,review.count.get(source,0))
                except (OSError,ValueError,RuntimeError) as exc:
                    kind="error"
                    print(f"BENCHMARK WARNING: {source} {type(exc).__name__}: {str(exc)[:80]}",flush=True)
                finally:
                    metrics[source]["attempts"]+=1
                    metrics[source]["seconds"]+=time.monotonic()-started
                metrics[source][kind]+=1
                if kind=="verified" and not found_on_this_song:
                    metrics[source]["unique"]+=1
                    found_on_this_song=True
            completed=n
            print(f"BENCHMARK PROGRESS: {n}/{len(samples)} songs; "
                  f"elapsed {int(time.monotonic()-began)}s",flush=True)
    except KeyboardInterrupt:
        stopped=True
        print("BENCHMARK STOP: partial aggregate results only; music unchanged.",flush=True)
    finally:
        report=report_csv(metrics,len(sources),completed,time.monotonic()-began,
                          stopped,folder=report_folder)
        print("BENCHMARK REPORT: "+str(report),flush=True)
        print("BENCHMARK NO AUDIO WRITES: only an aggregate report was created.",flush=True)
    return metrics,report,stopped
