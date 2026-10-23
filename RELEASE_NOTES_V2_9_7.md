# v2.9.7 — Provider Intelligence: safe benchmark + individual source exclusions

This is the **two-feature update** requested after v2.9.6, not v3.0. Old v2.9.6 release files remain available.

## Test My Providers (new)
Go to **Provider health** and click **Test My Providers**. Choose a small, deterministic sample of **5 / 10 / 20** metadata-valid songs from the selected library. The application asks for explicit permission because this test makes REAL ONLINE lyrics API requests, even when the selected normal search action is offline-only.

The isolated benchmark worker probes each currently enabled provider independently for every sampled song, instead of stopping after the first result. Each provider gets: attempts, resolved verified matches, unique verified matches contributed in tier order, manual review candidates, true no-match responses, timeouts, errors, skipped/unavailable responses and mean response duration. A stable deterministic shuffle samples across the library (rather than just its first alphabetically sorted songs). Use the SAME test size for Tier 1 and Tier 2 to compare fairly.

**Privacy / safety:** no original audio, ID3 tags, .lrc, .candidate.lrc or search checkpoints are created, edited or installed by the benchmark. It reads song metadata in memory only and saves a separate aggregate-only CSV under your own user application-data folder: AppData/LRCBulkFinder/benchmarks. The CSV does not contain song names or filenames. Existing server-required rate limits / cooldown state can still be updated to prevent accidental rate-limit bypass on subsequent runs. Press **Stop benchmark** to terminate its process independently of a normal lyrics search.

A verified match *count* means the provider returned a match meeting the existing strict checks, **not** that the benchmark saved any lyrics. Unique counts attribute each sampled song to its first verifying source in tier priority order; they are comparisons, not evidence of global provider quality. A provider that returned no matches for this sample is not automatically broken. Actual upstream availability and latency must be confirmed on your real network; CI uses no HTTP traffic.

## Individual provider exclusions (new)
In **Saved searches > Individual provider exclusions**, there is one checkbox for each source in the chosen provider pack. By default all selected sources are checked. Uncheck any source you prefer to skip, then save your search profile. **No requests go to excluded providers** during that profile's normal online stage or benchmark. At least one source must remain enabled.

The built-in Tier 1–6 lists remain **unchanged and cumulative**. Exclusions apply only AFTER choosing and ordering sources, and are saved per profile as a validated list. Legacy FAST/FULL profiles load exactly as before, with no exclusions. CUSTOM ordering still describes the complete underlying tier so re-enabling a provider does not destroy your saved ordering. Offline-only mode still makes no online source requests.

## Status and cautions
Existing STOP, resume checkpoints, strict metadata/version/duration matching, provider cooldowns, G2G optional AI setup, and 15 saved presets are preserved. Benchmark attempts can be slow or rate limited; experiment with five songs before using the larger samples. The one-click benchmark consent is required for each run. Automated tests verify no lyric-writing functions are invoked, profile compatibility, sample privacy, CSV integrity and GUI controls. Real provider effectiveness requires a user acceptance run.
