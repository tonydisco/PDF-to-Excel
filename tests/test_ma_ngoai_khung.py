# -*- coding: utf-8 -*-
"""
V6 việc #1 — §7.6/G2: mã parser bóc được nhưng KHÔNG khớp khung template phải
HIỆN RA (mục 'MÃ NGOÀI KHUNG' cuối sheet) + sinh cảnh báo, thay vì biến mất âm
thầm khi excel_writer chỉ duyệt các dòng có trong template.
"""
from bctc import excel_writer


def _texts(ws):
    return [str(c.value) for row in ws.iter_rows()
            for c in row if c.value is not None]


def _values(ws):
    return [c.value for row in ws.iter_rows() for c in row]


def test_ma_ngoai_khung_hien_ra_trong_sheet():
    # '999' không có trong khung CĐKT (Thông tư 200) -> phải hiện ra cùng số.
    results = {"CDKT": {"100": (10, 20), "999": (33, 44)}}
    wb = excel_writer.build_workbook("Cty X", results)
    ws = wb["Bảng cân đối kế toán"]
    texts = _texts(ws)
    assert "999" in texts, "mã ngoài khung '999' bị bỏ khỏi sheet (mất âm thầm)"
    assert any("MÃ NGOÀI KHUNG" in t for t in texts), \
        "thiếu mục tiêu đề 'MÃ NGOÀI KHUNG'"
    vals = _values(ws)
    assert 33 in vals and 44 in vals, "giá trị của mã ngoài khung bị bỏ"


def test_ma_ngoai_khung_sinh_canh_bao():
    results = {"CDKT": {"100": (10, 20), "999": (33, 44)}}
    warns = excel_writer.out_of_framework_warnings(results)
    assert len(warns) == 1
    assert "999" in warns[0]
    assert "NGOÀI KHUNG" in warns[0]


def test_khong_co_ma_ngoai_khung_thi_khong_canh_bao_khong_them_muc():
    # Mọi mã đều trong khung -> không cảnh báo, không mục thừa.
    results = {"CDKT": {"100": (10, 20), "270": (1, 2)}}
    assert excel_writer.out_of_framework_warnings(results) == []
    wb = excel_writer.build_workbook("Cty X", results)
    ws = wb["Bảng cân đối kế toán"]
    assert not any("NGOÀI KHUNG" in t for t in _texts(ws))


def test_extra_codes_giu_thu_tu_va_loc_dung():
    results = {"KQHDKD": {"01": (1, 2), "888": (3, 4), "10": (5, 6),
                          "777": (7, 8)}}
    assert excel_writer.extra_codes("KQHDKD", results["KQHDKD"]) == ["888", "777"]


def test_out_of_framework_nhieu_bao_cao():
    results = {"CDKT": {"999": (1, 2)}, "KQHDKD": {"01": (3, 4)}}
    warns = excel_writer.out_of_framework_warnings(results)
    assert len(warns) == 1                     # chỉ CĐKT có mã ngoài khung
    assert "cân đối" in warns[0].lower()
