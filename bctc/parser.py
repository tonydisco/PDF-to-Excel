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

# số luồng OCR song song (mỗi luồng gọi 1 tiến trình tesseract riêng)
MAX_WORKERS = max(2, min(8, (os.cpu_count() or 4)))


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
    "CDKT":   ["bang can doi ke toan"],
    "KQHDKD": ["ket qua hoat dong kinh doanh", "ket qua kinh doanh"],
    "LCTT":   ["luu chuyen tien te"],
}
MAX_HEADING_WORDS = 11   # tiêu đề là dòng NGẮN, không phải câu văn xuôi


def detect_title(text_norm):
    for key, pats in TITLES.items():
        if any(p in text_norm for p in pats):
            return key
    return None


def line_title(line_text):
    """Trả về mã báo cáo nếu DÒNG này là một TIÊU ĐỀ ngắn (không phải prose)."""
    nl = norm(line_text)
    wc = len(nl.split())
    if wc == 0 or wc > MAX_HEADING_WORDS:
        return None
    return detect_title(nl)


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


# ----------------------------------------------------------------------
# Phân tích con số kiểu Việt Nam:  1.234.567  (1.234)  -   =>  int / None
# ----------------------------------------------------------------------
_NUM_RE = re.compile(r"^\(?\-?[\d.\s]+\)?$")


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
    # giá trị tài chính thường >= 3 chữ số hoặc có dấu chấm phân tách
    return len(digits) >= 3 or "." in t


# ----------------------------------------------------------------------
# Bóc Mã số và 2 cột giá trị từ một DÒNG (list từ kèm toạ độ)
# ----------------------------------------------------------------------
_CODE_RE = re.compile(r"^(\d{1,3}[abc]?)$")


def _token_code(wd, valid_codes):
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
    for ln, _ in section_lines:
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
        # 'cong tai san' / 'cong nguon von' chỉ xuất hiện ở dòng TỔNG CỘNG
        if "cong tai san" in nline:
            return "270"
        if "cong nguon von" in nline:
            return "440"
    return None


def split_values(words, split_frac):
    """Tách token số thành (năm nay/cuối năm, năm trước/đầu năm) theo vị trí x."""
    cur = prior = None
    for wd in words:
        if wd["cx"] < 0.60:          # bỏ qua cột chỉ tiêu / mã số / thuyết minh
            continue
        if not looks_like_value(wd["text"]):
            continue
        v = parse_number(wd["text"])
        if v is None:
            continue
        if wd["right"] <= split_frac:
            cur = v if cur is None else cur
        else:
            prior = v if prior is None else prior
    return cur, prior


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
# Định vị các trang chứa báo cáo (quét nhanh dải đầu trang)
# ----------------------------------------------------------------------
def _scan_strip(doc, i, lang, scan_dpi):
    """OCR dải đầu 1 trang -> (i, title_key_or_None)."""
    from PIL import Image
    page = doc[i]
    pix = page.get_pixmap(dpi=scan_dpi, clip=fitz_rect(page, top_frac=0.42))
    img = ocr.preprocess(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    _, _, lines = ocr.ocr_lines(img, lang=lang, psm=6, min_conf=20)
    line_texts = [" ".join(w["text"] for w in ln) for ln in lines]
    return i, heading_in_lines(line_texts)


def locate_pages(doc, lang="vie", scan_dpi=135, page_range=None, log=lambda *_: None):
    """
    Quét dải đầu mỗi trang theo từng BATCH song song, dừng sớm khi đã tìm đủ
    cả 3 báo cáo và batch tiếp theo không còn trang báo cáo nào.
    """
    lo, hi = (page_range or (0, doc.page_count))
    lo, hi = max(0, lo), min(doc.page_count, hi)
    pages = list(range(lo, hi))

    scope, found = [], set()
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for b in range(0, len(pages), MAX_WORKERS):
            chunk = pages[b:b + MAX_WORKERS]
            res = sorted(ex.map(lambda i: _scan_strip(doc, i, lang, scan_dpi), chunk))
            had_stmt = False
            for i, title in res:
                if title:
                    scope.append((i, title)); found.add(title); had_stmt = True
                    log(f"   • trang {i+1}: {title}")
            # đã đủ 3 báo cáo và batch này không còn -> dừng (đã sang phần thuyết minh)
            if len(found) >= 3 and not had_stmt and scope:
                break
    return scope


def fitz_rect(page, top_frac=0.34):
    import fitz
    r = page.rect
    return fitz.Rect(r.x0, r.y0, r.x1, r.y0 + (r.y1 - r.y0) * top_frac)


# ----------------------------------------------------------------------
# Trích xuất đầy đủ 3 báo cáo
# ----------------------------------------------------------------------
def extract(doc, lang="vie", dpi=300, page_range=None, log=lambda *_: None):
    """
    Trả về:
        results : {stmt_key: {code: (cur, prior)}}
        warnings: [str]
    """
    scope = locate_pages(doc, lang=lang, page_range=page_range, log=log)
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

    # render (tuần tự) rồi OCR (song song) các trang đã định vị
    rendered = []
    for p in pages:
        pix = doc[p].get_pixmap(dpi=dpi)
        rendered.append((p, Image.frombytes("RGB", (pix.width, pix.height), pix.samples)))

    def _ocr(item):
        p, img = item
        _, _, lines = ocr.ocr_lines(ocr.preprocess(img), lang=lang, psm=6, min_conf=25)
        return p, lines

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        page_lines = dict(ex.map(_ocr, rendered))

    # ---- Lượt 1: gán mỗi dòng vào đúng báo cáo ----
    # Mỗi trang đã được locate gán 1 báo cáo (đáng tin); dùng làm mốc đầu trang,
    # rồi cho phép chuyển nếu trong trang gặp tiêu đề báo cáo khác (trang chuyển tiếp).
    page_title = dict(scope)
    section_lines = {k: [] for k in T.STATEMENTS}
    for p in pages:
        lines = page_lines[p]
        split = estimate_split([wd for ln in lines for wd in ln])
        page_meta[p] = {"split": split, "nlines": len(lines)}
        current = page_title.get(p, current)
        for ln in lines:
            t = line_title(" ".join(wd["text"] for wd in ln))
            if t:
                current = t
                continue
            if current is not None:
                section_lines[current].append((ln, split))

    # ---- Lượt 2: dò cột Mã số cho từng báo cáo rồi bóc số ----
    cols = {}
    for key in T.STATEMENTS:
        col = detect_code_column(section_lines[key], valid[key], ORDER[key])
        cols[key] = col
        for ln, split in section_lines[key]:
            code = find_code_at(ln, valid[key], col)
            if not code:
                code = forced_total_code(ln, key)   # dòng "TỔNG CỘNG ... (270=...)"
            if not code:
                continue
            cur, prior = split_values(ln, split)
            if cur is None and prior is None:
                results[key].setdefault(code, (None, None))
            else:
                results[key][code] = (cur, prior)
    page_meta["_code_columns"] = cols
    return results, warnings, page_meta


def extract_consensus(doc, lang="vie", dpis=(185, 240), page_range=None,
                      log=lambda *_: None, on_pass=lambda done, total: None):
    """
    Chạy bóc tách ở NHIỀU độ phân giải rồi hợp nhất để giảm lỗi OCR:
      - DPI đầu tiên là CHÍNH (thực nghiệm cho kết quả tốt & ổn định nhất);
      - các DPI sau chỉ ĐIỀN vào ô còn trống, KHÔNG ghi đè giá trị đã có
        (tránh mang lỗi của DPI cao vào);
      - ô nào hai lần đọc ra số KHÁC nhau -> ghi nhận 'nghi ngờ' để soát lại.
    Trả về: results, warnings, meta, conflicts
    """
    merged = {k: {} for k in T.STATEMENTS}
    conflicts = []
    base_warnings, base_meta = [], {}
    for idx, dpi in enumerate(dpis):
        primary = (idx == 0)
        res, warns, meta = extract(
            doc, lang=lang, dpi=dpi, page_range=page_range,
            log=(log if primary else (lambda *_: None)))
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
