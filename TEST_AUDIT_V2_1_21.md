# v2.1.21 — Regression Test Audit

The earlier v2.1.20 CI selected **10 modules** out of the **21** then present. v2.1.21 adds `TEST_STABILITY_V2_1_21.py`, bringing the total to **22**.

The new CI command discovers **all 22** `TEST_*.py` modules on Windows and Linux (Python 3.10 and Python 3.13), including the eleven previously omitted modules:

- `TEST_AUTO_INSTALL_V2_1_12.py` — archive download/resume and extraction.
- `TEST_AUTO_INSTALL_V2_1_13.py` — official snapshot discovery and safe URL rules.
- `TEST_BATCH_COVERAGE_V2_1_10.py` — LRCLIB 503 coverage and queue.
- `TEST_CLEANUP_V2_1_14.py` — guarded database cleanup and confirmations.
- `TEST_FIRST_ATTEMPT_V2_1_10.py` — first-attempt coverage/recovery behavior.
- `TEST_LRCLIB_OFFLINE_V2_1_11.py` — database and offline/network separation.
- `TEST_LRCLIB_PRIORITY_V2_1_7.py` — provider priority and LRCLIB recovery.
- `TEST_LRCLIB_STABLE_V2_1_9.py` — conservative fallback and catch-up.
- `TEST_PROVIDER_DIAGNOSTICS_V2_1_9.py` — HTTP/timeout diagnostics.
- `TEST_RELEASE_V2_1_4.py` — original files/retries/provider safety.
- `TEST_RELEASE_V2_1_5.py` — MusicBrainz metadata and prompts.

The four regression areas introduced in v2.1.21 have new offline-only fixtures: third approved Greek variant with a tiny SQLite fixture, unchanged-file checkpoint replay, invalidation on file change/truncated JSONL, and candidate review surviving timeout-only retries.

Historical fixtures were corrected to close temporary Windows SQLite connections, use dynamic versioned report names, and reset global recovery options between tests.

Tests use mocked network access and scratch files; they cannot assert live online provider availability or verify an individual's full downloaded LRCLIB snapshot.
