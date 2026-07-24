# -*- coding: utf-8 -*-
"""Điều phối: PDF scan -> OCR -> bóc tách -> Excel, kèm kiểm tra cân đối."""
import os
import traceback
# Mỗi tiến trình tesseract chạy 1 luồng -> để ThreadPool song song hoá theo TRANG
# (nhanh hơn nhiều so với để 1 tesseract tự đa luồng rồi xử lý tuần tự).
os.environ.setdefault("OMP_THREAD_LIMIT", "1")
import fitz

from . import ocr
from . import parser
from . import excel_writer
from . import workers as W
from . import dedup

MAX_FILES = 150


class Cancelled(Exception):
    """Người dùng yêu cầu dừng giữa chừng."""


class LoiFileKhongHopLe(Exception):
    """File đầu vào không phải PDF hợp lệ (rỗng / hỏng / mã hoá / sai định dạng).
    Ném ra để convert_many báo lỗi TỬ TẾ theo từng file và chạy tiếp cả mẻ,
    thay vì để fitz ném traceback thô làm chết mẻ."""


def _kiem_tra_pdf(pdf_path):
    """§7.9: chặn file hỏng TRƯỚC khi mở. Dò MAGIC BYTES (không suy loại file
    từ đuôi — '.PDF' hoa, 'BCTC.jpeg.jpeg'): 0 byte / không có chữ ký '%PDF' /
    không đọc được -> LoiFileKhongHopLe kèm thông báo tiếng Việt rõ ràng."""
    try:
        size = os.path.getsize(pdf_path)
    except OSError:
        raise LoiFileKhongHopLe(
            "Không đọc được file (không tồn tại hoặc không có quyền đọc).")
    if size == 0:
        raise LoiFileKhongHopLe("File rỗng (0 byte) — không phải PDF.")
    try:
        with open(pdf_path, "rb") as fh:
            head = fh.read(1024)
    except OSError:
        raise LoiFileKhongHopLe("Không đọc được nội dung file.")
    if b"%PDF" not in head:
        raise LoiFileKhongHopLe(
            "File không phải PDF hợp lệ (không thấy chữ ký '%PDF' ở đầu file).")


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
                file_progress=lambda frac: None, cancel=lambda: False,
                mode=W.MODE_BALANCED):
    name = os.path.splitext(os.path.basename(pdf_path))[0]
    log(f"▶ {name}")
    if cancel():
        raise Cancelled()
    _kiem_tra_pdf(pdf_path)          # §7.9: chặn file rỗng/hỏng với thông báo rõ
    file_progress(0.03)
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise LoiFileKhongHopLe("Không mở được PDF (file có thể bị hỏng): %s" % e)
    if doc.needs_pass:
        doc.close()
        raise LoiFileKhongHopLe(
            "File PDF được mã hoá (cần mật khẩu) — không đọc được nội dung.")

    # mỗi lượt đọc (1 độ phân giải) là một mốc tiến độ -> lấp dần 0.05 → 0.93
    def _on_pass(done, total):
        if cancel():
            raise Cancelled()
        file_progress(0.05 + 0.88 * done / max(1, total))

    results, warnings, meta, conflicts = parser.extract_consensus(
        doc, lang=lang, dpis=dpis, log=log, on_pass=_on_pass,
        workers=W.worker_count(mode))
    doc.close()
    file_progress(0.95)

    # §7.3: đơn vị tính phát hiện được -> ghi vào A2 (parser đã tự cảnh báo khi
    # khác VND). §7.6/G2: mã ngoài khung -> thêm cảnh báo (excel_writer cũng
    # ghi ra sheet) để KHÔNG mất dữ liệu âm thầm.
    unit = (meta or {}).get("unit")
    warnings = list(warnings) + excel_writer.out_of_framework_warnings(results)

    out_path = os.path.join(out_dir, name + ".xlsx")
    excel_writer.save(name, results, out_path, conflicts=conflicts, unit=unit)
    file_progress(1.0)

    n_rows = {k: len(v) for k, v in results.items()}
    checks = _check_balance(results.get("CDKT", {}))
    log(f"   ✔ Đã lưu: {os.path.basename(out_path)}  "
        f"(CĐKT {n_rows['CDKT']} dòng, KQ {n_rows['KQHDKD']}, LC {n_rows['LCTT']})")
    return {
        "pdf": pdf_path, "name": name, "out_path": out_path,
        "rows": n_rows, "warnings": warnings, "checks": checks,
        "conflicts": conflicts,
        "unit": unit,                # <-- V8 §D: bản sao phải ghi ĐÚNG đơn vị
        "results": results,          # <-- THÊM: phục vụ bộ đo hồi quy
    }


def _luu_ban_sao(pdf_path, out_dir, ket_qua_goc, log):
    """Ghi lại kết quả của file gốc dưới tên của file trùng nội dung.

    V8 §D: phải chuyền cả `unit`. Thiếu nó thì file trùng nội dung của một báo
    cáo 'triệu đồng' bị ghi 'Đơn vị tính: VND' — sai đơn vị 10^6 một cách âm
    thầm, lại còn MÂU THUẪN với cảnh báo đơn vị vốn được chép sang."""
    name = os.path.splitext(os.path.basename(pdf_path))[0]
    out_path = os.path.join(out_dir, name + ".xlsx")
    excel_writer.save(name, ket_qua_goc["results"], out_path,
                      conflicts=ket_qua_goc.get("conflicts"),
                      unit=ket_qua_goc.get("unit"))
    log("↩ %s — trùng nội dung với %s, dùng lại kết quả."
        % (name, ket_qua_goc["name"]))
    r = dict(ket_qua_goc)
    r.update({"pdf": pdf_path, "name": name, "out_path": out_path,
              "trung_voi": ket_qua_goc["name"]})
    return r


def convert_many(pdf_paths, out_dir, lang="vie", dpis=(180, 235),
                 log=lambda *_: None, progress=lambda done, total: None,
                 on_file=lambda index, event, data: None,
                 cancel=lambda: False, pause_wait=lambda: None,
                 mode=W.MODE_BALANCED):
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

    # File trùng nội dung chỉ xử lý một lần rồi chép kết quả sang tên còn lại.
    _, ban_sao = dedup.group_duplicates(pdf_paths)
    ket_qua_theo_file = {}
    if ban_sao:
        log("↩ Phát hiện %d file trùng nội dung — sẽ dùng lại kết quả."
            % len(ban_sao))

    for i, p in enumerate(pdf_paths):
        pause_wait()                 # chặn nếu đang tạm dừng
        if cancel():                 # dừng hẳn trước khi sang file mới
            on_file(i, "cancelled", None)
            log("⏹ Đã dừng theo yêu cầu.")
            break
        on_file(i, "start", None)
        try:
            goc = ban_sao.get(p)
            if goc is not None and goc in ket_qua_theo_file:
                r = _luu_ban_sao(p, out_dir, ket_qua_theo_file[goc], log)
            else:
                r = convert_pdf(p, out_dir, lang=lang, dpis=dpis, log=log,
                                file_progress=lambda frac, i=i: on_file(i, "progress", frac),
                                cancel=cancel, mode=mode)
                ket_qua_theo_file[p] = r
            on_file(i, "done", r)
            out.append(r)
        except Cancelled:
            on_file(i, "cancelled", None)
            log("⏹ Đã dừng theo yêu cầu.")
            break
        except LoiFileKhongHopLe as e:
            # Lỗi ĐÃ BIẾT (file rỗng/hỏng/mã hoá): thông báo tử tế, KHÔNG dump
            # traceback, và chạy tiếp cả mẻ.
            log(f"   ✖ {e}")
            r = {"pdf": p, "name": os.path.basename(p),
                 "error": str(e), "out_path": None}
            on_file(i, "error", str(e))
            out.append(r)
        except Exception as e:
            log(f"   ✖ Lỗi: {e}")
            log("   ⋯ chi tiết:\n   " + traceback.format_exc().replace("\n", "\n   "))
            r = {"pdf": p, "name": os.path.basename(p),
                 "error": str(e), "out_path": None}
            on_file(i, "error", str(e))
            out.append(r)
        progress(i + 1, total)
    return out
