# v2.9.0 — Code review, safety audit and full-day Windows acceptance

## Code-review coverage
Reviewed the provider/STOP and worker boundary, safe v2.5 Manager undo, v2.6 candidate no-overwrite design, v2.7 playback/waveform, v2.8 instrumentals and karaoke playlist, and the new Smart Library indexing path. Existing search matching and APIs were deliberately not refactored in this stability update.

Stability change: reopening a new audio track after optional VLC variable-speed playback must reset to a normal, live pygame backend rather than trying to reuse a released VLC object.

Smart Library: index only metadata and quality summaries in a private SQLite database, not the lyrics themselves; validate roots/symlinks, cancel with SQL rollback, paginate, bound to 100k tracks, reject future schema versions, and protect CSV exports and existing source files.

## Automated gates and exact evidence
- Four Python CI environments: Windows 3.10 / 3.13; Ubuntu 3.10 / 3.13.
- Full offline regressions, Greek/English native Tk GUI tests and 10,000-file library inventory, incremental cached scan, Unicode filename query, explicit CSV formula safety, deep LRC validation, cancellation and history tests.
- Native Windows repeated STOP/child process verification, actual synthetic WAV playback with unchanged SHA256, PyInstaller frozen GUI/worker launch.
- Updated PDFs in English and Greek; source/standalone ZIP integrity and SHA-256 manifest; public download re-verification.

## Full-day test before v3.0
1. Copy a representative folder of your real music first. Download ZIP + SHA256 from official release; extract ALL files and launch the Control Center.
2. Quick Search, Saved Searches, provider health, offline/online, selected retry, safe Undo, STOP while active, full reports and candidate review.
3. Smart Library first scan; repeat unchanged scan; change one copied LRC and rescan; explore Greek filename search, duplicate/out-of-order flags, bookmark/review markers, cancel a larger scan and export CSV to a NEW path.
4. Open an affected track directly in Lyrics Studio, edit individual stamps, Undo/Redo, view read-only waveform, export a uniquely numbered candidate and compare original music/LRC hashes.
5. Karaoke Edition: add instrumentals, auto/manual pair LRC, reorder, drag/drop, next/previous, countdown, A-B loop, offset, full-screen second display, Greek fonts, background and optional installed VLC speed.
6. English and Greek UI, Windows 11 100%/125%/150% scaling, windows resize, restart, offline mode, native car-radio LRC behavior, both PDFs.
7. Record any reproducible issue as a GitHub issue with version and exact steps. Do not upload copyrighted songs/lyrics or unredacted private logs.

**Decision:** a small v2.9.1 stability-only patch makes sense if this hands-on day identifies defects; otherwise go directly to v3.0. This is a Public Beta: virtual CI does not certify real soundcards, karaoke projectors, every audio codec or actual vehicle head units.
