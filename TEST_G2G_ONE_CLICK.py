"""Never downloads a real model. Tests one-click consent, isolation, bridge and UI gates."""
from __future__ import annotations
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import g2g_auto
import g2g_integration


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.env=mock.patch.dict(os.environ,{"LRC_G2G_HOME":str(self.base)})
        self.env.start();self.addCleanup(self.env.stop)
        script=self.base/"g2g_sidecar.py"
        script.write_text("# fake local model sidecar\n",encoding="utf-8")
        self.script=mock.patch.object(g2g_auto,"model_script",return_value=script)
        self.script.start();self.addCleanup(self.script.stop)

    def _fake_runtime(self):
        exe=g2g_auto.venv_python(self.base)
        exe.parent.mkdir(parents=True,exist_ok=True)
        exe.write_text("",encoding="utf-8")
        return exe

    def test_missing_install_is_not_ready(self):
        self.assertIsNone(g2g_auto.installed())

    def test_verified_is_ready_only_with_python_and_sidecar(self):
        exe=self._fake_runtime()
        (self.base/"verified.json").write_text(
            json.dumps({"schema":1,"model":"g2g","verified":True}),encoding="utf-8")
        self.assertEqual(g2g_auto.installed()["python"],exe)
        exe.unlink()
        self.assertIsNone(g2g_auto.installed())

    def test_user_consents_then_installs_without_touching_global_python(self):
        py=self.base/"python.exe";py.touch()
        calls=[]
        def fake_call(args,**kwargs):
            calls.append(tuple(map(str,args)))
            if "-m" in args and "venv" in args:
                self._fake_runtime()
        with mock.patch.object(g2g_auto,"_locate_python",return_value=py),\
             mock.patch.object(g2g_auto,"_run",side_effect=fake_call):
            g2g_auto.setup("g2g",allow_python_install=True)
        self.assertEqual(len(calls),4)  # venv, CPU torch, toolkit, model self-test
        self.assertTrue(any("download.pytorch.org/whl/cpu" in " ".join(a) for a in calls))
        self.assertTrue(any("gr-nlp-toolkit==0.3.0" in a for a in calls))
        self.assertIsNotNone(g2g_auto.installed())
        self.assertFalse((self.base/"venv"/"Lib"/"site-packages"/"music.mp3").exists())

    def test_failure_does_not_create_verified_state(self):
        py=self.base/"python.exe";py.touch()
        def fail_if_model(args,**kwargs):
            if "--self-test" in args: raise RuntimeError("offline model init failed")
            if "-m" in args and "venv" in args:self._fake_runtime()
        with mock.patch.object(g2g_auto,"_locate_python",return_value=py),\
             mock.patch.object(g2g_auto,"_run",side_effect=fail_if_model):
            with self.assertRaises(RuntimeError):
                g2g_auto.setup(allow_python_install=False)
        self.assertIsNone(g2g_auto.installed())

    def test_no_python_without_permission_is_safe(self):
        with mock.patch.object(g2g_auto,"_locate_python",return_value=None),\
             mock.patch.object(g2g_auto,"_install_python_via_winget") as install:
            with self.assertRaisesRegex(RuntimeError,"not approved"):
                g2g_auto.setup(allow_python_install=False)
            install.assert_not_called()

    def test_installer_is_opt_in_not_triggered_by_import(self):
        self.assertFalse((self.base/"venv").exists())
        self.assertFalse((self.base/"verified.json").exists())

    def test_bridge_manager_uses_verified_model_only_when_frozen(self):
        exe=self._fake_runtime()
        (self.base/"verified.json").write_text(
            json.dumps({"schema":1,"model":"g2g","verified":True}),encoding="utf-8")
        with mock.patch("sys.frozen",True,create=True),\
             mock.patch("g2g_auto.ModelProcess") as sidecar:
            sidecar.return_value.return_value="καλημέρα"
            m=g2g_integration.G2GManager(cache_file=self.base/"cache.json")
            # Skip typical English words only.
            greek,status=m.convert("Kalimera sou",kind="title")
            self.assertEqual(greek,"καλημέρα")
            sidecar.assert_called_once()
            m.release_model()
            sidecar.return_value.close.assert_called_once()


class ProtocolTests(unittest.TestCase):
    def test_oversized_model_input_rejected_by_runtime_source(self):
        import g2g_sidecar
        parser_output=io.StringIO()
        with mock.patch.object(g2g_sidecar,"load_model",return_value=lambda x: type("D",(),{"text":"καλημέρα"})()),\
             mock.patch("sys.stdin",io.StringIO('{"text":"'+("a"*401)+'"}\n')),\
             mock.patch("sys.stdout",parser_output):
            self.assertEqual(g2g_sidecar.main(["--serve","--model","g2g"]),0)
        self.assertIn("Invalid or too-long input",parser_output.getvalue())
        self.assertIn(g2g_auto.MAGIC,parser_output.getvalue())

    def test_installer_cli_refuses_unrequested_actions(self):
        with self.assertRaises(SystemExit) as ex:
            g2g_auto.main([])
        self.assertEqual(ex.exception.code,2)


def display_available():
    if os.name=="nt":return True
    try:
        import tkinter as tk
        r=tk.Tk();r.withdraw();r.destroy();return True
    except Exception:return False


@unittest.skipUnless(display_available(),"No Tk display")
class GuiInstalledStatusTests(unittest.TestCase):
    def setUp(self):
        from LRC_Control_Center import ControlCenter
        self.folder=tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        env=mock.patch.dict(os.environ,{"APPDATA":self.folder.name})
        env.start();self.addCleanup(env.stop)
        self.root=ControlCenter()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)

    def test_frozen_model_disabled_until_setup_confirmed(self):
        with mock.patch("sys.frozen",True,create=True),\
             mock.patch("g2g_auto.installed",return_value=None):
            self.root._refresh_g2g_capability()
            self.assertEqual(str(self.root.g2g_checkbox.cget("state")),"disabled")
            self.assertNotIn("Greek Local AI — FULL",self.root._available_preset_names())
        with mock.patch("sys.frozen",True,create=True),\
             mock.patch("g2g_auto.installed",return_value={"verified":True}):
            self.root._refresh_g2g_capability()
            self.assertEqual(str(self.root.g2g_checkbox.cget("state")),"normal")
            self.assertIn("Greek Local AI — FULL",self.root._available_preset_names())


if __name__=="__main__":
    unittest.main()
