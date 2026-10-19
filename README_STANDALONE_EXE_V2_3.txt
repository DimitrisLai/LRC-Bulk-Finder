LRC BULK FINDER v2.3.0 - OPTIONAL STANDALONE WINDOWS GUI
PUBLIC BETA - Created by Dimitris L.

THIS IS A SEPARATE WINDOWS-ONLY PACKAGE, NOT A REPLACEMENT FOR THE
COMPLETE PYTHON/CMD DISTRIBUTION.

1) EXTRACT EVERYTHING INTO A WRITABLE FOLDER (e.g., Documents\LRCFinder).
2) KEEP THESE TWO FILES TOGETHER:
     LRC_Control_Center.exe            - the Windows GUI
     LRC_Bulk_Finder_Worker.exe        - standalone lyrics search engine
3) ALSO KEEP ALL CSV DICTIONARIES, Greek_Lexicon.sqlite3,
   LRCLIB_CONTACT.txt AND OTHER DATA FILES BESIDE BOTH EXEs.
4) Double-click LRC_Control_Center.exe. No separate Python required for
   default Greek dictionary/MusicBrainz/syncedlyrics functions.
5) Select your existing LRCLIB SQLite database file in the Saved
   searches tab; the program will not redownload or copy it.
6) Saved profiles remain in %APPDATA%\LRCBulkFinder\profiles.json.

LIMITATIONS
- The optional LOCAL G2G TRANSFORMER MODEL is NOT embedded.
  If your profile requires a locally installed G2G/AI model, use
  OPEN_CONTROL_CENTER.cmd in the full Python ZIP instead.
- MusicBrainz and online lyrics sources still require the internet,
  provider rate limits, and correct LRCLIB contact configuration.
- Never run two searches against one MP3 folder at the same time.
- Default Windows security warnings may occur for newly created,
  unsigned community applications. Verify the SHA256 from GitHub
  release; do not override organizational security policy.
- A truly new .EXE build is not externally code-signed.

SAFETY
- MP3 audio files and their ID3 tags are never written by the program.
- Existing .lrc files are not overwritten.
- Uncertain candidates remain explicitly marked [00:00.00] candidate
  after the user chooses to install one.
- The standalone GUI subprocess can be stopped; completed track/stage
  checkpoint records are fsynced so interruption recovery works.

SOURCE CODE AND PDF MANUAL:
https://github.com/DimitrisLai/LRC-Bulk-Finder/releases/tag/v2.3.0
