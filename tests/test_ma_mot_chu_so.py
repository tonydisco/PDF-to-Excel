# -*- coding: utf-8 -*-
"""
V6 việc #3 — §7.1 (thu hẹp): find_code_at chấp nhận mã in 1 chữ số ('1'->'01')
CHỈ ở đúng cột mã đã dò. KHÔNG đụng detect_code_column (chẩn đoán chứng minh nới
ở đó bắt nhầm cột SỐ THỨ TỰ). Guard: chưa dò được cột (col_center=None) thì giữ
strict; '1' lạc ở cột số thứ tự (cx khác hẳn) không lọt vì d > tol.
"""
from bctc import parser


def _w(text, cx):
    return {"text": text, "cx": cx, "right": cx + 0.02, "cy": 0.5}


# ---- _canon_ma_mot_chu_so ----
def test_canon_chi_ma_1_chu_so_va_co_trong_khung():
    valid = {"01", "02", "10"}
    assert parser._canon_ma_mot_chu_so("1", valid) == "01"
    assert parser._canon_ma_mot_chu_so("2", valid) == "02"
    assert parser._canon_ma_mot_chu_so("2.", valid) == "02"   # bỏ chấm cuối
    assert parser._canon_ma_mot_chu_so("3", valid) is None    # '03' không trong khung
    assert parser._canon_ma_mot_chu_so("10", valid) is None   # đã 2 chữ số
    assert parser._canon_ma_mot_chu_so("0", valid) is None    # '00' không phải mã
    assert parser._canon_ma_mot_chu_so("a", valid) is None


# ---- find_code_at ----
def test_ma_1_chu_so_map_tai_cot_ma():
    valid = {"01", "02", "10", "20"}
    # nhãn (trái) + mã '1' ở cột mã (cx ~0.43) + giá trị (phải)
    words = [_w("Doanh", 0.10), _w("thu", 0.15), _w("1", 0.43), _w("22.730", 0.66)]
    assert parser.find_code_at(words, valid, 0.43) == "01"


def test_stray_1_o_cot_so_thu_tu_khong_map():
    valid = {"01", "02", "10", "20"}
    # cột mã đã dò ở x=0.43; '1' lạc ở cột SỐ THỨ TỰ x=0.05 -> quá xa, bị loại
    words = [_w("1", 0.05), _w("Doanh", 0.10), _w("thu", 0.15), _w("22.730", 0.66)]
    assert parser.find_code_at(words, valid, 0.43) is None


def test_phan_biet_cot_ma_va_cot_so_thu_tu_cung_dong():
    valid = {"01", "02", "10", "20"}
    # '1' số thứ tự ở 0.05 (loại) VÀ mã thật '1'(->01) ở cột mã 0.43 (nhận)
    words = [_w("1", 0.05), _w("Doanh", 0.10), _w("1", 0.43), _w("22.730", 0.66)]
    assert parser.find_code_at(words, valid, 0.43) == "01"


def test_guard_col_center_none_khong_noi_mot_chu_so():
    # Chưa dò được cột mã -> giữ strict (find_code với _token_code chuỗi chính xác)
    valid = {"01", "02"}
    words = [_w("1", 0.43), _w("22.730", 0.66)]
    assert parser.find_code_at(words, valid, None) is None


def test_ma_2_chu_so_van_hoat_dong_binh_thuong():
    valid = {"01", "02", "10", "20"}
    words = [_w("Loi", 0.10), _w("nhuan", 0.15), _w("20", 0.43), _w("999", 0.66)]
    assert parser.find_code_at(words, valid, 0.43) == "20"
