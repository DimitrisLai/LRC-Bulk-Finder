# Changelog

## v2.9.2 — Responsive preflight and actual MP3 compatibility

- Apply 20-song limit during ID3 metadata preflight instead of after inspecting every candidate in a large library.
- Show live discovery/indexing/metadata preparation progress and leave search-result counters honest; improve STOP responsiveness.
- Safely handle unknown-artist placeholders for Greeklish MP3s whose title tags show Song - Artist filenames, while retaining existing Artist - Song fallbacks.
- Privately test three genuine MP3s (metadata, short audio decode, unchanged SHA-256). Do NOT ship the user's audio in GitHub.
- Add synthetic 3,200-file tests, native Tk progress regressions, optional local real-MP3 QA tool, updated EN/EL manuals, and full Windows packaging gates.



## v2.9.1 — Windows Startup and Version Display

- Fixed old v2.7.0 title appearing after the v2.9.0 app completed interface language initialization.
- Corrected stale update-checker version so GUI and engine report one version source.
- Added a first-class one-click Windows GUI launcher; direct worker launch now explains the appropriate app and retains proper CLI errors.
- Added real frozen PyInstaller GUI title and missing-profile worker smoke tests. Retains all Smart Library, Karaoke Edition, STOP and non-destructive data protections.



## v2.9.0 — Smart Library and Stability

- Transactional incremental SQLite metadata indexing, Unicode/Greek filename search, conservative LRC QC flags, optional deep duration checks and a cancel-safe non-destructive review queue.
- 200-row pages, filters, persistent Reviewed/Bookmarked records, recent scan history, direct Lyrics Studio navigation and UTF-8 BOM formula-escaped CSV exports.
- Correctly recreate the normal embedded player when switching tracks after optional native VLC speed control.
- Preserve eight main tabs, five nested Sync Lab tabs, 266 approved Greek translations, v2.8 karaoke tools and the legacy provider, STOP, no-overwrite and Undo invariants.
- Final pre-v3.0 full-day user acceptance checklist, new Greek/English PDFs and Windows/Linux release gates.



## v2.8.0 — Karaoke Edition

- New playlist-focused, performer-friendly Karaoke Edition workspace while preserving eight Control Center tabs.
- Clean separate audience/projector screen, optional second-monitor targeting, themes, font sizes, next-line visibility and local background photo.
- Guarded instrumental suffix LRC pairing, manual pairing, playlist reorder, track switching, last song and safe private settings persistence.
- Optional native file drag/drop with chooser fallback, playback countdown, persisted A–B loops, keyboard track navigation.
- Display-only lyric timing calibration ±30s; explicitly confirmed in-memory apply, ordinary Undo and separately confirmed new candidate export only.
- Read-only candidate export preview, redacted support diagnostics, Greek/English manual update and Windows/4-platform QA gates.



## v2.7.0 — Karaoke & Precision Lab

- Fullscreen instrumental karaoke using local timed LRC, with active/next lyric preview and no vocal removal.
- Read-only bounded waveform, zoom/navigation, timestamp warnings and A–B looping.
- Optional speed adjustment through installed VLC, private restart-recovery drafts, configurable lyric-table shortcuts.
- Direct dashboard/candidate-to-Studio navigation, configurable nudge steps and never-overwrite 2/3-decimal/BOM LRC export.
- Preserves v2.6 Studio, v2.5 Library Manager, protected audio and existing LRCs, EN/EL interface and older releases.


## v2.6.0 — Lyrics Studio (development; not released until Windows/CI QA)

- Integrated offline pygame-backed music playback in the new inner Lyrics Studio workspace within Sync Lab.
- Read-only LRC import (UTF-8 or legacy CP1253), active-line preview, timestamp nudges, precise timestamp entry and Stamp at playback.
- In-memory Undo/Redo and safe numbered UNVERIFIED candidate export; never overwrites music, ID3, existing LRC or candidates.
- Classic Sync Lab, v2.5 Library Manager, bilingual interface, existing search engine and STOP remain available.
- Dedicated Windows/Linux regression cases, real SDL WAV player smoke, and versioned EN/EL manual/build automation.
- Limitations: codec seek position is approximate, MP4/M4A/OPUS require external player; no waveform or word-level alignment.


## v2.5.0 — Library Manager: filtered retries, rejection details and creation-journal undo
- Extend the bilingual searchable dashboard with user-selectable exact online retry for missing/review tracks (maximum 2500 per explicit run). Validate size/mtime and fail closed if a selected track changes or gains an LRC.
- Bypass prior cached NO_MATCH only for the user-requested retry; preserve distinct resume checkpoint files and provider cooldown behavior.
- Explain unmatched/review outcomes with actual historical engine CSV provider and candidate rejection details, clearly labelled potentially stale.
- Journal exclusively created verified and candidate sidecars per GUI session under user APPDATA. Require exact path, size, mtime and SHA256 before removal. Confirm first; never delete audio, existing/edited LRC, manually repaired candidates, reports or settings.
- Additive Greek UI labels, original approved translations intact, former Quick Search and advanced workflows preserved.
- Adversarial offline, real Windows GUI, Linux Xvfb, and frozen EXE process-tree/STOP tests.


## v2.4.5 — Quick Search, library overview, synchronization timing offset repair
- Beginner Quick Search tab with 20-song test or whole-library scanning, advanced settings preserved.
- Read-only Results dashboard with status/filename filtering and exclusive-create CSV export.
- Uniform timing-offset preview for existing LRC and non-overwriting, clearly UNVERIFIED candidate LRC output.
- User-initiated latest GitHub release check, with no automatic download or background telemetry.
- One-click privacy-conscious diagnostics omitting personal paths, filenames, song metadata, lyrics and credentials.
- Additive English/Greek labels and preserved 266 previously approved translation phrases.
- New offline core and actual GUI tests for these workflows, along with existing strict file safeguards.
- Refreshed Windows standalone/Python archives and English/Greek PDF guides.


This changelog summarizes documented beta milestones; it is not a verbatim Git commit history.

## v2.4.4 — Approved bilingual Windows UI and safer STOP verification
- English / Ελληνικά live language selection for all five Control Center tabs, with remembered preference separate from saved search profiles.
- 266 reviewed Greek UI entries (265 unique English source strings): controls, presets, tooltips, messages; internal engine, original audio and lyrics stay unchanged.
- Native Windows process snapshot plus conservative fallback improves STOP worker/child verification, preserving warnings if independent checks fail.
- Complete English manual updated for v2.4.4 and new Greek user guide.
- Windows/Linux Python 3.10 and 3.13 validation: 261 regression tests and 27 adversarial GUI tests per environment, plus Windows command launcher and repeated process-tree STOP tests.
- PyInstaller portable standalone Windows application built and checked for correct bundled language support.

## v2.4.3 — Provider health, verified STOP, Skipped counting and one-click resume
- **Provider Health Dashboard** distinguishes working, temporarily unavailable, timed-out and blocked providers. Records a verified success only after an approved `.lrc` sidecar is saved, not merely after receiving HTTP 200.
- **STOP verification** attempts to terminate worker descendants and warns if full process-tree termination cannot be verified. Completed stage/song checkpoints are retained; an unfinished song or unwritten report may be lost on force stop.
- **Separate Skipped counter** distinguishes missing/unusable metadata from genuine no-match searches. Four stage counters reset between rounds; two cumulative totals track distinct verified and candidate-bearing songs.
- **Resume previous search** restores a saved profile and uses safe resumable checkpoints; no duplicate search against the same folder should run simultaneously.
- **Provider contribution CSV** records providers that actually deliver new verified `.lrc` files, not candidates or repeated findings.
- **Approved Greek aliases** can be saved locally for later matching without rewriting audio tags or trusting unreviewed AI output.
- **SimpMusic experimental route** is an explicit opt-in and remains disabled by default; results without verifiable recording metadata are candidates only. LetrasMus, YouTube Music and separate Apple Music experiments are research only, not silently added to existing FAST/FULL routes.
- Complete standalone Windows GUI/worker ZIP, complete Python/CMD ZIP and a **29-page beginner-first English PDF user manual** published together.
- **Validation:** full regression suite passed on Windows and Linux with Python 3.10 and 3.13; Windows frozen GUI/worker startup and STOP smoke tests passed; release assets were downloaded again and SHA-256 compared with tested packages.
- Version remains labeled **Public Beta** because provider availability and correctness on real music libraries cannot be guaranteed.

## v2.4.2 — Immediate worker-tree STOP and distinct stage/all-stage counters
- A single confirmation immediately kills the entire search worker tree without terminating or freezing the Control Center.
- Windows `taskkill /T /F` handles PyInstaller worker children; Linux searches use an isolated process session. Completed-song checkpoints remain; current in-flight work may be retried.
- Three current-stage counters and two persistent run totals now appear in separate GUI groups.
- Candidate counts measure unique songs with actual saved candidate sidecars, rather than unsaved diagnostic review notes.
- Full Windows/Linux 3.10/3.13 regression suite and standalone worker smoke tests.

## v2.4.1 — Reliable STOP and stage-by-stage live counters
- Fixed Stop in both Python and frozen Windows GUI via console-independent, per-run cooperative marker; provider sleeps respond promptly.
- Completed stage checkpoints and reports are retained when stopping gracefully; an explicit last-resort Force STOP is available after eight seconds.
- Five counters: verified LRC, candidate and not-found THIS stage, plus unique verified LRC and candidate totals across ALL stages of the current run. Stage counts reset after finishing.
- Resume respects completed checkpoints; errors/timeouts never inflate NOT_FOUND counters.
- Expanded Windows/Linux automated regressions, live Tkinter stop-button checks, and new independent Windows standalone build verification.
- All v2.4 features and original source audio/ID3 protection remain unchanged.

## v2.4.0 — Built-in Greek/Night presets, incremental library, multiple formats & experimental Sync Lab
- Six editable prebuilt templates; per-control help tooltips and native LRCLIB/G2G setup buttons.
- Read-only SQLite audio index for new/changed files, reused metadata for unchanged library members; optional GUI toggle.
- Additional FLAC/M4A/MP4/OGG/OPUS/WAV audio support alongside MP3. Same-stem duplicates conservatively skipped.
- Experimental untimed lyrics helper with rough initial timestamps and manual tap timing, user-reviewed/saved only as unverified .candidate.lrc.
- Full Windows/Linux regression matrix, 29-page manual and optional separate Windows standalone GUI EXE release.
- Original strict recording verification, offline-first 3-stage search and MP3/ID3 protections remain in force. No fingerprinting.

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
