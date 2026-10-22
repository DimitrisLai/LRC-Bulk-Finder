"""Lyrics Studio v2.6 Tkinter UI, embedded INSIDE the existing Sync Lab tab.

The original experimental Sync Lab remains available, unchanged, in a nested
'Classic Sync Lab' workspace. Studio files are never saved on import or edit.
"""
from __future__ import annotations
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from lyric_sync_lab import estimate_timestamps, plain_lines
from v260_player import PlaybackError, StudioPlayer, duration_seconds
from v260_studio import LyricLine, StudioDocument, format_time, read_lyric_file, render_candidate, save_candidate


class V260StudioMixin:
    def _studio_build_tabs(self):
        self.studio_tabs = ttk.Notebook(self.sync_tab)
        self.studio_tabs.pack(fill="both", expand=True)
        self.studio_frame = ttk.Frame(self.studio_tabs, padding=8)
        self.classic_sync_frame = ttk.Frame(self.studio_tabs, padding=8)
        self.studio_tabs.add(self.studio_frame, text="Lyrics Studio")
        self.studio_tabs.add(self.classic_sync_frame, text="Classic Sync Lab")
        self._studio_build()
        return self.classic_sync_frame

    def _studio_build(self):
        area = self.studio_frame
        self.studio_player = StudioPlayer()
        self.studio_doc = None
        self._studio_saved = True
        self._studio_active = None
        self.studio_audio = tk.StringVar()
        self.studio_status = tk.StringVar(value="Choose a track and a timed LRC, or import text from Classic Sync Lab.")
        self.studio_position = tk.StringVar(value="00:00.00 / ?")
        self.studio_preview = tk.StringVar(value="No lyric line at this position.")

        ttk.Label(area, text="Lyrics Studio — line-by-line synchronization",
                  style="Header.TLabel").pack(anchor="w")
        ttk.Label(area, text="Offline workspace. Listen, preview and correct individual timestamps. "
                  "SAVE creates only a NEW UNVERIFIED .candidate.lrc; existing music and lyrics stay unchanged.",
                  wraplength=930).pack(anchor="w", pady=(3, 6))
        top = ttk.Frame(area)
        top.pack(fill="x")
        ttk.Entry(top, textvariable=self.studio_audio, state="readonly").pack(side="left", fill="x", expand=True)
        ttk.Button(top, text="Choose audio...", command=self._studio_choose_audio).pack(side="left", padx=3)
        ttk.Button(top, text="Load LRC...", command=self._studio_choose_lyrics).pack(side="left", padx=3)
        ttk.Button(top, text="From Classic Sync Lab", command=self._studio_from_classic).pack(side="left", padx=3)

        player = ttk.Frame(area)
        player.pack(fill="x", pady=6)
        ttk.Button(player, text="Play / Resume", command=self._studio_play).pack(side="left", padx=2)
        ttk.Button(player, text="Pause", command=self._studio_pause).pack(side="left", padx=2)
        ttk.Button(player, text="Stop", command=self._studio_stop).pack(side="left", padx=2)
        ttk.Button(player, text="−5 seconds", command=lambda: self._studio_seek_relative(-5)).pack(side="left", padx=2)
        ttk.Button(player, text="+5 seconds", command=lambda: self._studio_seek_relative(5)).pack(side="left", padx=2)
        ttk.Label(player, textvariable=self.studio_position).pack(side="left", padx=12)
        self.studio_seek = ttk.Scale(area, from_=0, to=100, orient="horizontal")
        self.studio_seek.pack(fill="x")
        self.studio_seek.bind("<ButtonRelease-1>", self._studio_seek_release)

        ttk.Label(area, text="Live lyric preview").pack(anchor="w", pady=(6, 0))
        ttk.Label(area, textvariable=self.studio_preview, wraplength=920,
                  font=("Segoe UI", 11, "bold")).pack(fill="x", pady=(1, 5))
        body = ttk.Frame(area)
        body.pack(fill="both", expand=True)
        self.studio_tree = ttk.Treeview(body, columns=("time", "text"),
                                        show="headings", selectmode="extended", height=10)
        self.studio_tree.heading("time", text="Timestamp")
        self.studio_tree.heading("text", text="Lyric line")
        self.studio_tree.column("time", anchor="w", width=110, stretch=False)
        self.studio_tree.column("text", anchor="w", width=700, stretch=True)
        self.studio_tree.tag_configure("playing", background="#d8efe7")
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.studio_tree.yview)
        self.studio_tree.configure(yscrollcommand=scrollbar.set)
        self.studio_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.studio_tree.bind("<Double-1>", self._studio_seek_selected)
        self.studio_tree.bind("<space>", self._studio_stamp_key)

        edits = ttk.Frame(area)
        edits.pack(fill="x", pady=(6, 2))
        ttk.Button(edits, text="Stamp selected at playback",
                   command=self._studio_stamp).pack(side="left", padx=2)
        ttk.Button(edits, text="−0.10 s", command=lambda: self._studio_shift(-0.10)).pack(side="left", padx=2)
        ttk.Button(edits, text="+0.10 s", command=lambda: self._studio_shift(0.10)).pack(side="left", padx=2)
        ttk.Label(edits, text="Exact seconds:").pack(side="left", padx=(12, 2))
        self.studio_exact = tk.StringVar()
        ttk.Entry(edits, textvariable=self.studio_exact, width=11).pack(side="left", padx=2)
        ttk.Button(edits, text="Set time", command=self._studio_exact).pack(side="left", padx=2)
        ttk.Button(edits, text="Undo", command=self._studio_undo).pack(side="left", padx=4)
        ttk.Button(edits, text="Redo", command=self._studio_redo).pack(side="left", padx=2)
        ttk.Label(area, textvariable=self.studio_status, wraplength=930).pack(anchor="w", pady=(3, 5))
        ttk.Button(area, text="Save NEW UNVERIFIED candidate (keep all originals)",
                   command=self._studio_save).pack(fill="x", pady=3)
        self.after(150, self._studio_tick)

    def _studio_will_replace(self):
        if self.studio_doc is not None and not self._studio_saved:
            return bool(self._dialog("askyesno", "Discard unsaved Studio edits?",
                                     "Unsaved timing changes will be lost. Continue?"))
        return True

    def _studio_choose_audio(self):
        filename = self._file_dialog("askopenfilename", title="Select audio for Lyrics Studio",
                filetypes=[("Audio files", "*.mp3 *.wav *.ogg *.flac *.m4a *.mp4 *.opus"),
                           ("All files", "*.*")])
        if not filename:
            return
        if not self._studio_will_replace():
            return
        p = Path(filename)
        self.studio_player.close()
        self.studio_audio.set(str(p))
        self.studio_doc = None
        self._studio_saved = True
        self._studio_render()
        try:
            self.studio_player.load(p)
            self.studio_status.set("Embedded player is ready. Load or import timed lyrics.")
        except (ValueError, OSError, PlaybackError) as ex:
            self.studio_status.set("Embedded player unavailable: " + str(ex))
        source = p.with_suffix(".lrc")
        if source.is_file() and not source.is_symlink():
            self._studio_load_lyrics(source)

    def _studio_choose_lyrics(self):
        filename = self._file_dialog("askopenfilename", title="Import existing LRC (read-only)",
                            filetypes=[("LRC lyrics", "*.lrc"), ("All files", "*.*")])
        if filename:
            if not self._studio_will_replace():
                return
            p = Path(filename)
            if self.studio_audio.get() and p.name.lower() != Path(self.studio_audio.get()).with_suffix(".lrc").name.lower():
                if not self._dialog("askyesno", "Different lyric filename",
                        "Lyrics do not have the selected audio's filename. Import anyway (read-only)?"):
                    return
            self._studio_load_lyrics(p)

    def _studio_load_lyrics(self, source):
        try:
            lines = read_lyric_file(source)
            self.studio_doc = StudioDocument(lines)
            self._studio_saved = True
            self._studio_render()
            self.studio_status.set(f"Read-only import: {len(lines)} lines. All edits stay in memory until Save.")
        except (OSError, ValueError) as ex:
            self._dialog("showerror", "Cannot import LRC", str(ex))

    def _studio_from_classic(self):
        if not self._studio_will_replace():
            return
        p = self.studio_audio.get() or getattr(self, "sync_audio", tk.StringVar()).get()
        if p and not self.studio_audio.get():
            self.studio_audio.set(p)
            try:
                self.studio_player.load(p)
            except (ValueError, OSError, PlaybackError) as ex:
                self.studio_status.set("Embedded player unavailable: " + str(ex))
        try:
            draft = self.sync_draft.get("1.0", "end").strip()
            try:
                from v260_studio import parse_lrc
                lines = parse_lrc(draft)
            except ValueError:
                source_lines = plain_lines(self.sync_source.get("1.0", "end"))
                duration = duration_seconds(p) if p else 0.0
                times = (estimate_timestamps(source_lines, duration) if duration > 0
                         else [float(i + 1) for i in range(len(source_lines))])
                lines = [LyricLine(t, row) for t, row in zip(times, source_lines)]
            self.studio_doc = StudioDocument(lines)
            self._studio_saved = False  # Generated timings must not imply verification.
            self._studio_render()
            self.studio_tabs.select(self.studio_frame)
            self.studio_status.set("IMPORTED UNVERIFIED estimates/taps. Play and correct each line.")
        except (OSError, ValueError) as ex:
            self._dialog("showerror", "Import from Classic Sync Lab", str(ex))

    def _studio_selected(self):
        if self.studio_doc is None:
            raise ValueError("Load or import lyrics first")
        positions = [int(i) for i in self.studio_tree.selection()]
        if not positions:
            raise ValueError("Select one or more lyric lines first")
        return positions

    def _studio_render(self, selection=()):
        old = tuple(selection) if selection else tuple(self.studio_tree.selection())
        self.studio_tree.delete(*self.studio_tree.get_children())
        if self.studio_doc is not None:
            for i, line in enumerate(self.studio_doc.lines):
                self.studio_tree.insert("", "end", iid=str(i), values=(format_time(line.seconds), line.text))
        good = [str(i) for i in old if str(i) in self.studio_tree.get_children()]
        if good:
            self.studio_tree.selection_set(good)
        self._studio_active = None

    def _studio_edit(self, action):
        try:
            action()
            self._studio_saved = False
            self._studio_render()
            try:
                render_candidate(self.studio_doc.lines)
                self.studio_status.set("Timing changed in memory. Save only when you have checked the preview.")
            except ValueError as ex:
                self.studio_status.set("Fix timing before saving: " + str(ex))
        except (IndexError, ValueError) as ex:
            self._dialog("showerror", "Timing correction", str(ex))

    def _studio_shift(self, seconds):
        self._studio_edit(lambda: self.studio_doc.shift(self._studio_selected(), seconds))

    def _studio_exact(self):
        def perform():
            selected = self._studio_selected()
            if len(selected) != 1:
                raise ValueError("Select exactly one lyric line")
            self.studio_doc.set_time(selected[0], float(self.studio_exact.get()))
        self._studio_edit(perform)

    def _studio_stamp(self):
        def perform():
            selected = self._studio_selected()
            if len(selected) != 1:
                raise ValueError("Select exactly one lyric line")
            self.studio_doc.set_time(selected[0], self.studio_player.position())
        self._studio_edit(perform)
        if self.studio_doc:
            selected = self.studio_tree.selection()
            if selected and int(selected[0]) + 1 < len(self.studio_doc.lines):
                self.studio_tree.selection_set(str(int(selected[0]) + 1))
                self.studio_tree.see(str(int(selected[0]) + 1))

    def _studio_stamp_key(self, event=None):
        self._studio_stamp()
        return "break"

    def _studio_undo(self):
        if self.studio_doc and self.studio_doc.undo():
            self._studio_saved = False
            self._studio_render()

    def _studio_redo(self):
        if self.studio_doc and self.studio_doc.redo():
            self._studio_saved = False
            self._studio_render()

    def _studio_play(self):
        try:
            if self.studio_player.path is None and self.studio_audio.get():
                self.studio_player.load(self.studio_audio.get())
            self.studio_player.play()
        except (ValueError, PlaybackError) as ex:
            self._dialog("showerror", "Embedded player", str(ex))

    def _studio_pause(self):
        try:
            self.studio_player.pause()
        except PlaybackError as ex:
            self._dialog("showerror", "Embedded player", str(ex))

    def _studio_stop(self):
        self.studio_player.stop()

    def _studio_seek(self, second):
        try:
            self.studio_player.seek(max(0.0, float(second)))
        except (ValueError, PlaybackError) as ex:
            self._dialog("showerror", "Seek failed", str(ex))

    def _studio_seek_relative(self, delta):
        self._studio_seek(self.studio_player.position() + delta)

    def _studio_seek_release(self, event=None):
        self._studio_seek(float(self.studio_seek.get()))

    def _studio_seek_selected(self, event=None):
        if self.studio_doc and self.studio_tree.selection():
            line = self.studio_doc.lines[int(self.studio_tree.selection()[0])]
            self._studio_seek(line.seconds)

    def _studio_tick(self):
        try:
            if not self.winfo_exists():
                return
            current = self.studio_player.position()
            total = duration_seconds(self.studio_audio.get()) if self.studio_audio.get() else 0.0
            self.studio_position.set(format_time(current).strip("[]") +
                                     (" / " + format_time(total).strip("[]") if total > 0 else " / ?"))
            if total > 0:
                self.studio_seek.configure(to=total)
                # Do not interrupt a user dragging the seek bar.
                if not self.studio_seek.focus_get() == self.studio_seek:
                    self.studio_seek.set(min(total, current))
            if self.studio_doc:
                idx = self.studio_doc.active_line(current)
                self.studio_preview.set(self.studio_doc.lines[idx].text if idx is not None
                                        else "No lyric line at this position.")
                if idx != self._studio_active:
                    if self._studio_active is not None and self.studio_tree.exists(str(self._studio_active)):
                        self.studio_tree.item(str(self._studio_active), tags=())
                    if idx is not None:
                        self.studio_tree.item(str(idx), tags=("playing",))
                    self._studio_active = idx
            self.after(150, self._studio_tick)
        except tk.TclError:
            return

    def _studio_save(self):
        if self.process is not None and self.process.poll() is None:
            self._dialog("showwarning", "Search running", "Finish the active search before saving lyrics.")
            return
        if self.studio_doc is None or not self.studio_audio.get():
            self._dialog("showerror", "Cannot save Studio lyrics", "Choose audio and import lyrics first.")
            return
        try:
            render_candidate(self.studio_doc.lines)  # Before confirmation, fail invalid ordering.
        except ValueError as ex:
            self._dialog("showerror", "Cannot save Studio lyrics", str(ex))
            return
        if not self._dialog("askyesno", "Save separate unverified candidate?",
              "A NEW numbered .candidate.lrc will be created next to the audio.\n"
              "Existing audio, ID3, .lrc, and other candidates will never be overwritten.\n"
              "Timing remains UNVERIFIED until you review it. Continue?"):
            return
        try:
            path = save_candidate(self.studio_audio.get(), self.studio_doc.lines)
            self._studio_saved = True
            self.studio_status.set("Saved UNVERIFIED: " + str(path))
            self._dialog("showinfo", "Lyrics Studio saved", "New candidate:\n" + str(path))
            self._refresh_review()
        except (OSError, ValueError) as ex:
            self._dialog("showerror", "Cannot save Studio lyrics", str(ex))

    def _studio_can_close(self):
        return self._studio_will_replace()

    def destroy(self):
        player = getattr(self, "studio_player", None)
        if player is not None:
            player.close()
        super().destroy()
