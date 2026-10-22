"""v2.8 Karaoke Edition GUI: operator queue, calibrated performance view, and safe UX."""
from __future__ import annotations
import os
import math
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog
from v270_gui import V270Mixin
from v260_studio import format_time
from v280_karaoke_core import (KaraokeSession, AUDIO_EXTS, THEMES, FONTS, COUNTDOWNS,
                               regular_file, preview_export)

class V280Mixin(V270Mixin):
    def _studio_build_tabs(self):
        result=super()._studio_build_tabs()
        self._v280_session=KaraokeSession.load()
        self.karaoke_edition_tab=ttk.Frame(self.studio_tabs,padding=8)
        self.studio_tabs.add(self.karaoke_edition_tab,text="Karaoke Edition")
        self._v280_canvas=None
        self._v280_visual_photo=None
        self._v280_canvas_current=None
        self._v280_canvas_next=None
        self._v280_canvas_bg=None
        self._v280_picture=None
        self._v280_render_token=0
        self._v280_count_id=0
        self._v280_count_remaining=0
        self._v280_last_time=-1
        self._v280_build()
        return result

    def _v280_build(self):
        p=self.karaoke_edition_tab
        session=self._v280_session
        self._v280_status=tk.StringVar(value="Add local instrumentals to the playlist. Original files remain read-only.")
        self._v280_theme=tk.StringVar(value=session.theme)
        self._v280_font=tk.IntVar(value=session.font_size)
        self._v280_next=tk.BooleanVar(value=session.show_next)
        self._v280_count=tk.IntVar(value=session.countdown)
        self._v280_offset=tk.StringVar(value=f"{session.offset:+.2f}")
        self._v280_display=tk.StringVar(value="Default / manual move")
        ttk.Label(p,text="Karaoke Edition — operator controls",style="Header.TLabel").pack(anchor="w")
        ttk.Label(p,text="The audience gets a clean lyrics window; music and playlists stay in the operator workspace. No source audio/LRC is modified.",
                  wraplength=900).pack(anchor="w",pady=(1,7))
        row=ttk.Frame(p);row.pack(fill="x",pady=2)
        ttk.Button(row,text="Add audio files...",command=self._v280_add_dialog).pack(side="left",padx=2)
        ttk.Button(row,text="Pair selected LRC...",command=self._v280_pair_dialog).pack(side="left",padx=2)
        ttk.Button(row,text="Open selected song",command=self._v280_open_selected).pack(side="left",padx=2)
        ttk.Button(row,text="Restore last song",command=self._v280_restore_last).pack(side="left",padx=2)
        self._v280_tree=ttk.Treeview(p,columns=("audio","lyrics"),show="headings",height=8,selectmode="browse")
        self._v280_tree.heading("audio",text="Audio / instrumental")
        self._v280_tree.heading("lyrics",text="Paired .lrc (or needs pairing)")
        self._v280_tree.column("audio",width=365)
        self._v280_tree.column("lyrics",width=420)
        self._v280_tree.pack(fill="both",expand=True,pady=4)
        self._v280_tree.bind("<Double-1>",lambda e:self._v280_open_selected())
        ttk.Label(p,text="Drag audio/LRC files onto the playlist (when native drag-and-drop is available).").pack(anchor="w")
        row=ttk.Frame(p);row.pack(fill="x",pady=3)
        for name,command in (("Move up",lambda:self._v280_move(-1)),
                             ("Move down",lambda:self._v280_move(1)),
                             ("Remove",self._v280_remove),
                             ("Previous track",lambda:self._v280_step(-1)),
                             ("Next track",lambda:self._v280_step(1)),
                             ("Play with countdown",self._v280_play_countdown)):
            ttk.Button(row,text=name,command=command).pack(side="left",padx=2)
        row=ttk.Frame(p);row.pack(fill="x",pady=5)
        ttk.Label(row,text="Audience theme:").pack(side="left",padx=2)
        cb=ttk.Combobox(row,state="readonly",values=tuple(THEMES),textvariable=self._v280_theme,width=16)
        cb.pack(side="left",padx=2);cb.bind("<<ComboboxSelected>>",lambda e:self._v280_update_settings())
        ttk.Label(row,text="Font size:").pack(side="left",padx=5)
        cb=ttk.Combobox(row,state="readonly",values=FONTS,textvariable=self._v280_font,width=5)
        cb.pack(side="left");cb.bind("<<ComboboxSelected>>",lambda e:self._v280_update_settings())
        ttk.Checkbutton(row,text="Show next line",variable=self._v280_next,
                        command=self._v280_update_settings).pack(side="left",padx=8)
        ttk.Label(row,text="Countdown (seconds):").pack(side="left",padx=5)
        cb=ttk.Combobox(row,state="readonly",values=COUNTDOWNS,textvariable=self._v280_count,width=4)
        cb.pack(side="left");cb.bind("<<ComboboxSelected>>",lambda e:self._v280_update_settings())
        row=ttk.Frame(p);row.pack(fill="x",pady=3)
        ttk.Label(row,text="Lyric offset (seconds, + delays lyrics):").pack(side="left",padx=2)
        for v in (-1.0,-0.1,0.1,1.0):
            ttk.Button(row,text=f"{v:+g}",command=lambda step=v:self._v280_change_offset(step)).pack(side="left",padx=2)
        ttk.Label(row,textvariable=self._v280_offset,width=8).pack(side="left",padx=4)
        ttk.Button(row,text="Reset offset",command=self._v280_reset_offset).pack(side="left",padx=3)
        ttk.Button(row,text="Apply offset to ALL lyric timestamps...",
                   command=self._v280_apply_offset).pack(side="left",padx=7)
        row=ttk.Frame(p);row.pack(fill="x",pady=4)
        ttk.Button(row,text="Choose local background image...",
                   command=self._v280_background_dialog).pack(side="left",padx=2)
        ttk.Button(row,text="Clear background image",command=self._v280_clear_background).pack(side="left",padx=2)
        ttk.Button(row,text="Preview LRC export (read-only)...",
                   command=self._v280_preview_export).pack(side="left",padx=7)
        ttk.Button(row,text="Open audience screen",
                   command=self._v270_show_karaoke).pack(side="left",padx=4)
        row=ttk.Frame(p);row.pack(fill="x",pady=4)
        ttk.Label(row,text="Target display:").pack(side="left")
        self._v280_displays=self._v280_detect_displays()
        names=("Default / manual move",)+tuple(n for n,_ in self._v280_displays)
        cb=ttk.Combobox(row,state="readonly",values=names,textvariable=self._v280_display,width=39)
        cb.pack(side="left",padx=6)
        ttk.Label(row,text="F11 fullscreen · Esc close · Space play/pause · ←/→ previous/next track",
                  wraplength=510).pack(side="left",padx=4)
        ttk.Label(p,textvariable=self._v280_status,wraplength=940).pack(anchor="w",pady=4)
        self._v280_render_playlist()
        self._v280_activate_dnd()

    def _v280_detect_displays(self):
        try:
            from screeninfo import get_monitors
            monitors=get_monitors()
            return [(f"Screen {i+1}: {m.width}×{m.height}" + (" (primary)" if m.is_primary else ""),
                     (int(m.x),int(m.y),int(m.width),int(m.height))) for i,m in enumerate(monitors)
                    if m.width>0 and m.height>0]
        except (ImportError,OSError,ValueError,RuntimeError):
            return []

    def _v280_activate_dnd(self):
        try:
            from tkinterdnd2 import TkinterDnD, DND_FILES
            TkinterDnD.require(self)
            TkinterDnD.DnDWrapper.drop_target_register(self._v280_tree,DND_FILES)
            TkinterDnD.DnDWrapper.dnd_bind(self._v280_tree,"<<Drop>>",self._v280_drop)
            self._v280_status.set("Drag and drop ready. Add instrumentals and LRC files to the playlist.")
        except (ImportError,OSError,tk.TclError,AttributeError,RuntimeError) as ex:
            self._v280_status.set("File chooser available; native drag-and-drop unavailable on this setup.")

    def _v280_drop(self,event):
        try:
            paths=self.tk.splitlist(event.data)
            self._v280_add_files(paths)
        except (ValueError,OSError,tk.TclError) as ex:
            self._dialog("showerror","Karaoke drag and drop",str(ex))
        return "copy"

    def _v280_add_dialog(self):
        paths=filedialog.askopenfilenames(parent=self,title="Choose local instrumentals / audio",
            filetypes=[("Audio files","*.mp3 *.wav *.flac *.ogg *.opus *.m4a *.mp4"),("All files","*.*")])
        if paths:self._v280_add_files(paths)

    def _v280_add_files(self,paths):
        items=[Path(x) for x in paths]
        if len(items)>500:
            self._dialog("showerror","Karaoke playlist","Too many files dropped.")
            return
        audio=[p for p in items if p.suffix.casefold() in AUDIO_EXTS]
        lyrics=[p for p in items if p.suffix.casefold()==".lrc"]
        invalid=[p for p in items if p not in audio and p not in lyrics]
        if invalid:
            self._v280_status.set(f"Skipped {len(invalid)} unsupported file(s).")
        added=0
        for p in audio:
            try:
                explicit=lyrics[0] if len(audio)==1 and len(lyrics)==1 else None
                self._v280_session.add(p,explicit)
                added+=1
            except (OSError,ValueError) as ex:
                self._v280_status.set("Could not add track: "+str(ex))
        if not audio and len(lyrics)==1:
            self._v280_attach_path(lyrics[0])
        self._v280_render_playlist()
        self._v280_persist()
        if added:self._v280_status.set(f"{added} audio file(s) accepted into the playlist. Double-click to open.")

    def _v280_row(self):
        selected=self._v280_tree.selection()
        return int(selected[0]) if selected else self._v280_session.selected

    def _v280_attach_path(self,path):
        i=self._v280_row()
        if i is None or not 0<=i<len(self._v280_session.entries):
            self._dialog("showinfo","Pair LRC","Select an audio entry first.")
            return
        try:
            self._v280_session.attach(i,path)
            self._v280_render_playlist()
            self._v280_persist()
        except (ValueError,OSError) as ex:
            self._dialog("showerror","Pair LRC",str(ex))

    def _v280_pair_dialog(self):
        chosen=filedialog.askopenfilename(parent=self,title="Choose LRC for selected audio",
                   filetypes=[("Timed LRC","*.lrc"),("All files","*.*")])
        if chosen:self._v280_attach_path(chosen)

    def _v280_render_playlist(self):
        existing=self._v280_tree.selection()
        self._v280_tree.delete(*self._v280_tree.get_children())
        for i,item in enumerate(self._v280_session.entries):
            self._v280_tree.insert("","end",iid=str(i),values=(Path(item.audio).name,
               Path(item.lrc).name if item.lrc else "Needs LRC pairing"))
        selection=self._v280_session.selected
        if existing and int(existing[0])<len(self._v280_session.entries):
            selection=int(existing[0])
        if 0<=selection<len(self._v280_session.entries):
            self._v280_tree.selection_set(str(selection))
            self._v280_tree.see(str(selection))

    def _v280_open_selected(self):
        i=self._v280_row()
        if i is None or not 0<=i<len(self._v280_session.entries):
            self._dialog("showinfo","Karaoke playlist","Select an audio file first.")
            return False
        item=self._v280_session.entries[i]
        try:
            item.validate()
        except (ValueError,OSError) as ex:
            self._dialog("showerror","Karaoke playlist",str(ex))
            return False
        if not self._v270_open(item.audio,item.lrc or None):
            return False
        self._v280_session.selected=i
        self._v280_session.last_audio=item.audio
        self._v280_persist()
        return True

    def _v280_step(self,step):
        i=self._v280_row()
        if i is None:return
        dest=i+step
        if not 0<=dest<len(self._v280_session.entries):
            self._v280_status.set("Reached the beginning or end of the playlist.")
            return
        self._v280_tree.selection_set(str(dest))
        self._v280_session.selected=dest
        self._v280_open_selected()

    def _v280_move(self,step):
        i=self._v280_row()
        if i is None:return
        dest=self._v280_session.move(i,step)
        self._v280_tree.selection_remove(self._v280_tree.selection())
        self._v280_render_playlist()
        if 0<=dest<len(self._v280_session.entries):
            self._v280_tree.selection_set(str(dest))
        self._v280_persist()

    def _v280_remove(self):
        i=self._v280_row()
        if i is None:return
        self._v280_session.remove(i)
        self._v280_tree.selection_remove(self._v280_tree.selection())
        self._v280_render_playlist()
        self._v280_persist()

    def _v280_restore_last(self):
        path=self._v280_session.last_audio
        if not path:
            self._dialog("showinfo","Restore last song","No previously opened song is saved.")
            return
        match=next((i for i,r in enumerate(self._v280_session.entries) if r.audio==path),None)
        if match is None:
            self._dialog("showwarning","Restore last song","Previous track is no longer in the playlist.")
            return
        self._v280_tree.selection_set(str(match))
        self._v280_open_selected()

    def _v280_persist(self):
        try:
            self._v280_session.save()
        except (OSError,ValueError) as ex:
            self._v280_status.set("Local karaoke preferences could not be saved: "+str(ex))

    def _v280_update_settings(self):
        s=self._v280_session
        s.theme=self._v280_theme.get()
        s.font_size=int(self._v280_font.get())
        s.show_next=self._v280_next.get()
        s.countdown=int(self._v280_count.get())
        self._v280_persist()
        self._v280_style_karaoke()

    def _v280_change_offset(self,delta):
        s=self._v280_session
        value=round(s.offset+delta,2)
        if not -30<=value<=30:
            self._dialog("showwarning","Global lyric offset","Offset must stay within ±30 seconds.")
            return
        s.offset=value
        self._v280_offset.set(f"{value:+.2f}")
        self._v280_persist()
        self._v270_karaoke_refresh()

    def _v280_reset_offset(self):
        self._v280_session.offset=0.0
        self._v280_offset.set("+0.00")
        self._v280_persist()
        self._v270_karaoke_refresh()

    def _v280_apply_offset(self):
        if not self.studio_doc or not self.studio_audio.get():
            self._dialog("showinfo","Global lyric offset","Open audio and LRC in Lyrics Studio first.")
            return
        delta=self._v280_session.offset
        if abs(delta)<0.001:
            self._dialog("showinfo","Global lyric offset","Offset is already zero.")
            return
        if not self._dialog("askyesno","Apply offset to all lines?",
               f"Shift ALL {len(self.studio_doc.lines)} timestamps by {delta:+.2f} seconds in memory?\n"
               "Original audio and LRC remain untouched. Save ONLY creates a NEW UNVERIFIED candidate."):
            return
        before=list(self.studio_doc.lines)
        self._studio_edit(lambda:self.studio_doc.shift(list(range(len(self.studio_doc.lines))),delta))
        if before!=self.studio_doc.lines:
            self._v280_reset_offset()
            self._v280_status.set("Applied offset in memory. Use Undo or export a NEW candidate after review.")

    def _v280_preview_export(self):
        if not self.studio_doc or not self.studio_audio.get():
            self._dialog("showinfo","Candidate preview","Open audio and timed lyrics first.")
            return
        try:
            text=preview_export(self.studio_audio.get(),self.studio_doc.lines,self._v270_profile.get())
        except (OSError,ValueError) as ex:
            self._dialog("showerror","Candidate preview",str(ex))
            return
        win=tk.Toplevel(self);win.title("NEW candidate export preview — READ ONLY");win.geometry("780x540")
        ttk.Label(win,text="Preview only. No files are written. Saving requires the separate confirmed Save action.",
                  wraplength=730).pack(anchor="w",padx=12,pady=9)
        from tkinter.scrolledtext import ScrolledText
        widget=ScrolledText(win,font=("Consolas",11),wrap="none")
        widget.pack(fill="both",expand=True,padx=9,pady=7)
        widget.insert("1.0",text);widget.configure(state="disabled")

    def _v280_background_dialog(self):
        filename=filedialog.askopenfilename(parent=self,title="Choose local karaoke background",
                   filetypes=[("Images","*.png *.jpg *.jpeg"),("All files","*.*")])
        if filename:
            try:
                self._v280_validate_picture(filename)
            except (OSError,ValueError) as ex:
                self._dialog("showerror","Karaoke background",str(ex))
                return
            self._v280_session.background_image=str(filename)
            self._v280_persist()
            self._v280_picture=None
            self._v280_style_karaoke()

    def _v280_validate_picture(self,path):
        p=regular_file(path,{".jpg",".jpeg",".png"})
        if p.stat().st_size>15*1024*1024:
            raise ValueError("Background images are limited to 15 MB")
        try:
            from PIL import Image
            with Image.open(p) as im:
                if im.width*im.height>20_000_000:
                    raise ValueError("Background pixel limit exceeded (20 MP)")
                im.verify()
        except ImportError as ex:
            raise ValueError("Background images need Pillow (bundled in the Windows EXE)") from ex
        except Exception as ex:
            raise ValueError("Invalid or unsupported image") from ex

    def _v280_clear_background(self):
        self._v280_session.background_image=""
        self._v280_picture=None
        self._v280_visual_photo=None
        self._v280_persist()
        self._v280_style_karaoke()

    def _v280_loop_restore(self):
        audio=self.studio_audio.get()
        self.loop_a=self.loop_b=None
        if audio:
            points=self._v280_session.load_loop(audio)
            if points:self.loop_a,self.loop_b=points
        self._v270_show_loop()

    def _v270_set_b(self):
        super()._v270_set_b()
        if self.loop_a is not None and self.loop_b is not None and self.studio_audio.get():
            self._v280_session.save_loop(self.studio_audio.get(),self.loop_a,self.loop_b)
            self._v280_persist()

    def _v270_clear_loop(self):
        super()._v270_clear_loop()
        audio=self.studio_audio.get()
        if audio:
            self._v280_session.loops.pop(str(Path(audio).resolve()).casefold(),None)
            self._v280_persist()

    def _v270_open(self,audio,lrc=None):
        opened=super()._v270_open(audio,lrc)
        if opened:
            self._v280_session.last_audio=str(audio)
            self._v280_loop_restore()
            self._v280_persist()
        return opened

    def _studio_choose_audio(self):
        previous=self.studio_audio.get()
        super()._studio_choose_audio()
        if previous!=self.studio_audio.get() and self.studio_audio.get():
            self._v280_session.last_audio=self.studio_audio.get()
            self._v280_loop_restore()
            self._v280_persist()

    def _v280_play_countdown(self):
        if not self.studio_audio.get():
            self._dialog("showinfo","Karaoke countdown","Open a song first.")
            return
        self._v280_count_id+=1
        self._v280_count_remaining=self._v280_session.countdown
        if self._v280_count_remaining==0:
            self._studio_play();return
        self._v270_show_karaoke()
        self._v280_count_step(self._v280_count_id,self.studio_audio.get())

    def _v280_count_step(self,token,audio):
        if token!=self._v280_count_id or audio!=self.studio_audio.get():
            return
        if self._v280_count_remaining<=0:
            self._v280_count_remaining=0
            self._studio_play()
            return
        if self._v280_canvas is not None and self.karaoke_window is not None:
            try:
                self._v280_canvas.itemconfigure(self._v280_canvas_current,
                               text=str(self._v280_count_remaining))
                self._v280_canvas.itemconfigure(self._v280_canvas_next,text="Get ready...")
            except tk.TclError:pass
        self._v280_count_remaining-=1
        self.after(1000,lambda:self._v280_count_step(token,audio))

    def _v280_safe_geometry(self,win):
        try:
            win.geometry(self._v280_session.window_geometry)
        except tk.TclError:
            win.geometry("1000x560")
        name=self._v280_display.get()
        match=next((coords for label,coords in self._v280_displays if label==name),None)
        if match:
            x,y,w,h=match
            win.geometry(f"{w}x{h}{x:+d}{y:+d}")

    def _v270_show_karaoke(self):
        if not self.studio_doc or not self.studio_audio.get():
            self._dialog("showinfo","Instrumental karaoke","Choose audio and import its timed LRC first.")
            return
        if self.karaoke_window is not None and self.karaoke_window.winfo_exists():
            self.karaoke_window.lift();return
        win=tk.Toplevel(self);win.title("LRC Bulk Finder — Karaoke Edition")
        self._v280_safe_geometry(win)
        win.protocol("WM_DELETE_WINDOW",self._v270_close_karaoke)
        win.bind("<Escape>",lambda e:self._v270_close_karaoke())
        win.bind("<F11>",lambda e:win.attributes("-fullscreen",not bool(win.attributes("-fullscreen"))))
        win.bind("<space>",lambda e:self._v270_karaoke_play_pause())
        win.bind("<Left>",lambda e:self._v280_step(-1))
        win.bind("<Right>",lambda e:self._v280_step(1))
        self.karaoke_window=win
        self.karaoke_current=tk.StringVar(value="♪")
        self.karaoke_next=tk.StringVar(value="")
        self._v280_canvas=tk.Canvas(win,highlightthickness=0,bd=0)
        self._v280_canvas.pack(fill="both",expand=True)
        self._v280_canvas_bg=self._v280_canvas.create_image(0,0,anchor="center")
        self._v280_canvas_current=self._v280_canvas.create_text(500,250,text="♪",anchor="center",
                   justify="center",width=930,font=("Segoe UI",self._v280_session.font_size,"bold"))
        self._v280_canvas_next=self._v280_canvas.create_text(500,420,text="",anchor="center",
                   justify="center",width=930,font=("Segoe UI",max(16,self._v280_session.font_size-11)))
        self._v280_canvas.bind("<Configure>",self._v280_canvas_resize)
        self._v280_picture=None
        self._v280_style_karaoke()
        self._v270_karaoke_refresh()

    def _v280_canvas_resize(self,event=None):
        if self._v280_canvas is None:return
        canvas=self._v280_canvas
        w,h=max(100,canvas.winfo_width()),max(100,canvas.winfo_height())
        canvas.coords(self._v280_canvas_bg,w/2,h/2)
        canvas.coords(self._v280_canvas_current,w/2,h*.45)
        canvas.coords(self._v280_canvas_next,w/2,h*.76)
        canvas.itemconfigure(self._v280_canvas_current,width=max(100,w-70))
        canvas.itemconfigure(self._v280_canvas_next,width=max(100,w-90))
        self._v280_draw_background(w,h)

    def _v280_draw_background(self,w,h):
        canvas=self._v280_canvas
        if canvas is None:return
        path=self._v280_session.background_image
        if not path:
            self._v280_visual_photo=None
            canvas.itemconfigure(self._v280_canvas_bg,image="")
            return
        try:
            self._v280_validate_picture(path)
            from PIL import Image,ImageTk
            with Image.open(path) as file:
                file.thumbnail((w,h),Image.Resampling.LANCZOS)
                copy=file.convert("RGB")
            self._v280_visual_photo=ImageTk.PhotoImage(copy,master=canvas)
            canvas.itemconfigure(self._v280_canvas_bg,image=self._v280_visual_photo)
        except (OSError,ValueError,tk.TclError):
            self._v280_visual_photo=None
            canvas.itemconfigure(self._v280_canvas_bg,image="")
            self._v280_status.set("Background image unavailable; using solid theme.")

    def _v280_style_karaoke(self):
        canvas=self._v280_canvas
        if canvas is None:return
        s=self._v280_session
        bg,fg,next_fg=THEMES.get(s.theme,THEMES["Midnight"])
        try:
            canvas.configure(background=bg)
            canvas.itemconfigure(self._v280_canvas_current,fill=fg,
                            font=("Segoe UI",s.font_size,"bold"))
            canvas.itemconfigure(self._v280_canvas_next,fill=next_fg,
                            font=("Segoe UI",max(16,s.font_size-11)))
            canvas.itemconfigure(self._v280_canvas_next,state="normal" if s.show_next else "hidden")
            canvas.lift(self._v280_canvas_current)
            canvas.lift(self._v280_canvas_next)
            self._v280_canvas_resize()
        except tk.TclError:pass

    def _v270_karaoke_refresh(self):
        if self.karaoke_window is None or not self.karaoke_window.winfo_exists() or not self.studio_doc:
            return
        if self._v280_count_remaining>0:return
        # Positive offset delays lyric transitions: display lyric(t - offset).
        time_value=max(0.0,self.studio_player.position()-self._v280_session.offset)
        idx=self.studio_doc.active_line(time_value)
        lines=self.studio_doc.lines
        current=lines[idx].text if idx is not None else "♪"
        upcoming=(lines[idx+1].text if idx is not None and idx+1<len(lines)
                  else lines[0].text if idx is None and lines else "")
        self.karaoke_current.set(current)
        self.karaoke_next.set(upcoming if self._v280_session.show_next else "")
        if self._v280_canvas is not None:
            try:
                self._v280_canvas.itemconfigure(self._v280_canvas_current,text=current)
                self._v280_canvas.itemconfigure(self._v280_canvas_next,
                                   text=upcoming if self._v280_session.show_next else "")
            except tk.TclError:pass

    def _v270_close_karaoke(self):
        self._v280_count_id+=1
        self._v280_count_remaining=0
        if self.karaoke_window is not None:
            try:
                if not self.karaoke_window.attributes("-fullscreen"):
                    geometry=self.karaoke_window.geometry()
                    if self._v280_session.window_geometry!=geometry:
                        self._v280_session.window_geometry=geometry
                        self._v280_persist()
            except tk.TclError:pass
        super()._v270_close_karaoke()
        self._v280_canvas=None
        self._v280_visual_photo=None

    def _studio_can_close(self):
        self._v280_count_id+=1
        self._v280_count_remaining=0
        return super()._studio_can_close()
