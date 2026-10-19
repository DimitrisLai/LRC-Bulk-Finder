# LRC Bulk Finder v2.3.0 — Control Center, Profiles, Progress & Safe Review

Public Beta • Created by Dimitris L.

## New Windows Tkinter Control Center

The complete Windows ZIP contains **OPEN_CONTROL_CENTER.cmd**, launching a native GUI built with Python's standard library. The original CLI **START_HERE.cmd** remains intact. The GUI features three tabs:

1. **Saved searches:** Profile manager for Options 1/4/5. Save named MP3 folders, offline LRCLIB SQLite paths, Greek/local AI/MusicBrainz settings, FULL/FAST mode, provider priority, recovery waiting, recursion, history, number of songs, exact fallback, and preview-only/automatic search. Profiles persist locally under Windows user **%APPDATA%/LRCBulkFinder/profiles.json**, saved atomically, with strict validation. Unknown prompts abort safely.
2. **Live progress:** Streaming output, phase-aware progress bar and THIS ROUND ETA calculated from actually completed (not checkpoint-replayed) songs, after three samples; does not invent an end-to-end ETA for unknown later rounds. Stop requests a process interrupt; durable checkpoints survive hard stops.
3. **Candidate review:** Discover all primary and numbered .candidate.lrc files, preview lyrics without changes, open the MP3 in its default player, and explicitly confirm promotion of ONE primary candidate. The resulting LRC is **[00:00.00] candidate**, visibly UNVERIFIED. The original MP3/ID3, existing approved LRC and other candidate safeguards remain.

### CLI improvements
Option 1/5 and Option 4 now show clear per-round completion percentage, elapsed time and sensible ETA based on measured time. Resume-replayed songs count as complete without skewing the ETA.

### Optional standalone EXE
A separately packaged Windows GUI+worker EXE bundle may be published after separate build and verification. It will not replace the complete Python/CMD release. Local AI model files are intentionally not embedded; using them may require the original Python installation.

### What stays unchanged
- Strict title, artist, duration, live/remix/version matching.
- Original MP3/ID3 and existing verified .lrc files untouched.
- Option 5 offline-first all missing songs, online misses, then only genuine timed-out providers.
- Persistent MusicBrainz cache and verified-only provider performance from v2.2.
- Candidate review marker and numbered shifts from earlier versions.
- Downloaded large LRCLIB SQLite reused, not copied or downloaded.

### Install
Download the **complete v2.3.0 Windows ZIP**, extract into a **new folder**, double-click **OPEN_CONTROL_CENTER.cmd** for the new GUI or **START_HERE.cmd** for original CLI. Reconnect an existing large LRCLIB database via the bundled connector. Read [HOW_TO_START_V2_3.txt](HOW_TO_START_V2_3.txt) for all GUI choices and CLI prompt sequence.

### Testing
Full Windows/Linux Python 3.10/3.13 legacy regressions plus independent v2.3 GUI/profile/candidate/ETA tests. Tkinter widget smoke test on Windows may require a desktop session, so automated tests don't prove GUI rendering in every Windows configuration or live-provider availability.
