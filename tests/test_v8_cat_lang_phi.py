# -*- coding: utf-8 -*-
"""V8 Đợt 2 — cắt việc OCR lãng phí (§A) và chặn GHI ĐÈ âm thầm (§C).

§A. Trang trong scope không cho MÃ nào thì theo định nghĩa không đóng góp gì,
    nhưng vẫn bị render + OCR TRỌN TRANG ở MỌI lượt DPI, và còn được V2 coi là
    ứng viên "cứu OCR" (thêm tối đa 2 lượt OCR nữa, một lượt ở DPI+100). Đo
    trên 27. Cty CP SXKD hang XK Tan Binh BCTC 2019_chua kt.pdf: 5/10 trang
    scope cho 0 mã ở CẢ HAI lượt DPI. Sửa: lượt DPI ĐẦU vẫn soi đủ mọi trang
    (không nhìn thì không biết), sau đó loại các trang 0 mã khỏi những lượt sau
    và khỏi diện cứu — có log, không bao giờ âm thầm.

§C. Lượt 2 của extract ghi results[key][code] = (cur, prior) VÔ ĐIỀU KIỆN:
    trang đứng SAU trong scope (trang tiếp diễn / trang bắt được nhờ dải rộng)
    có số rơi cạnh cột mã sẽ ĐÈ LÊN giá trị ĐÚNG của trang trước mà không một
    cảnh báo nào. Bộ dò xung đột giữa các DPI cũng không thấy vì hai lượt DPI
    dùng CHUNG scope nên cùng sai giống hệt nhau. Sửa: giá trị đầu tiên đọc
    được THẮNG, lần đọc sau chỉ điền vào ô trống, lệch nhau -> ghi 'nghi ngờ'.
"""
import fitz
import pytest

from bctc import parser as P
from bctc import templates as T


# ----------------------------------------------------------------------
# Dựng PDF lớp text tổng hợp: font đều (Courier) nên vị trí cột tính được
# theo chỉ số ký tự -> bảng có cột mã và 2 cột số ổn định.
# ----------------------------------------------------------------------
def _dong(page, y, o_chu):
    txt = ""
    for idx in sorted(o_chu):
        if len(txt) < idx:
            txt += " " * (idx - len(txt))
        txt += o_chu[idx]
    page.insert_text((40, y), txt, fontsize=10, fontname="cour")


def _trang_bang(doc, tieu_de, hang):
    """hang = [(nhãn, mã, số cuối kỳ, số đầu kỳ)]"""
    pg = doc.new_page(width=595, height=842)
    if tieu_de:
        pg.insert_text((200, 60), tieu_de, fontsize=13, fontname="cour")
    y = 120
    for nhan, ma, v1, v2 in hang:
        _dong(pg, y, {0: nhan, 38: ma, 55: v1, 70: v2})
        y += 20
    return pg


def _trang_chu(doc, cac_dong):
    pg = doc.new_page(width=595, height=842)
    y = 120
    for d in cac_dong:
        _dong(pg, y, {0: d})
        y += 20
    return pg


@pytest.fixture
def doc_hai_trang():
    """Trang 1 = CĐKT thật; trang 2 = trang VĂN XUÔI có số rác rơi vào đúng
    cột mã (mô phỏng trang tiếp diễn bị V1 kéo vào scope)."""
    d = fitz.open()
    _trang_bang(d, "BANG CAN DOI KE TOAN", [
        ("TAI SAN NGAN HAN", "100", "1.111.111", "2.222.222"),
        ("Tien va tuong duong tien", "110", "3.333.333", "4.444.444"),
        ("Cac khoan phai thu", "130", "5.555.555", "6.666.666"),
        ("TAI SAN DAI HAN", "200", "7.777.777", "8.888.888"),
    ])
    _trang_bang(d, None, [
        ("Phu luc so lieu doi chieu", "100", "9.999.999", "9.999.999"),
        ("Ghi chu bo sung", "110", "1.000.000", "1.000.000"),
    ])
    d._bctc_dung_lop_text = True
    yield d
    d.close()


# ======================================================================
# §C — trang sau KHÔNG được ghi đè giá trị đúng của trang trước
# ======================================================================
def test_trang_sau_khong_ghi_de_gia_tri_da_co(doc_hai_trang):
    """Tái hiện lỗi: trước khi sửa, mã 100 ra 9.999.999 (rác trang 2) thay cho
    1.111.111, và warnings TRỐNG RỖNG.

    Yêu cầu của review: GIỮ giá trị đầu + ghi 'nghi ngờ' (chặn hỏng dữ liệu,
    không chỉ chú thích nó). Cú tụt cân đối 69,7% -> 64,5% ở lần đo đầu KHÔNG
    do luật này mà do va chạm CÙNG TRANG — xem
    test_cung_mot_trang_thi_dong_sau_van_thang_nhu_cu.
    """
    res, _, meta = P.extract(doc_hai_trang, scope=[(0, "CDKT"), (1, "CDKT")])
    assert res["CDKT"]["100"] == (1111111, 2222222), \
        "giá trị đúng của trang 1 bị trang 2 ghi đè: %r" % (res["CDKT"]["100"],)
    assert res["CDKT"]["110"] == (3333333, 4444444)
    ma_nghi_ngo = {(k, c) for k, c, _l, _a, _b in meta["_xung_dot"]}
    assert ("CDKT", "100") in ma_nghi_ngo, \
        "chặn ghi đè mà không ghi nghi ngờ = vẫn là âm thầm"


def test_bi_doi_ghi_de_thi_ghi_nhan_nghi_ngo(doc_hai_trang):
    """Không im lặng: ô bị đòi ghi đè phải vào danh sách 'nghi ngờ' (chính là
    cơ chế tô cam ô trong Excel)."""
    _, _, meta = P.extract(doc_hai_trang, scope=[(0, "CDKT"), (1, "CDKT")])
    xd = meta["_xung_dot"]
    assert xd, "phải ghi nhận nghi ngờ khi trang sau đòi ghi đè"
    ma_nghi_ngo = {(k, c) for k, c, _l, _a, _b in xd}
    assert ("CDKT", "100") in ma_nghi_ngo
    assert ("CDKT", "110") in ma_nghi_ngo


def test_nghi_ngo_trong_mot_luot_di_ra_toi_conflicts(doc_hai_trang):
    """Đường đi trọn vẹn: extract_consensus phải đưa nghi ngờ trong-một-lượt
    ra `conflicts` -> excel_writer tô cam ô."""
    merged, _, _, conflicts = P.extract_consensus(doc_hai_trang, dpis=(180,))
    assert merged["CDKT"]["100"] == (1111111, 2222222)
    assert any(c[0] == "CDKT" and c[1] == "100" for c in conflicts), \
        "conflicts phải chứa ô bị đòi ghi đè, đang là %r" % (conflicts,)


def test_trang_sau_van_duoc_DIEN_vao_o_con_trong():
    """Không được thụt lùi: ô trang trước để TRỐNG thì trang sau vẫn điền."""
    d = fitz.open()
    _trang_bang(d, "BANG CAN DOI KE TOAN", [
        ("TAI SAN NGAN HAN", "100", "", ""),
        ("Tien va tuong duong tien", "110", "3.333.333", "4.444.444"),
    ])
    _trang_bang(d, None, [
        ("Cong tai san ngan han", "100", "1.111.111", "2.222.222"),
    ])
    d._bctc_dung_lop_text = True
    try:
        res, _, meta = P.extract(d, scope=[(0, "CDKT"), (1, "CDKT")])
        assert res["CDKT"]["100"] == (1111111, 2222222), \
            "ô trống phải được trang sau điền vào"
        assert not meta["_xung_dot"], "điền ô trống KHÔNG phải xung đột"
    finally:
        d.close()


def test_cung_mot_trang_thi_dong_sau_van_thang_nhu_cu():
    """Ràng buộc NGƯỢC lại, do phép đo tầng-2 phát hiện: luật "giữ giá trị
    đầu" CHỈ áp cho TRANG KHÁC. Trong CÙNG một trang, dòng sau vẫn thắng.

    Mẫu cũ (QĐ15) đánh 270 = 'Tài sản dài hạn khác' và tổng cộng là 280; khung
    Thông tư 200 lại lấy 270 làm tổng, nên forced_total_code ép dòng 'TỔNG CỘNG
    TÀI SẢN' về 270 và phải ĐÈ LÊN dòng 270 gốc đứng ngay trên nó (cùng trang).
    Đo trên 02_Cty CP TM Ben Thanh BC quyet toan Q3 2013.pdf: chặn cú đè này
    làm 6/6 phép kiểm tra cân đối chuyển từ ĐẠT sang HỎNG.
    """
    d = fitz.open()
    _trang_bang(d, "BANG CAN DOI KE TOAN", [
        ("TAI SAN NGAN HAN", "100", "1.111.111", "2.222.222"),
        ("V. Tai san dai han khac", "270", "250.166", "273.929"),
        ("TONG CONG TAI SAN", "280", "358.121.611", "346.468.212"),
    ])
    d._bctc_dung_lop_text = True
    try:
        res, _, meta = P.extract(d, scope=[(0, "CDKT")])
        assert res["CDKT"]["270"] == (358121611, 346468212), \
            "dòng TỔNG CỘNG cùng trang phải thắng, đang là %r" % (res["CDKT"]["270"],)
        assert not meta["_xung_dot"], "đè trong CÙNG trang không tính nghi ngờ"
    finally:
        d.close()


def test_hop_nhat_o_giu_gia_tri_da_co_va_bao_nghi_ngo():
    """Giá trị ĐÃ CÓ thắng, cặp mới chỉ điền ô trống, lệch nhau -> nghi ngờ.

    Đây KHÔNG phải nguyên nhân của cú tụt cân đối 69,7% -> 64,5% ở lần đo
    đầu: nguyên nhân thật là va chạm CÙNG TRANG (xem
    test_cung_mot_trang_thi_dong_sau_van_thang_nhu_cu). Đừng "sửa" bằng cách
    lật hàm này sang lấy-giá-trị-sau — nó dùng chung cho hợp nhất giữa các
    lượt DPI (xem test dưới).
    """
    ghi = []
    assert P._hop_nhat_o(None, (5, 6), "CDKT", "100", ghi.append) == (5, 6)
    assert ghi == []
    # đọc lại ra số KHÁC -> giữ số ĐÃ CÓ, nhưng PHẢI ghi nghi ngờ (không im lặng)
    assert P._hop_nhat_o((5, 6), (9, 9), "CDKT", "100", ghi.append) == (5, 6)
    assert [x[2] for x in ghi] == ["cuối năm/năm nay", "đầu năm/năm trước"]
    assert [(x[3], x[4]) for x in ghi] == [(5, 9), (6, 9)]
    # ô trống được điền từ trang kia, không phải ghi đè -> không nghi ngờ
    ghi[:] = []
    assert P._hop_nhat_o((None, 6), (9, None), "CDKT", "100", ghi.append) == (9, 6)
    assert ghi == []


def test_luot_dpi_sau_khong_duoc_de_len_luot_dpi_chinh(monkeypatch):
    """Hợp đồng đa-DPI (có sẵn từ trước V8, ghi ngay trong docstring của
    extract_consensus): "các DPI sau chỉ ĐIỀN vào ô còn trống, KHÔNG ghi đè
    giá trị đã có (tránh mang lỗi của DPI cao vào)".

    Chốt lại bằng test vì `_hop_nhat_o` dùng chung cho cả hợp nhất trong-lượt
    lẫn giữa-các-lượt: lật nó sang lấy-giá-trị-sau sẽ ÂM THẦM phá hợp đồng này
    (đo được: DPI đầu (100,200) + DPI 2 (999,888) -> ra (999,888)).
    """
    n = [0]

    def fake_extract(doc, **kw):
        n[0] += 1
        v = (100, 200) if n[0] == 1 else (999, 888)
        return ({"CDKT": {"270": v}, "KQHDKD": {}, "LCTT": {}}, [], {})

    monkeypatch.setattr(P, "extract", fake_extract)
    monkeypatch.setattr(P, "locate_pages", lambda doc, **kw: [(0, "CDKT")])
    merged, _, _, conflicts = P.extract_consensus(object(), dpis=(185, 240))
    assert merged["CDKT"]["270"] == (100, 200), \
        "lượt DPI chính phải thắng, đang là %r" % (merged["CDKT"]["270"],)
    assert conflicts, "hai lượt đọc lệch nhau vẫn phải ghi 'nghi ngờ'"


# ======================================================================
# §A — trang 0 mã bị loại khỏi các lượt DPI sau
# ======================================================================
def test_extract_bao_cao_trang_khong_co_ma():
    """Trang văn xuôi thuần (không token mã nào) -> vào _trang_khong_ma."""
    d = fitz.open()
    _trang_bang(d, "BANG CAN DOI KE TOAN", [
        ("TAI SAN NGAN HAN", "100", "1.111.111", "2.222.222"),
        ("Tien va tuong duong tien", "110", "3.333.333", "4.444.444"),
    ])
    _trang_chu(d, ["Ban Giam doc chiu trach nhiem lap bao cao nay",
                   "Cac chinh sach ke toan ap dung nhat quan"])
    d._bctc_dung_lop_text = True
    try:
        _, _, meta = P.extract(d, scope=[(0, "CDKT"), (1, "CDKT")])
        assert meta["_trang_khong_ma"] == [1]
    finally:
        d.close()


def test_trang_tiep_dien_that_co_ma_thi_GIU_LAI():
    """Trang tiếp diễn THẬT của bảng cân đối (không lặp tiêu đề nhưng CÓ mã)
    phải được giữ nguyên chế độ đầy đủ — đây là ca V1 sinh ra để cứu."""
    d = fitz.open()
    _trang_bang(d, "BANG CAN DOI KE TOAN", [
        ("TAI SAN NGAN HAN", "100", "1.111.111", "2.222.222"),
        ("Tien va tuong duong tien", "110", "3.333.333", "4.444.444"),
    ])
    _trang_bang(d, None, [           # trang 2: tiếp diễn, KHÔNG có tiêu đề
        ("NO PHAI TRA", "300", "5.555.555", "6.666.666"),
        ("Von chu so huu", "400", "7.777.777", "8.888.888"),
    ])
    d._bctc_dung_lop_text = True
    try:
        _, _, meta = P.extract(d, scope=[(0, "CDKT"), (1, "CDKT")])
        assert meta["_trang_khong_ma"] == [], \
            "trang tiếp diễn CÓ mã không được loại"
    finally:
        d.close()


def test_bo_trang_khong_ma_cat_scope_va_ghi_log():
    scope = [(0, "CDKT"), (1, "CDKT"), (2, "CDKT"), (5, "LCTT")]
    logs = []
    con = P._bo_trang_khong_ma(scope, {"_trang_khong_ma": [1, 5]}, logs.append)
    assert con == [(0, "CDKT"), (2, "CDKT")]
    assert logs == [
        "   - trang 2: không có mã số ở lượt đầu, bỏ khỏi các lượt sau",
        "   - trang 6: không có mã số ở lượt đầu, bỏ khỏi các lượt sau",
    ]


def test_bo_trang_khong_ma_khong_co_gi_thi_giu_nguyen():
    scope = [(0, "CDKT"), (1, "CDKT")]
    logs = []
    assert P._bo_trang_khong_ma(scope, {}, logs.append) is scope
    assert P._bo_trang_khong_ma(scope, {"_trang_khong_ma": []}, logs.append) is scope
    assert logs == []


def test_luot_dpi_sau_chay_tren_scope_da_cat(monkeypatch):
    """Lượt DPI ĐẦU soi ĐỦ scope; các lượt sau chỉ chạy trên scope đã cắt."""
    scope_goc = [(0, "CDKT"), (1, "CDKT"), (2, "CDKT"), (3, "LCTT")]
    da_goi = []

    def fake_extract(doc, **kw):
        da_goi.append(list(kw["scope"]))
        meta = {"_trang_khong_ma": [1, 3]} if len(da_goi) == 1 else {}
        return {k: {} for k in T.STATEMENTS}, [], meta

    monkeypatch.setattr(P, "extract", fake_extract)
    monkeypatch.setattr(P, "locate_pages", lambda doc, **kw: list(scope_goc))

    logs = []
    P.extract_consensus(object(), dpis=(180, 235, 290), log=logs.append)

    assert da_goi[0] == scope_goc, "lượt đầu phải soi đủ mọi trang"
    assert da_goi[1] == [(0, "CDKT"), (2, "CDKT")]
    assert da_goi[2] == [(0, "CDKT"), (2, "CDKT")]
    assert sum(1 for l in logs if "bỏ khỏi các lượt sau" in l) == 2


def test_trang_bi_loai_khong_con_la_ung_vien_cuu_ocr(monkeypatch):
    """Trang bị loại biến mất khỏi scope nên _trang_sap ở lượt sau không thể
    chọn nó -> hết luôn 2 lượt OCR cứu (một lượt ở DPI+100) mỗi lượt DPI."""
    scope_goc = [(0, "CDKT"), (1, "CDKT"), (2, "CDKT")]
    scope_thay = []

    def fake_extract(doc, **kw):
        scope_thay.append(list(kw["scope"]))
        meta = {"_trang_khong_ma": [1]} if len(scope_thay) == 1 else {}
        return {k: {} for k in T.STATEMENTS}, [], meta

    monkeypatch.setattr(P, "extract", fake_extract)
    monkeypatch.setattr(P, "locate_pages", lambda doc, **kw: list(scope_goc))
    P.extract_consensus(object(), dpis=(180, 235))

    sap_luot_2 = P._trang_sap(scope_thay[1], {0: [], 2: []},
                              {"CDKT": set(), "KQHDKD": set(), "LCTT": set()})
    assert 1 not in [p for p, _ in sap_luot_2]
