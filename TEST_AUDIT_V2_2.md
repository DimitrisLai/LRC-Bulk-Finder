# v2.2.0 — Performance & Safety Test Coverage

The v2.1.21 full 22-module test suite has been retained. The new
`TEST_SEARCH_PERFORMANCE_V2_2.py` module adds offline tests for:

- MusicBrainz cached success persists across simulated process restart.
- Duration and Greek/non-Greek mode prevent cross-recording cache poisoning.
- Completed clean MusicBrainz no-matches are cached, but provider errors are not.
- Expired cache results are discarded.
- Provider DEFAULT preserves original ordering.
- Provider CUSTOM rejects missing, duplicated and unknown source names.
- Verified-only provider stats exclude cached and unavailable providers.
- SMART uses actual verified saves and elapsed seconds, without dropping sources.
- Corrupted checkpoint tail is repaired before recording new completed work.
- Console CUSTOM selection retains the entire selected provider list.

Old tests were updated to answer the new provider ordering prompt in the
correct sequence; their original assertions for offline matching, provider
timeouts, rate limits, review candidates and untouched MP3s remain.

The Windows ZIP is tested for required CMD/BAT launchers, the complete
Python program, v2.2 helpers, Greek words, the small lexicon SQLite,
manual and attribution. The downloaded large LRCLIB snapshot is not
included or copied.

No tests send real HTTP requests to lyrics providers, so they do not
establish live provider availability or song coverage on the user's
entire music library.
