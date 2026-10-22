# LRC Bulk Finder v2.7.0 — Instrumental Karaoke & Precision Lab

Public Beta candidate built on v2.6.0. No changes to provider order, Greek matching, checkpoint strategy, STOP, Library Manager undo, original audio or existing primary lyrics.

## Karaoke with instrumental audio and .lrc

Open Sync Lab → Lyrics Studio and choose an **instrumental** recording. If a corresponding timed LRC exists it loads read-only; otherwise use Load LRC... to import a chosen LRC file (even if its name differs), or From Classic Sync Lab to create timings from text you already have. In the nested **Precision & Karaoke** tab choose Open karaoke display. It shows large, line-by-line highlighted lyrics plus the upcoming line, synchronized to the selected local audio player position. F11 toggles fullscreen; Escape closes. It does **not** separate or remove vocals from songs, automatically transcribe audio, supply copyrighted lyrics or perform word-level alignment.

## Precision tools

- A–B looping with set-A, set-later-B, clear-loop, and rewind 1/5 seconds. Timing accuracy depends on the audio backend.
- Compact read-only waveform, zoom 1x/2x/4x/8x and click-to-seek. Native PCM WAV without extra dependencies; compressed audio waveform through optional Python soundfile/libsndfile, whose format availability depends on native codec support. Cancellable background sampling and bounded memory; neither waveform nor lyrics modify source audio.
- Export validation with duration warnings, duplicate or out-of-order timestamps, unusually short gaps and large gaps. Invalid LRC timestamps block export; warnings for unusually close/long lyric lines require human review.
- Private APPDATA Studio recovery drafts with original audio fingerprint and original lyric source hash check; recovery asks permission and never writes to originals.
- Nudge selected timestamps by 0.01/0.05/0.10 seconds, locally configurable lyric-tree-only keyboard shortcuts, and new candidate export profiles: Standard 2 decimals UTF-8; Precise 3 decimals UTF-8; Car radio 2 decimals UTF-8 BOM. All exports are explicitly marked UNVERIFIED, exclusively create new numbered .candidate.lrc files and cannot overwrite originals.
- Direct Open in Studio from Results dashboard and Candidate review, where existing candidate alternatives load READ-ONLY.
- Privacy-safe backend diagnostics without file names, paths, lyrics or media metadata.
- 0.75x / 1.0x / 1.25x speed controls: 1.0x uses the embedded pygame backend; variable playback speed **requires compatible VLC installed locally and the optional python-vlc binding**. No unsupported speed is silently claimed to work. The standalone package contains the Python binding but not VLC itself.

## Safety notes

- Source edition dependencies include pygame/mutagen (as in v2.6); optionally install soundfile for compressed waveforms and python-vlc plus native VLC for speed changes. All optional features degrade with a clear message.
- No automatic word-level sync, no voice extraction/removal, no online audio upload, no audio/ID3 edits. Lyrics and music rights remain the original owners' responsibility.
- Library Manager safe undo only covers search-created unchanged sidecars; manually saved Studio candidates are excluded.
- SmartScreen may still warn until the independent SignPath Foundation approval and actual code signing have completed.

## Acceptance checks

GitHub Actions must pass full Windows/Linux Python 3.10 and 3.13 offline regressions, extra adversarial GUI, Windows nested STOP, real SDL WAV smoke, package+frozen GUI/worker smoke, EN/EL PDF generation, ZIP integrity and SHA-256 hashes before publishing. Real-PC listening and screen/DPI testing remain manual checks.
