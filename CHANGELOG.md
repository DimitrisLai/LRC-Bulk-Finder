# Changelog

This changelog summarizes documented beta milestones; it is not a verbatim Git commit history.

## v2.1.18 — Large public Greek word lexicon and read-only SQLite
- Added 950 separate Greeklish word spellings to the public `Greek_Words_Expanded.csv`, drawn from recurring spellings in a large Greek music example list (without sharing private song filenames or personal paths).
- Added reproducible SQLite database builder `BUILD_GREEK_LEXICON_DB.py`, combining public words and customizable `Greek_Words.csv` into an optional small read-only `Greek_Lexicon.sqlite3` included in the Windows ZIP.
- Added safeguards for database corruption, out-of-date CSV fingerprints, user overrides and cross-platform Windows SQLite close semantics.
- Preserved original title/artist and remix, Option 2 `[00:00.00] candidate` behavior, strict match checking, and audio/ID3 safety.
- Added dedicated offline database regression tests and Linux/Windows Python 3.10/3.13 coverage.

## v2.1.17 — Greeklish quality and dictionary-first search
- Corrected Greek search-plan priority to **manual full title alias → verified accented word dictionary → optional local AI suggestion**.
- Expanded the small curated word-level Greeklish lexicon and preserved punctuation, years and remix/version labels.
- Avoided phonetic Greek nonsense for common English titles and international/mixed artist credits such as `2002 GR`.
- Made dictionary corrections apply to matching tokens in previously cached AI suggestions, without trusting invented spellings.
- Original artist/title search variants remain first; MP3 files and existing lyrics are not changed.
- Added isolated Greek-title quality regression tests on Linux and Windows.

## v2.1.16 — Marked bulk candidate promotion
- Option 2 installs a timed primary candidate as playable `.lrc` with `[00:00.00] candidate` at the beginning, visibly UNVERIFIED.
- Following promotion, numbered alternate candidates shift down one position.
- Existing `.lrc`, MP3 audio and ID3 tags are not modified. Explicit confirmation, CSV reporting and offline operation remain.
- Added offline Windows/Linux regression tests for the marker, shifting, repeat promotion and 110-song batch.
## v2.1.15 — Offline-only folder search
- Added **4 — OFFLINE LRCLIB ONLY** to scan any music folder, no prior catch-up queue needed.
- Added `CONNECT_EXISTING_LRCLIB_DATABASE.cmd`: link previously extracted SQLite without copying or redownloading hundreds of GiB.
- Added standalone offline scan/result review CSV files.
- Preserved strict artist/title/version/duration matching and original MP3 protection.

## v2.1.14 — Safe cleanup
- Added cleanup choices for compressed archive only, extracted database only, both or cancel; typed confirmation required.
- Added post-install disk usage feedback.

## v2.1.13 — Database discovery fix
- Updated automatic dump discovery to use structured LRCLIB catalog with safe filename checks and fallback.

## v2.1.12 — Automatic setup
- Added optional LRCLIB database installer; snapshot downloaded separately.

## v2.1.11 — Offline SQLite lookup
- Added local LRCLIB lookup and online LRCLIB HTTP 503 safety stop.

## v2.1.10 — Provider coverage
- Added first-attempt provider coverage report and improved temporary recovery handling.

## v2.1.9 — LRCLIB reliability
- Added catch-up queue, optional exact lookup and improved LRCLIB request pacing.

## v2.1.8 — Candidate review
- Added `.candidate.lrc` files and explicit promotion workflow.

## v2.1.7 — LRCLIB priority
- Updated search order and LRCLIB service overload handling.

## v2.1.6 — Diagnostics
- Added visible provider errors, request statuses and skip reasons.

## v2.1.5 — Metadata
- Enabled optional MusicBrainz lookup for Greek and international libraries.

## v2.1.4 — Public beta
- Improved history, rate limit handling, review reporting and packaging.

## v2.1.2–v2.1.3
- Public packaging and stricter version/duration checks.

## v1.x–v2.1.1
- Original multi-provider synchronized lyric search, Greeklish support, timeout-only retries and optional local G2G AI.
