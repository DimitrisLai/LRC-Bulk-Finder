# LRC Bulk Finder v2.4.0 — Greek Presets, Library Index & Experimental Sync Lab

**Public Beta**, created by Dimitris L. No fingerprint identification is included.

## Ready-made search profiles

The Control Center provides six built-in **editable templates**: Greek FULL Offline First, Greek Night Search Maximum Coverage, Greek 20-Song Quick Test, Greek OFFLINE ONLY, Greek Local AI FULL and International FAST 20 Songs. Selecting a template fills the existing toggles and leaves personal saved profiles intact. 'Night' selects full coverage and recovery waiting: it is an unattended preset, **not a background scheduler**.

Hover on preset/setting controls for descriptions covering Greek mode, optional local AI, MusicBrainz, fallback, recovery, subfolders, history, automatic search and new incremental index.

## Setup buttons

The Windows GUI now has LRCLIB database download/setup and Greek G2G AI setup buttons. In the Python/CMD package these open the existing consent-based setup scripts. In the optional standalone EXE, the LRCLIB installer is a separate console worker action; Greek local AI still needs the separate Python environment, so the button opens the full package's release instructions. The large LRCLIB dump and heavyweight G2G model are **not bundled**.

## Incremental library

An optional, default-on GUI setting maintains `LRC_Incremental_Library_v2_4.sqlite3` in the music folder, saving read-only audio metadata and detecting new/changed files by size and nanosecond mtime. The existing downloaded lyrics, provider checkpoint, rate limits and strict recording matching are preserved. Disable the toggle to use normal metadata reads.

## Additional audio formats

Sidecar searches work with **MP3, FLAC, M4A, MP4, OGG, OPUS and WAV** where Mutagen reads usable duration and metadata. Source audio/ID3 is never written. Ambiguous same-stem files, e.g. `Song.mp3` and `Song.flac`, are skipped rather than sharing a possibly incorrect `Song.lrc`.

## Experimental Sync Lab

New Control Center tab for **user-provided untimed lyric text**. Estimate rough timestamps from audio duration, or manually tap lyrics while listening using an external audio player; preview/edit results. The tool saves only explicitly marked `[00:00.00] candidate` sidecars after user confirmation. It **does not perform forced alignment, automatic transcription or validation of actual spoken timing**. Existing approved `.lrc` sidecars and original audio files are never overwritten.

## What stays the same

Five-mode CLI, Option 5's local-all → online-misses → genuine timeout-only retries, per-round ETA, Greek word/artist dictionaries, MusicBrainz cache, SMART/CUSTOM ordering, incremental checkpoints, and strong duration/version verification remain. No acoustic fingerprint feature has been added.

## Install

Extract the **complete v2.4 Windows ZIP**, use `OPEN_CONTROL_CENTER.cmd` or `START_HERE.cmd`. A separately tested standalone EXE package is optional. Keep any earlier verified v2.3 archive as an offline fallback. See `HOW_TO_START_V2_4.txt` for full instructions.

## Testing limitations

Automated Windows/Linux tests use local fixtures and simulated providers. They do not guarantee live remote lyrics coverage, local external AI model readiness, or SmartScreen reputation. Longer live workloads should still be trialed on your own collection.
