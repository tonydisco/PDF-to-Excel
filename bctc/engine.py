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

MAX_FILES = 150


class Cancelled(Exception):
    """Người dùng yêu cầu dừng giữa chừng."""


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


def convert_pdf(pdf_path, out_dir, lang="vie", dpis=(180, 235), log=lambda *_: None,
                file_progress=lambda frac: None, cancel=lambda: False):
    name = os.path.splitext(os.path.basename(pdf_path))[0]
    log(f"▶ {name}")
    if cancel():
        raise Cancelled()
    file_progress(0.03)
    doc = fitz.open(pdf_path)

    # mỗi lượt đọc (1 độ phân giải) là một mốc tiến độ -> lấp dần 0.05 → 0.93
    def _on_pass(done, total):
        if cancel():
            raise Cancelled()
        file_progress(0.05 + 0.88 * done / max(1, total))

    results, warnings, _, conflicts = parser.extract_consensus(
        doc, lang=lang, dpis=dpis, log=log, on_pass=_on_pass)
    doc.close()
    file_progress(0.95)

    out_path = os.path.join(out_dir, name + ".xlsx")
    excel_writer.save(name, results, out_path, conflicts=conflicts)
    file_progress(1.0)

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
                 log=lambda *_: None, progress=lambda done, total: None,
                 on_file=lambda index, event, data: None,
                 cancel=lambda: False, pause_wait=lambda: None):
    """
    on_file(index, event, data) báo trạng thái từng file cho giao diện:
        event="start"     data=None
        event="progress"  data=frac (0..1)
        event="done"      data=result dict
        event="error"     data=thông báo lỗi
        event="cancelled" data=None   (file này và các file sau bị dừng)

    cancel()      -> True nếu người dùng yêu cầu DỪNG HẲN.
    pause_wait()  -> chặn luồng khi đang TẠM DỪNG (trả về khi tiếp tục/dừng).
    """
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
        pause_wait()                 # chặn nếu đang tạm dừng
        if cancel():                 # dừng hẳn trước khi sang file mới
            on_file(i, "cancelled", None)
            log("⏹ Đã dừng theo yêu cầu.")
            break
        on_file(i, "start", None)
        try:
            r = convert_pdf(p, out_dir, lang=lang, dpis=dpis, log=log,
                            file_progress=lambda frac, i=i: on_file(i, "progress", frac),
                            cancel=cancel)
            on_file(i, "done", r)
            out.append(r)
        except Cancelled:
            on_file(i, "cancelled", None)
            log("⏹ Đã dừng theo yêu cầu.")
            break
        except Exception as e:
            log(f"   ✖ Lỗi: {e}")
            r = {"pdf": p, "name": os.path.basename(p),
                 "error": str(e), "out_path": None}
            on_file(i, "error", str(e))
            out.append(r)
        progress(i + 1, total)
    return out
