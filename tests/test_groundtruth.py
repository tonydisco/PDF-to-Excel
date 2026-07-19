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


# ---------------------------------------------------------------------------
# Defect 1: _to_int từng vỡ (ValueError) trên chuỗi có dấu gạch ngang Ở GIỮA
# (ngày tháng dạng '2023-12-31', 'Ngày 30-06-2025'...). 98/135 file đáp án
# thật chết vì lỗi này. Dấu âm chỉ được nhận theo '-' ở ĐẦU chuỗi hoặc dạng
# ngoặc đơn '(...)'; độ lớn luôn trích riêng từ ký tự \d.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    # Các ca bắt buộc theo yêu cầu sửa lỗi
    ("31/12/2023", 31122023),
    ("2023-12-31", 20231231),
    ("Ngày 30-06-2025", 30062025),
    ("1.234.567", 1234567),
    ("(1.234)", -1234),
    ("-1.234", -1234),
    ("-", None),
    ("", None),
    ("abc", None),
    # Giữ nguyên hành vi cũ cho None / bool / int / float
    (None, None),
    (True, None),
    (False, None),
    (5, 5),
    (5.6, 6),
    (-5.4, -5),
    (0, 0),
])
def test_to_int_khong_vo_voi_dau_gach_ngang_o_giua(raw, expected):
    assert G._to_int(raw) == expected


# ---------------------------------------------------------------------------
# Defect 2: _find_columns trước đây CHỈ dò được cột nếu có hàng đánh số thứ
# tự '1','2','3','4'. 27/135 file (đo trên baseline cũ, lẫn cả phần bị Defect
# 1 che khuất) không có hàng đó và vỡ ValueError. Test dưới đây dựng dữ liệu
# trong bộ nhớ (không hàng đánh số) để buộc _find_columns phải rơi xuống
# nhánh dự phòng hình học (_find_columns_fallback), theo đúng khuyến nghị của
# yêu cầu: kiểm _find_columns bằng list-of-lists, không tạo file Excel.
# ---------------------------------------------------------------------------
def _rows_khong_co_hang_danh_so():
    """Bảng KQKD giả lập: nhãn tiêu đề mojibake, KHÔNG có hàng đánh số cột."""
    return [
        ["CÔNG TY CỔ PHẦN ABC", None, None, None, None],
        ["BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH", None, None, None, None],
        ["Chỉ tiêu", "M· sè", "TM", "N¨m nay", "N¨m tr­íc"],
        ["Doanh thu bán hàng và cung cấp dịch vụ", "01", "VI.25", 52000000, 41000000],
        ["Các khoản giảm trừ doanh thu", "02", "", 2000, 1500],
        ["Doanh thu thuần", "10", "", 50000000, 39500000],
        ["Giá vốn hàng bán", "11", "VI.26", 31000000, 26000000],
        ["Lợi nhuận gộp", "20", "", 19000000, 13500000],
        ["Chi phí tài chính", "22b", "", 300, 250],
    ]


def test_find_columns_du_phong_khi_khong_co_hang_danh_so():
    """Không có hàng '1,2,3,4' -> phải rơi xuống dự phòng hình học và dò đúng."""
    rows = _rows_khong_co_hang_danh_so()
    found = G._find_columns(rows)
    assert found is not None
    hdr_row, code_col, cur_col, prior_col = found
    # Cột 1 = mã số ('01'..'22b'), cột 3 = năm nay, cột 4 = năm trước.
    # Cột 2 (Thuyết minh, 'VI.25'/'VI.26') không được lẫn vào cột giá trị.
    assert (hdr_row, code_col, cur_col, prior_col) == (2, 1, 3, 4)
    # hàng tiêu đề = ngay trước hàng dữ liệu đầu tiên có mã số
    assert rows[hdr_row][0] == "Chỉ tiêu"


def test_find_columns_du_phong_that_bai_khi_qua_it_ma_so():
    """Dưới 5 ô khớp mã số -> dự phòng phải chịu thua (trả về None)."""
    rows = _rows_khong_co_hang_danh_so()
    # Chỉ còn 3 ô mã số hợp lệ (dòng 3,4,5), xoá mã ở 3 dòng còn lại.
    for i in (6, 7, 8):
        rows[i][1] = None
    assert G._find_columns(rows) is None


def test_find_columns_du_phong_that_bai_khi_thieu_cot_gia_tri():
    """Có đủ cột mã số nhưng chỉ 1 cột giá trị đạt ngưỡng -> thất bại."""
    rows = _rows_khong_co_hang_danh_so()
    # Dìm mọi giá trị ở cột "năm trước" xuống dưới ngưỡng 1000.
    for i in range(3, 9):
        rows[i][4] = 5
    assert G._find_columns(rows) is None


# ---------------------------------------------------------------------------
# Test đo tỉ lệ thành công trên corpus thật — mục tiêu của cả hai lần sửa
# lỗi ở trên. Trước khi sửa: ~10/135 (~7%). Trần 60 file đầu (đã sắp xếp ổn
# định theo đường dẫn, không phụ thuộc thứ tự trả về của glob) để test chạy
# nhanh; tự skip nếu máy không có corpus thật (biến BCTC_CORPUS).
# ---------------------------------------------------------------------------
_CORPUS_EXTS = (".xls", ".xlsx")
_CORPUS_SAMPLE_CAP = 60
_MIN_SUCCESS_RATE = 0.6


def test_read_statement_ty_le_thanh_cong_tren_corpus(corpus_root):
    """read_statement() phải đọc thành công > 60% số file đáp án nhận diện được."""
    all_paths = glob.glob(os.path.join(corpus_root, "**", "*"), recursive=True)
    recognized = sorted(
        p for p in all_paths
        if os.path.isfile(p)
        and os.path.splitext(p)[1].lower() in _CORPUS_EXTS
        and G.statement_kind(p)
    )
    if not recognized:
        pytest.skip("Không tìm thấy file báo cáo nào trong corpus")

    sample = recognized[:_CORPUS_SAMPLE_CAP]
    ok = 0
    for p in sample:
        try:
            vals = G.read_statement(p)
        except Exception:
            continue
        if vals:
            ok += 1

    rate = ok / len(sample)
    assert rate > _MIN_SUCCESS_RATE, (
        "Tỉ lệ đọc thành công chỉ %.1f%% (%d/%d file) — chưa vượt ngưỡng %.0f%%"
        % (rate * 100, ok, len(sample), _MIN_SUCCESS_RATE * 100)
    )
