# 🎵 LRC Bulk Finder

**Synchronized lyrics for your entire MP3 collection — online or offline.**

**Windows · Python 3.10+ · Public Beta v2.1.16 · Created by Dimitris L.**  

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![MIT License](https://img.shields.io/badge/License-MIT-green)
[![Python tests](https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/workflows/tests.yml/badge.svg)](https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/workflows/tests.yml)

**Project source code: [MIT License](LICENSE)** · [Releases](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases) · [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

LRC Bulk Finder finds timestamped **`.lrc` lyrics files** for MP3 music libraries. It can work through multiple online lyrics sources or search an optional **local LRCLIB SQLite snapshot** — without internet requests during an offline-only scan. It supports international music, Greek and Greeklish titles, multi-folder collections, and reporting designed for large unattended runs.

Lyrics are saved alongside the MP3 with the same base filename, making them compatible with many portable music players and car stereos that support synchronized LRC text.

> **Public Beta:** External provider APIs can change, disappear, restrict requests or return incomplete metadata. Finding lyrics for every song is not guaranteed, particularly for rare remixes, instrumentals and extended versions.

## ✨ Highlights

- **Four clear work modes:** complete search, marked candidate promotion, LRCLIB catch-up, and offline-only scanning of any folder.
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
4. Double-click **`START_HERE.cmd`**. Select one of the four menu modes, then follow the questions.
5. Test with **20** eligible songs before choosing **A** to scan an entire collection.

### Main menu

| Choice | Use it when… | Network during scan? |
| --- | --- | --- |
| **1 — SEARCH** | You want offline LRCLIB first (if configured) and then other selected lyrics sources for missing matches. | **Yes**, for selected online routes |
| **2 — MARKED PROMOTION** | Bulk-install the first `.candidate.lrc` for each MP3 as a playable, clearly **UNVERIFIED** `.lrc`, then shift other numbered candidates down. | **No** |
| **3 — LRCLIB CATCH-UP** | A previous run created a queue of unfinished LRCLIB searches. | Configurable: offline-only or online fallback |
| **4 — OFFLINE LRCLIB ONLY** | You want to scan **any MP3 directory**, even if no catch-up queue exists, using only your local LRCLIB database. | **No** lyrics/metadata requests |

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

### 🇬🇷 Greek and Greeklish collections

Choose Greek mode **Y** when prompted. You may optionally install the local Greeklish-to-Greek AI model with `SETUP_GREEK_AI.cmd`; model downloads are separate. Original MP3 filenames and ID3 tags remain untouched. Greek search can work without the AI through built-in search variants and reviewed aliases.

**MusicBrainz Picard is not required.** MusicBrainz metadata lookup is an optional built-in online search aid, not a separate lyrics database.

## 🪟 Which Windows launcher should I use?

| Launcher | What it does | Recommended use |
| --- | --- | --- |
| **`START_HERE.cmd`** | Opens the four-mode application menu | **Start here for everyday use** |
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
