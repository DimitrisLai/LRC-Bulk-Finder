# LRC Bulk Finder

**Multi-source synchronized lyrics downloader for Windows** with optional offline **Greeklish-to-Greek AI** support.

**Created by Dimitris L.**  
**Current release:** v2.1.4 — **Public Beta**  
**Interface:** Command-line (no GUI required)

> **Public beta:** This release has automated/offline test coverage, but has not been fully validated across every live lyrics service or Windows configuration. Lyrics-provider APIs and access rules may change.

## What it does

- Searches up to **12 lyrics routes** in **FAST** and **FULL** modes (some routes aggregate or overlap other databases).
- Downloads **synchronized `.lrc`** sidecar files next to existing MP3s, when a suitable match can be verified.
- Reads existing MP3 metadata; **does not rename, delete, move or retag your MP3s**.
- Optionally converts Greeklish artist and song-title search terms to Greek using the **local AUEB G2G model** (`gr-nlp-toolkit`), while preserving the original metadata.
- Supports editable **Greek aliases** and a test/preview mode before searching.
- Uses conservative checks for **artist, title, track duration (within 3 seconds), and remix / version labels**.
- Puts uncertain results into **Review** rather than attaching potentially incorrect lyrics.
- **Skips existing `.lrc` files** and excludes tracks labeled **LIVE**.
- Retries **only the exact song/provider pair that timed out**; completed no-match searches are not retried within a run.
- Optionally remembers genuine completed no-match queries for seven days and archives each run's reports.
- Supports unattended folder processing after all startup selections are entered.

## Download

**For most Windows users:** visit [GitHub Releases](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases) and download the **Windows ZIP** and **PDF manual** attached to the latest release.

**Important:** Download and extract the ZIP before using the launcher. The source repository alone is not a Windows installer.

## Requirements

- Windows 10 or 11.
- Python **3.10 or later** available through `py` or `python`.
- Internet access to search lyrics services.
- Optional: additional space and memory for the Greek G2G model (approximately **1.2 GB** model download plus dependencies).

The Windows launcher checks for core Python packages and can install missing dependencies. See `README_FIRST.txt` and `User_Manual_Public_v2_1_4.pdf` for more information.

## Quick start — English / international music

1. Download and **extract** the Windows ZIP from Releases.
2. Double-click **`START_HERE.cmd`** (or run `./START_HERE.cmd` from PowerShell).
3. Select your MP3 folder and make the startup choices:

   | Setting | Suggested choice |
   | --- | --- |
   | Greek search | **N** |
   | MusicBrainz metadata | **N** for the first test |
   | Search mode | **FAST** first; **FULL** for tracks still missing lyrics |
   | Include subfolders | As needed |
   | Number of songs | **20** for initial testing; **A** for all |
   | Optional 7-day history | **Y** to avoid repeat completed misses; **N** for fresh searches |

4. Check downloaded `.lrc` files and the CSV reports before running your entire library.

## Optional Greeklish-to-Greek AI

For Greek songs with Latin-character titles, run the optional setup script once:

```powershell
.\SETUP_GREEK_AI.cmd
```

Or use the manual PowerShell commands:

```powershell
py -m pip install gr-nlp-toolkit
py -c "from gr_nlp_toolkit import Pipeline; nlp = Pipeline('g2g'); print(nlp('O Volos kai h Larisa einai sth Thessalia').text)"
```

The first model load may download a large model. Future runs normally reuse the local cache. The AI is **optional**; it proposes search spellings and does not change MP3 tags or guarantee correct conversions.

For Greek music, choose **Greek mode Y**, **local G2G AI Y**, **MusicBrainz N** initially, and **20 songs** for the first test. Review the preview CSV before processing a large folder. Manually reviewed corrections can go into `Greek_Aliases.csv` and take priority over AI guesses.

## Matching and safety

**Accuracy is prioritized over quantity.** A result is automatically saved only when sufficiently reliable artist/title, recording version and timing information are available. Unverified candidates are logged for review; they are **not** automatically installed alongside the MP3. Do not treat all downloaded or suggested lyric files as guaranteed correct.

Existing MP3s and `.lrc` files are preserved. Lyrics text and song metadata submitted to external search providers may be subject to their own terms and privacy policies; the optional Greek AI model itself runs locally.

## Main outputs

Reports are written into the chosen music folder, including:

- `LRC_Finder_Report_v2_1_4.csv` — per-track results
- `LRC_Finder_Provider_Details_v2_1_4.csv` — provider outcomes and response times
- `LRC_Source_Statistics_v2_1_4.csv` — per-provider statistics
- `LRC_Review_Needed.txt` and `LRC_Review_Only_v2_1_4/` — candidates requiring review
- `LRC_Not_Found.txt` — completed searches without an accepted match
- `LRC_Timeouts.txt` — interrupted/unfinished attempts
- `LRC_G2G_AI_Review_v2_1_4.csv` — Greek alternative preview when enabled
- `LRC_Run_Reports/` — archived runs

See the [PDF manual](User_Manual_Public_v2_1_4.pdf) and `REVIEW_CANDIDATES_README.txt` for details.

## LRCLIB identification

LRCLIB requires a genuine publisher contact or project URL. Edit `LRCLIB_CONTACT.txt` and use the project's actual GitHub page:

```text
https://github.com/DimitrisLai/LRC-Bulk-Finder
```

If the setting is left empty, **LRCLIB will be skipped**; other sources remain available. Follow providers' API policies, `Retry-After` restrictions, and usage terms.

## Troubleshooting

- **Window closes or Python errors:** try `Run_Diagnostics.cmd` and inspect the message.
- **HTTP 429:** a lyrics service is rate-limiting requests; the program respects cooldowns and continues where possible.
- **No match:** try FULL after FAST, review title spelling and aliases, and check the candidate report.
- **Greek conversion looks wrong:** correct `Greek_Aliases.csv` and re-run the preview.

When reporting a problem, include the program version, the startup settings, the error message and a **redacted** excerpt of the relevant CSV. Do not share private music libraries or local paths unnecessarily.

## Attribution, terms and release status

**LRC Bulk Finder — Created by Dimitris L.**

The project uses external lyrics services and third-party Python libraries, including the optional AUEB Greek language model. Credit for those independent works belongs to their respective authors. See `SOURCES_AND_CREDITS.txt` and `PUBLICATION_AND_LICENSE_NOTES.txt`.

**Licensing:** A license for the project's own source code has not yet been selected. Public repository visibility **does not automatically grant permission to redistribute or modify** the project. Third-party packages, services and lyrics have their own conditions. A suitable license and dependency review should be completed before a broader open-source release.

This software is not affiliated with Spotify, Apple Music, LRCLIB or other lyrics providers. Users are responsible for complying with applicable provider terms and rights to lyrics content.
