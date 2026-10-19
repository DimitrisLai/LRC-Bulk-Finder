# LRC Bulk Finder v2.1.19 — Correct Greek Artist Names

Public Beta · Created by Dimitris L.

## What's new

- **113 curated Latin-to-Greek artist/group spellings** in `Greek_Artists.csv`. This file is separate from the general `Greek_Words.csv` and `Greek_Words_Expanded.csv` vocabulary and has no private MP3 names or paths.
- **Full artist identity first.** Reviewed artist aliases override unpredictable letter-by-letter Greeklish AI outputs. Unknown artist names stay in their original script instead of being presented as verified Greek.
- **Correct query priority.** Original artist/title first, original title plus approved Greek artist second, and the Greek-title-plus-approved-Greek-artist combination third if available.
- **Keep bilingual titles intact.** `Sexy koritsia` → `Sexy κορίτσια` (not `Σεξυ κορίτσια`); similarly preserve known English words mixed into Greeklish.
- **Handle verified collaboration credits** (commas, ampersands, and feat.) without guessing unknown artist names.
- **User overrides always win.** `Greek_Aliases.csv` remains your personal full-title/artist override file.
- More accented Greek song-title words including `Κύματα`, `Μεσάνυχτα`, `Σαββάτου`, and `Αντίδραση`.

## Your examples

| Original | Canonical Greek artist |
| --- | --- |
| Giorgos Alkaios | Γιώργος Αλκαίος |
| Alkinoos Ioannidis | Αλκίνοος Ιωαννίδης |
| Alinoos Ioannidis (typo in tags) | Αλκίνοος Ιωαννίδης |
| Antidrasi | Αντίδραση |
| Ditikes Sinikies | Δυτικές Συνοικίες |

## Safety

The original MP3 files/ID3 tags are **never rewritten**; English/brand names and unknown names are preserved. This only changes search variants and review previews. The strict recording/duration/version checks remain. Option 2's `[00:00.00] candidate` promotion remains unchanged. Prior releases are retained separately.

## Testing and installation

Run the included `TEST_GREEK_ARTIST_QUALITY_V2_1_19.py` through the repository CI on Windows and Linux; it checks exact provided names, mixed titles, two-query LRCLIB ordering, unknown artist behavior, custom overrides, and MusicBrainz precedence.

Extract the full **Windows v2.1.19 release ZIP**, double-click `START_HERE.cmd`, choose Option 1, Greek Y, local G2G AI Y if installed, MusicBrainz Y, FULL, recovery wait N, recursive Y, cached NO_MATCH N, sample 20, exact LRCLIB fallback Y, then preview-only N before the first lyric search. Read `HOW_TO_START_V2_1_19.txt` for the exact 12 prompts.
