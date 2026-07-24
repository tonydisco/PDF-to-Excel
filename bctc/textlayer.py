# -*- coding: utf-8 -*-
"""
Đọc lớp text sẵn có trong PDF, thay cho OCR — khi và chỉ khi lớp text đó
THẬT SỰ dùng được.

Khảo sát corpus (2.919 file):
  - 78,2% không có lớp text  -> phải OCR
  -  9,4% có lớp text MOJIBAKE -> phải OCR (nguy hiểm nhất)
  - 12,2% có lớp text dùng được -> đọc thẳng, chính xác tuyệt đối, gần như
    không tốn CPU

Mojibake là ca nguy hiểm: page.get_text() trả về hàng chục nghìn ký tự trông
như hợp lệ nhưng là rác ('BAD CAD TAl CHfNH RII~NG' thay vì 'BÁO CÁO TÀI
CHÍNH RIÊNG'). Nguyên nhân: bảng mã VNI/TCVN3 khai báo nhầm thành WinAnsi,
do OCR sẵn của máy scan Canon. Đọc chúng mà không lọc sẽ cho ra dữ liệu sai
một cách âm thầm — tệ hơn hiện trạng.

Ba bộ lọc, phải qua HẾT mới được dùng lớp text.
"""
import re
import unicodedata

# Ngưỡng ký tự tối thiểu mỗi trang. Đây là bộ lọc quan trọng nhất trong thực
# tế: file 33_Cty CP DL Dak Lak 2024.pdf có 38 trang nhưng chỉ 352 ký tự (toàn
# bộ là lớp phủ chữ ký số) mà tỷ lệ dấu vẫn đạt 0,126 — chỉ ngưỡng ký tự mới
# chặn được nó.
MIN_CHARS_PER_PAGE = 200

# Tỷ lệ ký tự có dấu tiếng Việt tối thiểu. Đo thực tế trên corpus:
# file text tốt trung vị 0,270; file mojibake 0,000.
MIN_DIACRITIC_RATIO = 0.02

SIGNATURE_MARKERS = (
    "digitally signed",
    "signature not verified",
    "ký bởi",
    "ky boi",
)

# V4a: neo TIÊU ĐỀ báo cáo (đã bỏ dấu) — đồng bộ với parser.TITLES. Lớp text
# VNI/TCVN 8-bit lọt hai bộ lọc ký-tự + tỷ-lệ-dấu (glyph phân rã ra chữ Latin
# CÓ dấu nên tỷ lệ dấu vẫn > 0) nhưng KHÔNG normalize ra tiếng Việt thật, nên
# mọi tiêu đề đều vỡ ("Baûng caân ñoái" != "bang can doi"). Đòi ÍT NHẤT một
# tiêu đề đọc được thì mới TIN lớp text; không có -> ép OCR (OCR đọc glyph
# HIỂN THỊ đúng của các file này).
_TITLE_ANCHORS = (
    "bang can doi ke toan",
    "bao cao tinh hinh tai chinh",
    "ket qua hoat dong kinh doanh",
    "ket qua kinh doanh",
    "luu chuyen tien te",
)


def _bo_dau(s):
    """Bỏ dấu tiếng Việt + hạ chữ thường + gộp khoảng trắng (khớp parser.norm)."""
    s = s.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def has_report_title(text):
    """True nếu văn bản (sau bỏ dấu) chứa ÍT NHẤT một tiêu đề báo cáo."""
    n = _bo_dau(text)
    return any(a in n for a in _TITLE_ANCHORS)


def diacritic_ratio(text):
    """Tỷ lệ ký tự chữ cái mang dấu tiếng Việt trên tổng ký tự chữ cái."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    co_dau = 0
    for c in letters:
        d = unicodedata.normalize("NFD", c)
        if len(d) > 1 or c in "đĐ":
            co_dau += 1
    return co_dau / float(len(letters))


def strip_signature_text(text):
    """Bỏ các dòng thuộc lớp phủ chữ ký số trước khi đánh giá chất lượng."""
    out = []
    for line in text.splitlines():
        low = line.lower()
        if any(m in low for m in SIGNATURE_MARKERS):
            continue
        out.append(line)
    return "\n".join(out)


def is_usable(doc):
    """
    True nếu lớp text của tài liệu đủ tin cậy để dùng thay OCR.

    Đánh giá trên toàn tài liệu chứ không từng trang: BCTC có trang bìa và
    trang ký tên gần như trống, xét riêng lẻ sẽ trượt oan.
    """
    try:
        raw = "".join(doc[i].get_text() for i in range(doc.page_count))
    except Exception:
        return False
    text = strip_signature_text(raw)
    if len(text.strip()) < MIN_CHARS_PER_PAGE * max(1, doc.page_count) * 0.25:
        return False
    if diacritic_ratio(text) < MIN_DIACRITIC_RATIO:
        return False
    # V4a: bộ lọc THỨ TƯ — lớp text phải có ít nhất một TIÊU ĐỀ báo cáo đọc
    # được. Chặn họ mojibake VNI/TCVN qua được tỷ lệ dấu nhưng không định vị
    # nổi báo cáo nào (đo trên corpus: 100% file 0-tiêu-đề đều là mojibake).
    return has_report_title(text)


def page_lines(page):
    """
    Đọc một trang thành danh sách DÒNG, cùng cấu trúc mà ocr.ocr_lines() trả về
    (phần tử thứ 3), để parser dùng chung không phải rẽ nhánh.

    page.get_text("words") trả tuple 8 phần tử:
        (x0, y0, x1, y1, text, block_no, line_no, word_no)
    """
    rect = page.rect
    W = float(rect.width) or 1.0
    H = float(rect.height) or 1.0

    nhom = {}
    for x0, y0, x1, y1, txt, block_no, line_no, _word_no in page.get_text("words"):
        t = (txt or "").strip()
        if not t:
            continue
        w, h = x1 - x0, y1 - y0
        nhom.setdefault((block_no, line_no), []).append({
            "text": t,
            "left": x0, "top": y0, "width": w, "height": h,
            "conf": 100.0,                 # lớp text: coi như chắc chắn
            "cx": (x0 + w / 2.0) / W,
            "cy": (y0 + h / 2.0) / H,
            "right": x1 / W,
            "lx": x0 / W,
        })

    out = []
    for key in sorted(nhom, key=lambda k: min(wd["top"] for wd in nhom[k])):
        out.append(sorted(nhom[key], key=lambda wd: wd["left"]))
    return out
