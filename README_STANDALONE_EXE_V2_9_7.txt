LRC Bulk Finder v2.9.7 — Provider Intelligence

1. Extract the entire standalone Windows ZIP into a new folder. Preserve v2.9.6 as backup.
2. To selectively skip sources: Saved searches > select Tier 1-6 (or Legacy) > Individual provider exclusions. Untick any troublesome sources, keeping at least one enabled. Save as a new profile if desired.
3. This does NOT modify the tier definitions, song limit, Greek mode, offline behavior, provider order or music files. Existing profiles default to no exclusions.
4. To compare provider performance: select your music folder, source tier and exclusions, open Provider health, select a sample of 5, 10 or 20 songs and press Test My Providers.
5. Confirm that the test makes LIVE API requests (even if your usual search is offline only). Small sample first. No MP3, tags, existing LRC or candidates are written; only provider aggregate CSV under AppData/LRCBulkFinder/benchmarks. Server cooldown metadata can be updated if services rate-limit requests.
6. Read the benchmark grid: Tested, Verified, Unique, Review, Timeout, Errors and average response seconds. All sources are checked independently, and the same seeded sample is used for fair comparisons.
7. If it runs too long, click Stop benchmark. The Control Center remains open. Do not use benchmarking to bypass HTTP 429 Retry-After.
8. Benchmark counts are NOT installation commands. Provider results are not enough to declare a source permanently dead.
9. Both EXEs are needed together. Greek G2G AI setup stays optional and separate.
