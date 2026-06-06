# -*- coding: utf-8 -*-
"""
Giao diện chuyển đổi Báo cáo tài chính (PDF scan) -> Excel theo Thông tư 200.

Giao diện phẳng (flat) bo tròn mềm mại, bảng màu Coolors (nhấn Sage), hỗ trợ
Sáng/Tối; có bộ đếm giờ tổng, mỗi file một thanh tiến độ bo tròn (Sage), thời
gian riêng; cho phép Tạm dừng / Dừng hẳn / Làm mới. Cuộn bằng con lăn chuột.
Nhận file PDF hoặc cả thư mục (tối đa 150 file).

Chạy:  python app.py
"""
import os
import sys
import time
import queue
import logging
import platform
import tempfile
import threading
import traceback
import webbrowser

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont

# cho phép chạy trực tiếp lẫn sau khi đóng gói
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bctc import engine, ocr           # noqa: E402
from version import __version__ as APP_VERSION   # noqa: E402

APP_TITLE = "BCTC PDF → Excel  •  Thông tư 200  •  v" + APP_VERSION
MAX_FILES = engine.MAX_FILES
EV_CONFIG = "<Configure>"
LBL_PAUSE = "⏸  Tạm dừng"
LBL_RETRY = "↻  Thử lại lỗi"
CAP_TIME = "THỜI GIAN"


# ----------------------------------------------------------------------
# Ghi log ra FILE để chẩn đoán (rất hữu ích khi chạy bản đóng gói .exe/.app)
# ----------------------------------------------------------------------
LOG_NAME = "BCTC_PDF_to_Excel.log"


def _log_file_path():
    """Chọn nơi ghi log mà người dùng chắc chắn ghi được."""
    cands = []
    if getattr(sys, "frozen", False):
        cands.append(os.path.join(os.path.dirname(sys.executable), LOG_NAME))
    cands.append(os.path.join(os.path.expanduser("~"), LOG_NAME))
    cands.append(os.path.join(tempfile.gettempdir(), LOG_NAME))
    for p in cands:
        try:
            with open(p, "a", encoding="utf-8"):
                return p
        except Exception:
            continue
    return os.path.join(tempfile.gettempdir(), LOG_NAME)


def _setup_logger(path):
    lg = logging.getLogger("bctc")
    lg.setLevel(logging.DEBUG)
    lg.propagate = False
    if not lg.handlers:
        try:
            fh = logging.FileHandler(path, encoding="utf-8")
            fh.setFormatter(logging.Formatter("%(asctime)s  %(message)s",
                                              "%Y-%m-%d %H:%M:%S"))
            lg.addHandler(fh)
        except Exception:
            pass
    return lg

# ----------------------------------------------------------------------
# Bảng màu chuẩn (Coolors): cream F4F1DE · terracotta E07A5F · navy 3D405B
#                           · sage 81B29A · sand F2CC8F
# https://coolors.co/f4f1de-e07a5f-3d405b-81b29a-f2cc8f
# Giao diện PHẲNG (không gradient), nhấn nhiều màu Sage.
# ----------------------------------------------------------------------
THEMES = {
    "light": {
        "bg": "#FAFAF7", "card": "#FFFFFF", "list_bg": "#FFFFFF",
        "row_alt": "#F3F3EE", "border": "#C7C7BC", "text": "#14161F",
        "sub": "#565A6B", "trough": "#E6E6DD",
        "accent": "#D8502E", "accent_hover": "#BF441F",
        "header_bg": "#14161F",
        "ok": "#15795A", "ok_hover": "#0F6147",
        "sage_soft": "#E2F0EA", "sage_soft_hover": "#D2E7DD",
        "warn": "#B9770A", "err": "#C0392B", "dot": "#B5B5A8",
        "soft_bg": "#FBE9E3", "soft_hover": "#F6D9CF",
        "neutral_bg": "#ECECE4", "neutral_hover": "#E0E0D6",
        "log_bg": "#FBFBF9", "entry_bg": "#FFFFFF",
        "disabled_bg": "#E4E4DC", "disabled_fg": "#A8A89E",
    },
    "dark": {
        "bg": "#14161B", "card": "#1C1F26", "list_bg": "#1C1F26",
        "row_alt": "#232730", "border": "#3C424E", "text": "#F4F6FA",
        "sub": "#A2A7B5", "trough": "#2A2E37",
        "accent": "#EC6A45", "accent_hover": "#F5805F",
        "header_bg": "#0C0E12",
        "ok": "#34D399", "ok_hover": "#5BD9AC",
        "sage_soft": "#1E3A30", "sage_soft_hover": "#264A3C",
        "warn": "#F2B233", "err": "#E0654C", "dot": "#4A4F5C",
        "soft_bg": "#3A2620", "soft_hover": "#4A3128",
        "neutral_bg": "#262A33", "neutral_hover": "#303642",
        "log_bg": "#15171D", "entry_bg": "#1C1F26",
        "disabled_bg": "#2A2E37", "disabled_fg": "#6B7080",
    },
}

# Bảng màu hiện hành (được hoán đổi tại chỗ khi đổi theme)
C = dict(THEMES["light"])

# Font lựa chọn lúc chạy (điền trong App.__init__)
FONT = "Helvetica"


def apply_theme(name):
    C.clear()
    C.update(THEMES[name])


def _font(size, weight="normal"):
    return (FONT, size, weight)


def _pick_font():
    try:
        fams = set(tkfont.families())
    except Exception:
        return "Helvetica"
    for f in ("SF Pro Text", "SF Pro Display", ".AppleSystemUIFont",
              "Helvetica Neue", "Segoe UI", "Arial"):
        if f in fams:
            return f
    return "Helvetica"


def _hex(h):
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _shade(h, factor):
    r, g, b = _hex(h)
    return "#%02x%02x%02x" % (max(0, min(255, int(r * factor))),
                              max(0, min(255, int(g * factor))),
                              max(0, min(255, int(b * factor))))


def _mix(h1, h2, t):
    """Trộn hai màu: t = tỉ lệ của h2 (0..1)."""
    r1, g1, b1 = _hex(h1)
    r2, g2, b2 = _hex(h2)
    return "#%02x%02x%02x" % (int(r1 + (r2 - r1) * t),
                              int(g1 + (g2 - g1) * t),
                              int(b1 + (b2 - b1) * t))


def _tint(color, t=0.86):
    """Màu nhạt (hover của nút viền): trộn màu về phía nền hiện hành."""
    return _mix(color, C["bg"], t)


def _round_rect(cv, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r, x2, y2 - r, x2, y2,
           x2 - r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return cv.create_polygon(pts, smooth=True, **kw)


def _fmt_time(sec):
    sec = int(sec)
    return f"{sec // 60:02d}:{sec % 60:02d}"


def _middle_ellipsis(s, n=46):
    if len(s) <= n:
        return s
    head = (n - 1) // 2
    tail = n - 1 - head
    return s[:head] + "…" + s[-tail:]


# ======================================================================
# Thẻ bo tròn (Canvas) — nền + viền bo góc, chứa nội dung trong .body
# ======================================================================
class RoundCard(tk.Canvas):
    def __init__(self, parent, *, app_bg, fill, border, radius=16, pad=8, fit=False):
        super().__init__(parent, highlightthickness=0, bd=0, bg=app_bg)
        self._fill, self._border = fill, border
        self._radius, self._pad, self._fit = radius, pad, fit
        self.body = tk.Frame(self, bg=fill)
        self._win = self.create_window(0, 0, window=self.body, anchor="nw")
        self.bind(EV_CONFIG, self._on_cfg)
        if fit:
            self.body.bind(EV_CONFIG, self._on_fit)

    def _on_fit(self, e):
        self.configure(height=e.height + 2 * self._pad)

    def _on_cfg(self, e):
        w, h = e.width, e.height
        self.delete("bg")
        _round_rect(self, 1, 1, w - 1, h - 1, self._radius,
                    fill=self._fill, outline=self._border, width=1, tags="bg")
        self.tag_lower("bg")
        p = self._pad
        self.coords(self._win, p, p)
        self.itemconfig(self._win, width=w - 2 * p, height=h - 2 * p)


# ======================================================================
# Thanh tiến độ bo tròn 4 góc (tự vẽ) — mềm mại, mặc định màu Sage
# ======================================================================
class RoundProgress(tk.Canvas):
    def __init__(self, parent, *, app_bg, trough, fill, height=9, radius=4):
        super().__init__(parent, height=height, highlightthickness=0, bd=0, bg=app_bg)
        self._trough = trough
        self._fill = fill
        self._radius = radius
        self._frac = 0.0
        self._cw = 0
        self._ch = height
        self.bind(EV_CONFIG, self._on_cfg)

    def _on_cfg(self, e):
        self._cw, self._ch = e.width, e.height
        self._draw()

    def set_fill(self, color):
        self._fill = color
        self._draw()

    def set_frac(self, f):
        self._frac = max(0.0, min(1.0, f))
        self._draw()

    def get_frac(self):
        return self._frac

    def _draw(self):
        if self._cw <= 1:
            return
        self.delete("all")
        w, h = self._cw, self._ch
        r = min(self._radius, h / 2)
        _round_rect(self, 1, 1, w - 1, h - 1, r, fill=self._trough, outline="")
        if self._frac > 0:
            x2 = 1 + (w - 2) * self._frac
            x2 = min(w - 1, max(1 + 2 * r, x2))
            _round_rect(self, 1, 1, x2, h - 1, r, fill=self._fill, outline="")


# ======================================================================
# Header phẳng (flat) + bộ đếm giờ tổng
# ======================================================================
class Header(tk.Canvas):
    # Sprite capybara (by Rainloaf — rainloaf.itch.io/capybara-sprite-sheet):
    #   sheet assets/capybara.png = 5 cột x 2 hàng (40x30 mỗi khung)
    #   hàng 0 = đi PHẢI · hàng 1 = đi TRÁI
    CAPY_W, CAPY_H, CAPY_COLS = 40, 30, 5
    CAPY_SPEED = 4          # px mỗi bước
    CAPY_INTERVAL = 80      # ms mỗi bước
    CAPY_MARGIN = 22        # lề ngang khi đi qua lại
    CAPY_BOTTOM = 4         # khoảng cách tới mép dưới header
    HEIGHT = 86             # chiều cao header (gọn cho màn hình thấp)

    def __init__(self, parent, title, subtitle):
        super().__init__(parent, height=self.HEIGHT, highlightthickness=0, bd=0)
        self._title = title
        self._subtitle = subtitle
        self._timer = "00:00"
        self._caption = CAP_TIME

        # ---- trạng thái capybara (kỹ thuật sprite) ----
        self._capy_R, self._capy_L, self._capy_sheet = [], [], None
        self._load_capy_sprite()
        self._capy_running = False
        self._capy_paused = False
        self._capy_dir = 1          # 1 = phải, -1 = trái
        self._capy_x = float(self.CAPY_MARGIN)
        self._capy_fi = 0           # chỉ số khung đi bộ
        self._capy_step = 0
        self._capy_job = None
        self._capy_item = None
        self._capy_xmin = self.CAPY_MARGIN
        self._capy_xmax = self.CAPY_MARGIN

        self.bind(EV_CONFIG, self._redraw)

    # -------------------------------------------- nạp & cắt khung từ sprite-sheet
    def _load_capy_sprite(self):
        try:
            base = os.path.dirname(os.path.abspath(__file__))
            p = os.path.join(base, "assets", "capybara.png")
            if not os.path.exists(p):
                return
            self._capy_sheet = tk.PhotoImage(file=p)   # giữ tham chiếu, tránh GC
            w, h = self.CAPY_W, self.CAPY_H

            def cut(col, row):
                fr = tk.PhotoImage(width=w, height=h)
                fr.tk.call(fr, "copy", self._capy_sheet, "-from",
                           col * w, row * h, col * w + w, row * h + h, "-to", 0, 0)
                return fr

            self._capy_R = [cut(c, 0) for c in range(self.CAPY_COLS)]
            self._capy_L = [cut(c, 1) for c in range(self.CAPY_COLS)]
        except Exception:
            self._capy_R, self._capy_L, self._capy_sheet = [], [], None

    def _capy_ready(self):
        return bool(self._capy_R) and bool(self._capy_L)

    def _capy_ytop(self):
        h = self.winfo_height() or 132
        return h - self.CAPY_H - self.CAPY_BOTTOM

    def set_timer(self, t):
        self._timer = t
        if hasattr(self, "_id_timer"):
            self.itemconfig(self._id_timer, text=t)

    def set_caption(self, c):
        self._caption = c
        if hasattr(self, "_id_cap"):
            self.itemconfig(self._id_cap, text=c)

    # ----------------------------------------------------- điều khiển capybara
    def capy_start(self):
        if not self._capy_ready():
            return
        self._capy_running = True
        self._capy_paused = False
        self._capy_dir = 1
        self._capy_x = float(self._capy_xmin)
        self._capy_fi = 0
        self._capy_step = 0
        if self._capy_item is not None:
            self.itemconfig(self._capy_item, state="normal", image=self._capy_R[0])
            self.coords(self._capy_item, self._capy_x, self._capy_ytop())
        if self._capy_job is None:
            self._capy_job = self.after(self.CAPY_INTERVAL, self._capy_anim)

    def capy_pause(self, paused):
        self._capy_paused = bool(paused)

    def capy_stop(self):
        self._capy_running = False
        self._capy_paused = False
        if self._capy_job is not None:
            try:
                self.after_cancel(self._capy_job)
            except Exception:
                pass
            self._capy_job = None
        if self._capy_item is not None:
            self.itemconfig(self._capy_item, state="hidden")

    def _capy_anim(self):
        self._capy_job = None
        if not self._capy_running:
            return
        if (not self._capy_paused and self._capy_item is not None
                and self._capy_ready()):
            self._capy_x += self.CAPY_SPEED * self._capy_dir
            if self._capy_x >= self._capy_xmax:
                self._capy_x = float(self._capy_xmax)
                self._capy_dir = -1
            elif self._capy_x <= self._capy_xmin:
                self._capy_x = float(self._capy_xmin)
                self._capy_dir = 1
            # đổi khung đi bộ mỗi 2 bước cho dáng đi tự nhiên
            self._capy_step += 1
            if self._capy_step % 2 == 0:
                self._capy_fi = (self._capy_fi + 1) % self.CAPY_COLS
            frames = self._capy_R if self._capy_dir >= 0 else self._capy_L
            self.itemconfig(self._capy_item, image=frames[self._capy_fi])
            self.coords(self._capy_item, self._capy_x, self._capy_ytop())
        self._capy_job = self.after(self.CAPY_INTERVAL, self._capy_anim)

    def _redraw(self, e):
        self.delete("all")
        w, h = e.width, e.height
        self.configure(bg=C["header_bg"])
        self.create_rectangle(0, 0, w, h, fill=C["header_bg"], outline="")
        self.create_text(22, 18, text=self._title, anchor="w",
                         fill="#FFFFFF", font=_font(16, "bold"))
        self.create_text(22, 40, text=self._subtitle, anchor="w",
                         fill="#F4F1DE", font=_font(9))
        self._id_cap = self.create_text(w - 22, 15, text=self._caption,
                                        anchor="e", fill="#F2CC8F", font=_font(9, "bold"))
        self._id_timer = self.create_text(w - 22, 40, text=self._timer,
                                          anchor="e", fill="#FFFFFF", font=_font(20, "bold"))

        # ---- capybara: tạo lại item ảnh ở dải dưới header ----
        self._capy_item = None
        if self._capy_ready():
            self._capy_xmin = self.CAPY_MARGIN
            self._capy_xmax = max(self._capy_xmin, w - self.CAPY_MARGIN - self.CAPY_W)
            self._capy_x = min(max(self._capy_x, self._capy_xmin), self._capy_xmax)
            frames = self._capy_R if self._capy_dir >= 0 else self._capy_L
            self._capy_item = self.create_image(
                self._capy_x, h - self.CAPY_H - self.CAPY_BOTTOM,
                anchor="nw", image=frames[self._capy_fi])
            if not self._capy_running:
                self.itemconfig(self._capy_item, state="hidden")


# ======================================================================
# Nút bo góc (Canvas) — phẳng, có hover
# ======================================================================
class RoundButton(tk.Canvas):
    """Nút bo góc. Hai kiểu:
       - VIỀN (outline): truyền outline=<màu>, outline_w>=2; nền = app_bg,
         chữ + viền cùng màu; hover tô nền nhạt.
       - ĐẶC (solid):   chỉ truyền bg/fg/hover như cũ (dùng cho CTA chính).
    """
    def __init__(self, parent, text, command, *, bg, fg, hover, app_bg,
                 width=150, height=44, radius=14, font=None,
                 outline="", outline_w=0, hover_outline=None):
        super().__init__(parent, width=width, height=height,
                         highlightthickness=0, bd=0, bg=app_bg)
        self.command = command
        self._bg, self._hover, self._fg = bg, hover, fg
        self._outline = outline
        self._outline_w = outline_w
        self._hover_outline = hover_outline or outline
        self._enabled = True
        self._rect = _round_rect(self, 2, 2, width - 2, height - 2, radius,
                                 fill=bg, outline=outline, width=outline_w)
        self._txt = self.create_text(width // 2, height // 2, text=text,
                                     fill=fg, font=font or _font(11, "bold"))
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
        self.bind("<Button-1>", self._click)

    def _enter(self, _):
        if self._enabled:
            self.itemconfig(self._rect, fill=self._hover, outline=self._hover_outline)
            self.config(cursor="hand2")

    def _leave(self, _):
        if self._enabled:
            self.itemconfig(self._rect, fill=self._bg, outline=self._outline)

    def _click(self, _):
        if self._enabled and self.command:
            self.command()

    def set_text(self, t):
        self.itemconfig(self._txt, text=t)

    def set_enabled(self, on):
        self._enabled = on
        self.itemconfig(self._rect,
                        fill=self._bg if on else C["disabled_bg"],
                        outline=self._outline if on else C["disabled_bg"])
        self.itemconfig(self._txt, fill=self._fg if on else C["disabled_fg"])
        self.config(cursor="hand2" if on else "")


# ======================================================================
# Một dòng file: chấm trạng thái + tên + thời gian + thanh tiến độ bo tròn
# ======================================================================
class FileRow(tk.Frame):
    def __init__(self, parent, name, bg, *, on_delete=None, on_select=None):
        super().__init__(parent, bg=bg)
        self._bg = bg
        self._on_delete = on_delete
        self._on_select = on_select
        self.selected = False
        self._deletable = True
        self._pad = tk.Frame(self, bg=bg)
        self._pad.pack(fill="x", padx=14, pady=7)

        top = tk.Frame(self._pad, bg=bg)
        self._top = top
        top.pack(fill="x")
        # ô chọn (cho xoá nhiều file)
        self.chk = tk.Label(top, text="☐", bg=bg, fg=C["sub"],
                            font=_font(13), cursor="hand2")
        self.chk.pack(side="left", padx=(0, 8))
        self.chk.bind("<Button-1>", lambda e: self._toggle())
        self.dot = tk.Canvas(top, width=12, height=12, bg=bg,
                             highlightthickness=0, bd=0)
        self._dot_id = self.dot.create_oval(2, 2, 11, 11, fill=C["dot"], outline="")
        self.dot.pack(side="left", padx=(0, 10))
        self.name_lbl = tk.Label(top, text=_middle_ellipsis(name), bg=bg, fg=C["text"],
                                 font=_font(11, "bold"), anchor="w")
        self.name_lbl.pack(side="left")
        # nút xoá 1 file
        self.del_btn = tk.Label(top, text="✕", bg=bg, fg=C["sub"],
                                font=_font(12, "bold"), cursor="hand2")
        self.del_btn.pack(side="right", padx=(8, 0))
        self.del_btn.bind("<Button-1>", lambda e: self._delete())
        self.meta_lbl = tk.Label(top, text="Chờ", bg=bg, fg=C["sub"],
                                 font=_font(10), anchor="e")
        self.meta_lbl.pack(side="right")

        self.bar = RoundProgress(self._pad, app_bg=bg, trough=C["trough"],
                                 fill=C["ok"], height=8, radius=4)
        self.bar.pack(fill="x", pady=(6, 0))

    def set_bg(self, bg):
        """Đổi màu nền (tô lại xen kẽ sau khi xoá) — mượt, không dựng lại."""
        self._bg = bg
        for w in (self, self._pad, self._top, self.chk, self.dot,
                  self.name_lbl, self.del_btn, self.meta_lbl, self.bar):
            try:
                w.config(bg=bg)
            except Exception:
                pass

    def _toggle(self):
        if not self._deletable:
            return
        self.set_selected(not self.selected)
        if self._on_select:
            self._on_select()

    def set_selected(self, v):
        self.selected = bool(v)
        self.chk.config(text="☑" if self.selected else "☐",
                        fg=C["ok"] if self.selected else C["sub"])

    def _delete(self):
        if self._deletable and self._on_delete:
            self._on_delete(self)

    def set_deletable(self, on):
        """Khoá/Mở thao tác chọn & xoá (khoá khi đang chuyển đổi)."""
        self._deletable = on
        cur = "hand2" if on else ""
        self.chk.config(cursor=cur, fg=(C["ok"] if self.selected else C["sub"])
                        if on else C["disabled_fg"])
        self.del_btn.config(cursor=cur, fg=C["err"] if on else C["disabled_fg"])

    def _set_dot(self, color):
        self.dot.itemconfig(self._dot_id, fill=color)

    def get_frac(self):
        return self.bar.get_frac()

    def set_pending(self):
        self.bar.set_fill(C["ok"])
        self.bar.set_frac(0)
        self._set_dot(C["dot"])
        self.meta_lbl.config(text="Chờ", fg=C["sub"])

    def set_processing(self, frac, elapsed):
        # Sage xuyên suốt trong lúc xử lý
        self.bar.set_fill(C["ok"])
        self.bar.set_frac(max(0.03, frac))
        self._set_dot(C["ok"])
        self.meta_lbl.config(text=f"Đang xử lý · {elapsed:.1f}s · {int(frac*100)}%",
                             fg=C["ok"])

    def set_done(self, elapsed, warn=False):
        # Thành công -> Sage; chỉ chuyển Cam khi có cảnh báo
        self.bar.set_fill(C["warn"] if warn else C["ok"])
        self.bar.set_frac(1.0)
        self._set_dot(C["warn"] if warn else C["ok"])
        self.meta_lbl.config(text=("⚠ Cần soát · %.1fs" % elapsed) if warn
                             else ("✓ Xong · %.1fs" % elapsed),
                             fg=C["warn"] if warn else C["ok"])

    def set_error(self, elapsed):
        # Chỉ màu Đỏ khi thất bại
        self.bar.set_fill(C["err"])
        self.bar.set_frac(1.0)
        self._set_dot(C["err"])
        self.meta_lbl.config(text="✖ Lỗi · %.1fs" % elapsed, fg=C["err"])

    def set_stopped(self):
        self.bar.set_fill(C["dot"])
        self._set_dot(C["sub"])
        self.meta_lbl.config(text="⏹ Đã dừng", fg=C["sub"])


# ======================================================================
# Ứng dụng chính
# ======================================================================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        global FONT
        FONT = _pick_font()

        # --- ghi log ra file (chẩn đoán, nhất là bản .exe/.app) ---
        self.log_path = _log_file_path()
        self._flog = _setup_logger(self.log_path)
        self._flog.info("=" * 64)
        self._flog.info("Khởi động BCTC PDF → Excel v%s", APP_VERSION)

        self.title(APP_TITLE)
        self.geometry("940x636")
        self.minsize(420, 320)          # nhỏ hơn min content -> tự hiện thanh cuộn
        self._set_icon()

        self.theme_name = "dark"
        apply_theme(self.theme_name)
        self.configure(bg=C["bg"])

        self.files = []
        self.rows = []
        self.failed = set()      # chỉ số file bị lỗi (để thử lại)
        self._run_map = []       # ánh xạ chỉ số lượt chạy -> chỉ số file
        self.out_dir = tk.StringVar(value="")
        self.hi_quality = tk.BooleanVar(value=False)
        self.msg_q = queue.Queue()
        self.running = False

        # điều khiển dừng / tạm dừng
        self._cancel = threading.Event()
        self._resume = threading.Event()
        self._resume.set()
        self.paused = False
        self.paused_total = 0.0
        self._pause_t = None

        # đếm giờ
        self.t0 = None
        self.file_t0 = {}
        self.file_elapsed = {}
        self.active_index = None

        self._init_styles()
        self._build()
        self._log_diagnostics()
        self.after(80, self._drain_queue)
        self.after(120, self._tick)

    # ------------------------------------------------------------ chẩn đoán
    def _log_diagnostics(self):
        """Ghi thông tin môi trường + tình trạng Tesseract ra file log."""
        try:
            self._flog.info("App v%s | %s %s | Python %s", APP_VERSION,
                            platform.system(), platform.release(),
                            sys.version.split()[0])
            self._flog.info("Frozen=%s | exe=%s | MEIPASS=%s",
                            getattr(sys, "frozen", False), sys.executable,
                            getattr(sys, "_MEIPASS", None))
            tess, td = ocr.locate_tesseract()
            self._flog.info("Tesseract path = %s", tess)
            self._flog.info("tessdata dir   = %s", td)
            import pytesseract
            if tess:
                pytesseract.pytesseract.tesseract_cmd = tess
            try:
                self._flog.info("Tesseract version = %s",
                                pytesseract.get_tesseract_version())
            except Exception as e:
                self._flog.error("Không lấy được tesseract version: %r", e)
            try:
                self._flog.info("Languages = %s",
                                pytesseract.get_languages(config=""))
            except Exception as e:
                self._flog.error("Không lấy được languages: %r", e)
        except Exception:
            try:
                self._flog.error("Lỗi diagnostics:\n%s", traceback.format_exc())
            except Exception:
                pass

    def _set_icon(self):
        """Đặt icon cửa sổ (PNG) nếu có."""
        try:
            base = os.path.dirname(os.path.abspath(__file__))
            for nm in ("icon_256.png", "icon.png"):
                p = os.path.join(base, "assets", nm)
                if os.path.exists(p):
                    self._icon_img = tk.PhotoImage(file=p)
                    self.iconphoto(True, self._icon_img)
                    break
        except Exception:
            pass

    # ------------------------------------------------------------------ styles
    def _init_styles(self):
        st = ttk.Style(self)
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure("Vertical.TScrollbar", background=C["border"],
                     troughcolor=C["card"], bordercolor=C["card"],
                     arrowcolor=C["sub"], relief="flat")
        st.map("Vertical.TScrollbar", background=[("active", C["ok"])])
        st.configure("Card.TCheckbutton", background=C["bg"], foreground=C["sub"],
                     font=_font(10))
        st.map("Card.TCheckbutton", background=[("active", C["bg"])],
               foreground=[("active", C["text"])])

    # ------------------------------------------------------ nút (viền/đặc)
    def _outline_btn(self, parent, text, cmd, color, width, height=44, font=None):
        """Nút VIỀN: nền trùng nền app, viền + chữ cùng màu, hover tô nhạt."""
        return RoundButton(parent, text, cmd, bg=C["bg"], fg=color,
                           hover=_tint(color), app_bg=C["bg"],
                           outline=color, outline_w=2,
                           width=width, height=height, font=font)

    def _solid_btn(self, parent, text, cmd, color, width, height=44, font=None):
        """Nút ĐẶC (CTA chính): nền màu, chữ trắng."""
        return RoundButton(parent, text, cmd, bg=color, fg="#FFFFFF",
                           hover=_shade(color, 0.9), app_bg=C["bg"],
                           width=width, height=height, font=font)

    # ------------------------------------------------------------------ UI
    def _build(self):
        # ===== Vùng CUỘN GỐC: cửa sổ nhỏ vẫn xem hết app bằng cách cuộn =====
        # content được ép kích thước tối thiểu; khi cửa sổ < min -> hiện thanh cuộn.
        self._root_cv = tk.Canvas(self, bg=C["bg"], highlightthickness=0, bd=0)
        self._root_vsb = ttk.Scrollbar(self, orient="vertical", command=self._root_cv.yview)
        self._root_hsb = ttk.Scrollbar(self, orient="horizontal", command=self._root_cv.xview)
        self._root_cv.configure(yscrollcommand=self._root_vsb.set,
                                xscrollcommand=self._root_hsb.set)
        self._root_cv.grid(row=0, column=0, sticky="nsew")
        self._root_vsb.grid(row=0, column=1, sticky="ns")
        self._root_hsb.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        content = tk.Frame(self._root_cv, bg=C["bg"])
        self._content_id = self._root_cv.create_window((0, 0), window=content, anchor="nw")
        self._root_cv.bind(EV_CONFIG, self._on_root_resize)
        self.bind_all("<MouseWheel>", self._on_wheel)
        self.bind_all("<Button-4>", lambda e: self._wheel_dir(e, -1))
        self.bind_all("<Button-5>", lambda e: self._wheel_dir(e, 1))

        self.header = Header(content, "Chuyển Báo cáo tài chính PDF → Excel",
                             "Bảng cân đối kế toán · Kết quả HĐKD · Lưu chuyển tiền tệ "
                             "— mỗi báo cáo 1 sheet (Thông tư 200)")
        self.header.pack(fill="x")
        self._content = content

        # thanh tiến độ tổng (bo tròn, Sage) + dòng trạng thái
        topbar = tk.Frame(content, bg=C["bg"])
        topbar.pack(fill="x", padx=18, pady=(8, 0))
        self.overall = RoundProgress(topbar, app_bg=C["bg"], trough=C["trough"],
                                     fill=C["ok"], height=8, radius=4)
        self.overall.pack(fill="x")
        self.status_lbl = tk.Label(topbar, text="Sẵn sàng", bg=C["bg"], fg=C["sub"],
                                   font=_font(10), anchor="w")
        self.status_lbl.pack(anchor="w", pady=(4, 0))

        # ---- thanh công cụ (nhấn Sage) ----
        tool = tk.Frame(content, bg=C["bg"])
        tool.pack(fill="x", padx=18, pady=(6, 0))
        self.btn_add = self._outline_btn(tool, "＋  Thêm file", self.add_files,
                                         C["ok"], 144, height=36)
        self.btn_add.pack(side="left")
        self.btn_folder = self._outline_btn(tool, "📁  Thêm thư mục", self.add_folder,
                                            C["ok"], 162, height=36)
        self.btn_folder.pack(side="left", padx=8)
        self.btn_clear = self._outline_btn(tool, "🗑  Xoá hết", self.clear_files,
                                           C["sub"], 112, height=36)
        self.btn_clear.pack(side="left")

        theme_txt = "🌙  Tối" if self.theme_name == "light" else "☀️  Sáng"
        self.btn_theme = self._outline_btn(tool, theme_txt, self.toggle_theme,
                                           C["sub"], 104, height=36)
        self.btn_theme.pack(side="right")
        self.count_lbl = tk.Label(tool, text="%d / %d file" % (len(self.files), MAX_FILES),
                                  bg=C["bg"], fg=C["text"], font=_font(11, "bold"))
        self.count_lbl.pack(side="right", padx=(0, 14))
        tk.Label(tool, text="v" + APP_VERSION, bg=C["bg"], fg=C["sub"],
                 font=_font(9)).pack(side="right", padx=(0, 12))

        # ---- thanh chọn nhiều file để xoá ----
        selbar = tk.Frame(content, bg=C["bg"])
        selbar.pack(fill="x", padx=18, pady=(6, 0))
        self.sel_all = tk.Label(selbar, text="☐  Chọn tất cả", bg=C["bg"], fg=C["sub"],
                                font=_font(10), cursor="hand2")
        self.sel_all.pack(side="left")
        self.sel_all.bind("<Button-1>", lambda e: self._toggle_select_all())
        self.sel_info = tk.Label(selbar, text="", bg=C["bg"], fg=C["sub"], font=_font(10))
        self.sel_info.pack(side="left", padx=(10, 0))
        self.btn_del_sel = self._outline_btn(selbar, "🗑  Xoá đã chọn", self._delete_selected,
                                             C["err"], 150, height=30, font=_font(10, "bold"))
        self.btn_del_sel.pack(side="right")
        self.btn_del_sel.set_enabled(False)

        # ---- danh sách file (thẻ bo tròn, cuộn được) ----
        listcard = RoundCard(content, app_bg=C["bg"], fill=C["list_bg"],
                             border=C["border"], radius=16, pad=6)
        listcard.pack(fill="both", expand=True, padx=18, pady=8)
        self.canvas = tk.Canvas(listcard.body, bg=C["list_bg"], highlightthickness=0, bd=0)
        vsb = ttk.Scrollbar(listcard.body, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=C["list_bg"])
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind(EV_CONFIG,
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind(EV_CONFIG,
                         lambda e: self.canvas.itemconfig(self._win, width=e.width))

        self.placeholder = tk.Label(
            self.inner, bg=C["list_bg"], fg=C["sub"], justify="center",
            font=_font(12),
            text="\n\n📄\n\nChưa có file nào\n"
                 "Bấm “Thêm file” (chỉ .pdf) hoặc “Thêm thư mục” để bắt đầu\n"
                 "Tối đa %d file mỗi lần" % MAX_FILES)

        # ---- hàng dưới: thư mục lưu + chất lượng ----
        bottom = tk.Frame(content, bg=C["bg"])
        bottom.pack(fill="x", padx=18, pady=(0, 6))

        opt = tk.Frame(bottom, bg=C["bg"])
        opt.pack(fill="x")
        tk.Label(opt, text="Lưu Excel tại:", bg=C["bg"], fg=C["text"],
                 font=_font(10, "bold")).pack(side="left")
        entrycard = RoundCard(opt, app_bg=C["bg"], fill=C["entry_bg"],
                              border=C["border"], radius=10, pad=3)
        entrycard.configure(height=34)
        entrycard.pack(side="left", fill="x", expand=True, padx=10)
        self.out_entry = tk.Entry(entrycard.body, textvariable=self.out_dir,
                                  bg=C["entry_bg"], fg=C["text"], relief="flat",
                                  font=_font(10), insertbackground=C["text"],
                                  highlightthickness=0, bd=0)
        self.out_entry.pack(fill="both", expand=True, padx=8)
        self._outline_btn(opt, "Chọn…", self.pick_out, C["sub"], 86,
                          height=36).pack(side="left")
        ttk.Checkbutton(opt, text="Chất lượng cao (chậm hơn)", style="Card.TCheckbutton",
                        variable=self.hi_quality).pack(side="left", padx=(14, 0))

        # ---- hàng nút: Chuyển đổi · Làm mới · Tạm dừng · Dừng hẳn ----
        runrow = tk.Frame(bottom, bg=C["bg"])
        runrow.pack(fill="x", pady=(8, 0))
        self.convert_btn = self._solid_btn(runrow, "CHUYỂN ĐỔI  ▶", self.start,
                                           C["accent"], 220, height=42,
                                           font=_font(12, "bold"))
        self.convert_btn.pack(side="left")
        self.btn_retry = self._outline_btn(runrow, LBL_RETRY, self.retry_failed,
                                           C["warn"], 132, height=42,
                                           font=_font(11, "bold"))
        self.btn_retry.pack(side="left", padx=(8, 0))
        self.btn_refresh = self._outline_btn(runrow, "🔄  Làm mới", self.reset_tool,
                                             C["ok"], 116, height=42,
                                             font=_font(11, "bold"))
        self.btn_refresh.pack(side="left", padx=(8, 0))
        self.btn_stop = self._outline_btn(runrow, "⏹  Dừng", self.stop,
                                          C["err"], 104, height=42,
                                          font=_font(11, "bold"))
        self.btn_stop.pack(side="right")
        self.btn_pause = self._outline_btn(runrow, LBL_PAUSE, self.toggle_pause,
                                           C["sub"], 132, height=42,
                                           font=_font(11, "bold"))
        self.btn_pause.pack(side="right", padx=(0, 8))
        self.btn_stop.set_enabled(False)
        self.btn_pause.set_enabled(False)
        self.btn_retry.set_enabled(False)

        # ---- lịch sử (thẻ bo tròn) ----
        logcard = RoundCard(content, app_bg=C["bg"], fill=C["card"],
                            border=C["border"], radius=14, pad=8, fit=True)
        logcard.pack(fill="x", padx=18, pady=(0, 10))
        tk.Label(logcard.body, text="Lịch sử", bg=C["card"], fg=C["text"],
                 font=_font(10, "bold")).pack(anchor="w")
        logf = tk.Frame(logcard.body, bg=C["card"])
        logf.pack(fill="x", pady=(3, 0))
        self.log = tk.Text(logf, height=4, bg=C["log_bg"], fg=C["text"], bd=0,
                           font=("Menlo", 9), wrap="word", state="disabled",
                           highlightthickness=0, insertbackground=C["text"])
        self.log.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(logf, command=self.log.yview)
        sb.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=sb.set)
        for tag, col in (("ok", C["ok"]), ("warn", C["warn"]),
                         ("err", C["err"]), ("muted", C["sub"])):
            self.log.tag_configure(tag, foreground=col)

        self._rebuild_list()
        self._logln(f"BCTC PDF → Excel · phiên bản v{APP_VERSION}", "muted")
        self._logln("📄 Lịch sử chi tiết: " + self.log_path, "muted")
        self._check_tesseract()
        self._sync_convert_btn()

    # ---------- vùng cuộn gốc: ép content tối thiểu, tự ẩn thanh cuộn ----------
    MIN_CONTENT_W = 740
    MIN_CONTENT_H = 560

    def _on_root_resize(self, e):
        vw, vh = e.width, e.height
        w = max(vw, self.MIN_CONTENT_W)
        h = max(vh, self.MIN_CONTENT_H)
        self._root_cv.itemconfig(self._content_id, width=w, height=h)
        self._root_cv.configure(scrollregion=(0, 0, w, h))
        # ẩn thanh cuộn khi không cần (grid_remove giữ nguyên vị trí ô)
        (self._root_vsb.grid if h > vh + 1 else self._root_vsb.grid_remove)()
        (self._root_hsb.grid if w > vw + 1 else self._root_hsb.grid_remove)()

    # ---------- cuộn bằng con lăn chuột (theo vùng con trỏ) ----------
    def _wheel_target(self, e):
        node = self.winfo_containing(e.x_root, e.y_root)
        while node is not None:
            if node is self.log:
                return self.log
            if node is self.canvas or node is self.inner:
                return self.canvas
            node = getattr(node, "master", None)
        return self._root_cv

    def _on_wheel(self, e):
        self._wheel_target(e).yview_scroll(-1 if e.delta > 0 else 1, "units")

    def _wheel_dir(self, e, d):
        self._wheel_target(e).yview_scroll(d, "units")

    # ----------------------------------------------------------- đổi theme
    def toggle_theme(self):
        if self.running:
            return
        self.theme_name = "dark" if self.theme_name == "light" else "light"
        apply_theme(self.theme_name)
        self._init_styles()
        for w in self.winfo_children():
            w.destroy()
        self.rows.clear()
        self.configure(bg=C["bg"])
        self._build()

    # ------------------------------------------------------------- helpers
    def _logln(self, text, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n", tag or ())
        self.log.see("end")
        self.log.configure(state="disabled")
        try:
            self._flog.info(text)
        except Exception:
            pass

    def _check_tesseract(self):
        try:
            ocr.configure_tesseract()
            if not ocr.has_vietnamese():
                self._logln("⚠ Chưa có gói tiếng Việt (vie) cho Tesseract.", "warn")
            else:
                self._logln("✓ Tesseract + tiếng Việt sẵn sàng.", "ok")
        except ocr.TesseractNotFound as e:
            self._logln("✖ " + str(e), "err")

    # --------------------------------------------------------------- thêm file
    def _add_paths(self, paths):
        added = 0
        hit_limit = False
        for p in paths:
            if not p.lower().endswith(".pdf"):
                continue
            if p in self.files:
                continue
            if len(self.files) >= MAX_FILES:
                hit_limit = True
                break
            self.files.append(p)
            added += 1
        if hit_limit:
            messagebox.showwarning("Giới hạn", f"Chỉ nhận tối đa {MAX_FILES} file mỗi lần.")
        if self.files and not self.out_dir.get():
            self.out_dir.set(os.path.join(os.path.dirname(self.files[0]), "Excel_output"))
        if added or hit_limit:
            self._rebuild_list()

    def add_files(self):
        if self.running:
            return
        paths = filedialog.askopenfilenames(
            title="Chọn file PDF báo cáo tài chính",
            filetypes=[("File PDF", "*.pdf")])
        self._add_paths(list(paths))

    def add_folder(self):
        if self.running:
            return
        d = filedialog.askdirectory(title="Chọn thư mục chứa file PDF")
        if not d:
            return
        found = []
        for root, _dirs, names in os.walk(d):
            for n in sorted(names):
                if n.lower().endswith(".pdf"):
                    found.append(os.path.join(root, n))
        if not found:
            messagebox.showinfo("Trống", "Không tìm thấy file .pdf trong thư mục này.")
            return
        self._add_paths(sorted(found))

    def clear_files(self):
        if self.running:
            return
        self.files.clear()
        self._rebuild_list()

    def _rebuild_list(self):
        for r in self.rows:
            r.destroy()
        self.rows.clear()
        if not self.files:
            self.placeholder.pack(fill="both", expand=True, pady=40)
        else:
            self.placeholder.pack_forget()
            for i, p in enumerate(self.files):
                bg = C["list_bg"] if i % 2 == 0 else C["row_alt"]
                row = FileRow(self.inner, os.path.basename(p), bg,
                              on_delete=self._delete_row,
                              on_select=self._on_row_select)
                row.pack(fill="x")
                self.rows.append(row)
        self.count_lbl.config(text=f"{len(self.files)} / {MAX_FILES} file")
        self.canvas.yview_moveto(0)
        self._sync_convert_btn()
        self._on_row_select()

    def _sync_convert_btn(self):
        """Nút Chuyển đổi chỉ sáng khi có file (và không đang chạy)."""
        if not hasattr(self, "convert_btn") or self.running:
            return
        self.convert_btn.set_enabled(bool(self.files))

    # ---------------------------------------------------- chọn & xoá file
    def _on_row_select(self):
        """Cập nhật số đã chọn + nút Xoá đã chọn + ô Chọn tất cả."""
        if not hasattr(self, "btn_del_sel"):
            return
        n = sum(1 for r in self.rows if r.selected)
        self.sel_info.config(text=(f"· Đã chọn {n}" if n else ""))
        self.btn_del_sel.set_enabled(n > 0 and not self.running)
        total = len(self.rows)
        allsel = total > 0 and n == total
        self.sel_all.config(text=("☑  Bỏ chọn tất cả" if allsel else "☐  Chọn tất cả"),
                            fg=C["ok"] if allsel else C["sub"])

    def _toggle_select_all(self):
        if self.running or not self.rows:
            return
        target = not all(r.selected for r in self.rows)
        for r in self.rows:
            r.set_selected(target)
        self._on_row_select()

    def _remove_files(self, idxs):
        """Xoá các file theo chỉ số — mượt: chỉ huỷ đúng dòng bị xoá, tô lại
        màu xen kẽ, giữ nguyên vị trí cuộn (không dựng lại cả danh sách)."""
        if self.running:
            messagebox.showinfo("Đang chuyển đổi",
                                "Không thể xoá khi đang chạy. Hãy Dừng rồi xoá.")
            return
        idxs = sorted((i for i in idxs if 0 <= i < len(self.files)), reverse=True)
        if not idxs:
            return
        for i in idxs:                      # xoá từ cuối -> đầu để chỉ số không lệch
            del self.files[i]
            self.rows.pop(i).destroy()
        self.failed = set()                 # chỉ số đã đổi -> bỏ hàng đợi thử lại
        self.btn_retry.set_enabled(False)
        self.btn_retry.set_text(LBL_RETRY)
        if not self.rows:
            self.placeholder.pack(fill="both", expand=True, pady=40)
        else:                               # tô lại màu xen kẽ (không dựng lại)
            for i, row in enumerate(self.rows):
                row.set_bg(C["list_bg"] if i % 2 == 0 else C["row_alt"])
        self.count_lbl.config(text=f"{len(self.files)} / {MAX_FILES} file")
        self._sync_convert_btn()
        self._on_row_select()

    def _delete_row(self, row):
        if row in self.rows:
            self._remove_files({self.rows.index(row)})

    def _delete_selected(self):
        idxs = {i for i, r in enumerate(self.rows) if r.selected}
        self._remove_files(idxs)

    def pick_out(self):
        d = filedialog.askdirectory(title="Chọn thư mục lưu Excel")
        if d:
            self.out_dir.set(d)

    # --------------------------------------------------------------- chuyển đổi
    def start(self, indices=None):
        if self.running:
            return
        if not self.files:
            messagebox.showinfo("Chưa có file", "Hãy thêm ít nhất 1 file PDF.")
            return
        out = self.out_dir.get().strip()
        if not out:
            messagebox.showinfo("Thiếu thư mục", "Hãy chọn thư mục lưu Excel.")
            return

        if indices is None:               # chạy mới toàn bộ -> xoá danh sách lỗi cũ
            indices = list(range(len(self.files)))
            self.failed = set()
        if not indices:
            return
        self._run_map = list(indices)
        files_subset = [self.files[k] for k in indices]

        self.running = True
        self._cancel.clear()
        self._resume.set()
        self.paused = False
        self.paused_total = 0.0
        self._pause_t = None

        self.convert_btn.set_enabled(False)
        self.convert_btn.set_text("ĐANG XỬ LÝ…")
        self.btn_add.set_enabled(False)
        self.btn_folder.set_enabled(False)
        self.btn_clear.set_enabled(False)
        self.btn_theme.set_enabled(False)
        self.btn_refresh.set_enabled(False)
        self.btn_retry.set_enabled(False)
        self.btn_pause.set_enabled(True)
        self.btn_pause.set_text(LBL_PAUSE)
        self.btn_stop.set_enabled(True)
        self.btn_del_sel.set_enabled(False)        # khoá xoá khi đang chạy
        for r in self.rows:
            r.set_deletable(False)
        self.overall.set_frac(0)
        self.status_lbl.config(text="Đang xử lý…", fg=C["text"])
        self.header.set_caption(CAP_TIME)
        self.header.capy_start()          # capybara chạy qua lại lúc convert

        self.t0 = time.time()
        self.file_t0.clear()
        self.file_elapsed.clear()
        self.active_index = None
        for k in indices:
            self.rows[k].set_pending()

        self._logln("─" * 52, "muted")
        t = threading.Thread(target=self._worker, args=(files_subset, out), daemon=True)
        t.start()

    def retry_failed(self):
        if self.running or not self.failed:
            return
        self._logln(f"↻ Thử lại {len(self.failed)} file bị lỗi…", "warn")
        self.start(indices=sorted(self.failed))

    def toggle_pause(self):
        if not self.running:
            return
        if not self.paused:
            self.paused = True
            self._pause_t = time.time()
            self._resume.clear()
            self.btn_pause.set_text("▶  Tiếp tục")
            self.status_lbl.config(text="Đã tạm dừng (dừng trước file kế tiếp)…",
                                   fg=C["warn"])
            self.header.set_caption("TẠM DỪNG")
            self.header.capy_pause(True)        # capybara đứng yên khi tạm dừng
        else:
            self.paused = False
            if self._pause_t:
                self.paused_total += time.time() - self._pause_t
                self._pause_t = None
            self._resume.set()
            self.btn_pause.set_text(LBL_PAUSE)
            self.status_lbl.config(text="Đang xử lý…", fg=C["text"])
            self.header.set_caption(CAP_TIME)
            self.header.capy_pause(False)       # capybara đi tiếp

    def stop(self):
        if not self.running:
            return
        self._cancel.set()
        if self.paused:                 # mở khoá để luồng thoát khỏi tạm dừng
            self.paused = False
            if self._pause_t:
                self.paused_total += time.time() - self._pause_t
                self._pause_t = None
        self._resume.set()
        self.btn_pause.set_enabled(False)
        self.btn_stop.set_enabled(False)
        self.status_lbl.config(text="Đang dừng…", fg=C["err"])

    def reset_tool(self):
        """Làm mới: đưa công cụ về trạng thái sẵn sàng."""
        if self.running:
            return
        self.files.clear()
        self.failed = set()
        self.btn_retry.set_enabled(False)
        self.btn_retry.set_text(LBL_RETRY)
        self._rebuild_list()
        self.overall.set_frac(0)
        self.t0 = None
        self.file_t0.clear()
        self.file_elapsed.clear()
        self.active_index = None
        self.header.set_timer("00:00")
        self.header.set_caption(CAP_TIME)
        self.status_lbl.config(text="Sẵn sàng", fg=C["sub"])
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self._check_tesseract()

    def _worker(self, files, out_dir):
        def log(m):
            self.msg_q.put(("log", m))

        def prog(done, total):
            self.msg_q.put(("prog", (done, total)))

        def on_file(i, ev, data):
            self.msg_q.put(("file", (i, ev, data)))

        try:
            dpis = (180, 220, 290) if self.hi_quality.get() else (180, 235)
            try:
                self._flog.info("Bắt đầu convert %d file | dpis=%s | out=%s",
                                len(files), dpis, out_dir)
            except Exception:
                pass
            results = engine.convert_many(
                files, out_dir, lang="vie", dpis=dpis, log=log, progress=prog,
                on_file=on_file,
                cancel=self._cancel.is_set,
                pause_wait=self._resume.wait)
            self.msg_q.put(("done", results))
        except Exception as e:
            self.msg_q.put(("fatal", f"{e}\n{traceback.format_exc()}"))

    # --------------------------------------------------------------- vòng lặp UI
    def _tick(self):
        if self.running and self.t0 is not None and not self.paused:
            el_total = time.time() - self.t0 - self.paused_total
            self.header.set_timer(_fmt_time(el_total))
            i = self.active_index
            if i is not None and i < len(self.rows) and i in self.file_t0:
                el = time.time() - self.file_t0[i]
                self.rows[i].set_processing(self.rows[i].get_frac(), el)
        self.after(120, self._tick)

    def _drain_queue(self):
        try:
            while True:
                kind, payload = self.msg_q.get_nowait()
                if kind == "log":
                    self._logln(payload)
                elif kind == "prog":
                    done, total = payload
                    self.overall.set_frac(done / max(1, total))
                    self.status_lbl.config(text=f"{done}/{total} file đã xong")
                elif kind == "file":
                    self._on_file_event(*payload)
                elif kind == "done":
                    self._finish(payload)
                elif kind == "fatal":
                    self._logln("✖ Lỗi nghiêm trọng:\n" + payload, "err")
                    try:
                        self._flog.error("FATAL:\n%s", payload)
                    except Exception:
                        pass
                    self._handle_fatal(payload)
                    self._reset()
        except queue.Empty:
            pass
        self.after(80, self._drain_queue)

    def _handle_fatal(self, payload):
        """Hiện popup lỗi rõ ràng; nếu thiếu Tesseract thì mời mở trang cài."""
        text = (payload or "").strip()
        first = text.splitlines()[0] if text else "Lỗi không rõ"
        url = "https://github.com/UB-Mannheim/tesseract/wiki"
        if "tesseract" in text.lower():
            if platform.system() == "Windows":
                ok = messagebox.askyesno(
                    "Thiếu Tesseract-OCR",
                    f"{first}\n\nỨng dụng cần Tesseract-OCR để nhận diện chữ. "
                    "Bản cài đặt lẽ ra đã kèm sẵn — nếu vẫn báo thiếu, bạn có thể "
                    "tự cài.\n\nMở trang tải Tesseract bây giờ?\n\n"
                    f"(Nhật ký: {self.log_path})")
                if ok:
                    try:
                        webbrowser.open(url)
                    except Exception:
                        pass
            else:
                messagebox.showerror(
                    "Thiếu Tesseract-OCR",
                    f"{first}\n\nmacOS: chạy 'brew install tesseract tesseract-lang'.\n"
                    f"(Nhật ký: {self.log_path})")
        else:
            messagebox.showerror(
                "Không chạy được tiến trình",
                f"{first}\n\nXem chi tiết trong nhật ký:\n{self.log_path}")

    def _on_file_event(self, i, ev, data):
        # i là chỉ số trong lượt chạy -> ánh xạ về chỉ số dòng/file thực tế
        idx = self._run_map[i] if i < len(self._run_map) else i
        if idx >= len(self.rows):
            return
        row = self.rows[idx]
        if ev == "start":
            self.active_index = idx
            self.file_t0[idx] = time.time()
            row.set_processing(0.0, 0.0)
        elif ev == "progress":
            el = time.time() - self.file_t0.get(idx, time.time())
            row.set_processing(float(data), el)
        elif ev == "cancelled":
            for k in self._run_map[i:]:
                self.rows[k].set_stopped()
            self.active_index = None
        elif ev in ("done", "error"):
            el = time.time() - self.file_t0.get(idx, time.time())
            self.file_elapsed[idx] = el
            if self.active_index == idx:
                self.active_index = None
            if ev == "error":
                self.failed.add(idx)
                row.set_error(el)
            else:
                self.failed.discard(idx)
                warn = bool(data.get("warnings") or data.get("conflicts")
                            or any(not k for _d, k, _ in (data.get("checks") or [])))
                row.set_done(el, warn=warn)

    def _finish(self, results):
        ok = sum(1 for r in results if r.get("out_path"))
        cancelled = self._cancel.is_set()
        total_t = (time.time() - self.t0 - self.paused_total) if self.t0 else 0
        self._logln("─" * 52, "muted")
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

        if cancelled:
            self._logln(f"⏹ Đã dừng. Hoàn tất {ok}/{len(self.files)} file "
                        f"trong {_fmt_time(total_t)}. Lưu tại: {self.out_dir.get()}", "warn")
            self.status_lbl.config(text=f"Đã dừng · {ok}/{len(self.files)} · "
                                   f"{_fmt_time(total_t)}", fg=C["warn"])
            self.header.set_caption("ĐÃ DỪNG")
        else:
            self._logln(f"Hoàn tất {ok}/{len(results)} file trong {_fmt_time(total_t)} "
                        f"(tổng {total_t:.1f}s). Lưu tại: {self.out_dir.get()}", "ok")
            self.status_lbl.config(text=f"Xong {ok}/{len(results)} · {_fmt_time(total_t)}",
                                   fg=C["ok"])
            self.header.set_caption("HOÀN TẤT")
        if ok > 0:
            try:
                self._open_folder(self.out_dir.get())
            except Exception:
                pass
        self._reset()

    @staticmethod
    def _open_folder(path):
        import subprocess
        import platform
        if platform.system() == "Windows":
            os.startfile(path)          # noqa
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def _reset(self):
        self.running = False
        self.paused = False
        self._resume.set()
        self.header.capy_stop()             # dừng & ẩn capybara khi xong/huỷ
        self.convert_btn.set_text("CHUYỂN ĐỔI  ▶")
        self._sync_convert_btn()            # chỉ sáng nếu còn file
        self.btn_add.set_enabled(True)
        self.btn_folder.set_enabled(True)
        self.btn_clear.set_enabled(True)
        self.btn_theme.set_enabled(True)
        self.btn_refresh.set_enabled(True)
        self.btn_pause.set_enabled(False)
        self.btn_pause.set_text(LBL_PAUSE)
        self.btn_stop.set_enabled(False)
        self.btn_retry.set_enabled(bool(self.failed))
        self.btn_retry.set_text(f"{LBL_RETRY} ({len(self.failed)})"
                                if self.failed else LBL_RETRY)
        for r in self.rows:                 # mở lại thao tác xoá
            r.set_deletable(True)
        self._on_row_select()


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
