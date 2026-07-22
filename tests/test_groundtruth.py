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


# ---------------------------------------------------------------------------
# Defect 5: mẫu 'bang can doi' của CDKT quá lỏng — 'bang can doi tai khoan
# 2016.xls' là bảng cân đối THỬ trên tài khoản (111, 112, 131... 911), tức
# CDPS, nhưng từng bị dán nhãn CDKT (bảng cân đối kế toán, mã 100-440). Ghép
# nhầm hai loại này vào bộ hồi quy sẽ biến sai số ĐO thành sai số TRÍCH XUẤT.
# Từ nay: 'bảng cân đối tài khoản' và 'bảng cân đối số phát sinh' là CDPS;
# chỉ 'cân đối kế toán' (và chữ tắt 'cdkt') mới là CDKT.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("filename,expected", [
    ("bang can doi tai khoan 2016.xls", "CDPS"),
    ("Bang can doi so phat sinh 2020.xls", "CDPS"),
    ("CDSPS.XLS", "CDPS"),
    ("2. Bang can doi ke toan 2023.xlsx", "CDKT"),
    ("CDKT.XLS", "CDKT"),
    ("cdkt_30.06.2024.xls", "CDKT"),
])
def test_statement_kind_phan_biet_can_doi_tai_khoan_va_ke_toan(filename, expected):
    assert G.statement_kind(filename) == expected


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


# ---------------------------------------------------------------------------
# Defect 4: _year_marker() xét _CUR_YEAR_MARKERS TRƯỚC _PRIOR_YEAR_MARKERS
# bằng containment thuần, không có bước phát hiện nhập nhằng. Nhiều mốc năm
# nay lại là tiền tố của cụm tiếng Việt tự nhiên nói về năm TRƯỚC (vd. "Số dư
# cuối năm trước" chứa "cuối năm" - mốc năm nay - nhưng cả câu là năm trước;
# "Cuối kỳ trước" chứa "cuối kỳ" - mốc năm nay - nhưng cả câu cũng là năm
# trước). _year_marker() từng trả 'current' một cách TỰ TIN nhưng SAI cho các
# câu này, khiến _order_by_header_labels gán nhầm cột và _find_columns_fallback
# còn báo column_order == "labels" - tức đánh dấu câu trả lời sai là đáng tin
# hơn cả "positional". Từ nay: khớp CẢ HAI danh sách -> nhập nhằng -> trả về
# None, không đoán đại một phía; bên gọi phải rơi về mặc định vị trí thay vì
# đoán liều một kết quả sai mà tự tin.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("text,expected", [
    ("Kỳ này", "current"),
    ("Kỳ trước", "prior"),
    ("Năm nay", "current"),
    ("Năm trước", "prior"),
    ("Số cuối năm", "current"),
    ("Số đầu năm", "prior"),
    ("Số dư cuối năm trước", None),  # chứa "cuối năm" LẪN "năm trước" -> nhập nhằng
    ("Cuối kỳ trước", None),         # chứa "cuối kỳ" LẪN "kỳ trước" -> nhập nhằng
    ("Năm nay và năm trước", None),  # cả 2 cụm cùng có mặt -> nhập nhằng
    ("Chỉ tiêu", None),              # không khớp danh sách nào
    ("", None),                      # chuỗi rỗng
])
def test_year_marker_nhap_nhang_tra_ve_none(text, expected):
    assert G._year_marker(text) == expected


# ---------------------------------------------------------------------------
# Defect 6 (Đợt 2): hàng đánh số '1..5' nằm trên Ô MERGE nên marker '4'/'5'
# có thể lệch 1 cột so với cột giá trị thật. Ba file thật đã xác nhận (xem
# .superpowers/sdd/dot2-chan-doan-report.md §4):
#   - 'KQKD_2023.xls' (SGMN 2023): marker '4','5' ở c9/c11 nhưng giá trị ở
#     c8/c10 -> key 20 mã bị đọc thành toàn (None, None), 14 ô parser trích
#     ĐÚNG bị đếm "thừa".
#   - 'cdkt_6t.xls' (SGMN 6T/2025) và 'CDKT Q2.xls' (SGMN Q2/2022): marker
#     '5' ở cột RỖNG (c12/c9), cột Kỳ-trước thật ở kề trái (c11/c8) -> mất
#     NGUYÊN cột năm trước (~47-115 ô đáp án mỗi file).
# Từ nay: sau khi neo cột theo hàng đánh số phải XÁC MINH cột được chọn có ô
# số thật trên các hàng có mã; cột rỗng thì dò 2 cột kề (trái/phải), lấy cột
# nhiều ô số hơn, hoà thì ưu tiên TRÁI (bằng chứng corpus: marker merge nằm
# bên phải cột giá trị).
# ---------------------------------------------------------------------------
def _rows_hang_danh_so_marker_lech_phai_do_merged_cell():
    """
    Mô phỏng thu nhỏ KQKD_2023.xls: numbering row có marker '4' ở c9 và '5' ở
    c11 (ô merge), trong khi giá trị Kỳ này/Kỳ trước thật nằm ở c8/c10; c9 và
    c11 rỗng hoàn toàn; c12 là cột Lũy kế (trùng Kỳ này) để chốt rằng bộ đọc
    phải ưu tiên cột kề TRÁI chứ không vồ cột phải.
    """
    return [
        ["KÕt qu¶ ho¹t ®éng kinh doanh"] + [None] * 13,
        ["ChØ tiªu", None, None, None, None, None, "M· sè", "TM",
         "Kú nµy", None, "Kú tr\xadíc", None, "Lòy kÕ", None],
        [None, 1, None, None, None, None, 2, 3, None, 4, None, 5, None, None],
        ["1. Doanh thu", None, None, None, None, None, "01", None,
         52000000, None, 41000000, None, 52000000, None],
        ["2. Gi¶m trõ", None, None, None, None, None, "02", None,
         0, None, 0, None, 0, None],
        ["3. Doanh thu thuÇn", None, None, None, None, None, "10", None,
         52000000, None, 41000000, None, 52000000, None],
        ["4. Gi¸ vèn", None, None, None, None, None, "11", None,
         31000000, None, 26000000, None, 31000000, None],
        ["5. Lîi nhuËn gép", None, None, None, None, None, "20", None,
         21000000, None, 15000000, None, 21000000, None],
    ]


def test_find_columns_hang_danh_so_marker_lech_phai_do_merged_cell():
    """Marker '4'/'5' trỏ vào cột rỗng -> phải dò sang cột kề trái có số thật
    (c8/c10), không được trả về cặp cột rỗng làm key thành toàn (None, None)."""
    rows = _rows_hang_danh_so_marker_lech_phai_do_merged_cell()
    found = G._find_columns(rows)
    assert found is not None
    hdr_row, code_col, cur_col, prior_col = found
    assert (hdr_row, code_col) == (2, 6)
    assert (cur_col, prior_col) == (8, 10), (
        "marker lệch cột do merged cell: kỳ vọng dò ra cột giá trị thật "
        "(8, 10) nhưng được (%d, %d)" % (cur_col, prior_col)
    )


def _rows_hang_danh_so_marker_lech_trai_canh_thuyet_minh():
    """
    Đối xứng gương của ca trên: marker '4' nằm bên TRÁI cột giá trị thật (c3
    rỗng, giá trị ở c4), và cột kề trái của marker là Thuyết minh THƯA ('VI.25'
    -> _to_int ra 25 nên vẫn đếm là "ô số"). Bộ đọc phải chọn cột kề có NHIỀU
    ô số hơn (c4, đủ 5/5 hàng) chứ không vồ ngay cột trái thưa.
    """
    return [
        ["ChØ tiªu", "M· sè", "TM", "Kú nµy", None, "Kú tr\xadíc", None],
        [1, 2, 3, 4, None, 5, None],
        ["1. Doanh thu", "01", "VI.25", None, 52000000, 41000000, None],
        ["2. Gi¶m trõ", "02", None, None, 1000, 2000, None],
        ["3. Doanh thu thuÇn", "10", "VI.26", None, 51000000, 39000000, None],
        ["4. Gi¸ vèn", "11", None, None, 31000000, 26000000, None],
        ["5. Lîi nhuËn", "20", None, None, 20000000, 13000000, None],
    ]


def test_find_columns_hang_danh_so_marker_lech_trai_chon_cot_nhieu_so_hon():
    rows = _rows_hang_danh_so_marker_lech_trai_canh_thuyet_minh()
    found = G._find_columns(rows)
    assert found is not None
    hdr_row, code_col, cur_col, prior_col = found
    assert (hdr_row, code_col) == (1, 1)
    assert (cur_col, prior_col) == (4, 5), (
        "cột kề phải (c4, 5/5 ô số) phải thắng cột Thuyết minh thưa bên trái "
        "(c2, 2/5 ô số) nhưng dò được (%d, %d)" % (cur_col, prior_col)
    )


# ---------------------------------------------------------------------------
# Defect 7 (Đợt 2): bảng 4 cột giá trị theo NHÓM header (Trong kỳ nay/trước +
# Lũy kế nay/trước — file thật '18_Cty TNHH Ben Thanh Hoang Thanh_BCTC
# Q2.2016_KQKD.xls'). Dự phòng hình học cũ lấy "2 cột nhiều số nhất" nên vồ
# trúng 2 cột Năm-Trước (chúng có NHIỀU ô số hơn vì vài dòng chỉ có số năm
# trước) -> key thành (prior, prior), 9 ô parser trích ĐÚNG bị chấm lệch.
# Từ nay: khi nhãn còn đọc được và có cả cột năm-nay lẫn cột năm-trước trong
# các ứng viên, phải ghép cặp THEO NHÃN (cột năm nay nhiều số nhất + cột năm
# trước gần nó nhất — tức cùng nhóm), không lấy 2 cột nhiều số nhất xuyên nhóm.
# ---------------------------------------------------------------------------
def _rows_bon_cot_nhom_trong_ky_luy_ke():
    """Mô phỏng thu nhỏ file BTHT: 2 nhóm (Trong kỳ | Lũy kế), mỗi nhóm 2 cột
    Năm nay/Năm Trước; 2 dòng ('31', '40') chỉ có số năm trước nên 2 cột
    Năm-Trước đếm được NHIỀU ô số hơn 2 cột Năm-nay."""
    return [
        ["CHỈ TIÊU", "Mã số", "Thuyết minh", "Trong kỳ", None,
         "Lũy kế từ đầu năm", None],
        [None, None, None, "Năm nay", "Năm Trước", "Năm nay", "Năm Trước"],
        ["1. Doanh thu", "01", None, 8852241816, 7940375454, 8852241816, 7940375454],
        ["3. Doanh thu thuần", "10", None, 8852241816, 7940375454, 8852241816, 7940375454],
        ["4. Giá vốn", "11", None, 2148768000, 2148768000, 2148768000, 2148768000],
        ["5. LN gộp", "20", None, 6703473816, 5791607454, 6703473816, 5791607454],
        ["11. Thu nhập khác", "31", None, None, 10000000, None, 10000000],
        ["13. LN khác", "40", None, None, 10000000, None, 10000000],
        ["17. LN sau thuế", "60", None, 4938168598, 4295436466, 4938168598, 4295436466],
    ]


def test_find_columns_du_phong_bon_cot_ghep_cap_theo_nhom_header():
    """2 cột nhiều số nhất là c4+c6 (đều 'Năm Trước') nhưng nhãn còn đọc được
    -> phải ghép cặp (c3 năm nay, c4 năm trước) cùng nhóm Trong kỳ, và báo
    column_order='labels'."""
    rows = _rows_bon_cot_nhom_trong_ky_luy_ke()
    found = G._find_columns_fallback(rows)
    assert found is not None
    hdr_row, code_col, cur_col, prior_col, column_order = found
    assert (code_col, cur_col, prior_col) == (1, 3, 4), (
        "kỳ vọng cặp (năm nay=3, năm trước=4) cùng nhóm 'Trong kỳ' nhưng dò "
        "được cur=%d, prior=%d" % (cur_col, prior_col)
    )
    assert column_order == "labels"


def test_find_columns_du_phong_bon_cot_khong_nhan_giu_duong_cu():
    """Companion: cùng bố cục 4 cột nhưng nhãn mojibake (không đọc được) ->
    giữ nguyên đường cũ '2 cột nhiều số nhất' + mặc định vị trí."""
    rows = _rows_bon_cot_nhom_trong_ky_luy_ke()
    rows[0][3] = "Trong kú"
    rows[0][5] = "Lòy kÕ tõ ®Çu n¨m"
    rows[1][3] = "N¨m nay"
    rows[1][4] = "N¨m tr\xadíc"
    rows[1][5] = "N¨m nay"
    rows[1][6] = "N¨m tr\xadíc"
    found = G._find_columns_fallback(rows)
    assert found is not None
    _, code_col, cur_col, prior_col, column_order = found
    assert (code_col, cur_col, prior_col) == (1, 4, 6)
    assert column_order == "positional"


# ---------------------------------------------------------------------------
# Đối chiếu Defect 6 + 7 trên đúng 4 file corpus thật đã chẩn đoán (giá trị
# kỳ vọng chép tay từ xls thô — xem docs/superpowers/plans/chan-doan-dot-2.md
# §3 và .superpowers/sdd/dot2-chan-doan-report.md §4). Tự skip nếu máy không
# có corpus.
# ---------------------------------------------------------------------------
_KQKD_2023_REL_PATH = (
    "BTG document/BCTC 5/2023/BCTC - tu lap 2023/"
    "18_Cty CP Sai gon Mui Ne 2023/KQKD_2023.xls"
)


def test_statement_detail_kqkd_2023_marker_lech_van_doc_du_gia_tri(corpus_root):
    """File thật KQKD_2023.xls: marker '4','5' ở c9/c11 (merge), giá trị ở
    c8/c10. Trước khi sửa: key = 20 mã TOÀN (None, None) -> 14 ô "thừa" ảo."""
    path = os.path.join(corpus_root, *_KQKD_2023_REL_PATH.split("/"))
    if not os.path.isfile(path):
        pytest.skip("Không có file corpus: %s" % _KQKD_2023_REL_PATH)
    detail = G.statement_detail(path)
    assert detail["strategy"] == "numbering"
    vals = detail["values"]
    assert len(vals) == 20
    assert all(v != (None, None) for v in vals.values()), (
        "key vẫn bị đọc rỗng: %d/%d mã toàn (None, None)"
        % (sum(1 for v in vals.values() if v == (None, None)), len(vals))
    )
    assert vals["01"] == (41666012511, 30782937591)
    assert vals["11"] == (29465782955, 26109045021)
    assert vals["30"] == (5177679470, -1193467056)
    assert vals["60"] == (4648769324, -1162942742)


_CDKT_6T_2025_REL_PATH = (
    "BTG document/BCTC 9/2025/Quy 2.2025/"
    "18_Cty CP Sai gon Mui Ne 6Th_2025/cdkt_6t.xls"
)


def test_statement_detail_cdkt_6t_2025_khong_mat_cot_ky_truoc(corpus_root):
    """File thật cdkt_6t.xls: marker '5' ở c12 RỖNG, cột Kỳ-trước thật ở c11.
    Trước khi sửa: 115 mã chỉ còn giá trị năm nay (mất nguyên cột prior)."""
    path = os.path.join(corpus_root, *_CDKT_6T_2025_REL_PATH.split("/"))
    if not os.path.isfile(path):
        pytest.skip("Không có file corpus: %s" % _CDKT_6T_2025_REL_PATH)
    vals = G.read_statement(path)
    assert len(vals) == 115
    n_prior = sum(1 for v in vals.values() if v[1] is not None)
    assert n_prior >= 110, (
        "cột Kỳ-trước vẫn mất: chỉ %d/%d mã có giá trị năm trước"
        % (n_prior, len(vals))
    )
    assert vals["100"] == (25469190675, 21062692235)
    assert vals["111"] == (2637956528, 5020895989)
    assert vals["131"] == (807840945, 902637569)
    assert vals["137"] == (-35504700, -35504700)


_CDKT_Q2_2022_REL_PATH = (
    "BTG document/BCTC 4/2022/QUY II.2022/"
    "18_CTCP Du lich KS Sai Gon Mui Ne/BCTC_Q2_SGMN/CDKT Q2.xls"
)


def test_statement_detail_cdkt_q2_2022_khong_mat_cot_ky_truoc(corpus_root):
    """Cùng dạng lỗi với cdkt_6t.xls: marker '5' ở c9 rỗng, Kỳ-trước thật ở c8."""
    path = os.path.join(corpus_root, *_CDKT_Q2_2022_REL_PATH.split("/"))
    if not os.path.isfile(path):
        pytest.skip("Không có file corpus: %s" % _CDKT_Q2_2022_REL_PATH)
    vals = G.read_statement(path)
    assert len(vals) == 115
    n_prior = sum(1 for v in vals.values() if v[1] is not None)
    assert n_prior >= 110, (
        "cột Kỳ-trước vẫn mất: chỉ %d/%d mã có giá trị năm trước"
        % (n_prior, len(vals))
    )
    assert vals["100"] == (13444369091, 8153516150)
    assert vals["111"] == (3253695613, 3752217151)
    assert vals["131"] == (2407157429, 2215724377)


_BTHT_KQKD_REL_PATH = (
    "BTG document/BCTC 4/2016/Quy 2.2016/18_Ben Thanh Hoang Thanh/"
    "18_Cty TNHH Ben Thanh Hoang Thanh_BCTC Q2.2016_KQKD.xls"
)


def test_statement_detail_btht_kqkd_khong_lay_hai_cot_nam_truoc(corpus_root):
    """File thật BTHT KQKD: 4 cột giá trị (Trong kỳ nay/trước + Lũy kế
    nay/trước). Trước khi sửa: fallback vồ 2 cột Năm-Trước -> key '01' =
    (7940375454, 7940375454); năm nay THẬT là 8852241816 (cột 3)."""
    path = os.path.join(corpus_root, *_BTHT_KQKD_REL_PATH.split("/"))
    if not os.path.isfile(path):
        pytest.skip("Không có file corpus: %s" % _BTHT_KQKD_REL_PATH)
    detail = G.statement_detail(path)
    assert detail["strategy"] == "fallback"
    assert detail["column_order"] == "labels"
    vals = detail["values"]
    assert vals["01"] == (8852241816, 7940375454)
    assert vals["20"] == (6703473816, 5791607454)
    assert vals["50"] == (6160168598, 5369295583)
    assert vals["60"] == (4938168598, 4295436466)
    # dòng '31' trong xls thô KHÔNG có số năm nay — key phải giữ đúng như thế
    assert vals["31"] == (None, 10000000)


def _rows_nhan_nhap_nhang_cuoi_ky_truoc_dau_ky():
    """
    Bảng giả lập kiểu bảng cân đối phát sinh: nhãn tiêu đề 'Số dư cuối kỳ
    trước' vừa chứa mốc năm nay ('cuối kỳ') vừa chứa mốc năm trước ('kỳ
    trước') trong cùng một cụm tự nhiên - nhập nhằng thật, không phải lỗi gõ.
    KHÔNG có hàng đánh số cột nên buộc phải rơi xuống _find_columns_fallback.
    """
    return [
        ["Chỉ tiêu", "MS", "Số dư cuối kỳ trước", "Số dư đầu kỳ"],
        ["Tiền mặt", "111", 1000000, 2000000],
        ["Tiền gửi ngân hàng", "112", 3000000, 4000000],
        ["Phải thu khách hàng", "131", 5000000, 6000000],
        ["Hàng tồn kho", "141", 7000000, 8000000],
        ["Tài sản cố định", "211", 9000000, 10000000],
        ["Đầu tư tài chính", "221", 11000000, 12000000],
    ]


def test_find_columns_du_phong_nhan_nhap_nhang_khong_doan_bua():
    """Nhãn nhập nhằng ('Số dư cuối kỳ trước' khớp cả 2 danh sách mốc) không
    được phép quyết định thứ tự cột - _order_by_header_labels phải từ chối
    (trả None) và _find_columns_fallback phải rơi về mặc định vị trí, báo
    đúng column_order == "positional" thay vì "labels" tự tin nhưng sai.
    Trước khi sửa Defect 4, ca này báo column_order == "labels" và gán cột
    'cuối kỳ trước' làm cột năm nay - sai mà không có tín hiệu cảnh báo."""
    rows = _rows_nhan_nhap_nhang_cuoi_ky_truoc_dau_ky()
    found = G._find_columns_fallback(rows)
    assert found is not None
    _, _, _, _, column_order = found
    assert column_order == "positional", (
        "nhãn nhập nhằng không được đoán bừa: kỳ vọng column_order='positional' "
        "nhưng dò được %r" % (column_order,)
    )
