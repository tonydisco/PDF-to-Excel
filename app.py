# -*- coding: utf-8 -*-
"""
Giao diện chuyển đổi Báo cáo tài chính (PDF scan) -> Excel theo Thông tư 200.

Chạy:  python app.py
"""
import os
import sys
import queue
import threading
import traceback

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# cho phép chạy trực tiếp lẫn sau khi đóng gói
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bctc import engine, ocr           # noqa: E402

APP_TITLE = "BCTC PDF → Excel  •  Thông tư 200"
MAX_FILES = engine.MAX_FILES
BG = "#0f172a"; CARD = "#1e293b"; FG = "#e2e8f0"; SUB = "#94a3b8"
ACCENT = "#2563eb"; OK = "#22c55e"; WARN = "#f59e0b"; ERR = "#ef4444"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("860x640")
        self.minsize(760, 560)
        self.configure(bg=BG)
        self.files = []
        self.out_dir = tk.StringVar(value="")
        self.hi_quality = tk.BooleanVar(value=False)
        self.msg_q = queue.Queue()
        self.running = False
        self._build()
        self.after(80, self._drain_queue)

    # ------------------------------------------------------------------ UI
    def _build(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TButton", padding=8, font=("Segoe UI", 10))
        style.configure("Accent.TButton", foreground="#fff",
                        background=ACCENT, padding=10, font=("Segoe UI", 11, "bold"))
        style.map("Accent.TButton", background=[("active", "#1d4ed8")])
        style.configure("TProgressbar", thickness=18, background=ACCENT)

        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=20, pady=(18, 6))
        tk.Label(header, text="Chuyển Báo cáo tài chính PDF → Excel", bg=BG, fg=FG,
                 font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(header, text="Bóc 3 báo cáo: Bảng cân đối kế toán · Kết quả HĐKD · "
                 "Lưu chuyển tiền tệ — mỗi báo cáo 1 sheet (mẫu Thông tư 200).",
                 bg=BG, fg=SUB, font=("Segoe UI", 10)).pack(anchor="w", pady=(2, 0))

        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=20, pady=10)

        # --- danh sách file ---
        left = tk.Frame(body, bg=CARD, bd=0, highlightthickness=1,
                        highlightbackground="#334155")
        left.pack(side="left", fill="both", expand=True)
        bar = tk.Frame(left, bg=CARD)
        bar.pack(fill="x", padx=12, pady=10)
        tk.Label(bar, text="File PDF (tối đa %d)" % MAX_FILES, bg=CARD, fg=FG,
                 font=("Segoe UI", 11, "bold")).pack(side="left")
        self.count_lbl = tk.Label(bar, text="0 file", bg=CARD, fg=SUB,
                                   font=("Segoe UI", 10))
        self.count_lbl.pack(side="right")

        self.listbox = tk.Listbox(left, selectmode="extended", activestyle="none",
                                  bg="#0b1220", fg=FG, bd=0, highlightthickness=0,
                                  font=("Consolas", 10), selectbackground=ACCENT)
        self.listbox.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        btns = tk.Frame(left, bg=CARD)
        btns.pack(fill="x", padx=12, pady=(0, 12))
        ttk.Button(btns, text="+ Thêm file", command=self.add_files).pack(side="left")
        ttk.Button(btns, text="Xoá chọn", command=self.remove_selected).pack(side="left", padx=6)
        ttk.Button(btns, text="Xoá hết", command=self.clear_files).pack(side="left")

        # --- bảng điều khiển ---
        right = tk.Frame(body, bg=BG, width=300)
        right.pack(side="right", fill="y", padx=(14, 0))
        right.pack_propagate(False)

        tk.Label(right, text="Thư mục lưu Excel", bg=BG, fg=FG,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        of = tk.Frame(right, bg=BG); of.pack(fill="x", pady=(4, 12))
        self.out_entry = tk.Entry(of, textvariable=self.out_dir, bg="#0b1220", fg=FG,
                                  bd=0, font=("Segoe UI", 9), insertbackground=FG)
        self.out_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 6))
        ttk.Button(of, text="Chọn…", command=self.pick_out, width=7).pack(side="right")

        tk.Checkbutton(right, text="Chất lượng cao (chậm hơn)",
                       variable=self.hi_quality, bg=BG, fg=SUB, selectcolor=BG,
                       activebackground=BG, activeforeground=FG,
                       font=("Segoe UI", 9)).pack(anchor="w")

        self.convert_btn = ttk.Button(right, text="CHUYỂN ĐỔI  ▶",
                                      style="Accent.TButton", command=self.start)
        self.convert_btn.pack(fill="x", pady=14)

        self.progress = ttk.Progressbar(right, mode="determinate")
        self.progress.pack(fill="x")
        self.status_lbl = tk.Label(right, text="Sẵn sàng", bg=BG, fg=SUB,
                                   font=("Segoe UI", 9))
        self.status_lbl.pack(anchor="w", pady=(6, 0))

        # --- nhật ký ---
        tk.Label(self, text="Nhật ký", bg=BG, fg=FG,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=20)
        logf = tk.Frame(self, bg=BG); logf.pack(fill="both", padx=20, pady=(2, 16))
        self.log = tk.Text(logf, height=9, bg="#0b1220", fg=FG, bd=0,
                           font=("Consolas", 9), wrap="word", state="disabled")
        self.log.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(logf, command=self.log.yview); sb.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=sb.set)
        for tag, col in (("ok", OK), ("warn", WARN), ("err", ERR), ("muted", SUB)):
            self.log.tag_configure(tag, foreground=col)

        self._check_tesseract()

    # --------------------------------------------------------------- helpers
    def _logln(self, text, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n", tag or ())
        self.log.see("end")
        self.log.configure(state="disabled")

    def _check_tesseract(self):
        try:
            ocr.configure_tesseract()
            if not ocr.has_vietnamese():
                self._logln("⚠ Chưa có gói tiếng Việt (vie) cho Tesseract.", "warn")
            else:
                self._logln("✓ Tesseract + tiếng Việt sẵn sàng.", "ok")
        except ocr.TesseractNotFound as e:
            self._logln("✖ " + str(e), "err")

    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="Chọn file PDF báo cáo tài chính",
            filetypes=[("PDF", "*.pdf"), ("Tất cả", "*.*")])
        for p in paths:
            if p not in self.files:
                if len(self.files) >= MAX_FILES:
                    messagebox.showwarning("Giới hạn", f"Tối đa {MAX_FILES} file mỗi lần.")
                    break
                self.files.append(p)
        if self.files and not self.out_dir.get():
            self.out_dir.set(os.path.join(os.path.dirname(self.files[0]), "Excel_output"))
        self._refresh_list()

    def remove_selected(self):
        for i in reversed(self.listbox.curselection()):
            del self.files[i]
        self._refresh_list()

    def clear_files(self):
        self.files.clear(); self._refresh_list()

    def _refresh_list(self):
        self.listbox.delete(0, "end")
        for p in self.files:
            self.listbox.insert("end", "  " + os.path.basename(p))
        self.count_lbl.config(text=f"{len(self.files)} file")

    def pick_out(self):
        d = filedialog.askdirectory(title="Chọn thư mục lưu Excel")
        if d:
            self.out_dir.set(d)

    # --------------------------------------------------------------- convert
    def start(self):
        if self.running:
            return
        if not self.files:
            messagebox.showinfo("Chưa có file", "Hãy thêm ít nhất 1 file PDF.")
            return
        out = self.out_dir.get().strip()
        if not out:
            messagebox.showinfo("Thiếu thư mục", "Hãy chọn thư mục lưu Excel.")
            return
        self.running = True
        self.convert_btn.config(state="disabled")
        self.progress.config(value=0, maximum=len(self.files))
        self.status_lbl.config(text="Đang xử lý…")
        self._logln("─" * 48, "muted")
        t = threading.Thread(target=self._worker, args=(list(self.files), out), daemon=True)
        t.start()

    def _worker(self, files, out_dir):
        def log(m): self.msg_q.put(("log", m))
        def prog(done, total): self.msg_q.put(("prog", (done, total)))
        try:
            dpis = (180, 220, 290) if self.hi_quality.get() else (180, 235)
            results = engine.convert_many(files, out_dir, lang="vie", dpis=dpis,
                                          log=log, progress=prog)
            self.msg_q.put(("done", results))
        except Exception as e:
            self.msg_q.put(("fatal", f"{e}\n{traceback.format_exc()}"))

    def _drain_queue(self):
        try:
            while True:
                kind, payload = self.msg_q.get_nowait()
                if kind == "log":
                    self._logln(payload)
                elif kind == "prog":
                    done, total = payload
                    self.progress.config(value=done, maximum=total)
                    self.status_lbl.config(text=f"{done}/{total} file")
                elif kind == "done":
                    self._finish(payload)
                elif kind == "fatal":
                    self._logln("✖ Lỗi nghiêm trọng:\n" + payload, "err")
                    self._reset()
        except queue.Empty:
            pass
        self.after(80, self._drain_queue)

    def _finish(self, results):
        ok = sum(1 for r in results if r.get("out_path"))
        self._logln("─" * 48, "muted")
        for r in results:
            if not r.get("out_path"):
                self._logln(f"✖ {r['name']}: {r.get('error','lỗi')}", "err")
                continue
            warns = r.get("warnings") or []
            checks = r.get("checks") or []
            conflicts = r.get("conflicts") or []
            bad = [d for d, k, _ in checks if not k]
            if warns:
                self._logln(f"⚠ {r['name']}: " + "; ".join(warns), "warn")
            if bad:
                self._logln(f"⚠ {r['name']}: lệch cân đối — " + "; ".join(bad), "warn")
            if conflicts:
                self._logln(f"⚠ {r['name']}: {len(conflicts)} ô nên soát lại "
                            f"(hai lần đọc lệch nhau).", "warn")
            if not warns and not bad and not conflicts:
                self._logln(f"✓ {r['name']}: OK (đã kiểm tra cân đối)", "ok")
        self._logln(f"Hoàn tất: {ok}/{len(results)} file. Lưu tại: {self.out_dir.get()}", "ok")
        self.status_lbl.config(text=f"Xong {ok}/{len(results)}")
        try:
            self._open_folder(self.out_dir.get())
        except Exception:
            pass
        self._reset()

    @staticmethod
    def _open_folder(path):
        import subprocess, platform
        if platform.system() == "Windows":
            os.startfile(path)          # noqa
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def _reset(self):
        self.running = False
        self.convert_btn.config(state="normal")


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
