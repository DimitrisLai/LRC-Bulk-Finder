"""Offline tests for Wikipedia category pagination and safe public artist alias import."""
from pathlib import Path
import csv
import tempfile
import unittest
import UPDATE_GREEK_ARTISTS_WIKIPEDIA as wiki


class WikiArtistImportTests(unittest.TestCase):
    def test_category_continuation_reads_every_page(self):
        calls=[]
        def fake(url,p):
            self.assertEqual(p["cmlimit"],200)
            token=p.get("cmcontinue")
            calls.append(token)
            if not token:
                return {"query":{"categorymembers":[
                    {"title":"Γιώργος Μαζωνάκης","ns":0},
                    {"title":"Αντώνης Ρέμος","ns":0}]},"continue":{"cmcontinue":"next"}}
            if token=="next":
                return {"query":{"categorymembers":[
                    {"title":"Μαρίνα Σάττι","ns":0},
                    {"title":"Γιώργος Μαζωνάκης","ns":0},
                    {"title":"Κατηγορία:Χ","ns":14}]}}
            raise AssertionError("unexpected continuation")
        members,pages=wiki.category_members(wiki.ROOT,api=fake)
        self.assertEqual(pages,2)
        self.assertEqual(len(members),3)
        self.assertEqual(calls,[None,"next"])

    def test_title_disambiguators_are_only_removed_for_known_roles(self):
        self.assertEqual(wiki.normalize_person("Γιώργος Παπαδόπουλος (τραγουδιστής)"),"Γιώργος Παπαδόπουλος")
        self.assertEqual(wiki.normalize_person("Nino (singer)"),"Nino")
        self.assertEqual(wiki.normalize_person("Παπαδόπουλος (άλλος)"),"Παπαδόπουλος (άλλος)")
        self.assertIsNone(wiki.mapping("Γιώργος","Γιώργος"))
        self.assertIsNone(wiki.mapping("Γιώργος Παπαδόπουλος","George Papadopoulos (politician)"))

    def test_manual_existing_mappings_cannot_be_replaced(self):
        before=[{"greeklish":"Giorgos Mazonakis","greek":"Γιώργος Μαζωνάκης"},
                {"greeklish":"Giorgos Papadopoulos","greek":"Γιώργος Παπαδόπουλος"}]
        pages={
            "Γιώργος Μαζωνάκης":{wiki.ROOT},
            "Άλλος Γιώργος Παπαδόπουλος":{wiki.ROOT},
            "Άννα Βίσση":{wiki.ROOT},
        }
        identities={
            "Γιώργος Μαζωνάκης":("Giorgos Mazonakis","enwiki"),
            "Άλλος Γιώργος Παπαδόπουλος":("Giorgos Papadopoulos","wikidata-en"),
            "Άννα Βίσση":("Anna Vissi","enwiki"),
        }
        result,audit,original,added=wiki.expand(before,pages,identities)
        self.assertEqual(original,2)
        self.assertEqual(added,1)
        self.assertIn(("Giorgos Papadopoulos","Γιώργος Παπαδόπουλος"),result)
        self.assertNotIn(("Giorgos Papadopoulos","Άλλος Γιώργος Παπαδόπουλος"),result)
        self.assertIn(("Anna Vissi","Άννα Βίσση"),result)
        self.assertTrue(any(row[-1]=="collision-existing-skipped" for row in audit))

    def test_duplicate_latin_identity_is_never_assigned_to_two_greek_names(self):
        names={"Γιώργος Μανιάτης":{wiki.ROOT},"Γεώργιος Μανιάτης":{wiki.ROOT}}
        labels={g:("George Maniatis","enwiki") for g in names}
        result,audit,old,added=wiki.expand([],names,labels)
        self.assertEqual(added,0)
        self.assertTrue(any("collision-new-skipped" in r[-1] for r in audit))

    def test_source_is_not_an_unreviewed_transliteration(self):
        self.assertIsNone(wiki.mapping("Γιώργος Μανιάτης",""))
        self.assertIsNone(wiki.mapping("Γιώργος Μανιάτης","Unknown (singer 2025)"))
        result,audit,old,added=wiki.expand([],{"Νέος Άγνωστος":{wiki.ROOT}},{})
        self.assertEqual(added,0)
        self.assertEqual(audit[0][-1],"needs-manual-identity")

    def test_existing_csv_is_valid_and_preserved_in_order(self):
        source=Path(__file__).with_name("Greek_Artists.csv")
        if not source.exists():self.skipTest("CSV missing")
        rows=wiki.read_existing(source)
        self.assertGreaterEqual(len(rows),80)
        self.assertIn({"greeklish":"Giorgos Mazwnakis","greek":"Γιώργος Μαζωνάκης"},rows)
        exact=[wiki.key(r["greeklish"]) for r in rows]
        self.assertEqual(len(exact),len(set(exact)))
        serialized=wiki.make_csv(wiki.HEADERS,[(r["greeklish"],r["greek"]) for r in rows])
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/"artist.csv"
            file.write_text(serialized,encoding="utf-8")
            self.assertEqual(len(wiki.read_existing(file)),len(rows))

if __name__=="__main__":unittest.main(verbosity=2)
