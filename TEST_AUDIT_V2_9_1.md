# v2.9.1 — Windows startup regression and stability audit

## Confirmed defect and root cause
- v2.9.0 `ControlCenter.__init__` displayed the correct `v2.9.0` but `_refresh_language`, which runs unconditionally during initialization, reset the title to a hard-coded `v2.7.0`. The GUI was not necessarily an older executable. The legacy update-checker version constant in `v245_features.py` had also remained v2.7.0.
- The separate Worker EXE is designed to launch with `--profile`. A direct double-click without it produces argparse error code 2. That isn't a search crash or any issue with the user's song files.
- The previous PyInstaller release smoke checked the GUI process remained running, not its visible title.

## Targeted code changes
- `APP_VERSION` imported from `v245_features.VERSION` and displayed at startup and on every English/Greek refresh; matched to `LRC_Bulk_Finder.VERSION` through regression tests.
- Worker no-profile error retains nonzero exit and explicitly directs to the GUI.
- Added a simple optional one-click Windows GUI launcher with actionable missing-file messages.
- Frozen Windows GUI title checked with Windows EnumWindows, across the PyInstaller onefile bootstrap-child process boundary.

## Required release gates
- Entire historical regression suite, Smart Library 10k stress test, Windows/Linux Python 3.10/3.13; native Windows GUI tests, 27+ extra adversarial tests, WAV read-only playback, STOP and frozen EXE smoke.
- Correct real frozen GUI title; direct worker error/help; safe two-EXE assembly; full refreshed English/Greek PDF manuals.
- Official five assets downloaded again and SHA-256 checked after publishing.

## User acceptance
After extracting the v2.9.1 standalone ZIP, open the new launcher and also test direct `LRC_Control_Center.exe`. Both should open the graphical application with v2.9.1 title, after switching English/Greek too. The Worker EXE is never a manual GUI entrypoint. Then continue with `TEST_AUDIT_V2_9_0.md` for the complete day-long music-library acceptance trial. Do not upload copyrighted source audio or unredacted personal paths.

## Official final release verification — 22 October 2026

- Source PR [#15](https://github.com/DimitrisLai/LRC-Bulk-Finder/pull/15) merged, fixing the proven GUI title bug and the mistaken manual Worker launch diagnostic.
- Final [Windows + Ubuntu Python 3.10/3.13 test matrix](https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/runs/39823574637): **all four cells SUCCESS**.
- Official [Windows dual-EXE packaging and SHA256-verified publication](https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/runs/39823574523): **SUCCESS**; 462 core tests plus 27 additional native Tk GUI tests; real synthetic WAV playback and STOP tests; actual frozen GUI visible title **v2.9.1**; explicit Worker missing-profile guidance; 15 standalone assets in the ZIP; freshly rebuilt English and Greek manuals.
- [Release v2.9.1](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/tag/v2.9.1) contains five public assets. The publishing workflow downloaded each asset and printed **PASS: all five official release assets match the published SHA256 manifest.**
- Limits: Windows CI proves the frozen GUI starts, stays open, and displays the correct title; it does NOT verify that the user’s specific Windows PC can run it, soundcard playback, true drag/drop from Explorer, or all optional VLC codecs. Physical full-day acceptance testing on the intended machine is still required.
