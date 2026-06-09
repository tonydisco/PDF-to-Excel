# -*- coding: utf-8 -*-
"""
Lớp OCR: render trang PDF (ảnh scan) -> tiền xử lý -> Tesseract (tiếng Việt)
Trả về danh sách DÒNG, mỗi dòng gồm các từ kèm toạ độ (bounding box).
"""
import os
import sys
import shutil
import platform
import subprocess

# ----------------------------------------------------------------------
# Windows: chặn cửa sổ console NHẤP NHÁY khi gọi tesseract.exe.
# App đóng gói dạng cửa sổ (không console); mỗi lần chạy tesseract.exe
# (chương trình console) Windows sẽ bật 1 console chớp nhoáng -> trông như
# "2-3 app mở lên rồi tắt" lúc khởi động. Thêm cờ CREATE_NO_WINDOW cho mọi
# subprocess để ẩn hẳn các cửa sổ này.
if sys.platform == "win32":
    _CREATE_NO_WINDOW = 0x08000000
    _OrigPopen = subprocess.Popen

    class _SilentPopen(_OrigPopen):
        def __init__(self, *args, **kwargs):
            kwargs["creationflags"] = kwargs.get("creationflags", 0) | _CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)

    subprocess.Popen = _SilentPopen      # pytesseract dùng subprocess.Popen

import fitz                       # PyMuPDF
import pytesseract
from PIL import Image, ImageOps


# ----------------------------------------------------------------------
# 1. Định vị Tesseract + tessdata (vie) một cách "chống lỗi"
# ----------------------------------------------------------------------
def _bundle_dir():
    """Thư mục tài nguyên khi đã đóng gói bằng PyInstaller, hoặc thư mục mã nguồn."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def locate_tesseract():
    """
    Trả về (tesseract_path, tessdata_dir).
    Ưu tiên bản đi kèm app -> PATH hệ thống -> các vị trí cài đặt thông dụng.
    """
    base = _bundle_dir()
    system = platform.system()

    # (a) bản tesseract đóng gói kèm app (Windows portable)
    cand = []
    if system == "Windows":
        cand += [
            os.path.join(base, "tesseract", "tesseract.exe"),
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
    elif system == "Darwin":
        cand += [
            os.path.join(base, "tesseract", "bin", "tesseract"),
            "/opt/homebrew/bin/tesseract",   # Apple Silicon
            "/usr/local/bin/tesseract",      # Intel
        ]
    else:  # Linux
        cand += ["/usr/bin/tesseract", "/usr/local/bin/tesseract"]

    tess = next((p for p in cand if os.path.exists(p)), None)
    if tess is None:
        tess = shutil.which("tesseract")    # tìm trong PATH

    # tessdata: ưu tiên tessdata NẰM CẠNH tesseract (đủ eng/osd/vie nếu là bản
    # đóng gói kèm), sau đó tới bản vie đi kèm app, cuối cùng là biến môi trường.
    tessdata = None
    cand_td = []
    if tess:
        cand_td.append(os.path.join(os.path.dirname(tess), "tessdata"))
    cand_td.append(os.path.join(base, "tessdata"))
    for d in cand_td:
        if os.path.exists(os.path.join(d, "vie.traineddata")):
            tessdata = d
            break
    if tessdata is None and os.environ.get("TESSDATA_PREFIX"):
        tessdata = os.environ["TESSDATA_PREFIX"]

    return tess, tessdata


class TesseractNotFound(Exception):
    pass


def configure_tesseract():
    os.environ.setdefault("OMP_THREAD_LIMIT", "1")
    tess, tessdata = locate_tesseract()
    if not tess:
        raise TesseractNotFound(
            "Không tìm thấy Tesseract OCR.\n"
            "- Windows: cài tại https://github.com/UB-Mannheim/tesseract/wiki\n"
            "- macOS:   chạy 'brew install tesseract tesseract-lang'\n"
            "rồi mở lại ứng dụng."
        )
    pytesseract.pytesseract.tesseract_cmd = tess
    if tessdata:
        os.environ["TESSDATA_PREFIX"] = tessdata
    return tess, tessdata


def has_vietnamese():
    """Kiểm tra đã có gói ngôn ngữ tiếng Việt chưa."""
    try:
        return "vie" in pytesseract.get_languages(config="")
    except Exception:
        return False


# ----------------------------------------------------------------------
# 2. Render + tiền xử lý ảnh
# ----------------------------------------------------------------------
def render_page(doc, page_index, dpi=300):
    page = doc[page_index]
    pix = page.get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return img


def preprocess(img):
    """Chuyển xám + tăng tương phản nhẹ. Giữ ảnh sạch để OCR ổn định."""
    g = ImageOps.grayscale(img)
    g = ImageOps.autocontrast(g, cutoff=1)
    return g


# ----------------------------------------------------------------------
# 3. OCR một trang -> danh sách dòng kèm toạ độ
# ----------------------------------------------------------------------
def ocr_lines(img, lang="vie", psm=6, min_conf=25, whitelist=None):
    """
    Trả về:
        width, height, lines
    lines: list các dòng; mỗi dòng là list dict
           {text, left, top, width, height, conf, cx, cy, right, nh}
    Toạ độ chuẩn hoá theo chiều rộng ảnh để bộ parser dùng phân số (0..1).

    whitelist: nếu truyền (vd "0123456789.,()-"), giới hạn ký tự Tesseract đọc ->
    dùng cho PASS CHỈ-CHỮ-SỐ ở cột số (giảm nhầm 0/O, 1/l, mất dấu chấm nghìn).
    """
    config = f"--psm {psm}"
    if whitelist:
        config += f" -c tessedit_char_whitelist={whitelist}"
    data = pytesseract.image_to_data(
        img, lang=lang, config=config,
        output_type=pytesseract.Output.DICT,
    )
    W, H = img.size
    lines = {}
    n = len(data["text"])
    for i in range(n):
        txt = (data["text"][i] or "").strip()
        if not txt:
            continue
        conf = float(data["conf"][i]) if data["conf"][i] not in ("-1", -1) else -1
        if conf < min_conf:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        l, t = data["left"][i], data["top"][i]
        w, h = data["width"][i], data["height"][i]
        word = {
            "text": txt, "left": l, "top": t, "width": w, "height": h,
            "conf": conf, "cx": (l + w / 2) / W, "cy": (t + h / 2) / H,
            "right": (l + w) / W, "lx": l / W, "nh": h / H,
        }
        lines.setdefault(key, []).append(word)

    out = []
    for key in sorted(lines, key=lambda k: min(wd["top"] for wd in lines[k])):
        words = sorted(lines[key], key=lambda wd: wd["left"])
        out.append(words)
    return W, H, out


def lines_to_text(lines):
    return "\n".join(" ".join(wd["text"] for wd in ln) for ln in lines)
