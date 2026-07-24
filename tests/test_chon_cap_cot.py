# -*- coding: utf-8 -*-
"""
Chọn CẶP cột giá trị khi bảng có >= 3 cột số (Đợt 2, việc #1).

Bối cảnh (docs/superpowers/plans/chan-doan-dot-2.md §2): gia đình bản in phần
mềm kế toán in KQHDKD/LCTT với BA cột số 'Kỳ này | Kỳ trước | Lũy kế'
(kqkd_6t.pdf, BCTC 2023.pdf, SGMN-2022). Lối chọn cũ `sel = centers[-2:]`
lấy 2 cột PHẢI NHẤT = (Kỳ trước, Lũy kế); trên báo cáo 6 tháng/năm thì
Lũy kế == Kỳ này nên kết quả là hoán vị hoàn hảo hai cột — kqkd_6t.pdf lệch
24/24 ô. Cặp đúng là (Kỳ này, Kỳ trước).

Từ nay khi có >2 cột phải chọn theo NGỮ NGHĨA, ưu tiên lần lượt:
  1. Nhãn tiêu đề cột (khi OCR đọc được): 'kỳ này/quý này/năm nay/số cuối' =
     kỳ này; 'kỳ trước/quý trước/năm trước/số đầu' = kỳ trước; 'lũy kế' = cột
     dồn -> LOẠI khỏi cặp. Nhãn nhập nhằng/mâu thuẫn -> giữ đường cũ + CẢNH BÁO
     (không bao giờ im lặng).
  2. Cột phải nhất TRÙNG GIÁ TRỊ cột 1 trên nhiều dòng (Lũy kế == Kỳ này của
     báo cáo 6T/năm) -> loại cột trùng.
  3. Kỳ báo cáo là QUÝ + 3-4 cột không đọc được nhãn -> quy ước bố cục quý
     (Kỳ này | Kỳ trước | Lũy kế [| Lũy kế trước]) -> lấy 2 cột TRÁI. Không
     áp cho CDKT (bảng cân đối không có cột Lũy kế).
  <= 2 cột: GIỮ NGUYÊN hành vi cũ (đa số corpus là báo cáo năm 2 cột).
"""
import os
import pytest

from bctc import parser

C3 = [0.668, 0.802, 0.938]          # đúng tâm 3 cột đo được trên kqkd_6t.pdf
C4 = [0.55, 0.67, 0.80, 0.94]


# ---------------------------------------------------------------------------
# chon_cap_cot — hàm quyết định thuần (đầu vào tổng hợp, không cần OCR)
# ---------------------------------------------------------------------------
def test_hai_cot_giu_nguyen_hanh_vi_cu():
    """Báo cáo năm 2 cột (đa số corpus): không được đụng vào."""
    sel, cb = parser.chon_cap_cot([0.75, 0.90], [set(), set()], "year", {})
    assert sel is None
    assert cb == []


def test_mot_cot_va_rong_giu_nguyen():
    assert parser.chon_cap_cot([0.9], [set()], "quarter", {}) == (None, [])
    assert parser.chon_cap_cot([], [], "quarter", {}) == (None, [])


def test_nhan_du_hai_phia_chon_theo_nhan():
    """Đọc được cả 'kỳ này' lẫn 'kỳ trước' -> cặp theo nhãn, loại 'lũy kế'."""
    sel, cb = parser.chon_cap_cot(
        C3, [{"cur"}, {"prior"}, {"cum"}], "year", {})
    assert sel == [0.668, 0.802]
    assert cb == []


def test_nhan_thang_vi_tri_khi_hai_cot_dao_cho():
    """Nhãn là căn cứ mạnh nhất: 'kỳ trước' đứng TRÁI 'kỳ này' thì cặp phải
    theo nhãn (cur trước, prior sau), không theo vị trí."""
    sel, cb = parser.chon_cap_cot(
        C3, [{"prior"}, {"cur"}, {"cum"}], "year", {})
    assert sel == [0.802, 0.668]
    assert cb == []


def test_chi_doc_duoc_luy_ke_van_loai_dung_cot():
    """Chỉ nhãn 'Lũy kế' đọc được (2 cột kia mờ): loại cột dồn, còn đúng 2
    cột thì trái = kỳ này."""
    sel, cb = parser.chon_cap_cot(C3, [set(), set(), {"cum"}], "year", {})
    assert sel == [0.668, 0.802]
    assert cb == []


def test_cot_phai_trung_gia_tri_cot_mot_bi_loai():
    """Tín hiệu kqkd_6t.pdf: cột phải nhất trùng giá trị cột 1 trên >= 4 dòng
    (Lũy kế == Kỳ này của báo cáo 6T) -> loại, lấy 2 cột trái."""
    trung = {(0, 1): (0, 13), (0, 2): (12, 13), (1, 2): (0, 13)}
    sel, cb = parser.chon_cap_cot(C3, [set(), set(), set()], "year", trung)
    assert sel == [0.668, 0.802]
    assert cb == []


def test_trung_duoi_nguong_khong_duoc_loai():
    """Ít dòng so sánh được / tỷ lệ trùng thấp -> KHÔNG đủ bằng chứng, giữ
    đường cũ (không đoán liều)."""
    for trung in ({(0, 2): (2, 3)},           # dưới 4 dòng so sánh được
                  {(0, 2): (5, 13)}):         # trùng 5/13 < 60%
        sel, cb = parser.chon_cap_cot(C3, [set(), set(), set()], "year", trung)
        assert sel is None
        assert cb == []


def test_quy_khong_nhan_lay_hai_cot_trai():
    """Báo cáo QUÝ 4 cột không đọc được nhãn -> quy ước bố cục quý, lấy 2 cột
    TRÁI (Kỳ này, Kỳ trước) thay vì 2 cột phải (cặp Lũy kế)."""
    sel, cb = parser.chon_cap_cot(C4, [set()] * 4, "quarter", {})
    assert sel == [0.55, 0.67]
    assert cb == []
    sel, cb = parser.chon_cap_cot(C3, [set()] * 3, "quarter", {},
                                  bao_cao="KQHDKD")
    assert sel == [0.668, 0.802]


def test_quy_uoc_quy_khong_ap_cho_cdkt():
    """CDKT không có cột Lũy kế -> 3 cụm trên CDKT là nhiễu, không được áp
    quy ước quý mà phải giữ đường cũ."""
    sel, cb = parser.chon_cap_cot(C3, [set()] * 3, "quarter", {},
                                  bao_cao="CDKT")
    assert sel is None
    assert cb == []


def test_nam_khong_nhan_khong_trung_giu_duong_cu():
    """Không tín hiệu nào -> hành vi cũ (2 cột phải nhất), không cảnh báo."""
    sel, cb = parser.chon_cap_cot(C3, [set()] * 3, "year", {})
    assert sel is None
    assert cb == []


def test_nhan_nhap_nhang_giu_duong_cu_va_canh_bao():
    """Một cột khớp CẢ 'kỳ này' lẫn 'kỳ trước' -> nhập nhằng: giữ đường cũ
    nhưng BẮT BUỘC có cảnh báo (không bao giờ im lặng)."""
    sel, cb = parser.chon_cap_cot(
        C3, [{"cur", "prior"}, set(), {"cum"}], "year", {})
    assert sel is None
    assert len(cb) == 1
    assert "nhãn" in cb[0].lower()


def test_hai_cot_cung_mot_nhan_giu_duong_cu_va_canh_bao():
    """Hai cột cùng khớp 'kỳ này' -> mâu thuẫn: giữ đường cũ + cảnh báo."""
    sel, cb = parser.chon_cap_cot(C3, [{"cur"}, {"cur"}, {"prior"}], "year", {})
    assert sel is None
    assert len(cb) == 1


# ---------------------------------------------------------------------------
# doc_nhan_cot / dem_cot_trung — hai bộ thu thập tín hiệu từ dòng OCR
# ---------------------------------------------------------------------------
def _w(text, cx, right=None):
    return {"text": text, "cx": cx,
            "right": right if right is not None else cx + 0.02, "cy": 0.5}


def _sl(*line_lists):
    """Bọc các dòng thành section_lines dạng (ln, split, vtoks)."""
    return [(ln, 0.84, []) for ln in line_lists]


def test_doc_nhan_cot_gom_dung_cot_va_dung_o_dong_ma_dau_tien():
    section = _sl(
        # dòng tiêu đề: nhãn nằm GIỮA cột nên lệch trái so với mép phải cột số
        [_w("Kỳ", 0.60), _w("này", 0.63), _w("Kỳ", 0.73), _w("trước", 0.77),
         _w("Lũy", 0.86), _w("kế", 0.89)],
        # dòng dữ liệu đầu tiên có mã -> dừng quét tiêu đề tại đây
        [_w("Doanh", 0.10), _w("thu", 0.14), _w("01", 0.43),
         _w("22.730.333.061", 0.62, 0.668)],
        # nhãn "năm trước" ở GIỮA bảng không được tính vào tiêu đề
        [_w("năm", 0.60), _w("trước", 0.64)],
    )
    nhan = parser.doc_nhan_cot(section, C3, {"01"}, 0.43)
    assert nhan == [{"cur"}, {"prior"}, {"cum"}]


def test_doc_nhan_cot_khong_doc_duoc_tra_set_rong():
    section = _sl(
        [_w("|:", 0.41), _w("|2", 0.50), _w("1!", 0.62), _w("|", 0.81)],
        [_w("01", 0.43), _w("22.730.333.061", 0.62, 0.668)],
    )
    nhan = parser.doc_nhan_cot(section, C3, {"01"}, 0.43)
    assert nhan == [set(), set(), set()]


def test_dem_cot_trung_dem_dung_cap():
    lines = []
    # 5 dòng: cột 2 trùng cột 0; 1 dòng: khác nhau
    for i, (a, b) in enumerate([(111222333, 111222333)] * 5
                               + [(444555666, 999888777)]):
        lines.append([
            _w("%d" % a, 0.62, 0.668), _w("55.667", 0.78, 0.802),
            _w("%d" % b, 0.90, 0.938),
        ])
    trung = parser.dem_cot_trung(_sl(*lines), C3, False)
    assert trung[(0, 2)] == (5, 6)
    assert trung[(0, 1)] == (0, 6)
    assert trung[(1, 2)] == (0, 6)


# ---------------------------------------------------------------------------
# Hồi quy corpus: kqkd_6t.pdf — file bằng chứng của chẩn đoán (24/24 ô lệch
# là hoán vị hoàn hảo). Sau fix, cặp cột phải là (Kỳ này, Kỳ trước) đúng đáp
# án KQKD_6T.xls. Tự skip nếu máy không có corpus.
# ---------------------------------------------------------------------------
_KQKD_6T_PDF_REL = ("BTG document/BCTC 8/2024/Quý 2/"
                    "18_Cty CP Sai gon Mui Ne 2022/BC 6T.2024/kqkd_6t.pdf")
_KQKD_6T_KEY_REL = ("BTG document/BCTC 11/2024/Quý 2/"
                    "18_Cty CP Sai gon Mui Ne 2022/BC 6T.2024/KQKD_6T.xls")


def test_kqkd_6t_chon_dung_cap_ky_nay_ky_truoc(corpus_root, tmp_path):
    from bctc import engine, ocr
    from tests.regression import groundtruth, metrics

    pdf = os.path.join(corpus_root, *_KQKD_6T_PDF_REL.split("/"))
    key = os.path.join(corpus_root, *_KQKD_6T_KEY_REL.split("/"))
    if not (os.path.isfile(pdf) and os.path.isfile(key)):
        pytest.skip("Không có cặp kqkd_6t.pdf / KQKD_6T.xls trong corpus")
    ocr.configure_tesseract()
    if not ocr.has_vietnamese():
        pytest.skip("Tesseract chưa có gói tiếng Việt (vie)")

    exp = groundtruth.read_statement(key)
    # tự vệ: đáp án phải đúng như chẩn đoán đã soát tay, nếu không thì test
    # này đang đo trên key khác (đừng đổ oan cho parser)
    assert metrics._norm_map(exp)["1"] == (22730333061, 20761958628)

    res = engine.convert_pdf(pdf, str(tmp_path))
    got = res["results"]["KQHDKD"]
    a = metrics._norm_map(got)

    # Trước fix: got['1'] == (20761958628, 22730333061) — hoán vị hoàn hảo.
    assert a.get("1") == (22730333061, 20761958628), (
        "mã 01 vẫn chọn sai cặp cột: got=%r (hoán vị = còn lấy (Kỳ trước, "
        "Lũy kế))" % (a.get("1"),))

    # 24 ô từng lệch (hoán vị) phải quay về đúng >= 15 ô; trước fix dung=0.
    c = metrics.compare(exp, got)
    assert c["dung"] >= 15, "chỉ đúng %(dung)d ô (lệch %(lech)d, sót %(sot)d)" % c
    assert c["lech"] <= 5, "còn lệch %(lech)d ô — cặp cột vẫn sai?" % c
