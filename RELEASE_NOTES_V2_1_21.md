# LRC Bulk Finder v2.1.21 — Reliability and Accurate Offline Search

Public beta. Created by Dimitris L.

## What's new

**Third Greek-search variant enabled offline.** The locally downloaded LRCLIB database now checks up to six approved, distinct search combinations (instead of two), including *Greek title + approved Greek artist* for songs such as `Giorgos Alkaios - Kimata`. SQL candidate counts remain bounded, and the strict recording and duration verification rules are unchanged.

**Persistent review status.** If an earlier stage found timed candidate lyrics but a later provider timed out or returned no match, the final song remains marked for review rather than being incorrectly classified as not found. `.candidate.lrc` sidecars are preserved.

**Crash-resilient resume checkpoints.** Options 1 and 5 append a new, versioned `LRC_Run_Checkpoint_v2_1_21.jsonl` entry for each completed song/stage. Relaunching with the *same settings and unchanged MP3s* skips completed work and reconstructs corresponding provider/candidate/report rows. A partially written final line is ignored. Changed song size/mtime, aliases, provider settings or LRCLIB snapshot invalidate obsolete entries. Move or rename this checkpoint file to force a completely fresh run.

**Broader automated tests.** The previous v2.1.20 workflow selected 10 modules. v2.1.21 reviews and enables all 22 historical/current `TEST_*.py` modules on Windows and Linux (Python 3.10 and 3.13), with fixture cleanup and version-agnostic test fixes where needed.

## Preserved safeguards

- No writes to MP3 audio or ID3 metadata, no overwrites of existing `.lrc`.
- Option 2 `[00:00.00] candidate` and numbered candidate shifts unchanged.
- Option 4 remains strictly local/offline.
- Option 5 remains local-first for *all* eligible songs, online misses, then genuine timeout-only retries.
- Respect 401/403, 429, 503 and per-provider cooldowns.
- Compatible with the existing downloaded LRCLIB SQLite: no database copy or redownload.

## Install

Extract the complete **v2.1.21 Windows ZIP**, run `START_HERE.cmd`, and reconnect your already-downloaded large SQLite database using `CONNECT_EXISTING_LRCLIB_DATABASE.cmd` if necessary. See `HOW_TO_START_V2_1_21.txt` for every prompt in order and restart behavior.

This beta does not guarantee that all online providers work, or that every recording has synchronized lyrics.
