# LRC Bulk Finder v2.7.0 — QA audit

**Date:** 22 October 2026.
**Baseline:** v2.6.0.
**Development:** feature/v2.7.0-karaoke-precision, PR #12.
**Purpose:** preserve all prior search, STOP, bilingual and no-overwrite behavior while adding instrumental karaoke and precision utilities.

## Verified by automated tests

- Four regression environments: Ubuntu/Windows with Python 3.10/3.13 **PASS, 409 tests** after the new 10,000-track inventory test. [GitHub four-platform QA](https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/runs/39784696741).
- **10,000 disposable MP3 placeholders** arranged in 100 folders were inventoried read-only. On Windows Python 3.13, the inventory benchmark printed **18.26 seconds** (runner-specific; not a UI benchmark, not a guarantee of production speed). Counts: 10,000 total, 9,998 missing LRC, 1 present, 1 needs candidate review. All original file sizes stayed unchanged.
- A fully successful Windows packaging rehearsal [run 39783841329](https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/runs/39783841329) executed **408 pre-scale regression tests plus 27 extra adversarial GUI tests** and native nested worker STOP trials. Its real SDL WAV play/pause/resume/stop smoke preserved the audio SHA-256; frozen Windows GUI launched; the frozen worker STOP marker was independently acknowledged; bilingual manuals built; ZIP/package inspections and manifest passed.
- The final v2.7.0 code includes direct Results dashboard/Candidate review import, private draft integrity checks, timing warnings and invalid export blocking, exclusive candidate creation and no audio/ID3 writes, karaoke lyric display/controls, configurable shortcuts, loop A/B, read-only waveform and a mock-tested optional VLC speed adapter. Unit and disposable Tk journeys are included in TEST_V270_FEATURES.py and TEST_V270_GUI.py.
- Original 266 owner-reviewed English↔Greek translations are preserved using additive mapping. The main notebook still has eight tabs, with one extra nested Precision & Karaoke view.

## Honest limitations

- Windows/Linux CI uses synthetic audio, fake VLC playback where appropriate and a bounded real WAV smoke test. It **does not** certify native VLC speed adjustment on every PC, every compressed codec/MP3 seek, every installed sound device, or actual car-radio LRC rendering.
- The waveform is a *sampled visual overview*, not a full-fidelity spectrogram. PCM WAV is native; MP3/FLAC/OGG decoding depends on optional soundfile/libsndfile.
- Non-1x speed requires compatible native VLC installed, not included in the portable ZIP; python-vlc alone is insufficient.
- Karaoke is LINE-level display synchronized to the current recording; no vocal removal or automatic word-level alignment. A user provides audio and rights-cleared lyrics.
- One 10,000-song distributed-folder inventory took 18.26 seconds on a GitHub Windows runner; large directory/GUI redraw performance remains a target for 2.9's SQLite indexed library, not something proven near-instant.
- Visual inspection of every PDF page and full Windows 100–150% DPI testing on the user's own PC is still required.
- SmartScreen warning is separate from QA. SignPath Foundation code signing is not verified.

## Real-PC release acceptance checklist

1. Extract entire standalone ZIP, keep both EXEs together and verify release SHA256.
2. Run English and Greek modes at 100%/125%/150% DPI; check all new buttons, nested tabs and truncated text.
3. With a **copied** test set, open MP3/FLAC/WAV, import your own LRC and make sure karaoke highlights current and upcoming lines in fullscreen without rewriting either input.
4. Play/pause/seek, A–B loop, change shortcuts, nudge selected lines, review warnings, inspect waveform zoom and cancel. If VLC 64-bit installed, separately test 0.75x/1.25x and device stability.
5. Save multiple numbered candidates in all three export profiles; ensure no audio, tags or original/older candidate bytes are modified.
6. Interrupt after editing, restart and recover the private draft; modify source LRC/audio and confirm stale recovery is rejected.
7. Try invalid timestamps, very large files, unsupported formats, missing/ambiguous same-stem audio, cancellation, STOP and offline operation.
8. Visually inspect the English/Greek PDFs and confirm car-radio compatibility independently.

**Release rule:** only claim final release when main CI, both Windows packages, publication download hashes and GitHub release status all succeed. Keep prior release assets intact.
