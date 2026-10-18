# Contributing to LRC Bulk Finder

Thank you for helping improve **LRC Bulk Finder**, created by Dimitris L.

This is a Windows-oriented Python tool for finding synchronized `.lrc` lyrics, with strict safeguards for artist, title, recording version, and duration. The project is published as a **Public Beta**.

## How to help

1. Check [existing issues](https://github.com/DimitrisLai/LRC-Bulk-Finder/issues) to avoid duplicates.
2. Open an issue for unexpected matches, an offline LRCLIB problem, an unavailable provider, or confusing documentation. Include the version, menu option, reproduction steps, and a **sanitized** error message.
3. Never upload copyrighted lyrics, MP3s, private music inventories, full disk paths, personal metadata or giant LRCLIB dumps as test fixtures.
4. For code changes, fork the repository, create a focused branch and open a pull request. Explain what the change does and how you tested it.
5. Add an **offline regression test** for any changed matching rule, database operation, cleanup behavior, or network error handling.
6. Keep normal searching backwards compatible where reasonable. In particular, **do not weaken** artist/title/version/duration checks without clear evidence and tests.

## Run the focused automated tests

On Windows, macOS, or Linux with Python **3.10+**, install only the test suite's direct dependencies:

```sh
python -m pip install mutagen Unidecode
python -m unittest -v TEST_OFFLINE_FOLDER_V2_1_15 TEST_CONNECT_EXISTING_DB_V2_1_15 TEST_PACKAGE_OFFLINE TEST_SAFETY_V2_1_4
```

These tests use temporary directories, small in-memory/temporary SQLite fixtures and mocked provider calls; they do **not** download the huge LRCLIB database or perform live lyrics-provider searches. The [Python tests GitHub workflow](https://github.com/DimitrisLai/LRC-Bulk-Finder/actions/workflows/tests.yml) runs the same focused set on Linux and Windows.

This is a **focused safety/feature regression suite**, not a comprehensive validation of every provider, Python combination, or Windows environment.

## Safety priorities

- Never modify MP3 contents or ID3 tags; don't overwrite an existing `.lrc`.
- Only save automatically verified lyrics; send uncertain candidates to `.candidate.lrc` for review.
- Respect provider 429 rate limiting, HTTP access restrictions and service errors.
- Option 4 must remain **offline only**; option 1 may use online providers.
- Never delete a huge local SQLite database without an explicit, unmistakable confirmation.
- Keep copyrights, author credit and third-party license notices intact.

## Licensing

The original project source is published under the [MIT License](LICENSE), **Copyright (c) 2026 Dimitris L.** Third-party libraries, lyrics, services, and LRCLIB snapshots retain their respective licenses and rights. See [PUBLICATION_AND_LICENSE_NOTES.txt](PUBLICATION_AND_LICENSE_NOTES.txt).
