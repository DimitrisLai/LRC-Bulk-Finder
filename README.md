# 🎵 LRC Bulk Finder

**Synchronized lyrics for your entire MP3 collection — online or offline.**

**Windows · Python 3.10+ · Public Beta v2.4.0 · Created by Dimitris L.**  

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![MIT License](https://img.shields.io/badge/License-MIT-green)
[![Python tests](https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/workflows/tests.yml/badge.svg)](https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/workflows/tests.yml)

**Project source code: [MIT License](LICENSE)** · [Releases](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases) · [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

LRC Bulk Finder finds timestamped **`.lrc` lyrics files** for MP3 music libraries. It can work through multiple online lyrics sources or search an optional **local LRCLIB SQLite snapshot** — without internet requests during an offline-only scan. It supports international music, Greek and Greeklish titles, multi-folder collections, and reporting designed for large unattended runs.

Lyrics are saved alongside the MP3 with the same base filename, making them compatible with many portable music players and car stereos that support synchronized LRC text.

> **Public Beta:** External provider APIs can change, disappear, restrict requests or return incomplete metadata. Finding lyrics for every song is not guaranteed, particularly for rare remixes, instrumentals and extended versions.

## What's new in v2.4.0: ready-made profiles, incrementally scanned libraries and experimental timing assistance

Open `OPEN_CONTROL_CENTER.cmd` and select a **built-in preset** at the top: **Greek FULL Offline First**, **Greek Night Search** (wait for temporary provider recovery; can take hours), **Greek Quick Test 20**, **Greek OFFLINE ONLY**, **Greek Local AI FULL** (separately installed model) or **International FAST 20**. Click **Apply preset**; personalize toggles and save without overwriting existing profiles. Hover on each checkbox for a short explanation.

The new **Download / set up LRCLIB database** and **Download / set up Greek G2G AI** buttons launch the established consent-based scripts in the complete CMD distribution. Standalone EXE users can invoke the database downloader in a separate worker console; local G2G AI still requires its external Python environment.

The **incremental library** toggle caches read-only metadata in `LRC_Incremental_Library_v2_4.sqlite3` inside your music folder. New/changed audio or sidecar status is detected without changing MP3/ID3/LRC safety. Supported read-only audio types now include **MP3, FLAC, M4A, MP4, OGG, OPUS and WAV**. Same-stem cross-format clashes are skipped to prevent sidecar ambiguity.

In the **Sync Lab (experimental)**, paste/import your own plain lyrics; estimate rough timestamps based on track duration or manually tap the starts while listening externally. Saving requires confirmation and creates **only UNVERIFIED `[00:00.00] candidate` sidecars**. This is not automatic audio alignment or transcription. Acoustic fingerprinting is intentionally not included.

[Full v2.4 guide](HOW_TO_START_V2_4.txt) · [Release notes](RELEASE_NOTES_V2_4.md) · [Test audit](TEST_AUDIT_V2_4.md)

## What's new in v2.3.0: Windows Control Center and saved profiles

**New `OPEN_CONTROL_CENTER.cmd`** launches the standard-library Tkinter GUI; `START_HERE.cmd` still runs the original five-mode console. Three tabs: **Saved searches**, **Live progress**, and **Candidate review**.

- **Profiles:** save named folders and the complete Option 1/4/5 search settings locally under `%APPDATA%\LRCBulkFinder\profiles.json`. All saved answers are validated; unknown prompts fail closed, and provider CUSTOM lists cannot omit a route. No personal music files are uploaded.
- **Per-round ETA:** every completed song/stage prints a clear progress percentage, elapsed time, and **THIS ROUND** estimated remaining time after three uncached songs. Resume-replayed songs do not skew estimates. The GUI streams logs and shows a live progress bar.
- **Review candidates:** browse numbered `.candidate.lrc`, preview lyrics, open a matching MP3 in your external player, and explicitly confirm installing a single *primary* candidate as an LRC marked `[00:00.00] candidate`. The GUI never automatically declares uncertain lyrics verified, never overwrites existing LRCs or modifies MP3/ID3. Numbered alternatives retain the existing shift rules.
- **Optional standalone GUI EXE:** a separately built, verified EXE+worker package may be published for Windows. The complete Python/CMD ZIP remains supported, particularly for heavy optional local G2G AI models.

[Complete v2.3 user instructions](HOW_TO_START_V2_3.txt) · [Release notes](RELEASE_NOTES_V2_3.md) · [Test audit](TEST_AUDIT_V2_3.md)

## What's new in v2.2.0: Search performance

**Persistent MusicBrainz metadata cache** (30-day suggestions, 7-day successful no-matches): completed lookups survive restarts without using unverified artist/title spellings to auto-save lyrics. Failed HTTP responses are not cached.

**Configurable provider ordering:** After FAST/FULL, choose **D** for the original list, **S** for SMART (rank based on verified saves per elapsed second from prior runs) or **C** for an exact comma-separated permutation of the selected provider names. Custom order must include each selected source once; invalid choices fall back to DEFAULT. Changing the order does not omit providers or reduce matching strictness.

**Actual provider performance:** Local `LRC_Provider_Performance_v2_2.csv` and a 90-day local historical JSONL log count only **verified** automatic lyric saves as successes, separately tracking review candidates, no-matches, errors and elapsed seconds. Skipped/cached/unavailable providers are excluded. SMART keeps LRCLIB first and waits for at least 10 completed outcomes per provider before ranking it.

**Safer interruption recovery:** Flush and fsync completed song/stage checkpoints, repair a partially written final JSONL entry, and reuse unchanged work even when provider order changes within the same selection mode. Checkpoint identity prevents counting resumed stages twice in success-rate metrics.

All five modes and the existing offline-first sequence are retained. **See [every v2.2 setting in the correct order](HOW_TO_START_V2_2.txt).**

## What's new in v2.1.21: stability, accuracy, checkpoint resume

- **More complete Greek offline matching:** offline LRCLIB now tries up to six approved title/artist combinations, including the Greek-title + approved-Greek-artist pair that was previously excluded from local lookup. Exact recording/version/duration verification is unchanged.
- **Review candidates survive across all stages:** timeout retries and later NO_MATCH responses cannot misclassify already discovered review candidates as genuinely not found.
- **Resume large searches:** Option 1 and Option 5 append a per-song/stage record to `LRC_Run_Checkpoint_v2_1_21.jsonl` inside your chosen folder. A restarted scan with identical settings reuses completed unchanged work and reconstructs provider and review reports. Changed MP3 size/mtime, dictionaries, provider settings and local SQLite snapshot invalidate stale stage checkpoints. For a completely fresh run, first rename/move the checkpoint file. Do not run two simultaneous copies on the same folder.
- **Regression tests:** CI now discovers all 22 test modules on Windows/Linux Python 3.10/3.13, including legacy snapshot setup, cleanup, provider diagnostics and timeout behavior. See [test audit](TEST_AUDIT_V2_1_21.md) and the [new complete instructions](HOW_TO_START_V2_1_21.txt).

## What's new in v2.1.20: offline-first full folder pipeline

**New menu Option 5** performs three distinct, ordered stages: **Round 1** scans your existing large LRCLIB SQLite snapshot for **all selected eligible songs offline** (zero HTTP/MusicBrainz), **Round 2** searches only songs still lacking verified `.lrc` against chosen online providers (no duplicate local SQLite lookup), and **Round 3** retries only the particular provider/song pairs that genuinely timed out in Round 2. The original MP3/ID3, existing `.lrc` and candidate safety guarantees remain. A valid local snapshot is required; no silent online-only fallback. Existing **Option 4** remains offline-only, as before. Full prompts in [`HOW_TO_START_V2_1_20.txt`](HOW_TO_START_V2_1_20.txt).

## ✨ Highlights

- **Five clear work modes:** normal search, candidate promotion, LRCLIB catch-up, offline-only search, and the new offline-first three-stage search.
- **Offline LRCLIB:** optionally search an official, locally installed SQLite snapshot before going online—or exclusively offline.
- **12 lyrics search routes:** FAST (5) and FULL (12); some routes use overlapping back-end services.
- **Greek/Greeklish search:** manual alias and word conversion support; optional local Greeklish-to-Greek AI.
- **Matching safeguards:** title and artist verification, version/remix compatibility, and duration within 3 seconds for automatic saving.
- **No silent substitutions:** uncertain timed lyrics become `.candidate.lrc` files requiring manual review.
- **Safe library handling:** no modifications to MP3 audio or ID3 artist/title tags; existing `.lrc` files are skipped; LIVE tracks are excluded.
- **Diagnostics:** per-provider HTTP/status details, per-song results, review lists, timeout records, and statistics.
- **Smart retries:** only verified network timeouts trigger targeted retry rounds; HTTP 429 and access restrictions are respected.
- **Large collections:** subfolders, seven-day no-match history, and unattended processing.

## 🚀 Quick start

1. Download the **Windows ZIP** and **PDF user manual** from [the latest release](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases).
2. Extract the ZIP completely to a normal folder; don't launch from inside an archive.
3. Install [Python 3.10 or later](https://www.python.org/downloads/) if necessary. The Windows launcher can install required Python packages through `pip` if they are missing.
4. Double-click **`START_HERE.cmd`**. Select one of the five menu modes, then follow the questions.
5. Test with **20** eligible songs before choosing **A** to scan an entire collection.

### Main menu

| Choice | Use it when… | Network during scan? |
| --- | --- | --- |
| **1 — SEARCH** | You want offline LRCLIB first (if configured) and then other selected lyrics sources for missing matches. | **Yes**, for selected online routes |
| **2 — MARKED PROMOTION** | Bulk-install the first `.candidate.lrc` for each MP3 as a playable, clearly **UNVERIFIED** `.lrc`, then shift other numbered candidates down. | **No** |
| **3 — LRCLIB CATCH-UP** | A previous run created a queue of unfinished LRCLIB searches. | Configurable: offline-only or online fallback |
| **4 — OFFLINE LRCLIB ONLY** | You want to scan **any MP3 directory**, even if no catch-up queue exists, using only your local LRCLIB database. | **No** lyrics/metadata requests |
| **5 — OFFLINE FIRST / ONLINE FALLBACK** | Scan the whole folder offline first, online only for remaining songs, then retry real network timeouts. Supports persistent per-song/stage restart checkpoints. | **Offline in Round 1; online in Round 2/3 only** |

**Option 3 is not a general-purpose new-folder scanner.** Use **option 4** to search a new folder only against your local LRCLIB snapshot.

### Option 2 — bulk promotion with a visible review marker (new in v2.1.16)

For large libraries where opening hundreds of candidate files individually is impractical:

1. Choose **2** in `START_HERE.cmd`, select your MP3 folder, and optionally include subfolders.
2. Review the preview, then explicitly confirm bulk promotion. It never contacts the Internet.
3. For each song without an existing `.lrc`, the first `Song.candidate.lrc` becomes `Song.lrc` **with this first line:**

   ```lrc
   [00:00.00] candidate
   [00:05.00] First synchronized lyric
   ```

4. The used primary candidate is removed. Remaining alternatives advance one position: `.candidate.2.lrc` becomes `.candidate.lrc`, `.candidate.3.lrc` becomes `.candidate.2.lrc`, and so on.
5. Listen to the track. If the lyrics are correct, delete only the **00:00 candidate line**. If wrong, delete `Song.lrc` and run Option 2 again to try the next candidate.

Example: `Song.mp3`, `Song.candidate.lrc`, `Song.candidate.2.lrc`, `Song.candidate.3.lrc` becomes `Song.mp3`, `Song.lrc`, `Song.candidate.lrc`, `Song.candidate.2.lrc`.

**Safety:** Option 2 does *not* verify the true recording version. Existing `.lrc` files, MP3 audio and ID3 tags are never overwritten. Invalid/untimed candidates are skipped. Errors and partially shifted alternatives are listed in `LRC_Candidate_Promotion_Report_v2_1_16.csv`. No online providers are queried.

### 🔌 Reuse an existing LRCLIB database

Already have a large `.sqlite3` snapshot installed?

1. Run **`CONNECT_EXISTING_LRCLIB_DATABASE.cmd`**.
2. Select or paste the full path to your existing SQLite database.
3. The tool saves its location in `LRCLIB_LOCAL_DB.txt`. **It doesn't copy, decompress or re-download the database.**
4. Open `START_HERE.cmd` and choose **4** to scan only offline or **1** for offline-first, then other sources.

A large LRCLIB database is **never bundled** inside this GitHub repository or its Windows ZIP. Official snapshots can use **hundreds of GiB of disk space**; confirm disk capacity before installing one.

### Greeklish artist-name accuracy in v2.1.19

**New separate `Greek_Artists.csv`** contains 113 curated standalone artist and group name spellings, separate from the word dictionary. This addresses full identities rather than attempting letter-by-letter conversion, e.g. `Giorgos Alkaios → Γιώργος Αλκαίος`, `Alkinoos Ioannidis → Αλκίνοος Ιωαννίδης`, `Ditikes Sinikies → Δυτικές Συνοικίες`, `Antidrasi → Αντίδραση`. The file contains no private MP3 filenames or collection paths.

**Exact search plan:** original title + original artist is always first; original title + approved Greek artist is second; Greek title + approved artist follows if present. Unknown Greeklish artist names are **not** converted by the local AI. Your personal `Greek_Aliases.csv` overrides the public artist names.

**Mixed-language titles:** preserve known English words in Greeklish titles: `Sexy koritsia` becomes `Sexy κορίτσια`, never `Σεξυ κορίτσια`. This improves search alternatives but does not change song tags. The new guide `HOW_TO_START_V2_1_19.txt` contains **all 12 prompts** in the correct Option 1 order for a 20-song quality test.

### Greeklish accuracy in v2.1.18 - expanded dictionary + local SQLite

The app uses **three levels of confidence**, in this order:

1. **Manual aliases** in `Greek_Aliases.csv` - reviewed full-title/artist spellings you explicitly provided.
2. **Curated accented word dictionaries** in `Greek_Words_Expanded.csv` (public additions) and `Greek_Words.csv` (editable overrides), optionally indexed into the small `Greek_Lexicon.sqlite3` - used only when the entire base title is recognized, before AI. Examples: `Fonazo → Φωνάζω`, `Den Ise Erotas Esi → Δεν είσαι έρωτας εσύ`, `Esy Horeveis Kai Ego Pethaino → Εσύ χορεύεις και εγώ πεθαίνω`.
3. **Optional installed local AUEB G2G AI** - only for otherwise unresolved plausible Greeklish, marked as an AI suggestion needing review. Known words in aligned model output can be corrected from the dictionary, including older cached predictions.

**English protection:** Titles such as `Best of Times` will not be phonetically transliterated to fake Greek. Artist brands such as `2002 GR` and mixed international artist credits are left alone unless you supply a manual alias.

**Important:** Greeklish-to-Greek is inherently ambiguous; the expanded curated dictionary cannot resolve every unknown title perfectly. No AI output is evidence of the correct recording/remix. Original title+artist searches always run first, and strict version/duration checks still control automatic `.lrc` saving.

The CSV `LRC_G2G_AI_Review_v2_1_15.csv` includes the original text, Greek alternatives, origin, AI output, and review flags. (This historical filename is retained for compatibility.) Copy any personal edits to `Greek_Aliases.csv` when installing into a new program directory; do not replace them with the empty example file.

To fix additional problematic songs permanently, add a reviewed row in `Greek_Aliases.csv`, for example:

```csv
type,greeklish,greek
title,Den Ise Erotas Esi,Δεν είσαι έρωτας εσύ
title,Fonazo,Φωνάζω
```

#### Public Greek vocabulary database (new in v2.1.18)

- **950 additional common Greeklish spellings** were curated from recurring words in a large Greek music example list, without distributing its private full-song filenames or Windows directory paths.
- The public SQLite file **`Greek_Lexicon.sqlite3`** is generated from both CSV sources and contains just word mappings (roughly 1,000 distinct entries). It is tiny, local, read-only and entirely separate from the gigantic LRCLIB lyrics SQLite database.
- `Greek_Words.csv` remains the highest-priority **per-word customization**. `Greek_Aliases.csv` remains the highest-priority **full-title and artist customization**.
- To rebuild the small database after editing a CSV: `python BUILD_GREEK_LEXICON_DB.py`. If it is missing, corrupted, or older than the CSV files, the app falls back to those CSV files automatically.
- Known dictionary words can also correct *aligned tokens* in the optional AI suggestion when the complete title includes unfamiliar Greeklish. This still does not prove song identity.
- No MP3/ID3, existing LRC files, or artist names are renamed or rewritten. Your separate private alias list should be reviewed before importing.

**Why not automatically trust every phrase?** Words such as `pote` (ποτέ / πότε), `ton` (τον / των), `i` (η / ή / οι) and `kaneis` (κάνεις / κανείς) need context. Google can use contextual search and indexed song titles; a standalone word-to-word database cannot always infer them. Use a reviewed full-title alias for these cases.

Option 2's verified-working `[00:00.00] candidate` marker and numbered candidate rotation are **unchanged**.

### 🇬🇷 Greek and Greeklish collections

Choose Greek mode **Y** when prompted. You may optionally install the local Greeklish-to-Greek AI model with `SETUP_GREEK_AI.cmd`; model downloads are separate. Original MP3 filenames and ID3 tags remain untouched. Greek search can work without the AI through built-in search variants and reviewed aliases.

**MusicBrainz Picard is not required.** MusicBrainz metadata lookup is an optional built-in online search aid, not a separate lyrics database.

## 🪟 Which Windows launcher should I use?

| Launcher | What it does | Recommended use |
| --- | --- | --- |
| **`START_HERE.cmd`** | Opens the five-mode application menu | **Start here for everyday use** |
| `CONNECT_EXISTING_LRCLIB_DATABASE.cmd` | Links an already extracted local SQLite snapshot | Reuse an existing database, no new download |
| `SETUP_LRCLIB_DATABASE.cmd` | Offers an optional automated official snapshot download and setup | First-time **offline database installation**, with enough disk space |
| `SETUP_LRCLIB_DATABASE_FROM_FILE.cmd` | Imports a separately obtained `.sqlite3` or `.sqlite3.gz` file | Manual database setup |
| `CLEANUP_LRCLIB_DATABASE.cmd` | Offers separately confirmed deletion of compressed archive, extracted database, both, or cancel | Recover disk space safely |
| `SETUP_GREEK_AI.cmd` | Installs optional local Greeklish AI dependencies | Greek/G​reeklish music |
| `Run_Diagnostics.cmd` | Checks Python and basic application dependencies | Troubleshooting |
| `Run_LRC_Finder.cmd` | Lower-level command-line program launcher | Alternative/advanced usage |
| `Start_LRC_Finder.bat` | Compatibility launcher | When an older Windows batch entry point is needed |

If you use PowerShell instead of double-clicking a launcher, prefix the filename with `.\`, for example:

```powershell
.\START_HERE.cmd
```

## 🛡️ Matching, review, and reports

Automatic search (options 1 and 4) saves an unmarked `.lrc` only when it can verify the artist, song title, recording version, and a duration difference of **no more than three seconds**. A possible result that cannot be reliably verified is stored as a **review-only** `.candidate.lrc` rather than silently replacing the correct remix or radio edit.

Results, source statistics and HTTP diagnostics are written to the selected MP3 folder. They help distinguish **NO_MATCH** from an unavailable provider, HTTP **401/403**, **429**, **503**, a genuine **network timeout**, and a candidate requiring review. Only actual network timeouts are eligible for the automated retry rounds.

Option 2 intentionally makes candidate lyrics playable **without claiming they are verified**. The line `[00:00.00] candidate` is a reminder to review the track in your player; delete that single line only after confirming its accuracy.

## 📘 Documentation

The accompanying [v2.1.16 English PDF manual](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/tag/v2.1.16) includes:

- Installation and every CMD/BAT launcher, explained in order
- Each startup prompt and the meaning of **Enter / Y / N / FAST / FULL / 20 / A**
- International, Greek/Greeklish, and offline-only worked examples
- LRCLIB automatic setup, existing-database connection, and optional cleanup
- Review candidates, report files, troubleshooting, and version history

For individual changes across versions, see [CHANGELOG.md](CHANGELOG.md).

## ⚖️ License, third-party software and lyrics rights

**Original LRC Bulk Finder project source code** is made available under the [MIT License](LICENSE), © 2026 Dimitris L.

**This does not relicense third-party packages, provider APIs, song lyrics, or LRCLIB database dumps.** The program uses separately installed libraries, including **Mutagen** and **Unidecode**, both **GPL-2.0-or-later**. Their copyleft terms may affect redistribution of a combined application, even where the original code has an MIT notice. Distributors should review the applicable obligations and include relevant notices; do not represent the entire dependency stack as MIT-only.

Other components include `syncedlyrics` (MIT) and an optional AUEB Greek NLP toolkit (check its upstream license and model terms). See [SOURCES_AND_CREDITS.txt](SOURCES_AND_CREDITS.txt) and [PUBLICATION_AND_LICENSE_NOTES.txt](PUBLICATION_AND_LICENSE_NOTES.txt).

Downloaded lyrics belong to their respective rights holders. No MP3s, lyrics collection, or huge LRCLIB snapshot is distributed with the program.

## ✅ Automated tests

GitHub Actions runs focused **offline feature and safety regression tests, including marked candidate rotation,** across Windows and Linux using Python 3.10 and 3.13. The badge above reflects the actual workflow status. These tests cover offline LRCLIB folder scanning, database reuse, no-network safeguards, review behavior and remix/version matching. **They do not test live lyrics-provider availability** or guarantee perfect matching on every track.

Run locally with:

```sh
python -m pip install mutagen Unidecode
python -m unittest -v TEST_OFFLINE_FOLDER_V2_1_15 TEST_CONNECT_EXISTING_DB_V2_1_15 TEST_PACKAGE_OFFLINE TEST_SAFETY_V2_1_4 TEST_CANDIDATE_PROMOTION_V2_1_16 TEST_CANDIDATE_SIDECARS_V2_1_8
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for test and pull-request guidance, and [SECURITY.md](SECURITY.md) for privacy, database and safety notes.

## 💬 Feedback and contributions

Found a bug, an outdated provider or an inaccurate match? Open a [GitHub Issue](https://github.com/DimitrisLai/LRC-Bulk-Finder/issues) with the **software version**, selected mode, the provider status/error, and a sanitized report excerpt. **Remove personal folder paths and private metadata** before uploading reports.

Contributions that improve reliability, offline searching, provider error handling, or documentation are welcome. The current Windows CLI edition remains a **Public Beta**.
