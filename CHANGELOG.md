# Changelog

This changelog summarizes documented beta milestones; it is not a verbatim Git commit history.

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
