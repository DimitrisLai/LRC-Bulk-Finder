# LRC Bulk Finder v2.9.2 — Large-library Search Preflight Stability (Public Beta)

A targeted fix for a user-observed 3,183-track Greek library, where a 20-song search remained on zero counters during the preflight stage for several minutes. Earlier Smart Library, Lyrics Studio, karaoke, Greek translation and strict matching features remain.

## Fixed
- **20-song limit BEFORE costly ID3 metadata reads.** Preserves established ordering, filename- and ID3-tag LIVE exclusions, already present .lrc, selected-track allowlists and the ALL option. A tag-LIVE song does not consume a test slot.
- **Real GUI progress** during DISCOVERY, INDEXING and PREFLIGHT: inspected candidate count, selected/target count and meaningful phase labels instead of an unexplained zero search counter.
- **Safe STOP** during discovery, indexing and each metadata candidate.
- **Real MP3 metadata correction:** when the MP3 has a title tag, no artist, and a Song - Artist filename, a known artist suffix may be used as a filename hint; unknown artist placeholders remain explicitly unknown. Valid tags and the original Artist - Song fallback are preserved.
- **Private actual MP3 tests:** three user-supplied Greeklish-named MP3s were read, timed, and decoded for a brief segment. All SHA-256 hashes were identical after the test. None of those songs or audio bytes are published, bundled, or committed.
- Optional source-only QA_V292_REAL_MP3.py lets users privately validate their own real local MP3 files without internet or writes. Synthetic 3,200-track, cancellation and Tk-progress regressions cover the large-library bug.

## How to use
Extract the full standalone Windows ZIP and run LAUNCH_LRC_BULK_FINDER_WINDOWS.cmd or LRC_Control_Center.exe. Do not start Worker.exe manually. For 20 Greek tracks use Quick Search, select Greek/Greeklish matching and Test 20 Songs (normal online action, no local AI). Greek FULL — Offline First still requires the downloaded local LRCLIB database.

## Release gates
Windows and Ubuntu Python 3.10/3.13; all prior regressions, 3,200-file preflight, 10k index stress, native GUI tests, STOP, real WAV preservation, frozen Windows GUI+Worker, updated English/Greek manuals, 2 ZIPs and public-download SHA-256 check.

This is a pre-v3.0 stability-only update, not an online provider overhaul. The Windows binaries are unsigned pending independently granted SignPath approval.
