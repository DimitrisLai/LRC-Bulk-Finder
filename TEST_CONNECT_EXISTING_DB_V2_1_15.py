import io,sqlite3,tempfile,unittest
from pathlib import Path
from contextlib import closing, redirect_stdout
from unittest import mock
from connect_existing_lrclib_database import link_existing_folder

class ConnectorTests(unittest.TestCase):
    def test_reuse_existing_without_copying_db(self):
        with tempfile.TemporaryDirectory() as td:
            t=Path(td);db=t/'fixture.sqlite3';program=t/'program';program.mkdir()
            with closing(sqlite3.connect(db)) as con, con:
                con.execute('create table tracks (id integer, name text, name_lower text, artist_name text,artist_name_lower text, duration real, last_lyrics_id integer)')
                con.execute('create table lyrics (id integer, synced_lyrics text)')
            size=db.stat().st_size
            with redirect_stdout(io.StringIO()):self.assertTrue(link_existing_folder(program,choose=lambda:str(db)))
            self.assertEqual(Path((program/'LRCLIB_LOCAL_DB.txt').read_text().strip()).resolve(),db.resolve())
            self.assertEqual(db.stat().st_size,size)
    def test_wrong_database_keeps_current_config(self):
        with tempfile.TemporaryDirectory() as td:
            t=Path(td);(t/'LRCLIB_LOCAL_DB.txt').write_text('previous/path\n')
            with redirect_stdout(io.StringIO()):self.assertFalse(link_existing_folder(t,choose=lambda:str(t/'missing.sqlite3')))
            self.assertEqual((t/'LRCLIB_LOCAL_DB.txt').read_text(),'previous/path\n')
if __name__=='__main__':unittest.main()
