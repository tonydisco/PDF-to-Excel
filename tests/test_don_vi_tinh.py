# -*- coding: utf-8 -*-
"""
V6 việc #2 — §7.3: nhận diện ĐƠN VỊ TÍNH. Parser dò cụm 'Đơn vị tính: ...' trên
trang báo cáo, ghi đúng đơn vị vào ô A2 và CẢNH BÁO khi khác VND. KHÔNG tự quy
đổi giá trị (không bịa độ chính xác không có trong nguồn).
"""
import pytest

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


# ======================================================================
# V8 §E — hệ số viết bằng SỐ ('1.000 đồng') và nhãn viết tắt 'ĐVT:'
#
# Đo trên bản trước khi sửa: 'Đơn vị tính: 1.000 đồng' -> 'VND' KHÔNG cảnh báo
# (lệch 10^3 âm thầm — đây là cách ghi nghìn PHỔ BIẾN NHẤT trên bản in Việt);
# 'Đơn vị tính: 1.000.000 đồng' -> 'VND' (lệch 10^6); 'ĐVT: 1.000 đồng' -> None
# (nhãn viết tắt không được nhận, mất luôn cả đơn vị lẫn cảnh báo).
# ======================================================================
@pytest.mark.parametrize("dong,mong_doi", [
    # --- hệ số bằng SỐ, nhãn đầy đủ ---
    ("Đơn vị tính: 1.000 đồng", "nghìn đồng"),
    ("Đơn vị tính: 1.000.000 đồng", "triệu đồng"),
    ("Đơn vị tính: 1.000.000.000 đồng", "tỷ đồng"),
    # --- hệ số bằng SỐ, không có dấu phân tách / dấu phẩy kiểu Anh ---
    ("Đơn vị tính: 1000 đồng", "nghìn đồng"),
    ("Đơn vị tính: 1,000 đồng", "nghìn đồng"),
    ("Đơn vị tính: 1000000 đồng", "triệu đồng"),
    ("Đơn vị tính: 1,000,000 VND", "triệu đồng"),
    # --- nhãn VIẾT TẮT 'ĐVT' / 'Đvt' ---
    ("ĐVT: 1.000 đồng", "nghìn đồng"),
    ("Đvt: 1.000.000 đồng", "triệu đồng"),
    ("ĐVT: triệu đồng", "triệu đồng"),
    ("Đvt: đồng", "VND"),
    ("ĐVT: VND", "VND"),
    # --- hệ số bằng CHỮ vẫn như cũ (không hồi quy) ---
    ("Đơn vị tính: nghìn đồng", "nghìn đồng"),
    ("Đơn vị tính: triệu đồng", "triệu đồng"),
    ("Đơn vị tính: tỷ đồng", "tỷ đồng"),
    ("Đơn vị tính: đồng", "VND"),
    ("Đơn vị tính: VND", "VND"),
])
def test_detect_unit_bang_moi_dang_ghi(dong, mong_doi):
    assert parser.detect_unit([dong]) == mong_doi


@pytest.mark.parametrize("dong", [
    "Đơn vị tính: 1.000 đồng",
    "Đơn vị tính: 1.000.000 đồng",
    "ĐVT: 1.000 đồng",
    "Đvt: 1.000.000 đồng",
])
def test_he_so_bang_so_luon_kem_canh_bao(dong):
    """Mọi dạng CÓ hệ số đều phải sinh cảnh báo — không bao giờ im lặng."""
    u = parser.detect_unit([dong])
    assert u != "VND"
    assert parser.unit_warning(u) is not None


def test_he_so_la_ghi_nguyen_van_va_van_canh_bao():
    """Hệ số không phải 10^3/10^6/10^9 (vd '10.000 đồng') KHÔNG được âm thầm
    coi là VND: ghi nguyên văn theo nguồn để cảnh báo vẫn bật."""
    u = parser.detect_unit(["Đơn vị tính: 10.000 đồng"])
    assert u == "10.000 đồng"
    assert parser.unit_warning(u) is not None


@pytest.mark.parametrize("dong", [
    # số KHÔNG phải hệ số (ngày tháng, số hiệu mẫu) -> vẫn là VND
    "Đơn vị tính: đồng (tại ngày 31/12/2024)",
    "Mẫu số B01-DN  Đơn vị tính: VND",
    # 'triệu đồng' kèm chú thích số trong ngoặc -> vẫn là triệu đồng
    "Đơn vị tính: triệu đồng",
])
def test_khong_bat_nham_so_khac_thanh_he_so(dong):
    assert parser.detect_unit([dong]) in ("VND", "triệu đồng")


def test_dvt_khong_bat_nham_trong_tu_khac():
    """'dvt' phải là TỪ riêng, không dính vào chữ khác."""
    assert parser.detect_unit(["Mã hàng ABCDVTX đồng bộ"]) is None


def test_a2_ghi_dung_khi_nguon_ghi_he_so_bang_so():
    """Đường đi trọn vẹn: '1.000 đồng' -> A2 ghi 'nghìn đồng', không phải VND."""
    unit = parser.detect_unit(["BẢNG CÂN ĐỐI KẾ TOÁN", "ĐVT: 1.000 đồng"])
    wb = excel_writer.build_workbook("Cty", {"CDKT": {"100": (1, 2)}}, unit=unit)
    assert wb["Bảng cân đối kế toán"]["A2"].value == "Đơn vị tính: nghìn đồng"
