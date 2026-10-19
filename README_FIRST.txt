LRC BULK FINDER v2.3.0 - COMPLETE WINDOWS PACKAGE
Created by Dimitris L. - PUBLIC BETA

NEW: OPEN_CONTROL_CENTER.cmd  (native Windows GUI, Python 3.10+)
  - SAVE named search settings and folder profiles locally
  - TRACK live elapsed time, progress and honest per-round ETA
  - REVIEW .candidate.lrc and open matching MP3 in default audio player
  - PROMOTE one primary candidate ONLY after explicit confirmation;
    all promoted sidecars keep [00:00.00] candidate marker: NOT VERIFIED!
EXISTING: START_HERE.cmd (original full interactive CLI; no changes)
OTHER: Run_Diagnostics.cmd, existing LRCLIB DB reconnect/setup scripts.

SAFE LOCAL PROFILE DATA: %APPDATA%\LRCBulkFinder\profiles.json
CLI 13-PROMPT GUIDE, GUI DETAILS: HOW_TO_START_V2_3.txt
RELEASE NOTES: RELEASE_NOTES_V2_3.md
NEW TESTS: TEST_AUDIT_V2_3.md

A separately built standalone GUI EXE bundle may be published if
Windows packaging smoke tests pass. Python GUI is the reliable default.
NO large LRCLIB SQLite database or local G2G AI model is bundled.

---- PRIOR RELEASE NOTES ----

LRC BULK FINDER v2.2.0 - WINDOWS START HERE
Created by Dimitris L. - PUBLIC BETA

PREFERRED LAUNCHER: START_HERE.cmd
Windows Python 3.10+ required (NOT a standalone EXE).

NEW: persistent MusicBrainz metadata cache (30 days, no-match 7 days).
NEW: D=DEFAULT, S=SMART, C=CUSTOM provider ordering (after FAST/FULL).
NEW: actual verified-match provider success metrics and time per verified save.
NEW: fsync crash-tolerant per-song checkpoint with truncated-line recovery.

COMPLETE EXACT OPTION 1/5 PROMPTS: HOW_TO_START_V2_2.txt
VERSION NOTES: RELEASE_NOTES_V2_2.md
TEST COVERAGE: TEST_AUDIT_V2_2.md

CHECKPOINT: LRC_Run_Checkpoint_v2_2_0.jsonl
MUSICBRAINZ CACHE: LRC_MusicBrainz_Cache_v2_2.jsonl
STATS FILE: LRC_Provider_Performance_v2_2.csv

OPTION 4: Offline SQLite ONLY with no MusicBrainz or HTTP.
OPTION 5: Local SQLite all songs -> online misses -> true timeouts only.
Existing original MP3s/ID3, verified .lrc and candidate safety protected.

Your separately downloaded LARGE LRCLIB database is NOT bundled.
Use CONNECT_EXISTING_LRCLIB_DATABASE.cmd to reconnect without redownloading.

---- PREVIOUS VERSION NOTES ----

LRC BULK FINDER v2.1.21 - START HERE
Created by Dimitris L. - PUBLIC BETA

NEW v2.1.21: More accurate offline Greek artist/title matching,
review-candidate statuses retained across every round,
and durable auto-resume after interruption for Options 1 and 5.

RESTART WITH THE SAME SETTINGS to reuse per-song checkpoints saved as:
  LRC_Run_Checkpoint_v2_1_21.jsonl (inside selected MP3 folder)
To force completely fresh searches, rename/move this file BEFORE launch.

Historical regression tests now cover all 22 modules on Windows/Linux.
The original MP3 audio/ID3 and existing .lrc files are never overwritten.
Use Option 4 for strictly local-only search.
Use Option 5 for local ALL -> online MISSING -> timeouts ONLY.

EXACT ALL OPTIONS: HOW_TO_START_V2_1_21.txt
RELEASE NOTES: RELEASE_NOTES_V2_1_21.md
TEST AUDIT: TEST_AUDIT_V2_1_21.md
Full version has START_HERE.cmd, Run_LRC_Finder.cmd and BAT launchers.
The downloaded LARGE LRCLIB SQLite is NOT bundled. Reconnect existing DB.

---- PREVIOUS RELEASE NOTES ----

LRC BULK FINDER v2.1.20 - START HERE
Created by Dimitris L. - PUBLIC BETA

NEW OPTION 5: 1) OFFLINE LRCLIB across ALL files first,
2) ONLINE selected providers only for remaining files,
3) ONLY timed-out provider/song retries (once).
No network during Stage 1, and no double local DB checks in Stage 2.
DB must be configured or Option 5 exits safely.
Option 4 remains 100% offline-only (no MusicBrainz or HTTP).

FULL ORDERED PROMPTS: HOW_TO_START_V2_1_20.txt
Keep the existing [00:00.00] candidate behavior unchanged.
Your large LRCLIB SQLite database is reused from its existing disk location;
it is NOT copied into this program ZIP.

---- PREVIOUS RELEASE NOTES ----

LRC BULK FINDER v2.1.19 - START HERE
Created by Dimitris L. - PUBLIC BETA

NEW: Greek_Artists.csv = 113 curated artist/group name variants.
Never blindly transliterate unknown artist names using the AI.
Examples: Giorgos Alkaios -> Γιώργος Αλκαίος
          Alkinoos Ioannidis -> Αλκίνοος Ιωαννίδης
          Ditikes Sinikies -> Δυτικές Συνοικίες
          Antidrasi -> Αντίδραση
          Sexy koritsia -> Sexy κορίτσια (title)

Full, ordered test prompts: HOW_TO_START_V2_1_19.txt
Continue to use START_HERE.cmd with the extracted Windows ZIP.
Greek_Words_Expanded.csv and Greek_Lexicon.sqlite3 stay included.
All original MP3 files/ID3 tags and candidate LRCs stay unchanged.

---- PREVIOUS RELEASE NOTES ----

LRC BULK FINDER v2.1.18 - START HERE
Created by Dimitris L. - PUBLIC BETA

NEW GREEKLISH VOCABULARY
Expanded community word list: Greek_Words_Expanded.csv
Optional tiny read-only SQLite word database: Greek_Lexicon.sqlite3
Source/editor dictionary: Greek_Words.csv (your custom edits win)
Full title or artist overrides: Greek_Aliases.csv (highest priority)

IMPORTANT: This word database is NOT the large LRCLIB SQLite database.
Neither database changes your MP3 audio or ID3 tags. Original names stay.

To rebuild the small lexicon after editing the CSV files:
  python BUILD_GREEK_LEXICON_DB.py
If the SQLite is missing or stale the program uses the CSV sources.
Option 2 remains [00:00.00] candidate with alternative shifting.
Start with a 20-track Greek preview before a large search.

Detailed guide: HOW_TO_START_V2_1_18.txt

---- PREVIOUS RELEASE NOTES ----

LRC BULK FINDER v2.1.17 - START HERE
Created by Dimitris L. - PUBLIC BETA

GREEKLISH QUALITY UPDATE
The accented Greek_Words.csv dictionary now takes priority over local G2G AI.
Known examples: Fonazo -> Φωνάζω, Den Ise Erotas Esi -> Δεν είσαι έρωτας εσύ.
English titles like Best of Times remain English; 2002 GR artist label stays.
Manual Greek_Aliases.csv still takes first priority over both dictionary and AI.
The original MP3 tags and audio are never rewritten.

NEW VERSION GUIDE: HOW_TO_START_V2_1_17.txt
RELEASE NOTES: RELEASE_NOTES_V2_1_17.md

---- PREVIOUS RELEASE INSTRUCTIONS ----

LRC BULK FINDER v2.1.16 — START HERE
Created by Dimitris L. — PUBLIC BETA

NEW OPTION 2: BULK INSTALL UNVERIFIED CANDIDATES WITH VISIBLE MARKER
Promotes first Song.candidate.lrc -> Song.lrc and prepends:
  [00:00.00] candidate
Remaining Song.candidate.2.lrc -> Song.candidate.lrc;
Song.candidate.3.lrc -> Song.candidate.2.lrc, etc.
Existing .lrc, MP3 and ID3 data are never overwritten.
If lyrics are correct, remove the marker line after listening.
If wrong, delete Song.lrc and run Option 2 again to use the next candidate.
Full instructions: HOW_TO_START_V2_1_16.txt or README.md.

--- HISTORICAL NOTES ---
LRC BULK FINDER v2.1.15 — START HERE
Created by Dimitris L. — PUBLIC BETA

NEW: OFFLINE LRCLIB ONLY (OPTION 4) — SEARCH ANY FOLDER.
If you have downloaded the huge LRCLIB SQLite snapshot previously,
run CONNECT_EXISTING_LRCLIB_DATABASE.cmd ONCE to point at it.
NO NEW DOWNLOAD, NO DATABASE COPY OR EXTRACTION.

Double-click START_HERE.cmd and choose:
1 = Normal full lyrics searching (offline LRCLIB first; online other providers)
2 = Promote reviewed .candidate.lrc files (offline)
3 = Catch-up from a previous LRCLIB queue
4 = Search ANY MP3 folder using ONLY installed offline LRCLIB SQLite (NO internet)

For step-by-step Windows choices: HOW_TO_START_V2_1_15.txt
Detailed new features: CHANGES_V2_1_15.txt

---- Previous release notes ----
LRC BULK FINDER v2.1.15 — IMPORTANT NEW OPTION 4
Scan any selected directory using ONLY your existing offline LRCLIB database.
No catch-up queue or internet required. Run CONNECT_EXISTING_LRCLIB_DATABASE.cmd
once to connect a pre-installed .sqlite3 file WITHOUT copying/downloading it.
See HOW_TO_START_V2_1_15.txt and CHANGES_V2_1_15.txt.

LRC BULK FINDER v2.1.14 | PUBLIC BETA | Created by Dimitris L.

IMPORTANT: Optional automated OFFLINE LRCLIB database installer (not bundled).
The official database was nearly 250 GB uncompressed in August 2026.
Normal searching does not require an offline database. See HOW_TO_START_V2_1_14.txt.

LRC BULK FINDER v2.1.14 | PUBLIC BETA | COMMAND-LINE EDITION
Created by Dimitris L.
===============================================================
Windows 10/11. Python 3.10 or newer. Local AI is optional.

For step-by-step offline LRCLIB setup, read HOW_TO_START_V2_1_14.txt.
Optional large offline LRCLIB: run SETUP_LRCLIB_DATABASE.cmd for automatic official download (requires 350 GiB free).
Optional safe cleanup afterwards: run CLEANUP_LRCLIB_DATABASE.cmd; choose archive only, database only, both, or cancel.

QUICK START
1. Extract the ZIP fully to a new folder (never run directly from inside the ZIP).
2. Double-click START_HERE.cmd or run .\START_HERE.cmd in PowerShell.
3. Choose 1 (SEARCH), 2 (PROMOTE candidates) or 3 (LRCLIB-only catch-up), then select the MP3 folder.
4. First test: choose 20 missing songs. Run all later if results are acceptable.
5. Your MP3 files, ID3 tags and existing LRC sidecars are never modified.

GREEK / GREEKLISH
  Greek mode: Y. If installed, optional G2G AI: Y. MusicBrainz: optional.
  Optional model setup: SETUP_GREEK_AI.cmd; command details in INSTALL_GREEK_AI_COMMANDS.txt.
  The model runs locally and creates alternative search spellings without changing the MP3 tags.

INTERNATIONAL / NON-GREEK
  Greek mode: N. MusicBrainz: N when artist/title tags are already accurate (faster),
  or Y to look for alternative metadata spellings (slower).
  MusicBrainz Picard is NOT required. It is a separate tagging application.

FAST / FULL
  FAST: 5 providers for a quicker first pass.
  FULL: 12 routes, some overlapping sources; slower and more review candidates.
  FULL is particularly useful as a second pass on songs still without an LRC.

SAME MATCHING / RETRY SAFEGUARDS AS v2.1.5
  Automatically save only verified artist/title, correct recording version and <=3s duration gap.
  Unverified lyrics are saved beside each MP3 as .candidate.lrc, never installed as approved .lrc.
  Existing LRC sidecars are skipped. LIVE tracks are excluded by filename or ID3 title.
  Retry rounds 2/3 ONLY for network timeouts on the exact timed-out song AND provider.
  NO_MATCH, SKIPPED, HTTP 429, HTTP 5xx and generic errors do not trigger retries.
  HTTP 429 cooldowns are saved and honored across restarts in the selected music folder.
  A 7-day cache can skip only completed NO_MATCH searches; review results stay searchable.

NEW — PROVIDER DIAGNOSTICS
  Provider startup availability displays READY (not yet contacted), DISABLED, or UNAVAILABLE.
  Each song shows provider outcome, actual HTTP status when exposed, and elapsed time.
  HTTP 200 = HTTP request succeeded; it does NOT necessarily mean lyrics were found.
  HTTP 404 = endpoint/resource had no result; HTTP 401/403 = authorization/access problem.
  HTTP 429 = rate limit; program respects provider cooldown (do NOT bypass it).
  HTTP 5xx = service error. NETWORK_TIMEOUT is not an HTTP status code.
  Some external libraries hide HTTP status codes; the program displays UNKNOWN instead of guessing.
  A source disabled halfway through a run is still shown on later songs as SKIPPED with its reason.

NEW REPORTS — written to your selected MP3 folder
  LRC_HTTP_Diagnostics_v2_1_14.csv: one row per HTTP request/status or no-request reason.
     Includes round, provider, endpoint host/path (NEVER the query string), status,
     reason and request time.
  LRC_Finder_Provider_Details_v2_1_14.csv: one row per song/provider, provider outcome,
     HTTP status summary and request count.
  LRC_Finder_Report_v2_1_14.csv: song-level search results.
  LRC_Finder_Review_v2_1_14.csv: uncertain candidates and rejection explanations.
  LRC_Source_Statistics_v2_1_14.csv: results and elapsed time by provider.
  LRC_Not_Found.txt / LRC_Timeouts.txt / LRC_Review_Needed.txt: final song lists.
  LRC_Run_Reports/: archived copies of report files for each run.

OPTIONAL LRCLIB CLIENT ID
  The public project's official URL is included in LRCLIB_CONTACT.txt.
  LRCLIB may rate-limit access independently of client ID; a configured URL does not guarantee access.

PUBLIC BETA / DOCUMENTATION
  This is an installer update for testing. The version-specific English PDF manual is available separately for public release.
  See CHANGES_V2_1_14.txt and HOW_TO_START_V2_1_14.txt for current setup.
  External lyrics sources and libraries have separate licenses and terms.
  This ZIP contains no personal song lists, MP3s, lyrics or cached AI model.


v2.1.7 — LRCLIB PRIORITY & RECOVERY
  LRCLIB is queried first in FAST and FULL, provided its real client URL is
  configured and an HTTP 429 cooldown is not active.
  HTTP 503 is a temporary provider-wide recovery (60s, 120s, etc., capped at
  10 minutes); another song can probe after cooldown. It does NOT cause rounds
  2/3, because those are reserved ONLY for real network timeouts.
  HTTP 429 remains protected by the persistent cooldown. Do not circumvent it.
  BetterTTML HTTP 401 is now correctly treated as unauthorized, not NO_MATCH,
  and the route stops for the run instead of wasting hundreds of requests.
  Existing LRC and MP3 protection, candidate sidecars, reports and all 12
  routes remain in place. No new PDF for this interim test version.


v2.1.8 — CANDIDATE SIDECARS AND SAFE PROMOTION
  The launch menu offers 1 = normal lyrics search or 2 = promote .candidate.lrc to .lrc.
  Search stores MP3NAME.candidate.lrc beside MP3NAME.mp3, without changing audio.
  If several sources offer different lyrics, extras are stored as
  MP3NAME.candidate.2.lrc, MP3NAME.candidate.3.lrc, etc. They remain UNAPPROVED.
  A song's approved MP3NAME.lrc is never overwritten. Existing candidate files
  are also never overwritten on repeat searches.
  Promotion scans the selected directory and optionally subdirectories,
  previews the first five filenames, and requires explicit confirmation.
  It only promotes the primary MP3NAME.candidate.lrc when matching MP3 exists,
  the candidate is timestamped LRC and there is no existing approved .lrc.
  Alternate .candidate.2.lrc (etc.) stay untouched; choose manually after
  reviewing if the primary was wrong. Results go to
  LRC_Candidate_Promotion_Report_v2_1_8.csv.
  WARNING: Promotion means YOU ACCEPT the candidate. The script does not verify
  that the lyrics or timings actually match the audio. Listen and check first.
  Prior .candidate.txt files from v2.1.6/2.1.7 remain in their legacy folder.
  This menu deliberately does NOT attempt to guess their MP3 identities.


v2.1.9 — CONSERVATIVE LRCLIB RELIABILITY PATCH (INTERIM BETA)
  1) Existing LRCLIB /api/search requests, order, strict matching, FAST/FULL
     and three timeout-only rounds are unchanged by default.
  2) The program now honors the LRCLIB 503 Retry-After response with an extra
     safe minimum 5 seconds after overload. Without Retry-After it retains
     60/120/.../600-second fallback. 429 persists cooldown across restarts.
  3) LRCLIB sends requests sequentially with at least a 500ms finished-to-next-
     request gap, in addition to the previously used 2.4-second pacing.
  4) NEW OPTIONAL startup question after selecting how many songs:
       Optional LRCLIB exact-signature fallback after existing searches? [y/N]
     DEFAULT: N. Y adds at most ONE /api/get request after all existing
     /api/search attempts failed to find a verified match, and only if valid
     artist/title and a duration between 1 and 3600 seconds are available.
     This can make FULL scans longer and adds server load; for the first test
     on a huge library, choose N. All exact results pass the SAME strict
     song identity, version and duration checks before auto-saving.
  5) A normal SEARCH now writes a separate:
       LRC_LRCLIB_Catchup_Queue_v2_1_9.csv
     listing songs whose LRCLIB coverage was incomplete due to HTTP 503/429
     or the resulting provider cooldown. Existing queue entries are kept
     across smaller later runs unless successfully checked or now have .lrc.
     This list does NOT automatically cause extra retries.
  6) NEW STARTUP ACTION 3 (manual, separate from automatic timeout retries):
       LRCLIB-only catch-up
     Select SAME music collection root and read that versioned queue. It
     contacts ONLY LRCLIB, never other lyrics providers; it skips existing
     .lrc and LIVE tracks and creates normal safe review candidate sidecars.
     It respects any persistent 429 cooldown, pauses/stops on 503, and writes
       LRC_LRCLIB_Catchup_Report_v2_1_9.csv
     Already accepted .lrc, original MP3s, and normal search reports are
     never overwritten. This step needs explicit user confirmation.

For your full-folder overnight run: choose 1 SEARCH, optional exact lookup N
unless you deliberately want to test the extra request (start with 20 songs).
After the run, you may choose 3 to cover only those songs LRCLIB missed.
Do NOT delete provider 429 cooldown files to force additional requests.


v2.1.10 — FIRST-ATTEMPT COVERAGE & RECOVERY
  Before "Include subfolders" the SEARCH workflow asks:
  "Wait for temporary provider recovery before EACH first attempt? [Y/n]"
    Y (default): wait before contacting the temporarily unavailable provider
      for EACH NEW SONG; can take MANY HOURS if a server keeps returning 503.
    N: faster; provider is marked SKIPPED for songs encountered during its
      recovery interval, with missing coverage visible in the reports.
  HTTP 503 is not automatically retried for the same song: the next song gets
  its own first request after cooldown. HTTP 401/403 access denied stops that
  provider; HTTP 429 respects its original persisted cooldown.
  LiriQo is no longer permanently disabled after two ordinary server errors.
  New LRC_First_Attempt_Coverage_v2_1_14.csv tells whether each source
  actually received a request for each selected song. External libraries may
  hide actual HTTP traffic, which is explicitly marked UNKNOWN.
  Option 3 automatically imports v2.1.9's existing LRCLIB catch-up queue,
  preserving the original, and waits between queued songs during 503 recovery.
  Use CTRL+C if repeated server 503s make waiting unproductive; reports and
  outstanding catch-up queue entries remain available for a later run.
  Do not use this mode to bypass HTTP 429, access restrictions or external
  provider terms. Provider availability is not guaranteed.
