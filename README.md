# 🎵 LRC Bulk Finder

**Synchronized lyrics for your entire MP3 collection — online or offline.**

**Windows · Python 3.10+ · Public Beta v2.9.6 · Created by Dimitris L.**  

![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![MIT License](https://img.shields.io/badge/License-MIT-green)
[![Python tests](https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/workflows/tests.yml/badge.svg)](https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/workflows/tests.yml)

**Project source code: [MIT License](LICENSE)** · [Releases](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases) · [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md)

LRC Bulk Finder finds timestamped **`.lrc` lyrics files** for MP3 music libraries. It can work through multiple online lyrics sources or search an optional **local LRCLIB SQLite snapshot** — without internet requests during an offline-only scan. It supports international music, Greek and Greeklish titles, multi-folder collections, and reporting designed for large unattended runs.

Lyrics are saved alongside the MP3 with the same base filename, making them compatible with many portable music players and car stereos that support synchronized LRC text.

> **Public Beta:** External provider APIs can change, disappear, restrict requests or return incomplete metadata. Finding lyrics for every song is not guaranteed, particularly for rare remixes, instrumentals and extended versions.

## v2.9.6 — Cumulative online provider packs (3–14 sources)

Saved searches now offers **six cumulative tiers** alongside the unchanged Legacy FAST/FULL choice: **Tier 1** LRCLIB + SyncLRC + Unison; **Tier 2** adds LrcAPI; **Tier 3** adds NetEase, Musixmatch and Megalobiz; **Tier 4** adds LiriQo and BetterKuGou; **Tier 5** adds BetterQQ (new review-only QRC/QQ), YouLyTTML, BetterTTML and Tencent; **Tier 6** adds experimental SimpMusic. Every higher tier keeps all prior sources. Changing the tier does **not** change the song limit, Greek mode, search action or saved lyrics. Older saved profiles and presets default to Legacy, completely unchanged.

QQ word-timed XML becomes line-timed human-review candidates only because the public endpoint cannot verify resolved recording identity and duration for safe automatic lyric writing. Some late-stage sources are restricted or unavailable, and may be skipped after safe cooldowns. See [v2.9.6 details](RELEASE_NOTES_V2_9_6.md).

## v2.9.5 — Modern Light / Dark interface (Windows)

The Control Center has a cleaner Windows interface using the standard ttk engine (no heavyweight new GUI dependencies). The refreshed design includes a distinct indigo Start Search button, a separate STOP action, readable counters and tables, a modern header, and vertical scrolling for the Saved searches form. Switch **Appearance → Light / Dark** or **Εμφάνιση → Φωτεινό / Σκοτεινό** at the top-right. Both the theme and interface language persist across restarts without changing saved profiles, the current scan or lyric files. See [release notes](RELEASE_NOTES_V2_9_5.md) and the [latest releases](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases).

## v2.9.4 — One-click optional Greek G2G AI setup (Windows)

The standalone Windows edition can now set up the optional **full AUEB Greek G2G model** from inside Control Center, without opening folders or manually typing Python commands. Click *Install / verify Greek G2G AI (one click)* and approve the large download. The model (about 1.2 GB) and additional Python/PyTorch dependencies install into an isolated local user environment. Windows may request authorization if Python needs installing through winget. Only a successfully verified real model enables the AI checkbox and preset. A local CPU-based companion provides reusable inference. No music files are uploaded or modified by AI installation; generated spellings remain suggestions to review. On failure, dictionary-only mode remains usable. See [v2.9.4 notes](RELEASE_NOTES_V2_9_4.md).

## Windows v2.9.3 — Unicode crash and Local AI fixes

**Latest maintenance release:** fixes the fatal `charmap`/Unicode-hyphen error from the 5,150-track search; the standalone EXE now falls back safely to curated Greek dictionaries instead of offering an unusable Local AI model. The GUI warns when a saved preset name differs from its scope (such as a 20-song FAST preset incorrectly saved as ALL/Offline First).

Includes **15 Greek/international search presets**, **730** Greek artist aliases and **92** additional unverified Greeklish word candidates drawn from Wikipedia *song titles* (not copyrighted lyrics). English and Greek manuals and five checksum-verified release assets are provided. Unfinished songs remain retryable; no lyrics provider success is guaranteed.

See [release notes](RELEASE_NOTES_V2_9_3.md), [Wikipedia provenance](NEXT_UPDATE_GREEK_VOCABULARY_PRESETS.md) and [official releases](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases).

## Expanded Greek singer aliases — 23 October 2026

The repository now includes **730** reviewed/source-linked `greeklish,greek` artist aliases: all **113 preexisting manually approved spellings** plus **617 new Wikipedia-linked mappings**. The import followed both continuation pages of Greek Wikipedia's [Έλληνες τραγουδιστές](https://el.wikipedia.org/wiki/Κατηγορία:Έλληνες_τραγουδιστές) category (386 direct articles), both pages for Greek female singers (247), and ten additional related singer categories, for 750 distinct source article titles. Only explicit English Wikipedia titles or linked Wikidata English labels are accepted as new mappings; unknown names and spelling collisions are kept out. Provenance and scope: [full audit](GREEK_ARTISTS_WIKIPEDIA_AUDIT.md), [per-artist source CSV](Greek_Artists_Wikipedia_Audit.csv), [reproducible updater](UPDATE_GREEK_ARTISTS_WIKIPEDIA.py), [approved baseline](Greek_Artists_Baseline_Approved.csv).

**Existing standalone v2.9.2 downloads remain immutable** and still include the original small CSV. To test this improvement before the next official application build, close Control Center, back up the `Greek_Artists.csv` beside the two EXEs in your *extracted* application folder, replace only that CSV with the [expanded raw file](https://raw.githubusercontent.com/DimitrisLai/LRC-Bulk-Finder/main/Greek_Artists.csv), and restart the app. Your audio, ID3, primary lyrics, profiles and current app version are unchanged. Alternatively use a new official release when the data is bundled.

## Current release — v2.9.2 Bounded Greek Search Preflight

Fixes the user-reported 3,183-track, zero-progress startup: displays PREFLIGHT DISCOVERY/METADATA progress and honors a selected 20-song limit before expensive ID3 reading. A short search no longer processes all 3,183 track metadata records before searching. Tag-only LIVE exclusions are preserved; original audio and LRC files remain untouched. The three privately provided real MP3s were inspected (two with artist/title, one lacking artist), and their audio is **not included** in this repository or its release archives. [Release notes](RELEASE_NOTES_V2_9_2.md) · [QA plan](TEST_AUDIT_V2_9_2.md). **Official v2.9.2 is now published and all five public downloads passed independent SHA-256 verification:**

| Asset | Download |
| --- | --- |
| **Windows standalone GUI ZIP** (recommended; no Python required) | [LRC Bulk Finder v2.9.2 Standalone Windows](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.9.2/LRC_Bulk_Finder_v2_9_2_Standalone_Windows_GUI.zip) |
| Source/CMD/test ZIP | [Complete v2.9.2 source](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.9.2/LRC_Bulk_Finder_Public_v2_9_2_GitHub_Release_Windows.zip) |
| Complete English user manual PDF | [English v2.9.2 manual](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.9.2/LRC_Bulk_Finder_v2_9_2_Complete_User_Manual_EN.pdf) |
| Ελληνικός οδηγός PDF | [Greek v2.9.2 guide](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.9.2/LRC_Bulk_Finder_v2_9_2_User_Guide_EL.pdf) |
| SHA-256 hashes | [v2.9.2 SHA256SUMS](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.9.2/LRC_Bulk_Finder_v2_9_2_SHA256SUMS.txt) |

[Official v2.9.2 release](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/tag/v2.9.2) · [Merged PR #17](https://github.com/DimitrisLai/LRC-Bulk-Finder/pull/17) · [Final four-platform tests](https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/runs/39855697401) · [Windows release and verification](https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/runs/39855697333).



## Previous release — v2.9.1 Windows Startup & Version Display Stability Patch

**If you see a black terminal saying `LRC_Bulk_Finder_Worker.exe: --profile is required`, you've launched the background search worker instead of the main app.** Extract the **entire** Windows standalone ZIP and run **`LAUNCH_LRC_BULK_FINDER_WINDOWS.cmd`** (or **`LRC_Control_Center.exe`**). The worker is launched automatically by the Control Center when you start a search profile.

The previous app also had an incorrect version label: initial language refresh reset the Control Center title to v2.7.0 even while running v2.9.0. v2.9.1 fixes that bug and the outdated update-checker version, tests the visible title of the frozen Windows EXE and adds explicit user-friendly startup guidance. No lyrics, media, provider, Smart Library or karaoke behavior is changed.

[Hotfix source PR](https://github.com/DimitrisLai/LRC-Bulk-Finder/pull/15) · [Notes](RELEASE_NOTES_V2_9_1.md) · [QA audit](TEST_AUDIT_V2_9_1.md). **v2.9.1 is now officially published, and all five downloadable assets were independently SHA-256-verified:**

| Download | Description |
| --- | --- |
| [**Windows standalone GUI ZIP v2.9.1**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.9.1/LRC_Bulk_Finder_v2_9_1_Standalone_Windows_GUI.zip) | **Recommended**, 86.8 MB; extract the entire ZIP and open `LAUNCH_LRC_BULK_FINDER_WINDOWS.cmd` or `LRC_Control_Center.exe`. No Python needed. |
| [**Complete Python/CMD source ZIP**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.9.1/LRC_Bulk_Finder_Public_v2_9_1_GitHub_Release_Windows.zip) | Source, tests and launchers. |
| [**English complete manual (PDF)**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.9.1/LRC_Bulk_Finder_v2_9_1_Complete_User_Manual_EN.pdf) | Includes startup correction and comprehensive features. |
| [**Ελληνικός οδηγός (PDF)**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.9.1/LRC_Bulk_Finder_v2_9_1_User_Guide_EL.pdf) | Greek quick-start and corrections. |
| [**SHA-256 manifest**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.9.1/LRC_Bulk_Finder_v2_9_1_SHA256SUMS.txt) | Verified against all published release assets. |

[Official v2.9.1 release](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/tag/v2.9.1) · [Four-platform final tests](https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/runs/39823574637) · [Windows build and publication](https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/runs/39823574523).



## Previous release — v2.9.0 Smart Library & Stability (English / Ελληνικά Public Beta)

The new fifth **nested** Sync Lab workspace, Smart Library, adds an incremental SQLite local inventory, conservative LRC quality checks, Greek Unicode indexed search, a 200-record paginated review queue, Bookmarked/Reviewed markers, optional audio duration checks, cancellation-safe rollback, recent scan history, and confirmed formula-safe CSV export. No original music, ID3, primary LRC or existing candidate files are modified.

**Stability improvement:** switching songs after optional VLC variable-speed playback now recreates the default pygame 1x backend instead of reusing a released VLC instance. Existing search providers, STOP, safe Undo, and v2.8 karaoke are retained.

**Development:** [v2.9 pull request #14](https://github.com/DimitrisLai/LRC-Bulk-Finder/pull/14) · [Release notes](RELEASE_NOTES_V2_9_0.md) · [QA audit and full-day Windows test checklist](TEST_AUDIT_V2_9_0.md). **Official v2.9.0 downloads, all five assets successfully SHA-256 verified:**

| Download | Description |
| --- | --- |
| [**Windows Standalone GUI ZIP v2.9.0**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.9.0/LRC_Bulk_Finder_v2_9_0_Standalone_Windows_GUI.zip) | **Recommended**, 86.8 MB, no Python installation required; extract the entire ZIP. |
| [**Complete Python/CMD source ZIP**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.9.0/LRC_Bulk_Finder_Public_v2_9_0_GitHub_Release_Windows.zip) | Source code, tests and launchers. |
| [**English complete manual (PDF)**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.9.0/LRC_Bulk_Finder_v2_9_0_Complete_User_Manual_EN.pdf) | Smart Library, quality control and full-day testing. |
| [**Οδηγός χρήσης Ελληνικά (PDF)**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.9.0/LRC_Bulk_Finder_v2_9_0_User_Guide_EL.pdf) | Greek Smart Library and pre-v3.0 checklist. |
| [**SHA-256 checksums**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.9.0/LRC_Bulk_Finder_v2_9_0_SHA256SUMS.txt) | All public download hashes verified. |



## Previous release — v2.8.0 Karaoke Edition (English / Ελληνικά Public Beta)

The new **Karaoke Edition** fourth nested Sync Lab tab turns local instrumental plus LRC playback into a performer-friendly workflow. It offers a saved 500-track operator playlist, guarded automatic instrumental/LRC pairing and manual pairing, optional native drag-and-drop, projector/audience-only lyrics window with target display selection, themes/font/next-line/background, playback countdown, previous/next keyboard controls, global display offset ±30 seconds, separately confirmed undoable timing apply, persisted A–B loops, last-song restoration, precise read-only LRC export preview and redacted support reports.

**Source/QA:** [v2.8 development PR #13](https://github.com/DimitrisLai/LRC-Bulk-Finder/pull/13), [v2.8 release notes](RELEASE_NOTES_V2_8_0.md), [v2.8 audit](TEST_AUDIT_V2_8_0.md), [English/Greek quick start](HOW_TO_START_V2_8_0.txt).

All audio, ID3, source LRC and previous candidates remain protected. Instrumental karaoke displays EXISTING line-level lyrics; no word-by-word highlighting or vocal removal. **Official release v2.8.0 — all assets published and verified against SHA-256:**

| Download | Details |
| --- | --- |
| [**Windows standalone GUI ZIP v2.8.0**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.8.0/LRC_Bulk_Finder_v2_8_0_Standalone_Windows_GUI.zip) | Recommended, 86.7 MB, includes two EXEs; no Python installation needed. |
| [**Python and CMD source ZIP**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.8.0/LRC_Bulk_Finder_Public_v2_8_0_GitHub_Release_Windows.zip) | Full code, tests and launchers. |
| [**Complete English manual**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.8.0/LRC_Bulk_Finder_v2_8_0_Complete_User_Manual_EN.pdf) | PDF updated for Karaoke Edition. |
| [**Αναλυτικός ελληνικός οδηγός**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.8.0/LRC_Bulk_Finder_v2_8_0_User_Guide_EL.pdf) | Greek PDF including projector, playlists and timing correction. |
| [**SHA-256 checksums**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.8.0/LRC_Bulk_Finder_v2_8_0_SHA256SUMS.txt) | Official file hashes reverified after public download. |



## Previous release — v2.7.0 Karaoke & Precision (English / Ελληνικά Public Beta)

Version 2.7 adds karaoke for instrumental audio + your timed LRC, fullscreen current/next lyric display, A–B repeat, optional pitch-preserving VLC speed controls, bounded waveform visualization, timestamp warnings, recovery drafts, nudge sizes/shortcuts, car-radio export profiles and one-click navigation from Results/Candidate review. See [release notes](RELEASE_NOTES_V2_7_0.md), [quick start](HOW_TO_START_V2_7_0.txt), [post-v2.7 roadmap](ROADMAP_V2_8_V2_9_V3_0.md), and [PR #12](https://github.com/DimitrisLai/LRC-Bulk-Finder/pull/12). The primary and secondary LRC files remain protected; only new UNVERIFIED numbered candidates are written. 0.75x/1.25x requires a compatible locally installed VLC player (not bundled); compressed waveform display depends on optional soundfile support.

**Official v2.7.0 downloads (published and SHA-256 checked):**

| Download | Details |
| --- | --- |
| [**Standalone Windows GUI ZIP — v2.7.0**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.7.0/LRC_Bulk_Finder_v2_7_0_Standalone_Windows_GUI.zip) | **Recommended.** Both EXEs and dependencies bundled; unzip the whole archive. |
| [**Python/CMD source ZIP**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.7.0/LRC_Bulk_Finder_Public_v2_7_0_GitHub_Release_Windows.zip) | Source, tests and launchers. |
| [**English complete manual (PDF)**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.7.0/LRC_Bulk_Finder_v2_7_0_Complete_User_Manual_EN.pdf) | All features plus karaoke and precision sections. |
| [**Οδηγός χρήσης στα Ελληνικά (PDF)**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.7.0/LRC_Bulk_Finder_v2_7_0_User_Guide_EL.pdf) | Greek interface and karaoke guidance. |
| [**SHA-256 release manifest**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.7.0/LRC_Bulk_Finder_v2_7_0_SHA256SUMS.txt) | Checksums independently verified against all published binaries and PDFs. |



## Previous release — v2.6.0 Lyrics Studio

The previously published [v2.6.0 release](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/tag/v2.6.0) added the original audio-backed Lyrics Studio and non-overwriting candidate timing corrections. It remains available for users preferring the older workflow.

## Earlier release — v2.5.0 Library Manager (English / Ελληνικά Public Beta)

**NEW Library Manager:** The Results dashboard now offers a searchable and filterable music inventory, exact **Retry selected tracks**, **Why was this rejected?** based on saved provider/review CSV reports, and **Undo last search session...** which safely removes only unchanged sidecars created by that specific v2.5.0 GUI session. Reports may be stale; LRC existence does not mean verified lyrics.

**Safe selected retries:** Only the explicitly selected missing/review songs are searched, using FULL online providers, without reusing old NO_MATCH cache. Changed, missing, ambiguous or already-provided-LRC selections refuse to launch rather than searching your entire library. Normal scan checkpoints are preserved separately.

**Safe undo:** Local journal in your own APPDATA records newly created LRC/candidate files after exclusive creation. Undo asks for confirmation and rechecks byte size, modification timestamp and SHA256. It leaves your original audio, ID3 metadata, pre-existing/edited LRCs, manually created timing fixes, reports and settings untouched. Pre-v2.5.0 runs have no journal and cannot be undone.

| Download | Usage |
| --- | --- |
| [**Standalone Windows GUI ZIP — v2.5.0 (EN / EL)**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.5.0/LRC_Bulk_Finder_v2_5_0_Standalone_Windows_GUI.zip) | Earlier v2.5 release. Extract all files, then open `LRC_Control_Center.exe`. No Python needed. |
| [**Complete Python/CMD ZIP — v2.5.0**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.5.0/LRC_Bulk_Finder_Public_v2_5_0_GitHub_Release_Windows.zip) | Python 3.10+, advanced launchers and optional local AI. |
| [**Complete English manual (PDF)**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.5.0/LRC_Bulk_Finder_v2_5_0_Complete_User_Manual_EN.pdf) | Entire application, including Library Manager. |
| [**Ελληνικός οδηγός PDF**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.5.0/LRC_Bulk_Finder_v2_5_0_User_Guide_EL.pdf) | New Library Manager sections in Greek. |

See the [v2.5.0 release notes](RELEASE_NOTES_V2_5_0.md), [quick start](HOW_TO_START_V2_5_0.txt), and [changelog](CHANGELOG.md). Windows executables are currently unsigned.

## Previous release — v2.4.5 (English / Ελληνικά Public Beta)

The application now opens with **Quick Search**: choose a music folder, choose 20 songs or All songs, and click **START QUICK SEARCH**. No need to configure provider order or a large LRCLIB database for ordinary online searching.

**New Results dashboard:** read-only audio/LRC inventory, searchable table, LRC-present / missing / review-needed filters and CSV export. **New Timing repair:** preview a plus/minus seconds offset for an existing LRC and explicitly save a separate **UNVERIFIED** candidate; the original LRC and audio are protected. **Manual update check and diagnostics** are in Quick Search. Both languages remain available in one installer-free Windows download.

| Download | Who should use it |
| --- | --- |
| [**Standalone Windows GUI ZIP — v2.4.5 (EN / EL)**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.4.5/LRC_Bulk_Finder_v2_4_5_Standalone_Windows_GUI.zip) | Recommended: extract all files, open `LRC_Control_Center.exe`. No Python needed. |
| [**Complete Windows Python/CMD ZIP**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.4.5/LRC_Bulk_Finder_Public_v2_4_5_GitHub_Release_Windows.zip) | Advanced mode with Python 3.10+, CMD launchers and optional Greek AI installation. |
| [**Full English PDF manual**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.4.5/LRC_Bulk_Finder_v2_4_5_Complete_User_Manual_EN.pdf) | Full instructions with the new v2.4.5 chapters. |
| [**Οδηγός χρήσης στα Ελληνικά (PDF)**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.4.5/LRC_Bulk_Finder_v2_4_5_User_Guide_EL.pdf) | Greek user guide for all new features. |

**Safe by design:** A dashboard status of *Has LRC* means a file exists, **not** that the lyrics were independently verified. Timing-repair output is marked candidate; existing files are not overwritten. Read the [v2.4.5 release notes](RELEASE_NOTES_V2_4_5.md), [quick start](HOW_TO_START_V2_4_5.txt), and the [changelog](CHANGELOG.md). Windows EXEs remain unsigned.

## Previous release — v2.4.4 (English / Ελληνικά Public Beta)

**English and Greek are both included in the same Windows application.** Select **Interface language / Γλώσσα εφαρμογής** at the top-right and choose **English** or **Ελληνικά**. Labels, buttons, tooltips, presets and common dialogs change immediately; the selection is remembered. Search settings, saved profiles, filenames and lyrics are unchanged.

| Download | Who should use it |
| --- | --- |
| [**Standalone Windows GUI ZIP (EN + EL)**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.4.4/LRC_Bulk_Finder_v2_4_4_Standalone_Windows_GUI.zip) | Recommended: extract the complete ZIP, keep both EXEs together and run `LRC_Control_Center.exe`. Python is not needed. |
| [**Complete Windows Python/CMD ZIP**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.4.4/LRC_Bulk_Finder_Public_v2_4_4_GitHub_Release_Windows.zip) | Python 3.10+, CLI launchers and optional local Greek AI setup. |
| [**Full English PDF manual**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.4.4/LRC_Bulk_Finder_v2_4_4_Complete_User_Manual_EN.pdf) | Complete instructions, including v2.4.4 English/Greek addendum. |
| [**Οδηγός χρήσης στα Ελληνικά (PDF)**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.4.4/LRC_Bulk_Finder_v2_4_4_User_Guide_EL.pdf) | Greek first-use instructions, settings, STOP and troubleshooting. |

**Also in v2.4.4:** improved Windows STOP worker/child verification using a native process snapshot, with a conservative fallback and warnings if verification is uncertain. Strict artist/title/version/duration checks, audio/ID3 protection, separate `.candidate.lrc` files, and existing sidecar protection are unchanged. See [release notes](RELEASE_NOTES_V2_4_4.md), [quick start](HOW_TO_START_V2_4_4.txt), and [changelog](CHANGELOG.md).

**New users:** first test 20 songs. Search mode 1 requires no large local LRCLIB database; modes 4 and 5 do. External providers can be unreliable. Windows executables are unsigned.

## Previous release — v2.4.3 (historical)


**Previous version:** v2.4.3 remains available for compatibility. Download from the [v2.4.3 release page](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/tag/v2.4.3), or choose the package you need:

| Download | Who should use it |
| --- | --- |
| [**Standalone Windows GUI ZIP**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.4.3/LRC_Bulk_Finder_v2_4_3_Standalone_Windows_GUI.zip) | Easiest Windows option: extract everything and open `LRC_Control_Center.exe`. No separate Python installation required for normal searches; keep both EXEs together. |
| [**Complete Windows Python/CMD ZIP**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.4.3/LRC_Bulk_Finder_Public_v2_4_3_GitHub_Release_Windows.zip) | Python 3.10+ edition for the GUI (`OPEN_CONTROL_CENTER.cmd`), classic console (`START_HERE.cmd`), or optional external local Greek G2G AI. |
| [**Complete v2.4.3 English PDF user manual**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.4.3/LRC_Bulk_Finder_v2_4_3_Complete_User_Manual_EN.pdf) | Beginner-friendly step-by-step setup, 20-song test, all controls, candidate review, provider health, STOP/resume and troubleshooting. |

**Start with 20 songs.** In the GUI choose a music folder, select action **1** for online searching without a local snapshot, **5** for a three-stage offline-first scan with an existing large LRCLIB SQLite database, or **4** for offline-only SQLite searching. Select and save a search profile, then start your test. The full LRCLIB snapshot is not included.

### What's included in v2.4.3

- **Provider Health:** observed working, temporary-error, timed-out and blocked statuses; a successful HTTP response is distinct from a *verified lyric file actually saved*.
- **Improved STOP:** attempts to terminate the worker process tree, checks termination, and warns if verification is incomplete. Saved checkpoints can help resume unfinished work.
- **Six search counters:** four stage counters (verified LRCs, candidates, not found, skipped/missing metadata) reset after each stage, while two all-stage totals remain cumulative for the run.
- **Resume previous search**, per-provider contribution statistics, and locally approved Greeklish/artist/title aliases.
- **Optional experimental SimpMusic** support, disabled by default. Other experimental source research does not automatically enable additional providers.
- All prior strict title/artist/version/duration checks, protected existing sidecars, and read-only original audio/metadata remain in force.

**QA:** the Windows/Linux Python 3.10/3.13 regression matrix and the independent Windows standalone GUI/worker build and smoke tests passed. External music services can change or be unavailable; the project remains a *Public Beta*.

For older-version changes see the [full changelog](CHANGELOG.md). The older release notes below are historical.

## Earlier release: v2.4.1 — historical STOP and five counters

The Control Center now sends a **cooperative stop request** to the search worker. This also works with the frozen Windows GUI, which may have no console for Ctrl+Break. Press **Stop search safely** to finish the bounded current request, preserve completed checkpoints and write reports. If it cannot exit within eight seconds, the GUI offers a **Force STOP (last resort)** action requiring separate confirmation.

The Live Progress tab shows **LRC found / Candidates / Not found** for the active stage and separate cumulative **LRC found (ALL stages) / Candidates (ALL stages)**. The first three return to **0 immediately after each stage finishes**, while both cumulative totals remain. Timeouts and server errors are *not* falsely described as confirmed no-matches.

[Detailed v2.4.1 instructions](HOW_TO_START_V2_4_1.txt) · [Release notes](RELEASE_NOTES_V2_4_1.md)

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

1. Choose the **standalone GUI ZIP** (no Python needed for normal searches) or the **complete Python/CMD ZIP** from [the current v2.4.3 release](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/tag/v2.4.3).
2. Extract **all** files into a normal Windows folder; do not open the program inside the compressed archive.
3. For standalone, double-click **`LRC_Control_Center.exe`** and keep `LRC_Bulk_Finder_Worker.exe` in the same folder. For the Python/CMD edition, install [Python 3.10+](https://www.python.org/downloads/) if needed, and run **`OPEN_CONTROL_CENTER.cmd`** (GUI) or **`START_HERE.cmd`** (classic console).
4. Select the music folder. Use **action 1** without a downloaded LRCLIB SQLite snapshot, **action 5** for offline-first plus online fallback with the snapshot, or **action 4** for offline-only.
5. Save a profile and test with **20** missing-lyrics tracks. Review candidates and reports before choosing **A** for an entire collection.

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

The [**current v2.4.3 Complete English User Manual (PDF)**](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/download/v2.4.3/LRC_Bulk_Finder_v2_4_3_Complete_User_Manual_EN.pdf) walks a new user through:

- Installing either the standalone Windows GUI or the full Python/CMD edition.
- Connecting an existing LRCLIB SQLite database (or choosing online-only), and trying a **20-song first test**.
- The profiles, Greek/Greeklish options, all search actions and the experimental-provider safety switch.
- Reading the provider health dashboard, stage counters, verified results, review candidates and reports.
- Using STOP safely, resuming unfinished searches, optionally approving Greek aliases, and troubleshooting.

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
