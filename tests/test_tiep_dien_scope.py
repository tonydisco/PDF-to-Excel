# -*- coding: utf-8 -*-
"""V1 Đợt 2 — trang TIẾP DIỄN (không lặp tiêu đề) phải vào scope.

CĐKT dài 2-3 trang nhưng locate_pages chỉ giữ trang CÓ tiêu đề; trang nối
không lặp tiêu đề bị vứt vĩnh viễn (bằng chứng: BCTC 6T Tân Bình mất CĐKT
p4-p5, LCTT p8 — docs/superpowers/plans/chan-doan-dot-2.md §1). Sau khi
định vị, scope phải được MỞ RỘNG: trang nằm giữa một trang báo cáo và mốc
kế tiếp (tiêu đề khác / trang thuyết minh / mục lục / trần K trang) được
gán vào báo cáo đứng TRƯỚC nó, giữ nguyên hình dạng trả về
[(trang, nhãn báo cáo)] để mọi tầng dưới không phải đổi.
"""
import glob
import os

import fitz
import pytest

from bctc import parser


def _doc(n):
    d = fitz.open()
    for _ in range(n):
        d.new_page()
    # trang trống không có lớp text — đặt cờ tường minh để không đụng textlayer
    d._bctc_dung_lop_text = False
    return d


def _lap_quet(monkeypatch, bang):
    """Giả lập _scan_strip theo bảng {trang: (tiêu đề, dấu hiệu dừng)}.

    Trả về dict đếm số LƯỢT quét dải của từng trang (đo chi phí: mỗi dải
    chỉ được OCR một lần, mở rộng phải tái dùng kết quả vòng batch).
    """
    dem = {}

    def fake(doc, i, lang, dpi, nd=None, quet_dai=True):
        # nd: V5 — vòng batch của locate render dải trên luồng chính rồi
        # truyền vào; giả lập bỏ qua ảnh, chỉ tra bảng.
        # quet_dai: V4a — có quét dải dưới không (mở rộng tiếp diễn tắt).
        dem[i] = dem.get(i, 0) + 1
        title, dau_hieu = bang.get(i, (None, None))
        return i, title, dau_hieu

    monkeypatch.setattr(parser, "_scan_strip", fake)
    return dem


# ----------------------------------------------------------------------
# Mở rộng scope: các luật gán / dừng
# ----------------------------------------------------------------------
def test_trang_giua_hai_tieu_de_thuoc_bao_cao_truoc(monkeypatch):
    """Trang kẹp giữa 2 tiêu đề = trang tiếp diễn của báo cáo đứng trước."""
    _lap_quet(monkeypatch, {
        0: ("CDKT", None),
        3: ("KQHDKD", None),
        5: ("LCTT", None),
    })
    doc = _doc(6)
    scope = parser.locate_pages(doc, workers=2)
    doc.close()

    assert scope == [(0, "CDKT"), (1, "CDKT"), (2, "CDKT"),
                     (3, "KQHDKD"), (4, "KQHDKD"), (5, "LCTT")]


def test_giu_hinh_dang_va_thu_tu_tang_dan(monkeypatch):
    """Hình dạng trả về [(int, str)] và thứ tự trang tăng dần được giữ."""
    _lap_quet(monkeypatch, {1: ("CDKT", None), 4: ("KQHDKD", None)})
    doc = _doc(6)
    scope = parser.locate_pages(doc, workers=2)
    doc.close()

    assert all(isinstance(p, int) and t in ("CDKT", "KQHDKD", "LCTT")
               for p, t in scope)
    trang = [p for p, _ in scope]
    assert trang == sorted(trang) and len(trang) == len(set(trang))


def test_tran_3_trang_tiep_dien_moi_bao_cao(monkeypatch):
    """Trần K=3 trang tiếp diễn cho mỗi báo cáo — không nuốt cả tài liệu."""
    _lap_quet(monkeypatch, {0: ("CDKT", None)})
    doc = _doc(9)
    scope = parser.locate_pages(doc, workers=2)
    doc.close()

    assert scope == [(0, "CDKT"), (1, "CDKT"), (2, "CDKT"), (3, "CDKT")]


@pytest.mark.parametrize("dau_hieu", ["thuyet minh", "muc luc"])
def test_dau_hieu_dung_chan_mo_rong(monkeypatch, dau_hieu):
    """Gặp trang thuyết minh / mục lục thì dừng, trang sau đó không vào scope."""
    _lap_quet(monkeypatch, {0: ("CDKT", None), 2: (None, dau_hieu)})
    doc = _doc(5)
    scope = parser.locate_pages(doc, workers=2)
    doc.close()

    assert scope == [(0, "CDKT"), (1, "CDKT")]


def test_khong_them_trang_truoc_tieu_de_dau(monkeypatch):
    """Trang ĐỨNG TRƯỚC tiêu đề đầu tiên (bìa, ý kiến kiểm toán) không bao
    giờ được thêm; trần mở rộng không vượt quá trang cuối tài liệu."""
    _lap_quet(monkeypatch, {2: ("CDKT", None)})
    doc = _doc(5)
    scope = parser.locate_pages(doc, workers=2)
    doc.close()

    assert scope == [(2, "CDKT"), (3, "CDKT"), (4, "CDKT")]
    assert all(p >= 2 for p, _ in scope)


def test_khong_tieu_de_khong_mo_rong(monkeypatch):
    """Không định vị được tiêu đề nào -> scope rỗng như cũ (không mở rộng mù)."""
    _lap_quet(monkeypatch, {})
    doc = _doc(4)
    scope = parser.locate_pages(doc, workers=2)
    doc.close()

    assert scope == []


# ----------------------------------------------------------------------
# Chi phí: dải đầu mỗi trang chỉ OCR MỘT lần; sau điểm dừng sớm chỉ quét
# thêm đúng phần cần cho mở rộng
# ----------------------------------------------------------------------
def test_moi_dai_trang_chi_quet_mot_lan(monkeypatch):
    dem = _lap_quet(monkeypatch, {
        0: ("CDKT", None),
        3: ("KQHDKD", None),
        5: ("LCTT", None),
    })
    doc = _doc(6)
    parser.locate_pages(doc, workers=2)
    doc.close()

    assert all(v == 1 for v in dem.values()), \
        "dải trang bị OCR lặp: %r" % dem


def test_mo_rong_sau_dung_som_gap_tieu_de_moi_thi_dung(monkeypatch):
    """Sau điểm dừng sớm của vòng batch, mở rộng báo cáo CUỐI phải tự quét
    thêm dải trang chưa quét; gặp trang mang tiêu đề thì coi là mốc dừng
    (không thêm trang đó, không quét tiếp)."""
    dem = _lap_quet(monkeypatch, {
        0: ("CDKT", None),
        1: ("KQHDKD", None),
        2: ("LCTT", None),
        4: ("KQHDKD", None),          # tài liệu hợp nhất lặp lại phía sau
    })
    doc = _doc(8)
    # workers=1 -> batch 1 trang: p3 không tiêu đề + đủ 3 báo cáo -> dừng sớm
    scope = parser.locate_pages(doc, workers=1)
    doc.close()

    assert scope == [(0, "CDKT"), (1, "KQHDKD"), (2, "LCTT"), (3, "LCTT")]
    assert dem.get(4) == 1, "phải quét thêm dải trang 5 để biết mốc dừng"
    assert 5 not in dem and 6 not in dem and 7 not in dem, \
        "dừng rồi thì không được quét tiếp: %r" % dem


# ----------------------------------------------------------------------
# _dau_hieu_dung: nhận trang thuyết minh, KHÔNG nhầm cột 'Thuyết minh'
# trong header bảng của trang tiếp diễn
# ----------------------------------------------------------------------
@pytest.mark.parametrize("dong, mong_doi", [
    (["THUYẾT MINH BÁO CÁO TÀI CHÍNH"], "thuyet minh"),
    (["BẢN THUYẾT MINH BÁO CÁO TÀI CHÍNH (tiếp theo)"], "thuyet minh"),
    (["NOTES TO THE FINANCIAL STATEMENTS"], "thuyet minh"),
    (["MỤC LỤC"], "muc luc"),
    # header bảng của trang báo cáo/tiếp diễn: có chữ 'Thuyết minh' (tên CỘT)
    # nhưng KHÔNG phải trang thuyết minh -> không được chặn mở rộng
    (["TÀI SẢN", "Mã số", "Thuyết minh", "Số cuối năm", "Số đầu năm"], None),
    (["Chỉ tiêu Mã số Thuyết minh Số cuối năm Số đầu năm"], None),
    # chân trang 'Các thuyết minh ... là bộ phận hợp thành của báo cáo tài
    # chính này' là CÂU VĂN dài, không phải tiêu đề phần thuyết minh
    (["Các thuyết minh đính kèm là một bộ phận hợp thành "
      "của báo cáo tài chính này"], None),
    (["A - TÀI SẢN NGẮN HẠN", "100", "1.234.567"], None),
    ([], None),
])
def test_dau_hieu_dung(dong, mong_doi):
    assert parser._dau_hieu_dung(dong) == mong_doi


# ----------------------------------------------------------------------
# _scan_strip (nhánh lớp text): trả thêm dấu hiệu dừng, không đổi 2 phần đầu
# ----------------------------------------------------------------------
def _doc_text(dong_chu):
    """Doc 1 trang có lớp text thật (chữ KHÔNG dấu — font Helvetica);
    norm() bỏ dấu nên khớp mẫu y như chữ có dấu."""
    d = fitz.open()
    page = d.new_page()
    y = 60
    for t in dong_chu:
        page.insert_text((60, y), t, fontsize=11)
        y += 20
    d._bctc_dung_lop_text = True
    return d


def test_scan_strip_lop_text_tra_tieu_de_va_dau_hieu():
    doc = _doc_text(["BANG CAN DOI KE TOAN"])
    assert parser._scan_strip(doc, 0, "vie", 135) == (0, "CDKT", None)
    doc.close()

    doc = _doc_text(["THUYET MINH BAO CAO TAI CHINH"])
    i, title, dau_hieu = parser._scan_strip(doc, 0, "vie", 135)
    assert (i, title, dau_hieu) == (0, None, "thuyet minh")
    doc.close()


# ----------------------------------------------------------------------
# Corpus: hồ sơ động lực của V1 — BCTC 6T Tân Bình mất CĐKT p4-p5, LCTT p8
# vì trang nối không lặp tiêu đề (chan-doan-dot-2.md §1). Chỉ chạy locate
# (rẻ); phần bóc tách đo ở probe/tier riêng.
# ----------------------------------------------------------------------
def test_corpus_tan_binh_trang_noi_vao_scope(corpus_root):
    hits = glob.glob(os.path.join(corpus_root, "**", "BCTC 6T*2025.pdf"),
                     recursive=True)
    if not hits:
        pytest.skip("Không có BCTC 6T ĐẦU NĂM 2025.pdf trong corpus")

    from bctc import ocr
    try:
        ocr.configure_tesseract()
    except ocr.TesseractNotFound:
        pytest.skip("Máy không có Tesseract")
    if not ocr.has_vietnamese():
        pytest.skip("Tesseract chưa có gói tiếng Việt (vie)")

    doc = fitz.open(sorted(hits)[0])
    logs = []
    scope = parser.locate_pages(doc, log=logs.append)
    doc.close()

    them = [m for m in logs if "tiếp diễn" in m]
    assert them, "phải có trang tiếp diễn vào scope (CĐKT p4-p5, LCTT p8)"
    so_trang = {}
    for _, t in scope:
        so_trang[t] = so_trang.get(t, 0) + 1
    assert so_trang.get("CDKT", 0) >= 2, \
        "CĐKT nhiều trang phải chiếm >= 2 trang trong scope: %r" % scope
