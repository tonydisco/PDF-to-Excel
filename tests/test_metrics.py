# -*- coding: utf-8 -*-
from tests.regression import metrics as M


def test_canon_bo_so_khong_dung_dau():
    assert M.canon("01") == M.canon("1")
    assert M.canon("270") == "270"
    assert M.canon("411a") == "411a"


def test_compare_dem_dung_bon_loai():
    expected = {"1": (100, 90), "10": (200, 180), "20": (300, None), "30": (5, 5)}
    actual = {"1": (100, 90),        # đúng, đúng
              "10": (999, None),     # lệch, sót
              "20": (300, None),     # đúng, (đáp án rỗng -> bỏ qua)
              "40": (7, None)}       # thừa
    r = M.compare(expected, actual)
    assert r["dung"] == 3     # 1/cur, 1/prior, 20/cur
    assert r["lech"] == 1     # 10/cur
    assert r["sot"] == 3      # 10/prior, 30/cur, 30/prior
    assert r["thua"] == 1     # 40/cur


def test_compare_khop_du_lech_so_khong_dung_dau():
    """Đáp án in '1', app có thể xuất '01' — phải khớp."""
    assert M.compare({"1": (5, None)}, {"01": (5, None)})["dung"] == 1


def test_compare_dap_an_bang_0_tinh_la_thua():
    """Đáp án = 0 nghĩa là 'không có số liệu': máy bóc ra số -> phải đếm
    'thừa', tuyệt đối không phải 'lệch' (chốt quy tắc g != 0)."""
    r = M.compare({"1": (0, None)}, {"1": (5, None)})
    assert r["thua"] == 1
    assert r["lech"] == 0


def test_coverage_ty_le_dong_co_gia_tri():
    assert M.coverage({}, "CDKT") == 0.0
    full = {c: (1, 1) for c in M._codes("CDKT")}
    assert M.coverage(full, "CDKT") == 1.0


def test_balance_score_dem_phep_kiem_tra_dat():
    can_doi = {"100": (60, 60), "200": (40, 40), "270": (100, 100),
               "300": (30, 30), "400": (70, 70), "440": (100, 100)}
    dat, tong = M.balance_score(can_doi)
    assert dat == tong and tong == 6      # 3 phép x 2 cột

    lech = dict(can_doi, **{"270": (999, 100)})
    dat2, tong2 = M.balance_score(lech)
    assert dat2 < tong2
