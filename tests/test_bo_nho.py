# -*- coding: utf-8 -*-
"""V5 Đợt 2 — G5 bộ nhớ: render XÁM tại nguồn (§8.1), máy bơm render→OCR
có chặn thay vì giữ ảnh mọi trang trong RAM (§8.2), trần điểm ảnh (§8.3).

Ràng buộc cứng: kết quả bóc tách KHÔNG ĐƯỢC đổi. Vì vậy:
  - trần điểm ảnh phải nằm TRÊN phong bì sản xuất (A4 @ 235 DPI = 5,34 MP —
    bằng chứng đo 9 file corpus: mọi trang đều A4) — trần 6 MP chỉ chặn
    trang khổ bất thường;
  - lượt cứu DPI cao (A4 @ 330 = 10,5 MP là hành vi V2 sẵn có) dùng trần
    RIÊNG rộng hơn (11 MP) vì chỉ render 1 trang một lúc trên luồng chính;
  - máy bơm trả kết quả THEO KHOÁ TRANG nên bất biến với thứ tự hoàn thành
    của các luồng OCR.
"""
import glob
import os
import threading
import time

import fitz
import pytest
from PIL import Image

from bctc import ocr, parser

A4_W, A4_H = 595.0, 842.0


def _doc_trang(w=A4_W, h=A4_H):
    d = fitz.open()
    d.new_page(width=w, height=h)
    d._bctc_dung_lop_text = False
    return d


# ----------------------------------------------------------------------
# §8.3 — trần điểm ảnh: _dpi_theo_tran
# ----------------------------------------------------------------------
def test_tran_diem_anh_phong_bi_san_xuat_khong_doi():
    """A4 ở mọi DPI của đường sản xuất (quét dải 135, extract 180/235) phải
    GIỮ NGUYÊN DPI — trần chỉ dành cho trang khổ bất thường."""
    for dpi in (135, 180, 235):
        assert parser._dpi_theo_tran(A4_W, A4_H, dpi) == dpi


def test_tran_diem_anh_trang_lon_bi_chan_sat_tran():
    """Trang 2xA4 mỗi chiều (diện tích x4) @235 DPI ~ 21,3 MP: phải hạ DPI
    sao cho vừa lọt trần nhưng KHÔNG chặn quá tay."""
    w, h = A4_W * 2, A4_H * 2
    dpi = parser._dpi_theo_tran(w, h, 235)
    assert dpi < 235
    w_in, h_in = w / 72.0, h / 72.0
    assert w_in * h_in * dpi * dpi <= parser.TRAN_MP_RENDER * 1e6
    assert w_in * h_in * (dpi + 2) ** 2 > parser.TRAN_MP_RENDER * 1e6


def test_tran_diem_anh_tran_cuu_rong_hon():
    """A4 @ 330 (10,5 MP — lượt cứu V2 sẵn có) phải LỌT trần cứu để hành vi
    cứu không đổi, nhưng vượt trần render hàng loạt."""
    assert parser._dpi_theo_tran(A4_W, A4_H, 330, parser.TRAN_MP_CUU) == 330
    assert parser._dpi_theo_tran(A4_W, A4_H, 330) < 330


# ----------------------------------------------------------------------
# §8.1 — render xám tại nguồn: _render_trang_xam / ocr.render_page / preprocess
# ----------------------------------------------------------------------
def test_render_trang_xam_mode_L_va_kich_thuoc():
    d = _doc_trang()
    anh, dpi_hd = parser._render_trang_xam(d, 0, 150)
    d.close()
    assert anh.mode == "L"
    assert dpi_hd == 150
    assert abs(anh.size[0] - A4_W / 72.0 * 150) <= 2
    assert abs(anh.size[1] - A4_H / 72.0 * 150) <= 2


def test_render_trang_xam_log_khi_bi_chan():
    d = _doc_trang(w=A4_W * 2, h=A4_H * 2)
    logs = []
    anh, dpi_hd = parser._render_trang_xam(d, 0, 235, log=logs.append)
    d.close()
    assert dpi_hd < 235
    assert anh.size[0] * anh.size[1] <= parser.TRAN_MP_RENDER * 1e6 * 1.01
    mau = "↓ trang 1: giới hạn %d MP (DPI 235->%d)" \
          % (int(parser.TRAN_MP_RENDER), dpi_hd)
    assert any(mau in m for m in logs), logs


def test_render_trang_xam_khong_log_khi_lot_tran():
    d = _doc_trang()
    logs = []
    parser._render_trang_xam(d, 0, 180, log=logs.append)
    d.close()
    assert logs == []


def _im(cs, xref=7):
    """Metadata ảnh nhúng như page.get_images: (xref, smask, w, h, bpc, cs, ...)."""
    return (xref, 0, 1000, 1400, 8, cs, "", "Im%d" % xref, "DCTDecode")


def test_anh_nhung_xam_chi_khi_moi_anh_deu_xam():
    """Render GRAY trực tiếp CHỈ khi mọi ảnh nhúng đều colorspace xám —
    trang màu/vector/không metadata phải đi đường RGB→Pillow như cũ (công
    thức trộn kênh MuPDF khác ITU-601, đổi điểm ảnh -> đổi kết quả OCR)."""
    assert parser._anh_nhung_xam([_im("DeviceGray")]) is True
    assert parser._anh_nhung_xam([_im("DeviceGray"), _im("DeviceRGB", 8)]) is False
    assert parser._anh_nhung_xam([_im("ICCBased")]) is False
    assert parser._anh_nhung_xam([]) is False
    assert parser._anh_nhung_xam(None) is False


def test_render_page_ocr_tra_anh_xam():
    d = _doc_trang()
    img = ocr.render_page(d, 0, dpi=96)
    d.close()
    assert img.mode == "L"


def test_preprocess_anh_xam_y_het_duong_rgb():
    """preprocess trên ảnh "L" phải cho KẾT QUẢ Y HỆT đường RGB→xám cũ
    (cùng nội dung) — bảo đảm đổi nguồn render không đổi ảnh vào Tesseract."""
    g = Image.linear_gradient("L").resize((64, 64))
    rgb = Image.merge("RGB", (g, g, g))
    assert ocr.preprocess(g).mode == "L"
    assert ocr.preprocess(g).tobytes() == ocr.preprocess(rgb).tobytes()


# ----------------------------------------------------------------------
# §8.2 — máy bơm render→OCR: _bom_ocr
# ----------------------------------------------------------------------
def test_bom_ocr_du_trang_dung_ket_qua_khi_hoan_thanh_lech_thu_tu():
    """Trang sau xong TRƯỚC trang đầu — kết quả vẫn đủ và đúng theo khoá."""
    pages = list(range(9))

    def render(p):
        return "anh%d" % p

    def ocr_fn(p, anh):
        time.sleep(0.002 * (9 - p))
        return anh + ":kq"

    ket = parser._bom_ocr(pages, render, ocr_fn, 3)
    assert ket == {p: "anh%d:kq" % p for p in pages}


def test_bom_ocr_gioi_han_so_anh_song_cung_luc():
    """Không bao giờ giữ quá nw+1 ảnh sống (mục tiêu chính của §8.2)."""
    nw = 2
    khoa = threading.Lock()
    song, dinh = [0], [0]

    def render(p):
        with khoa:
            song[0] += 1
            dinh[0] = max(dinh[0], song[0])
        return p

    def ocr_fn(p, anh):
        time.sleep(0.005)
        with khoa:
            song[0] -= 1
        return anh

    parser._bom_ocr(list(range(12)), render, ocr_fn, nw)
    assert dinh[0] <= nw + 1, "giữ %d ảnh cùng lúc (trần %d)" % (dinh[0], nw + 1)


def test_bom_ocr_loi_lan_len_khong_treo():
    """Luồng OCR hỏng: lỗi phải LAN LÊN (không nuốt), máy bơm không treo."""
    def ocr_fn(p, anh):
        if p == 3:
            raise ValueError("hỏng giả lập")
        return anh

    with pytest.raises(ValueError):
        parser._bom_ocr(list(range(6)), lambda p: p, ocr_fn, 2)


def test_bom_ocr_rong():
    assert parser._bom_ocr([], lambda p: p, lambda p, a: a, 2) == {}


# ----------------------------------------------------------------------
# Corpus: streaming đa luồng phải cho kết quả Y HỆT đường 1 luồng
# ----------------------------------------------------------------------
@pytest.fixture(scope="module")
def _tesseract():
    try:
        ocr.configure_tesseract()
    except ocr.TesseractNotFound:
        pytest.skip("Máy không có Tesseract")
    if not ocr.has_vietnamese():
        pytest.skip("Tesseract chưa có gói tiếng Việt (vie)")


def test_corpus_stream_nhieu_luong_bang_mot_luong(corpus_root, _tesseract):
    """PDF scan thật nhiều trang: extract workers=4 (OCR song song, render
    tuần tự trên luồng chính) phải ra results Y HỆT workers=1 — an toàn
    luồng + bất biến với thứ tự hoàn thành."""
    hits = glob.glob(
        os.path.join(corpus_root, "**",
                     "18_Cty TNHH Ben Thanh Hoang Thanh - kiem toan.pdf"),
        recursive=True)
    if not hits:
        pytest.skip("Không có file corpus Hoang Thanh")

    doc = fitz.open(sorted(hits)[0])
    doc._bctc_dung_lop_text = False
    scope = parser.locate_pages(doc, workers=4)
    r1, _, _ = parser.extract(doc, dpi=180, scope=scope, workers=1)
    r4, _, _ = parser.extract(doc, dpi=180, scope=scope, workers=4)
    doc.close()

    assert sum(len(v) for v in r1.values()) > 0
    assert r1 == r4
