# Changelog

This changelog summarizes documented beta milestones; it is not a verbatim Git commit history.

## v2.3.0 — Saved profiles, live progress and safe candidate review
- NEW `OPEN_CONTROL_CENTER.cmd` and `LRC_Control_Center.py`: native Python/Tkinter GUI and log/progress/ETA dashboard. CLI START_HERE.cmd remains available.
- NEW `search_profiles.py` and `run_saved_profile.py`: validated, atomic local user profiles and known-answer-only launch of Options 1, 4 and 5.
- NEW `progress_eta.py`: clear per-round percentage, elapsed time and ETA based on actual uncached songs.
- NEW `review_candidates_gui.py`: browse candidate sidecars, preview without modifying them, open MP3 externally and explicitly confirm one MARKED unverified candidate promotion using existing safe routines.
- 17 new GUI/profile/progress/candidate regression tests plus full legacy matrix on Windows and Linux.
- Existing Greek offline search, provider statistics, MusicBrainz cache, JSONL resume safety and all MP3/ID3 protections remain unchanged.

## v2.2.0 — Persistent metadata, provider ordering, performance and stronger recovery
- New persistent duration- and Greek-mode-aware MusicBrainz artist/title spelling cache (30-day positive/7-day clean no-match TTL; never cache provider errors).
- New provider priority prompt: D=DEFAULT, S=SMART based on independently verified LRC saves per provider seconds (minimum 10 observations), C=CUSTOM exact permutation; FULL/FAST provider sets unchanged.
- New persistent `LRC_Provider_Performance_v2_2.jsonl` and aggregated `LRC_Provider_Performance_v2_2.csv`: completed outcomes, verified success rate, reviews, errors and seconds per verified save. Never count cached/skipped provider states as successful checks.
- Resumable v2.2 checkpoints fsync each completed song/stage, repair truncated JSONL tail, and use stable session IDs to deduplicate history on restart without losing genuinely new-run metrics.
- Retains offline-first Option 5, offline-only Option 4, strict recording verification, candidate LRC marking and original MP3/ID3 protections.
- Complete Windows package with all 9 launchers, and expanded Windows/Linux test matrix with v2.2 dedicated performance tests.

## v2.1.21 — Stability, full Greek offline variants, resumable checkpoints
- Offline LRCLIB uses up to six approved deduplicated search pairs rather than only two, including original song + approved Greek artist and approved Greek title + approved Greek artist.
- Track candidate review presence across all rounds; later timeout retries cannot turn retained `.candidate.lrc` files into incorrect NOT_FOUND statuses.
- New `search_checkpoint.py` stores song/stage results after each song; safe automatic resume when settings, dictionaries, local snapshot and song timestamps are unchanged; restored results populate provider reports and LRCLIB catch-up bookkeeping.
- All 22 regression modules selected in Windows/Linux Python 3.10/3.13 CI (previously ten); corrected historic test fixture cleanup and expectations.
- Updated complete Windows ZIP, 24-page manual, README and change notes. No MP3/ID3/approved LRC modifications.

## v2.1.20 — One-click offline-first, then online misses, then timeouts
- New Option 5 scans the full selected eligible folder with the existing large LRCLIB database before contacting any online music provider.
- Round 2 checks only unsaved songs against chosen FAST/FULL online providers, skipping redundant offline DB reads.
- Round 3 retries only a provider/song pair with an actual network timeout, once; no re-search of NO_MATCH, 401, 429 or 503 outcomes.
- Offline-only Option 4, the original Option 1, original MP3/ID3, matching strictness, and exact `[00:00.00] candidate` format are retained.
- Full ordered prompts and dedicated staged offline-first Windows/Linux regression tests added.

## v2.1.19 — Full artist/group identities, not letter-by-letter conversions
- Re-analysed a Greek music filename inventory (about 5,686 MP3 files). Added 113 standalone, public artist and group spelling aliases to `Greek_Artists.csv` without shipping music paths or the inventory.
- Approved artist names take priority; speculative AI artist transliteration is disabled as a search alternative.
- Original title + approved Greek artist is searched before combined alternatives, especially in LRCLIB's first two variants.
- Added sensible mixed English/Greeklish title handling such as `Sexy koritsia` → `Sexy κορίτσια`.
- Added song vocabulary for the supplied cases including `Kimata`, `Mesanychta Savvatou`, `Antidrasi`.
- Added artist-identity and recording-query regression tests on Windows and Linux.
- Preserved original MP3s, ID3 tags, old sidecars, review candidate marker, local SQLite and existing releases.

## v2.1.18 — Large public Greek word lexicon and read-only SQLite
- Added 950 separate Greeklish word spellings to the public `Greek_Words_Expanded.csv`, drawn from recurring spellings in a large Greek music example list (without sharing private song filenames or personal paths).
- Added reproducible SQLite database builder `BUILD_GREEK_LEXICON_DB.py`, combining public words and customizable `Greek_Words.csv` into an optional small read-only `Greek_Lexicon.sqlite3` included in the Windows ZIP.
- Added safeguards for database corruption, out-of-date CSV fingerprints, user overrides and cross-platform Windows SQLite close semantics.
- Preserved original title/artist and remix, Option 2 `[00:00.00] candidate` behavior, strict match checking, and audio/ID3 safety.
- Added dedicated offline database regression tests and Linux/Windows Python 3.10/3.13 coverage.

## v2.1.17 — Greeklish quality and dictionary-first search
- Corrected Greek search-plan priority to **manual full title alias → verified accented word dictionary → optional local AI suggestion**.
- Expanded the small curated word-level Greeklish lexicon and preserved punctuation, years and remix/version labels.
- Avoided phonetic Greek nonsense for common English titles and international/mixed artist credits such as `2002 GR`.
- Made dictionary corrections apply to matching tokens in previously cached AI suggestions, without trusting invented spellings.
- Original artist/title search variants remain first; MP3 files and existing lyrics are not changed.
- Added isolated Greek-title quality regression tests on Linux and Windows.

## v2.1.16 — Marked bulk candidate promotion
- Option 2 installs a timed primary candidate as playable `.lrc` with `[00:00.00] candidate` at the beginning, visibly UNVERIFIED.
- Following promotion, numbered alternate candidates shift down one position.
- Existing `.lrc`, MP3 audio and ID3 tags are not modified. Explicit confirmation, CSV reporting and offline operation remain.
- Added offline Windows/Linux regression tests for the marker, shifting, repeat promotion and 110-song batch.
## v2.1.15 — Offline-only folder search
- Added **4 — OFFLINE LRCLIB ONLY** to scan any music folder, no prior catch-up queue needed.
- Added `CONNECT_EXISTING_LRCLIB_DATABASE.cmd`: link previously extracted SQLite without copying or redownloading hundreds of GiB.
- Added standalone offline scan/result review CSV files.
- Preserved strict artist/title/version/duration matching and original MP3 protection.

## v2.1.14 — Safe cleanup
- Added cleanup choices for compressed archive only, extracted database only, both or cancel; typed confirmation required.
- Added post-install disk usage feedback.

## v2.1.13 — Database discovery fix
- Updated automatic dump discovery to use structured LRCLIB catalog with safe filename checks and fallback.

## v2.1.12 — Automatic setup
- Added optional LRCLIB database installer; snapshot downloaded separately.

## v2.1.11 — Offline SQLite lookup
- Added local LRCLIB lookup and online LRCLIB HTTP 503 safety stop.

## v2.1.10 — Provider coverage
- Added first-attempt provider coverage report and improved temporary recovery handling.

## v2.1.9 — LRCLIB reliability
- Added catch-up queue, optional exact lookup and improved LRCLIB request pacing.

## v2.1.8 — Candidate review
- Added `.candidate.lrc` files and explicit promotion workflow.

## v2.1.7 — LRCLIB priority
- Updated search order and LRCLIB service overload handling.

## v2.1.6 — Diagnostics
- Added visible provider errors, request statuses and skip reasons.

## v2.1.5 — Metadata
- Enabled optional MusicBrainz lookup for Greek and international libraries.

## v2.1.4 — Public beta
- Improved history, rate limit handling, review reporting and packaging.

## v2.1.2–v2.1.3
- Public packaging and stricter version/duration checks.

## v1.x–v2.1.1
- Original multi-provider synchronized lyric search, Greeklish support, timeout-only retries and optional local G2G AI.
