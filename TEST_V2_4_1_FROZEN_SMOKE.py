"""Run against the *built* standalone EXE on Windows CI.

The worker must receive the stop request without a shared console.
Only temporary folders/profiles; no user music and no live network.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

class FrozenStopSmoke(unittest.TestCase):
    def test_real_frozen_worker_acknowledges_stop_marker(self):
        executable=Path(sys.argv[1]).resolve()
        self.assertTrue(executable.is_file(),executable)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            music=root/"music";music.mkdir()
            marker=root/"STOP.request";marker.write_text("STOP\n",encoding="utf-8")
            settings={"schema":1,"profiles":{"StopSmoke":{
                "folder":str(music),"action":"1","greek":False,"local_ai":False,
                "musicbrainz":False,"provider_mode":"fast","order":"d",
                "custom_order":"","recovery_wait":False,"recursive":False,
                "history":False,"limit":"1","exact_fallback":False,
                "auto_search":True,"database":"","incremental":True}}}
            profile=root/"profiles.json";profile.write_text(
                json.dumps(settings),encoding="utf-8")
            env=dict(os.environ,LRC_STOP_FILE=str(marker))
            result=subprocess.run(
                [str(executable),"--profile","StopSmoke","--profiles-path",str(profile)],
                env=env,text=True,errors="replace",capture_output=True,timeout=90)
            self.assertEqual(result.returncode,130,
                f"Worker ignored GUI stop request: stdout={result.stdout[-1300:]} stderr={result.stderr[-500:]}")
            self.assertIn("STOP REQUESTED",result.stdout)
            self.assertEqual(list(music.rglob("*.lrc")),[])
            print("PASS FROZEN WINDOWS STOP: worker acknowledged GUI marker with exit 130 and no audio changes")

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("Usage: python TEST_V2_4_1_FROZEN_SMOKE.py path/to/LRC_Bulk_Finder_Worker.exe")
    exe=sys.argv[1]
    sys.argv=[sys.argv[0],exe]
    unittest.main(verbosity=2)
