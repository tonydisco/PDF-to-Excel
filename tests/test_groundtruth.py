# -*- coding: utf-8 -*-
import os
import glob
import pytest

from tests.regression import groundtruth as G


def test_statement_kind_nhan_dien_theo_ten_file():
    assert G.statement_kind("CDKT.XLS") == "CDKT"
    assert G.statement_kind("KQKD.XLS") == "KQHDKD"
    assert G.statement_kind("LCTT.XLS") == "LCTT"
    assert G.statement_kind("CDSPS.XLS") == "CDPS"
    assert G.statement_kind("1 Can doi ke toan 06 thang dau 2025.xlsx") == "CDKT"
    assert G.statement_kind("3 KQKD 6 thang 2025.xlsx") == "KQHDKD"
    assert G.statement_kind("4 LCTT truc tiep 06 thang 2025.xlsx") == "LCTT"
    assert G.statement_kind("BCTC 2019.pdf") == ""


def test_sniff_format_khong_tin_duoi_file(corpus_root):
    """KQKD.XLS thực chất là OOXML - đuôi file nói dối."""
    hits = glob.glob(os.path.join(corpus_root, "**", "KQKD.XLS"), recursive=True)
    if not hits:
        pytest.skip("Không có file KQKD.XLS trong corpus")
    assert G.sniff_format(hits[0]) == "ooxml"


def test_read_statement_boc_dung_ma_so_va_gia_tri(corpus_root):
    """Đối chiếu với giá trị đã xác minh bằng mắt của Cty CP Du Lịch Đăk Lăk 2023."""
    # Lọc thêm "2023": corpus có từ 2 file KQKD.XLS trở lên chứa "Dak Lak"
    # (vd. báo cáo 2024 của cùng công ty). Nếu chỉ lọc theo "Dak Lak", glob
    # trả về thứ tự không đảm bảo nên hits[0] có thể là file SAI NĂM - các
    # giá trị bên dưới chỉ đúng với báo cáo 2023 đã xác minh bằng mắt.
    hits = [p for p in glob.glob(os.path.join(corpus_root, "**", "KQKD.XLS"),
                                 recursive=True) if "Dak Lak" in p and "2023" in p]
    if not hits:
        pytest.skip("Không có file KQKD.XLS của Đăk Lăk")
    vals = G.read_statement(hits[0])
    # Mã số in trong báo cáo là '1', '2' (KHÔNG phải '01', '02')
    assert vals["1"] == (23752205505, 21874564189)   # Doanh thu bán hàng
    assert vals["10"] == (23752205505, 21874564189)  # Doanh thu thuần
    assert vals["11"] == (19410766207, 16239369636)  # Giá vốn hàng bán
    assert vals["50"] == (-2677527567, -1184043693)  # Tổng lợi nhuận trước thuế
    assert vals["70"] == (0, 0)                      # Lãi cơ bản trên cổ phiếu
