"""Offline regression checks; no network access or real LRCLIB downloads."""
import io
import json
import unittest
from unittest import mock
from urllib.error import URLError
import auto_install_lrclib_database as ins

class Response:
    def __init__(self, payload, redirect=None):
        self.payload=io.BytesIO(payload)
        self.redirect=redirect or ins.CATALOG
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,n=-1):return self.payload.read(n)
    def geturl(self):return self.redirect

class DiscoveryTests(unittest.TestCase):
    def test_latest_json_dump(self):
        sample={"objects":[
          {"key":"lrclib-db-dump-20260410T172629Z.sqlite3.gz", "size":100, "uploaded":"2026-04-10"},
          {"key":"lrclib-db-dump-20261010T172629Z.sqlite3.gz", "size":500, "uploaded":"2026-10-10"},
          {"key":"non_db.txt", "size":900,"uploaded":"2027-01-01"}]}
        url, size=ins.discover_snapshot_json(json.dumps(sample))
        self.assertEqual(url,'https://db-dumps.lrclib.net/lrclib-db-dump-20261010T172629Z.sqlite3.gz')
        self.assertEqual(size,500)
    def test_json_api_nested_key(self):
        url,size=ins.discover_snapshot_json(json.dumps({'objects':[{'key':'2026/lrclib-db-dump-20261011T123456Z.sqlite3.gz','size':'1024'}]}))
        self.assertEqual(url,'https://db-dumps.lrclib.net/2026/lrclib-db-dump-20261011T123456Z.sqlite3.gz')
        self.assertEqual(size,1024)
    def test_rejects_unsafe_or_bogus_entries(self):
        for key in ('../secret.sqlite3.gz','/absolute.sqlite3.gz','other.sqlite3.gz?evil=1','evil\\db.sqlite3.gz', 'x.sqlite3', 'https://fake/a.sqlite3.gz'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                ins.discover_snapshot_json(json.dumps({'objects':[{'key':key}]}))
    def test_rejects_bad_json(self):
        for text in ('{}','not json','[]','{"objects":{}}'):
            with self.subTest(text=text), self.assertRaises(ValueError):ins.discover_snapshot_json(text)
    def test_bounded_fetch(self):
        blob=json.dumps({'objects':[{'key':'abc.sqlite3.gz','size':700}]}).encode()
        self.assertEqual(ins.fetch_catalog(opener=lambda req,timeout:Response(blob)),blob.decode())
        with self.assertRaises(ValueError):
            ins.fetch_catalog(opener=lambda req,timeout:Response(b'x'*(4*1024*1024+1)))
    def test_insecure_redirect_rejected(self):
        with self.assertRaises(ValueError):
            ins.fetch_catalog(opener=lambda req,timeout:Response(b'{}','http://example.com'))
    def test_json_first(self):
        with mock.patch.object(ins,'fetch_catalog',return_value=json.dumps({'objects':[{'key':'latest.sqlite3.gz','size':100}]})),mock.patch.object(ins,'fetch_index',side_effect=AssertionError('HTML fallback must not run')):
            url,size,method=ins.discover_official_snapshot()
        self.assertEqual(size,100)
        self.assertEqual(method,'LRCLIB JSON catalog')
    def test_html_fallback(self):
        sample='<a href="https://lrclib.net/db-dumps/lrclib-db-dump-20260805T100000Z.sqlite3.gz">db</a>'
        with mock.patch.object(ins,'fetch_catalog',side_effect=URLError('offline')),mock.patch.object(ins,'fetch_index',return_value=sample):
            url,size,method=ins.discover_official_snapshot()
        self.assertIn('20260805',url)
        self.assertIsNone(size)
        self.assertEqual(method,'official LRCLIB webpage')
    def test_both_fail_safe(self):
        with mock.patch.object(ins,'fetch_catalog',side_effect=URLError('offline')),mock.patch.object(ins,'fetch_index',return_value='no dumps'):
            with self.assertRaisesRegex(ValueError,'No files were downloaded or changed'):
                ins.discover_official_snapshot()

if __name__=='__main__':unittest.main(verbosity=2)
