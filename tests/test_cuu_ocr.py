# -*- coding: utf-8 -*-
"""V2 Đợt 2 — cứu OCR trang SẬP (trang định vị được nhưng OCR ra gần-không).

Hồ sơ động lực: `BCTC 2023.pdf` — trang LCTT (p7, trang TIÊU ĐỀ) OCR thành
ký tự ống, 0-1 token mã -> trọn 23 ô LCTT sót; probe cho thấy psm=4 GIỮ
NGUYÊN DPI đọc lại ra 16 mã (docs/superpowers/plans/chan-doan-dot-2.md +
.superpowers/sdd/dot2-v2-cuu-ocr.md §1). Trang cuối run 0 mã (p4/p6/p8) là
trang CHỮ KÝ: mọi biến thể vẫn 0 mã -> không bao giờ cứu (chi phí thuần).

Luật V2 (bên trong extract, sau lượt gán dòng):
  - SẬP = trang có < 2 dòng chứa token mã khớp khung của nhãn trang, và:
      (a) trang TIÊU ĐỀ của run mà TỔNG mã cả run mỏng (< 8), hoặc
      (b) trang GIỮA run (hai phía đều còn trang cùng nhãn).
    Trang CUỐI run không bao giờ cứu.
  - Cứu tối đa 2 lượt OCR: psm=4 giữ DPI (tái dùng ảnh) rồi psm=6 ở
    min(DPI+100, 330); chọn biến thể NHIỀU mã nhất, chỉ thay khi HƠN bản gốc.
"""
import glob
import os

import fitz
import pytest

from bctc import parser
from bctc import templates as T

VALID = {
    "CDKT": T.codes_of(T.BANG_CAN_DOI_KE_TOAN),
    "KQHDKD": T.codes_of(T.KET_QUA_KINH_DOANH),
    "LCTT": T.codes_of(T.LUU_CHUYEN_TIEN_TE_GT) | T.codes_of(T.LUU_CHUYEN_TIEN_TE_TT),
}


def w(text, cx, cy, right=None):
    """Từ OCR tổng hợp — đủ các khoá mà đường extract dùng."""
    return {"text": text, "cx": cx, "cy": cy,
            "right": right if right is not None else min(cx + 0.03, 1.0),
            "left": max(cx - 0.03, 0.0), "top": cy, "width": 10, "height": 10,
            "conf": 90.0, "lx": max(cx - 0.03, 0.0), "nh": 0.01}


def dong_ma(code, cy, cur="1.234.567", prior="7.654.321"):
    """Một dòng dữ liệu: chỉ tiêu + mã số + 2 cột giá trị."""
    return [w("Chỉ", 0.10, cy), w("tiêu", 0.16, cy), w(code, 0.45, cy),
            w(cur, 0.72, cy, right=0.75), w(prior, 0.88, cy, right=0.91)]


def dong_rac(cy):
    return [w("|", 0.30, cy), w("¬", 0.55, cy)]


def trang_khoe(nhan="LCTT", n=12):
    """Trang OCR tốt: n dòng mã tăng dần theo khung."""
    ma = sorted(VALID[nhan], key=lambda c: (len(c), c))[:n]
    return [dong_ma(c, 0.08 + i * 0.06) for i, c in enumerate(ma)]


def trang_sap():
    """Trang sập: toàn ký tự ống / mảnh vụn, 0 token mã."""
    return [dong_rac(0.1 + i * 0.08) for i in range(8)]


# ----------------------------------------------------------------------
# _dem_ma_trang: đếm số DÒNG chứa token mã khớp khung
# ----------------------------------------------------------------------
def test_dem_ma_trang():
    lines = trang_khoe("LCTT", 5) + trang_sap()
    assert parser._dem_ma_trang(lines, VALID["LCTT"]) == 5
    assert parser._dem_ma_trang(trang_sap(), VALID["LCTT"]) == 0
    assert parser._dem_ma_trang([], VALID["LCTT"]) == 0


# ----------------------------------------------------------------------
# _trang_sap: bộ phát hiện trang sập (thuần dữ liệu, không OCR)
# ----------------------------------------------------------------------
def test_trang_tieu_de_0_ma_bao_cao_mong_bi_danh_dau():
    """Hồ sơ LCTT p7 BCTC-2023: trang tiêu đề 0 mã, cả run chỉ có nó."""
    scope = [(6, "LCTT")]
    page_lines = {6: trang_sap()}
    assert parser._trang_sap(scope, page_lines, VALID) == [(6, "LCTT")]


def test_trang_tieu_de_khoe_khong_danh_dau():
    scope = [(0, "CDKT")]
    page_lines = {0: trang_khoe("CDKT", 20)}
    assert parser._trang_sap(scope, page_lines, VALID) == []


def test_trang_cuoi_run_0_ma_khong_cuu():
    """Trang CUỐI run 0 mã = trang chữ ký (p4/p6/p8 BCTC-2023) — bỏ qua."""
    scope = [(6, "LCTT"), (7, "LCTT")]
    page_lines = {6: trang_khoe("LCTT", 12), 7: trang_sap()}
    assert parser._trang_sap(scope, page_lines, VALID) == []


def test_trang_giua_run_0_ma_duoc_cuu():
    """Lỗ hổng GIỮA bảng (hồ sơ Tân Bình CDKT p3): hai phía đều có mã."""
    scope = [(1, "CDKT"), (2, "CDKT"), (3, "CDKT")]
    page_lines = {1: trang_khoe("CDKT", 15), 2: trang_sap(),
                  3: trang_khoe("CDKT", 10)}
    assert parser._trang_sap(scope, page_lines, VALID) == [(2, "CDKT")]


def test_tieu_de_it_ma_nhung_bao_cao_day_khong_cuu():
    """Trang tiêu đề chỉ chứa header, bảng bắt đầu trang sau: tổng mã cả
    run vẫn dày -> KHÔNG cứu (đỡ 2 lượt OCR vô ích)."""
    scope = [(0, "CDKT"), (1, "CDKT")]
    page_lines = {0: trang_sap(), 1: trang_khoe("CDKT", 25)}
    assert parser._trang_sap(scope, page_lines, VALID) == []


def test_hai_run_rieng_biet_deu_xet():
    """Hai báo cáo, mỗi run xét độc lập: LCTT tiêu đề sập được cứu,
    KQHDKD khoẻ không đụng."""
    scope = [(4, "KQHDKD"), (6, "LCTT")]
    page_lines = {4: trang_khoe("KQHDKD", 12), 6: trang_sap()}
    assert parser._trang_sap(scope, page_lines, VALID) == [(6, "LCTT")]


def test_scope_rong_khong_sap():
    assert parser._trang_sap([], {}, VALID) == []


# ----------------------------------------------------------------------
# _bien_the_tot_nhat: chọn biến thể cứu theo số mã
# ----------------------------------------------------------------------
def test_chon_bien_the_nhieu_ma_nhat():
    bt = [(4, 180, ["a"], 16), (6, 280, ["b"], 3)]
    assert parser._bien_the_tot_nhat(1, bt) == (4, 180, ["a"], 16)


def test_khong_bien_the_nao_hon_ban_goc():
    bt = [(4, 180, ["a"], 0), (6, 280, ["b"], 1)]
    assert parser._bien_the_tot_nhat(1, bt) is None


def test_hoa_so_ma_lay_bien_the_dau():
    """Hoà -> lấy lượt thử ĐẦU (rẻ hơn, tất định)."""
    bt = [(4, 180, ["a"], 5), (6, 280, ["b"], 5)]
    assert parser._bien_the_tot_nhat(2, bt) == (4, 180, ["a"], 5)


# ----------------------------------------------------------------------
# extract tích hợp: cứu OCR chạy trong extract với OCR giả lập
# ----------------------------------------------------------------------
def _doc_mot_trang():
    d = fitz.open()
    d.new_page()                       # A4 mặc định 595x842pt
    d._bctc_dung_lop_text = False
    return d


class _OcrGia:
    """Giả lập ocr.ocr_lines, điều phối THEO THAM SỐ (an toàn đa luồng):
    psm=6 ở DPI chính -> lượt chính; psm=4 -> lượt cứu 1; psm=6 DPI cao ->
    lượt cứu 2. DPI suy từ bề rộng ảnh (trang A4 595pt)."""

    def __init__(self, main_dpi, chinh, cuu1, cuu2):
        self.main_dpi = main_dpi
        self.chinh, self.cuu1, self.cuu2 = chinh, cuu1, cuu2
        self.gois = []                 # [(psm, dpi_est)]

    def __call__(self, img, lang="vie", psm=6, min_conf=25, whitelist=None):
        dpi_est = int(round(img.size[0] * 72.0 / 595))
        self.gois.append((psm, dpi_est))
        if psm == 4:
            lines = self.cuu1
        elif dpi_est > self.main_dpi + 5:
            lines = self.cuu2
        else:
            lines = self.chinh
        return img.size[0], img.size[1], lines


def test_extract_cuu_trang_tieu_de_sap(monkeypatch):
    """Trang LCTT sập ở psm=6, psm=4 đọc lại được -> extract phải ra mã,
    log ⛑ đúng biến thể thắng."""
    gia = _OcrGia(180, chinh=trang_sap(),
                  cuu1=[dong_ma("01", 0.30), dong_ma("02", 0.38),
                        dong_ma("20", 0.46)],
                  cuu2=trang_sap())
    monkeypatch.setattr(parser.ocr, "ocr_lines", gia)
    doc = _doc_mot_trang()
    logs = []
    res, warns, meta = parser.extract(doc, dpi=180, scope=[(0, "LCTT")],
                                      log=logs.append, workers=2)
    doc.close()

    assert set(res["LCTT"]) == {"01", "02", "20"}
    assert res["LCTT"]["01"] == (1234567, 7654321)
    assert any("⛑ trang 1: OCR lại (psm=4 dpi=180) — 3 mã" in m for m in logs), logs


def test_extract_trang_khoe_khong_ocr_them(monkeypatch):
    """Trang khoẻ: KHÔNG được tốn thêm lượt OCR nào (không psm=4, không DPI cao)."""
    gia = _OcrGia(180, chinh=trang_khoe("LCTT", 12), cuu1=[], cuu2=[])
    monkeypatch.setattr(parser.ocr, "ocr_lines", gia)
    doc = _doc_mot_trang()
    logs = []
    res, _, _ = parser.extract(doc, dpi=180, scope=[(0, "LCTT")],
                               log=logs.append, workers=2)
    doc.close()

    assert len(res["LCTT"]) == 12
    assert gia.gois == [(6, 180)], gia.gois
    assert not any("⛑" in m or "✕" in m for m in logs)


def test_extract_cuu_that_bai_giu_ban_goc_va_bao(monkeypatch):
    """Cả 2 biến thể vẫn 0 mã -> giữ bản gốc, log ✕, đúng 2 lượt thử."""
    gia = _OcrGia(180, chinh=trang_sap(), cuu1=trang_sap(), cuu2=trang_sap())
    monkeypatch.setattr(parser.ocr, "ocr_lines", gia)
    doc = _doc_mot_trang()
    logs = []
    res, _, _ = parser.extract(doc, dpi=180, scope=[(0, "LCTT")],
                               log=logs.append, workers=2)
    doc.close()

    assert res["LCTT"] == {}
    assert any("✕ trang 1: cứu OCR không cải thiện" in m for m in logs), logs
    them = [g for g in gia.gois if g != (6, 180)]
    assert len(them) == 2 and them[0][0] == 4, gia.gois


def test_extract_dpi_tran_chi_mot_luot_cuu(monkeypatch):
    """DPI chính đã >= trần 330 -> lượt cứu 2 (DPI cao hơn) bị bỏ, chỉ psm=4.

    Nới trần điểm ảnh V5 riêng cho test này: A4 @ 330 = 10,5 MP vượt trần
    render hàng loạt (6 MP) sẽ bị hạ DPI — ở đây ta chỉ kiểm luật TRẦN DPI
    CỨU, không kiểm trần điểm ảnh (đã có tests/test_bo_nho.py lo)."""
    monkeypatch.setattr(parser, "TRAN_MP_RENDER", 99.0)
    gia = _OcrGia(330, chinh=trang_sap(), cuu1=trang_sap(), cuu2=trang_sap())
    monkeypatch.setattr(parser.ocr, "ocr_lines", gia)
    doc = _doc_mot_trang()
    res, _, _ = parser.extract(doc, dpi=330, scope=[(0, "LCTT")],
                               log=lambda *_: None, workers=2)
    doc.close()

    them = [g for g in gia.gois if g != (6, 330)]
    assert them == [(4, 330)], gia.gois


# ----------------------------------------------------------------------
# Corpus: hồ sơ động lực — BCTC 2023.pdf, LCTT sập toàn thân bảng
# ----------------------------------------------------------------------
@pytest.fixture(scope="module")
def _tesseract():
    from bctc import ocr
    try:
        ocr.configure_tesseract()
    except ocr.TesseractNotFound:
        pytest.skip("Máy không có Tesseract")
    if not ocr.has_vietnamese():
        pytest.skip("Tesseract chưa có gói tiếng Việt (vie)")


def test_corpus_bctc_2023_lctt_duoc_cuu(corpus_root, _tesseract, tmp_path):
    """LCTT của BCTC 2023.pdf trước V2 = 0 mã (trang OCR thành ký tự ống).
    Sau V2 phải bóc được mã LCTT và khớp đáp án LCTT_2023.xls ở mức đo được.

    Đo qua engine.convert_pdf — đúng đường sản xuất (dpis 180/235, cùng
    đường tier-1 chấm); extract_consensus mặc định (185/240) cho psm=4 ra
    ít mã hơn hẳn (10 so với 16) — DPI lượt cứu rất nhạy trên trang này."""
    hits = [p for p in glob.glob(os.path.join(corpus_root, "**", "BCTC 2023.pdf"),
                                 recursive=True) if "Mui Ne" in p]
    if not hits:
        pytest.skip("Không có BCTC 2023.pdf (Sai gon Mui Ne) trong corpus")
    keys = [p for p in glob.glob(os.path.join(corpus_root, "**", "LCTT_2023.xls"),
                                 recursive=True) if "Mui Ne" in p]
    if not keys:
        pytest.skip("Không có đáp án LCTT_2023.xls trong corpus")

    from bctc import engine
    from tests.regression import groundtruth, metrics

    logs = []
    res = engine.convert_pdf(sorted(hits)[0], str(tmp_path), log=logs.append)
    got = (res.get("results") or {}).get("LCTT", {})

    # Trước V2: LCTT trống hoàn toàn. Sau V2: phải có mã kèm giá trị.
    lctt = {c: v for c, v in got.items() if any(x is not None for x in v)}
    assert len(lctt) > 0, "LCTT vẫn 0 mã sau cứu OCR — logs: %r" % logs
    assert any("⛑" in m for m in logs), "phải có log cứu OCR: %r" % logs

    # Đối chiếu đáp án: trước V2 LCTT sót trọn 23/23 ô chấm được (0 đúng);
    # sau V2 đo được 12 đúng / 11 sót / 0 lệch — chốt ngưỡng >= 10 đúng
    # (trừ hao dao động phiên bản Tesseract, vẫn bắt được mọi thoái lui lớn).
    expected = groundtruth.read_statement(sorted(keys)[0])
    c = metrics.compare(expected, got)
    assert c["dung"] >= 10, "LCTT khớp đáp án quá ít: %r (logs %r)" % (c, logs)
