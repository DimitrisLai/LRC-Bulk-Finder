# LRC Bulk Finder v2.6.0 — QA & Release Audit

Date: 22 October 2026. Scope: feature branch `feature/v2.6.0-lyrics-studio`, PR #11.
**This report distinguishes CI evidence from manual acceptance; passing CI does not prove every music codec or third-party service works on user hardware.**

## Tested and verified

| Domain | Result | Evidence |
|---|---|---|
| Windows 3.10/3.13 + Linux 3.10/3.13 Python regression matrix | PASS | [Run 39778915156](https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/runs/39778915156), [head documentation-only run 39779108014](https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/runs/39779108014) |
| Full Windows regression | PASS — 380 tests (plus separately run extra GUI and command probes) | [Package run 39778900532](https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/runs/39778900532) |
| Local SDL playback via actual pygame mixer | PASS — generated WAV: play, pause, resume, stop, original audio SHA256 unchanged | Same Windows package run, QA_V260_PLAYER_SMOKE.py |
| Tk GUI, selected lyric rows, time shift and undo, EN↔EL, classic Sync Lab, cancel/confirm save | PASS — disposable audio/LRC plus editor test suites | TEST_V260_GUI.py and TEST_V260_STUDIO.py in full regression |
| Editor safety | PASS — existing audio/ID3 and original .lrc preserved, numbered unverified candidates exclusively created, malformed timestamps blocked, same-stem ambiguity fails closed on export | TEST_V260_STUDIO.py and TEST_V260_GUI.py |
| Existing search STOP behavior | PASS — repeated Windows nested process-tree stress and frozen worker acknowledged STOP exit 130, no audio changes | Package run 39778900532 |
| Frozen GUI startup, bilingual package & pygame bundling | PASS — EXE remained running for startup smoke; inspect PyInstaller module archive | Package run 39778900532 |
| English / Greek PDF generation | PASS build and textual validations | BUILD_V260_MANUALS.py via package run |
| Source and standalone ZIP / SHA256 | PASS — 14 standalone entries, 179 source entries, two archives, two PDF documents, checksum manifest; all package checks passed | BUILD_V260_RELEASE.py via package run |
| Existing v2.5 workflows | v2.5 publisher no longer auto-runs on new main merges | GitHub workflow difference in PR |

## Fixed defects found during v2.6 QA

1. Audio pause/resume monotonic clock initially restarted instead of resuming saved position — fixed; fake-player regression now passes.
2. Unsupported codec was incorrectly masked by shared-stem ambiguity — fixed: codec validation is reported first for embedded playback; candidate write safety remains strict.
3. Invalid fake audio MP3 crashed Mutagen duration extraction on Windows — fixed by cautious optional duration fallback to zero.
4. Initial ZIP assembler required the QA-only WAV smoke file even though QA_* files are deliberately excluded from source distribution — package check now passed.
5. Seek slider progress repaint interfered with mouse dragging — protected while dragging.

## What is NOT yet verified

- Hands-on playback on the owner's Windows PC with real MP3/FLAC/OGG/WAV collection, audio-output devices, seek correctness and user DPI settings.
- Exact word-accurate synchronization; the playback position is a GUI-estimated clock, and all manual/estimated lyrics are labeled UNVERIFIED.
- Third-party online provider availability on the day of use; network providers are not contacted during offline CI.
- Full visual inspection of every PDF page at production size (PDF text/build validation is automated).
- SmartScreen trust/signing: EXEs are unsigned pending external SignPath Foundation approval.

## Release acceptance exercise for a real PC

Copy 20 tracks into a throwaway folder, keep a byte-for-byte backup, test classic and new Studio with MP3 and FLAC, load one original LRC read-only, correct two lines, use Pause/Resume/Seek/Undo/Redo, save a new numbered .candidate.lrc, verify SHA256 of audio and pre-existing original LRC, switch to Greek and back, test STOP and candidate review. Check 100% / 125% / 150% Windows display scaling and compare PDF Greek rendering manually.

## Version direction

2.7: dashboard-to-Studio entry, A–B loops, timing warnings, bounded-memory waveform, seeking/audio-device polish, local draft recovery and configurable shortcuts. 3.0: optional offline advanced aligner, Enhanced LRC word timing, richer format import/export, library index and provider adapter architecture. See [ROADMAP_V2_7_V3_0.md](ROADMAP_V2_7_V3_0.md).
