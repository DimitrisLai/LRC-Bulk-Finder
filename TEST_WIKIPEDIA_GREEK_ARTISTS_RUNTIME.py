"""Safety regression for the expanded Wikipedia-backed approved Greek artist table."""
import csv
import sys
import types
import unicodedata
import unittest
from pathlib import Path

sys.modules.setdefault("syncedlyrics",types.SimpleNamespace(search=lambda *a,**k:None))
import LRC_Bulk_Finder as engine

ROOT=Path(__file__).resolve().parent

def rows(filename):
    with (ROOT/filename).open(encoding="utf-8-sig",newline="") as fh:
        r=csv.DictReader(fh)
        assert r.fieldnames==["greeklish","greek"]
        return list(r)

class ArtistWikipediaIntegration(unittest.TestCase):
    def test_all_manual_spelling_mappings_unchanged(self):
        original=rows("Greek_Artists_Baseline_Approved.csv")
        expanded=rows("Greek_Artists.csv")
        self.assertEqual(expanded[:len(original)],original)
        self.assertEqual(len(original),113)
        self.assertGreaterEqual(len(expanded),700)

    def test_no_production_normalized_alias_collisions(self):
        seen={}
        for i,row in enumerate(rows("Greek_Artists.csv"),2):
            k=engine.normalize(row["greeklish"])
            self.assertTrue(k)
            self.assertNotIn(k,seen,f"search-key collision on CSV line {i}: {row['greeklish']}")
            seen[k]=row["greek"]

    def test_runtime_approved_artist_lookup_examples(self):
        engine.GREEK_ARTIST_ALIASES.clear()
        engine.load_curated_artists()
        wanted={
            "Giorgos Mazwnakis":"Γιώργος Μαζωνάκης",
            "Haris Alexiou":"Χάρις Αλεξίου",
            "Alkistis Protopsalti":"Άλκηστις Πρωτοψάλτη",
            "Glykeria":"Γλυκερία",
            "Anna Vissi":"Άννα Βίσση",
            "Aramis":"Άραμις",
            "Christakis":"Χρηστάκης",
        }
        for latin,greek in wanted.items():
            with self.subTest(latin=latin):
                self.assertEqual(engine.approved_artist_alias(latin),greek)

    def test_source_audit_covers_all_articles_not_only_first_200(self):
        with (ROOT/"Greek_Artists_Wikipedia_Audit.csv").open(encoding="utf-8-sig",newline="") as fh:
            r=csv.DictReader(fh)
            rows_audit=list(r)
        self.assertGreaterEqual(len(rows_audit),700)
        direct=sum("Έλληνες τραγουδιστές" in item["category"].split("|")
                   for item in rows_audit)
        female=sum("Ελληνίδες τραγουδίστριες" in item["category"].split("|")
                   for item in rows_audit)
        self.assertGreaterEqual(direct,350)
        self.assertGreaterEqual(female,200)
        self.assertTrue(all(item["source_page"].startswith("https://el.wikipedia.org/wiki/") for item in rows_audit))

if __name__=="__main__":unittest.main(verbosity=2)
