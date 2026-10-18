# LRC Bulk Finder

**Windows synchronized lyrics downloader · v2.1.15 · Public Beta**  
Created by **Dimitris L.**

Find synchronized `.lrc` lyrics for MP3 collections, with strict artist, recording-version and duration safeguards. Optional local LRCLIB SQLite searches can work without lyrics-provider network requests. Greek/Greeklish search variants and an optional locally installed G2G AI model are also supported.

> The full LRCLIB database is **not bundled**. Provider services and database snapshots have their own usage rules. No lyrics provider can guarantee matches for every song or remix.

## Getting started

Download the matching **Windows ZIP and complete English PDF User Manual** from [GitHub Releases](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases). Extract the ZIP to a folder, then double-click **`START_HERE.cmd`**. Requires Windows 10/11 and Python 3.10+.

| Menu | What it does | Network |
| --- | --- | --- |
| **1 — SEARCH** | Offline LRCLIB first if configured, then selected online lyrics providers | Yes for remote providers |
| **2 — PROMOTE** | Review/approve primary `.candidate.lrc` files | No |
| **3 — LRCLIB CATCH-UP** | Retry a prior incomplete LRCLIB queue | Optional |
| **4 — OFFLINE LRCLIB ONLY** | Scan any selected MP3 folder, even without a catch-up queue | No lyrics/metadata HTTP requests |

For **option 4**, connect a previously extracted LRCLIB SQLite snapshot once via `CONNECT_EXISTING_LRCLIB_DATABASE.cmd`. Choose the existing `.sqlite3` file. It saves a tiny `LRCLIB_LOCAL_DB.txt` configuration; it does **not** copy or download the database. Then launch `START_HERE.cmd`, choose 4, select a folder, and try **20** songs before **A** (all). Optional Greek G2G conversion runs locally after it has been installed.

## What every CMD/BAT file does

| Launcher | Purpose |
| --- | --- |
| `START_HERE.cmd` | Recommended main launcher, actions 1–4 |
| `CONNECT_EXISTING_LRCLIB_DATABASE.cmd` | Link a previously extracted huge SQLite database without downloading it again |
| `SETUP_LRCLIB_DATABASE.cmd` | Optional automatic download/install of an official LRCLIB snapshot |
| `SETUP_LRCLIB_DATABASE_FROM_FILE.cmd` | Set up from an already downloaded `.sqlite3` or `.sqlite3.gz` |
| `CLEANUP_LRCLIB_DATABASE.cmd` | Confirmed cleanup of a downloaded archive, extracted DB, or both |
| `SETUP_GREEK_AI.cmd` | Optional Greeklish-to-Greek AI setup |
| `Run_Diagnostics.cmd` | Python/dependency diagnostics |
| `Run_LRC_Finder.cmd` | Lower-level runner invoked by START_HERE |
| `Start_LRC_Finder.bat` | Compatibility launcher |

## Main behavior

- Original MP3 audio and artist/title tags are not modified.
- Existing `.lrc` files and LIVE tracks are skipped.
- Automatic saves require verified artist/title, matching recording version and duration within 3 seconds.
- Unverified timed lyrics are written as `.candidate.lrc` files requiring careful manual review.
- Only genuine network timeouts trigger targeted timeout-retry rounds; HTTP 429/503 and access-denied errors do not.
- Option 4 never contacts online lyrics providers or MusicBrainz during the scan.
- Option 3 needs a previously created LRCLIB catch-up queue. Use option 4 for any new folder.

## Optional offline LRCLIB storage

The SQLite database can require **hundreds of GiB**. One official October 2026 snapshot extracted to about **243.5 GiB**, but later files may vary. After verifying installation, cleanup option **1** removes only the compressed archive and keeps the local SQLite search available. Deleting the extracted database disables offline searching.

## Greek and international collections

For Greek/Greeklish, answer **Y** to Greek mode and optionally install/enable the G2G model. For international music with good artist/title tags, MusicBrainz metadata lookup can be set to **N** for faster online search. **MusicBrainz Picard is not required.**

## Documentation, rights and reporting

The matching PDF manual provides step-by-step installation, each prompt and default, all nine launchers, three examples, report formats, troubleshooting, and release history.

See [CHANGELOG.md](CHANGELOG.md), [SOURCES_AND_CREDITS.txt](SOURCES_AND_CREDITS.txt) and [PUBLICATION_AND_LICENSE_NOTES.txt](PUBLICATION_AND_LICENSE_NOTES.txt). A public repository does **not** automatically grant a code or lyric redistribution license; the project owner must select an appropriate license after checking dependencies and third-party content rights.

Submit reproducible problems using [GitHub Issues](https://github.com/DimitrisLai/LRC-Bulk-Finder/issues). Sanitize local paths and credentials; never post private music collections or copyright-protected lyrics.
