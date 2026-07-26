# -*- coding: utf-8 -*-
"""
Tự sửa lỗi OCR 1 chữ số ở Ô TỔNG bằng phương trình cân đối của Bảng cân đối
kế toán. Hoàn toàn THUẦN PDF: "đáp án" là nội tại của bảng (270=440,
100+200=270, 300+400=440), không dùng bất kỳ file Excel/Word đối chiếu nào.

Đây là phần LÕI LOGIC (khoanh ô lệch + cổng 1-chữ-số). Phần re-OCR ô đó trên
ảnh PDF ở DPI cao là bước sau, có test corpus riêng.
"""
from bctc import parser as P


def _cdkt(**kw):
    """Dựng dict CĐKT {code: (cuối, đầu)} chỉ từ giá trị cột 'cuối'."""
    return {k: (v, None) for k, v in kw.items()}


def test_khoanh_o_270_sai_khi_hai_ve_kia_khop():
    # 100+200 = 40+60 = 100 = 440; nhưng 270 đọc thành 900 -> đúng phải 100
    cdkt = _cdkt(**{"100": 40, "200": 60, "270": 900,
                    "300": 30, "400": 70, "440": 100})
    assert P.khoanh_o_lech_can_doi(cdkt, 0) == ("270", 100)


def test_khoanh_o_440_sai():
    cdkt = _cdkt(**{"100": 40, "200": 60, "270": 100,
                    "300": 30, "400": 70, "440": 900})
    assert P.khoanh_o_lech_can_doi(cdkt, 0) == ("440", 100)


def test_khoanh_thanh_phan_200_sai():
    # 270 tin cậy (==440, và 300+400==440); 100+200 lệch; chỉ 200 bù được
    # đúng 1 chữ số (68->63), còn 100 phải đổi 2 chữ số -> khoanh 200.
    cdkt = _cdkt(**{"100": 40, "200": 68, "270": 103,
                    "300": 50, "400": 53, "440": 103})
    assert P.khoanh_o_lech_can_doi(cdkt, 0) == ("200", 63)


def test_khong_khoanh_khi_hai_thanh_phan_deu_bu_duoc():
    # 100+200 lệch nhưng CẢ HAI thành phần đều bù được 1 chữ số -> nhập nhằng
    cdkt = _cdkt(**{"100": 40, "200": 60, "270": 100,
                    "300": 30, "400": 70, "440": 100})
    # 100 đọc nhầm thành 10 (đúng phải 40): 100+200=70!=100. target_100=40
    # (10->40, 1 số), target_200=90 (60->90, 1 số) -> cả hai -> None
    cdkt["100"] = (10, None)
    assert P.khoanh_o_lech_can_doi(cdkt, 0) is None


def test_khong_khoanh_khi_da_can_doi():
    cdkt = _cdkt(**{"100": 40, "200": 60, "270": 100,
                    "300": 30, "400": 70, "440": 100})
    assert P.khoanh_o_lech_can_doi(cdkt, 0) is None


def test_khong_khoanh_khi_thieu_so():
    cdkt = _cdkt(**{"100": 40, "270": 900, "440": 100})
    assert P.khoanh_o_lech_can_doi(cdkt, 0) is None


def test_khoanh_theo_dung_cot_nam():
    # cột đầu (idx=1) lệch, cột cuối (idx=0) khớp -> chỉ khoanh ở cột đầu
    cdkt = {"100": (40, 40), "200": (60, 60), "270": (100, 900),
            "300": (30, 30), "400": (70, 70), "440": (100, 100)}
    assert P.khoanh_o_lech_can_doi(cdkt, 0) is None
    assert P.khoanh_o_lech_can_doi(cdkt, 1) == ("270", 100)


def test_khe_mot_chu_so_nhan_ca_lech_thuc_te():
    assert P.khe_mot_chu_so(172125135754, 172125735754) is True   # 1 -> 7
    assert P.khe_mot_chu_so(40586123955, 49586123955) is True     # 0 -> 9
    assert P.khe_mot_chu_so(100, 900) is True
    assert P.khe_mot_chu_so(100, 110) is True


def test_khe_mot_chu_so_loai_lech_lon():
    assert P.khe_mot_chu_so(100, 999) is False        # khác 3 chữ số
    assert P.khe_mot_chu_so(100, 1000) is False       # khác số chữ số
    assert P.khe_mot_chu_so(None, 100) is False
