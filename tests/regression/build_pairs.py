# -*- coding: utf-8 -*-
"""
Đề xuất cặp (PDF, Excel đáp án) để dựng bộ hồi quy.

QUY TẮC SỐNG CÒN: mã công ty CHỈ lấy từ tên THƯ MỤC tổ tiên khớp '^NN[._ -]'.
Lấy từ tên file sẽ ghép nhầm công ty — đã kiểm chứng: file
'1 Can doi ke toan 06 thang dau 2025.xlsx' nằm trong thư mục
'27_Cty CP SXKD Hàng XK Tân Bình 6Th_2025/' nhưng số '1' ở đầu tên file lại
nối nó với '01_CTCP DVTH Saigon 2025 (Riêng).pdf'.

Khớp (mã, năm, kỳ) CHƯA đủ — mã công ty chỉ duy nhất TRONG một thư mục năm,
không duy nhất toàn corpus. Bốn lớp lọc bổ sung (mỗi lần loại đều được ĐẾM,
không bao giờ lặng lẽ vứt):
  A. Trùng danh tính công ty: hai phía phải chung >= 2 token tên (đã bỏ dấu,
     bỏ từ đệm) — đã kiểm chứng '10_BCTC kiem toan Bac Au.pdf' (Bắc Âu) từng
     ghép với '10_BCTC chua kiem toan Volvo/CDSPS.xlsx' (Volvo) vì cùng số 10.
  B. Cùng cơ sở lập (kiểm toán vs tự lập — số liệu sau kiểm toán được điều
     chỉnh hợp pháp, không so được) và cùng phạm vi (hợp nhất vs riêng).
     Phân loại đọc mọi bản sao THẬT trong khóa — cùng tên file VÀ trùng
     nội dung từng byte (SHA-256) — vì bản sao ở cây 'BCTC - Da kiem toan
     .../' mang mốc mà bản sao ở cây trần không có (xem _merged_labels).
     Trùng tên nhưng KHÁC nội dung là sổ khác (vd. cùng 'CDKT quy 2.2016.xls'
     dưới '(Rieng)/' và '(Hop nhat)/'): nhãn giữ riêng từng bản, không trộn;
     khi các bản khác-nội-dung cùng tên khẳng định ĐỐI NGHỊCH nhau mà bản
     đại diện không tự khẳng định được thì danh tính tranh chấp — cặp bị
     loại có đếm (loai_xung_dot_ban_sao). UNKNOWN không bị loại nhưng được
     đếm để người xác nhận biết cặp nào đứng trên cơ sở chưa kiểm chứng.
  C. PDF xuất đơn lẻ một loại báo cáo (vd. 'cdps_6t.pdf' chỉ có 4 trang bảng
     cân đối phát sinh) chỉ được ghép với Excel cùng loại đó.
  Cuối cùng gộp các bản sao do corpus nhân đôi cây thư mục ('BCTC 3/',
  'BCTC 4/'...): trùng cả (mã, năm, kỳ, loại, tên file PDF, tên file Excel)
  VÀ trùng nội dung từng byte ở CẢ HAI phía thì giữ bản đầu tiên theo thứ
  tự đường dẫn; cùng tên nhưng khác nội dung là hai cặp riêng biệt, cả hai
  sống sót. File không đọc được khi băm -> coi là duy nhất, không bị gộp.

Kết quả của module này là ĐỀ XUẤT. Người phải xác nhận rồi mới đóng băng vào
pairs.json — xem hướng dẫn ở cuối file.
"""
import os
import re
import glob
import hashlib
import json
import unicodedata

from . import groundtruth

_DIR_INDEX = re.compile(r"^(\d{1,2})[._\s-]")
_YEAR = re.compile(r"(20\d{2})")


def _strip_accents(s):
    s = s.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c)).lower()


def company_index(path):
    """Mã công ty, lấy từ thư mục tổ tiên GẦN NHẤT có dạng 'NN_...'."""
    parts = os.path.dirname(path).split(os.sep)
    for d in reversed(parts):
        m = _DIR_INDEX.match(d)
        if m:
            return m.group(1).lstrip("0") or "0"
    return ""


def year(path):
    ys = _YEAR.findall(path)
    return ys[-1] if ys else ""


def period(path):
    t = _strip_accents(path)
    if re.search(r"6\s*th|06 thang|\b6t\b|_6t|ban nien", t):
        return "6T"
    for pat, name in ((r"quy\s*4|\bq4\b|\bqiv\b|quy iv\b", "Q4"),
                      (r"quy\s*3|\bq3\b|\bqiii\b|quy iii\b", "Q3"),
                      (r"quy\s*2|\bq2\b|\bqii\b|quy ii\b", "Q2"),
                      (r"quy\s*1|\bq1\b|\bqi\b|quy i\b", "Q1")):
        if re.search(pat, t):
            return name
    return "NAM"


def _pdf_company(path):
    """PDF có thể mang mã ở tên file (vd '33_Cty CP DL Dak Lak 2024.pdf')."""
    c = company_index(path)
    if c:
        return c
    m = _DIR_INDEX.match(os.path.basename(path))
    return (m.group(1).lstrip("0") or "0") if m else ""


# ----------------------------------------------------------------------
# Lọc A — trùng danh tính công ty. Mã số chỉ duy nhất TRONG một thư mục năm
# (đã kiểm chứng: Bắc Âu và Volvo cùng mang số 10 năm 2018), nên hai phía
# phải chung tên công ty thật sự, không chỉ chung con số.
# ----------------------------------------------------------------------
_MIN_SHARED_TOKENS = 2

# Từ đệm KHÔNG được dùng làm bằng chứng trùng tên công ty. Gồm 3 nhóm:
#   1. từ đệm pháp nhân/hồ sơ theo brief: cty, ctcp, cong, ty, co, phan,
#      tnhh, mtv, bctc, nam, quy (token chứa chữ số bị loại riêng bên dưới,
#      bao trùm luôn 'năm 2016', '6t2025', 'q2'...);
#   2. từ vựng cơ sở lập / phạm vi / trạng thái: nếu tính chúng, cặp Bắc Âu
#      vs Volvo sẽ "trùng tên" chỉ nhờ 2 token {kiem, toan} — đúng lỗi mà
#      lớp lọc này sinh ra để chặn;
#   3. từ vựng nhãn hồ sơ chung (bao, cao, tai, chinh, quyet) — hai công ty
#      khác nhau vẫn cùng có 'Bao cao tai chinh' trong tên thư mục.
# LƯU Ý: 'thang' KHÔNG phải từ đệm — 'Cty CP DL KS Tháng Mười' dùng nó làm
# tên riêng, loại nó sẽ giết cặp thật của công ty 21.
_TU_DEM = frozenset((
    "cty", "ctcp", "cong", "ty", "co", "phan", "tnhh", "mtv", "bctc",
    "nam", "quy",
    "kiem", "toan", "soat", "xet", "chua", "lap", "rieng", "audited",
    "hop", "nhat",
    "bao", "cao", "tai", "chinh", "quyet",
))


def _norm_text(s):
    """Bỏ dấu, hạ chữ thường, mọi ký tự không chữ-số thành 1 khoảng trắng."""
    t = _strip_accents(s)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split())


def _identity_text(path, dung_ten_file):
    """
    Chuỗi tên công ty của một phía: phần chữ SAU tiền tố số 'NN[._ -]' của
    thư mục tổ tiên GẦN NHẤT mang tiền tố đó. Với PDF (dung_ten_file=True),
    nếu không thư mục tổ tiên nào mang mã thì lấy từ chính tên file (bỏ đuôi)
    — nhất quán với cách _pdf_company suy ra mã. Excel KHÔNG bao giờ lấy từ
    tên file (xem QUY TẮC SỐNG CÒN đầu module). Trả về '' nếu không có.

    Lưu ý ca 'BCTC 2018_BenthanhMuine_chuakiemtoan/5.pdf': _pdf_company vẫn
    ra mã 5 (khớp '5.' trên tên file đủ đuôi), nhưng sau khi bỏ đuôi thì '5'
    trần trụi không còn khớp '^NN[._ -]' — trả về '' và lớp lọc A loại cặp
    theo đúng quy tắc "không có chữ nào ngoài con số thì không tin".
    """
    parts = os.path.dirname(path).split(os.sep)
    for d in reversed(parts):
        m = _DIR_INDEX.match(d)
        if m:
            return d[m.end():]
    if dung_ten_file:
        base = os.path.splitext(os.path.basename(path))[0]
        m = _DIR_INDEX.match(base)
        if m:
            return base[m.end():]
    return ""


def _company_tokens(text):
    """Tập token tên công ty: >= 3 ký tự, không chứa chữ số, không từ đệm."""
    toks = set()
    for tok in _norm_text(text).split():
        if len(tok) < 3 or tok in _TU_DEM:
            continue
        if any(ch.isdigit() for ch in tok):
            continue
        toks.add(tok)
    return toks


def _same_company(pdf_rel, excel_rel):
    """True nếu hai phía chung >= 2 token tên công ty. Phía nào không còn
    chữ nào ngoài con số thì KHÔNG tin — trả về False."""
    a = _company_tokens(_identity_text(pdf_rel, True))
    b = _company_tokens(_identity_text(excel_rel, False))
    if not a or not b:
        return False
    return len(a & b) >= _MIN_SHARED_TOKENS


# ----------------------------------------------------------------------
# Lọc B — cơ sở lập và phạm vi, phân loại theo TOÀN BỘ đường dẫn (đã bỏ dấu,
# đệm khoảng trắng hai đầu để so cụm theo ranh giới từ).
# 'chua kiem toan' CHỨA 'kiem toan' nên nhóm TULAP phải xét TRƯỚC KIEMTOAN.
# ----------------------------------------------------------------------
_TULAP_MARKS = (" tu lap ", " chua kiem toan ", " chua ky ")
_KIEMTOAN_MARKS = (" da kiem toan ", " kiem toan ", " soat xet ", " audited ")
_HN_MARKS = (" hop nhat ", " hn ")
# 'cty me' là dạng viết tắt thật trên corpus ('00_TCT Ben Thanh_BCTC Cty me
# Q3.2016.pdf') của 'cong ty me' — bổ sung để không bỏ sót phạm vi RIENG.
_RIENG_MARKS = (" rieng ", " cong ty me ", " cty me ")


def basis_of(path):
    """Cơ sở lập suy từ đường dẫn: 'KIEMTOAN' / 'TULAP' / 'UNKNOWN'."""
    t = " %s " % _norm_text(path)
    if any(m in t for m in _TULAP_MARKS):
        return "TULAP"
    if any(m in t for m in _KIEMTOAN_MARKS):
        return "KIEMTOAN"
    return "UNKNOWN"


def scope_of(path):
    """Phạm vi suy từ đường dẫn: 'HN' / 'RIENG' / 'UNKNOWN'.

    Đường dẫn chứa CẢ HAI loại mốc (vd. bộ 'BCTC riêng và hợp nhất') là nhập
    nhằng — trả về 'UNKNOWN', không đoán đại một phía.
    """
    t = " %s " % _norm_text(path)
    hn = any(m in t for m in _HN_MARKS)
    rieng = any(m in t for m in _RIENG_MARKS)
    if hn and rieng:
        return "UNKNOWN"
    if hn:
        return "HN"
    if rieng:
        return "RIENG"
    return "UNKNOWN"


def _pair_label(a, b):
    """Nhãn chung của cặp: chỉ khẳng định khi CẢ HAI phía cùng khẳng định.
    Một phía UNKNOWN nghĩa là cặp đứng trên cơ sở chưa kiểm chứng -> UNKNOWN
    (được đếm riêng trong thống kê, không lặng lẽ coi như đã khớp)."""
    return a if a == b else "UNKNOWN"


def _content_digest(path, cache):
    """SHA-256 nội dung file, đọc theo khối 1 MiB; mỗi file chỉ băm đúng một
    lần mỗi lượt chạy nhờ `cache` (dict đường dẫn -> digest). Trả về None
    nếu không đọc được — file đó phải được coi là DUY NHẤT: không mượn nhãn
    của ai, không bị gộp với ai (nhất quán nguyên tắc không lặng lẽ vứt
    dữ liệu)."""
    if path in cache:
        return cache[path]
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                h.update(chunk)
        digest = h.hexdigest()
    except OSError:
        digest = None
    cache[path] = digest
    return digest


def _merged_labels(rep, copies, corpus_root, cache):
    """
    (basis, scope, xung_dot) cho file đại diện `rep`, hợp nhất nhãn trên các
    bản sao THẬT trong `copies` — cùng tên file trong cùng khóa (mã, năm, kỳ)
    VÀ trùng nội dung từng byte với `rep` (SHA-256). `rep` và `copies` là
    đường dẫn tuyệt đối; nhãn luôn phân loại trên đường dẫn TƯƠNG ĐỐI trong
    corpus (thành phần ngoài corpus không được ảnh hưởng).

    Corpus nhân đôi nội dung qua 'BCTC 3/', 'BCTC 4/'... nên cùng một file có
    thể nằm ở cả cây CÓ đánh dấu lẫn cây KHÔNG đánh dấu — đã kiểm chứng:
    '30.Cty TNHH Ben Thanh - Sao Thuy 2023.pdf' vừa nằm trần ở 'BTG document/
    BCTC/' (không dấu hiệu gì) vừa nằm trong 'BCTC - Da kiem toan 2023/'.
    Nếu chỉ phân loại theo đường dẫn của bản sao được chọn (bản ngắn nhất,
    không đánh dấu) thì mốc kiểm toán bị che mất và cặp kiểm-toán-vs-tự-lập
    lọt lưới. Vì vậy: bản sao có đánh dấu nói hộ cho bản sao không đánh dấu.

    NHƯNG "bản sao" phải là bản sao THẬT — trùng tên file KHÔNG đủ:
    '05_... (Rieng)/CDKT quy 2.2016.xls' và '05_... (Hop nhat)/CDKT quy
    2.2016.xls' cùng khóa, cùng tên mà là HAI SỔ khác nhau (riêng vs hợp
    nhất). Trộn nhãn của chúng -> UNKNOWN sẽ vô hiệu hóa lọc HN-vs-RIENG
    đúng chỗ cần nó nhất. Quy tắc:
      - Chỉ bản TRÙNG nội dung với rep mới được hợp nhất nhãn; trong cùng
        nhóm nội dung mà nhãn khẳng định MÂU THUẪN nhau (vd. cùng một file
        nằm dưới cả cây 'Da kiem toan' lẫn 'tu lap') -> UNKNOWN, không
        đoán đại (giữ hành vi cũ cho bản sao thật).
      - Bản KHÁC nội dung (hoặc không đọc được -> coi là duy nhất) giữ nhãn
        riêng, không trộn vào rep.
      - xung_dot=True khi nhóm của rep không tự khẳng định được (UNKNOWN)
        mà các bản khác-nội-dung cùng tên lại khẳng định ĐỐI NGHỊCH nhau
        (KIEMTOAN vs TULAP, hoặc HN vs RIENG): tên file đang trỏ tới những
        sổ mâu thuẫn — bên gọi phải loại cặp và ĐẾM (loai_xung_dot_ban_sao),
        không được lặng lẽ coi là UNKNOWN.
    """
    rep_digest = _content_digest(rep, cache)
    nhom_rep = []      # đường dẫn tương đối của rep + các bản sao thật
    nhan_le = []       # đường dẫn tương đối của các bản cùng tên KHÁC nội dung
    for q in copies:
        rel = os.path.relpath(q, corpus_root)
        if q == rep:
            nhom_rep.append(rel)
        elif rep_digest is not None and _content_digest(q, cache) == rep_digest:
            nhom_rep.append(rel)
        else:
            nhan_le.append(rel)

    bases = {basis_of(p) for p in nhom_rep}
    bases.discard("UNKNOWN")
    scopes = {scope_of(p) for p in nhom_rep}
    scopes.discard("UNKNOWN")
    b = bases.pop() if len(bases) == 1 else "UNKNOWN"
    s = scopes.pop() if len(scopes) == 1 else "UNKNOWN"

    xung_dot = False
    if nhan_le:
        bases_le = {basis_of(p) for p in nhan_le}
        scopes_le = {scope_of(p) for p in nhan_le}
        if b == "UNKNOWN" and {"KIEMTOAN", "TULAP"} <= bases_le:
            xung_dot = True
        if s == "UNKNOWN" and {"HN", "RIENG"} <= scopes_le:
            xung_dot = True
    return b, s, xung_dot


def build_with_stats(corpus_root):
    """
    Như build() nhưng trả thêm thống kê loại bỏ: (danh sách cặp, stats).

    stats — mọi cặp ứng viên bị loại đều được đếm, không bao giờ lặng lẽ vứt:
      ung_vien             : số cặp khớp (mã, năm, kỳ) TRƯỚC khi lọc
      loai_khac_cong_ty    : lọc A — danh tính công ty không trùng
      loai_khac_co_so      : lọc B — kiểm toán vs tự lập
      loai_khac_pham_vi    : lọc B — hợp nhất vs riêng
      loai_xung_dot_ban_sao: lọc B — cùng tên file trong khóa nhưng KHÁC nội
                             dung và nhãn đối nghịch nhau (danh tính tranh
                             chấp, xem _merged_labels)
      loai_khac_loai_bc    : lọc C — PDF đơn lẻ khác loại báo cáo
      gop_ban_sao          : bản sao thật (trùng cả nội dung) đã gộp
      co_so_chua_xac_minh  : cặp SỐNG SÓT có basis UNKNOWN
      pham_vi_chua_xac_minh: cặp SỐNG SÓT có scope UNKNOWN
    """
    pdfs = {}
    excels = []
    for f in glob.glob(os.path.join(corpus_root, "**", "*"), recursive=True):
        if not os.path.isfile(f):
            continue
        low = f.lower()
        if low.endswith(".pdf"):
            c, y = _pdf_company(f), year(f)
            if c and y:
                pdfs.setdefault((c, y, period(f)), []).append(f)
        elif low.endswith((".xls", ".xlsx", ".xlsm")) and groundtruth.statement_kind(f):
            excels.append(f)

    # Nhóm các bản sao Excel cùng (mã, năm, kỳ, tên file) để lọc B phân loại
    # trên MỌI bản sao (xem _merged_labels) — đối xứng với phía PDF.
    ex_keyed = []
    ex_groups = {}
    for x in excels:
        c, y, p = company_index(x), year(x), period(x)
        if not (c and y):
            continue
        ex_keyed.append((x, c, y, p))
        ex_groups.setdefault(
            (c, y, p, os.path.basename(x)), []).append(x)

    stats = {
        "ung_vien": 0,
        "loai_khac_cong_ty": 0,
        "loai_khac_co_so": 0,
        "loai_khac_pham_vi": 0,
        "loai_xung_dot_ban_sao": 0,
        "loai_khac_loai_bc": 0,
        "gop_ban_sao": 0,
        "co_so_chua_xac_minh": 0,
        "pham_vi_chua_xac_minh": 0,
    }
    bang_bam = {}   # cache digest nội dung: mỗi file chỉ băm 1 lần mỗi lượt
    raw = []
    for x, c, y, p in ex_keyed:
        cands = pdfs.get((c, y, p))
        if not cands:
            continue
        # tên ngắn nhất = ít hậu tố nhất; thêm khóa phụ theo chuỗi để kết quả
        # ổn định khi hai bản sao dài bằng nhau (glob không đảm bảo thứ tự)
        pdf = min(cands, key=lambda s: (len(s), s))
        stats["ung_vien"] += 1

        # Mọi phân loại chỉ nhìn phần đường dẫn BÊN TRONG corpus — thành phần
        # bên ngoài (tên máy, thư mục tạm của pytest...) không được phép ảnh
        # hưởng tới danh tính/cơ sở lập/phạm vi.
        pdf_rel = os.path.relpath(pdf, corpus_root)
        x_rel = os.path.relpath(x, corpus_root)

        if not _same_company(pdf_rel, x_rel):               # lọc A
            stats["loai_khac_cong_ty"] += 1
            continue
        # Lọc B trên nhãn hợp nhất của các bản sao THẬT (cùng tên VÀ trùng
        # nội dung) trong khóa; bản cùng tên khác nội dung là sổ khác — nhãn
        # giữ riêng, khẳng định đối nghịch thì loại (xem _merged_labels).
        pdf_copies = [q for q in cands
                      if os.path.basename(q) == os.path.basename(pdf)]
        x_copies = ex_groups[(c, y, p, os.path.basename(x))]
        b_pdf, s_pdf, xd_pdf = _merged_labels(pdf, pdf_copies,
                                              corpus_root, bang_bam)
        b_x, s_x, xd_x = _merged_labels(x, x_copies, corpus_root, bang_bam)
        if {b_pdf, b_x} == {"KIEMTOAN", "TULAP"}:           # lọc B: cơ sở lập
            stats["loai_khac_co_so"] += 1
            continue
        if {s_pdf, s_x} == {"HN", "RIENG"}:                 # lọc B: phạm vi
            stats["loai_khac_pham_vi"] += 1
            continue
        if xd_pdf or xd_x:                    # lọc B: xung đột bản sao giả
            stats["loai_xung_dot_ban_sao"] += 1
            continue
        kind = groundtruth.statement_kind(x)
        pdf_kind = groundtruth.statement_kind(pdf)          # lọc C
        if pdf_kind and pdf_kind != kind:
            stats["loai_khac_loai_bc"] += 1
            continue

        raw.append({
            "pdf": pdf,
            "excel": x,
            "kind": kind,
            "company": c,
            "year": y,
            "period": p,
            "basis": _pair_label(b_pdf, b_x),
            "scope": _pair_label(s_pdf, s_x),
        })

    # Gộp bản sao: corpus nhân đôi nội dung qua 'BCTC 3/', 'BCTC 4/'...
    # Chỉ gộp bản sao THẬT — trùng tên file VÀ trùng nội dung từng byte ở
    # CẢ HAI phía; cùng tên nhưng khác nội dung là hai cặp riêng biệt (vd.
    # sổ riêng vs sổ hợp nhất cùng tên), cả hai phải sống sót. File không
    # đọc được -> coi là duy nhất, không bao giờ gộp.
    # Sắp xếp trước để "bản đầu tiên được giữ" ổn định theo đường dẫn.
    raw.sort(key=lambda d: (d["company"], d["year"], d["period"], d["kind"],
                            d["pdf"], d["excel"]))
    seen = set()
    out = []
    for d in raw:
        bam_pdf = _content_digest(d["pdf"], bang_bam)
        bam_x = _content_digest(d["excel"], bang_bam)
        if bam_pdf is None or bam_x is None:
            out.append(d)
            continue
        key = (d["company"], d["year"], d["period"], d["kind"],
               os.path.basename(d["pdf"]), os.path.basename(d["excel"]),
               bam_pdf, bam_x)
        if key in seen:
            stats["gop_ban_sao"] += 1
            continue
        seen.add(key)
        out.append(d)

    for d in out:
        if d["basis"] == "UNKNOWN":
            stats["co_so_chua_xac_minh"] += 1
        if d["scope"] == "UNKNOWN":
            stats["pham_vi_chua_xac_minh"] += 1
    return out, stats


def build(corpus_root):
    """Trả về danh sách cặp đề xuất, khớp cả (mã công ty, năm, kỳ) rồi qua
    các lớp lọc A/B/C và gộp bản sao (xem docstring đầu module). Mỗi cặp có
    thêm 2 khóa 'basis' và 'scope'. Cần số liệu loại bỏ thì dùng
    build_with_stats()."""
    return build_with_stats(corpus_root)[0]


def main():
    root = os.environ.get(
        "BCTC_CORPUS", "/Users/motmi/Documents/DAYS/Y-NHI/BTG/Documents")
    pairs, stats = build_with_stats(root)
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(here, "pairs.candidate.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"pairs": pairs}, fh, ensure_ascii=False, indent=2)

    print("TỔNG KẾT LOẠI BỎ (không cặp nào bị vứt lặng lẽ):")
    print("  Ứng viên khớp (mã, năm, kỳ):              %3d" % stats["ung_vien"])
    print("  Loại A  — khác danh tính công ty:         %3d" % stats["loai_khac_cong_ty"])
    print("  Loại B  — kiểm toán vs tự lập:            %3d" % stats["loai_khac_co_so"])
    print("  Loại B  — hợp nhất vs riêng:              %3d" % stats["loai_khac_pham_vi"])
    print("  Loại B  — xung đột bản sao khác nội dung: %3d" % stats["loai_xung_dot_ban_sao"])
    print("  Loại C  — PDF đơn lẻ khác loại báo cáo:   %3d" % stats["loai_khac_loai_bc"])
    print("  Gộp bản sao thật (trùng nội dung):        %3d" % stats["gop_ban_sao"])
    print("Đã đề xuất %d cặp (%d PDF riêng biệt) -> %s"
          % (len(pairs), len({p["pdf"] for p in pairs}), out_path))
    print("  trong đó: cơ sở lập chưa xác minh %d cặp, phạm vi chưa xác minh %d cặp"
          % (stats["co_so_chua_xac_minh"], stats["pham_vi_chua_xac_minh"]))

    print("\nNGƯỜI PHẢI XÁC NHẬN trước khi dùng:")
    print("  1. Mở pairs.candidate.json, đối chiếu từng cặp — ưu tiên soi các")
    print("     cặp basis/scope UNKNOWN (chưa kiểm chứng được từ đường dẫn).")
    print("  2. Xoá cặp sai phạm vi (riêng vs hợp nhất) hoặc sai kỳ.")
    print("  3. Đổi tên thành pairs.json rồi commit.")
    for p in pairs:
        print("  CT%-3s %s %-4s %-7s %-8s %-7s %s  <-  %s"
              % (p["company"], p["year"], p["period"], p["kind"],
                 p["basis"], p["scope"],
                 os.path.basename(p["excel"])[:30],
                 os.path.basename(p["pdf"])[:44]))


if __name__ == "__main__":
    main()
