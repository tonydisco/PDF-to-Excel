# -*- coding: utf-8 -*-
import os

from bctc import dedup


def _viet(tmp_path, ten, noi_dung):
    p = tmp_path / ten
    p.write_bytes(noi_dung)
    return str(p)


def test_file_digest_giong_nhau_cho_noi_dung_giong_nhau(tmp_path):
    a = _viet(tmp_path, "a.pdf", b"X" * 5000)
    b = _viet(tmp_path, "b.pdf", b"X" * 5000)
    assert dedup.file_digest(a) == dedup.file_digest(b)


def test_file_digest_khac_nhau_cho_noi_dung_khac_nhau(tmp_path):
    a = _viet(tmp_path, "a.pdf", b"X" * 5000)
    c = _viet(tmp_path, "c.pdf", b"Y" * 5000)
    assert dedup.file_digest(a) != dedup.file_digest(c)


def test_group_duplicates_gom_dung_nhom(tmp_path):
    a = _viet(tmp_path, "a.pdf", b"X" * 5000)
    b = _viet(tmp_path, "b.pdf", b"X" * 5000)
    c = _viet(tmp_path, "c.pdf", b"Y" * 5000)
    dai_dien, ban_sao = dedup.group_duplicates([a, b, c])
    assert len(dai_dien) == 2                 # 2 nội dung riêng biệt
    assert ban_sao == {b: a}                  # b là bản sao của a
    assert a not in ban_sao and c not in ban_sao


def test_group_duplicates_giu_thu_tu_file_dau_lam_dai_dien(tmp_path):
    a = _viet(tmp_path, "a.pdf", b"Z" * 100)
    b = _viet(tmp_path, "b.pdf", b"Z" * 100)
    _, ban_sao = dedup.group_duplicates([a, b])
    assert ban_sao[b] == a


def test_file_rong_khong_gay_loi(tmp_path):
    e = _viet(tmp_path, "rong.pdf", b"")
    dai_dien, ban_sao = dedup.group_duplicates([e])
    assert len(dai_dien) == 1


def test_convert_many_khong_xu_ly_lai_file_trung(tmp_path, monkeypatch):
    """File trùng nội dung phải dùng lại kết quả, không gọi convert_pdf lần hai."""
    from bctc import engine

    a = _viet(tmp_path, "a.pdf", b"PDFGIA" * 500)
    b = _viet(tmp_path, "b.pdf", b"PDFGIA" * 500)
    out_dir = str(tmp_path / "out")

    goi = []

    def fake_convert_pdf(pdf_path, od, **kw):
        goi.append(pdf_path)
        return {"pdf": pdf_path, "name": os.path.basename(pdf_path),
                "out_path": os.path.join(od, "x.xlsx"),
                "rows": {}, "warnings": [], "checks": [], "conflicts": [],
                "results": {"CDKT": {}, "KQHDKD": {}, "LCTT": {}}}

    monkeypatch.setattr(engine, "convert_pdf", fake_convert_pdf)
    monkeypatch.setattr(engine.ocr, "configure_tesseract", lambda: ("x", "y"))
    monkeypatch.setattr(engine.ocr, "has_vietnamese", lambda: True)

    res = engine.convert_many([a, b], out_dir)

    assert len(goi) == 1, "convert_pdf phải chạy 1 lần, đang chạy %d lần" % len(goi)
    assert len(res) == 2, "vẫn phải trả kết quả cho cả 2 file"
    assert res[1].get("trung_voi") == os.path.basename(a)


# ======================================================================
# V8 §D — file TRÙNG nội dung phải ghi ĐÚNG đơn vị tính
#
# Trước khi sửa: _luu_ban_sao gọi excel_writer.save(...) mà KHÔNG truyền unit
# -> workbook của bản sao ghi 'Đơn vị tính: VND' dù bản gốc là 'triệu đồng'
# (sai 10^6, âm thầm, lại mâu thuẫn với cảnh báo đơn vị VỐN ĐƯỢC chép sang).
# Test cũ ở trên không phát hiện được vì nó giả lập convert_pdf và KHÔNG BAO
# GIỜ MỞ workbook — nên test này mở file .xlsx thật và đọc ô A2.
# ======================================================================
def _mo_a2(path, sheet="Bảng cân đối kế toán"):
    from openpyxl import load_workbook
    wb = load_workbook(path)
    try:
        return wb[sheet]["A2"].value
    finally:
        wb.close()


def _chay_hai_file_trung(tmp_path, monkeypatch, unit):
    """Chạy convert_many trên 2 file trùng nội dung; bản gốc có `unit`."""
    from bctc import engine, excel_writer

    a = _viet(tmp_path, "a.pdf", b"PDFGIA" * 500)
    b = _viet(tmp_path, "b.pdf", b"PDFGIA" * 500)
    out_dir = str(tmp_path / "out")
    ket_qua = {"CDKT": {"100": (1111, 2222)}, "KQHDKD": {}, "LCTT": {}}

    def fake_convert_pdf(pdf_path, od, **kw):
        name = os.path.splitext(os.path.basename(pdf_path))[0]
        out_path = os.path.join(od, name + ".xlsx")
        # giả lập ĐÚNG như convert_pdf thật: ghi workbook kèm unit rồi trả dict
        excel_writer.save(name, ket_qua, out_path, unit=unit)
        return {"pdf": pdf_path, "name": name, "out_path": out_path,
                "rows": {}, "warnings": [], "checks": [], "conflicts": [],
                "unit": unit, "results": ket_qua}

    monkeypatch.setattr(engine, "convert_pdf", fake_convert_pdf)
    monkeypatch.setattr(engine.ocr, "configure_tesseract", lambda: ("x", "y"))
    monkeypatch.setattr(engine.ocr, "has_vietnamese", lambda: True)
    return engine.convert_many([a, b], out_dir)


def test_ban_sao_ghi_dung_don_vi_trieu_dong(tmp_path, monkeypatch):
    res = _chay_hai_file_trung(tmp_path, monkeypatch, "triệu đồng")
    assert res[1].get("trung_voi") == "a"
    assert _mo_a2(res[0]["out_path"]) == "Đơn vị tính: triệu đồng"
    assert _mo_a2(res[1]["out_path"]) == "Đơn vị tính: triệu đồng", \
        "bản sao phải ghi ĐÚNG đơn vị của bản gốc, không mặc định VND"


def test_ban_sao_ghi_vnd_khi_goc_la_vnd(tmp_path, monkeypatch):
    res = _chay_hai_file_trung(tmp_path, monkeypatch, None)
    assert _mo_a2(res[1]["out_path"]) == "Đơn vị tính: VND"


def test_convert_pdf_tra_ve_khoa_unit():
    """Hợp đồng: dict kết quả của convert_pdf phải mang 'unit' thì
    _luu_ban_sao mới có gì để chuyền."""
    import inspect
    from bctc import engine
    src = inspect.getsource(engine.convert_pdf)
    assert '"unit": unit' in src
