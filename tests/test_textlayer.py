# -*- coding: utf-8 -*-
import os
import glob
import fitz
import pytest

from bctc import textlayer as TL


def test_diacritic_ratio_van_ban_tieng_viet_that():
    t = "Bảng cân đối kế toán của Công ty Cổ phần Dịch vụ Bến Thành"
    assert TL.diacritic_ratio(t) > 0.1


def test_diacritic_ratio_mojibake_bang_khong():
    """Mẫu mojibake thật lấy từ corpus (OCB_17CN_BCTC_M.pdf)."""
    t = "BAD CAD TAl CHfNH RII~NG Cho yay khach hang Milu sa BOSrrCTD"
    assert TL.diacritic_ratio(t) < TL.MIN_DIACRITIC_RATIO


def test_diacritic_ratio_chuoi_rong():
    assert TL.diacritic_ratio("") == 0.0
    assert TL.diacritic_ratio("123 456") == 0.0


def test_strip_signature_text_bo_lop_phu_chu_ky():
    t = "Digitally signed by NGUYEN VAN A\nKý bởi: CONG TY ABC\nSố liệu thật"
    out = TL.strip_signature_text(t)
    assert "Digitally signed" not in out
    assert "Ký bởi" not in out
    assert "Số liệu thật" in out


def test_is_usable_tu_choi_tai_lieu_khong_co_text():
    d = fitz.open()
    d.new_page()
    assert TL.is_usable(d) is False
    d.close()


def test_is_usable_tu_choi_file_chi_co_chu_ky(corpus_root):
    """33_Cty CP DL Dak Lak 2024.pdf: 38 trang nhưng chỉ 352 ký tự chữ ký số.

    Tỷ lệ dấu của nó (0,126) vượt ngưỡng, nên chính NGƯỠNG SỐ KÝ TỰ mới là thứ
    chặn được file này. Test này canh đúng chỗ đó.
    """
    hits = glob.glob(os.path.join(corpus_root, "**", "33_Cty CP DL Dak Lak 2024.pdf"),
                     recursive=True)
    if not hits:
        pytest.skip("Không có file Đăk Lăk 2024 trong corpus")
    d = fitz.open(hits[0])
    try:
        assert TL.is_usable(d) is False
    finally:
        d.close()


def test_page_lines_tra_dung_cau_truc_nhu_ocr():
    """Cấu trúc phải khớp ocr.ocr_lines() để parser dùng chung."""
    d = fitz.open()
    pg = d.new_page()
    pg.insert_text((72, 100), "Tiền và các khoản tương đương tiền")
    lines = TL.page_lines(pg)
    d.close()
    assert lines and isinstance(lines[0], list)
    w = lines[0][0]
    for k in ("text", "left", "top", "width", "height", "conf",
              "cx", "cy", "right", "lx"):
        assert k in w, "thiếu khoá %r" % k
    assert 0.0 <= w["cx"] <= 1.0
    assert 0.0 <= w["right"] <= 1.0
