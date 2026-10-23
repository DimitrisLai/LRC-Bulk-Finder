"""Offline tests: all MediaWiki song pages, collisions, priority and preset order."""
from __future__ import annotations
import csv
import tempfile
import types
import sys
import unittest
from pathlib import Path

import UPDATE_GREEK_SONG_WORDS_WIKIPEDIA as wiki
import search_profiles


class SongWordImportTests(unittest.TestCase):
    def test_page_and_subcategory_continuation(self):
        calls = []
        def fake(_url, params):
            self.assertEqual(params["cmtype"], "page|subcat")
            calls.append(params.get("cmcontinue"))
            if not params.get("cmcontinue"):
                return {
                    "query": {"categorymembers": [
                        {"title": "Μαύρα μάτια (τραγούδι)", "ns": 0},
                        {"title": "Κατηγορία:Ελληνικά παραδοσιακά τραγούδια", "ns": 14},
                    ]},
                    "continue": {"cmcontinue": "page-two"},
                }
            return {"query": {"categorymembers": [
                {"title": "Φεγγαράκι μου λαμπρό", "ns": 0},
            ]}}
        songs, subs, count = wiki.api_members(wiki.ROOT, api=fake)
        self.assertEqual(count, 2)
        self.assertEqual(calls, [None, "page-two"])
        self.assertEqual(len(songs), 2)
        self.assertIn("Ελληνικά παραδοσιακά τραγούδια", subs)

    def test_category_recursion(self):
        def fake(_url, params):
            category = params["cmtitle"]
            if category.endswith(wiki.ROOT):
                return {"query": {"categorymembers": [
                    {"title": "Μαύρα μάτια", "ns": 0},
                    {"title": "Category:Child songs", "ns": 14},
                ]}}
            self.assertTrue(category.endswith("Child songs"))
            return {"query": {"categorymembers": [
                {"title": "Χάρτινο Φεγγαράκι", "ns": 0},
            ]}}
        songs, pages = wiki.collect(api=fake)
        self.assertEqual(len(songs), 2)
        self.assertEqual(len(pages), 2)
        self.assertIn("Χάρτινο Φεγγαράκι", songs)

    def test_cyclic_continuation_fails(self):
        def fake(_url, params):
            return {"query": {"categorymembers": []},
                    "continue": {"cmcontinue": "repeat"}}
        with self.assertRaisesRegex(ValueError, "Cyclic"):
            wiki.api_members(wiki.ROOT, api=fake)

    def test_song_title_tokens_not_lyrics_or_artist_category(self):
        words = list(wiki.title_words("Αγάπη Που 'γινες Δίκοπο Μαχαίρι (τραγούδι)"))
        self.assertIn("αγάπη", words)
        self.assertIn("δίκοπο", words)
        self.assertNotIn("τραγούδι", words)
        self.assertNotIn("που", words)  # short, risky words are curated separately

    def test_deterministic_romanization(self):
        self.assertEqual(wiki.romanize("αγάπη"), "agapi")
        self.assertEqual(wiki.romanize("καλοκαίρι"), "kalokairi")
        self.assertEqual(wiki.romanize("φεγγάρι"), "fengari")

    def test_manual_priorities_and_conflicts(self):
        songs = {
            "Αγάπη στο φεγγάρι": {wiki.ROOT},
            "Αγάπη στην καρδιά": {wiki.ROOT},
            "Όραμα": {wiki.ROOT},
            "Οραμα": {wiki.ROOT},
        }
        known = {"agapi": "αγάπη", "kardia": "καρδιά"}
        proposed, audit = wiki.generate(songs, known)
        suggestions = dict(proposed)
        self.assertNotIn("agapi", suggestions)
        self.assertIn("fengari", suggestions)
        self.assertNotIn("orama", suggestions)
        self.assertIn("ambiguous-key-skipped", {r[-1] for r in audit})
        self.assertIn("existing-approved", {r[-1] for r in audit})

    def test_generated_words_are_runtime_visible_but_curated_words_win(self):
        sys.modules.setdefault('syncedlyrics', types.SimpleNamespace(search=lambda *args, **kw: None))
        import LRC_Bulk_Finder as app
        previous = app.GREEK_WORDS.copy()
        try:
            app.GREEK_WORDS.clear()
            app.load_greek_words()
            with Path(wiki.__file__).with_name(wiki.TITLE_CSV).open(
                    encoding="utf-8-sig", newline="") as stream:
                suggestions = list(csv.DictReader(stream))
            self.assertGreaterEqual(len(suggestions), 50)
            for item in suggestions[:15]:
                self.assertEqual(app.GREEK_WORDS[item["greeklish"]], item["greek"])
            # A manually curated entry already present in the old dictionaries.
            self.assertEqual(app.GREEK_WORDS["fonazo"], "φωνάζω")
            self.assertEqual(app.GREEK_WORDS["agapi"], "αγάπη")
        finally:
            app.GREEK_WORDS.clear()
            app.GREEK_WORDS.update(previous)

    def test_generator_preserves_on_partial_error(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("Greek_Words.csv", "Greek_Words_Expanded.csv"):
                (root / name).write_text("greeklish,greek\nagapi,αγάπη\n", encoding="utf-8")
            output = root / wiki.TITLE_CSV
            output.write_bytes(b"OLD PUBLIC DATA")
            def fake(_url, _params):
                return {"query": {"categorymembers": []}}
            with self.assertRaisesRegex(ValueError, "No Wikipedia"):
                wiki.build(root, api=fake)
            self.assertEqual(output.read_bytes(), b"OLD PUBLIC DATA")


class PresetCoverageTests(unittest.TestCase):
    def test_greek_then_international_order(self):
        names = list(search_profiles.PRESET_TEMPLATES)
        kinds = [search_profiles.PRESET_TEMPLATES[n]["greek"] for n in names]
        self.assertTrue(kinds[0])
        self.assertFalse(kinds[-1])
        self.assertEqual(kinds, sorted(kinds, reverse=True))
        self.assertGreaterEqual(len(names), 14)
        self.assertEqual(len(set(names)), len(names))

    def test_names_have_unique_descriptions(self):
        self.assertEqual(set(search_profiles.PRESET_TEMPLATES),
                         set(search_profiles.PRESET_DESCRIPTIONS))
        self.assertTrue(all(search_profiles.PRESET_DESCRIPTIONS.values()))

    def test_presets_validate_with_existing_profile_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            for name, template in search_profiles.PRESET_TEMPLATES.items():
                with self.subTest(name=name):
                    p = search_profiles.preset_profile(name, folder=folder)
                    self.assertEqual(p["greek"], template["greek"])
                    self.assertEqual(p["limit"], template["limit"])
                    self.assertFalse(p["local_ai"] and not p["greek"])

    def test_foreign_never_turns_on_greek_or_local_ai(self):
        for name, values in search_profiles.PRESET_TEMPLATES.items():
            if name.startswith("International"):
                self.assertFalse(values["greek"])
                self.assertFalse(values["local_ai"])

    def test_exhaustive_precedes_fast_and_offline(self):
        names = list(search_profiles.PRESET_TEMPLATES)
        self.assertLess(names.index("Greek Night Search — Maximum Coverage"),
                        names.index("Greek FAST — Online 20 Songs"))
        self.assertLess(names.index("International MAX — Overnight ALL"),
                        names.index("International FAST — 20 Songs"))


if __name__ == "__main__":
    unittest.main()
