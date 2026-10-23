# Next update candidate — Greek song-title vocabulary, artists, search presets

**Status:** Development branch only. Do not describe this branch as a published
Windows release or an installed EXE update until a separately versioned,
fully tested standalone ZIP is published.

## A. Greek songs vocabulary — title words, not copyrighted song lyrics

Source: https://el.wikipedia.org/wiki/Κατηγορία:Ελληνικά_τραγούδια

- `UPDATE_GREEK_SONG_WORDS_WIKIPEDIA.py` queries the category and its linked
  song subcategories, traversing **every MediaWiki `cmcontinue` page** for
  each visited category. It records the number of continuation pages per
  category and stops with an error rather than silently truncating a too-large
  or unexpectedly deep tree.
- Takes only **article titles** and extracts standalone Greek words. It does
  **not** download or reproduce lyric text from Wikipedia, or extract words
  from full lyric pages. Songs outside the Wikipedia categories are not included.
- `Greek_Words_Wikipedia.csv` contains derived Latin-to-Greek word *suggestions*.
  Their Greek spelling is evidenced by the song titles. The Greeklish spelling
  is a deterministic approximation and **not verified romanization**. Short
  words and conflicting or unsupported aliases are rejected.
- `Greek_Song_Title_Words_Audit.csv` records source song article URLs,
  title/category provenance and decisions per word, including rejections.
- In `LRC_Bulk_Finder.py`, the auto-sourced vocabulary is loaded first, then
  `Greek_Words_Expanded.csv`, then manually approved `Greek_Words.csv`.
  Existing approved spellings therefore win. Search results remain unverified
  `.candidate.lrc` files requiring human review.
- The optional `Greek_Lexicon.sqlite3` builder fingerprints **all three**
  vocabulary CSV files and rejects a stale database. CSV-only fallback still
  works. New Windows releases must ship the new CSV and rebuilt SQLite;
  historical v2.9.2 artifacts stay unchanged.
- No MP3, user filenames, private data, or copyrighted full song lyrics are
  transferred to Wikipedia or GitHub as part of the importer.

## B. Greek singer names

Source: https://el.wikipedia.org/wiki/Κατηγορία:Έλληνες_τραγουδιστές

The earlier artist-expansion branch is included as the base of this feature.
It preserves **113 manually approved** Greek singer mappings and adds
**617 source-linked** Greek Wikipedia/English identity mappings, totaling
**730** rows in `Greek_Artists.csv` at initial branch creation.
Audited source: `Greek_Artists_Wikipedia_Audit.csv` and
`GREEK_ARTISTS_WIKIPEDIA_AUDIT.md`. Data refresh may change counts.
Not all linked English names are personally approved Greeklish transliterations;
ambiguous name collisions are excluded.

## C. Search presets

The combobox is deliberately **ordered**, not alphabetically. All Greek options
appear together first, followed by all international/foreign options. Within
each group, broadest coverage appears near the top. Exceptions are labelled
for offline-only and separately installed local AI.

| Order | Greek presets | Scope |
|---|---|---|
| 1 | Greek Night Search — Maximum Coverage | All; offline first; full online sources; retry/recovery |
| 2 | Greek FULL — Offline First | All; SQLite first, full online fallback |
| 3 | Greek FULL — Online ALL | All; full online sources, no SQLite needed |
| 4 | Greek Local AI — FULL | All; optional separately installed G2G model (not bundled in EXE) |
| 5 | Greek FULL — Online 100 Songs | First 100 eligible; full online |
| 6 | Greek FAST — Online ALL | All; fewer sources |
| 7 | Greek Quick Test — 20 Songs | 20; full offline-first / online fallback |
| 8 | Greek FAST — Online 20 Songs | 20; fast online only |
| 9 | Greek OFFLINE ONLY | All; configured local SQLite only |

| Order | Foreign / international presets | Scope |
|---|---|---|
| 1 | International MAX — Overnight ALL | All; full online + recovery waits |
| 2 | International FULL — Online ALL | All; full online |
| 3 | International FULL — Online 100 Songs | First 100; full online |
| 4 | International FAST — Online ALL | All; quick provider set |
| 5 | International FAST — 20 Songs | 20; quick provider set |
| 6 | International OFFLINE ONLY | All; configured local SQLite only |

The six original preset names remain present for old workflows. Presets **only
fill the editor settings**; they do not overwrite saved profiles, start an
unattended search on selection, or automatically schedule a scan.
English/Greek UI translations are additive.

## Build and QA gates

```bash
python -m unittest TEST_WIKIPEDIA_GREEK_SONG_WORDS.py -v
python UPDATE_GREEK_SONG_WORDS_WIKIPEDIA.py
python BUILD_GREEK_LEXICON_DB.py
python -m unittest discover -p 'TEST_*.py' -v
```

The Wikipedia API is required only for refreshing the generated song-title
CSV/audit, not for running the app. Review generated Greeklish suggestions
before shipping in a new version.

**Release:** Do not modify immutable v2.9.2 assets; the next standalone
packaging workflow must include `Greek_Artists.csv`,
`Greek_Words_Wikipedia.csv`, `Greek_Words_Expanded.csv`, `Greek_Words.csv`
and a rebuilt `Greek_Lexicon.sqlite3` together with bilingual user guides.
