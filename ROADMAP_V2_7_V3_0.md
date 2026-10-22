# Product review: LRC Bulk Finder v2.7 vs v3.0

This roadmap is a proposal, not an announcement. Existing v2.5 search, Greek/Greeklish matching, selective retry, safe STOP, and no-overwrite guarantees remain contractual.

## What v2.6.0 adds

- A new Lyrics Studio inner workspace without changing the eight main Control Center tabs.
- Local player (pygame/SDL_mixer), timed-line preview, stamp/nudge/exact positions, undo/redo.
- Read-only LRC imports, classic Sync Lab interoperability, safe candidate-only exports.
- Extra EN/EL translations, offline tests, Windows player smoke and versioned package pipeline.
- No waveform, word-sync, audio transcription, AI model, background music analysis or proprietary-format conversion.

## Proposed v2.7 — Precision and usability (incremental release)

| Priority | Change | User value | Risk / acceptance criterion |
|---|---|---|---|
| P0 | Open in Lyrics Studio directly from Results dashboard and Candidate review | One-click search → review → correct | Do not edit originals; inspect selected path and candidate origin |
| P0 | A–B loop and rewind 1/5 seconds | Repeat difficult verses without losing position | Pause/resume/seek accurate across MP3/WAV/FLAC/OGG; real codec tests |
| P0 | Timestamp warnings (duplicates, out-of-order, overlaps, large gaps, beyond duration) | Avoid broken car-player lyrics | No automatic silent correction; export blocks invalid standard LRC |
| P1 | Waveform with horizontal zoom and time markers | Human timing correction becomes visual | Lazy bounded-memory waveform, read-only local audio, cancelable decode |
| P1 | Playback speed 0.75x, 1x, 1.25x (ideally pitch-preserving) | Easier listening/tapping | Test backing engine before advertising; no corrupted sound |
| P1 | Autosaved local **draft recovery** in APPDATA | Recover from accidental close/crash | No original sidecar overwrite; clear ownership; fingerprint checks |
| P1 | Multiple-line selection shifts, 10/50/100ms nudge, customizable hotkeys | Faster timing edits | Full keyboard/focus tests, no conflict with normal text entry |
| P2 | Export compatibility options (UTF-8/BOM, 2/3 decimal timestamp, player profile) | Better hardware LRC support | Strict validation; do not assume every car stereo supports LRC |
| P2 | More granular status/diagnostics for playback backends | Explain codec/device failures | No absolute filenames, song text or personal paths in support report |

### Release-ready definition for v2.7

On top of v2.6: 4-matrix CI green, GUI and worker frozen Windows smoke, repeat WAV/MP3/FLAC seek exercises, no original audio/LRC writes, large 10k-track dashboard responsiveness, multilingual/manual checks at 100–150% DPI, checksum-verified ZIP assets. Preserve offline operation and approved 266 original Greek strings.

## Proposed v3.0 — Advanced syncing (major architecture release)

| Area | Upgrade | Essential safeguard |
|---|---|---|
| Word-level editor | Enhanced LRC word and syllable boundaries with karaoke-like highlighting | Explicit project format, lossless original preservation, backward-compatible line-LRC export |
| Assisted alignment | OPTIONAL local forced alignment against lyrics the user supplies | Clearly label guesses UNVERIFIED; offline privacy by default, never secretly upload audio |
| Formats | Optional import/export SRT, TTML, Enhanced LRC, Lyricsfile and plain text | Preserve metadata and report any lossy conversion |
| Better playback engine | Pluggable decoder with reliable seek/speed/loop on common formats | License review, signed package feasibility, repeatable Windows behavior |
| Library index | SQLite incremental search of hundreds of thousands of tracks, batch Studio queue | Migration backups, checkpoints, deterministic rollback and low memory usage |
| Provider architecture | Testable adapters with backoff and explicit provider outcomes | Respect 429/503, rights and terms; never auto-install uncertain lyrics |
| Accessibility | Resizable panels, contrast controls, keyboard-first editing | Test with Greek layouts, screen readers and high DPI |

### Reasons not to rush AI into v2.6

Models require downloads, may be inaccurate on Greek vocals and remixes, add disk/memory/GPU requirements and may expose copyrighted audio to third parties. A safe v3 workflow would be optional, offline-first, evidence-labeled and human-reviewed rather than an automatic "fix".

## Competitive benchmarks

- LRCGET: rich browser/editor, line and word-level syncing, playback speed control, LRCLIB integration.
  https://github.com/tranxuanthang/lrcget
- Lyrical Sync: waveform markers and realtime keyboard stamps.
  https://github.com/AHRI2nd/Lyrical-Sync
- samgum/lrc-editor: waveform/spectrogram, timing warnings and many lyric formats.
  https://github.com/samgum/lrc-editor
- MakeLRC: lightweight, simple stamp-and-export experience.
  https://makelrc.com/editor/

**Recommendation:** v2.7 should perfect local editing and one-click library navigation; v3.0 should be reserved for actual word-level synchronization, advanced format migrations and optional smart alignment. Signing via SignPath Foundation remains a separate external approval and must not be misrepresented as done.
