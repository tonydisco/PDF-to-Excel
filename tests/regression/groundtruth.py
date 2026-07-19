# -*- coding: utf-8 -*-
"""
Đọc file Excel "đáp án" (bản xuất trực tiếp từ phần mềm kế toán).

Ba cạm bẫy đã xác nhận trên corpus thật:
  1. Đuôi file nói dối: 'KQKD.XLS' thực chất là OOXML (bắt đầu bằng 'PK').
     openpyxl từ chối theo ĐUÔI FILE chứ không theo nội dung -> phải nạp qua
     BytesIO sau khi tự dò magic bytes.
  2. Nhãn chỉ tiêu là mojibake TCVN3 ('C«ng ty CP Du LÞch §¨k L¨k'). Không cần
     giải mã: ta chỉ dùng MÃ SỐ + CON SỐ.
  3. Hàng tiêu đề không ở vị trí cố định -> phải dò động.
"""
import io
import os
import re

MAGIC_OOXML = b"PK\x03\x04"
MAGIC_BIFF = b"\xd0\xcf\x11\xe0"

# Thứ tự quan trọng: 'can doi ke toan' phải xét TRƯỚC 'cdps/cdsps' vì
# 'CDSPS.XLS' cũng chứa 'cd'. Mỗi mẫu khớp trên tên file đã hạ chữ thường.
_KIND_PATTERNS = (
    ("CDPS", r"cdsps|cdps|can doi so phat sinh|can doi phat sinh"),
    ("CDKT", r"cdkt|can doi ke toan|bang can doi"),
    ("KQHDKD", r"kqkd|kqhdkd|ket qua"),
    ("LCTT", r"lctt|luu chuyen"),
)


def statement_kind(filename):
    """Suy ra loại báo cáo từ tên file. Trả về '' nếu không nhận ra."""
    name = os.path.basename(filename).lower()
    for kind, pat in _KIND_PATTERNS:
        if re.search(pat, name):
            return kind
    return ""


def sniff_format(path):
    """Dò định dạng thật theo magic bytes, KHÔNG tin đuôi file."""
    with open(path, "rb") as fh:
        head = fh.read(8)
    if head.startswith(MAGIC_OOXML):
        return "ooxml"
    if head.startswith(MAGIC_BIFF):
        return "biff"
    return "unknown"


def _rows_ooxml(path):
    import openpyxl
    with open(path, "rb") as fh:
        data = fh.read()
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    ws = wb[wb.sheetnames[0]]
    try:
        return [list(r) for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()


def _rows_biff(path):
    import xlrd
    book = xlrd.open_workbook(path)
    sh = book.sheet_by_index(0)
    return [[sh.cell_value(r, c) for c in range(sh.ncols)]
            for r in range(sh.nrows)]


def _read_rows(path):
    fmt = sniff_format(path)
    if fmt == "ooxml":
        return _rows_ooxml(path)
    if fmt == "biff":
        return _rows_biff(path)
    raise ValueError("Không nhận ra định dạng Excel: %s" % path)


def _to_int(v):
    """Chuyển ô Excel thành int. Trả về None nếu ô rỗng/không phải số."""
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(round(v))
    s = str(v).strip()
    if not s:
        return None
    neg = s.startswith("(") and s.endswith(")")
    digits = re.sub(r"[^\d\-]", "", s)
    if digits in ("", "-"):
        return None
    val = int(digits)
    return -abs(val) if neg else val


_CODE_CELL = re.compile(r"^\s*(\d{1,3}[abc]?)\s*$")


def _find_columns(rows):
    """
    Dò (cột mã số, cột năm nay, cột năm trước).

    Neo vào hàng đánh số thứ tự cột ('1','2','3','4','5') vì nhãn tiêu đề là
    mojibake nên không so khớp chữ được. Hàng đó nằm ngay dưới hàng tiêu đề và
    có ít nhất 4 ô là số nguyên nhỏ tăng dần bắt đầu từ 1.
    """
    for r, row in enumerate(rows[:25]):
        nums = [(c, _to_int(v)) for c, v in enumerate(row) if _to_int(v) is not None]
        seq = [(c, n) for c, n in nums if 1 <= n <= 9]
        if len(seq) >= 4 and [n for _, n in seq][:4] == [1, 2, 3, 4]:
            cols = [c for c, _ in seq]
            # cột 1 = Chỉ tiêu, 2 = Mã số, 3 = Thuyết minh, 4 = Năm nay, 5 = Năm trước
            code_col = cols[1]
            cur_col = cols[3]
            prior_col = cols[4] if len(cols) >= 5 else cols[3] + 1
            return r, code_col, cur_col, prior_col
    return None


def read_statement(path):
    """
    Trả về {ma_so: (nam_nay, nam_truoc)}.

    Mã số giữ nguyên dạng in trong file ('1' chứ không phải '01') — việc chuẩn
    hoá là trách nhiệm của bên so sánh.
    """
    rows = _read_rows(path)
    found = _find_columns(rows)
    if not found:
        raise ValueError("Không dò được hàng tiêu đề trong %s" % path)
    hdr_row, code_col, cur_col, prior_col = found

    out = {}
    for row in rows[hdr_row + 1:]:
        if code_col >= len(row):
            continue
        raw = row[code_col]
        code = None
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            code = str(int(round(raw)))
        else:
            m = _CODE_CELL.match(str(raw or ""))
            if m:
                code = m.group(1)
        if not code:
            continue
        cur = _to_int(row[cur_col]) if cur_col < len(row) else None
        prior = _to_int(row[prior_col]) if prior_col < len(row) else None
        out[code] = (cur, prior)
    return out
