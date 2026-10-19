# v2.1.17 - Greeklish search quality update (Public Beta)

**Created by Dimitris L.**

## Fixed

- **Dictionary before AI:** Known spellings now use the reviewed accented word lexicon rather than allowing uncertain G2G model output to take precedence.
- **Full-title preservation:** Preserve years, punctuation and recording/version suffixes while using the dictionary.
- **English protection:** Common English titles, including `Best of Times`, are no longer transliterated into fake Greek by the local AI.
- **Artist protection:** Labels such as `2002 GR`, names with numbers, DJ/MC identifiers and mixed international credits are kept unchanged by default.
- **Cached corrections:** Known original Greeklish words can correct corresponding model-generated Greek tokens where alignment is unambiguous, without needing to throw away the local model cache.
- **Vocabulary:** The small user-editable accented `Greek_Words.csv` now covers more frequent Greek song words and variant Greeklish spellings.

## Examples

| Original | New Greek search alternative |
| --- | --- |
| `Fonazo` | `Φωνάζω` |
| `Den Ise Erotas Esi` | `Δεν είσαι έρωτας εσύ` |
| `Esy Horeveis Kai Ego Pethaino` | `Εσύ χορεύεις και εγώ πεθαίνω` |
| `2002 Nyhtes - 2025 Remastered` | `2002 Νύχτες - 2025 Remastered` |
| `Best of Times` | Remains English |

## Unchanged

- Option 2 `[00:00.00] candidate` marker and alternative rotation.
- Windows launchers, original MP3 files/ID3 tags, strict metadata/remix/duration safeguards.
- Four search modes, large optional offline LRCLIB database support and all release history.

## How to use

Extract the new Windows ZIP, run `START_HERE.cmd`, choose Option 1 and Greek mode. Run a small preview first. Manual title/artist mappings in `Greek_Aliases.csv` remain your highest-priority controls; copy your existing custom file into the new installation.

**Important limitation:** No automatic transliterator can fully disambiguate Greeklish lyrics titles or official recordings. Generated Greek is a search alternative requiring review, not a rewrite of music metadata or proof of a correct song.
