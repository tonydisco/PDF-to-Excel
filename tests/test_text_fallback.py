# -*- coding: utf-8 -*-
"""Đường text không cho ra số liệu -> extract_consensus phải quay về OCR.

Hồi quy đo được trên corpus (kqkd_6t.pdf): lớp text qua được bộ lọc chất
lượng nhưng parser bóc ra 0 giá trị — trước đây trả luôn kết quả trống,
tệ hơn cả OCR. Nguyên tắc: lớp text không bao giờ được làm dữ liệu tệ đi.
"""
import glob
import os

import fitz
import pytest

from bctc import parser

KEYS = ("CDKT", "KQHDKD", "LCTT")


def _doc_rong():
    d = fitz.open()
    d.new_page()
    return d


def _res_rong():
    return {k: {} for k in KEYS}


def _res_co_so_lieu():
    r = _res_rong()
    r["CDKT"]["270"] = (123456, 654321)
    return r


def _lap_fake(monkeypatch, res_text_fn, res_ocr_fn):
    """Giả lập locate/extract; rẽ nhánh theo cờ _bctc_dung_lop_text như
    parser thật. Trả về dict đếm lượt gọi từng đường."""
    dem = {"locate": 0, "extract_text": 0, "extract_ocr": 0}

    def fake_locate(doc, **kw):
        dem["locate"] += 1
        return [(0, "CDKT")]

    def fake_extract(doc, lang="vie", dpi=300, page_range=None, digit_pass=False,
                     log=lambda *_: None, scope=None, workers=None):
        if getattr(doc, "_bctc_dung_lop_text", False):
            dem["extract_text"] += 1
            return res_text_fn(), [], {}
        dem["extract_ocr"] += 1
        return res_ocr_fn(), [], {}

    monkeypatch.setattr(parser, "locate_pages", fake_locate)
    monkeypatch.setattr(parser, "extract", fake_extract)
    return dem


# ----------------------------------------------------------------------
# extract_consensus: khi nào quay về OCR, khi nào không
# ----------------------------------------------------------------------
@pytest.mark.parametrize("res_text_rong", [
    _res_rong(),                                                  # không dòng nào
    {"CDKT": {"270": (None, None)}, "KQHDKD": {}, "LCTT": {}},    # có dòng, toàn None
], ids=["khong_dong", "toan_none"])
def test_text_rong_quay_ve_ocr_dung_mot_lan(monkeypatch, res_text_rong):
    dem = _lap_fake(
        monkeypatch,
        res_text_fn=lambda: {k: dict(v) for k, v in res_text_rong.items()},
        res_ocr_fn=_res_co_so_lieu)

    logs = []
    doc = _doc_rong()
    doc._bctc_dung_lop_text = True
    merged, _, _, _ = parser.extract_consensus(doc, dpis=(180, 235),
                                               log=logs.append)
    doc.close()

    assert merged["CDKT"]["270"] == (123456, 654321), \
        "phải trả về kết quả của lượt OCR"
    assert dem["locate"] == 2, "phải định vị LẠI dưới OCR (đúng 1 lần retry)"
    assert dem["extract_text"] == 2 and dem["extract_ocr"] == 2, \
        "mỗi đường chạy đủ 2 DPI, không có lượt thừa"
    assert any("↻" in m for m in logs), "thiếu dòng log ↻ báo quay về OCR"


def test_text_rong_va_ocr_cung_rong_chi_thu_lai_mot_lan(monkeypatch):
    """Chốt chặn lặp vô hạn: OCR retry cũng rỗng -> dừng, không thử thêm."""
    dem = _lap_fake(monkeypatch, res_text_fn=_res_rong, res_ocr_fn=_res_rong)

    doc = _doc_rong()
    doc._bctc_dung_lop_text = True
    merged, _, _, _ = parser.extract_consensus(doc, dpis=(180, 235))
    doc.close()

    assert dem["locate"] == 2, "chỉ được thử lại ĐÚNG một lần"
    assert dem["extract_ocr"] == 2
    assert all(not any(v is not None for cap in bang.values() for v in cap)
               for bang in merged.values())


def test_khong_thu_lai_khi_text_co_so_lieu(monkeypatch):
    """Chỉ MỘT giá trị (thậm chí lệch cột: cur=None) cũng đủ giữ đường text."""
    res = _res_rong()
    res["KQHDKD"]["01"] = (None, 500)
    dem = _lap_fake(monkeypatch,
                    res_text_fn=lambda: {k: dict(v) for k, v in res.items()},
                    res_ocr_fn=_res_co_so_lieu)

    logs = []
    doc = _doc_rong()
    doc._bctc_dung_lop_text = True
    merged, _, _, _ = parser.extract_consensus(doc, dpis=(180, 235),
                                               log=logs.append)
    doc.close()

    assert merged["KQHDKD"]["01"] == (None, 500)
    assert dem["locate"] == 1 and dem["extract_ocr"] == 0
    assert not any("↻" in m for m in logs)


def test_khong_thu_lai_khi_ocr_rong(monkeypatch):
    """Đường OCR ngay từ đầu mà rỗng -> không có gì để quay về, trả như cũ."""
    dem = _lap_fake(monkeypatch, res_text_fn=_res_co_so_lieu,
                    res_ocr_fn=_res_rong)

    logs = []
    doc = _doc_rong()
    doc._bctc_dung_lop_text = False
    merged, _, _, _ = parser.extract_consensus(doc, dpis=(180, 235),
                                               log=logs.append)
    doc.close()

    assert dem["locate"] == 1
    assert dem["extract_text"] == 0 and dem["extract_ocr"] == 2
    assert not any("↻" in m for m in logs)


# ----------------------------------------------------------------------
# locate_pages: không được lật cờ False (do lượt retry đặt) ngược về True
# ----------------------------------------------------------------------
def test_locate_pages_ton_trong_co_false_da_dat(monkeypatch):
    monkeypatch.setattr(parser, "_scan_strip", lambda doc, i, lang, dpi: (i, None))
    monkeypatch.setattr(
        parser.textlayer, "is_usable",
        lambda d: pytest.fail("không được tính lại cờ đã đặt tường minh"))

    doc = _doc_rong()
    doc._bctc_dung_lop_text = False
    parser.locate_pages(doc)
    assert doc._bctc_dung_lop_text is False
    doc.close()


def test_locate_pages_van_tinh_co_khi_chua_dat(monkeypatch):
    monkeypatch.setattr(parser, "_scan_strip", lambda doc, i, lang, dpi: (i, None))
    monkeypatch.setattr(parser.textlayer, "is_usable", lambda d: True)

    doc = _doc_rong()                     # chưa có thuộc tính cờ
    parser.locate_pages(doc)
    assert doc._bctc_dung_lop_text is True
    doc.close()


# ----------------------------------------------------------------------
# Corpus: file hồi quy thật — text qua bộ lọc nhưng bóc ra 0 giá trị
# ----------------------------------------------------------------------
def test_corpus_kqkd_6t_quay_ve_ocr_va_co_so_lieu(corpus_root, tmp_path):
    hits = glob.glob(os.path.join(corpus_root, "**", "kqkd_6t.pdf"),
                     recursive=True)
    if not hits:
        pytest.skip("Không có kqkd_6t.pdf trong corpus")

    from bctc import engine, ocr
    try:
        ocr.configure_tesseract()
    except ocr.TesseractNotFound:
        pytest.skip("Máy không có Tesseract")
    if not ocr.has_vietnamese():
        pytest.skip("Tesseract chưa có gói tiếng Việt (vie)")

    logs = []
    r = engine.convert_pdf(sorted(hits)[0], str(tmp_path), log=logs.append)

    assert any("↻" in m for m in logs), "phải có dòng log quay về OCR"
    so_gia_tri = sum(1 for bang in r["results"].values()
                     for cap in bang.values() for v in cap if v is not None)
    assert so_gia_tri > 0, "OCR fallback phải bóc được ít nhất một giá trị"
