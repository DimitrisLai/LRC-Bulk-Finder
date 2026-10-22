# LRC Bulk Finder v2.8.0 — QA audit

Development branch: \`feature/v2.8.0-karaoke-edition\`.

## Required automated acceptance
- Four Python test runners: Windows 3.10, Windows 3.13, Ubuntu 3.10, Ubuntu 3.13.
- Full preexisting offline regression suite, plus TEST_V280_KARAOKE.py core adversarial tests and TEST_V280_GUI.py real Tk workflow tests.
- 10,000-track inventory benchmark (not claimed instant).
- Actual synthetic WAV player smoke test preserving its original SHA256.
- Windows PyInstaller GUI/worker smoke and native STOP process stress.
- Both freshly versioned English/Greek manuals generated; 2 ZIPs, 2 PDFs, 1 SHA256 manifest, all integrity verified after download.

## Safety invariants
1. Audio/ID3/primary LRC/existing candidates must remain unmodified. No destructive media edits.
2. Pairing must refuse ambiguous same-name lyrics, ignore candidate .lrc in auto-match, and never follow symlinks.
3. Playlist session writes only to a bounded atomic JSON file under APPDATA.
4. Audiences see clean lyrics while operator workspace controls settings; no automatic playback on program startup.
5. Positive calibration delays previewed lines. Applying offset requires confirmation, only mutates in memory and remains undoable; Save creates a new numbered UNVERIFIED candidate.
6. Drop/monitor/photo/native-VLC features have safe and usable fallbacks.
7. Preserve the owner-approved 266 Greek translations and eight main tabs.

## Manual Windows acceptance still needed
A live human must validate actual multi-monitor fullscreen/projector DPI at 100–150%, dragging Explorer files into frozen PyInstaller GUI, media seek and loop accuracy on representative MP3/WAV/FLAC/OGG, a real instrumentals playlist, background-image rendering, Greek typography, timed LRC compatibility on a car radio and a native VLC installation. These behaviors cannot be fully established by headless or virtualized CI.
