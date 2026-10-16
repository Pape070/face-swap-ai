"""HeadSwap Studio — Desktop edition (Tkinter).

Same full-head swap engine as the web app (`face_swap.py`), wrapped in a
native desktop GUI: pick a source photo + target video, tune sliders, watch
progress, and play/open the result. No server or browser needed.

Run:
    pip install -r requirements.txt   # from repo root, then:
    python desktop/faceswap_desktop.py
"""
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from face_swap import process_video  # noqa: E402


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("HeadSwap Studio — Desktop")
        self.geometry("640x560")
        self.source = tk.StringVar()
        self.target = tk.StringVar()
        self.scalp = tk.DoubleVar(value=0.85)
        self.side = tk.DoubleVar(value=0.30)
        self.blend = tk.DoubleVar(value=0.92)
        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 4}
        ttk.Label(self, text="HeadSwap Studio — Desktop",
                  font=("TkDefaultFont", 16, "bold")).pack(**pad)
        ttk.Label(self, text="Swap a full head from a photo onto a video.",
                  foreground="gray").pack()
        for label, var, cmd in (("1 · Source photo", self.source, self.pick_source),
                                ("2 · Target video", self.target, self.pick_target)):
            f = ttk.Frame(self)
            f.pack(fill="x", **pad)
            ttk.Label(f, text=label, width=18).pack(side="left")
            ttk.Entry(f, textvariable=var, width=48, state="readonly").pack(side="left", padx=4)
            ttk.Button(f, text="Browse…", command=cmd).pack(side="left")
        for label, var, lo, hi in (("Scalp / hair coverage", self.scalp, 0.2, 1.4),
                                   ("Head width", self.side, 0.0, 0.8),
                                   ("Blend strength", self.blend, 0.3, 1.0)):
            f = ttk.Frame(self)
            f.pack(fill="x", **pad)
            ttk.Label(f, text=label, width=22).pack(side="left")
            ttk.Scale(f, from_=lo, to=hi, variable=var, orient="horizontal", length=320).pack(side="left")
            ttk.Label(f, textvariable=var, width=6).pack(side="left")
        self.swap_btn = ttk.Button(self, text="✨ Swap head into video", command=self.start)
        self.swap_btn.pack(pady=10)
        self.prog = ttk.Progressbar(self, mode="determinate", length=560)
        self.prog.pack(**pad)
        self.status = tk.StringVar(value="Pick a source photo and a target video.")
        ttk.Label(self, textvariable=self.status, wraplength=600).pack(**pad)
        self.result_path = None
        self.open_btn = ttk.Button(self, text="▶ Open result video", command=self.open_result, state="disabled")
        self.open_btn.pack()
        ttk.Label(self, text="Only swap faces you have consent to use.", foreground="gray", wraplength=600).pack(side="bottom", pady=8)

    def pick_source(self):
        p = filedialog.askopenfilename(title="Source photo", filetypes=[("Images", "*.jpg *.jpeg *.png *.webp")])
        if p:
            self.source.set(p)

    def pick_target(self):
        p = filedialog.askopenfilename(title="Target video", filetypes=[("Videos", "*.mp4 *.mov *.avi *.webm *.mkv")])
        if p:
            self.target.set(p)

    def start(self):
        if not self.source.get() or not self.target.get():
            messagebox.showwarning("Missing files", "Pick both a source photo and a target video.")
            return
        base, _ = os.path.splitext(self.target.get())
        out = base + "_headswap.mp4"
        self.swap_btn.config(state="disabled")
        self.open_btn.config(state="disabled")
        self.status.set("Processing…")
        threading.Thread(target=self._run, args=(out,), daemon=True).start()

    def _run(self, out):
        try:
            def cb(done, total, faces):
                self.after(0, self._tick, done, max(1, total), faces)
            info = process_video(self.source.get(), self.target.get(), out, progress_cb=cb,
                                 top=self.scalp.get(), side=self.side.get(), blend=self.blend.get())
            self.after(0, self._done, out, info)
        except Exception as e:  # noqa: BLE001 — surfaced in the GUI
            self.after(0, self._fail, str(e))

    def _tick(self, done, total, faces):
        self.prog["maximum"] = total
        self.prog["value"] = done
        self.status.set(f"Frame {done}/{total} · faces swapped in {faces} frames…")

    def _done(self, out, info):
        self.result_path = out
        self.prog["value"] = self.prog["maximum"]
        self.status.set(f"Done — swapped faces in {info['faces_found']}/{info['frames']} frames ({info['engine']}). Saved to {out}")
        self.swap_btn.config(state="normal")
        self.open_btn.config(state="normal")

    def _fail(self, err):
        self.status.set(f"Error: {err}")
        messagebox.showerror("Swap failed", err)
        self.swap_btn.config(state="normal")

    def open_result(self):
        if self.result_path and os.path.exists(self.result_path):
            import webbrowser
            webbrowser.open("file://" + os.path.abspath(self.result_path))


if __name__ == "__main__":
    App().mainloop()
