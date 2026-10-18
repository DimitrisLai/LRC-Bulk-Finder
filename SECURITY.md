# Security and data safety

**LRC Bulk Finder** searches for synchronized lyrics and optionally reads a large, locally installed LRCLIB SQLite database. It is released as a **Public Beta**.

## Understand what it accesses

- **Search mode (1):** may send song titles, artist names, durations and other search metadata to enabled online lyrics providers and optionally MusicBrainz. Third-party services have their own terms, privacy practices and rate limits.
- **Offline LRCLIB mode (4):** searches an existing local SQLite snapshot without making online lyrics or metadata requests during the scan. Initial database downloads and optional Greek AI installation are **separate setup actions** and may require network access.
- **Audio safety:** original MP3 audio and ID3 tags aren't intentionally modified. Existing `.lrc` sidecars are skipped; candidates are saved separately for manual review.
- **Database cleanup:** deleting a downloaded archive is different from deleting the extracted database. The cleanup tool requests explicit confirmation. Verify the selected path and maintain a separate backup if the database is important.
- **Large installations:** LRCLIB snapshots can use hundreds of GiB. Never share the full database or upload local media collections in bug reports.

## Report a vulnerability

If GitHub offers **private vulnerability reporting** for this repository, use the private reporting option in the repository's **Security** section for security-sensitive issues.

Otherwise, open a [GitHub Issue](https://github.com/DimitrisLai/LRC-Bulk-Finder/issues) **only if you can explain the problem without revealing an exploitable secret or private data**. Do not publish passwords, access tokens, private paths, personally identifying song inventories, or vulnerable-system details. Never submit real media files or full lyrics.

No specific response or patch timeline is guaranteed by this volunteer-maintained Public Beta project.

## Safe installation

- Use official files from [GitHub Releases](https://github.com/DimitrisLai/LRC-Bulk-Finder/releases).
- Inspect Windows `.cmd` and `.bat` launchers before running them.
- Install Python dependencies from trusted package indexes, and check upstream licenses.
- Avoid running as Administrator unless truly required by your own system.
- Download official SQLite snapshots only from trusted LRCLIB links.
- Test with 20 songs before allowing a long full-folder scan.

The [MIT License](LICENSE) includes a warranty disclaimer; please review the actual license terms.
