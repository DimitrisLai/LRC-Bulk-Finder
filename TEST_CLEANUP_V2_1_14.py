"""Cleanup utility safeguards; uses only temporary tiny files."""
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock
import cleanup_lrclib_database as cleanup
import auto_install_lrclib_database as installer

class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        folder=Path(self.tmp.name)
        self.db=folder/'lrclib-db-dump-20261012T090639Z.sqlite3'
        self.gz=folder/'lrclib-db-dump-20261012T090639Z.sqlite3.gz'
        self.cfg=folder/'LRCLIB_LOCAL_DB.txt'
        self.db.write_bytes(b'test database fixture only')
        self.gz.write_bytes(b'compressed fixture')
        self.cfg.write_text(cleanup.AUTO_MARKER+'\n'+str(self.db)+'\n',encoding='utf-8')
    def test_locates_exact_managed_paths(self):
        self.assertEqual(cleanup.locate_managed_files(self.cfg),(self.db,self.gz))
    def test_remove_archive_only_leaves_offline_db(self):
        result=cleanup.remove_managed_files('1',self.cfg)
        self.assertEqual(result,[self.gz]);self.assertTrue(self.db.exists())
        self.assertTrue(self.cfg.exists());self.assertFalse(self.gz.exists())
        self.assertEqual(cleanup.locate_managed_files(self.cfg),(self.db,self.gz))
    def test_remove_database_only_disables_offline_config(self):
        result=cleanup.remove_managed_files('2',self.cfg)
        self.assertEqual(result,[self.db]);self.assertTrue(self.gz.exists())
        self.assertFalse(self.db.exists())
        self.assertIn('was removed', self.cfg.read_text())
        with self.assertRaises(ValueError):cleanup.locate_managed_files(self.cfg)
    def test_remove_both(self):
        result=cleanup.remove_managed_files('3',self.cfg)
        self.assertCountEqual(result,[self.db,self.gz])
        self.assertFalse(self.db.exists());self.assertFalse(self.gz.exists())
        self.assertIn('was removed',self.cfg.read_text())
    def test_refuse_unmanaged_config(self):
        self.cfg.write_text('# my manual DB\n'+str(self.db)+'\n',encoding='utf-8')
        with self.assertRaises(ValueError):cleanup.remove_managed_files('3',self.cfg)
        self.assertTrue(self.db.exists());self.assertTrue(self.gz.exists())
    def test_refuse_unexpected_filename_even_if_auto_marked(self):
        other=self.db.with_name('my-critical-database.sqlite3')
        self.cfg.write_text(cleanup.AUTO_MARKER+'\n'+str(other)+'\n')
        with self.assertRaises(ValueError):cleanup.remove_managed_files('3',self.cfg)
    def test_refuse_multiple_config_paths(self):
        self.cfg.write_text(cleanup.AUTO_MARKER+'\n'+str(self.db)+'\n'+str(self.db)+'\n')
        with self.assertRaises(ValueError):cleanup.remove_managed_files('3',self.cfg)
    def test_refuse_invalid_choice(self):
        with self.assertRaises(ValueError):cleanup.remove_managed_files('0',self.cfg)
    def test_refuse_symlink(self):
        other=self.db.parent/'fake.sqlite3'
        try:other.symlink_to(self.db)
        except OSError:self.skipTest('symlinks not available')
        self.cfg.write_text(cleanup.AUTO_MARKER+'\n'+str(other)+'\n')
        with self.assertRaises(ValueError):cleanup.locate_managed_files(self.cfg)
    def test_cancel_does_not_delete(self):
        with mock.patch.object(cleanup,'CONFIG',self.cfg),mock.patch('builtins.input',return_value=''),redirect_stdout(io.StringIO()):
            self.assertEqual(cleanup.main(),0)
        self.assertTrue(self.db.exists());self.assertTrue(self.gz.exists())
    def test_confirmation_required(self):
        with mock.patch.object(cleanup,'CONFIG',self.cfg),mock.patch('builtins.input',side_effect=['3','NO']),redirect_stdout(io.StringIO()):
            self.assertEqual(cleanup.main(),0)
        self.assertTrue(self.db.exists());self.assertTrue(self.gz.exists())
    def test_destination_shortcut_delegates_to_package(self):
        app=self.db.parent/'app';app.mkdir()
        (app/'CLEANUP_LRCLIB_DATABASE.cmd').write_text('@echo off\n')
        folder=self.db.parent/'storage';folder.mkdir()
        with mock.patch.object(installer,'BASE',app),redirect_stdout(io.StringIO()):
            installer.offer_destination_cleanup_launcher(folder)
        text=(folder/'CLEANUP_LRCLIB_DATABASE.cmd').read_text()
        self.assertIn('CLEANUP_LRCLIB_DATABASE.cmd',text)
        self.assertIn('call ',text)
    def test_destination_shortcut_not_overwritten(self):
        app=self.db.parent/'app';app.mkdir()
        (app/'CLEANUP_LRCLIB_DATABASE.cmd').write_text('@echo off\n')
        folder=self.db.parent/'storage';folder.mkdir()
        (folder/'CLEANUP_LRCLIB_DATABASE.cmd').write_text('original',encoding='utf-8')
        with mock.patch.object(installer,'BASE',app):
            installer.offer_destination_cleanup_launcher(folder)
        self.assertEqual((folder/'CLEANUP_LRCLIB_DATABASE.cmd').read_text(),'original')

if __name__=='__main__':unittest.main(verbosity=2)
