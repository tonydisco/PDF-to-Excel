# -*- coding: utf-8 -*-
"""Điều phối: PDF scan -> OCR -> bóc tách -> Excel, kèm kiểm tra cân đối."""
import os
# Mỗi tiến trình tesseract chạy 1 luồng -> để ThreadPool song song hoá theo TRANG
# (nhanh hơn nhiều so với để 1 tesseract tự đa luồng rồi xử lý tuần tự).
os.environ.setdefault("OMP_THREAD_LIMIT", "1")
import fitz

from . import ocr
from . import parser
from . import excel_writer

MAX_FILES = 10


def _check_balance(cdkt):
    """Trả về danh sách (mô tả, đạt?) kiểm tra tính cân đối của BCĐKT."""
    out = []

    def g(code, idx):
        v = cdkt.get(code)
        return v[idx] if v and v[idx] is not None else None

    for idx, label in ((0, "cuối năm"), (1, "đầu năm")):
        ts, nv = g("270", idx), g("440", idx)
        if ts is not None and nv is not None:
            out.append((f"Tổng tài sản = Tổng nguồn vốn ({label})", ts == nv,
                        f"{ts:,} vs {nv:,}"))
        a, b, tot = g("100", idx), g("200", idx), g("270", idx)
        if None not in (a, b, tot):
            out.append((f"100 + 200 = 270 ({label})", a + b == tot,
                        f"{a:,}+{b:,} vs {tot:,}"))
        c, d, tot2 = g("300", idx), g("400", idx), g("440", idx)
        if None not in (c, d, tot2):
            out.append((f"300 + 400 = 440 ({label})", c + d == tot2,
                        f"{c:,}+{d:,} vs {tot2:,}"))
    return out


def convert_pdf(pdf_path, out_dir, lang="vie", dpis=(180, 235), log=lambda *_: None):
    name = os.path.splitext(os.path.basename(pdf_path))[0]
    log(f"▶ {name}")
    doc = fitz.open(pdf_path)
    results, warnings, _, conflicts = parser.extract_consensus(
        doc, lang=lang, dpis=dpis, log=log)
    doc.close()

    out_path = os.path.join(out_dir, name + ".xlsx")
    excel_writer.save(name, results, out_path, conflicts=conflicts)

    n_rows = {k: len(v) for k, v in results.items()}
    checks = _check_balance(results.get("CDKT", {}))
    log(f"   ✔ Đã lưu: {os.path.basename(out_path)}  "
        f"(CĐKT {n_rows['CDKT']} dòng, KQ {n_rows['KQHDKD']}, LC {n_rows['LCTT']})")
    return {
        "pdf": pdf_path, "name": name, "out_path": out_path,
        "rows": n_rows, "warnings": warnings, "checks": checks,
        "conflicts": conflicts,
    }


def convert_many(pdf_paths, out_dir, lang="vie", dpis=(180, 235),
                 log=lambda *_: None, progress=lambda done, total: None):
    if len(pdf_paths) > MAX_FILES:
        raise ValueError(f"Tối đa {MAX_FILES} file mỗi lần (đang chọn {len(pdf_paths)}).")
    ocr.configure_tesseract()
    if not ocr.has_vietnamese():
        raise ocr.TesseractNotFound(
            "Tesseract chưa có gói tiếng Việt (vie).\n"
            "- Windows: copy 'vie.traineddata' vào thư mục tessdata.\n"
            "- macOS:   chạy 'brew install tesseract-lang'."
        )
    os.makedirs(out_dir, exist_ok=True)
    out = []
    total = len(pdf_paths)
    for i, p in enumerate(pdf_paths):
        try:
            out.append(convert_pdf(p, out_dir, lang=lang, dpis=dpis, log=log))
        except Exception as e:
            log(f"   ✖ Lỗi: {e}")
            out.append({"pdf": p, "name": os.path.basename(p),
                        "error": str(e), "out_path": None})
        progress(i + 1, total)
    return out
