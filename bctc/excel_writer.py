# -*- coding: utf-8 -*-
"""Xuất kết quả ra file Excel: mỗi báo cáo = 1 sheet."""
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

from . import templates as T

HEADERS = {
    "CDKT":   ("Mã số", "Số cuối năm", "Số đầu năm"),
    "KQHDKD": ("Mã số", "Năm nay", "Năm trước"),
    "LCTT":   ("Mã số", "Năm nay", "Năm trước"),
}
SHEET_NAMES = {
    "CDKT": "Bảng cân đối kế toán",
    "KQHDKD": "Kết quả HĐKD",
    "LCTT": "Lưu chuyển tiền tệ",
}

THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
HEAD_FILL = PatternFill("solid", fgColor="1F4E78")
TOTAL_FILL = PatternFill("solid", fgColor="DDEBF7")
SECTION_FILL = PatternFill("solid", fgColor="F2F2F2")
FLAG_FILL = PatternFill("solid", fgColor="FFE08A")   # ô nghi ngờ -> tô cam nhạt
NUMFMT = '#,##0;(#,##0)'

# Nhãn cột trong danh sách conflicts -> số cột Excel
_CONFLICT_COL = {"cuối năm/năm nay": 3, "đầu năm/năm trước": 4}


def pick_lctt_template(values):
    gt = T.codes_of(T.LUU_CHUYEN_TIEN_TE_GT)
    tt = T.codes_of(T.LUU_CHUYEN_TIEN_TE_TT)
    have = set(values)
    return T.LUU_CHUYEN_TIEN_TE_TT if len(have & tt) > len(have & gt) else T.LUU_CHUYEN_TIEN_TE_GT


def _write_sheet(ws, stmt_key, title_full, values, flags=frozenset()):
    if stmt_key == "LCTT":
        template = pick_lctt_template(values)
    else:
        template = T.STATEMENTS[stmt_key][1]
    h_code, h_cur, h_prior = HEADERS[stmt_key]

    # ---- tiêu đề ----
    ws.merge_cells("A1:D1")
    ws["A1"] = title_full.upper()
    ws["A1"].font = Font(bold=True, size=13, color="1F4E78")
    ws["A1"].alignment = Alignment(horizontal="center")
    ws.merge_cells("A2:D2")
    ws["A2"] = "Đơn vị tính: VND"
    ws["A2"].font = Font(italic=True, size=9)
    ws["A2"].alignment = Alignment(horizontal="right")

    # ---- hàng tiêu đề cột ----
    hr = 4
    cols = ["Chỉ tiêu", h_code, h_cur, h_prior]
    for j, c in enumerate(cols, start=1):
        cell = ws.cell(row=hr, column=j, value=c)
        cell.font = Font(bold=True, color="FFFFFF", size=10)
        cell.fill = HEAD_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = BORDER

    # ---- dữ liệu ----
    r = hr + 1
    for code, label, level, kind in template:
        cur = prior = None
        if code in values:
            cur, prior = values[code]
        c_label = ws.cell(row=r, column=1, value=("    " * level) + label)
        c_code = ws.cell(row=r, column=2, value=code if code else "")
        c_cur = ws.cell(row=r, column=3, value=cur)
        c_prior = ws.cell(row=r, column=4, value=prior)

        for cc in (c_label, c_code, c_cur, c_prior):
            cc.border = BORDER
        c_code.alignment = Alignment(horizontal="center")
        c_cur.number_format = NUMFMT
        c_prior.number_format = NUMFMT
        c_cur.alignment = c_prior.alignment = Alignment(horizontal="right")

        bold = kind in ("header", "section", "total")
        if bold:
            f = Font(bold=True)
            for cc in (c_label, c_code, c_cur, c_prior):
                cc.font = f
        if kind in ("header", "section"):
            for cc in (c_label, c_code, c_cur, c_prior):
                cc.fill = SECTION_FILL
        elif kind == "total":
            for cc in (c_label, c_code, c_cur, c_prior):
                cc.fill = TOTAL_FILL
        # tô cam ô "nghi ngờ" (hai lần OCR đọc lệch) — ưu tiên hơn fill nền
        if (code, 3) in flags:
            c_cur.fill = FLAG_FILL
        if (code, 4) in flags:
            c_prior.fill = FLAG_FILL
        r += 1

    # ---- định dạng cột ----
    ws.column_dimensions["A"].width = 58
    ws.column_dimensions["B"].width = 8
    ws.column_dimensions["C"].width = 20
    ws.column_dimensions["D"].width = 20
    ws.freeze_panes = "A5"
    ws.sheet_view.showGridLines = False


def _flags_by_key(conflicts):
    """[(key, code, label, v1, v2)] -> {key: {(code, colno)}}"""
    out = {}
    for key, code, label, _v1, _v2 in (conflicts or []):
        colno = _CONFLICT_COL.get(label)
        if colno:
            out.setdefault(key, set()).add((code, colno))
    return out


def build_workbook(company_name, results, conflicts=None):
    flags = _flags_by_key(conflicts)
    wb = Workbook()
    wb.remove(wb.active)
    for key in ("CDKT", "KQHDKD", "LCTT"):
        ws = wb.create_sheet(title=SHEET_NAMES[key])
        _write_sheet(ws, key, T.STATEMENTS[key][0], results.get(key, {}),
                     flags.get(key, frozenset()))
    return wb


def save(company_name, results, out_path, conflicts=None):
    wb = build_workbook(company_name, results, conflicts)
    wb.save(out_path)
    return out_path
