# LRC Bulk Finder v2.2.0 — Faster Searches & Better Recovery

Public beta. Created by Dimitris L.

## New: persistent MusicBrainz cache

Optional artist/title metadata lookup results now persist in `LRC_MusicBrainz_Cache_v2_2.jsonl` inside the chosen music folder. Cache keys include normalized artist/title, track duration and Greek mode. Successful matches expire after **30 days**, clean `NO_MATCH` results after **7 days**. Network errors are not stored. The suggestion only helps create search spellings; it is **never a substitute for independent, strict recording/lyrics verification**.

## New: configurable search priority

After FAST/FULL selection, choose **D** (unchanged default order), **S** (SMART, uses the verified-match and elapsed-time statistics collected by the program), or **C** (exact comma-separated order containing every chosen provider once). An invalid custom choice falls back to default and shows why. LRCLIB remains first in SMART. Reordering never silently disables a provider or relaxes safeguards.

## New: actual provider success statistics

`LRC_Provider_Performance_v2_2.jsonl` retains 90 days of local observations; `LRC_Provider_Performance_v2_2.csv` contains attempt counts, **verified** lyric saves, reviews, no-matches, errors, true success rate and elapsed time. Cached results and providers not contacted are deliberately excluded. SMART uses verified saves per elapsed second once at least 10 outcomes are recorded per provider. A completed stage restored from checkpoint does not count as a new attempt; a genuinely fresh scan has a new session ID.

## Improved interruption handling

`LRC_Run_Checkpoint_v2_2_0.jsonl` flushes and syncs each completed track/stage, repairs truncated tail fragments, and reuses prior completed coverage when restarting with otherwise equivalent provider selections. An intentionally fresh run starts a distinct statistics session after moving the checkpoint file. Existing .lrc and all original MP3/ID3 metadata are preserved.

## Preserved

- All **five** main menu actions. Option 5 is still **offline-first all songs → online misses → genuine timeout-only retries**; Option 4 remains offline-only with no web.
- Verified-only automatic saving, exact version/duration safeguards, approved Greek artist dictionary, and `[00:00.00] candidate` promotion.
- Rate-limit and access-denied handling, no repeat of completed `NO_MATCH` providers during timeout rounds.
- Complete Windows CMD/BAT launchers and large LRCLIB SQLite reconnect workflow.
- Full Windows/Linux Python 3.10/3.13 offline tests.

## Getting started

Extract the official **v2.2.0 complete Windows ZIP** into a NEW folder, reconnect the existing downloaded LRCLIB SQLite file when necessary, and double-click `START_HERE.cmd`. See `HOW_TO_START_V2_2.txt` for every prompt in exact order.

**Important:** The new journal does not import v2.1.21 checkpoints. Previously downloaded verified `.lrc` sidecars are skipped automatically. No automated test can guarantee the live availability of third-party providers.
