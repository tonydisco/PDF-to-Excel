# -*- coding: utf-8 -*-
"""V4a Đợt 2 — sửa ĐỊNH VỊ để bắt CĐKT bị bỏ sót (nhóm LOCATE_FAIL).

Ba cơ chế lỗi đã đo trên corpus (xem .superpowers/sdd/dot2-v4a-locate.md):
  (a) Tiêu đề CĐKT nằm DƯỚI dải 42% đầu trang (letterhead công ty đẩy tiêu đề
      xuống ~0,47–0,76): dải quét cũ chỉ lấy 42% trên nên bỏ sót. Nới dải quét
      + tìm tiêu đề trên CẢ dải rộng (giữ nguyên phát hiện ở dải trên để không
      hồi quy trang đang chạy tốt).
  (b) Lớp text VNI/TCVN 8-bit lọt is_usable (tỷ lệ dấu vẫn > 0 vì glyph phân
      rã ra chữ Latin có dấu) nhưng KHÔNG normalize ra tiếng Việt thật -> ép
      OCR bằng cách đòi lớp text phải có ÍT NHẤT một TIÊU ĐỀ báo cáo đọc được.
  (c) Tiêu đề CĐKT bị OCR đọc sai ("TOÁN"->"T0AN") hoặc trang bảng KHÔNG có
      dòng tiêu đề (mảnh 1 trang): nhận trang CĐKT theo CỤM MÃ cấu trúc riêng
      của bảng cân đối (100/110/.../440 — không trùng KQKD/LCTT).

Test viết TRƯỚC khi sửa parser/textlayer (TDD).
"""
import fitz
import pytest

from bctc import parser as P
from bctc import textlayer as TL


# ----------------------------------------------------------------------
# Tiện ích dựng DÒNG tổng hợp: mỗi từ tối thiểu có 'text' và 'cy' (phân số
# theo chiều cao TRANG). _dinh_vi_trang nhận list các dòng (list từ).
# ----------------------------------------------------------------------
def w(text, cy, cx=0.2):
    return {"text": text, "cx": cx, "cy": cy, "right": cx + 0.03,
            "left": cx - 0.03, "top": cy, "width": 10, "height": 10,
            "conf": 90.0, "lx": cx - 0.03, "nh": 0.01}


def line(text, cy, cx=0.2):
    """Một dòng = list các từ (tách theo dấu cách), cùng cy."""
    toks = text.split()
    n = len(toks)
    return [w(t, cy, cx=cx + i * 0.05) for i, t in enumerate(toks)] if n else [w("", cy)]


def dong_ma_cdkt(codes, cy0=0.45, step=0.03):
    """Các dòng thân bảng CĐKT: 'Chỉ tiêu <mã> <giá trị>'."""
    out = []
    for i, c in enumerate(codes):
        cy = cy0 + i * step
        out.append([w("Khoản", cy, 0.10), w("mục", cy, 0.15),
                    w(c, cy, 0.45), w("1.234.567", cy, 0.75)])
    return out


# ======================================================================
# (a) Tiêu đề DƯỚI dải 42% vẫn được tìm thấy
# ======================================================================
def test_tieu_de_giua_trang_60pct_van_tim_thay():
    """Tiêu đề CĐKT ở cy=0.60 (dưới dải 42%) -> vẫn định vị được."""
    lines = [line("Công ty Cổ phần ABC", 0.05),
             line("Địa chỉ: 123 Đường XYZ, TP HCM", 0.12),
             line("Mẫu số B01-DN", 0.20),
             line("Kỳ báo cáo: Quý 3 năm 2014", 0.30),
             line("BẢNG CÂN ĐỐI KẾ TOÁN", 0.60),
             line("Tại ngày 30 tháng 9 năm 2014", 0.66)]
    title, stop = P._dinh_vi_trang(lines)
    assert title == "CDKT", "tiêu đề ở 60%% phải được tìm thấy, được %r" % title


def test_tieu_de_o_dai_tren_van_tim_thay_nhu_cu():
    """Regression: tiêu đề ở dải trên (cy=0.08) vẫn tìm thấy (hành vi cũ)."""
    lines = [line("BÁO CÁO KẾT QUẢ HOẠT ĐỘNG KINH DOANH", 0.08),
             line("Đơn vị: đồng", 0.14)] + dong_ma_cdkt(["01", "10", "11"], cy0=0.3)
    title, stop = P._dinh_vi_trang(lines)
    assert title == "KQHDKD"


def test_tieu_de_dai_tren_thang_khi_dai_duoi_co_tieu_de_khac():
    """Dải trên có ĐÚNG 1 tiêu đề -> lấy nó, không bị nhiễu bởi tiêu đề khác
    xuất hiện thấp hơn (tránh gộp thành 'nhiều tiêu đề' rồi loại oan)."""
    lines = [line("BẢNG CÂN ĐỐI KẾ TOÁN", 0.10),
             line("Tại ngày ...", 0.18),
             line("tham chiếu Báo cáo lưu chuyển tiền tệ", 0.70)]
    title, _ = P._dinh_vi_trang(lines)
    assert title == "CDKT"


# ======================================================================
# (c) Nhận trang CĐKT theo CỤM MÃ cấu trúc
# ======================================================================
def test_cum_ma_cdkt_du_ma_cau_truc():
    lines = dong_ma_cdkt(["100", "110", "200", "270", "300", "440"])
    assert P._cum_ma_cdkt(lines) is True


def test_cum_ma_cdkt_khong_du():
    lines = dong_ma_cdkt(["100", "110"])           # < ngưỡng
    assert P._cum_ma_cdkt(lines) is False


def test_cum_ma_cdkt_bo_qua_ma_kqkd_lctt():
    """Mã KQKD/LCTT (01,02,10,20,30) KHÔNG phải mã cấu trúc CĐKT."""
    lines = dong_ma_cdkt(["01", "02", "10", "20", "30", "40"])
    assert P._cum_ma_cdkt(lines) is False


def test_cum_ma_cdkt_bo_qua_ma_tai_khoan_cdps():
    """Mã tài khoản CDPS (111,112,131,138,211) trùng vài mã CĐKT con nhưng
    KHÔNG phải mã cấu trúc x00/xN0 -> không đủ để nhận nhầm là CĐKT."""
    lines = dong_ma_cdkt(["111", "112", "131", "138", "211", "331"])
    assert P._cum_ma_cdkt(lines) is False


def test_dinh_vi_trang_nhan_cdkt_khi_tieu_de_ocr_sai_nhung_co_cum_ma():
    """Tiêu đề bị OCR đọc sai ('T0AN') -> không khớp; nhưng cụm mã cấu trúc
    đủ dày -> vẫn nhận là CĐKT (mảnh 1 trang / scan xấu)."""
    lines = [line("BANG CAN DOI KE T0AN", 0.06)] + \
        dong_ma_cdkt(["100", "110", "120", "200", "270", "440"], cy0=0.2)
    title, _ = P._dinh_vi_trang(lines)
    assert title == "CDKT"


# ======================================================================
# Trang MỤC LỤC nhiều tiêu đề vẫn bị loại (không nhận nhầm)
# ======================================================================
def test_trang_muc_luc_nhieu_tieu_de_van_bi_loai():
    """Trang liệt kê cả 3 báo cáo (kèm số trang) -> heading_in_lines loại;
    cụm mã cũng KHÔNG có -> _dinh_vi_trang trả None."""
    lines = [line("Bảng cân đối kế toán 01-04", 0.30),
             line("Báo cáo kết quả hoạt động kinh doanh 05", 0.35),
             line("Báo cáo lưu chuyển tiền tệ 06", 0.40)]
    title, _ = P._dinh_vi_trang(lines)
    assert title is None


def test_trang_muc_luc_co_chu_muc_luc_bi_loai():
    lines = [line("MỤC LỤC", 0.10),
             line("BẢNG CÂN ĐỐI KẾ TOÁN", 0.30)]
    title, _ = P._dinh_vi_trang(lines)
    assert title is None


# ======================================================================
# Mốc DỪNG chỉ tính ở dải TRÊN (không hồi quy mở rộng tiếp diễn)
# ======================================================================
def test_moc_dung_chi_tinh_dai_tren():
    """Mốc 'bản thuyết minh...' NẰM DƯỚI 42% không được kích hoạt dừng
    (giữ nguyên hành vi mở rộng trang tiếp diễn của V1)."""
    lines = [line("BẢNG CÂN ĐỐI KẾ TOÁN", 0.06)] + \
        dong_ma_cdkt(["100", "110", "120"], cy0=0.2) + \
        [line("Bản thuyết minh báo cáo tài chính", 0.80)]
    title, stop = P._dinh_vi_trang(lines)
    assert stop is None, "mốc dừng dưới 42%% không được kích hoạt, được %r" % stop


def test_moc_dung_tren_dai_tren_van_bat():
    lines = [line("Bản thuyết minh báo cáo tài chính", 0.10),
             line("năm 2020", 0.16)]
    _, stop = P._dinh_vi_trang(lines)
    assert stop == "thuyet minh"


# ======================================================================
# (b) is_usable ép OCR khi lớp text KHÔNG có tiêu đề báo cáo đọc được
# ======================================================================
def _doc_text(txt, times=12):
    """Dựng lớp text tiếng Việt SẠCH: insert_htmlbox tạo hình HarfBuzz (font
    nội bộ có tiếng Việt) — insert_text mặc định không encode được ả/đ/ố."""
    d = fitz.open()
    pg = d.new_page()
    pg.insert_htmlbox(fitz.Rect(40, 40, 560, 780),
                      "".join("<p>%s</p>" % txt for _ in range(times)))
    return d


def test_is_usable_tu_choi_lop_text_khong_co_tieu_de():
    """Lớp text có dấu tiếng Việt nhưng KHÔNG có tiêu đề báo cáo nào đọc
    được (mô phỏng VNI: nhiều chữ có dấu, không cụm tiêu đề) -> phải ép OCR."""
    d = _doc_text("Công ty cổ phần đầu tư phát triển Việt Nam năm tài chính")
    try:
        assert TL.is_usable(d) is False
    finally:
        d.close()


def test_is_usable_chap_nhan_lop_text_co_tieu_de():
    """Lớp text có tiêu đề báo cáo đọc được -> dùng thẳng (không ép OCR)."""
    d = _doc_text("Bảng cân đối kế toán tại ngày 31 tháng 12 năm 2020 Tài sản")
    try:
        assert TL.is_usable(d) is True
    finally:
        d.close()


def test_has_report_title_helper():
    assert TL.has_report_title("... bao cao luu chuyen tien te ...") is True
    assert TL.has_report_title("cong ty co phan khong co tieu de") is False
    assert TL.has_report_title("BẢNG CÂN ĐỐI KẾ TOÁN") is True
