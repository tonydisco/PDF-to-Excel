# -*- coding: utf-8 -*-
"""
Nhận diện 3 báo cáo trong file PDF scan và bóc tách số liệu theo Mã số.

Chiến lược:
  1) Quét nhanh dải đầu mỗi trang (DPI thấp) để định vị các trang chứa
     'Bảng cân đối kế toán' / 'Kết quả HĐKD' / 'Lưu chuyển tiền tệ'
     (yêu cầu vừa có TIÊU ĐỀ vừa có dấu hiệu BẢNG -> tránh nhầm Mục lục).
  2) OCR đầy đủ (DPI cao) các trang đã định vị, đi từ trên xuống, bám theo
     tiêu đề gần nhất để gán dòng vào đúng báo cáo, rồi map Mã số -> giá trị.
"""
import re
import os
import unicodedata
from concurrent.futures import ThreadPoolExecutor

from . import ocr
from . import templates as T
from . import textlayer
from . import workers as W

# số luồng OCR song song (mỗi luồng gọi 1 tiến trình tesseract riêng)
# Số luồng OCR mặc định (chế độ Cân bằng — chừa headroom cho giao diện/HĐH).
# Truyền tham số `workers` xuống các hàm để đổi lúc chạy mà không nạp lại module.
MAX_WORKERS = W.worker_count()


# ----------------------------------------------------------------------
# Tiện ích chuẩn hoá tiếng Việt (bỏ dấu) để so khớp tiêu đề
# ----------------------------------------------------------------------
def strip_accents(s):
    s = s.replace("đ", "d").replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def norm(s):
    return re.sub(r"\s+", " ", strip_accents(s).lower()).strip()


TITLES = {
    # "Báo cáo tình hình tài chính" = tên gọi KHÁC của Bảng cân đối kế toán (một số
    # báo cáo dùng tên này; tương đương "statement of financial position").
    "CDKT":   ["bang can doi ke toan", "bao cao tinh hinh tai chinh"],
    "KQHDKD": ["ket qua hoat dong kinh doanh", "ket qua kinh doanh"],
    "LCTT":   ["luu chuyen tien te"],
}
# B-A4: tiêu đề báo cáo TIẾNG ANH (mẫu B01/B02/B03-DN bản (en), cùng cấu trúc T200).
# Các cụm này dễ xuất hiện trong văn xuôi thuyết minh ("the income statement when...",
# "OFF BALANCE SHEET ITEMS") và mục lục -> chỉ nhận khi đứng ĐẦU dòng + dòng NGẮN.
EN_TITLES = {
    "CDKT":   ["balance sheet", "statement of financial position"],
    "KQHDKD": ["income statement", "statement of income",
               "statement of profit or loss", "profit and loss statement"],
    "LCTT":   ["cash flow statement", "statement of cash flows"],
}
MAX_HEADING_WORDS = 11   # tiêu đề là dòng NGẮN, không phải câu văn xuôi
MAX_EN_HEADING_WORDS = 5  # tiêu đề tiếng Anh còn ngắn hơn ("BALANCE SHEET")


def detect_title(text_norm):
    for key, pats in TITLES.items():
        if any(p in text_norm for p in pats):
            return key
    return None


def line_title(line_text):
    """Trả về mã báo cáo nếu DÒNG này là một TIÊU ĐỀ ngắn (không phải prose)."""
    nl = norm(line_text)
    wc = len(nl.split())
    if wc == 0:
        return None
    if wc <= MAX_HEADING_WORDS:
        k = detect_title(nl)
        if k:
            return k
    # tiếng Anh: yêu cầu khớp ở ĐẦU dòng + dòng ngắn (loại prose/mục lục/"off balance sheet")
    if wc <= MAX_EN_HEADING_WORDS:
        for key, pats in EN_TITLES.items():
            if any(nl.startswith(p) for p in pats):
                return key
    return None


def heading_in_lines(line_texts):
    """
    Quét các dòng của một trang; trả về tiêu đề báo cáo nếu đây là TRANG báo cáo.
    Bỏ qua trang Mục lục / trang bìa liệt kê nhiều tên báo cáo cùng lúc.
    """
    joined = " ".join(norm(t) for t in line_texts)
    if "muc luc" in joined:
        return None
    titles = []
    for t in line_texts:
        key = line_title(t)
        if key and key not in titles:
            titles.append(key)
    if len(titles) != 1:        # 0 = không có; >=2 = trang liệt kê (mục lục/bìa)
        return None
    return titles[0]


# Phát hiện KỲ báo cáo: QUÝ (có cột "Kỳ này"/"Lũy kế từ đầu năm") hay NĂM.
_QUARTER_RE = re.compile(r"\bquy\s*(iv|iii|ii|i|[1-4])\b")
_QUARTER_LABEL = {"i": "I", "ii": "II", "iii": "III", "iv": "IV",
                  "1": "I", "2": "II", "3": "III", "4": "IV"}
_YEAR_RE = re.compile(r"\b(20\d{2})\b")


def detect_period(line_texts):
    """Đoán kỳ báo cáo từ các dòng OCR của trang báo cáo.
    Trả: {kind: 'quarter'|'year'|'unknown', label, year?, quarter?}.
    Dấu hiệu QUÝ: có 'lũy kế' (cột lũy kế từ đầu năm) — đặc trưng báo cáo quý —
    kèm 'kỳ này' hoặc 'Quý I/II/III/IV'. Còn lại coi là báo cáo năm (nếu thấy năm)."""
    joined = " ".join(norm(t) for t in line_texts)
    qm = _QUARTER_RE.search(joined)
    years = _YEAR_RE.findall(joined)
    # năm = xuất hiện NHIỀU NHẤT (năm tài chính, không phải năm ký tên); hoà -> mới nhất
    year = max(years, key=lambda y: (years.count(y), y)) if years else None
    # CHỈ nhận QUÝ khi có dấu hiệu CỘT đặc trưng: "lũy kế từ đầu năm" (cột lũy kế của
    # báo cáo quý/giữa niên độ) HOẶC "Quý <số>" kèm cột "kỳ này". KHÔNG dùng "lũy kế"
    # trơ trọi (vì có trong "giá trị hao mòn lũy kế" - khấu hao - ở báo cáo NĂM).
    is_quarter = ("luy ke tu dau nam" in joined) or (qm is not None and "ky nay" in joined)
    if is_quarter:
        q = _QUARTER_LABEL.get(qm.group(1), qm.group(1).upper()) if qm else None
        label = (f"Quý {q}" if q else "Báo cáo quý") + (f"/{year}" if year else "")
        return {"kind": "quarter", "quarter": q, "year": year, "label": label}
    if year:
        return {"kind": "year", "year": year, "label": f"Năm {year}"}
    return {"kind": "unknown", "year": year, "quarter": None, "label": ""}


# ----------------------------------------------------------------------
# Phân tích con số kiểu Việt Nam:  1.234.567  (1.234)  -   =>  int / None
# ----------------------------------------------------------------------
# Chấp nhận cả dấu CHẤM (Việt: 1.234.567) lẫn dấu PHẨY (Anh: 1,234,567) phân cách nghìn.
# parse_number xoá hết ký tự không-số nên giá trị nguyên (đồng) ra đúng dù dùng dấu nào.
_NUM_RE = re.compile(r"^\(?\-?[\d.,\s]+\)?$")


def parse_number(tok):
    t = tok.strip().replace(" ", "")
    if t in {"-", "–", "—", "=", ".", "_", "", "ˆ"}:
        return None
    neg = t.startswith("(") or t.endswith(")")
    t = t.strip("()")
    digits = re.sub(r"\D", "", t)
    if not digits:
        return None
    val = int(digits)
    return -val if neg else val


def looks_like_value(tok):
    t = tok.strip()
    if t in {"-", "–", "—", "="}:
        return False
    if not _NUM_RE.match(t):
        return False
    digits = re.sub(r"\D", "", t)
    # giá trị tài chính thường >= 3 chữ số hoặc có dấu phân tách (chấm/phẩy)
    return len(digits) >= 3 or "." in t or "," in t


# ----------------------------------------------------------------------
# Bóc Mã số và 2 cột giá trị từ một DÒNG (list từ kèm toạ độ)
# ----------------------------------------------------------------------
_CODE_RE = re.compile(r"^(\d{1,3}[abc]?)$")


def _token_code(wd, valid_codes):
    # GIỮ NGUYÊN strict: benchmark cho thấy nới lỏng (strip ngoặc) làm lệch
    # detect_code_column -> MẤT mã tổng ở file đang tốt (05/28 HN). Dòng tổng
    # dính ngoặc ("[270") được forced_total_code bắt qua từ khoá thay vì ở đây.
    t = wd["text"].strip().rstrip(".")
    m = _CODE_RE.match(t)
    if m and m.group(1) in valid_codes:
        return m.group(1)
    return None


# Thứ tự chỉ tiêu theo template (dùng để dò ĐÚNG cột Mã số)
def _order_index(template):
    return {row[0]: n for n, row in enumerate(template) if row[0] is not None}


ORDER = {
    "CDKT":   _order_index(T.BANG_CAN_DOI_KE_TOAN),
    "KQHDKD": _order_index(T.KET_QUA_KINH_DOANH),
    "LCTT":   _order_index(T.LUU_CHUYEN_TIEN_TE_GT),
}


def detect_code_column(section_lines, valid_codes, order_index):
    """
    Vị trí cột Mã số thay đổi theo từng mẫu (trái / giữa). Cột Mã số ĐÚNG là cột
    mà các token mã (đọc từ trên xuống) khớp khung chuẩn và TĂNG DẦN theo template,
    đồng thời xuất hiện ở nhiều dòng nhất. Trả về toạ độ x (phân số) tâm cột.
    """
    from collections import defaultdict
    bins = defaultdict(list)
    for ln, *_ in section_lines:
        for wd in ln:
            code = _token_code(wd, valid_codes)
            if code:
                bins[round(wd["cx"] / 0.05)].append((wd["cy"], code, wd["cx"]))
    best_center, best_score = None, -1.0
    for toks in bins.values():
        toks.sort()
        idxs = [order_index[c] for _, c, _ in toks if c in order_index]
        if len(idxs) >= 2:
            inc = sum(1 for a, b in zip(idxs, idxs[1:]) if b > a)
            score = inc + 0.15 * len(idxs)
        else:
            score = 0.15 * len(idxs)
        if score > best_score:
            best_score = score
            best_center = sum(cx for _, _, cx in toks) / len(toks)
    return best_center


def find_code_at(words, valid_codes, col_center, tol=0.07):
    """Lấy mã số ở đúng cột đã dò (gần col_center nhất)."""
    if col_center is None:
        return find_code(words, valid_codes)
    best, best_d = None, tol
    for wd in words:
        code = _token_code(wd, valid_codes)
        if code is None:
            continue
        d = abs(wd["cx"] - col_center)
        if d <= best_d:
            best, best_d = code, d
    return best


def find_code(words, valid_codes):
    """Fallback: token mã số ưu tiên cột giữa, nếu không có thì bên trái."""
    best = None
    for wd in words:
        code = _token_code(wd, valid_codes)
        if not code:
            continue
        if 0.42 <= wd["cx"] <= 0.64:
            return code
        if wd["cx"] < 0.66 and best is None:
            best = code
    return best


def forced_total_code(words, key):
    """
    Dòng tổng cộng thường viết 'TỔNG CỘNG TÀI SẢN (270 = 100 + 200)' khiến mã
    dính ngoặc và lệch cột -> nhận diện theo từ khoá để không bỏ sót.
    """
    nline = norm(" ".join(wd["text"] for wd in words))
    if key == "CDKT":
        # 'cong tai san' / 'cong nguon von' chỉ xuất hiện ở dòng TỔNG CỘNG.
        # OCR hay DÍNH CHỮ ("TỔNGCỘNGTÀSẢN") -> kiểm thêm bản bỏ hết dấu cách.
        ns = nline.replace(" ", "")
        if "cong tai san" in nline or "congtaisan" in ns or "congtasan" in ns:
            return "270"
        if "cong nguon von" in nline or "congnguonvon" in ns:
            return "440"
        # B-A4: dòng tổng bản TIẾNG ANH (B01-DN en) khi mã không đọc được
        if "total assets" in nline:
            return "270"
        if ("total resources" in nline or "total liabilities and owner" in nline
                or "total liabilities and equity" in nline):
            return "440"
    return None


def split_values(words, split_frac):
    """Tách token số thành (cur, prior) — lấy 2 CỘT PHẢI NHẤT:
      cur   = cột phải nhất trong nhóm right <= split_frac
      prior = cột phải nhất trong nhóm right >  split_frac
    -> Báo cáo NĂM (2 cột Năm nay/Năm trước): không đổi.
    -> Báo cáo QUÝ (4 cột Quý này / Quý trước / Lũy kế năm nay / Lũy kế năm trước):
       tự lấy đúng cặp 'Lũy kế' (2 cột phải nhất) — phù hợp so sánh như báo cáo năm."""
    left = right = None          # (right_x, value): phần tử phải nhất mỗi nhóm
    for wd in words:
        if wd["cx"] < 0.60:          # bỏ qua cột chỉ tiêu / mã số / thuyết minh
            continue
        tok = wd["text"].strip().strip("[]{}|")   # bỏ ngoặc vuông/pipe nhiễu OCR ("...966]")
        if not looks_like_value(tok):
            continue
        v = parse_number(tok)
        if v is None:
            continue
        rx = wd["right"]
        if rx <= split_frac:
            if left is None or rx > left[0]:
                left = (rx, v)
        else:
            if right is None or rx > right[0]:
                right = (rx, v)
    return (left[1] if left else None), (right[1] if right else None)


def detect_value_columns(section_lines, digit_pass):
    """Tâm (right_x) các CỘT SỐ của 1 báo cáo, gom từ token số trên MỌI dòng dữ liệu.
    Số canh phải -> right_x rất ổn định trong một cột. Bỏ cụm nhiễu (ít phần tử).
    Trả centers (trái->phải). Báo cáo NĂM -> 2 cột; báo cáo QUÝ -> 4 cột."""
    rights = []
    for ln, _split, vtoks in section_lines:
        words = vtoks if (digit_pass and vtoks) else ln
        for wd in words:
            if wd["cx"] < 0.55:
                continue
            tok = wd["text"].strip().strip("[]{}|")
            if looks_like_value(tok) and parse_number(tok) is not None:
                rights.append(wd["right"])
    if len(rights) < 6:
        return []
    rights.sort()
    clusters = [[rights[0]]]
    for r in rights[1:]:
        if r - clusters[-1][-1] > 0.05:     # cột mới khi cách > 0.05
            clusters.append([r])
        else:
            clusters[-1].append(r)
    big = max(len(c) for c in clusters)
    keep = [c for c in clusters if len(c) >= max(3, big * 0.3)]   # bỏ cụm nhiễu
    return [sum(c) / len(c) for c in keep]


def pick_values(words, cur_c, prior_c, tol=0.045):
    """Lấy giá trị tại 2 TÂM CỘT cho trước (cur_c, prior_c) — token số có right_x
    gần tâm nhất (trong tol). Dùng cho báo cáo QUÝ (4 cột) để lấy đúng cặp 'Lũy kế'."""
    cur = prior = None
    cbd = pbd = tol
    for wd in words:
        if wd["cx"] < 0.55:
            continue
        tok = wd["text"].strip().strip("[]{}|")
        if not looks_like_value(tok):
            continue
        v = parse_number(tok)
        if v is None:
            continue
        rx = wd["right"]
        dc, dp = abs(rx - cur_c), abs(rx - prior_c)
        if dc < cbd:
            cur, cbd = v, dc
        if dp < pbd:
            prior, pbd = v, dp
    return cur, prior


# ----------------------------------------------------------------------
# Chọn CẶP cột giá trị khi bảng có >= 3 cột số (Đợt 2, việc #1)
# ----------------------------------------------------------------------
# Gia đình bản in phần mềm kế toán ("Phần I. Lãi Lỗ", "Kỳ kế toán: MM/YYYY")
# in KQHDKD/LCTT với BA cột số 'Kỳ này | Kỳ trước | Lũy kế'. Lối chọn cũ
# `centers[-2:]` lấy (Kỳ trước, Lũy kế); trên báo cáo 6 tháng/năm Lũy kế ==
# Kỳ này nên kết quả hoán vị hoàn hảo hai cột (kqkd_6t.pdf lệch 24/24 ô —
# xem docs/superpowers/plans/chan-doan-dot-2.md §2). Cặp đúng: (Kỳ này,
# Kỳ trước). Ba tín hiệu, xét theo độ tin cậy giảm dần:
#   1. NHÃN tiêu đề cột (khi OCR đọc được) — mạnh nhất; 'lũy kế' bị LOẠI.
#   2. Cột phải nhất TRÙNG GIÁ TRỊ cột 1 trên nhiều dòng (Lũy kế == Kỳ này).
#   3. Kỳ báo cáo QUÝ + 3-4 cột không nhãn -> quy ước bố cục quý, lấy 2 cột
#      TRÁI (không áp cho CDKT — bảng cân đối không có cột Lũy kế).
# <= 2 cột: GIỮ NGUYÊN hành vi cũ. Nhãn nhập nhằng/mâu thuẫn: giữ đường cũ
# nhưng BẮT BUỘC cảnh báo (không bao giờ im lặng).
_NHAN_KY_NAY = ("ky nay", "quy nay", "nam nay", "so cuoi")
_NHAN_KY_TRUOC = ("ky truoc", "quy truoc", "nam truoc", "so dau")
_NHAN_LUY_KE = ("luy ke",)
# Cửa sổ x quanh TÂM CỘT SỐ (right_x) để gom chữ tiêu đề của cột: nhãn nằm
# giữa cột nên lệch TRÁI so với mép phải của các con số (đo trên kqkd_6t:
# "Kỳ này" cx 0.61-0.64 dưới cột right_x 0.668).
_NHAN_X_TRAI, _NHAN_X_PHAI = 0.13, 0.04
# Ngưỡng tin "cột phải trùng giá trị cột 1": tối thiểu số dòng so sánh được
# và tỷ lệ dòng bằng nhau (kqkd_6t đo được 12/13, BCTC-2023-KQ 5/5).
_TRUNG_MIN_DONG = 4
_TRUNG_MIN_TYLE = 0.6


def doc_nhan_cot(section_lines, centers, valid_codes, col_center):
    """Đọc nhãn tiêu đề ('Kỳ này'/'Kỳ trước'/'Lũy kế'...) cho từng TÂM CỘT SỐ.

    Chỉ quét các dòng PHÍA TRÊN dòng dữ liệu đầu tiên có mã số (dải tiêu đề
    bảng); chữ trong cửa sổ x quanh mỗi tâm cột được ghép lại rồi norm() để
    so mốc. Trả về list cùng thứ tự với centers, mỗi phần tử là set con của
    {"cur", "prior", "cum"} (rỗng = không đọc được nhãn — OCR nát là chuyện
    thường trên gia đình bản in này).
    """
    nhan = [set() for _ in centers]
    if not centers:
        return nhan
    for ln, _split, _vtoks in section_lines:
        if find_code_at(ln, valid_codes, col_center):
            break                      # đã chạm thân bảng -> hết dải tiêu đề
        for ci, c in enumerate(centers):
            toks = [wd["text"] for wd in ln
                    if c - _NHAN_X_TRAI <= wd["cx"] <= c + _NHAN_X_PHAI]
            if not toks:
                continue
            text = norm(" ".join(toks))
            if any(m in text for m in _NHAN_LUY_KE):
                nhan[ci].add("cum")
            if any(m in text for m in _NHAN_KY_NAY):
                nhan[ci].add("cur")
            if any(m in text for m in _NHAN_KY_TRUOC):
                nhan[ci].add("prior")
    return nhan


def dem_cot_trung(section_lines, centers, digit_pass, tol=0.045):
    """Đếm theo từng CẶP cột (i, j): (số dòng hai giá trị BẰNG NHAU, số dòng
    cả hai cột cùng có số). Token số của mỗi dòng được gán vào tâm cột gần
    nhất trong tol — cùng cách gán với pick_values để hai nơi nhìn thấy cùng
    một bảng. Dùng để nhận diện cột Lũy kế trùng cột Kỳ này (báo cáo 6T/năm).
    """
    rows = []
    for ln, _split, vtoks in section_lines:
        words = vtoks if (digit_pass and vtoks) else ln
        gia_tri = {}                  # cột -> (khoảng cách, giá trị) gần nhất
        for wd in words:
            if wd["cx"] < 0.55:
                continue
            tok = wd["text"].strip().strip("[]{}|")
            if not looks_like_value(tok):
                continue
            v = parse_number(tok)
            if v is None:
                continue
            rx = wd["right"]
            for ci, c in enumerate(centers):
                d = abs(rx - c)
                if d < tol and (ci not in gia_tri or d < gia_tri[ci][0]):
                    gia_tri[ci] = (d, v)
        if len(gia_tri) >= 2:
            rows.append({ci: dv[1] for ci, dv in gia_tri.items()})
    ket = {}
    for i in range(len(centers)):
        for j in range(i + 1, len(centers)):
            bang = so_sanh = 0
            for gia_tri in rows:
                if i in gia_tri and j in gia_tri:
                    so_sanh += 1
                    if gia_tri[i] == gia_tri[j]:
                        bang += 1
            ket[(i, j)] = (bang, so_sanh)
    return ket


def chon_cap_cot(centers, nhan, ky_bao_cao, trung, bao_cao=None):
    """Chọn cặp (tâm cột Kỳ-này, tâm cột Kỳ-trước) khi có >= 3 cột số.

    centers   : tâm (right_x) các cột số, trái -> phải (detect_value_columns)
    nhan      : nhãn từng cột từ doc_nhan_cot (list các set {"cur","prior","cum"})
    ky_bao_cao: detect_period(...)["kind"] ('quarter'/'year'/'unknown')
    trung     : bảng đếm trùng giá trị từ dem_cot_trung
    bao_cao   : mã báo cáo ('CDKT'/'KQHDKD'/'LCTT') — quy ước quý không áp
                cho CDKT

    Trả (sel, canh_bao): sel = [tâm kỳ này, tâm kỳ trước] hoặc None (giữ
    đường cũ '2 cột phải nhất'); canh_bao = list chuỗi tiếng Việt (chỉ khi
    nhãn nhập nhằng/mâu thuẫn — không bao giờ chọn khác đi một cách im lặng).
    """
    if len(centers) <= 2:
        return None, []
    nhan = list(nhan or []) + [set()] * (len(centers) - len(nhan or []))

    # 1) NHÃN tiêu đề — căn cứ mạnh nhất khi đọc được
    vai = []
    for tags in nhan[:len(centers)]:
        if "cum" in tags:
            # 'Lũy kế' thắng mọi nhãn con trong cùng cột (header 2 tầng kiểu
            # 'Lũy kế từ đầu năm' đè trên 'Năm nay/Năm trước')
            vai.append("cum")
        elif "cur" in tags and "prior" in tags:
            return None, ["nhãn cột giá trị NHẬP NHẰNG (một cột khớp cả "
                          "'kỳ này' lẫn 'kỳ trước') — giữ cách chọn cũ "
                          "(2 cột phải nhất), số liệu 2 cột cần soát lại."]
        elif "cur" in tags:
            vai.append("cur")
        elif "prior" in tags:
            vai.append("prior")
        else:
            vai.append(None)
    if vai.count("cur") > 1 or vai.count("prior") > 1:
        return None, ["nhãn cột giá trị MÂU THUẪN (nhiều cột cùng khớp một "
                      "nhãn kỳ) — giữ cách chọn cũ (2 cột phải nhất), số "
                      "liệu 2 cột cần soát lại."]
    if vai.count("cur") == 1 and vai.count("prior") == 1:
        return [centers[vai.index("cur")], centers[vai.index("prior")]], []
    con = [ci for ci, v in enumerate(vai) if v != "cum"]
    if len(con) == 2:
        # nhãn 'Lũy kế' loại được cột dồn — còn đúng 2 cột; thứ tự theo nhãn
        # nếu đọc được một phía, mặc định trái = kỳ này
        a, b = con
        if vai[a] == "prior" or vai[b] == "cur":
            a, b = b, a
        return [centers[a], centers[b]], []
    if len(con) < 2:
        return None, ["nhãn 'Lũy kế' khớp gần hết các cột số — giữ cách "
                      "chọn cũ (2 cột phải nhất), số liệu 2 cột cần soát lại."]

    # 2) Cột phải nhất TRÙNG GIÁ TRỊ cột 1 (Lũy kế == Kỳ này trên báo cáo
    #    6T/năm của gia đình bản in này) -> loại dần từ phải
    trung = trung or {}
    while len(con) > 2:
        bang, so_sanh = trung.get((con[0], con[-1]), (0, 0))
        if so_sanh >= _TRUNG_MIN_DONG and bang >= so_sanh * _TRUNG_MIN_TYLE:
            con = con[:-1]
        else:
            break
    if len(con) == 2:
        return [centers[con[0]], centers[con[1]]], []

    # 3) Kỳ báo cáo QUÝ + 3-4 cột không nhãn -> quy ước bố cục quý
    #    (Kỳ này | Kỳ trước | Lũy kế [| Lũy kế trước]): lấy 2 cột TRÁI.
    #    CDKT không có cột Lũy kế nên không áp quy ước này.
    if ky_bao_cao == "quarter" and bao_cao != "CDKT" and len(con) in (3, 4):
        return [centers[con[0]], centers[con[1]]], []
    return None, []


def estimate_split(all_words):
    """Tìm ranh giới giữa 2 cột số từ phân bố mép phải các con số (mặc định 0.84)."""
    rights = sorted(wd["right"] for wd in all_words
                    if wd["cx"] > 0.60 and looks_like_value(wd["text"]))
    if len(rights) < 4:
        return 0.84
    # tìm khoảng trống lớn nhất trong vùng 0.74..0.90
    best_gap, best_mid = 0, 0.84
    for a, b in zip(rights, rights[1:]):
        if 0.72 <= a <= 0.92 and (b - a) > best_gap:
            best_gap, best_mid = b - a, (a + b) / 2
    return best_mid if best_gap > 0.03 else 0.84


# ----------------------------------------------------------------------
# B-A1: PASS CHỈ-CHỮ-SỐ cho cột số
# ----------------------------------------------------------------------
# Giới hạn Tesseract chỉ đọc ký tự số ở vùng cột số -> giảm nhầm 0/O, 1/l, 8/B,
# mất dấu chấm nghìn. Gán token số (theo toạ độ y) về đúng DÒNG của pass chữ.
DIGIT_WHITELIST = "0123456789.,()-"
DIGIT_VALUE_XMIN = 0.50        # chỉ lấy token ở nửa phải trang (vùng cột số)
DIGIT_BAND_TOL = 0.012         # dung sai gán token vào dòng theo tâm y (phân số)


def _line_cy(ln):
    return sum(wd["cy"] for wd in ln) / len(ln) if ln else 0.0


def assign_value_tokens(lines, digit_tokens, tol=DIGIT_BAND_TOL):
    """
    Gán mỗi token số (pass whitelist) về DÒNG gần nhất theo tâm y. Trả về list
    cùng thứ tự với `lines`, mỗi phần tử là danh sách token số của dòng đó.
    """
    per_line = [[] for _ in lines]
    if not lines or not digit_tokens:
        return per_line
    cys = [_line_cy(ln) for ln in lines]
    for dt in digit_tokens:
        if dt["cx"] < DIGIT_VALUE_XMIN or not looks_like_value(dt["text"]):
            continue
        best, bd = None, tol
        for li, lcy in enumerate(cys):
            d = abs(dt["cy"] - lcy)
            if d < bd:
                best, bd = li, d
        if best is not None:
            per_line[best].append(dt)
    return per_line


# ----------------------------------------------------------------------
# Định vị các trang chứa báo cáo (quét nhanh dải đầu trang)
# ----------------------------------------------------------------------
# V1 Đợt 2: CĐKT/LCTT dài 2-3 trang nhưng trang TIẾP DIỄN không lặp tiêu đề
# nên trước đây bị vứt vĩnh viễn (BCTC 6T Tân Bình mất CĐKT p4-p5, LCTT p8 —
# docs/superpowers/plans/chan-doan-dot-2.md §1). Sau khi định vị, scope được
# mở rộng: trang nằm giữa một trang báo cáo và mốc kế tiếp thuộc về báo cáo
# đứng TRƯỚC nó, có trần số trang để chặn chi phí.
TRAN_TIEP_DIEN = 3          # trần số trang tiếp diễn cho MỖI báo cáo

# Cụm nhận trang mở đầu phần THUYẾT MINH (mốc dừng mở rộng) trong MỘT dòng
# ngắn. KHÔNG dùng chữ "thuyết minh" trơ trọi: header bảng của chính trang
# báo cáo (và trang tiếp diễn) có CỘT 'Thuyết minh' sẽ dính oan.
_DUNG_THUYET_MINH = ("ban thuyet minh", "notes to the financial statements")


def _dau_hieu_dung(line_texts):
    """Dấu hiệu DỪNG mở rộng scope trên dải đầu trang.

    Trả 'thuyet minh' (trang mở đầu phần thuyết minh), 'muc luc', hoặc None.
    Tiêu đề thuyết minh là DÒNG NGẮN chứa cả cụm 'thuyết minh' lẫn 'báo cáo
    tài chính' (hoặc 'bản thuyết minh' / bản tiếng Anh); câu văn dài kiểu
    'Các thuyết minh ... là bộ phận hợp thành của báo cáo tài chính này'
    (chân trang báo cáo) không tính.
    """
    lines_norm = [norm(t) for t in line_texts]
    if any("muc luc" in nl for nl in lines_norm):
        return "muc luc"
    for nl in lines_norm:
        if len(nl.split()) > MAX_HEADING_WORDS:
            continue
        if ("thuyet minh" in nl and "bao cao tai chinh" in nl) \
                or any(p in nl for p in _DUNG_THUYET_MINH):
            return "thuyet minh"
    return None


def _scan_strip(doc, i, lang, scan_dpi):
    """OCR dải đầu 1 trang -> (i, tiêu đề báo cáo | None, dấu hiệu dừng | None)."""
    from PIL import Image
    page = doc[i]

    if getattr(doc, "_bctc_dung_lop_text", False):
        # Có lớp text tin cậy -> lấy chữ ở dải đầu trang, khỏi OCR.
        gioi_han = page.rect.y0 + (page.rect.y1 - page.rect.y0) * 0.42
        line_texts = [" ".join(w["text"] for w in ln)
                      for ln in textlayer.page_lines(page)
                      if ln and ln[0]["top"] <= gioi_han]
        return i, heading_in_lines(line_texts), _dau_hieu_dung(line_texts)

    pix = page.get_pixmap(dpi=scan_dpi, clip=fitz_rect(page, top_frac=0.42))
    img = ocr.preprocess(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    _, _, lines = ocr.ocr_lines(img, lang=lang, psm=6, min_conf=20)
    line_texts = [" ".join(w["text"] for w in ln) for ln in lines]
    return i, heading_in_lines(line_texts), _dau_hieu_dung(line_texts)


def _mo_rong_tiep_dien(doc, scope, quet, lang, scan_dpi, hi, log):
    """Gán trang TIẾP DIỄN (không lặp tiêu đề) vào báo cáo đứng trước nó.

    Mốc dừng cho mỗi báo cáo đã định vị: (a) trang tiêu đề kế tiếp — kể cả
    tiêu đề chỉ lộ ra khi quét thêm sau điểm dừng sớm; (b) trang thuyết minh
    / mục lục (dấu hiệu trên dải đầu); (c) trần TRAN_TIEP_DIEN trang. KHÔNG
    lọc theo mật độ mã số: trang không có mã vào scope cũng vô hại vì lượt 2
    của extract chỉ map mã thuộc khung chuẩn — trần (c) đã chặn chi phí.

    Quyết định mở rộng chỉ dùng quét DẢI ĐẦU giá rẻ: trang đã quét trong vòng
    batch được tái dùng qua `quet` (trang -> (tiêu đề, dấu hiệu)), chỉ trang
    CHƯA quét (nằm sau điểm dừng sớm) mới được quét thêm. Giữ nguyên hình
    dạng trả về [(trang, nhãn báo cáo)] và thứ tự trang tăng dần — mọi tầng
    dưới (extract lượt 1, sidecar) không phải đổi gì.
    """
    if not scope:
        return scope
    ket = []
    for idx, (p, t) in enumerate(scope):
        ket.append((p, t))
        # biên phải: trang tiêu đề kế tiếp đã định vị, hoặc hết vùng quét
        bien = scope[idx + 1][0] if idx + 1 < len(scope) else hi
        for q in range(p + 1, min(p + 1 + TRAN_TIEP_DIEN, bien)):
            if q in quet:
                title_q, dau_hieu = quet[q]
            else:
                _, title_q, dau_hieu = _scan_strip(doc, q, lang, scan_dpi)
                quet[q] = (title_q, dau_hieu)
            if title_q or dau_hieu:
                break               # gặp mốc dừng -> trang đó không thuộc t
            ket.append((q, t))
            log(f"   + trang {q+1}: tiếp diễn {t}")
    return ket


def locate_pages(doc, lang="vie", scan_dpi=135, page_range=None, log=lambda *_: None,
                 workers=None):
    """
    Quét dải đầu mỗi trang theo từng BATCH song song, dừng sớm khi đã tìm đủ
    cả 3 báo cáo và batch tiếp theo không còn trang báo cáo nào.
    """
    nw = workers or MAX_WORKERS
    # Chỉ tính cờ lớp text khi CHƯA đặt. Lượt thử-lại-bằng-OCR đặt cờ False
    # một cách chủ đích — định vị lại không được lật ngược nó về True.
    if getattr(doc, "_bctc_dung_lop_text", None) is None:
        try:
            doc._bctc_dung_lop_text = textlayer.is_usable(doc)
        except Exception:
            pass
    lo, hi = (page_range or (0, doc.page_count))
    lo, hi = max(0, lo), min(doc.page_count, hi)
    pages = list(range(lo, hi))

    scope, found = [], set()
    quet = {}          # trang -> (tiêu đề, dấu hiệu dừng): tái dùng khi mở rộng
    with ThreadPoolExecutor(max_workers=nw) as ex:
        for b in range(0, len(pages), nw):
            chunk = pages[b:b + nw]
            res = sorted(ex.map(lambda i: _scan_strip(doc, i, lang, scan_dpi), chunk))
            had_stmt = False
            for i, title, dau_hieu in res:
                quet[i] = (title, dau_hieu)
                if title:
                    scope.append((i, title)); found.add(title); had_stmt = True
                    log(f"   • trang {i+1}: {title}")
            # đã đủ 3 báo cáo và batch này không còn -> dừng (đã sang phần thuyết minh)
            if len(found) >= 3 and not had_stmt and scope:
                break
    # V1: trang tiếp diễn không lặp tiêu đề — mở rộng SAU vòng batch để cơ chế
    # dừng sớm giữ nguyên; chỉ dùng kết quả quét dải giá rẻ đã có.
    return _mo_rong_tiep_dien(doc, scope, quet, lang, scan_dpi, hi, log)


def fitz_rect(page, top_frac=0.34):
    import fitz
    r = page.rect
    return fitz.Rect(r.x0, r.y0, r.x1, r.y0 + (r.y1 - r.y0) * top_frac)


# ----------------------------------------------------------------------
# Trích xuất đầy đủ 3 báo cáo
# ----------------------------------------------------------------------
def extract(doc, lang="vie", dpi=300, page_range=None, log=lambda *_: None,
            scope=None, digit_pass=False, workers=None):
    """
    Trả về:
        results : {stmt_key: {code: (cur, prior)}}
        warnings: [str]

    scope: kết quả định vị trang (list (trang, nhãn báo cáo)). Nếu None thì tự
    chạy locate_pages; truyền sẵn để TÁI DÙNG qua nhiều DPI (locate độc lập DPI render).
    digit_pass: pass CHỈ-CHỮ-SỐ (B-A1, thí nghiệm). MẶC ĐỊNH TẮT: benchmark cho thấy
    nó làm TỆ HƠN (model 'vie' vốn đọc cụm số tốt; whitelist toàn-trang thỉnh thoảng
    thêm lỗi + sinh rác cột mã -> conflicts tăng, balance giảm). Xem
    plans/260609-accuracy-and-performance/results.md. Hạ tầng giữ lại cho B-A3
    (re-OCR whitelist trên CROP ô nghi ngờ — cách dùng đúng hơn).
    """
    if scope is None:
        scope = locate_pages(doc, lang=lang, page_range=page_range, log=log,
                             workers=workers)
    results = {k: {} for k in T.STATEMENTS}
    warnings = []
    if not scope:
        warnings.append("Không định vị được trang báo cáo (file có thể theo mẫu khác).")
        return results, warnings, {}

    pages = [p for p, _ in scope]
    found_titles = {t for _, t in scope}
    for key in T.STATEMENTS:
        if key not in found_titles:
            name = T.STATEMENTS[key][0]
            warnings.append(f"Không tìm thấy '{name}'.")

    valid = {k: T.codes_of(tpl) for k, (_, tpl) in T.STATEMENTS.items()}
    # với LCTT thử cả 2 phương pháp (gián tiếp & trực tiếp)
    valid["LCTT"] = T.codes_of(T.LUU_CHUYEN_TIEN_TE_GT) | T.codes_of(T.LUU_CHUYEN_TIEN_TE_TT)

    page_meta = {}          # phục vụ kiểm tra/chẩn đoán
    current = None
    from PIL import Image

    dung_lop_text = getattr(doc, "_bctc_dung_lop_text", None)
    if dung_lop_text is None:
        dung_lop_text = textlayer.is_usable(doc)
        try:
            doc._bctc_dung_lop_text = dung_lop_text
        except Exception:
            pass

    page_digits = {p: [] for p in pages}
    if dung_lop_text:
        # Lớp text tin cậy -> đọc thẳng, không OCR (và không cần pass chữ-số).
        # Chính xác tuyệt đối và gần như không tốn CPU.
        log("   ⚡ Dùng lớp text sẵn có (bỏ qua OCR)")
        page_lines = {p: textlayer.page_lines(doc[p]) for p in pages}
    else:
        nw = workers or MAX_WORKERS
        # render (tuần tự) rồi OCR (song song) các trang đã định vị
        rendered = []
        for p in pages:
            pix = doc[p].get_pixmap(dpi=dpi)
            rendered.append((p, Image.frombytes("RGB", (pix.width, pix.height), pix.samples)))

        def _ocr(item):
            p, img = item
            _, _, lines = ocr.ocr_lines(ocr.preprocess(img), lang=lang, psm=6, min_conf=25)
            return p, lines

        with ThreadPoolExecutor(max_workers=nw) as ex:
            page_lines = dict(ex.map(_ocr, rendered))

        # PASS CHỈ-CHỮ-SỐ (B-A1): OCR lại trang với whitelist số -> token số sạch hơn.
        if digit_pass:
            def _ocr_digits(item):
                p, img = item
                _, _, dlines = ocr.ocr_lines(ocr.preprocess(img), lang=lang, psm=6,
                                             min_conf=0, whitelist=DIGIT_WHITELIST)
                return p, [wd for ln in dlines for wd in ln]
            with ThreadPoolExecutor(max_workers=nw) as ex:
                page_digits = dict(ex.map(_ocr_digits, rendered))

    # ---- Lượt 1: gán mỗi dòng vào đúng báo cáo ----
    # Mỗi trang đã được locate gán 1 báo cáo (đáng tin); dùng làm mốc đầu trang,
    # rồi cho phép chuyển nếu trong trang gặp tiêu đề báo cáo khác (trang chuyển tiếp).
    page_title = dict(scope)
    section_lines = {k: [] for k in T.STATEMENTS}
    for p in pages:
        lines = page_lines[p]
        split = estimate_split([wd for ln in lines for wd in ln])
        page_meta[p] = {"split": split, "nlines": len(lines)}
        # token số (pass whitelist) gán về đúng dòng theo tâm y
        line_vtoks = assign_value_tokens(lines, page_digits.get(p, []))
        current = page_title.get(p, current)
        for li, ln in enumerate(lines):
            t = line_title(" ".join(wd["text"] for wd in ln))
            if t:
                current = t
                continue
            if current is not None:
                section_lines[current].append((ln, split, line_vtoks[li]))

    # ---- Lượt 2: dò cột Mã số cho từng báo cáo rồi bóc số ----
    # Kỳ báo cáo (quý/năm) tính MỘT lần trên toàn bộ dòng: vừa là metadata
    # (page_meta["period"]) vừa là tín hiệu chọn cặp cột khi bảng >= 3 cột số.
    period = detect_period(
        [" ".join(wd["text"] for wd in ln) for p in pages for ln in page_lines[p]]
    )
    cols = {}
    for key in T.STATEMENTS:
        col = detect_code_column(section_lines[key], valid[key], ORDER[key])
        cols[key] = col
        # Bảng >= 3 cột số (bản in 'Kỳ này | Kỳ trước | Lũy kế' hoặc báo cáo
        # quý 4 cột) -> chọn cặp theo NGỮ NGHĨA (nhãn tiêu đề / cột trùng giá
        # trị / quy ước quý); không tín hiệu nào thì giữ đường cũ 2 cột phải
        # nhất. Báo cáo NĂM (<=2 cột) giữ split_values như cũ.
        centers = detect_value_columns(section_lines[key], digit_pass)
        if len(centers) > 2:
            sel, canh_bao = chon_cap_cot(
                centers,
                doc_nhan_cot(section_lines[key], centers, valid[key], col),
                period.get("kind"),
                dem_cot_trung(section_lines[key], centers, digit_pass),
                bao_cao=key)
            for cb in canh_bao:
                warnings.append("%s: %s" % (T.STATEMENTS[key][0], cb))
            if sel is None:
                sel = centers[-2:]          # đường cũ: 2 cột phải nhất
        else:
            sel = None
        for ln, split, vtoks in section_lines[key]:
            code = find_code_at(ln, valid[key], col)
            if not code:
                code = forced_total_code(ln, key)   # dòng "TỔNG CỘNG ... (270=...)"
            if not code:
                continue
            # ưu tiên token pass-số; không có thì fallback về pass chữ (không thụt lùi)
            value_words = vtoks if (digit_pass and vtoks) else ln
            if sel:
                cur, prior = pick_values(value_words, sel[0], sel[1])
            else:
                cur, prior = split_values(value_words, split)
            if cur is None and prior is None:
                results[key].setdefault(code, (None, None))
            else:
                results[key][code] = (cur, prior)
    page_meta["_code_columns"] = cols
    page_meta["period"] = period
    return results, warnings, page_meta


def extract_consensus(doc, lang="vie", dpis=(185, 240), page_range=None,
                      log=lambda *_: None, on_pass=lambda done, total: None,
                      digit_pass=False, workers=None):
    """
    Chạy bóc tách ở NHIỀU độ phân giải rồi hợp nhất để giảm lỗi OCR:
      - DPI đầu tiên là CHÍNH (thực nghiệm cho kết quả tốt & ổn định nhất);
      - các DPI sau chỉ ĐIỀN vào ô còn trống, KHÔNG ghi đè giá trị đã có
        (tránh mang lỗi của DPI cao vào);
      - ô nào hai lần đọc ra số KHÁC nhau -> ghi nhận 'nghi ngờ' để soát lại.
    Đường text phải TỰ CHỨNG MINH nó cho ra số liệu: nếu không bóc được giá
    trị nào thì quay về OCR (đúng một lần) — lớp text không bao giờ được làm
    dữ liệu tệ đi.
    Trả về: results, warnings, meta, conflicts
    """

    def _mot_luot():
        """Một lượt trọn vẹn: định vị + bóc tách mọi DPI + hợp nhất."""
        merged = {k: {} for k in T.STATEMENTS}
        conflicts = []
        base_warnings, base_meta = [], {}

        # Định vị MỘT lần rồi dùng chung cho mọi lượt DPI: kết quả tất định,
        # quét lại chỉ tốn thêm (số_DPI - 1) x số_trang lượt OCR mà không đổi gì.
        scope = locate_pages(doc, lang=lang, page_range=page_range, log=log,
                             workers=workers)

        for idx, dpi in enumerate(dpis):
            primary = (idx == 0)
            res, warns, meta = extract(
                doc, lang=lang, dpi=dpi, page_range=page_range,
                log=(log if primary else (lambda *_: None)), scope=scope,
                digit_pass=digit_pass, workers=workers)
            if primary:
                base_warnings, base_meta = warns, meta
            for key in res:
                for code, (cur, prior) in res[key].items():
                    if code not in merged[key]:
                        merged[key][code] = (cur, prior)
                        continue
                    ecur, eprior = merged[key][code]
                    if ecur is not None and cur is not None and ecur != cur:
                        conflicts.append((key, code, "cuối năm/năm nay", ecur, cur))
                    if eprior is not None and prior is not None and eprior != prior:
                        conflicts.append((key, code, "đầu năm/năm trước", eprior, prior))
                    merged[key][code] = (ecur if ecur is not None else cur,
                                         eprior if eprior is not None else prior)
            on_pass(idx + 1, len(dpis))
        return merged, base_warnings, base_meta, conflicts

    merged, base_warnings, base_meta, conflicts = _mot_luot()

    # Lớp text tuy qua được bộ lọc chất lượng nhưng vẫn có thể không cho parser
    # bóc ra giá trị nào (hình học dòng/cột lệch chuẩn, thậm chí không định vị
    # nổi trang). Khi đó quay về OCR thay vì trả kết quả trống. Cấu trúc thẳng
    # dòng (không đệ quy) nên chỉ thử lại ĐÚNG MỘT lần.
    khong_co_gia_tri = not any(
        v is not None
        for bang in merged.values()
        for cap in bang.values()
        for v in cap)
    if getattr(doc, "_bctc_dung_lop_text", False) and khong_co_gia_tri:
        log("   ↻ Lớp text không cho ra số liệu — thử lại bằng OCR.")
        try:
            doc._bctc_dung_lop_text = False
        except Exception:
            pass
        merged, base_warnings, base_meta, conflicts = _mot_luot()
    return merged, base_warnings, base_meta, conflicts
