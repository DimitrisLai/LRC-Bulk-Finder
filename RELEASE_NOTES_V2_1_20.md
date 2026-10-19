# LRC Bulk Finder v2.1.20 — Offline First, then Online Misses

**Public beta — Created by Dimitris L.**

## New Option 5: Three-stage search

1. **Round 1, offline first:** use the user's existing **large LRCLIB SQLite snapshot** for **all selected eligible MP3s**. No online providers, no MusicBrainz and no HTTP. Verified lyrics are saved, unverified alternatives remain sidecar candidates.
2. **Round 2, online misses only:** remaining songs without verified `.lrc` files search the chosen FAST/FULL online providers. Their local SQLite lookup is not repeated. Online LRCLIB is independent and can be temporarily unavailable without affecting the local scan.
3. **Round 3, only network timeouts:** retry once only the exact provider/song combinations that genuinely timed out in Round 2. Do **not** repeat NO_MATCH, HTTP 401, 429, 503 or all providers.

Option 5 requires a valid downloaded LRCLIB database and will ask for its path if necessary. It does not quietly fall back to online-only. Existing **Option 4** remains the quickest purely offline-only solution, while Options 1–3 retain their behavior.

## Other safeguards

- Preserve **all MP3/ID3 metadata and existing `.lrc` files**.
- Preserve the exact candidate marker `[00:00.00] candidate` and rotation.
- Preserve artist-name fixes from v2.1.19 and the large CSV/SQLite word dictionaries.
- Never upload personal music filenames or private folder paths.
- New offline-first regression tests ensure all local lookups happen before any online lookups and only timed-out provider/song pairs get stage-three retries.
- Updated full PDF manual and Windows release ZIP, with separate release asset checks.

## Launch instructions

See `HOW_TO_START_V2_1_20.txt` for **every menu selection** in the order it appears. For a full Greek collection, choose **5**, your folder, Greek Y, installed AI Y if available, MusicBrainz Y, FULL, recovery waiting N, recursive Y, history N for a fresh test, songs A, exact LRCLIB fallback Y, automatic search Y. To test the local database without the internet, choose **4** instead.

**Important:** This changes the search order of a new run; it cannot change an already running v2.1.19 session. A safe restart leaves existing verified `.lrc` files untouched.
