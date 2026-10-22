# LRC Bulk Finder — Roadmap after v2.7.0

## v2.8 — Karaoke UX & audio reliability

1. Two-screen karaoke: operator controls on one window, projector/fullscreen lyrics on another, with window position persistence.
2. Practice presets: countdown before vocals, A–B loop presets, next line visibility setting, karaoke colors/font sizing and keyboard-friendly fullscreen.
3. Manual lyric/audio pairing library and external named LRC import without changing original file names; export all as new candidates.
4. More trustworthy playback position with seek-calibration tests on MP3, FLAC, WAV and OGG, including reduced latency when jumping between lyrics.
5. Optional supported pitch-preserving slow playback backend, with native dependency packaging tests and explicit user consent; keep 1x stable.
6. Waveform zoom-to-line/drag-time marker edits, timing quality score and saved queue of files needing correction.
7. A standalone offline karaoke-session mode with no provider calls; audio-only local play and no automatic screen/video recording.

**Why 2.8:** polish the new karaoke and precision workflow instead of introducing risky AI too soon. Requires real dual-display and music device testing.

## v2.9 — Library intelligence and release hardening

1. Batch QC audit of LRC files: missing, duplicate, invalid syntax, wrong duration, non-monotonic timestamps, suspicious offset, encoding and title mismatch; export CSV review queue.
2. Incremental SQLite inventory for 10k+ tracks with explicit migration and rollback.
3. One-click Studio review queue, bookmarking, resumable editing sessions, protected history.
4. Improved reader compatibility presets, Unicode normalization and real device samples, with no rewrite of source files.
5. Plug-in architecture for optional waveform/VLC/player backends and provider tests; rate limits and candidate verification unchanged.
6. Rich diagnostics with privacy redaction, opt-in debug bundle, accessibility QA and Windows 100–200% DPI checks.
7. Reproducible releases: SHA-256, independent binary tests, supply-chain review, SignPath code signing once approved.

**Why 2.9:** stabilize large library performance, audit, packaging and accessibility before breaking changes.

## v3.0 — Advanced sync architecture

1. Word-level Enhanced LRC karaoke (per-word color fill), with clean standard line-LRC fallback for car radios.
2. Optional, genuinely offline-assisted forced alignment against user-supplied lyrics: confidence scored, human approval mandatory, UNVERIFIED until reviewed. No background upload.
3. Pluggable playback engine with reliable seek/tempo/loop and optional instrumental/vocal stem separation as a separate opt-in tool (model download, time/disk/GPU cost and copyright rights documented). Do not promise quality without real model/Greek singing benchmarks.
4. Wider subtitle/lyrics formats (SRT, TTML, Enhanced LRC) with explicit conversion preview and lossy-format warnings.
5. Improved project-based editor with reusable undoable source snapshots and migration tests. Original audio/ID3/LRC stay immutable without explicit safe export.
6. Accessibility, locales, performer-friendly projector UX and mature contributing/provider architecture.

**Version rule:** v3.0 should represent a genuine format/model/architecture milestone, not merely new buttons. Publish each version only with verified Windows artifacts, updated Greek/English manuals, regression evidence and SHA-256 manifest.
