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


# ---------------------------------------------------------------------------
# Defect 3: _find_columns_fallback từng LUÔN coi cột giá trị bên TRÁI là năm
# nay ('cur_col, prior_col = sorted(value_cols[:2])'), bất kể nhãn tiêu đề
# thật sự nói gì. File thật xác nhận điều ngược lại: 'Luu chuyen tien te
# 2015.xls' (Cty CP DL KS Tháng Mười, Quý 4/2015) có nhãn tiêu đề ĐỌC ĐƯỢC
# 'Kỳ trước' | 'Kỳ này' với cột TRÁI lại là Kỳ trước — 2 năm bị hoán đổi lặng
# lẽ, không raise lỗi, không cảnh báo. Từ nay khi nhãn tiêu đề còn đọc được
# và xác định rõ đâu là năm nay/năm trước, nhãn phải THẮNG vị trí; chỉ rơi về
# mặc định trái=năm nay khi nhãn mojibake/thiếu/mơ hồ.
# ---------------------------------------------------------------------------
def _rows_nhan_doc_duoc_ky_truoc_ky_nay():
    """
    Mô phỏng đúng cấu trúc file LCTT thật đã xác nhận trên corpus: nhãn tiêu
    đề ĐỌC ĐƯỢC 'Kỳ trước' | 'Kỳ này' (không mojibake), KHÔNG có hàng đánh số
    cột, và — giống hệt file thật — cột TRÁI là Kỳ trước chứ không phải Kỳ
    này.
    """
    return [
        ["Chỉ tiêu", "MS", "Kỳ trước", "Kỳ này"],
        ["I. Lưu chuyển tiền từ hoạt động SXKD", "", 0, 0],
        ["1. Tiền thu từ bán hàng, cung cấp dịch vụ", "01", 1000, 31000000],
        ["2. Tiền chi trả cho người cung cấp", "02", 2000, 13000000],
        ["3. Tiền chi trả cho người lao động", "03", 3000, 7000000],
        ["4. Tiền chi trả lãi vay", "04", 4000, 100000],
        ["5. Tiền chi nộp thuế TNDN", "05", 5000, 0],
        ["6. Tiền thu khác từ hoạt động kinh doanh", "06", 6000, 1000000],
    ]


def test_find_columns_nhan_doc_duoc_thang_vi_tri():
    """Nhãn 'Kỳ trước' | 'Kỳ này' còn đọc được -> cột năm nay là cột BÊN
    PHẢI (chỉ số LỚN HƠN cột năm trước), dù mặc định vị trí (trái = năm nay)
    sẽ chọn NGƯỢC LẠI nếu chỉ nhìn hình dạng ô."""
    rows = _rows_nhan_doc_duoc_ky_truoc_ky_nay()
    found = G._find_columns(rows)
    assert found is not None
    hdr_row, code_col, cur_col, prior_col = found
    assert cur_col > prior_col, (
        "nhãn tiêu đề phải thắng vị trí: 'Kỳ này' nằm bên phải 'Kỳ trước' "
        "trong dữ liệu giả lập này nhưng dò được cur_col=%d, prior_col=%d"
        % (cur_col, prior_col)
    )
    assert (hdr_row, code_col, cur_col, prior_col) == (1, 1, 3, 2)


def test_find_columns_mojibake_giu_thu_tu_vi_tri_mac_dinh():
    """Companion của test trên: nhãn mojibake ('N¨m nay' / 'N¨m tr­íc') không
    khớp mốc nào -> không có tín hiệu chữ đáng tin -> GIỮ mặc định vị trí
    (trái = năm nay), y hệt hành vi trước khi sửa Defect 3."""
    rows = _rows_khong_co_hang_danh_so()
    found = G._find_columns(rows)
    assert found is not None
    hdr_row, code_col, cur_col, prior_col = found
    assert cur_col < prior_col
    assert (hdr_row, code_col, cur_col, prior_col) == (2, 1, 3, 4)
    # Đối chiếu thẳng cách quyết định, không chỉ suy luận qua thứ tự chỉ số.
    _, _, _, _, column_order = G._find_columns_fallback(rows)
    assert column_order == "positional"


def test_statement_detail_bao_cao_dung_strategy_va_column_order(tmp_path):
    """statement_detail() phải lộ đúng provenance cho cả 2 nhánh dò cột:
    hàng đánh số (strategy='numbering' -> luôn column_order='positional' vì
    nhánh này không đọc nhãn chữ) và dự phòng hình học có nhãn đọc được
    (strategy='fallback' -> column_order='labels')."""
    import openpyxl

    numbering_path = tmp_path / "numbering.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in [
        ["CÔNG TY CỔ PHẦN ABC", None, None, None, None],
        ["BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH", None, None, None, None],
        ["Chỉ tiêu", "Mã số", "TM", "Năm nay", "Năm trước"],
        [1, 2, 3, 4, 5],
        ["Doanh thu bán hàng", 1, "VI.25", 52000000, 41000000],
    ]:
        ws.append(row)
    wb.save(numbering_path)

    labels_path = tmp_path / "labels.xlsx"
    wb2 = openpyxl.Workbook()
    ws2 = wb2.active
    for row in _rows_nhan_doc_duoc_ky_truoc_ky_nay():
        ws2.append(row)
    wb2.save(labels_path)

    numbering_detail = G.statement_detail(str(numbering_path))
    assert numbering_detail["strategy"] == "numbering"
    assert numbering_detail["column_order"] == "positional"
    assert numbering_detail["values"]["1"] == (52000000, 41000000)
    assert numbering_detail["values"] == G.read_statement(str(numbering_path))

    labels_detail = G.statement_detail(str(labels_path))
    assert labels_detail["strategy"] == "fallback"
    assert labels_detail["column_order"] == "labels"
    assert labels_detail["values"]["01"] == (31000000, 1000)
    assert labels_detail["values"] == G.read_statement(str(labels_path))


# ---------------------------------------------------------------------------
# Đối chiếu trực tiếp trên file corpus thật đã xác nhận bị đảo năm (xem đầu
# khối Defect 3 ở trên). Đường dẫn tương đối tính từ BCTC_CORPUS; tự skip nếu
# máy không có corpus hoặc không có đúng file này.
# ---------------------------------------------------------------------------
_SWAPPED_YEAR_REL_PATH = (
    "BTG document/BCTC 10/2015/Quy 4.2015/"
    "21_Cty CP DL KS Thang Muoi_BCTC 2015/Luu chuyen tien te 2015.xls"
)


def test_statement_detail_doi_chieu_file_that_bi_dao_nam(corpus_root):
    """
    File thật: nhãn tiêu đề CÒN ĐỌC ĐƯỢC 'Kỳ trước' | 'Kỳ này' nhưng cột TRÁI
    lại là Kỳ trước — ngược mặc định trái = năm nay. Trước khi sửa Defect 3,
    read_statement() trả về vals['01'] == (0, 31023721511): 2 năm bị đảo hoàn
    toàn mà không có bất kỳ exception hay cảnh báo nào.
    """
    path = os.path.join(corpus_root, *_SWAPPED_YEAR_REL_PATH.split("/"))
    if not os.path.isfile(path):
        pytest.skip("Không có file corpus: %s" % _SWAPPED_YEAR_REL_PATH)
    vals = G.read_statement(path)
    assert vals["01"] == (31023721511, 0)
    detail = G.statement_detail(path)
    assert detail["column_order"] == "labels"
    assert detail["values"] == vals
