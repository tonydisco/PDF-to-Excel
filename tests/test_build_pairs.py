# -*- coding: utf-8 -*-
import pytest

from tests.regression import build_pairs as B
from tests.regression import groundtruth as G


def test_company_index_chi_lay_tu_ten_thu_muc():
    """Cạm bẫy chính: số đầu TÊN FILE không phải mã công ty."""
    p = "/x/Quy 2.2025/27_Cty CP SXKD Hang XK Tan Binh 6Th_2025/1 Can doi ke toan.xlsx"
    assert B.company_index(p) == "27"      # KHÔNG được ra '1'


def test_company_index_bo_so_khong_dung_dau():
    assert B.company_index("/x/01_CTCP DVTH Saigon/CDKT.XLS") == "1"


def test_company_index_rong_khi_khong_co():
    assert B.company_index("/x/BCTC 2023/CDKT.XLS") == ""


def test_period_nhan_dien():
    assert B.period("/x/27_Cty 6Th_2025/1 Can doi ke toan 06 thang dau 2025.xlsx") == "6T"
    assert B.period("/x/QUY II.2022/CDKT Q2.xls") == "Q2"
    assert B.period("/x/2024/CDKT.XLS") == "NAM"


def test_year_lay_nam_cuoi_cung():
    assert B.year("/x/BCTC 2023/Quy 2/CDKT 2024.xls") == "2024"
    assert B.year("/x/khong co nam/CDKT.xls") == ""


def test_build_khong_ghep_khac_cong_ty(corpus_root):
    """Mọi cặp sinh ra phải cùng mã công ty, cùng năm, cùng kỳ."""
    pairs = B.build(corpus_root)
    assert pairs, "Không sinh được cặp nào"
    for p in pairs:
        assert B.company_index(p["excel"]) == p["company"]
        assert B.year(p["pdf"]) == p["year"]
        assert B.period(p["pdf"]) == p["period"]
        # 2 khóa mới phải có mặt và hợp lệ trên MỌI cặp
        assert p["basis"] in ("KIEMTOAN", "TULAP", "UNKNOWN")
        assert p["scope"] in ("HN", "RIENG", "UNKNOWN")
        # Lọc C: PDF xuất đơn lẻ một loại thì cặp phải đúng loại đó
        pdf_kind = G.statement_kind(p["pdf"])
        assert pdf_kind in ("", p["kind"])


# ---------------------------------------------------------------------------
# Các lớp lọc A/B/C và gộp bản sao — kiểm bằng cây thư mục giả lập (tmp_path,
# không cần corpus). build() không đọc nội dung file nên file rỗng là đủ.
# ---------------------------------------------------------------------------
def _lam_corpus(tmp_path, rel_paths):
    """Dựng cây corpus giả: tạo file stub cho từng đường dẫn tương đối."""
    for rel in rel_paths:
        f = tmp_path.joinpath(*rel.split("/"))
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"stub")
    return str(tmp_path)


def test_loc_A_bac_au_volvo_cung_so_10_bi_loai(tmp_path):
    """Ca đã kiểm chứng trên corpus thật: Bắc Âu và Volvo cùng mang số 10
    trong năm 2018 (mã chỉ duy nhất TRONG thư mục năm). 'kiem toan' /
    'chua kiem toan' là từ vựng cơ sở lập, không được tính làm bằng chứng
    trùng tên công ty."""
    root = _lam_corpus(tmp_path, [
        "BCTC 3/2018/Nam 2018/10_BCTC kiem toan Bac Au.pdf",
        "BCTC 4/2018/Nam 2018/10_BCTC chua kiem toan Volvo/CDSPS.xlsx",
    ])
    pairs, stats = B.build_with_stats(root)
    assert pairs == []
    assert stats["ung_vien"] == 1
    assert stats["loai_khac_cong_ty"] == 1


def test_loc_A_pdf_chi_co_con_so_khong_ten_bi_loai(tmp_path):
    """Ca thật '.../BCTC 2018_BenthanhMuine_chuakiemtoan/5.pdf': tên file chỉ
    có con số, không mảnh tên công ty nào -> không tin, phải loại."""
    root = _lam_corpus(tmp_path, [
        "Nam 2018/Bo bao cao khac/5.pdf",
        "Nam 2018/05_Cty CP VHTH Ben Thanh_BCTC 2018/CDKT2018.xls",
    ])
    pairs, stats = B.build_with_stats(root)
    assert pairs == []
    assert stats["loai_khac_cong_ty"] == 1


def test_loc_B_kiem_toan_vs_tu_lap_bi_loai(tmp_path):
    """Ca đã kiểm chứng (cty 33 năm 2023/2024, cty 7 năm 2023): PDF đã kiểm
    toán không so được với Excel tự lập — điều chỉnh kiểm toán thay đổi số
    liệu hợp pháp."""
    root = _lam_corpus(tmp_path, [
        "BCTC - Da kiem toan 2023/33_Cty CP DL Dak Lak 2023 (kiem toan).pdf",
        "BCTC - tu lap 2023/33_Cty CP DL Dak Lak 2023/CDKT.XLS",
    ])
    pairs, stats = B.build_with_stats(root)
    assert pairs == []
    assert stats["loai_khac_co_so"] == 1
    assert stats["loai_khac_cong_ty"] == 0   # danh tính trùng, chỉ cơ sở lệch


def test_loc_B_ban_sao_mang_moc_kiem_toan_noi_ho_ban_tran(tmp_path):
    """Ca đã kiểm chứng (cty 30 năm 2023): CÙNG một PDF nằm ở hai nơi — bản
    trần 'BCTC/30...pdf' (không dấu hiệu gì) và bản trong 'BCTC - Da kiem
    toan 2023/'. Bản ngắn nhất (trần) được chọn, nhưng mốc kiểm toán của bản
    sao kia vẫn phải được đọc — nếu không, cặp kiểm-toán-vs-tự-lập lọt lưới
    với basis UNKNOWN."""
    root = _lam_corpus(tmp_path, [
        "BCTC/30.Cty TNHH Ben Thanh - Sao Thuy 2023.pdf",
        "BCTC 5/2023/BCTC - Da kiem toan 2023/30.Cty TNHH Ben Thanh - Sao Thuy 2023.pdf",
        "BCTC 5/2023/BCTC - tu lap 2023/30_Cty TNHH Ben Thanh - Sao Thuy 2023 (tu lap, chua ky)/2. Bang can doi ke toan 2023.xlsx",
    ])
    pairs, stats = B.build_with_stats(root)
    assert pairs == []
    assert stats["loai_khac_co_so"] == 1


def test_loc_B_hop_nhat_vs_rieng_bi_loai(tmp_path):
    """Ca đã kiểm chứng (cty 5 Q2/2016): PDF hợp nhất ('BCTC HN soát xét')
    không so được với bộ Excel công ty riêng."""
    root = _lam_corpus(tmp_path, [
        "Quy 2.2016/05-Cty CP VHTH Ben Thanh_BCTC HN soat xet 6T2016.pdf",
        "Quy 2.2016/05_Cty CP VHTH Ben Thanh (Rieng)/CDKT quy 2.2016.xls",
    ])
    pairs, stats = B.build_with_stats(root)
    assert pairs == []
    assert stats["loai_khac_pham_vi"] == 1
    assert stats["loai_khac_co_so"] == 0     # KIEMTOAN vs UNKNOWN được phép


def test_loc_C_pdf_don_le_chi_giu_dung_loai(tmp_path):
    """Ca đã kiểm chứng (cty 18 năm 2024 6T): 'cdps_6t.pdf' chỉ chứa bảng cân
    đối phát sinh (4 trang) — ghép với CDKT/KQHDKD/LCTT thì mọi phép so đều
    ra 100% thiếu. Chỉ cặp CDPS được giữ."""
    root = _lam_corpus(tmp_path, [
        "Quy 2/18_Cty CP Sai gon Mui Ne 2024/BC 6T.2024/cdps_6t.pdf",
        "Quy 2/18_Cty CP Sai gon Mui Ne 2024/BC 6T.2024/cdkt_30.06.2024.xls",
        "Quy 2/18_Cty CP Sai gon Mui Ne 2024/BC 6T.2024/cdps 6t.xls",
        "Quy 2/18_Cty CP Sai gon Mui Ne 2024/BC 6T.2024/KQKD_6T.xls",
        "Quy 2/18_Cty CP Sai gon Mui Ne 2024/BC 6T.2024/lctt_6t.xls",
    ])
    pairs, stats = B.build_with_stats(root)
    assert [p["kind"] for p in pairs] == ["CDPS"]
    assert stats["loai_khac_loai_bc"] == 3
    assert stats["ung_vien"] == 4


def test_cap_that_cung_thu_muc_song_sot_qua_moi_lop_loc(tmp_path):
    """Cặp chuẩn: cùng thư mục công ty, PDF tổng hợp (không phải xuất đơn
    lẻ) — phải sống sót qua cả A, B lẫn C, mang đủ 2 khóa mới."""
    root = _lam_corpus(tmp_path, [
        "2015/Quy 4.2015/21_Cty CP DL KS Thang Muoi_BCTC 2015/BCTC quy 4.pdf",
        "2015/Quy 4.2015/21_Cty CP DL KS Thang Muoi_BCTC 2015/Luu chuyen tien te 2015.xls",
    ])
    pairs, stats = B.build_with_stats(root)
    assert len(pairs) == 1
    p = pairs[0]
    assert (p["company"], p["year"], p["period"], p["kind"]) == ("21", "2015", "Q4", "LCTT")
    assert p["basis"] == "UNKNOWN"   # đường dẫn không nói gì về cơ sở lập
    assert p["scope"] == "UNKNOWN"
    assert stats["loai_khac_cong_ty"] == 0
    assert stats["loai_khac_co_so"] == 0
    assert stats["loai_khac_pham_vi"] == 0
    assert stats["loai_khac_loai_bc"] == 0
    assert stats["co_so_chua_xac_minh"] == 1  # UNKNOWN sống sót nhưng bị đếm
    assert stats["pham_vi_chua_xac_minh"] == 1


def test_cap_cung_co_so_kiem_toan_duoc_giu_va_ghi_nhan(tmp_path):
    """KIEMTOAN vs KIEMTOAN không bị loại và basis của cặp phải là KIEMTOAN
    (không rơi về UNKNOWN)."""
    root = _lam_corpus(tmp_path, [
        "Da kiem toan 2023/18_Cty CP Sai gon Mui Ne 2023/BCTC 2023.pdf",
        "Da kiem toan 2023/18_Cty CP Sai gon Mui Ne 2023/KQKD_2023.xls",
    ])
    pairs, stats = B.build_with_stats(root)
    assert len(pairs) == 1
    assert pairs[0]["basis"] == "KIEMTOAN"
    assert stats["co_so_chua_xac_minh"] == 0


def test_gop_ban_sao_thu_muc_nhan_ban(tmp_path):
    """Corpus nhân đôi nội dung qua 'BCTC 3/', 'BCTC 4/'... — cặp trùng cả
    (mã, năm, kỳ, loại, tên file PDF, tên file Excel) chỉ giữ bản đầu tiên,
    số bản gộp phải được đếm."""
    root = _lam_corpus(tmp_path, [
        "BCTC 3/2025/Quy 2.2025/18_Cty CP Sai gon Mui Ne 6Th_2025/bctc_6t.pdf",
        "BCTC 3/2025/Quy 2.2025/18_Cty CP Sai gon Mui Ne 6Th_2025/cdkt_6t.xls",
        "BCTC 4/2025/Quy 2.2025/18_Cty CP Sai gon Mui Ne 6Th_2025/bctc_6t.pdf",
        "BCTC 4/2025/Quy 2.2025/18_Cty CP Sai gon Mui Ne 6Th_2025/cdkt_6t.xls",
    ])
    pairs, stats = B.build_with_stats(root)
    assert len(pairs) == 1
    assert stats["gop_ban_sao"] == 1
    assert stats["ung_vien"] == 2


# ---------------------------------------------------------------------------
# Bộ phân loại cơ sở lập / phạm vi — kiểm trực tiếp trên chuỗi đường dẫn.
# ---------------------------------------------------------------------------
def test_basis_of_phan_loai_theo_duong_dan():
    assert B.basis_of("/x/BCTC - Da kiem toan 2023/33_Cty A (kiem toan).pdf") == "KIEMTOAN"
    assert B.basis_of("/x/2016/05-Cty B_BCTC HN soat xet 6T2016.pdf") == "KIEMTOAN"
    assert B.basis_of("/x/BCTC - tu lap 2023/33_Cty A/CDKT.XLS") == "TULAP"
    # 'chua kiem toan' CHỨA 'kiem toan' — phải ra TULAP, không phải KIEMTOAN
    assert B.basis_of("/x/2018/10_BCTC chua kiem toan Volvo/CDSPS.xlsx") == "TULAP"
    # có dấu tiếng Việt vẫn phải nhận ra ('chưa kiểm toán' trên corpus thật)
    assert B.basis_of("/x/BCTC 2022 chưa kiểm toán/30_BCTC BT Sao Thuy.pdf") == "TULAP"
    assert B.basis_of("/x/30_Cty C 2023 (tu lap, chua ky)/2. Bang can doi ke toan.xlsx") == "TULAP"
    assert B.basis_of("/x/2016/Quy 2.2016/05_Cty B/CDKT.xls") == "UNKNOWN"


def test_scope_of_phan_loai_theo_duong_dan():
    assert B.scope_of("/x/05-Cty B_BCTC HN soat xet 6T2016.pdf") == "HN"
    assert B.scope_of("/x/11_Cty CP DV DL Ben Thanh 6Th_2025 (HN).pdf") == "HN"
    assert B.scope_of("/x/02_Cty CP TM-DV Ben Thanh_BCTC Hop nhat 2016.pdf") == "HN"
    assert B.scope_of("/x/01_CTCP DVTH Saigon 2025 (Riêng).pdf") == "RIENG"
    assert B.scope_of("/x/00_TCT Ben Thanh_BCTC Cty me Q3.2016.pdf") == "RIENG"
    # 'hn' phải là token đứng riêng, không ăn vào giữa từ ('John', 'Thanh')
    assert B.scope_of("/x/18_Cty TNHH Ben Thanh Hoang Thanh - kiem toan.pdf") == "UNKNOWN"
    # chứa CẢ HAI loại mốc -> nhập nhằng -> UNKNOWN, không đoán đại
    assert B.scope_of("/x/BCTC rieng va hop nhat 2020/CDKT.xls") == "UNKNOWN"
