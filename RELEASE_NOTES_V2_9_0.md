# LRC Bulk Finder v2.9.0 — Smart Library & Stability (Public Beta)

Builds on the published v2.8.0 karaoke version without changing search/provider strategy, strict matching, rate limits, STOP, safe undo, or original media and lyrics.

## Smart Library
- Fifth nested Sync Lab tab; existing eight main tabs preserved.
- Private incremental SQLite index at APPDATA/LRCBulkFinder/smart_library_v290.sqlite3 (not in music folders), 100,000-track maximum and paginated 200-row review.
- QC warnings: missing or candidate-only LRC, ambiguous audio stems, malformed/untimed/empty/oversized LRC, legacy CP1253/unsupported UTF-16, duplicate and out-of-order timestamps, very large gaps, late/early lyrics, offset and title-metadata discrepancies.
- Optional slower deep-duration checks. Repeat scans reuse unchanged audio/LRC size+mtime fingerprints; these are performance heuristics, not cryptographic proof of file identity. The directory tree is still traversed each time.
- Unicode/Greek filename search, issue filters, Bookmarked/Reviewed tags, bounded recent scan history and one-click open in Lyrics Studio.
- Safe cancellation rolls back the incomplete SQLite transaction; the previous successful inventory remains available.
- Filtered CSV export is confirmed and exclusively created with UTF-8 BOM and spreadsheet formula-injection protection; no existing CSV is overwritten.

## Stability and safety
- Fixed native optional VLC-to-pygame transition when selecting a different song after changing playback speed; each newly selected audio starts on a fresh normal 1x backend.
- Existing original music, ID3, primary LRC, candidates, karaoke playlists, search profiles and undo journals are not modified by Smart Library.
- All 266 original owner-approved Greek translations are preserved, with additive Smart Library Greek labels.
- Search provider APIs can change; LRC quality warnings indicate possible issues, not proven incorrect lyrics. No automatic copyrighted lyric upload, AI transcription, word-level generation, file repair or overwrites.
- Separate native VLC installation remains required for optional non-1x speed. Windows code signing remains pending independent SignPath Foundation approval.

## Final acceptance and release
Regression test matrix: Windows and Ubuntu Python 3.10/3.13; additional Tk tests, 10k song stress, deep QC/cancel rollback, real pygame WAV smoke, STOP process stress, frozen dual Windows EXE startup, complete English/Greek PDF guides, archive and published SHA-256 verification. Details in TEST_AUDIT_V2_9_0.md.

This is the intended **full-day hands-on test build before v3.0**, the planned final major release in 2026. Publish v2.9.1 **only** if actual acceptance testing identifies reproducible defects.
