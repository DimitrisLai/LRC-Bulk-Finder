# Greek singer alias expansion — Greek Wikipedia source audit

**Source collected:** 23 October 2026, Greek Wikipedia category:
https://el.wikipedia.org/wiki/Κατηγορία:Έλληνες_τραγουδιστές

## Method

The generator `UPDATE_GREEK_ARTISTS_WIKIPEDIA.py` uses MediaWiki `categorymembers` with `cmcontinue` pagination; it never assumes the first 200 names constitute the entire category. All category pages below were followed to completion.

| Category | Article pages | Pagination pages |
| --- | ---: | ---: |
| Έλληνες τραγουδιστές (direct) | 386 | 2 |
| Ελληνίδες τραγουδίστριες | 247 | 2 |
| Αγγλόφωνοι τραγουδιστές από την Ελλάδα | 13 | 1 |
| Λαϊκοί τραγουδιστές | 96 | 1 |
| Έλληνες ηθοποιοί μουσικού θεάτρου | 28 | 1 |
| Έλληνες τραγουδιστές όπερας | 7 | 1 |
| Έλληνες ράπερ | 59 | 1 |
| Ελληνίδες ράπερ | 1 | 1 |
| Ρεμπέτες | 53 | 1 |
| Συμμετέχοντες στο Φεστιβάλ Τραγουδιού Θεσσαλονίκης | 33 | 1 |
| Τραγουδιστές ελαφρού τραγουδιού | 6 | 1 |
| Έλληνες ψάλτες | 22 | 1 |

**750 distinct article titles** after deduplication across these 12 categories. The Wikipedia root also contains category-tree links: the data import covers all pages in the 12 named singer-related categories, **not every nested subcategory in the entire Wikipedia tree**. Avoid claiming a complete directory of all Greek artists; articles and membership can change.

## Mapping safety

- Original `Greek_Artists_Baseline_Approved.csv`: **113 manually approved Latin-to-Greek spellings**, preserved in their original order, unchanged.
- Expanded `Greek_Artists.csv`: **730 total alias rows, including 617 additional source-linked mappings**. Same UTF-8 BOM `greeklish,greek` schema. No music files are read, copied or uploaded by the import.
- Added aliases use English titles linked from the *same Greek article* or that article's Wikidata English label. These are source-linked names, **not AI guesses**, but an English Wikipedia/Wikidata label is not a guarantee that every transliteration is how a person prefers to spell their name.
- Unmatched names, mostly already-written Latin-only stage names or pages without English labels, are **not assigned fabricated Greek names**.
- Colliding/ambiguous Latin keys are rejected. Names of disambiguation roles such as `(τραγουδιστής)` are removed from the output artist identity, but the original source page URL is retained in the audit.
- `Greek_Artists_Wikipedia_Audit.csv` provides per-article source URL, category, identity source and inclusion/review status. This file is provenance, not a runtime artist dictionary.
- The importer is repeatable: it **rebuilds from the original manually approved baseline**, not from the prior generated expansions. To manually approve an additional mapping for permanent inclusion in future refreshes, review it and append to the baseline, never assume a generated Wikipedia row is the manually approved source of truth.

## Rebuild and tests

From a source checkout run:

```bash
python UPDATE_GREEK_ARTISTS_WIKIPEDIA.py
python -m unittest TEST_WIKIPEDIA_GREEK_ARTISTS.py TEST_WIKIPEDIA_GREEK_ARTISTS_RUNTIME.py -v
```

Online rebuild requires Wikimedia API connectivity and rejects unexpectedly incomplete main or female category fetches. This feature branch's GitHub Action automates acquisition and commits both generated CSVs for review. The normal full GitHub test matrix checks old aliases and production matching.

## Existing Windows executable note

**The already published v2.9.2 ZIP remains immutable and includes its own old CSV.** This data upgrade appears in new source checkouts and later new app builds; it does not magically update an installed EXE. For the current extracted v2.9.2 standalone GUI, replacing *only* the companion `Greek_Artists.csv` with this reviewed file is possible after backing up the old CSV and restarting the app, because the program reads the CSV from its install directory at runtime.
