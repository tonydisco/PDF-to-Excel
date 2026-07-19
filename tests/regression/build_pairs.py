# -*- coding: utf-8 -*-
"""
Đề xuất cặp (PDF, Excel đáp án) để dựng bộ hồi quy.

QUY TẮC SỐNG CÒN: mã công ty CHỈ lấy từ tên THƯ MỤC tổ tiên khớp '^NN[._ -]'.
Lấy từ tên file sẽ ghép nhầm công ty — đã kiểm chứng: file
'1 Can doi ke toan 06 thang dau 2025.xlsx' nằm trong thư mục
'27_Cty CP SXKD Hàng XK Tân Bình 6Th_2025/' nhưng số '1' ở đầu tên file lại
nối nó với '01_CTCP DVTH Saigon 2025 (Riêng).pdf'.

Kết quả của module này là ĐỀ XUẤT. Người phải xác nhận rồi mới đóng băng vào
pairs.json — xem hướng dẫn ở cuối file.
"""
import os
import re
import glob
import json
import unicodedata

from . import groundtruth

_DIR_INDEX = re.compile(r"^(\d{1,2})[._\s-]")
_YEAR = re.compile(r"(20\d{2})")


def _strip_accents(s):
    s = s.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def company_index(path):
    """Mã công ty, lấy từ thư mục tổ tiên GẦN NHẤT có dạng 'NN_...'."""
    parts = os.path.dirname(path).split(os.sep)
    for d in reversed(parts):
        m = _DIR_INDEX.match(d)
        if m:
            return m.group(1).lstrip("0") or "0"
    return ""


def year(path):
    ys = _YEAR.findall(path)
    return ys[-1] if ys else ""


def period(path):
    t = _strip_accents(path)
    if re.search(r"6\s*th|06 thang|\b6t\b|_6t|ban nien", t):
        return "6T"
    for pat, name in ((r"quy\s*4|\bq4\b|\bqiv\b|quy iv\b", "Q4"),
                      (r"quy\s*3|\bq3\b|\bqiii\b|quy iii\b", "Q3"),
                      (r"quy\s*2|\bq2\b|\bqii\b|quy ii\b", "Q2"),
                      (r"quy\s*1|\bq1\b|\bqi\b|quy i\b", "Q1")):
        if re.search(pat, t):
            return name
    return "NAM"


def _pdf_company(path):
    """PDF có thể mang mã ở tên file (vd '33_Cty CP DL Dak Lak 2024.pdf')."""
    c = company_index(path)
    if c:
        return c
    m = _DIR_INDEX.match(os.path.basename(path))
    return (m.group(1).lstrip("0") or "0") if m else ""


def build(corpus_root):
    """Trả về danh sách cặp đề xuất, khớp cả (mã công ty, năm, kỳ)."""
    pdfs = {}
    excels = []
    for f in glob.glob(os.path.join(corpus_root, "**", "*"), recursive=True):
        if not os.path.isfile(f):
            continue
        low = f.lower()
        if low.endswith(".pdf"):
            c, y = _pdf_company(f), year(f)
            if c and y:
                pdfs.setdefault((c, y, period(f)), []).append(f)
        elif low.endswith((".xls", ".xlsx", ".xlsm")) and groundtruth.statement_kind(f):
            excels.append(f)

    out = []
    for x in excels:
        c, y, p = company_index(x), year(x), period(x)
        if not (c and y):
            continue
        cands = pdfs.get((c, y, p))
        if not cands:
            continue
        out.append({
            "pdf": min(cands, key=len),      # tên ngắn nhất = ít hậu tố nhất
            "excel": x,
            "kind": groundtruth.statement_kind(x),
            "company": c,
            "year": y,
            "period": p,
        })
    return sorted(out, key=lambda d: (d["company"], d["year"], d["kind"]))


def main():
    root = os.environ.get(
        "BCTC_CORPUS", "/Users/motmi/Documents/DAYS/Y-NHI/BTG/Documents")
    pairs = build(root)
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(here, "pairs.candidate.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"pairs": pairs}, fh, ensure_ascii=False, indent=2)
    print("Đã đề xuất %d cặp (%d PDF riêng biệt) -> %s"
          % (len(pairs), len({p["pdf"] for p in pairs}), out_path))
    print("\nNGƯỜI PHẢI XÁC NHẬN trước khi dùng:")
    print("  1. Mở pairs.candidate.json, đối chiếu từng cặp.")
    print("  2. Xoá cặp sai phạm vi (riêng vs hợp nhất) hoặc sai kỳ.")
    print("  3. Đổi tên thành pairs.json rồi commit.")
    for p in pairs:
        print("  CT%-3s %s %-4s %-7s %s  <-  %s"
              % (p["company"], p["year"], p["period"], p["kind"],
                 os.path.basename(p["excel"])[:30],
                 os.path.basename(p["pdf"])[:44]))


if __name__ == "__main__":
    main()
