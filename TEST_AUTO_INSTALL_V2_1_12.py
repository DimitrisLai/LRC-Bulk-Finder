"""Offline tests for official snapshot installer. Never contacts LRCLIB."""
import gzip
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path
from contextlib import closing
from unittest import mock
import auto_install_lrclib_database as ins
from lrclib_local import LocalLRCLIB

class FakeResponse:
    def __init__(self, content, code=200, headers=None, url='https://lrclib.net/db-dumps/file.sqlite3.gz'):
        self._io=io.BytesIO(content)
        self.status=code
        self.headers=headers or {'Content-Length':str(len(content))}
        self._url=url
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def read(self,n=-1):return self._io.read(n)
    def geturl(self):return self._url

class AutoTests(unittest.TestCase):
    def make_db_gzip(self, folder):
        db=folder/'demo.sqlite3'
        with closing(sqlite3.connect(db)) as con, con:
            con.executescript('''
              CREATE TABLE tracks (id INTEGER PRIMARY KEY, name TEXT, name_lower TEXT,
                artist_name TEXT, artist_name_lower TEXT, duration FLOAT, last_lyrics_id INTEGER);
              CREATE TABLE lyrics (id INTEGER PRIMARY KEY, synced_lyrics TEXT);
              INSERT INTO tracks VALUES (1,'Hello','hello','Tester','tester',180,1);
              INSERT INTO lyrics VALUES (1,'[00:01.00] Hello');
            ''')
        gz=folder/'demo.sqlite3.gz'
        with db.open('rb') as source, gzip.open(gz,'wb') as target:
            target.write(source.read())
        db.unlink()
        return gz, db

    def test_discover_latest_from_html_and_scripts(self):
        html='''<a href="/db-dumps/lrclib-db-dump-20260519T172012Z.sqlite3.gz">May</a>
        <a href="https://lrclib.net/db-dumps/lrclib-db-dump-20260901T120000Z.sqlite3.gz">September</a>'''
        self.assertIn('20260901',ins.discover_snapshot(html))
        script=r'https:\/\/lrclib.net\/db-dumps\/lrclib-db-dump-20261001T120000Z.sqlite3.gz'
        self.assertIn('20261001',ins.discover_snapshot(script))

    def test_discover_rejects_unrelated_or_missing(self):
        with self.assertRaises(ValueError):ins.discover_snapshot('no .sqlite3.gz in page')
        with self.assertRaises(ValueError):ins.discover_snapshot('<a href="http://example.com/bad.sqlite3.gz">')

    def test_regular_download(self):
        with tempfile.TemporaryDirectory() as t:
            dst=Path(t)/'demo.sqlite3.gz'
            body=b'123'*3000
            url='https://lrclib.net/db-dumps/demo.sqlite3.gz'
            def opener(_req,timeout):return FakeResponse(body,url=url)
            self.assertEqual(ins.download_resume(url,dst,opener=opener,chunk=1024).read_bytes(),body)
            self.assertFalse((Path(t)/'demo.sqlite3.gz.part').exists())

    def test_partial_download_can_resume(self):
        with tempfile.TemporaryDirectory() as t:
            dst=Path(t)/'demo.sqlite3.gz'
            part=Path(t)/'demo.sqlite3.gz.part';part.write_bytes(b'abc')
            url='https://lrclib.net/db-dumps/demo.sqlite3.gz'
            def opener(req,timeout):
                self.assertEqual(req.headers.get('Range'),'bytes=3-')
                return FakeResponse(b'def',206,{'Content-Range':'bytes 3-5/6','Content-Length':'3'},url)
            self.assertEqual(ins.download_resume(url,dst,opener=opener),dst)
            self.assertEqual(dst.read_bytes(),b'abcdef')

    def test_range_ignored_restarts_without_corruption(self):
        with tempfile.TemporaryDirectory() as t:
            dst=Path(t)/'demo.sqlite3.gz'
            part=Path(t)/'demo.sqlite3.gz.part';part.write_bytes(b'abc')
            url='https://lrclib.net/db-dumps/demo.sqlite3.gz'
            def opener(req,timeout):return FakeResponse(b'new',200,{'Content-Length':'3'},url)
            ins.download_resume(url,dst,opener=opener)
            self.assertEqual(dst.read_bytes(),b'new')

    def test_gzip_extract_verify_then_activate_config(self):
        with tempfile.TemporaryDirectory() as t:
            t=Path(t);gz,db=self.make_db_gzip(t);cfg=t/'config.txt'
            cfg.write_text('KEEP ME')
            result=ins.install_from_downloaded_gzip(gz,db,cfg)
            self.assertEqual(result,db)
            self.assertEqual(len(LocalLRCLIB(db).search([('hello','tester')],180)),1)
            self.assertIn(str(db),cfg.read_text())
            self.assertTrue(gz.exists())

    def test_bad_gzip_keeps_previous_config(self):
        with tempfile.TemporaryDirectory() as t:
            t=Path(t);gz=t/'invalid.sqlite3.gz';gz.write_bytes(gzip.compress(b'not sqlite'))
            cfg=t/'config.txt';cfg.write_text('EXISTING')
            with self.assertRaises(ValueError):ins.install_from_downloaded_gzip(gz,t/'bad.sqlite3',cfg)
            self.assertEqual(cfg.read_text(),'EXISTING')
            self.assertFalse((t/'bad.sqlite3').exists())

    def test_truncated_gzip_does_not_leave_active_db(self):
        with tempfile.TemporaryDirectory() as t:
            t=Path(t);gz,db=self.make_db_gzip(t);gz.write_bytes(gz.read_bytes()[:-4])
            cfg=t/'config.txt';cfg.write_text('EXISTING')
            with self.assertRaises((EOFError,OSError)):ins.install_from_downloaded_gzip(gz,db,cfg)
            self.assertEqual(cfg.read_text(),'EXISTING')
            self.assertFalse(db.exists())

if __name__=='__main__':unittest.main(verbosity=2)
