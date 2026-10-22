"""v2.7 additive Lyrics Studio precision, karaoke and library navigation.

Preserves all eight top-level tabs and original Classic Sync Lab. Tk widgets are
only updated on the UI thread. All saves create NEW marked candidate files.
"""
from __future__ import annotations
import json
import os
import queue
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from v260_studio import StudioDocument, read_lyric_file, format_time
from v260_player import StudioPlayer, PlaybackError, duration_seconds
from v260_studio_gui import V260StudioMixin
from v270_precision import (validate_timing, export_candidate, PROFILES, save_draft,
                             load_draft, clear_draft, playback_report)
from v270_waveform import read_waveform, window_peaks
from v270_vlc import VLCPlayer

KEY_CHOICES = ("<space>", "<Return>", "<F6>", "<F7>", "<F8>", "<Left>", "<Right>", "<Up>", "<Down>")
DEFAULT_KEYS = {"stamp": "<space>", "back": "<Left>", "forward": "<Right>"}

class V270Mixin(V260StudioMixin):
    def _studio_build_tabs(self):
        classic = super()._studio_build_tabs()
        self.precision_tab = ttk.Frame(self.studio_tabs, padding=8)
        self.studio_tabs.add(self.precision_tab, text="Precision & Karaoke")
        self._v270_build_precision()
        return classic

    def _build_results_dashboard(self):
        super()._build_results_dashboard()
        ttk.Button(self.dashboard_tab, text="Edit selected in Lyrics Studio",
                   command=self._v270_from_dashboard).pack(anchor="w", pady=3)

    def _build_review(self):
        super()._build_review()
        ttk.Button(self.review_tab, text="Edit selected candidate in Lyrics Studio",
                   command=self._v270_from_review).pack(anchor="w", pady=3)

    def _v270_build_precision(self):
        p = self.precision_tab
        self.loop_a = None
        self.loop_b = None
        self.karaoke_window = None
        self._v270_wave_peaks = []
        self._v270_wave_audio = None
        self._v270_wave_error = ""
        self._v270_wave_generation = 0
        self._v270_wave_cancel = threading.Event()
        self._v270_wave_queue = queue.Queue()
        self._v270_last_repaint = 0.0
        self._v270_source = None
        self._v270_zoom = tk.StringVar(value="1x")
        self._v270_rate = tk.StringVar(value="1.00x")
        self._v270_nudge = tk.StringVar(value="0.10")
        self._v270_profile = tk.StringVar(value="Standard 2 decimals")
        self._v270_start = tk.DoubleVar(value=0.0)
        self._v270_warn = tk.StringVar(value="Load lyrics to see timing diagnostics.")
        self._v270_wave_state = tk.StringVar(value="Choose audio to display a read-only waveform.")
        self._v270_loop_state = tk.StringVar(value="Loop: disabled")
        self._v270_source_warning = tk.StringVar(value="Import lyrics for instrumental audio to run line-level karaoke.")

        ttk.Label(p, text="Precision tools & instrumental karaoke", style="Header.TLabel").pack(anchor="w")
        ttk.Label(p, text="Karaoke plays your local instrumental and displays existing LRC lines. "
                  "It does NOT remove vocals or generate copyrighted lyrics.",
                  wraplength=940).pack(anchor="w", pady=(2, 8))
        row = ttk.Frame(p); row.pack(fill="x", pady=3)
        ttk.Button(row, text="Open karaoke display", command=self._v270_show_karaoke).pack(side="left", padx=2)
        ttk.Button(row, text="A = current time", command=self._v270_set_a).pack(side="left", padx=2)
        ttk.Button(row, text="B = current time", command=self._v270_set_b).pack(side="left", padx=2)
        ttk.Button(row, text="Clear A–B", command=self._v270_clear_loop).pack(side="left", padx=2)
        ttk.Button(row, text="Rewind 1 s", command=lambda: self._studio_seek_relative(-1)).pack(side="left", padx=2)
        ttk.Button(row, text="Rewind 5 s", command=lambda: self._studio_seek_relative(-5)).pack(side="left", padx=2)
        ttk.Label(p, textvariable=self._v270_loop_state).pack(anchor="w")
        row2 = ttk.Frame(p); row2.pack(fill="x", pady=6)
        ttk.Label(row2, text="Playback speed:").pack(side="left", padx=3)
        cb = ttk.Combobox(row2, state="readonly", width=9, textvariable=self._v270_rate,
                          values=("0.75x", "1.00x", "1.25x"))
        cb.pack(side="left", padx=3)
        cb.bind("<<ComboboxSelected>>", self._v270_change_speed)
        ttk.Label(row2, text="Non-1x requires compatible 64-bit VLC installed.").pack(side="left", padx=12)
        ttk.Button(row2, text="Playback diagnostics", command=self._v270_diagnostics).pack(side="right")
        row3 = ttk.Frame(p); row3.pack(fill="x", pady=4)
        ttk.Label(row3, text="Waveform zoom:").pack(side="left")
        zoom = ttk.Combobox(row3, textvariable=self._v270_zoom, state="readonly",
                            width=7, values=("1x", "2x", "4x", "8x"))
        zoom.pack(side="left", padx=5)
        zoom.bind("<<ComboboxSelected>>", lambda e: self._v270_draw_waveform())
        ttk.Button(row3, text="Reload waveform", command=self._v270_begin_waveform).pack(side="left")
        ttk.Button(row3, text="Cancel waveform", command=self._v270_cancel_waveform).pack(side="left", padx=4)
        self.wave_canvas = tk.Canvas(p, width=860, height=146, background="#162235",
                                     highlightthickness=1, highlightbackground="#63758a")
        self.wave_canvas.pack(fill="x", pady=6)
        self.wave_canvas.bind("<ButtonRelease-1>", self._v270_canvas_seek)
        ttk.Label(p, textvariable=self._v270_wave_state).pack(anchor="w")
        ttk.Label(p, text="Waveform window start (seconds):").pack(anchor="w", pady=(4, 0))
        self.wave_scroll = ttk.Scale(p, from_=0, to=1, variable=self._v270_start,
                                     command=lambda _: self._v270_draw_waveform())
        self.wave_scroll.pack(fill="x")
        ttk.Label(p, textvariable=self._v270_warn, wraplength=930).pack(anchor="w", pady=(8, 4))
        ttk.Button(p, text="Check all timestamp warnings", command=self._v270_warnings).pack(anchor="w")

        row4 = ttk.Frame(p); row4.pack(fill="x", pady=7)
        ttk.Label(row4, text="Nudge size (seconds):").pack(side="left", padx=3)
        ttk.Combobox(row4, textvariable=self._v270_nudge, state="readonly", width=8,
                     values=("0.01", "0.05", "0.10")).pack(side="left", padx=3)
        ttk.Button(row4, text="Nudge selected earlier",
                   command=lambda: self._studio_shift(-float(self._v270_nudge.get()))).pack(side="left", padx=4)
        ttk.Button(row4, text="Nudge selected later",
                   command=lambda: self._studio_shift(float(self._v270_nudge.get()))).pack(side="left", padx=4)
        row5 = ttk.Frame(p); row5.pack(fill="x", pady=5)
        ttk.Label(row5, text="LRC export profile:").pack(side="left", padx=4)
        ttk.Combobox(row5, textvariable=self._v270_profile, state="readonly", width=24,
                     values=tuple(PROFILES)).pack(side="left", padx=3)
        ttk.Button(row5, text="Save NEW unverified candidate...",
                   command=self._studio_save).pack(side="left", padx=7)
        ttk.Label(p, text="Keyboard shortcuts work ONLY while the lyric table is focused; no global shortcuts.",
                  wraplength=900).pack(anchor="w", pady=(5, 2))
        keys = self._v270_read_keys()
        self._v270_keys = {}
        key_frame = ttk.Frame(p); key_frame.pack(fill="x", pady=2)
        for label, action in (("Stamp", "stamp"), ("Rewind", "back"), ("Forward", "forward")):
            ttk.Label(key_frame, text=label + ":").pack(side="left", padx=3)
            var = tk.StringVar(value=keys[action])
            self._v270_keys[action] = var
            ttk.Combobox(key_frame, state="readonly", width=9, textvariable=var,
                         values=KEY_CHOICES).pack(side="left", padx=3)
        ttk.Button(key_frame, text="Apply shortcuts", command=self._v270_apply_keys).pack(side="left", padx=8)
        self._v270_apply_keys(save=False)
        self.after(125, self._v270_wave_poll)

    def _v270_key_file(self):
        root = Path(os.environ.get("APPDATA") or Path.home() / ".config")
        return root / "LRCBulkFinder" / "studio_shortcuts.json"

    def _v270_read_keys(self):
        try:
            raw = json.loads(self._v270_key_file().read_text(encoding="utf-8"))
            values = raw.get("keys", {})
            if set(values) == set(DEFAULT_KEYS) and len(set(values.values())) == 3 and all(x in KEY_CHOICES for x in values.values()):
                return values
        except (OSError, ValueError, AttributeError):
            pass
        return dict(DEFAULT_KEYS)

    def _v270_apply_keys(self, save=True):
        values = {a: v.get() for a, v in self._v270_keys.items()}
        if len(set(values.values())) != 3 or any(s not in KEY_CHOICES for s in values.values()):
            if save:
                self._dialog("showerror", "Keyboard shortcuts", "Choose three different permitted keys.")
            return
        old = getattr(self, "_v270_applied", DEFAULT_KEYS)
        for key in set(old.values()) | set(DEFAULT_KEYS.values()):
            self.studio_tree.unbind(key)
        actions = {"stamp": lambda e: self._studio_stamp_key(),
                   "back": lambda e: self._v270_key_seek(-1),
                   "forward": lambda e: self._v270_key_seek(1)}
        for action, key in values.items():
            self.studio_tree.bind(key, actions[action])
        self._v270_applied = values
        if save:
            try:
                dest = self._v270_key_file()
                dest.parent.mkdir(parents=True, exist_ok=True)
                tmp = dest.with_suffix(".tmp")
                tmp.write_text(json.dumps({"keys": values}), encoding="utf-8")
                os.replace(tmp, dest)
            except OSError as ex:
                self._dialog("showwarning", "Keyboard shortcuts", str(ex))

    def _v270_key_seek(self, seconds):
        self._studio_seek_relative(seconds)
        return "break"

    def _v270_from_dashboard(self):
        row = self._dashboard_selected()
        if not row:
            self._dialog("showinfo", "Lyrics Studio", "Select one track in the Results dashboard.")
            return
        self._v270_open(row["path"])

    def _v270_from_review(self):
        row = self._selection()
        if not row or not row.get("has_mp3"):
            self._dialog("showinfo", "Lyrics Studio", "Select a candidate with a matching audio file first.")
            return
        self._v270_open(row["mp3"], row["path"])

    def _v270_open(self, audio, lrc=None):
        if not self._studio_will_replace():
            return False
        track = Path(audio)
        if not track.is_file() or track.is_symlink():
            self._dialog("showerror", "Lyrics Studio", "Audio is missing or unsafe.")
            return False
        self._v270_cancel_waveform()
        self.studio_player.close()
        self.studio_audio.set(str(track))
        self._studio_duration = duration_seconds(track)
        self.studio_doc = None
        self._studio_saved = True
        self._v270_source = None
        self._studio_render()
        try:
            self.studio_player.load(track)
        except (OSError, ValueError, PlaybackError) as ex:
            self.studio_status.set("Embedded playback unavailable: " + str(ex))
        chosen = Path(lrc) if lrc else track.with_suffix(".lrc")
        if chosen.is_file() and not chosen.is_symlink():
            self._studio_load_lyrics(chosen)
        else:
            self._v270_offer_draft()
        self.notebook.select(self.sync_tab)
        self.studio_tabs.select(self.studio_frame)
        self._v270_begin_waveform()
        return True

    def _studio_choose_audio(self):
        # Preserve the existing file-picker semantics; add waveform and recovery.
        previous = self.studio_audio.get()
        super()._studio_choose_audio()
        if self.studio_audio.get() != previous:
            self._v270_cancel_waveform()
            self._v270_source = self.studio_audio.get() if Path(self.studio_audio.get()).with_suffix(".lrc").is_file() else None
            self._v270_begin_waveform()
            if self.studio_doc is None:
                self._v270_offer_draft()

    def _studio_load_lyrics(self, source):
        super()._studio_load_lyrics(source)
        if self.studio_doc is not None:
            self._v270_source = str(source)
            self._v270_warnings()
            self._v270_offer_draft()

    def _v270_offer_draft(self):
        if not self.studio_audio.get():
            return
        try:
            recovered = load_draft(self.studio_audio.get(), self._v270_source)
        except ValueError:
            return
        if recovered and self._dialog("askyesno", "Recover saved Studio draft?",
                                      "A matching private draft exists. Restore its UNVERIFIED timing changes?"):
            self.studio_doc = StudioDocument(recovered)
            self._studio_saved = False
            self._studio_render()
            self.studio_status.set("Recovered private draft (UNVERIFIED).")
            self._v270_warnings()

    def _studio_edit(self, action):
        before = list(self.studio_doc.lines) if self.studio_doc else []
        super()._studio_edit(action)
        if self.studio_doc and before != self.studio_doc.lines:
            self._v270_store_draft()
            self._v270_warnings()

    def _studio_undo(self):
        before = list(self.studio_doc.lines) if self.studio_doc else []
        super()._studio_undo()
        if self.studio_doc and before != self.studio_doc.lines:
            self._v270_store_draft()
            self._v270_warnings()

    def _studio_redo(self):
        before = list(self.studio_doc.lines) if self.studio_doc else []
        super()._studio_redo()
        if self.studio_doc and before != self.studio_doc.lines:
            self._v270_store_draft()
            self._v270_warnings()

    def _v270_store_draft(self):
        if self.studio_doc and self.studio_audio.get():
            try:
                save_draft(self.studio_audio.get(), self.studio_doc.lines, self._v270_source)
            except (ValueError, OSError) as ex:
                self.studio_status.set("Draft recovery unavailable: " + str(ex))

    def _v270_warnings(self):
        if not self.studio_doc:
            self._v270_warn.set("Load lyrics first.")
            return
        items = validate_timing(self.studio_doc.lines, self._studio_duration)
        if not items:
            self._v270_warn.set("No timing warnings found. Listen before treating alignment as accurate.")
        else:
            preview = "; ".join(f"line {w.line}: {w.message}" for w in items[:5])
            self._v270_warn.set(f"{len(items)} timing warning(s): {preview}")

    def _studio_save(self):
        if self.process is not None and self.process.poll() is None:
            self._dialog("showwarning", "Search running", "Finish the search before writing new candidates.")
            return
        if not self.studio_doc or not self.studio_audio.get():
            self._dialog("showerror", "Lyrics Studio", "Choose audio and load lyrics first.")
            return
        invalid = [w for w in validate_timing(self.studio_doc.lines, self._studio_duration)
                   if w.code in ("range", "duration", "duplicate", "order")]
        if invalid:
            self._dialog("showerror", "Unsafe LRC timestamps", "Correct invalid/duplicate/out-of-order or beyond-duration lines first.")
            return
        profile = self._v270_profile.get()
        if not self._dialog("askyesno", "Save NEW UNVERIFIED candidate?",
                            "Create a new numbered .candidate.lrc with the chosen export profile?\n"
                            "This DOES NOT overwrite any audio, tags, original LRC, or existing candidate."):
            return
        try:
            target = export_candidate(self.studio_audio.get(), self.studio_doc.lines, profile)
            self._studio_saved = True
            clear_draft(self.studio_audio.get())
            self.studio_status.set("Saved UNVERIFIED candidate: " + str(target))
            self._dialog("showinfo", "Candidate saved", str(target))
            self._refresh_review()
        except (OSError, ValueError) as ex:
            self._dialog("showerror", "Cannot save candidate", str(ex))

    def _v270_set_a(self):
        self.loop_a = round(self.studio_player.position(), 3)
        self.loop_b = None  # Never retain a stale B from a previous loop.
        self._v270_show_loop()

    def _v270_set_b(self):
        candidate = round(self.studio_player.position(), 3)
        if self.loop_a is None or candidate <= self.loop_a + 0.1:
            self._dialog("showwarning", "A–B loop", "Choose A first, then B later than A.")
            return
        self.loop_b = candidate
        self._v270_show_loop()

    def _v270_clear_loop(self):
        self.loop_a = self.loop_b = None
        self._v270_show_loop()

    def _v270_show_loop(self):
        self._v270_loop_state.set(
            f"Loop A {self.loop_a:.2f}s → B {self.loop_b:.2f}s" if
            self.loop_a is not None and self.loop_b is not None else
            "Loop: set point A, then set later point B.")

    def _v270_change_speed(self, event=None):
        speed = float(self._v270_rate.get().rstrip("x"))
        if speed == 1:
            if isinstance(self.studio_player, VLCPlayer):
                pos = self.studio_player.position()
                self.studio_player.close()
                self.studio_player = StudioPlayer()
                try:
                    self.studio_player.load(self.studio_audio.get())
                    self.studio_player.seek(pos)
                except (PlaybackError, ValueError, OSError) as ex:
                    self.studio_status.set("1x playback unavailable: " + str(ex))
            return
        if not self.studio_audio.get():
            self._v270_rate.set("1.00x")
            self._dialog("showinfo", "Playback speed", "Choose audio first.")
            return
        old = self.studio_player
        try:
            if isinstance(old, VLCPlayer):
                old.set_speed(speed)
            else:
                candidate = VLCPlayer()
                try:
                    candidate.load(self.studio_audio.get())
                    candidate.set_speed(speed)
                    candidate.seek(old.position())
                except Exception:
                    candidate.close()
                    raise
                self.studio_player = candidate
                old.close()
        except (OSError, ValueError, PlaybackError) as ex:
            self._v270_rate.set("1.00x" if not isinstance(old, VLCPlayer) else f"{old.rate:.2f}x")
            self._dialog("showwarning", "Playback speed unavailable",
                         "A compatible VLC installation is required: " + str(ex))

    def _v270_diagnostics(self):
        codec = Path(self.studio_audio.get()).suffix.lower() if self.studio_audio.get() else None
        report = playback_report(self.studio_player, codec)
        report["waveform"] = "available" if self._v270_wave_peaks else "unavailable"
        self._dialog("showinfo", "Playback diagnostics (private)", json.dumps(report, indent=2))

    def _v270_cancel_waveform(self):
        self._v270_wave_cancel.set()
        self._v270_wave_generation += 1

    def _v270_begin_waveform(self):
        self._v270_cancel_waveform()
        track = self.studio_audio.get()
        self._v270_wave_audio = track
        self._v270_wave_peaks = []
        self._v270_draw_waveform()
        if not track or not Path(track).is_file():
            return
        generation = self._v270_wave_generation
        event = threading.Event()
        self._v270_wave_cancel = event
        self._v270_wave_state.set("Computing bounded read-only waveform...")
        def work():
            try:
                result = read_waveform(track, 1100, event)
                self._v270_wave_queue.put((generation, result, ""))
            except (ValueError, OSError, RuntimeError) as ex:
                self._v270_wave_queue.put((generation, None, str(ex)))
        threading.Thread(target=work, daemon=True).start()

    def _v270_wave_poll(self):
        try:
            while True:
                generation, peaks, error = self._v270_wave_queue.get_nowait()
                if generation != self._v270_wave_generation:
                    continue
                if peaks is not None:
                    self._v270_wave_peaks = peaks
                    self._v270_wave_state.set("Read-only waveform ready. Click waveform to seek.")
                    self._v270_draw_waveform()
                else:
                    self._v270_wave_state.set("Waveform unavailable: " + (error or "cancelled"))
        except queue.Empty:
            pass
        try:
            if self.winfo_exists():
                self.after(125, self._v270_wave_poll)
        except tk.TclError:
            pass

    def _v270_draw_waveform(self):
        c = self.wave_canvas
        c.delete("all")
        w = max(200, c.winfo_width())
        h = max(90, c.winfo_height())
        c.create_line(0, h // 2, w, h // 2, fill="#708b9b")
        if not self._v270_wave_peaks or self._studio_duration <= 0:
            c.create_text(w // 2, h // 2 - 15, text="No waveform data", fill="white")
            return
        zoom = int(self._v270_zoom.get().rstrip("x"))
        total = self._studio_duration
        view = total / zoom
        start = min(max(0, self._v270_start.get()), max(0, total - view))
        self.wave_scroll.configure(to=max(0.01, total - view))
        part = window_peaks(self._v270_wave_peaks, total, start, view)
        if not part:
            return
        for x in range(w):
            index = min(len(part) - 1, int(x / w * len(part)))
            amp = max(0.01, min(1.0, part[index]))
            peak = amp * (h / 2 - 12)
            c.create_line(x, h / 2 - peak, x, h / 2 + peak, fill="#56b7ce")
        if self.studio_doc:
            for line in self.studio_doc.lines:
                if start <= line.seconds <= start + view:
                    x = int((line.seconds - start) / view * w)
                    c.create_line(x, 0, x, h, fill="#ddb765", dash=(2, 4))
        if self.loop_a is not None:
            for point in (self.loop_a, self.loop_b):
                if point is not None and start <= point <= start + view:
                    x = int((point - start) / view * w)
                    c.create_line(x, 0, x, h, fill="#e36769", width=2)
        now = self.studio_player.position()
        if start <= now <= start + view:
            x = int((now - start) / view * w)
            c.create_line(x, 0, x, h, fill="white", width=2)

    def _v270_canvas_seek(self, event):
        if self._studio_duration <= 0:
            return
        view = self._studio_duration / int(self._v270_zoom.get().rstrip("x"))
        start = min(self._v270_start.get(), self._studio_duration - view)
        second = start + min(1, max(0, event.x / max(1, self.wave_canvas.winfo_width()))) * view
        self._studio_seek(second)

    def _v270_show_karaoke(self):
        if not self.studio_doc or not self.studio_audio.get():
            self._dialog("showinfo", "Instrumental karaoke", "Choose instrumental audio and import its LRC first.")
            return
        if self.karaoke_window is not None and self.karaoke_window.winfo_exists():
            self.karaoke_window.lift()
            return
        win = tk.Toplevel(self)
        win.title("LRC Bulk Finder — Instrumental Karaoke")
        win.geometry("1000x560")
        win.configure(bg="#101b2d")
        win.protocol("WM_DELETE_WINDOW", self._v270_close_karaoke)
        win.bind("<Escape>", lambda e: self._v270_close_karaoke())
        win.bind("<F11>", lambda e: win.attributes("-fullscreen", not bool(win.attributes("-fullscreen"))))
        win.bind("<space>", lambda e: self._v270_karaoke_play_pause())
        self.karaoke_window = win
        tk.Label(win, text="KARAOKE • Instrumental + LRC", fg="#a8bbd4", bg="#101b2d",
                 font=("Segoe UI", 16, "bold")).pack(pady=(60, 35))
        self.karaoke_current = tk.StringVar(value="♪")
        self.karaoke_next = tk.StringVar(value="")
        tk.Label(win, textvariable=self.karaoke_current, fg="#f8dc85", bg="#101b2d",
                 font=("Segoe UI", 33, "bold"), wraplength=940).pack(fill="both", expand=True, padx=20)
        tk.Label(win, textvariable=self.karaoke_next, fg="#a7b9ce", bg="#101b2d",
                 font=("Segoe UI", 22), wraplength=940).pack(fill="x", pady=(0, 48))
        tk.Button(win, text="Play / Pause  (Space)", command=self._v270_karaoke_play_pause,
                  font=("Segoe UI", 12), bg="#283d58", fg="#ffffff", activebackground="#385a7b",
                  activeforeground="#ffffff").pack(side="bottom", pady=(3, 7))
        tk.Label(win, text="Line-by-line timing • Esc closes • F11 fullscreen • No vocal removal",
                 fg="#8596ac", bg="#101b2d", font=("Segoe UI", 11)).pack(side="bottom", pady=12)
        self._v270_karaoke_refresh()

    def _v270_karaoke_play_pause(self):
        try:
            if self.studio_player.is_playing():
                self.studio_player.pause()
            else:
                self.studio_player.play()
        except (PlaybackError, ValueError) as ex:
            self._dialog("showerror", "Instrumental karaoke", str(ex))
        return "break"

    def _v270_close_karaoke(self):
        try:
            if self.karaoke_window is not None:
                self.karaoke_window.destroy()
        except tk.TclError:
            pass
        self.karaoke_window = None

    def _v270_karaoke_refresh(self):
        if self.karaoke_window is None or not self.karaoke_window.winfo_exists() or not self.studio_doc:
            return
        idx = self.studio_doc.active_line(self.studio_player.position())
        lines = self.studio_doc.lines
        self.karaoke_current.set(lines[idx].text if idx is not None else "♪")
        self.karaoke_next.set(lines[idx + 1].text if idx is not None and idx + 1 < len(lines)
                              else lines[0].text if idx is None and lines else "")

    def _studio_tick(self):
        # Inherited routine schedules the next Tk tick and maintains original live preview.
        super()._studio_tick()
        try:
            if self.loop_a is not None and self.loop_b is not None and self.studio_player.is_playing():
                if self.studio_player.position() >= self.loop_b:
                    self._studio_seek(self.loop_a)
            self._v270_karaoke_refresh()
            if self.studio_tabs.select() == str(self.precision_tab):
                import time
                now = time.monotonic()
                if now - self._v270_last_repaint >= .5:
                    self._v270_draw_waveform()
                    self._v270_last_repaint = now
        except (tk.TclError, AttributeError):
            pass

    def _studio_can_close(self):
        self._v270_cancel_waveform()
        if not super()._studio_can_close():
            return False
        self._v270_close_karaoke()
        return True
