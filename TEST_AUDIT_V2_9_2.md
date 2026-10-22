# v2.9.2 — Search preflight stability / real-MP3 QA audit

## Observed bug
A real 3,183-song search screenshot showed progress stalled after incremental indexing, before Round 1. v2.9.1 code parsed ID3 metadata for every eligible song before applying the user-selected 20-song limit. The lyric counters correctly remained zero but the GUI showed no progress.

## Code changes
- v292_preflight.py implements bounded, stop-aware candidate selection in the same order, retaining filename and title-tag LIVE checks and normal Artist–Title fallback.
- v2.9.2 now selects 20 songs without pre-reading thousands of tags and reports DISCOVERY, INDEXING and PREFLIGHT progress to Live Progress.
- Explicit allowlists still fail closed. Invalid MP3 metadata is still eligible for fallback error reporting, not silently discarded.
- Artist placeholders remain missing rather than becoming false positives.
- Original audio, ID3, primary LRC and existing candidates remain protected by the same no-overwrite policy.

## Real user MP3s privately tested
Three uploaded Greeklish-named MP3s were inspected with mutagen for title, artist, album, duration and bitrate. ffmpeg decoded the first two seconds of each to PCM successfully, and before/after SHA-256 values were identical. Two full songs have titles/artists. A short 39-second clip has a title but lacks an ID3 artist, and ends in a literal unknown artist placeholder in its filename. No originals or copyrighted audio are in GitHub or release artifacts.

## Automated gates
Four-platform Windows/Ubuntu Python 3.10/3.13 regression suite; synthetic 3,200-track test verifying only the selected 20 song tags are read; title-tag LIVE exclusions; STOP; Unicode/Greek ID3 edge cases; real progress in native Tk; historic 10k/Smart Library tests; Windows frozen two-EXE/STOP; English/Greek PDFs; published ZIP SHA-256 validation.

## Remaining human QA
Online provider connectivity is subject to external services. Real user's collection, damaged MP3s, external drives, Windows audio hardware and car radios need in-person testing. Progress counts completed operations, not guaranteed wall-clock ETA. Independent SignPath code-signing approval remains pending. v3.0 is still planned as the final major release for 2026.
