LRC BULK FINDER v2.1.4  |  PUBLIC BETA  |  COMMAND-LINE EDITION
Created by Dimitris L.
===============================================================
For Windows 10/11 with Python 3.10+. See User_Manual_Public_v2_1_4.pdf.

INSTALL / START
1. Extract all ZIP contents into a new folder (do not run inside a ZIP).
2. Install Python 3.10+ if needed, including its launcher. Check: py --version
3. Optionally run SETUP_GREEK_AI.cmd for offline Greeklish-to-Greek AI.
4. IMPORTANT for LRCLIB: edit LRCLIB_CONTACT.txt, adding a real project
   HTTPS URL or contact email. Do not enter a made-up URL or email.
   If left blank, LRCLIB will be skipped and the other sources will run.
   This identifier is sent ONLY to LRCLIB; others do not receive it.
5. Double-click START_HERE.cmd or run from PowerShell: .\START_HERE.cmd
6. Answer ALL startup questions; none will appear while searching.
7. First run: choose 20 missing tracks to test before 'A' for all.

RECOMMENDED SETTINGS - INTERNATIONAL MUSIC
  Greek mode: N
  Search mode: FAST first (5 routes), then FULL (12 routes) for remaining.
  Include subfolders: Y if wanted.
  7-day NO_MATCH history: Y, or N to force fresh searches.
  Tracks: 20 for first test or A for all eligible tracks.

RECOMMENDED SETTINGS - GREEK MUSIC
  Greek mode: Y
  Local G2G AI: Y only after installing the optional model.
  MusicBrainz: N to minimize extra metadata requests.
  Search mode: FAST first; FULL for thorough follow-up.
  Include subfolders: Y if wanted.
  7-day NO_MATCH history: Y, or N to force fresh searches.
  Tracks: 20 first, then A after checking the preview.
  After Greek preview, automatically search: Y to run unattended.

OPTIONAL GREEK AI POWERSHELL SETUP
  py -m pip install gr-nlp-toolkit
  py -c "from gr_nlp_toolkit import Pipeline; nlp = Pipeline('g2g'); print(nlp('O Volos kai h Larisa einai sth Thessalia').text)"
The first model run may download roughly 1.2 GB and additional dependencies.
AI is optional; original artist/title metadata is never overwritten.

VERSION 2.1.4 IMPROVEMENTS
- True NO_MATCH only is saved in the optional 7-day search history.
- Providers returning review candidates are logged REVIEW_AVAILABLE, not NO_MATCH.
  Review candidates are NOT silently suppressed by the cache on later runs.
- Detailed provider report includes elapsed_seconds and candidate status.
- Source statistics include SAVED, REVIEW, NO_MATCH, CACHED, ERROR,
  SKIPPED and total/average seconds.
- LRC_Review_Needed.txt is new, alongside LRC_Not_Found.txt and
  LRC_Timeouts.txt. Review-only lyrics stay separate from the MP3s.
- HTTP 429 cooldowns are persisted as LRC_Provider_Cooldowns.json in the
  selected music folder, respecting a provider's Retry-After value.
- LRCLIB requires a valid public project URL or contact email to enable.

SAFETY / SEARCH RULES
- MP3s, ID3 tags and existing .lrc files are NEVER modified.
- LIVE songs are skipped (filename and ID3 title).
- Auto-save requires resolved artist/title, matching version, and
  <= 3-second source-vs-MP3 duration difference, plus plausible timed LRC.
- Unverifiable candidates go to a separate review-only folder, NOT next
  to the MP3. Candidates may be wrong; review before manually installing.
- Only actual network timeouts retry in round 2/3, only that same song
  and provider. No matches, 429, skipped, and 5xx never retry automatically.
- Existing .lrc sidecars are skipped even on future runs.
- Every run archives a separate set of reports under LRC_Run_Reports.

OUTPUT FILES (WRITTEN TO THE SELECTED MUSIC FOLDER)
  LRC_Finder_Report_v2_1_4.csv
  LRC_Finder_Provider_Details_v2_1_4.csv
  LRC_Finder_Review_v2_1_4.csv
  LRC_Source_Statistics_v2_1_4.csv
  LRC_Not_Found.txt
  LRC_Review_Needed.txt
  LRC_Timeouts.txt
  LRC_Review_Only_v2_1_4/      (only when candidates exist)
  LRC_Greek_Search_Preview_v2_1_4.csv  (Greek mode)
  LRC_G2G_AI_Review_v2_1_4.csv       (Greek mode)
  LRC_Completed_Search_History.jsonl (optional)
  LRC_Provider_Cooldowns.json         (when 429 occurs)
  LRC_Run_Reports/                   (copies from each run)

NO PERSONAL COLLECTION INCLUDED
This public ZIP includes no MP3s, no prefilled personal aliases, no
lyrics catalog, and no cached model weights.

PUBLICATION NOTES
This is a PUBLIC BETA, not fully validated across live providers or on
all Windows computers. External services may change or rate-limit requests.
Provide a real LRCLIB project/contact identity; choose a project license
before wider publication. See PUBLICATION_AND_LICENSE_NOTES.txt.
Keep v2.1.3 as backup while testing. Respect provider terms and lyrics rights.
