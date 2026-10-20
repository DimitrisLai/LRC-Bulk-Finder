# LRC Bulk Finder v2.4.3 — Public Beta

## Start here

Download either the **Complete Windows ZIP** (Python/CMD, supports external Greek AI) or the **Standalone Windows GUI ZIP** (both bundled EXEs; no Python installation for standard searches). Extract the complete archive before opening `OPEN_CONTROL_CENTER.cmd` or `LRC_Control_Center.exe`.

The separate **Complete English PDF User Manual** is a first-time, step-by-step walkthrough, not a version-change summary. It explains setup, existing/offline LRCLIB databases, first 20-song test, all settings, safe candidate review, STOP/resume, reports and troubleshooting.

## What this beta provides

- Provider health view distinguishing availability, timeouts, access blocks and actually installed verified LRCs. HTTP success alone does not count as an approved lyric.
- STOP attempts to terminate the worker tree and independently verifies observed descendants. The GUI warns if verification is incomplete.
- Separate **Skipped** (missing/invalid metadata) stage counter, in addition to LRC, candidate and not-found counts; two cumulative distinct-track totals remain.
- **Resume previous search** using saved search profile and durable stage checkpoints.
- Provider contribution CSV reports distinct verified installs; no inflated credit for candidate files.
- Reviewed Greek alias approval (local CSV) and additional candidate-only quality safeguards.
- An **opt-in experimental SimpMusic route**, OFF by default; results with unverifiable recording identity/duration are never silently approved.
- Research of additional sources, not automatically enabled. Every existing v2.4.2 core feature is preserved.

## Quality and limitations

Full Python regression suite: **240 tests** (including platform-specific skips), passing on Windows and Linux using Python 3.10 and 3.13. Standalone Windows worker/GUI build and smoke checks passed. This does not establish 100% availability/accuracy of live third-party services or substitute for testing an overnight scan on your own music collection.

Existing audio/tags and existing approved `.lrc` sidecars are not overwritten. The large external LRCLIB database and Greek AI model are not bundled. This remains an unsigned Public Beta; verify the GitHub origin and checksums, and do not globally disable Windows security protections.

License: MIT. Credit: Dimitris L.
