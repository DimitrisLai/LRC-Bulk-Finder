"""v2.4.3 STOP verification reliability QA; no music or external providers.

The real Windows integration test spawns a disposable parent->child->grandchild
worker tree and checks all three are terminated; other tests inject transient
process-enumeration faults and ensure no false success is reported.
"""
from __future__ import annotations
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import worker_stop as ws


class SnapshotRecoveryTests(unittest.TestCase):
    def test_descendants_include_grandchildren_only(self):
        self.assertEqual(ws._descendants({11:1,12:11,13:12,22:1},11),{12,13})

    def test_native_snapshot_preferred_when_available(self):
        with mock.patch.object(ws, '_windows_process_table_toolhelp', return_value={10:1}), \
             mock.patch.object(ws, '_windows_process_table_cim') as slow:
            self.assertEqual(ws._windows_process_table(), {10:1})
            slow.assert_not_called()

    def test_cim_used_when_native_unavailable(self):
        with mock.patch.object(ws, '_windows_process_table_toolhelp', return_value=None), \
             mock.patch.object(ws, '_windows_process_table_cim', return_value={10:1}) as slow:
            self.assertEqual(ws._windows_process_table(), {10:1})
            slow.assert_called_once()

    def test_both_snapshot_engines_unavailable_fail_closed(self):
        with mock.patch.object(ws, '_windows_process_table_toolhelp', return_value=None), \
             mock.patch.object(ws, '_windows_process_table_cim', return_value=None):
            self.assertIsNone(ws._windows_process_table())

    def test_retry_transient_windows_snapshot_failure(self):
        with mock.patch.object(ws, '_windows_process_table', side_effect=[None,None,{10:1}]), \
             mock.patch.object(ws.time, 'sleep') as sleep:
            self.assertEqual(ws._windows_snapshot_with_retry(),{10:1})
            self.assertEqual(sleep.call_count,2)

    def test_unavailable_before_snapshot_does_not_claim_safe(self):
        class Worker:
            pid=4100
            stopped=False
            def poll(self):return 0 if self.stopped else None
            def wait(self,timeout):self.stopped=True
        p=Worker()
        with mock.patch.object(ws,'_windows_snapshot_with_retry',side_effect=[None,{1:0}]), \
             mock.patch.object(ws.subprocess,'run',return_value=mock.Mock(returncode=0,stderr='',stdout='ok')):
            ok,msg=ws.kill_search_process(p,platform='nt')
        self.assertFalse(ok)
        self.assertIn('verification unavailable',msg.lower())

    def test_unavailable_after_snapshot_does_not_claim_safe(self):
        class Worker:
            pid=4100
            stopped=False
            def poll(self):return 0 if self.stopped else None
            def wait(self,timeout):self.stopped=True
        p=Worker()
        with mock.patch.object(ws,'_windows_snapshot_with_retry',side_effect=[{4100:1,4101:4100},None]), \
             mock.patch.object(ws.subprocess,'run',return_value=mock.Mock(returncode=0,stderr='',stdout='ok')):
            ok,msg=ws.kill_search_process(p,platform='nt')
        self.assertFalse(ok)
        self.assertIn('verification unavailable',msg.lower())

    def test_lingering_child_never_claimed_dead(self):
        class Worker:
            pid=4100
            stopped=False
            def poll(self):return 0 if self.stopped else None
            def wait(self,timeout):self.stopped=True
        p=Worker()
        with mock.patch.object(ws,'_windows_snapshot_with_retry',side_effect=[{4100:1,4101:4100},{4101:1}]), \
             mock.patch.object(ws.subprocess,'run',return_value=mock.Mock(returncode=0,stderr='',stdout='ok')):
            ok,msg=ws.kill_search_process(p,platform='nt')
        self.assertFalse(ok)
        self.assertIn('4101',msg)


@unittest.skipUnless(os.name=='nt', 'Windows native process table only')
class NativeProcessSnapshotTests(unittest.TestCase):
    def test_native_toolhelp_sees_current_process_without_powershell(self):
        with mock.patch.object(ws.subprocess,'run',side_effect=AssertionError('PowerShell was used')):
            pairs=ws._windows_process_table_toolhelp()
        self.assertIsNotNone(pairs)
        self.assertIn(os.getpid(),pairs)

    def test_real_parent_child_grandchild_stop(self):
        with tempfile.TemporaryDirectory(prefix='lrc_stop_grandchild_') as td:
            t=Path(td)
            child=t/'child.py'
            parent=t/'parent.py'
            child.write_text('import subprocess,sys,time,pathlib\n'
                             'g=subprocess.Popen([sys.executable,"-c","import time;time.sleep(120)"])\n'
                             'pathlib.Path(sys.argv[1]).write_text(str(g.pid))\n'
                             'time.sleep(120)\n',encoding='utf-8')
            parent.write_text('import subprocess,sys,time,pathlib\n'
                              'p=subprocess.Popen([sys.executable,sys.argv[1],sys.argv[2]])\n'
                              'pathlib.Path(sys.argv[3]).write_text(str(p.pid))\n'
                              'time.sleep(120)\n',encoding='utf-8')
            parent_pid=t/'child.pid';grand_pid=t/'grand.pid'
            proc=subprocess.Popen([sys.executable,str(parent),str(child),str(grand_pid),str(parent_pid)],
                                  creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
            ids=[]
            try:
                deadline=time.monotonic()+12
                while time.monotonic()<deadline and not (parent_pid.exists() and grand_pid.exists()):
                    time.sleep(.05)
                self.assertTrue(parent_pid.exists() and grand_pid.exists(),'Synthetic process tree did not initialize')
                ids=[int(parent_pid.read_text()),int(grand_pid.read_text())]
                before=ws._windows_process_table_toolhelp()
                self.assertIsNotNone(before)
                self.assertEqual(ws._descendants(before,proc.pid),set(ids))
                ok,msg=ws.kill_search_process(proc)
                self.assertTrue(ok,msg)
                self.assertIsNotNone(proc.poll())
                after=ws._windows_process_table_toolhelp()
                self.assertIsNotNone(after)
                self.assertFalse(set(ids).intersection(after),f'Child survived STOP: {ids}')
            finally:
                if proc.poll() is None:
                    subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,timeout=10)
                    proc.wait(timeout=10)
                # Only owned synthetic PIDs, cleanup if descendants survive.
                after=ws._windows_process_table_toolhelp() or {}
                for pid in ids:
                    if pid in after:
                        subprocess.run(['taskkill','/PID',str(pid),'/F'],capture_output=True,timeout=10)


if __name__=='__main__':unittest.main(verbosity=2)