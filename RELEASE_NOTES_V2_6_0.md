# LRC Bulk Finder v2.6.0 — Lyrics Studio

**Development preview (not published until full QA passes).** Built on v2.5.0 Library Manager, with all previous search profiles, provider matching, selective retries, candidate review, STOP, session undo, and approved English/Greek strings retained.

## New Lyrics Studio

Open Sync Lab (experimental) → Lyrics Studio. Select an audio track. If a same-named standard timestamped .lrc exists, the program imports it read-only. Otherwise select Load LRC... or prepare plain text in Classic Sync Lab and choose From Classic Sync Lab.

- Embedded Play / Resume, Pause, Stop, ±5-second navigation and seek slider using optional pygame/SDL_mixer (MP3/WAV/OGG/FLAC where supported by the installed decoder).
- Live line highlighting and read-only timestamped lyric table showing the estimated playback position.
- Select a lyric line and Stamp selected at playback or use the Space key while its row is focused. The selection moves to the next line.
- Nudge selected lines by 0.10 seconds, enter an exact number of seconds, or use Undo/Redo (100 editing steps).
- Existing Classic Sync Lab remains accessible, including approximate estimate, manual tap timing, and its older safe candidate export.
- The UI is bilingual English / Ελληνικά; previously approved translations remain unchanged.

## Important limitations

- Neither player playback position nor estimated timing is automatic transcription or proof of synchronization. Accurate codec seeking varies by file format and SDL version; visually/audibly verify results.
- Embedded player is optional in the source edition: install pygame via pip. A correctly built Windows standalone package should bundle pygame. Opus/MP4/M4A cannot be promised by this backend; use the external player instead.
- Standard line-timed LRC only; word-by-word timing, waveform display, playback-speed adjustment, and AI alignment are not included in 2.6.
- Standard-LRC import normalizes timestamps and global offset on export; proprietary format extensions and arbitrary metadata are not guaranteed to round-trip.
- Legacy Greek text in CP1253 is supported for import; exported candidates are UTF-8.
- If two audio files share the same stem, candidate export is refused until the ambiguity is resolved.

## Safe data handling

No edits to original audio, ID3 tags, primary .lrc, or prior candidates. Studio save requires user confirmation and exclusively creates a new .candidate.lrc, .candidate.2.lrc, etc. Candidates are marked UNVERIFIED. Library Manager undo covers search-created files only; it deliberately does not delete manual Studio edits.

## Windows package/release QA gates

All Windows/Linux Python 3.10 and 3.13 regression suites, packaged Windows player smoke, frozen GUI/worker STOP tests, bilingual PDF manual inspection, ZIP integrity, and SHA-256 verification must succeed before a new GitHub release. Windows SmartScreen signing remains a separate pending external process.
