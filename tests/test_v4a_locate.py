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
# V8 §B — dải RỘNG của ĐƯỜNG TEXT phải kẹp đúng [0,42–0,66] và chịu cùng
# cổng `quet_dai` như đường OCR.
#
# Trước khi sửa: đường text truyền CẢ trang (`lambda: lines`) làm dải rộng và
# không có cổng nào -> mọi tín hiệu CĐKT ở BẤT KỲ đâu trên trang (câu văn xuôi
# nhắc tên báo cáo, cụm mã ở chân trang) đều gán nhãn CĐKT cho trang đó. Đo
# được: tín hiệu ở cy 0,95 vẫn ra 'CDKT'.
# ======================================================================
def test_tin_hieu_cdkt_duoi_day_trang_khong_con_gan_nhan():
    """Dòng nhắc tên CĐKT ở cy 0,85 (NGOÀI dải 0,66) -> không nhận là CĐKT."""
    lines = [line("Công ty Cổ phần ABC", 0.05),
             line("Báo cáo của Ban Giám đốc", 0.20),
             line("Chi tiết xem Bảng cân đối kế toán", 0.85)]
    title, _ = P._dinh_vi_trang(lines)
    assert title is None, "tín hiệu ngoài dải 0,66 không được gán nhãn, được %r" % title


def test_cum_ma_cdkt_o_chan_trang_khong_con_gan_nhan():
    """Cụm mã cấu trúc nằm hẳn ở CHÂN trang (0,75–0,90) -> ngoài dải, bỏ qua."""
    lines = [line("Công ty Cổ phần ABC", 0.05),
             line("Báo cáo của Ban Giám đốc", 0.20)] + \
        dong_ma_cdkt(["100", "110", "120", "200", "270", "440"], cy0=0.75, step=0.03)
    title, _ = P._dinh_vi_trang(lines)
    assert title is None


def test_tieu_de_trong_dai_rong_van_nhan_nhu_v4a():
    """Không hồi quy V4a: tiêu đề thật trong dải [0,42–0,66] vẫn nhận."""
    lines = [line("Công ty Cổ phần ABC", 0.05),
             line("Địa chỉ: 123 Đường XYZ", 0.12),
             line("BẢNG CÂN ĐỐI KẾ TOÁN", 0.60),
             line("Tại ngày 30/06/2025", 0.66)]
    title, _ = P._dinh_vi_trang(lines)
    assert title == "CDKT"


def test_quet_dai_tat_thi_bo_qua_dai_rong():
    """quet_dai=False (đã có CĐKT / đang dò mốc tiếp diễn) -> chỉ nhìn dải
    TRÊN, y như đường OCR không render dải dưới."""
    lines = [line("Công ty Cổ phần ABC", 0.05),
             line("BẢNG CÂN ĐỐI KẾ TOÁN", 0.60)]
    assert P._dinh_vi_trang(lines, quet_dai=True)[0] == "CDKT"
    assert P._dinh_vi_trang(lines, quet_dai=False)[0] is None


def test_quet_dai_tat_khong_anh_huong_dai_tren():
    """Tiêu đề ở dải TRÊN luôn nhận được, bất kể quet_dai."""
    lines = [line("BẢNG CÂN ĐỐI KẾ TOÁN", 0.10), line("Tại ngày ...", 0.18)]
    assert P._dinh_vi_trang(lines, quet_dai=False)[0] == "CDKT"


def test_duong_text_chuyen_quet_dai_qua_scan_strip(monkeypatch):
    """_scan_strip_render mang `quet_dai` sang _scan_strip_doc trên đường TEXT
    (không thì cổng ở trên là vô nghĩa khi chạy thật)."""
    lines = [line("Công ty Cổ phần ABC", 0.05),
             line("BẢNG CÂN ĐỐI KẾ TOÁN", 0.60)]

    class _Doc(object):
        _bctc_dung_lop_text = True

        def __getitem__(self, i):
            return object()

    monkeypatch.setattr(P.textlayer, "page_lines", lambda page: lines)
    doc = _Doc()
    nd_rong = P._scan_strip_render(doc, 0, 135, quet_dai=True)
    nd_hep = P._scan_strip_render(doc, 0, 135, quet_dai=False)
    assert P._scan_strip_doc(nd_rong, "vie")[0] == "CDKT"
    assert P._scan_strip_doc(nd_hep, "vie")[0] is None


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
