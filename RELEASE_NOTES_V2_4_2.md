# LRC Bulk Finder v2.4.2 — Instant Stop and Clearer Live Counters

**Public Beta maintenance update** building on v2.4.1. Existing library search, verification, six presets and candidate safeguards remain unchanged.

## One-click STOP (no app exit)

The first Stop click now requests confirmation to **immediately terminate the background search worker process tree**, instead of waiting on a file-based graceful-stop signal or a later Force Stop. It acts only on the worker; **the Control Center remains open**. A background thread handles termination so the Tk interface is not blocked.

Windows uses `taskkill /T /F` to include subprocesses created by the packaged standalone EXE. The Python/Linux implementation stops the worker's own process session. Completed song/stage checkpoint entries remain durable and can be resumed. **Hard termination can lose the currently incomplete song and any not-yet-written final reports**, so rerun the same saved profile when needed.

## Stage counters separate from persistent totals

The Live Progress tab now has two clearly separated groups:

| Current stage: reset after Round 1, 2 and 3 | All stages: cumulative until a new run |
|---|---|
| Songs / LRC found | LRC Count |
| Songs / Candidate found | Candidate Count |
| Not found | |

All counts are of **unique songs** per category. One song with 2–3 review files contributes **1** to Candidate Count. A review candidate later upgraded to a verified LRC may legitimately be represented once in each historical total. Stage counters return to 0 at the end of each completed stage; totals stay visible between rounds. Only review candidates actually written as sidecar files count—metadata-only, unsaved review notes do not inflate candidate totals. Timeouts and server errors are not definite misses.

## Tests

Full Windows/Linux Python 3.10/3.13 regression suite, new real-process termination tests and Windows Tk user-interface smoke tests, plus official Windows package integrity, PDF, and standalone EXE smoke checks. Automated checks cannot guarantee availability or accuracy of external lyric services.

## Install

Download and extract the full **v2.4.2 Windows ZIP** into a NEW folder, preserving v2.4.1 as backup. Open `OPEN_CONTROL_CENTER.cmd` or `START_HERE.cmd`. Alternatively use the separately published standalone Windows GUI+worker ZIP. Existing large LRCLIB SQLite snapshot remains external; reuse it rather than downloading again.
