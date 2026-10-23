#!/usr/bin/env python3
"""Collect WORDS FROM GREEK SONG TITLES (not song lyrics) across ALL category pages.

Wikipedia category pages and their song-title subcategories are followed using
MediaWiki cmcontinue, with cycle and size bounds. Only Unicode Greek words in
article titles are collected. Their Latin keys are deterministic, conservative
Greeklish *suggestions*, not professionally verified romanizations.

The generated lexicon is loaded at the LOWEST priority. Manually approved word
spellings remain authoritative. Ambiguous keys, short words, and collisions
with approved keys are never imported. Every new mapping is UNVERIFIED and
must only help find candidate lyrics that still require manual review.
"""
from __future__ import annotations
import argparse
import csv
import io
import re
import unicodedata
from collections import deque
from pathlib import Path
from urllib.parse import quote

from UPDATE_GREEK_ARTISTS_WIKIPEDIA import _api, API, key as normalize_key

ROOT = "Ελληνικά τραγούδια"
MAX_DEPTH = 5
MAX_CATEGORIES = 100
MAX_ARTICLES = 4000
MAX_PAGES_PER_CATEGORY = 50
PAGE_SIZE = 200
GREEK_WORD = re.compile(r"[\u0370-\u03ff\u1f00-\u1fff]+")
QUALIFIER = re.compile(r"\s*\([^)]*\)\s*$")
TITLE_CSV = "Greek_Words_Wikipedia.csv"
AUDIT_CSV = "Greek_Song_Title_Words_Audit.csv"
HEADERS = ("greeklish", "greek")
AUDIT_HEADERS = ("greeklish", "greek", "source_title", "source_page",
                 "category", "status")
SINGLE = {
    "α":"a","β":"v","γ":"g","δ":"d","ε":"e","ζ":"z","η":"i",
    "θ":"th","ι":"i","κ":"k","λ":"l","μ":"m","ν":"n","ξ":"x",
    "ο":"o","π":"p","ρ":"r","σ":"s","ς":"s","τ":"t","υ":"y",
    "φ":"f","χ":"x","ψ":"ps","ω":"o",
}
PAIRS = {
    "αι":"ai","ει":"ei","οι":"oi","ου":"ou","υι":"yi",
    "μπ":"mp","ντ":"nt","γκ":"gk","γγ":"ng","τσ":"ts","τζ":"tz",
    "αυ":"av","ευ":"ev","ηυ":"iv",
}


def api_members(category, api=_api):
    """Read every page and subcategory, following each continuation token."""
    names, children, seen = set(), set(), set()
    token = None
    page_count = 0
    while True:
        params = {"action":"query", "list":"categorymembers",
                  "cmtitle":"Category:"+category, "cmtype":"page|subcat",
                  "cmlimit":PAGE_SIZE}
        if token:
            params["cmcontinue"] = token
        response = api(API, params)
        for row in response.get("query", {}).get("categorymembers", []):
            name = row.get("title", "")
            if row.get("ns") == 0 and name:
                names.add(name)
            elif row.get("ns") == 14 and name.startswith(("Κατηγορία:", "Category:")):
                children.add(name.split(":", 1)[1])
        page_count += 1
        if page_count > MAX_PAGES_PER_CATEGORY:
            raise ValueError("Wikipedia continuation bound exceeded")
        token = response.get("continue", {}).get("cmcontinue")
        if not token:
            break
        if token in seen:
            raise ValueError("Cyclic Wikipedia continuation")
        seen.add(token)
    return names, children, page_count


def collect(api=_api):
    """Bounded recursive walk of the named song category and its subcategories."""
    queue = deque([(ROOT, 0)])
    visited = set()
    pages = {}
    songs = {}
    while queue:
        category, depth = queue.popleft()
        if category in visited:
            continue
        if len(visited) >= MAX_CATEGORIES:
            raise ValueError("Too many Wikipedia song subcategories; audit required")
        visited.add(category)
        names, children, count = api_members(category, api)
        pages[category] = count
        for title in names:
            songs.setdefault(title, set()).add(category)
        if len(songs) > MAX_ARTICLES:
            raise ValueError("Too many song titles; manual scope review required")
        if children and depth >= MAX_DEPTH:
            raise ValueError("Subcategory depth exceeded; incomplete traversal refused")
        for child in sorted(children):
            if child not in visited:
                queue.append((child, depth + 1))
    return songs, pages


def title_words(title):
    """Use title text only. Never download or store song article/lyric content."""
    unqualified = QUALIFIER.sub("", title)
    for raw in GREEK_WORD.findall(unqualified):
        word = unicodedata.normalize("NFC", raw.lower())
        # Do not fabricate identities from short particles or Greeklish lookalikes.
        if len(word) >= 4 and word.isalpha():
            yield word


def romanize(word):
    """Conservative deterministic Greeklish *candidate* (not official Latin)."""
    decomposed = unicodedata.normalize("NFD", word.lower())
    bare = "".join(c for c in decomposed if not unicodedata.combining(c))
    out = []
    i = 0
    while i < len(bare):
        pair = bare[i:i+2]
        if pair in PAIRS:
            out.append(PAIRS[pair])
            i += 2
        elif bare[i] in SINGLE:
            out.append(SINGLE[bare[i]])
            i += 1
        else:
            return ""
    return "".join(out)


def approved_words(root):
    """Existing dictionaries always take precedence over automatic candidates."""
    known = {}
    for filename in ("Greek_Words_Expanded.csv", "Greek_Words.csv"):
        with (root / filename).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if tuple(reader.fieldnames or []) != HEADERS:
                raise ValueError("Unexpected dictionary schema: " + filename)
            for row in reader:
                latin = normalize_key(row["greeklish"])
                if latin and re.fullmatch(r"[a-z]+", latin):
                    known[latin] = row["greek"].strip()
    return known


def generate(songs, known):
    """Allow only unambiguous, new Greek word spellings; audit all decisions."""
    source = {}
    for title, categories in sorted(songs.items()):
        for word in title_words(title):
            source.setdefault(word, (title, "|".join(sorted(categories))))
    proposed = {}
    conflict = set()
    audits = []
    for greek, (title, category) in sorted(source.items()):
        latin = romanize(greek)
        if not re.fullmatch(r"[a-z]{5,}", latin):
            status = "short-or-unsupported"
        elif latin in known:
            status = "existing-approved" if unicodedata.normalize("NFC", known[latin].lower()) == greek else "collision-approved-skipped"
        elif latin in conflict:
            status = "ambiguous-key-skipped"
        elif latin in proposed and proposed[latin] != greek:
            conflict.add(latin)
            proposed.pop(latin, None)
            status = "ambiguous-key-skipped"
        else:
            proposed[latin] = greek
            status = "generated-unverified"
        url = "https://el.wikipedia.org/wiki/" + quote(title.replace(" ", "_"))
        audits.append([latin, greek, title, url, category, status])
    # Reclassify all collisions, including the first article with that key.
    for row in audits:
        if row[0] in conflict:
            row[-1] = "ambiguous-key-skipped"
    return sorted(proposed.items()), audits


def csv_text(columns, rows):
    data = io.StringIO(newline="")
    writer = csv.writer(data, lineterminator="\n")
    writer.writerow(columns)
    writer.writerows(rows)
    return "\ufeff" + data.getvalue()


def build(root, api=_api):
    root = Path(root).resolve()
    songs, pages = collect(api)
    if not songs or ROOT not in pages:
        raise ValueError("No Wikipedia song article titles; refusing an empty refresh")
    proposed, audit = generate(songs, approved_words(root))
    if not proposed:
        raise ValueError("No usable new words; existing data preserved")
    (root / TITLE_CSV).write_text(csv_text(HEADERS, proposed), encoding="utf-8")
    (root / AUDIT_CSV).write_text(csv_text(AUDIT_HEADERS, audit), encoding="utf-8")
    print(f"Read {sum(pages.values())} pagination pages in {len(pages)} categories, "
          f"{len(songs)} unique song titles; generated {len(proposed)} unverified words.")
    for category, number in sorted(pages.items()):
        print(f"  {category}: {number} continuation page(s)")
    return len(songs), len(pages), len(proposed)


def main():
    parser = argparse.ArgumentParser(description="Collect Greek Wikipedia song-title word vocabulary")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    build(args.root)


if __name__ == "__main__":
    main()
