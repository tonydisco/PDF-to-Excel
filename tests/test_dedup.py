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
