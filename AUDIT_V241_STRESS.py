"""3353-song scale test against the exact published v2.4.1 Python archive.

Actual mocked local/online provider transitions, real temp filesystem writes,
real JSONL fsync, real CSVs and checkpoint resume, with no HTTP requests.
"""
import csv,io,os,sys,tempfile,time,types,unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parent/"release_unpacked"/"LRC_Bulk_Finder_v2_4_1"
sys.path.insert(0,str(ROOT))
sys.modules.setdefault("syncedlyrics",types.SimpleNamespace(search=lambda *a,**k:None))
import LRC_Bulk_Finder as app

N=3353
LRC="[00:03.00] Alpha\n[00:51.00] Beta\n[01:43.00] Gamma\n[02:56.00] Omega\n"


class ActualScaleAudit(unittest.TestCase):
    def test_3353_tracks_three_stages_then_checkpoint_resume(self):
        with tempfile.TemporaryDirectory(prefix="lrc_v241_stress_") as tmp:
            folder=Path(tmp)
            for i in range(1,N+1):
                (folder/f"Song_{i:05d}.mp3").write_bytes(b"MP3_BYTES_PROTECTED")
            calls={"offline":0,"online":0,"retry":0}
            errors=[]
            def offline(title,artist,duration,review):
                calls["offline"]+=1
                idx=int(title.rsplit("_",1)[1])
                if idx%5==0:
                    return app.Hit(LRC,"LRCLIB","verified","LOCAL",True)
                if idx%71==0:
                    review.add("LRCLIB local",title,artist,"unverified candidate",LRC)
                return None
            def online(title,artist,album,duration,review,*,only_providers=None,
                       retry_targets=None,timings=None,request_traces=None):
                idx=int(title.rsplit("_",1)[1])
                if only_providers:
                    calls["retry"]+=1
                    assert tuple(only_providers)==("LiriQo",)
                    return None,"NOT_FOUND","no verified match",["LiriQo=NO_MATCH"]
                calls["online"]+=1
                if idx%7==0:
                    return app.Hit(LRC,"SyncLRC","verified","ORIGINAL",True),"SAVED","verified",["SyncLRC=SAVED"]
                if idx%101==0:
                    retry_targets.add("LiriQo")
                    return None,"TIMEOUT","LiriQo timed out",["LiriQo=ERROR (timeout)"]
                return None,"NOT_FOUND","not found",["SyncLRC=NO_MATCH"]
            def run():
                answers=iter(["5","n","n","full","d","n","n","n","a","n"])
                app.GREEK_MODE=False;app.G2G_ENABLED=False;app.G2G_TOOL=None
                app.MB_ENABLED=False;app.MB_DISK_CACHE=None;app.STAGED_ONLINE_MODE=False
                app.LOCAL_LRCLIB=None;app.blocked.clear()
                with mock.patch("builtins.input",side_effect=lambda _:next(answers)),\
                     mock.patch.object(app,"select_folder",return_value=folder),\
                     mock.patch.object(app,"ensure_local_lrclib_config",return_value=True),\
                     mock.patch.object(app,"load_provider_cooldowns"),\
                     mock.patch.object(app,"configure_lrclib_contact",return_value=True),\
                     mock.patch.object(app,"show_provider_availability"),\
                     mock.patch.object(app,"song_info",side_effect=lambda p:(p.stem,"Test Artist","",180)),\
                     mock.patch.object(app,"local_lrclib_search",side_effect=offline),\
                     mock.patch.object(app,"search_song",side_effect=online),\
                     redirect_stdout(io.StringIO()) as output:
                    app.main()
                return output.getvalue()
            start=time.perf_counter()
            log=run()
            elapsed=time.perf_counter()-start
            expected_offline=N
            expected_online=sum(i%5!=0 for i in range(1,N+1))
            expected_retry=sum(i%5!=0 and i%7!=0 and i%101==0
                               for i in range(1,N+1))
            self.assertEqual(calls,{"offline":expected_offline,
                                    "online":expected_online,
                                    "retry":expected_retry})
            self.assertIn("PROGRESS ROUND 1:",log)
            self.assertIn("PROGRESS ROUND 2:",log)
            self.assertIn("PROGRESS ROUND 3:",log)
            saved_offline=N//5
            saved_online=sum(i%5!=0 and i%7==0 for i in range(1,N+1))
            candidate_count=sum(i%5!=0 and i%71==0 for i in range(1,N+1))
            final_counter=(
                f"STAGE COUNTERS: stage=3 found=0 candidate=0 not_found=0 "
                f"total_found={saved_offline+saved_online} total_candidate={candidate_count}")
            self.assertIn(final_counter,log,
                "After Stage 3, stage counters must be zero and historical totals persist")
            self.assertTrue((folder/"LRC_Run_Checkpoint_v2_4_1.jsonl").is_file())
            checkpoint_size=(folder/"LRC_Run_Checkpoint_v2_4_1.jsonl").stat().st_size
            self.assertGreater(checkpoint_size,250_000)
            for i in (1,5,71,101,3045,3353):
                self.assertEqual((folder/f"Song_{i:05d}.mp3").read_bytes(),
                                 b"MP3_BYTES_PROTECTED")
            self.assertTrue((folder/"Song_00005.lrc").exists())
            self.assertTrue((folder/"Song_00007.lrc").exists())
            self.assertTrue((folder/"Song_00071.candidate.lrc").exists())
            self.assertFalse((folder/"Song_00101.lrc").exists())
            previous=dict(calls)
            restart=time.perf_counter()
            second=run()
            second_elapsed=time.perf_counter()-restart
            self.assertEqual(calls,previous,"All previously finished work should be reused")
            self.assertIn("CHECKPOINT:",second)
            self.assertIn("THIS ROUND ETA:",second)
            journal=folder/"LRC_Run_Checkpoint_v2_4_1.jsonl"
            self.assertEqual(journal.stat().st_size,checkpoint_size,
                             "Checkpoint replay alone should not append duplicates")
            report=folder/"LRC_Finder_Report_v2_1_15.csv"
            self.assertTrue(report.exists())
            with report.open(encoding="utf-8-sig",newline="") as handle:
                rows=list(csv.reader(handle))
            self.assertGreater(len(rows),expected_online)
            self.assertIn("Song_00071",(folder/"LRC_Review_Needed.txt").read_text(encoding="utf-8-sig"))
            print(f"\nPASS 3353-SONG STRESS: offline={expected_offline}, online={expected_online}, "
                  f"timeout-only retry={expected_retry}, checkpoint={checkpoint_size} bytes, "
                  f"first={elapsed:.1f}s, resumed={second_elapsed:.1f}s")


if __name__=="__main__":
    unittest.main(verbosity=2)
