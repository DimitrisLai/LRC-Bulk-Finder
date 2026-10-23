"""Optional isolated Greek G2G installer and frozen-worker bridge.

No installation occurs on import. Only --install with explicit GUI consent can
download anything. No media files, system-wide pip, or administrator access needed
when a compatible Python interpreter is already installed.
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

MODEL = "g2g"
SCHEMA = 1
TOOLKIT = "gr-nlp-toolkit==0.3.0"
SAMPLE = "O Volos kai h Larisa einai sth Thessalia"
MAGIC = "@@LRC_G2G@@"
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def home(environ=None):
    env = os.environ if environ is None else environ
    if env.get("LRC_G2G_HOME"):
        return Path(env["LRC_G2G_HOME"]).expanduser()
    return Path(env.get("LOCALAPPDATA") or env.get("APPDATA") or
                (Path.home() / ".local" / "share")) / "LRCBulkFinder" / "G2G"


def venv_python(base=None):
    root = Path(base or home())
    return root / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def model_script():
    # For frozen builds, this script is deliberately shipped beside both EXEs.
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "g2g_sidecar.py"
    return Path(__file__).resolve().with_name("g2g_sidecar.py")


def installed(base=None):
    root = Path(base or home())
    manifest = root / "verified.json"
    if not (manifest.is_file() and venv_python(root).is_file() and model_script().is_file()):
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if data.get("schema") == SCHEMA and data.get("model") in ("g2g", "g2g_lite") \
                and data.get("verified") is True:
            return {"python": venv_python(root), "model": data["model"],
                    "script": model_script(), "home": root}
    except (OSError, TypeError, ValueError):
        return None
    return None


def _run(args, env=None, timeout=None):
    # Inherits stdout/stderr so the Control Center displays truthful progress.
    code = subprocess.call([str(x) for x in args], env=env,
                           timeout=timeout,
                           creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0)
    if code:
        raise RuntimeError("Installation step failed (exit code %s)." % code)


def _interpreter_candidates():
    if not getattr(sys, "frozen", False) and Path(sys.executable).is_file():
        yield [sys.executable]
    if os.name == "nt":
        for v in ("3.11", "3.12", "3.10", "3.13"):
            yield ["py", "-"+v]
    for name in ("python3.11", "python3.12", "python3.10", "python"):
        yield [name]


def _locate_python():
    for cmd in _interpreter_candidates():
        try:
            result = subprocess.run(
                [*cmd, "-c",
                 "import sys; print(sys.executable if (3,10) <= sys.version_info[:2] <= (3,13) else '')"],
                capture_output=True, text=True, timeout=12,
                creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0)
            output = result.stdout.strip()
            if result.returncode == 0 and output and Path(output).is_file():
                return Path(output)
        except (OSError, subprocess.TimeoutExpired):
            continue
    if os.name == "nt":
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python" /
            "Python311" / "python.exe",
            Path("C:/Program Files/Python311/python.exe"),
        ]
        for p in candidates:
            if p.is_file():
                return p
    return None


def _install_python_via_winget():
    if os.name != "nt" or not shutil.which("winget"):
        raise RuntimeError(
            "Python 3.10–3.13 was not found and automatic Windows Python setup "
            "is unavailable. Install Python 3.11 from python.org, then retry here.")
    print("Python not found. Installing official Python 3.11 using Windows winget "
          "(a Windows confirmation may appear).", flush=True)
    _run(["winget", "install", "--id", "Python.Python.3.11", "--exact",
          "--source", "winget", "--silent",
          "--accept-source-agreements", "--accept-package-agreements"],
         timeout=1800)
    found = _locate_python()
    if found is None:
        raise RuntimeError("Python installation finished, but Windows cannot locate "
                           "Python 3.11. Reopen the Control Center and retry.")
    return found


def setup(model=MODEL, allow_python_install=False):
    if model not in ("g2g", "g2g_lite"):
        raise ValueError("Unsupported G2G model")
    if not model_script().is_file():
        raise RuntimeError("g2g_sidecar.py is missing. Extract the complete "
                           "Windows distribution instead of copying only EXEs.")
    root = home()
    root.mkdir(parents=True, exist_ok=True)
    print("Greek AI setup — separate private environment:", root, flush=True)
    py = _locate_python()
    if py is None:
        if not allow_python_install:
            raise RuntimeError("Compatible Python is missing; automatic setup "
                               "was not approved.")
        py = _install_python_via_winget()
    print("Using Python:", py, flush=True)
    worker = venv_python(root)
    if not worker.is_file():
        print("Creating an isolated Python environment (your system packages stay unchanged)...", flush=True)
        _run([py, "-m", "venv", root / "venv"], timeout=180)
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8:backslashreplace"
    env["HF_HOME"] = str(root / "model-cache")
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    print("Installing CPU-compatible PyTorch (large download; may take a while)...", flush=True)
    _run([worker, "-m", "pip", "install", "--only-binary", ":all:",
          "--index-url", "https://download.pytorch.org/whl/cpu", "torch"],
         env=env, timeout=3600)
    print("Installing the published AUEB Greek NLP toolkit...", flush=True)
    _run([worker, "-m", "pip", "install", TOOLKIT], env=env, timeout=3600)
    print("Downloading/checking the Greek model and running a real conversion...", flush=True)
    _run([worker, model_script(), "--self-test", "--model", model],
         env=env, timeout=1800)
    marker = root / "verified.json"
    fd, temp = tempfile.mkstemp(dir=root, prefix=".verified-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            json.dump({"schema": SCHEMA, "model": model, "verified": True,
                       "toolkit": TOOLKIT}, fp)
            fp.flush()
            os.fsync(fp.fileno())
        os.replace(temp, marker)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    print("G2G READY: model downloaded, verified, and enabled for the standalone worker.", flush=True)


class ModelProcess:
    """Persistent local model process: text-only stdin/stdout; no network use at search time."""
    def __init__(self, details, popen=subprocess.Popen, wait_seconds=180):
        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8:backslashreplace"
        env["HF_HOME"] = str(details["home"] / "model-cache")
        env["HF_HUB_OFFLINE"] = "1"
        env["TRANSFORMERS_OFFLINE"] = "1"
        env["TOKENIZERS_PARALLELISM"] = "false"
        self.proc = popen(
            [str(details["python"]), "-u", str(details["script"]),
             "--serve", "--model", details["model"]],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", errors="replace", bufsize=1, env=env,
            creationflags=CREATE_NO_WINDOW if os.name == "nt" else 0)
        self.answers = queue.Queue(maxsize=20)
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()
        first = self._answer(wait_seconds)
        if first.get("status") != "ready":
            self.close()
            raise RuntimeError(first.get("error", "G2G companion did not start."))

    def _read(self):
        try:
            for line in self.proc.stdout:
                if line.startswith(MAGIC):
                    payload = json.loads(line[len(MAGIC):])
                    self.answers.put(payload, timeout=5)
        except (OSError, ValueError, TypeError, queue.Full) as exc:
            self.answers.put({"error": type(exc).__name__}, timeout=5)
        finally:
            try:
                self.answers.put_nowait({"error": "G2G process exited"})
            except queue.Full:
                pass

    def _answer(self, timeout):
        try:
            result = self.answers.get(timeout=timeout)
        except queue.Empty:
            self.close()
            raise RuntimeError("Greek AI did not respond in time; continue without AI.")
        if "error" in result:
            raise RuntimeError(result["error"][:220])
        return result

    def __call__(self, text):
        if not self.proc or self.proc.poll() is not None:
            raise RuntimeError("Greek AI stopped unexpectedly")
        try:
            self.proc.stdin.write(json.dumps({"text": str(text)}, ensure_ascii=False) + "\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError, UnicodeError) as exc:
            raise RuntimeError("Greek AI input failed") from exc
        response = self._answer(120)
        if not isinstance(response.get("text"), str):
            raise RuntimeError("Greek AI returned an invalid result")
        return response["text"]

    def close(self):
        proc = self.proc
        self.proc = None
        if proc and proc.poll() is None:
            try:
                if proc.stdin:
                    proc.stdin.close()
            except (OSError, ValueError):
                pass
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                proc.kill()
                proc.wait(timeout=5)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Optional local Greek model installation")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--model", choices=("g2g","g2g_lite"), default="g2g")
    parser.add_argument("--allow-python-install", action="store_true")
    args = parser.parse_args(argv)
    if not args.install:
        parser.error("--install is required")
    try:
        setup(args.model, allow_python_install=args.allow_python_install)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as e:
        print("SETUP FAILED: "+str(e), file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
