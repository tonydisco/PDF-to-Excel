# -*- coding: utf-8 -*-
import pytest

from tests.regression import build_pairs as B


def test_company_index_chi_lay_tu_ten_thu_muc():
    """Cạm bẫy chính: số đầu TÊN FILE không phải mã công ty."""
    p = "/x/Quy 2.2025/27_Cty CP SXKD Hang XK Tan Binh 6Th_2025/1 Can doi ke toan.xlsx"
    assert B.company_index(p) == "27"      # KHÔNG được ra '1'


def test_company_index_bo_so_khong_dung_dau():
    assert B.company_index("/x/01_CTCP DVTH Saigon/CDKT.XLS") == "1"


def test_company_index_rong_khi_khong_co():
    assert B.company_index("/x/BCTC 2023/CDKT.XLS") == ""


def test_period_nhan_dien():
    assert B.period("/x/27_Cty 6Th_2025/1 Can doi ke toan 06 thang dau 2025.xlsx") == "6T"
    assert B.period("/x/QUY II.2022/CDKT Q2.xls") == "Q2"
    assert B.period("/x/2024/CDKT.XLS") == "NAM"


def test_year_lay_nam_cuoi_cung():
    assert B.year("/x/BCTC 2023/Quy 2/CDKT 2024.xls") == "2024"
    assert B.year("/x/khong co nam/CDKT.xls") == ""


def test_build_khong_ghep_khac_cong_ty(corpus_root):
    """Mọi cặp sinh ra phải cùng mã công ty, cùng năm, cùng kỳ."""
    pairs = B.build(corpus_root)
    assert pairs, "Không sinh được cặp nào"
    for p in pairs:
        assert B.company_index(p["excel"]) == p["company"]
        assert B.year(p["pdf"]) == p["year"]
        assert B.period(p["pdf"]) == p["period"]
