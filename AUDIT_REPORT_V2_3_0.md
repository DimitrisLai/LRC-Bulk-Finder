# LRC Bulk Finder v2.3.0 — Release-readiness audit

**Date:** 2026-10-19  
**Status:** PASS — no blocking failures in the tested scope  
**Audit run:** https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/runs/39309114890  
**Audit branch:** `audit/v2.3.0-release-readiness`  
**Published release:** https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/tag/v2.3.0  
**Source release tag commit:** `9b0287bb964108531a6fc216d6d423e652e2d909`

## Tested published assets

All checks downloaded real v2.3.0 GitHub release assets (not local development artifacts) and verified complete SHA-256 hashes.

| Published download | Expected/verified SHA-256 |
|---|---|
| Complete Python/CMD ZIP | `e663a3918ca6e1309cb32db59a0d499fef3863846060cc6b92db1faf55b674c1` |
| Complete English PDF manual | `62aa3cc0b94b4532921e7008cfabe54f378bb891fc03b532e3e4249203e69eec` |
| Standalone Windows GUI+worker ZIP | `bf927e6534c719e8d2a00dc63194c848878781c9640fcdaaba8f0a964b7c4694` |

The ZIP packages passed CRC/integrity and uniqueness checks. The complete Python ZIP contains all ten Windows `.cmd/.bat` launchers, code, SQLite word lexicon, CSV dictionaries and safety components. The 27-page English PDF passed A4 size, searchable text, all-page nonempty text and essential-section tests. This was not a full manual visual/layout review of all pages.

## Platform matrix

| Environment | Original tests | Independent integration tests | Result |
|---|---:|---:|---|
| Windows, Python 3.10 | 198 pass; 1 skipped | 14 pass | PASS |
| Windows, Python 3.13 | 198 pass; 1 skipped | 14 pass | PASS |
| Linux, Python 3.10 | 198 pass; 1 skipped | 14 pass | PASS |
| Linux, Python 3.13 | 198 pass; 1 skipped | 14 pass | PASS |

Additionally, **7 independent tests passed against the published standalone Windows executables**:

1. Frozen worker starts and responds to `--help`.
2. Frozen worker accepts an offline-only saved profile with a valid small SQLite database.
3. Frozen worker accepts an Option 5 saved profile.
4. A missing audio folder is explicitly rejected.
5. The native Windows GUI process opens without an immediate crash.
6. Actual Windows Tk widgets save and reload a profile, browse candidate sidecars and preview lyrics.
7. A **real, parseable MPEG-Layer-III MP3** with actual ID3 title/artist tags was read by the frozen worker, matched against real SQLite, produced a synced `.lrc`, and preserved the full original MP3 bytes on first and repeat run.

## Functional audit areas

- Offline-only action does not call web providers; independent SQLite fixture used.
- Offline-first Option 5 does offline processing for all eligible files **before** online fallbacks.
- Third stage reaches only genuinely timed-out sources for matching songs.
- Strict 3-second duration gap, artist/title identity and remix/version checks.
- Candidates remain explicitly reviewable and only primary candidates may be manually promoted.
- Explicit consent and `[00:00.00] candidate` marker; never overwrite verified `.lrc`.
- Profile JSON persistence is atomic, corrupt files fail closed, unknown prompts are rejected.
- MusicBrainz cached results are isolated by song duration and Greek mode.
- Provider success statistics count verified saves instead of review-only suggestions.
- ETA is scoped to the current round, with resumed songs excluded from time samples.
- Truncated JSONL checkpoint recovery, track-change invalidation and skip-on-resume.
- Original MP3/ID3 bytes unchanged for safety fixtures.

## 3,353-song stress simulation

**Test:** `AUDIT_V230_STRESS.py` against the real published Python package, with fake providers and 3,353 generated file entries; no live HTTP.

- Offline-first stage processed: **3,353**
- Online fallback songs: **2,683**
- Genuine provider-specific timeout retries: **23**
- Per-song checkpoint file: **4,658,746 bytes**
- First pass: **4.5 seconds** in the hosted Linux runner
- Restart with identical files/settings: **0.9 seconds**
- Repeated provider calls after resume: **0**
- No duplicate checkpoint records on replay
- Representative MP3 bytes unchanged
- Candidate files and review summary preserved

These timings are **not estimates of real lyrics-provider performance**; mocked HTTP calls do not reproduce network latency, throttling or remote provider outages.

## Limitations / before the next major version

- No live full-library online-provider benchmark was run; rate limits, server outages, false negatives and coverage remain real-world unknowns.
- The user's separate **large downloaded LRCLIB SQLite database** was not accessible; synthetic SQLite fixtures validated schema and matching only.
- The optional heavy **local G2G transformer model** is not bundled in the standalone EXE and was not used for this audit.
- GUI startup and selected widget behavior were exercised on GitHub Windows runners, not on every consumer Windows/antivirus configuration.
- EXEs are community-built and **not code-signed**. Antivirus/SmartScreen behaviors are not verified.
- The PDF was checked structurally and textually; no exhaustive page-by-page visual review was conducted.
- No multi-day unattended live workload or power-loss-on-write destructive test was conducted.

## Recommendation

**GO for planning the next major update**: no blocking errors identified in the tested scope. Keep v2.3.0 as a stable Public Beta backup while developing the next major release separately. Do not treat the tests as evidence that any third-party provider will always deliver correct synced lyrics.

All additional testing and this report are confined to the **audit branch**. The official v2.3.0 release and main-branch application source were **not changed** by this audit.
