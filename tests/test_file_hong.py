# -*- coding: utf-8 -*-
"""
V6 việc #4 — §7.9: chặn file rỗng/hỏng/không-phải-PDF với thông báo TIẾNG VIỆT
tử tế theo TỪNG file, không để traceback thô làm chết cả mẻ. Dò MAGIC BYTES
(không suy loại từ đuôi file).
"""
import pytest

from bctc import engine


def test_kiem_tra_pdf_0_byte(tmp_path):
    p = tmp_path / "rong.pdf"
    p.write_bytes(b"")
    with pytest.raises(engine.LoiFileKhongHopLe) as ei:
        engine._kiem_tra_pdf(str(p))
    assert "rỗng" in str(ei.value)


def test_kiem_tra_pdf_khong_phai_pdf(tmp_path):
    # đuôi .pdf nhưng nội dung là văn bản thường -> magic bytes không có '%PDF'
    p = tmp_path / "gia.pdf"
    p.write_text("đây là văn bản, không phải PDF")
    with pytest.raises(engine.LoiFileKhongHopLe) as ei:
        engine._kiem_tra_pdf(str(p))
    assert "%PDF" in str(ei.value)


def test_kiem_tra_pdf_khong_ton_tai(tmp_path):
    with pytest.raises(engine.LoiFileKhongHopLe):
        engine._kiem_tra_pdf(str(tmp_path / "khong-co.pdf"))


def test_kiem_tra_pdf_hop_le_khong_nem(tmp_path):
    p = tmp_path / "that.pdf"
    p.write_bytes(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n")
    engine._kiem_tra_pdf(str(p))            # không được ném


def test_convert_many_file_hong_khong_giet_me(tmp_path, monkeypatch):
    out_dir = tmp_path / "out"
    rong = tmp_path / "rong.pdf"
    rong.write_bytes(b"")
    gia = tmp_path / "gia.pdf"
    gia.write_text("khong phai pdf")
    # cô lập khỏi Tesseract: guard file hỏng chạy TRƯỚC mọi lời gọi OCR
    monkeypatch.setattr(engine.ocr, "configure_tesseract", lambda: None)
    monkeypatch.setattr(engine.ocr, "has_vietnamese", lambda: True)

    events = []
    res = engine.convert_many(
        [str(rong), str(gia)], str(out_dir),
        on_file=lambda i, e, d: events.append((i, e)))

    assert len(res) == 2, "cả mẻ phải chạy tiếp qua file hỏng"
    assert all("error" in r for r in res)
    assert res[0]["out_path"] is None and res[1]["out_path"] is None
    assert [e for _, e in events].count("error") == 2
    # thông báo tử tế bằng tiếng Việt (không phải traceback)
    assert "rỗng" in res[0]["error"]
    assert "%PDF" in res[1]["error"]
