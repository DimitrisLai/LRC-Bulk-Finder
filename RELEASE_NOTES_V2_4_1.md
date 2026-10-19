# LRC Bulk Finder v2.4.1 — Reliable STOP and Stage Counters

Public Beta maintenance patch to v2.4.0. Existing search verification and original audio protections remain intact.

## Reliable STOP

Earlier GUI versions depended on Windows Ctrl+Break delivered to a subprocess. A windowed standalone GUI may not share its worker's console, so Ctrl+Break could have no effect. v2.4.1 uses a unique per-run stop marker passed to the worker via LRC_STOP_FILE.

Click Stop search safely, then confirm. The search checks requests during inventory and Greek preflight, between songs and during provider-recovery waits. A current bounded network request may need to return or time out before the worker saves its final reports. Successfully completed per-song checkpoints are preserved.

If the worker is still active after eight seconds, the GUI offers Force STOP (last resort), with a second confirmation. Force-stopping can lose the current in-flight result and final report, but previously saved checkpoint entries remain.

## Five live counters

| Current stage | Across ALL stages of the current run |
|---|---|
| LRC found (stage) | LRC found (ALL stages) |
| Candidates (stage) | Candidates (ALL stages) |
| Not found (stage) | |

The THREE stage counters start at 0, increase during the current round and return to 0 immediately after each round finishes. The TWO cumulative totals retain unique song counts across stages and stay visible after a stage ends. A previously reviewable candidate later saved as verified can count in both historical totals. Unavailable providers, timeouts and errors never count as confirmed NOT FOUND.

The totals measure newly processed eligible songs in the CURRENT run, not installed LRCs from an earlier run. Resumed song/stage checkpoints are not searched again and are counted once for that run.

## Existing capabilities unchanged

All six Greek/Night/AI/offline built-in presets, hover explanations, LRCLIB and local G2G setup, incremental SQLite library metadata, seven audio types (MP3, FLAC, M4A, MP4, OGG, OPUS, WAV), candidate review and experimental Sync Lab. No audio fingerprinting, original audio modification or automatic promotion of unverified candidates.

## Verification

Windows/Linux regression matrix Python 3.10/3.13, additional cooperative-stop, stage accounting, candidate, version, timeout and checkpoint tests, actual Windows Tk GUI button tests, and separately built/verified Windows standalone GUI and worker. Third-party online availability, SmartScreen reputation and the user's private full LRCLIB dump aren't guaranteed by simulated-provider tests.
