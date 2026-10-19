"""Offline quality, privacy and failure-safety tests for Greek lexicon SQLite."""
import hashlib
import shutil
import sqlite3
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock
import sys

sys.modules.setdefault('syncedlyrics',types.SimpleNamespace(search=lambda *a,**k:None))
import LRC_Bulk_Finder as app
import BUILD_GREEK_LEXICON_DB as builder


class GreekLexiconSQLiteTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for name in builder.SOURCE_FILES:
            shutil.copy2(Path(builder.__file__).with_name(name),self.root/name)
        self.original=app.GREEK_WORDS.copy()
        self.addCleanup(lambda:(app.GREEK_WORDS.clear(),app.GREEK_WORDS.update(self.original)))

    def _load_local(self):
        app.GREEK_WORDS.clear()
        with mock.patch.object(app,'__file__',str(self.root/'LRC_Bulk_Finder.py')):
            app.load_greek_words()

    def test_builder_creates_small_privacy_safe_sql(self):
        sql,count=builder.build(root=self.root)
        self.assertEqual(sql.resolve(),(self.root/'Greek_Lexicon.sqlite3').resolve())
        self.assertGreaterEqual(count,1000)
        self.assertLess(sql.stat().st_size,2_000_000)
        self.assertEqual(sql.read_bytes()[:16],b'SQLite format 3\x00')
        with sqlite3.connect(sql) as connection:
            self.assertEqual(connection.execute('PRAGMA quick_check').fetchone()[0],'ok')
            self.assertEqual(connection.execute('PRAGMA application_id').fetchone()[0],
                             builder.APPLICATION_ID)
            self.assertEqual(connection.execute('SELECT COUNT(*) FROM words').fetchone()[0],count)
            self.assertEqual(connection.execute('SELECT greek FROM words WHERE greeklish=?',('fonazo',)).fetchone()[0],
                             'φωνάζω')
            self.assertFalse(connection.execute(
                "SELECT 1 FROM words WHERE greeklish LIKE '%onedrive%' OR greek LIKE '%onedrive%'").fetchone())
        self.assertNotIn(b'OneDrive',sql.read_bytes())
        self.assertNotIn(b'.mp3',sql.read_bytes())

    def test_sql_and_csv_fallback_produce_same_words(self):
        sql,count=builder.build(root=self.root)
        self._load_local()
        with_db=app.GREEK_WORDS.copy()
        self.assertEqual(len(with_db),count)
        sql.unlink()
        self._load_local()
        self.assertEqual(app.GREEK_WORDS,with_db)

    def test_stale_db_ignored_and_csv_user_override_wins(self):
        builder.build(root=self.root)
        base=self.root/'Greek_Words.csv'
        base.write_text(base.read_text(encoding='utf-8-sig')+'\nnewartistlessword,νέαλέξη\n',
                        encoding='utf-8-sig')
        self._load_local()
        self.assertEqual(app.GREEK_WORDS['newartistlessword'],'νέαλέξη')
        self.assertEqual(app.GREEK_WORDS['fonazo'],'φωνάζω')
        self.assertGreater(len(app.GREEK_WORDS),1000)

    def test_broken_db_never_prevents_dictionary_search(self):
        (self.root/'Greek_Lexicon.sqlite3').write_bytes(b'broken db')
        self._load_local()
        self.assertEqual(app.GREEK_WORDS['fonazo'],'φωνάζω')

    def test_known_greeklish_titles_and_english_protection(self):
        self._load_local()
        samples={
            'Den Ise Erotas Esi':'Δεν είσαι έρωτας εσύ',
            'Esy Horeveis Kai Ego Pethaino':'Εσύ χορεύεις και εγώ πεθαίνω',
            'Me Kati':'Με κάτι',
            'Fevgis Ke Hanese':'Φεύγεις και χάνεσαι',
            'Horis Logia':'Χωρίς λόγια',
            'Mia Kardia':'Μια καρδιά',
            'Tha Se Do':'Θα σε δω',
        }
        for greeklish,expected in samples.items():
            with self.subTest(greeklish=greeklish):
                self.assertEqual(app.dictionary_greek_title(greeklish),expected)
        self.assertIsNone(app.dictionary_greek_title('Best of Times'))

    def test_db_build_twice_is_valid_and_canonical(self):
        path,count=builder.build(root=self.root)
        rows=path.read_bytes()
        _,count2=builder.build(root=self.root)
        self.assertEqual(count,count2)
        self.assertEqual(hashlib.sha256(rows).hexdigest(),
                         hashlib.sha256(path.read_bytes()).hexdigest())

    def test_builder_rejects_invalid_latin_or_conflicting_doubles(self):
        with (self.root/'Greek_Words_Expanded.csv').open('a',encoding='utf-8') as output:
            output.write('malformed word,άκυρο\n')
        with self.assertRaises(ValueError):
            builder.build(root=self.root)


if __name__=='__main__':
    unittest.main(verbosity=2)
