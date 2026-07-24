# -*- coding: utf-8 -*-
"""
V6 việc #2 — §7.3: nhận diện ĐƠN VỊ TÍNH. Parser dò cụm 'Đơn vị tính: ...' trên
trang báo cáo, ghi đúng đơn vị vào ô A2 và CẢNH BÁO khi khác VND. KHÔNG tự quy
đổi giá trị (không bịa độ chính xác không có trong nguồn).
"""
from bctc import parser, excel_writer


# ---- parser.detect_unit ----
def test_detect_unit_trieu_dong():
    assert parser.detect_unit(["Đơn vị tính: triệu đồng"]) == "triệu đồng"


def test_detect_unit_nghin_dong():
    assert parser.detect_unit(["Đơn vị tính: nghìn đồng"]) == "nghìn đồng"
    assert parser.detect_unit(["Đơn vị: ngàn đồng"]) == "nghìn đồng"


def test_detect_unit_ty_dong():
    assert parser.detect_unit(["Đơn vị tính: tỷ đồng"]) == "tỷ đồng"


def test_detect_unit_vnd_va_dong_tro_thanh_vnd():
    assert parser.detect_unit(["Đơn vị tính: VND"]) == "VND"
    assert parser.detect_unit(["Đơn vị tính: VNĐ"]) == "VND"
    assert parser.detect_unit(["Đơn vị tính: đồng"]) == "VND"
    assert parser.detect_unit(["Đơn vị tính: Đồng Việt Nam"]) == "VND"


def test_detect_unit_khong_thay_tra_none():
    assert parser.detect_unit(["Chỉ tiêu", "Mã số", "Thuyết minh"]) is None
    # 'đơn vị' không kèm gốc tiền tệ trong ~24 ký tự -> không nhận nhầm
    assert parser.detect_unit(["Vốn kinh doanh ở đơn vị trực thuộc"]) is None


def test_detect_unit_lan_trong_nhieu_dong():
    lines = ["CÔNG TY CP ABC", "BẢNG CÂN ĐỐI KẾ TOÁN",
             "Tại ngày 30/06/2025    Đơn vị tính: triệu đồng", "Chỉ tiêu"]
    assert parser.detect_unit(lines) == "triệu đồng"


# ---- parser.unit_warning ----
def test_unit_warning_khac_vnd_co_canh_bao():
    w = parser.unit_warning("triệu đồng")
    assert w is not None and "triệu đồng" in w and "KHÔNG tự quy đổi" in w


def test_unit_warning_vnd_khong_canh_bao():
    assert parser.unit_warning("VND") is None
    assert parser.unit_warning(None) is None


# ---- một "trang" triệu đồng -> ra đơn vị + cảnh báo; trang VND -> không ----
def test_trang_trieu_dong_ra_unit_va_canh_bao():
    unit = parser.detect_unit(["BÁO CÁO KQHĐKD", "Đơn vị tính: triệu đồng"])
    assert unit == "triệu đồng"
    assert parser.unit_warning(unit) is not None


def test_trang_vnd_ra_unit_khong_canh_bao():
    unit = parser.detect_unit(["Đơn vị tính: VND"])
    assert unit == "VND"
    assert parser.unit_warning(unit) is None


# ---- excel_writer ghi A2 theo đơn vị ----
def test_a2_ghi_dung_don_vi_phat_hien():
    wb = excel_writer.build_workbook("Cty", {"CDKT": {"100": (1, 2)}},
                                     unit="triệu đồng")
    assert wb["Bảng cân đối kế toán"]["A2"].value == "Đơn vị tính: triệu đồng"


def test_a2_mac_dinh_vnd_khi_khong_ro():
    wb = excel_writer.build_workbook("Cty", {"CDKT": {"100": (1, 2)}})
    assert wb["Bảng cân đối kế toán"]["A2"].value == "Đơn vị tính: VND"
