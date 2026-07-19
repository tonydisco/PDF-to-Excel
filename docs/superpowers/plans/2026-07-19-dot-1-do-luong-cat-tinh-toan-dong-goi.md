# Đợt 1 — Bộ đo, cắt tính toán thừa, đóng gói Windows

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dựng bộ đo khách quan cho chất lượng bóc tách và tài nguyên, cắt bỏ khối lượng tính toán thừa để giảm nhiệt, và sửa dứt điểm thời gian khởi động trên Windows.

**Architecture:** Ba khối độc lập. GĐ0 thêm thư mục `tests/` hoàn toàn mới, không đụng code sản phẩm. GĐ1 sửa `bctc/parser.py` + `bctc/engine.py` và thêm ba module nhỏ (`workers.py`, `dedup.py`, `textlayer.py`); `textlayer.py` cố ý trả về **đúng cấu trúc dữ liệu** mà `ocr.ocr_lines()` trả về để `parser.py` dùng chung, không phải rẽ nhánh. GĐ2 chỉ đụng file đóng gói (`pdf2excel.spec`, `.github/workflows/build.yml`, `installer/`) cộng một thay đổi import trong `app.py`, nên chạy song song với GĐ1 mà không xung đột.

**Tech Stack:** Python 3.9+ · PyMuPDF (fitz) 1.27 · pytest · xlrd (chỉ cho test) · openpyxl · PyInstaller · Inno Setup 6

## Global Constraints

- Python tối thiểu **3.9** (`requirements.txt` hiện tại). Không dùng cú pháp 3.10+ như `match`, `X | Y` trong annotation lúc chạy.
- Thư viện sản phẩm **không được thêm mới**. `xlrd` và `pytest` chỉ nằm trong `requirements-dev.txt`, không bao giờ được `bctc/` hay `app.py` import.
- Dữ liệu **không rời khỏi máy**. Không thêm bất kỳ lời gọi mạng nào.
- Mọi văn bản hiển thị cho người dùng viết bằng **tiếng Việt có dấu**.
- Corpus nằm **ngoài repo**, truy cập qua biến môi trường `BCTC_CORPUS`; mặc định `/Users/motmi/Documents/DAYS/Y-NHI/BTG/Documents`. Test cần corpus phải `pytest.skip` khi biến không trỏ tới thư mục tồn tại.
- **Không commit file corpus** vào repo. Chỉ commit `pairs.json` (danh sách đường dẫn) và báo cáo baseline.
- Nguyên tắc bất di bất dịch: **không mất dữ liệu âm thầm**. Mọi nhánh bỏ qua dữ liệu phải ghi log hoặc cảnh báo.

## Bối cảnh số liệu (để không phải mở lại spec)

- Corpus: 2.919 PDF · 79.910 trang · 19,8 GB · trung vị 28 trang/file.
- 87,8% file phải OCR; chỉ 12,2% có lớp text dùng được; 9,4% là mojibake.
- 17,1% file trùng lặp theo nội dung.
- Máy đích: Windows 10, 4 GB RAM, HDD, 2–4 nhân.

Chi tiết đầy đủ: [spec](../specs/2026-07-19-nang-cap-bctc-design.md).

## Cấu trúc file

| File | Trách nhiệm |
|---|---|
| `requirements-dev.txt` | **Tạo** — pytest, xlrd (chỉ dev) |
| `tests/conftest.py` | **Tạo** — fixture corpus, skip khi thiếu |
| `tests/regression/groundtruth.py` | **Tạo** — đọc Excel đáp án, dò định dạng theo magic bytes |
| `tests/regression/build_pairs.py` | **Tạo** — đề xuất cặp PDF↔Excel |
| `tests/regression/pairs.json` | **Tạo** — danh sách cặp đã người xác nhận, đóng băng |
| `tests/regression/metrics.py` | **Tạo** — tầng 1 (đúng/sót/lệch/thừa) + tầng 2 (độ phủ, cân đối) |
| `tests/regression/resources.py` | **Tạo** — tầng 3 (CPU-giây, RSS đỉnh) |
| `tests/regression/run_regression.py` | **Tạo** — điều phối, xuất báo cáo |
| `bctc/workers.py` | **Tạo** — chọn số luồng OCR theo chế độ |
| `bctc/dedup.py` | **Tạo** — băm nội dung, gom nhóm trùng |
| `bctc/textlayer.py` | **Tạo** — đọc lớp text + ba bộ lọc |
| `bctc/parser.py` | **Sửa** — nhận `scope`, nhận `workers` |
| `bctc/engine.py` | **Sửa** — khử trùng lặp, truyền chế độ |
| `pdf2excel.spec` | **Sửa** — onedir, bỏ UPX, splash |
| `.github/workflows/build.yml` | **Sửa** — cắt Tesseract, dựng bộ cài |
| `installer/BCTC_Setup.iss` | **Tạo** — kịch bản Inno Setup |
| `app.py` | **Sửa** — hoãn import nặng |

---

# GIAI ĐOẠN 0 — BỘ ĐO

### Task 1: Nền test + bộ đọc file đáp án

Excel đáp án có ba cạm bẫy đã xác nhận trên file thật: đuôi file nói dối (`KQKD.XLS` thực chất là OOXML), nhãn chỉ tiêu là mojibake TCVN3, và hàng tiêu đề không nằm ở vị trí cố định. Bộ đọc phải xử lý cả ba.

**Files:**
- Create: `requirements-dev.txt`
- Create: `tests/__init__.py` (rỗng)
- Create: `tests/conftest.py`
- Create: `tests/regression/__init__.py` (rỗng)
- Create: `tests/regression/groundtruth.py`
- Test: `tests/test_groundtruth.py`

**Interfaces:**
- Consumes: không có (task đầu tiên)
- Produces:
  - `groundtruth.sniff_format(path: str) -> str` → `'ooxml'` | `'biff'` | `'unknown'`
  - `groundtruth.statement_kind(filename: str) -> str` → `'CDKT'` | `'KQHDKD'` | `'LCTT'` | `'CDPS'` | `''`
  - `groundtruth.read_statement(path: str) -> dict` → `{ma_so: (nam_nay, nam_truoc)}`, giá trị là `int` hoặc `None`
  - fixture pytest `corpus_root` → `str` (đường dẫn corpus, tự skip nếu không có)

- [ ] **Step 1: Tạo requirements-dev.txt**

```
# Chỉ dùng cho phát triển/kiểm thử. KHÔNG được import trong bctc/ hay app.py.
pytest>=7.4
xlrd>=2.0.1          # đọc file .xls định dạng BIFF cũ (114/173 file đáp án)
```

- [ ] **Step 2: Tạo môi trường và cài thư viện**

```bash
cd BCTC_PDF_to_Excel
# macOS: dùng Python có sẵn thư viện. Windows: python -m venv .venv
/opt/homebrew/bin/python3.13 -m venv .venv || python3 -m venv .venv
.venv/bin/python -m pip install -q --upgrade pip
.venv/bin/python -m pip install -q -r requirements.txt -r requirements-dev.txt
.venv/bin/python -c "import fitz, openpyxl, xlrd, pytest; print('deps OK')"
```

Expected: `deps OK`

- [ ] **Step 3: Tạo tests/conftest.py**

```python
# -*- coding: utf-8 -*-
"""Fixture dùng chung cho bộ kiểm thử."""
import os
import pytest

DEFAULT_CORPUS = "/Users/motmi/Documents/DAYS/Y-NHI/BTG/Documents"


@pytest.fixture(scope="session")
def corpus_root():
    """Thư mục corpus BCTC. Tự bỏ qua test nếu máy không có corpus."""
    root = os.environ.get("BCTC_CORPUS", DEFAULT_CORPUS)
    if not os.path.isdir(root):
        pytest.skip(f"Không tìm thấy corpus tại {root} (đặt biến BCTC_CORPUS)")
    return root
```

- [ ] **Step 4: Viết test thất bại cho bộ đọc đáp án**

Tạo `tests/test_groundtruth.py`:

```python
# -*- coding: utf-8 -*-
import os
import glob
import pytest

from tests.regression import groundtruth as G


def test_statement_kind_nhan_dien_theo_ten_file():
    assert G.statement_kind("CDKT.XLS") == "CDKT"
    assert G.statement_kind("KQKD.XLS") == "KQHDKD"
    assert G.statement_kind("LCTT.XLS") == "LCTT"
    assert G.statement_kind("CDSPS.XLS") == "CDPS"
    assert G.statement_kind("1 Can doi ke toan 06 thang dau 2025.xlsx") == "CDKT"
    assert G.statement_kind("3 KQKD 6 thang 2025.xlsx") == "KQHDKD"
    assert G.statement_kind("4 LCTT truc tiep 06 thang 2025.xlsx") == "LCTT"
    assert G.statement_kind("BCTC 2019.pdf") == ""


def test_sniff_format_khong_tin_duoi_file(corpus_root):
    """KQKD.XLS thực chất là OOXML - đuôi file nói dối."""
    hits = glob.glob(os.path.join(corpus_root, "**", "KQKD.XLS"), recursive=True)
    if not hits:
        pytest.skip("Không có file KQKD.XLS trong corpus")
    assert G.sniff_format(hits[0]) == "ooxml"


def test_read_statement_boc_dung_ma_so_va_gia_tri(corpus_root):
    """Đối chiếu với giá trị đã xác minh bằng mắt của Cty CP Du Lịch Đăk Lăk 2023."""
    hits = [p for p in glob.glob(os.path.join(corpus_root, "**", "KQKD.XLS"),
                                 recursive=True) if "Dak Lak" in p]
    if not hits:
        pytest.skip("Không có file KQKD.XLS của Đăk Lăk")
    vals = G.read_statement(hits[0])
    # Mã số in trong báo cáo là '1', '2' (KHÔNG phải '01', '02')
    assert vals["1"] == (23752205505, 21874564189)   # Doanh thu bán hàng
    assert vals["10"] == (23752205505, 21874564189)  # Doanh thu thuần
    assert vals["11"] == (19410766207, 16239369636)  # Giá vốn hàng bán
    assert vals["50"] == (-2677527567, -1184043693)  # Tổng lợi nhuận trước thuế
    assert vals["70"] == (0, 0)                      # Lãi cơ bản trên cổ phiếu
```

- [ ] **Step 5: Chạy test để xác nhận thất bại**

```bash
.venv/bin/python -m pytest tests/test_groundtruth.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'tests.regression.groundtruth'`

- [ ] **Step 6: Cài đặt bộ đọc đáp án**

Tạo `tests/regression/groundtruth.py`:

```python
# -*- coding: utf-8 -*-
"""
Đọc file Excel "đáp án" (bản xuất trực tiếp từ phần mềm kế toán).

Ba cạm bẫy đã xác nhận trên corpus thật:
  1. Đuôi file nói dối: 'KQKD.XLS' thực chất là OOXML (bắt đầu bằng 'PK').
     openpyxl từ chối theo ĐUÔI FILE chứ không theo nội dung -> phải nạp qua
     BytesIO sau khi tự dò magic bytes.
  2. Nhãn chỉ tiêu là mojibake TCVN3 ('C«ng ty CP Du LÞch §¨k L¨k'). Không cần
     giải mã: ta chỉ dùng MÃ SỐ + CON SỐ.
  3. Hàng tiêu đề không ở vị trí cố định -> phải dò động.
"""
import io
import os
import re

MAGIC_OOXML = b"PK\x03\x04"
MAGIC_BIFF = b"\xd0\xcf\x11\xe0"

# Thứ tự quan trọng: 'can doi ke toan' phải xét TRƯỚC 'cdps/cdsps' vì
# 'CDSPS.XLS' cũng chứa 'cd'. Mỗi mẫu khớp trên tên file đã hạ chữ thường.
_KIND_PATTERNS = (
    ("CDPS", r"cdsps|cdps|can doi so phat sinh|can doi phat sinh"),
    ("CDKT", r"cdkt|can doi ke toan|bang can doi"),
    ("KQHDKD", r"kqkd|kqhdkd|ket qua"),
    ("LCTT", r"lctt|luu chuyen"),
)


def statement_kind(filename):
    """Suy ra loại báo cáo từ tên file. Trả về '' nếu không nhận ra."""
    name = os.path.basename(filename).lower()
    for kind, pat in _KIND_PATTERNS:
        if re.search(pat, name):
            return kind
    return ""


def sniff_format(path):
    """Dò định dạng thật theo magic bytes, KHÔNG tin đuôi file."""
    with open(path, "rb") as fh:
        head = fh.read(8)
    if head.startswith(MAGIC_OOXML):
        return "ooxml"
    if head.startswith(MAGIC_BIFF):
        return "biff"
    return "unknown"


def _rows_ooxml(path):
    import openpyxl
    with open(path, "rb") as fh:
        data = fh.read()
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    ws = wb[wb.sheetnames[0]]
    try:
        return [list(r) for r in ws.iter_rows(values_only=True)]
    finally:
        wb.close()


def _rows_biff(path):
    import xlrd
    book = xlrd.open_workbook(path)
    sh = book.sheet_by_index(0)
    return [[sh.cell_value(r, c) for c in range(sh.ncols)]
            for r in range(sh.nrows)]


def _read_rows(path):
    fmt = sniff_format(path)
    if fmt == "ooxml":
        return _rows_ooxml(path)
    if fmt == "biff":
        return _rows_biff(path)
    raise ValueError("Không nhận ra định dạng Excel: %s" % path)


def _to_int(v):
    """Chuyển ô Excel thành int. Trả về None nếu ô rỗng/không phải số."""
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(round(v))
    s = str(v).strip()
    if not s:
        return None
    neg = s.startswith("(") and s.endswith(")")
    digits = re.sub(r"[^\d\-]", "", s)
    if digits in ("", "-"):
        return None
    val = int(digits)
    return -abs(val) if neg else val


_CODE_CELL = re.compile(r"^\s*(\d{1,3}[abc]?)\s*$")


def _find_columns(rows):
    """
    Dò (cột mã số, cột năm nay, cột năm trước).

    Neo vào hàng đánh số thứ tự cột ('1','2','3','4','5') vì nhãn tiêu đề là
    mojibake nên không so khớp chữ được. Hàng đó nằm ngay dưới hàng tiêu đề và
    có ít nhất 4 ô là số nguyên nhỏ tăng dần bắt đầu từ 1.
    """
    for r, row in enumerate(rows[:25]):
        nums = [(c, _to_int(v)) for c, v in enumerate(row) if _to_int(v) is not None]
        seq = [(c, n) for c, n in nums if 1 <= n <= 9]
        if len(seq) >= 4 and [n for _, n in seq][:4] == [1, 2, 3, 4]:
            cols = [c for c, _ in seq]
            # cột 1 = Chỉ tiêu, 2 = Mã số, 3 = Thuyết minh, 4 = Năm nay, 5 = Năm trước
            code_col = cols[1]
            cur_col = cols[3]
            prior_col = cols[4] if len(cols) >= 5 else cols[3] + 1
            return r, code_col, cur_col, prior_col
    return None


def read_statement(path):
    """
    Trả về {ma_so: (nam_nay, nam_truoc)}.

    Mã số giữ nguyên dạng in trong file ('1' chứ không phải '01') — việc chuẩn
    hoá là trách nhiệm của bên so sánh.
    """
    rows = _read_rows(path)
    found = _find_columns(rows)
    if not found:
        raise ValueError("Không dò được hàng tiêu đề trong %s" % path)
    hdr_row, code_col, cur_col, prior_col = found

    out = {}
    for row in rows[hdr_row + 1:]:
        if code_col >= len(row):
            continue
        raw = row[code_col]
        code = None
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            code = str(int(round(raw)))
        else:
            m = _CODE_CELL.match(str(raw or ""))
            if m:
                code = m.group(1)
        if not code:
            continue
        cur = _to_int(row[cur_col]) if cur_col < len(row) else None
        prior = _to_int(row[prior_col]) if prior_col < len(row) else None
        out[code] = (cur, prior)
    return out
```

- [ ] **Step 7: Chạy test để xác nhận thành công**

```bash
.venv/bin/python -m pytest tests/test_groundtruth.py -v
```

Expected: PASS (4 test; các test cần corpus sẽ SKIP nếu máy không có corpus)

- [ ] **Step 8: Commit**

```bash
git add requirements-dev.txt tests/
git commit -m "test: bộ đọc file Excel đáp án, dò định dạng theo magic bytes

Đuôi file trong corpus nói dối: 'KQKD.XLS' thực chất là OOXML. openpyxl từ
chối theo đuôi file nên phải tự dò magic bytes rồi nạp qua BytesIO. Nhãn chỉ
tiêu là mojibake TCVN3 nên hàng tiêu đề được dò bằng cách neo vào hàng đánh
số thứ tự cột thay vì so khớp chữ."
```

---

### Task 2: Ghép cặp PDF ↔ Excel và đóng băng danh sách

Ghép sai còn tệ hơn không ghép. Thử nghiệm cho thấy ghép theo số đầu tên file nối `1 Can doi ke toan 06 thang dau 2025.xlsx` (thuộc công ty 27) với `01_CTCP DVTH Saigon 2025 (Riêng).pdf` — hai doanh nghiệp khác nhau. Mã công ty **chỉ được lấy từ tên thư mục**.

**Files:**
- Create: `tests/regression/build_pairs.py`
- Create: `tests/regression/pairs.json` (sinh ra rồi người xác nhận)
- Test: `tests/test_build_pairs.py`

**Interfaces:**
- Consumes: `groundtruth.statement_kind` (Task 1)
- Produces:
  - `build_pairs.company_index(path: str) -> str` — mã công ty từ thư mục tổ tiên, `''` nếu không có
  - `build_pairs.period(path: str) -> str` — `'6T'` | `'Q1'`..`'Q4'` | `'NAM'`
  - `build_pairs.year(path: str) -> str` — `'2025'` hoặc `''`
  - `build_pairs.build(corpus_root: str) -> list` — danh sách dict `{"pdf","excel","kind","company","year","period"}`
  - File `tests/regression/pairs.json`: `{"pairs": [ ...dict như trên... ]}`

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_build_pairs.py`:

```python
# -*- coding: utf-8 -*-
import pytest

from tests.regression import build_pairs as B


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
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

```bash
.venv/bin/python -m pytest tests/test_build_pairs.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'tests.regression.build_pairs'`

- [ ] **Step 3: Cài đặt bộ ghép cặp**

Tạo `tests/regression/build_pairs.py`:

```python
# -*- coding: utf-8 -*-
"""
Đề xuất cặp (PDF, Excel đáp án) để dựng bộ hồi quy.

QUY TẮC SỐNG CÒN: mã công ty CHỈ lấy từ tên THƯ MỤC tổ tiên khớp '^NN[._ -]'.
Lấy từ tên file sẽ ghép nhầm công ty — đã kiểm chứng: file
'1 Can doi ke toan 06 thang dau 2025.xlsx' nằm trong thư mục
'27_Cty CP SXKD Hàng XK Tân Bình 6Th_2025/' nhưng số '1' ở đầu tên file lại
nối nó với '01_CTCP DVTH Saigon 2025 (Riêng).pdf'.

Kết quả của module này là ĐỀ XUẤT. Người phải xác nhận rồi mới đóng băng vào
pairs.json — xem hướng dẫn ở cuối file.
"""
import os
import re
import glob
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


def build(corpus_root):
    """Trả về danh sách cặp đề xuất, khớp cả (mã công ty, năm, kỳ)."""
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

    out = []
    for x in excels:
        c, y, p = company_index(x), year(x), period(x)
        if not (c and y):
            continue
        cands = pdfs.get((c, y, p))
        if not cands:
            continue
        out.append({
            "pdf": min(cands, key=len),      # tên ngắn nhất = ít hậu tố nhất
            "excel": x,
            "kind": groundtruth.statement_kind(x),
            "company": c,
            "year": y,
            "period": p,
        })
    return sorted(out, key=lambda d: (d["company"], d["year"], d["kind"]))


def main():
    root = os.environ.get(
        "BCTC_CORPUS", "/Users/motmi/Documents/DAYS/Y-NHI/BTG/Documents")
    pairs = build(root)
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(here, "pairs.candidate.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump({"pairs": pairs}, fh, ensure_ascii=False, indent=2)
    print("Đã đề xuất %d cặp (%d PDF riêng biệt) -> %s"
          % (len(pairs), len({p["pdf"] for p in pairs}), out_path))
    print("\nNGƯỜI PHẢI XÁC NHẬN trước khi dùng:")
    print("  1. Mở pairs.candidate.json, đối chiếu từng cặp.")
    print("  2. Xoá cặp sai phạm vi (riêng vs hợp nhất) hoặc sai kỳ.")
    print("  3. Đổi tên thành pairs.json rồi commit.")
    for p in pairs:
        print("  CT%-3s %s %-4s %-7s %s  <-  %s"
              % (p["company"], p["year"], p["period"], p["kind"],
                 os.path.basename(p["excel"])[:30],
                 os.path.basename(p["pdf"])[:44]))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Chạy test để xác nhận thành công**

```bash
.venv/bin/python -m pytest tests/test_build_pairs.py -v
```

Expected: PASS (6 test)

- [ ] **Step 5: Sinh danh sách đề xuất**

```bash
.venv/bin/python -m tests.regression.build_pairs
```

Expected: in ra khoảng **45 cặp / 14 PDF riêng biệt**, kèm bảng liệt kê.

- [ ] **Step 6: NGƯỜI XÁC NHẬN — cổng kiểm duyệt bắt buộc**

Đây **không** phải bước tự động. Mở `tests/regression/pairs.candidate.json` và kiểm từng cặp:

1. Excel và PDF có **cùng doanh nghiệp** không? (đối chiếu tên đầy đủ, không chỉ mã số)
2. Có **cùng kỳ** không? (đáp án 6 tháng không được ghép với PDF cả năm)
3. Có **cùng phạm vi** không? (`riêng` vs `hợp nhất` — số liệu khác nhau hoàn toàn)

Xoá mọi cặp không chắc chắn. **Thà ít cặp đúng còn hơn nhiều cặp sai** — một cặp sai làm hỏng toàn bộ chỉ số. Sau đó:

```bash
mv tests/regression/pairs.candidate.json tests/regression/pairs.json
```

- [ ] **Step 7: Commit**

```bash
git add tests/regression/build_pairs.py tests/regression/pairs.json tests/test_build_pairs.py
git commit -m "test: ghép cặp PDF-Excel đáp án, mã công ty lấy từ thư mục

Ghép theo số đầu tên file cho ra cặp SAI CÔNG TY: '1 Can doi ke toan 06 thang
dau 2025.xlsx' thuộc công ty 27 nhưng bị nối với '01_CTCP DVTH Saigon'. Mã
công ty vì vậy chỉ lấy từ tên thư mục tổ tiên, và phải khớp cả năm lẫn kỳ báo
cáo. Danh sách cặp đã được người xác nhận và đóng băng."
```

---

### Task 3: Chỉ số tầng 1 và tầng 2

**Files:**
- Create: `tests/regression/metrics.py`
- Test: `tests/test_metrics.py`

**Interfaces:**
- Consumes: `bctc.templates` (đã có), `bctc.engine._check_balance` (đã có)
- Produces:
  - `metrics.canon(code: str) -> str` — chuẩn hoá mã để so sánh (`'01'` và `'1'` cùng cho `'1'`)
  - `metrics.compare(expected: dict, actual: dict) -> dict` — `{"dung","sot","lech","thua"}` → int
  - `metrics.coverage(values: dict, stmt_key: str) -> float` — tỷ lệ 0..1
  - `metrics.balance_score(cdkt: dict) -> tuple` — `(so_dat, tong_so)`

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_metrics.py`:

```python
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
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

```bash
.venv/bin/python -m pytest tests/test_metrics.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'tests.regression.metrics'`

- [ ] **Step 3: Cài đặt module chỉ số**

Tạo `tests/regression/metrics.py`:

```python
# -*- coding: utf-8 -*-
"""
Chỉ số chất lượng bóc tách.

Tầng 1 (cần đáp án): đúng / sót / lệch / thừa.
Tầng 2 (không cần đáp án): độ phủ khung + tỷ lệ đạt kiểm tra cân đối.

Tầng 2 tồn tại vì chỉ có 14 PDF là có đáp án, quá mỏng để phủ các nhóm file
trước 2015, file ngân hàng, file mojibake. Độ phủ là proxy trực tiếp cho "sót
data"; cân đối là proxy cho "lệch data".
"""
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from bctc import templates as T      # noqa: E402
from bctc import engine              # noqa: E402


def canon(code):
    """
    Dạng chính tắc để so khớp mã số.

    Báo cáo in mã là '1', khung template ghi '01' -> phải quy về một dạng.
    Giữ nguyên hậu tố chữ ('411a').
    """
    s = str(code).strip()
    m = re.match(r"^0*(\d+)([abc]?)$", s)
    if not m:
        return s
    return m.group(1) + m.group(2)


def _codes(stmt_key):
    """Tập mã số của khung, dạng chính tắc."""
    if stmt_key == "LCTT":
        tpl_codes = (T.codes_of(T.LUU_CHUYEN_TIEN_TE_GT)
                     | T.codes_of(T.LUU_CHUYEN_TIEN_TE_TT))
    else:
        tpl_codes = T.codes_of(T.STATEMENTS[stmt_key][1])
    return {canon(c) for c in tpl_codes}


def _norm_map(d):
    return {canon(k): v for k, v in (d or {}).items()}


def compare(expected, actual):
    """
    So từng ô. Ô đáp án rỗng hoặc bằng 0 được coi là "không có số liệu" và
    chỉ dùng để phát hiện 'thừa'.
    """
    exp, act = _norm_map(expected), _norm_map(actual)
    out = {"dung": 0, "sot": 0, "lech": 0, "thua": 0}
    for code in set(exp) | set(act):
        e = exp.get(code, (None, None))
        a = act.get(code, (None, None))
        for i in (0, 1):
            g, o = e[i], a[i]
            has_g = g is not None and g != 0
            has_o = o is not None and o != 0
            if has_g and o == g:
                out["dung"] += 1
            elif has_g and not has_o:
                out["sot"] += 1
            elif has_g:
                out["lech"] += 1
            elif has_o:
                out["thua"] += 1
    return out


def coverage(values, stmt_key):
    """Tỷ lệ mã trong khung có ít nhất một giá trị khác None."""
    codes = _codes(stmt_key)
    if not codes:
        return 0.0
    got = {c for c, v in _norm_map(values).items()
           if c in codes and v and any(x is not None for x in v)}
    return len(got) / float(len(codes))


def balance_score(cdkt):
    """(số phép kiểm tra đạt, tổng số phép chạy được) trên Bảng cân đối."""
    checks = engine._check_balance(cdkt or {})
    return sum(1 for _, ok, _ in checks if ok), len(checks)
```

- [ ] **Step 4: Chạy test để xác nhận thành công**

```bash
.venv/bin/python -m pytest tests/test_metrics.py -v
```

Expected: PASS (5 test)

- [ ] **Step 5: Commit**

```bash
git add tests/regression/metrics.py tests/test_metrics.py
git commit -m "test: chỉ số tầng 1 (đúng/sót/lệch/thừa) và tầng 2 (độ phủ, cân đối)

Tầng 2 không cần đáp án nên chạy được trên mọi nhóm file mà 14 PDF có đáp án
không với tới. Độ phủ là proxy trực tiếp cho sót data: lỗi mã 1 chữ số không
khớp khung sẽ hiện ra ngay dưới dạng độ phủ thấp bất thường ở KQHDKD/LCTT."
```

---

### Task 4: Đo tài nguyên (tầng 3)

Đây là tiêu chí nghiệm thu chính của Đợt 1 (G3/G4/G5), nên phải đo được trước khi sửa bất cứ thứ gì.

**Files:**
- Create: `tests/regression/resources.py`
- Test: `tests/test_resources.py`

**Interfaces:**
- Consumes: không có
- Produces:
  - `resources.ResourceProbe` — context manager, sau khi thoát có thuộc tính `wall` (float, giây), `cpu` (float, CPU-giây), `peak_rss_mb` (float)

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_resources.py`:

```python
# -*- coding: utf-8 -*-
from tests.regression.resources import ResourceProbe


def test_probe_do_duoc_thoi_gian_va_cpu():
    with ResourceProbe() as p:
        total = 0
        for i in range(2_000_000):     # đủ nặng để CPU-giây > 0
            total += i
    assert p.wall > 0
    assert p.cpu > 0
    assert p.peak_rss_mb > 0


def test_probe_cpu_khong_vuot_qua_wall_nhan_so_luong_cpu():
    import os
    with ResourceProbe() as p:
        sum(range(500_000))
    assert p.cpu <= p.wall * max(1, os.cpu_count() or 1) + 1.0
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

```bash
.venv/bin/python -m pytest tests/test_resources.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'tests.regression.resources'`

- [ ] **Step 3: Cài đặt bộ đo tài nguyên**

Tạo `tests/regression/resources.py`:

```python
# -*- coding: utf-8 -*-
"""
Đo tài nguyên một đoạn xử lý: thời gian thực, CPU-giây, RSS đỉnh.

CPU-giây là chỉ số quan trọng nhất cho mục tiêu "giảm nhiệt": nó đo tổng công
CPU đã bỏ ra, không phụ thuộc việc chạy song song bao nhiêu luồng. Giảm
CPU-giây = giảm nhiệt thật, còn giảm thời gian thực có thể chỉ là chạy nhiều
luồng hơn (thậm chí NÓNG hơn).
"""
import os
import time


def _peak_rss_mb():
    """RSS đỉnh của tiến trình, tính bằng MB. Trả 0.0 nếu không đo được."""
    try:
        import resource
        val = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux trả KB, macOS trả byte
        return val / (1024.0 * 1024.0) if val > 1 << 20 else val / 1024.0
    except ImportError:
        pass
    try:                                    # Windows
        import ctypes
        from ctypes import wintypes

        class _PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD),
                        ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t),
                        ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t),
                        ("PeakPagefileUsage", ctypes.c_size_t)]

        c = _PMC()
        c.cb = ctypes.sizeof(c)
        ctypes.windll.psapi.GetProcessMemoryInfo(
            ctypes.windll.kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb)
        return c.PeakWorkingSetSize / (1024.0 * 1024.0)
    except Exception:
        return 0.0


def _cpu_seconds():
    """CPU-giây của tiến trình VÀ các tiến trình con (tesseract chạy ở con)."""
    t = time.process_time()
    try:
        import resource
        ch = resource.getrusage(resource.RUSAGE_CHILDREN)
        t += ch.ru_utime + ch.ru_stime
    except ImportError:
        pass
    return t


class ResourceProbe(object):
    """Context manager đo tài nguyên. Dùng: with ResourceProbe() as p: ..."""

    def __init__(self):
        self.wall = 0.0
        self.cpu = 0.0
        self.peak_rss_mb = 0.0

    def __enter__(self):
        self._t0 = time.time()
        self._c0 = _cpu_seconds()
        return self

    def __exit__(self, *exc):
        self.wall = time.time() - self._t0
        self.cpu = _cpu_seconds() - self._c0
        self.peak_rss_mb = _peak_rss_mb()
        return False
```

- [ ] **Step 4: Chạy test để xác nhận thành công**

```bash
.venv/bin/python -m pytest tests/test_resources.py -v
```

Expected: PASS (2 test)

- [ ] **Step 5: Commit**

```bash
git add tests/regression/resources.py tests/test_resources.py
git commit -m "test: đo thời gian thực, CPU-giây và RSS đỉnh

CPU-giây tính cả tiến trình con vì tesseract chạy ở tiến trình riêng. Đây là
chỉ số then chốt cho mục tiêu giảm nhiệt: giảm CPU-giây là giảm nhiệt thật,
còn giảm thời gian thực có thể chỉ là chạy nhiều luồng hơn."
```

---

### Task 5: Bộ chạy hồi quy và chốt baseline

Đây là task quan trọng nhất của GĐ0: kết thúc task này ta có **con số baseline** để mọi thay đổi sau đối chiếu.

**Files:**
- Create: `tests/regression/run_regression.py`
- Create: `docs/superpowers/plans/baseline-2026-07-19.json` (kết quả chạy)

**Interfaces:**
- Consumes: `groundtruth.read_statement`, `build_pairs` (pairs.json), `metrics.*`, `resources.ResourceProbe`, `bctc.engine.convert_pdf`
- Produces:
  - `run_regression.run_tier1(pairs, out_dir) -> dict`
  - `run_regression.run_tier2(pdf_paths, out_dir) -> dict`
  - File JSON báo cáo với khoá `tier1`, `tier2`, `tier3`, `meta`

- [ ] **Step 1: Cài đặt bộ chạy**

Tạo `tests/regression/run_regression.py`:

```python
# -*- coding: utf-8 -*-
"""
Chạy bộ hồi quy: tầng 1 (đối chiếu đáp án), tầng 2 (độ phủ + cân đối),
tầng 3 (tài nguyên). Xuất một file JSON để so sánh trước/sau.

Dùng:
    python -m tests.regression.run_regression --out baseline.json
    python -m tests.regression.run_regression --out sau-gd1.json --tier2-sample 300
"""
import os
import sys
import json
import glob
import random
import argparse
import tempfile
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from bctc import engine                              # noqa: E402
from tests.regression import groundtruth, metrics    # noqa: E402
from tests.regression.resources import ResourceProbe  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
STMT_KEYS = ("CDKT", "KQHDKD", "LCTT")


def load_pairs():
    path = os.path.join(HERE, "pairs.json")
    if not os.path.exists(path):
        raise SystemExit(
            "Chưa có pairs.json. Chạy 'python -m tests.regression.build_pairs' "
            "rồi xác nhận thủ công trước.")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["pairs"]


def _convert(pdf_path, out_dir):
    """Chạy engine trên 1 PDF, trả về (results, resource_probe) hoặc (None, probe)."""
    with ResourceProbe() as probe:
        try:
            res = engine.convert_pdf(pdf_path, out_dir)
        except Exception:
            traceback.print_exc()
            return None, probe
    return res, probe


def run_tier1(pairs, out_dir):
    """Đối chiếu giá trị tuyệt đối với đáp án."""
    by_pdf = {}
    for p in pairs:
        by_pdf.setdefault(p["pdf"], []).append(p)

    total = {"dung": 0, "sot": 0, "lech": 0, "thua": 0}
    per_file = []
    for pdf, group in sorted(by_pdf.items()):
        print("  [tầng 1] %s" % os.path.basename(pdf))
        res, probe = _convert(pdf, out_dir)
        if res is None:
            per_file.append({"pdf": pdf, "error": True})
            continue
        # engine.convert_pdf trả dict có khoá 'rows'; giá trị thật nằm ở
        # kết quả bóc tách -> đọc lại từ file Excel là thừa, nên ta gọi thẳng
        # parser qua engine và lấy 'results' đã lưu trong biến trả về.
        got = res.get("results") or {}
        f_counts = {"dung": 0, "sot": 0, "lech": 0, "thua": 0}
        for item in group:
            kind = item["kind"]
            if kind not in STMT_KEYS:
                continue          # CDPS không có sheet tương ứng
            try:
                expected = groundtruth.read_statement(item["excel"])
            except Exception as e:
                print("     ⚠ không đọc được đáp án: %s" % e)
                continue
            c = metrics.compare(expected, got.get(kind, {}))
            for k in f_counts:
                f_counts[k] += c[k]
        for k in total:
            total[k] += f_counts[k]
        per_file.append({"pdf": pdf, "counts": f_counts,
                         "wall": probe.wall, "cpu": probe.cpu})
    return {"total": total, "per_file": per_file}


def run_tier2(pdf_paths, out_dir):
    """Độ phủ + tỷ lệ đạt cân đối, không cần đáp án."""
    cov_sum = {k: 0.0 for k in STMT_KEYS}
    bal_ok = bal_total = 0
    ok_files = 0
    per_file = []
    for pdf in pdf_paths:
        print("  [tầng 2] %s" % os.path.basename(pdf))
        res, probe = _convert(pdf, out_dir)
        if res is None:
            per_file.append({"pdf": pdf, "error": True})
            continue
        got = res.get("results") or {}
        covs = {k: metrics.coverage(got.get(k, {}), k) for k in STMT_KEYS}
        o, t = metrics.balance_score(got.get("CDKT", {}))
        for k in STMT_KEYS:
            cov_sum[k] += covs[k]
        bal_ok += o
        bal_total += t
        ok_files += 1
        per_file.append({"pdf": pdf, "coverage": covs, "balance": [o, t],
                         "wall": probe.wall, "cpu": probe.cpu,
                         "rss_mb": probe.peak_rss_mb})
    n = max(1, ok_files)
    return {
        "n_files": ok_files,
        "coverage_avg": {k: cov_sum[k] / n for k in STMT_KEYS},
        "balance_pass_rate": (bal_ok / float(bal_total)) if bal_total else 0.0,
        "per_file": per_file,
    }


def sample_corpus(root, n, seed=20260719):
    """Mẫu phân tầng theo thư mục năm để phủ đều các giai đoạn."""
    pdfs = [f for f in glob.glob(os.path.join(root, "**", "*.pdf"), recursive=True)
            if os.path.isfile(f) and os.path.getsize(f) > 0]
    rnd = random.Random(seed)
    rnd.shuffle(pdfs)
    return pdfs[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="file JSON kết quả")
    ap.add_argument("--tier2-sample", type=int, default=30)
    ap.add_argument("--skip-tier1", action="store_true")
    args = ap.parse_args()

    root = os.environ.get(
        "BCTC_CORPUS", "/Users/motmi/Documents/DAYS/Y-NHI/BTG/Documents")
    report = {"meta": {"corpus": root, "tier2_sample": args.tier2_sample}}

    out_dir = tempfile.mkdtemp(prefix="bctc_reg_")
    print("Thư mục kết quả tạm: %s" % out_dir)

    with ResourceProbe() as overall:
        if not args.skip_tier1:
            print("Tầng 1 — đối chiếu đáp án")
            report["tier1"] = run_tier1(load_pairs(), out_dir)
        print("Tầng 2 — độ phủ + cân đối (%d file)" % args.tier2_sample)
        report["tier2"] = run_tier2(sample_corpus(root, args.tier2_sample), out_dir)

    report["tier3"] = {"wall": overall.wall, "cpu": overall.cpu,
                       "peak_rss_mb": overall.peak_rss_mb}

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)

    print("\n================ TÓM TẮT ================")
    if "tier1" in report:
        t = report["tier1"]["total"]
        tot = sum(t.values()) or 1
        print("Tầng 1: đúng=%d (%.1f%%) sót=%d lệch=%d thừa=%d"
              % (t["dung"], 100.0 * t["dung"] / tot, t["sot"], t["lech"], t["thua"]))
    t2 = report["tier2"]
    print("Tầng 2: %d file | độ phủ CĐKT=%.1f%% KQ=%.1f%% LC=%.1f%% | cân đối đạt=%.1f%%"
          % (t2["n_files"], 100 * t2["coverage_avg"]["CDKT"],
             100 * t2["coverage_avg"]["KQHDKD"], 100 * t2["coverage_avg"]["LCTT"],
             100 * t2["balance_pass_rate"]))
    t3 = report["tier3"]
    print("Tầng 3: thực=%.1fs CPU=%.1fs RSS đỉnh=%.0fMB"
          % (t3["wall"], t3["cpu"], t3["peak_rss_mb"]))
    print("Đã lưu: %s" % args.out)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Bổ sung `results` vào giá trị trả về của engine**

`run_tier1` cần giá trị bóc tách thô, nhưng `engine.convert_pdf` hiện không trả về. Sửa `bctc/engine.py`, trong khối `return` ở cuối `convert_pdf` (khoảng dòng 73-77), thêm khoá `results`:

```python
    return {
        "pdf": pdf_path, "name": name, "out_path": out_path,
        "rows": n_rows, "warnings": warnings, "checks": checks,
        "conflicts": conflicts,
        "results": results,          # <-- THÊM: phục vụ bộ đo hồi quy
    }
```

- [ ] **Step 3: Chạy thử nhanh để kiểm tra bộ chạy hoạt động**

```bash
.venv/bin/python -m tests.regression.run_regression \
    --out /tmp/smoke.json --tier2-sample 2 --skip-tier1
```

Expected: chạy xong, in dòng `Tầng 2: 2 file | độ phủ ...` và `Đã lưu: /tmp/smoke.json`

- [ ] **Step 4: Chạy baseline đầy đủ**

Lệnh này chạy lâu (mỗi PDF vài chục giây). Chạy nền và theo dõi:

```bash
.venv/bin/python -m tests.regression.run_regression \
    --out docs/superpowers/plans/baseline-2026-07-19.json \
    --tier2-sample 30
```

Expected: bảng TÓM TẮT với ba dòng tầng 1/2/3. **Ghi lại các con số này** — đây là baseline.

- [ ] **Step 5: Kiểm chứng dự đoán về mã 1 chữ số**

Baseline phải cho thấy **độ phủ KQHDKD và LCTT thấp bất thường** so với CĐKT, vì mã `01`–`09` không bao giờ khớp. Xác nhận:

```bash
.venv/bin/python -c "
import json
r=json.load(open('docs/superpowers/plans/baseline-2026-07-19.json'))
c=r['tier2']['coverage_avg']
print('CĐKT   %.1f%%' % (100*c['CDKT']))
print('KQHDKD %.1f%%' % (100*c['KQHDKD']))
print('LCTT   %.1f%%' % (100*c['LCTT']))
"
```

Expected: KQHDKD và LCTT thấp hơn CĐKT rõ rệt. Nếu **không** thấy chênh lệch, dự đoán ở spec §7.1 sai — ghi nhận lại vào spec trước khi đi tiếp.

- [ ] **Step 6: Commit**

```bash
git add tests/regression/run_regression.py bctc/engine.py \
        docs/superpowers/plans/baseline-2026-07-19.json
git commit -m "test: bộ chạy hồi quy 3 tầng và số liệu baseline

engine.convert_pdf trả thêm khoá 'results' để bộ đo lấy được giá trị bóc tách
thô mà không phải đọc ngược từ file Excel."
```

---

# GIAI ĐOẠN 1 — CẮT TÍNH TOÁN THỪA

### Task 6: Đưa `locate_pages` ra khỏi vòng lặp DPI

`parser.extract()` gọi `locate_pages()` ở dòng 293, còn `extract_consensus()` gọi `extract()` một lần cho **mỗi** DPI (dòng 380). Kết quả định vị là tất định nên đang lãng phí trọn một lượt quét đầu trang của toàn tài liệu cho mỗi DPI phụ.

**Files:**
- Modify: `bctc/parser.py:287` (chữ ký `extract`), `bctc/parser.py:293` (lời gọi `locate_pages`), `bctc/parser.py:367-399` (`extract_consensus`)
- Test: `tests/test_parser_scope.py`

**Interfaces:**
- Consumes: không có
- Produces: `parser.extract(doc, lang, dpi, page_range, log, scope=None)` — khi truyền `scope` thì bỏ qua bước định vị

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_parser_scope.py`:

```python
# -*- coding: utf-8 -*-
"""locate_pages chỉ được chạy MỘT lần dù bóc tách ở nhiều DPI."""
import fitz
import pytest

from bctc import parser


def _doc_rong():
    d = fitz.open()
    d.new_page()
    return d


def test_extract_nhan_tham_so_scope():
    import inspect
    assert "scope" in inspect.signature(parser.extract).parameters


def test_extract_consensus_chi_goi_locate_pages_mot_lan(monkeypatch):
    calls = []

    def fake_locate(doc, **kw):
        calls.append(1)
        return []

    def fake_extract(doc, lang="vie", dpi=300, page_range=None,
                     log=lambda *_: None, scope=None):
        if scope is None:
            fake_locate(doc)
        return {k: {} for k in ("CDKT", "KQHDKD", "LCTT")}, [], {}

    monkeypatch.setattr(parser, "locate_pages", fake_locate)
    monkeypatch.setattr(parser, "extract", fake_extract)

    doc = _doc_rong()
    parser.extract_consensus(doc, dpis=(180, 235, 290))
    doc.close()

    assert len(calls) == 1, "locate_pages phải chạy 1 lần, đang chạy %d lần" % len(calls)
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

```bash
.venv/bin/python -m pytest tests/test_parser_scope.py -v
```

Expected: FAIL — `assert 'scope' in ...` (tham số chưa có)

- [ ] **Step 3: Sửa `extract` để nhận `scope`**

Trong `bctc/parser.py`, đổi chữ ký hàm `extract` (dòng 287) và lời gọi `locate_pages` (dòng 293):

```python
def extract(doc, lang="vie", dpi=300, page_range=None, log=lambda *_: None,
            scope=None):
    """
    Trả về:
        results : {stmt_key: {code: (cur, prior)}}
        warnings: [str]

    scope: kết quả locate_pages() đã tính sẵn. Truyền vào để KHÔNG phải quét
           lại dải đầu trang ở mỗi lượt DPI — kết quả định vị là tất định nên
           quét lại chỉ tốn CPU mà không đổi kết quả.
    """
    if scope is None:
        scope = locate_pages(doc, lang=lang, page_range=page_range, log=log)
```

- [ ] **Step 4: Sửa `extract_consensus` để định vị một lần**

Trong `bctc/parser.py`, thay phần đầu vòng lặp của `extract_consensus` (dòng 377-385):

```python
    merged = {k: {} for k in T.STATEMENTS}
    conflicts = []
    base_warnings, base_meta = [], {}

    # Định vị MỘT lần rồi dùng chung cho mọi lượt DPI: kết quả tất định, quét
    # lại chỉ tốn thêm (số_DPI - 1) x số_trang lượt OCR mà không đổi gì.
    scope = locate_pages(doc, lang=lang, page_range=page_range, log=log)

    for idx, dpi in enumerate(dpis):
        primary = (idx == 0)
        res, warns, meta = extract(
            doc, lang=lang, dpi=dpi, page_range=page_range,
            log=(log if primary else (lambda *_: None)), scope=scope)
```

- [ ] **Step 5: Chạy test để xác nhận thành công**

```bash
.venv/bin/python -m pytest tests/test_parser_scope.py -v
```

Expected: PASS (2 test)

- [ ] **Step 6: Đo mức cải thiện thật**

```bash
.venv/bin/python -m tests.regression.run_regression \
    --out /tmp/sau-task6.json --tier2-sample 30
.venv/bin/python -c "
import json
a=json.load(open('docs/superpowers/plans/baseline-2026-07-19.json'))
b=json.load(open('/tmp/sau-task6.json'))
print('CPU-giây: %.1f -> %.1f (giảm %.0f%%)' % (
    a['tier3']['cpu'], b['tier3']['cpu'],
    100*(1-b['tier3']['cpu']/a['tier3']['cpu'])))
for k in ('CDKT','KQHDKD','LCTT'):
    print('  độ phủ %-7s %.1f%% -> %.1f%%' % (k,
        100*a['tier2']['coverage_avg'][k], 100*b['tier2']['coverage_avg'][k]))
"
```

Expected: CPU-giây **giảm rõ rệt**; độ phủ **không được giảm** (nếu giảm thì việc dùng chung `scope` đã làm hỏng kết quả — dừng lại và điều tra).

- [ ] **Step 7: Commit**

```bash
git add bctc/parser.py tests/test_parser_scope.py
git commit -m "perf: định vị trang một lần thay vì lặp lại mỗi lượt DPI

extract() gọi locate_pages() còn extract_consensus() gọi extract() một lần
mỗi DPI, nên lượt quét dải đầu trang của TOÀN tài liệu bị chạy lại 2-3 lần
với kết quả y hệt. Với file trung vị 28 trang ở chế độ thường, riêng thay đổi
này bỏ được 28 lượt OCR mỗi file."
```

---

### Task 7: Số luồng OCR theo chế độ

`parser.MAX_WORKERS = max(2, min(8, os.cpu_count()))` dùng **luồng logic**. Trên laptop 4 nhân/8 luồng thành 8 tiến trình Tesseract ghim sạch CPU, không chừa chỗ cho luồng giao diện. Đây là nguồn nhiệt chính.

**Files:**
- Create: `bctc/workers.py`
- Modify: `bctc/parser.py:21` (`MAX_WORKERS`), `bctc/parser.py:263`, `bctc/parser.py:326` (ThreadPoolExecutor)
- Test: `tests/test_workers.py`

**Interfaces:**
- Consumes: không có
- Produces:
  - `workers.MODE_ECO = "eco"`, `workers.MODE_BALANCED = "balanced"`, `workers.MODE_MAX = "max"`
  - `workers.worker_count(mode=MODE_BALANCED, logical=None) -> int`

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_workers.py`:

```python
# -*- coding: utf-8 -*-
import pytest

from bctc import workers as W


@pytest.mark.parametrize("logical,eco,balanced,mx", [
    (2, 1, 1, 1),
    (4, 1, 1, 3),
    (8, 1, 3, 7),
    (16, 1, 7, 15),
])
def test_worker_count_theo_so_luong_logic(logical, eco, balanced, mx):
    assert W.worker_count(W.MODE_ECO, logical) == eco
    assert W.worker_count(W.MODE_BALANCED, logical) == balanced
    assert W.worker_count(W.MODE_MAX, logical) == mx


def test_luon_it_nhat_mot_luong():
    for lg in (0, 1, 2):
        for m in (W.MODE_ECO, W.MODE_BALANCED, W.MODE_MAX):
            assert W.worker_count(m, lg) >= 1


def test_che_do_la_mac_dinh_can_bang():
    assert W.worker_count(logical=8) == W.worker_count(W.MODE_BALANCED, 8)


def test_che_do_khong_hop_le_quay_ve_can_bang():
    assert W.worker_count("linh tinh", 8) == W.worker_count(W.MODE_BALANCED, 8)
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

```bash
.venv/bin/python -m pytest tests/test_workers.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'bctc.workers'`

- [ ] **Step 3: Cài đặt module chọn số luồng**

Tạo `bctc/workers.py`:

```python
# -*- coding: utf-8 -*-
"""
Chọn số luồng OCR chạy song song.

Mỗi luồng gọi một tiến trình tesseract riêng (OMP_THREAD_LIMIT=1), nên số
luồng chính là số nhân CPU bị chiếm dụng hoàn toàn. Đặt bằng số LUỒNG LOGIC
sẽ ghim sạch CPU: máy nóng, quạt kêu, giao diện giật.

Máy đích là Windows 10, 4 GB RAM, 2-4 nhân — luôn phải chừa headroom cho
luồng giao diện và hệ điều hành.
"""
import os

MODE_ECO = "eco"
MODE_BALANCED = "balanced"
MODE_MAX = "max"

MODES = (MODE_ECO, MODE_BALANCED, MODE_MAX)

MODE_LABELS = {
    MODE_ECO: "Tiết kiệm điện",
    MODE_BALANCED: "Cân bằng",
    MODE_MAX: "Tối đa",
}


def worker_count(mode=MODE_BALANCED, logical=None):
    """
    Số luồng OCR nên dùng.

    eco      : 1 luồng — máy yếu, hoặc chạy nền lâu mà không muốn nóng.
    balanced : ~nửa số luồng logic, chừa 1 — mặc định.
    max      : tất cả trừ 1 — chỉ khi người dùng chủ động chọn.
    """
    if logical is None:
        logical = os.cpu_count() or 2
    logical = max(1, int(logical))

    if mode == MODE_ECO:
        return 1
    if mode == MODE_MAX:
        return max(1, logical - 1)
    return max(1, logical // 2 - 1)
```

- [ ] **Step 4: Chạy test để xác nhận thành công**

```bash
.venv/bin/python -m pytest tests/test_workers.py -v
```

Expected: PASS (7 test)

- [ ] **Step 5: Nối vào parser**

Trong `bctc/parser.py`, thay dòng 20-21:

```python
from . import ocr
from . import templates as T
from . import workers as W

# Số luồng OCR mặc định. Truyền tham số `workers` xuống các hàm để đổi lúc chạy
# mà không phải nạp lại module.
MAX_WORKERS = W.worker_count()
```

Trong `locate_pages` (dòng 253), thêm tham số và dùng nó:

```python
def locate_pages(doc, lang="vie", scan_dpi=135, page_range=None,
                 log=lambda *_: None, workers=None):
    """
    Quét dải đầu mỗi trang theo từng BATCH song song, dừng sớm khi đã tìm đủ
    cả 3 báo cáo và batch tiếp theo không còn trang báo cáo nào.
    """
    nw = workers or MAX_WORKERS
    lo, hi = (page_range or (0, doc.page_count))
    lo, hi = max(0, lo), min(doc.page_count, hi)
    pages = list(range(lo, hi))

    scope, found = [], set()
    with ThreadPoolExecutor(max_workers=nw) as ex:
        for b in range(0, len(pages), nw):
            chunk = pages[b:b + nw]
```

Trong `extract` (dòng 287), thêm tham số `workers=None`, và tại dòng 326 dùng nó:

```python
def extract(doc, lang="vie", dpi=300, page_range=None, log=lambda *_: None,
            scope=None, workers=None):
```

```python
    nw = workers or MAX_WORKERS
    with ThreadPoolExecutor(max_workers=nw) as ex:
        page_lines = dict(ex.map(_ocr, rendered))
```

Trong `extract_consensus`, thêm `workers=None` vào chữ ký và truyền xuống cả `locate_pages` lẫn `extract`:

```python
def extract_consensus(doc, lang="vie", dpis=(185, 240), page_range=None,
                      log=lambda *_: None, on_pass=lambda done, total: None,
                      workers=None):
```

```python
    scope = locate_pages(doc, lang=lang, page_range=page_range, log=log,
                         workers=workers)

    for idx, dpi in enumerate(dpis):
        primary = (idx == 0)
        res, warns, meta = extract(
            doc, lang=lang, dpi=dpi, page_range=page_range,
            log=(log if primary else (lambda *_: None)), scope=scope,
            workers=workers)
```

- [ ] **Step 6: Truyền chế độ qua engine**

Trong `bctc/engine.py`, thêm `mode` vào `convert_pdf` (dòng 45) và `convert_many` (dòng 80):

```python
from . import ocr
from . import parser
from . import excel_writer
from . import workers as W

MAX_FILES = 150
```

```python
def convert_pdf(pdf_path, out_dir, lang="vie", dpis=(180, 235), log=lambda *_: None,
                file_progress=lambda frac: None, cancel=lambda: False,
                mode=W.MODE_BALANCED):
```

```python
    results, warnings, _, conflicts = parser.extract_consensus(
        doc, lang=lang, dpis=dpis, log=log, on_pass=_on_pass,
        workers=W.worker_count(mode))
```

```python
def convert_many(pdf_paths, out_dir, lang="vie", dpis=(180, 235),
                 log=lambda *_: None, progress=lambda done, total: None,
                 on_file=lambda index, event, data: None,
                 cancel=lambda: False, pause_wait=lambda: None,
                 mode=W.MODE_BALANCED):
```

Và trong vòng lặp, truyền xuống:

```python
            r = convert_pdf(p, out_dir, lang=lang, dpis=dpis, log=log,
                            file_progress=lambda frac, i=i: on_file(i, "progress", frac),
                            cancel=cancel, mode=mode)
```

- [ ] **Step 7: Chạy toàn bộ test**

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: PASS toàn bộ

- [ ] **Step 8: Đo lại**

```bash
.venv/bin/python -m tests.regression.run_regression --out /tmp/sau-task7.json --tier2-sample 30
```

Expected: CPU-giây xấp xỉ Task 6 (số luồng ít hơn nhưng tổng công CPU không đổi), **thời gian thực có thể tăng nhẹ** — đây là đánh đổi có chủ ý: máy mát hơn. Độ phủ không đổi.

- [ ] **Step 9: Commit**

```bash
git add bctc/workers.py bctc/parser.py bctc/engine.py tests/test_workers.py
git commit -m "perf: số luồng OCR theo chế độ, chừa headroom cho giao diện

MAX_WORKERS đặt theo số luồng LOGIC nên máy 4 nhân/8 luồng chạy 8 tiến trình
tesseract, ghim sạch CPU. Chế độ Cân bằng (mặc định) lấy ~nửa số luồng logic
trừ 1, chế độ Tiết kiệm điện chỉ 1 luồng."
```

---

### Task 8: Khử trùng lặp theo hash nội dung

17,1% corpus (499 file, 4,11 GB) là bản sao y hệt.

**Files:**
- Create: `bctc/dedup.py`
- Modify: `bctc/engine.py` (`convert_many`)
- Test: `tests/test_dedup.py`

**Interfaces:**
- Consumes: không có
- Produces:
  - `dedup.file_digest(path: str, chunk: int = 1048576) -> str` — SHA-256 hex
  - `dedup.group_duplicates(paths: list) -> tuple` — `(dai_dien: dict, ban_sao: dict)` với `dai_dien[digest] = path`, `ban_sao[path] = path_dai_dien`

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_dedup.py`:

```python
# -*- coding: utf-8 -*-
import os

from bctc import dedup


def _viet(tmp_path, ten, noi_dung):
    p = tmp_path / ten
    p.write_bytes(noi_dung)
    return str(p)


def test_file_digest_giong_nhau_cho_noi_dung_giong_nhau(tmp_path):
    a = _viet(tmp_path, "a.pdf", b"X" * 5000)
    b = _viet(tmp_path, "b.pdf", b"X" * 5000)
    assert dedup.file_digest(a) == dedup.file_digest(b)


def test_file_digest_khac_nhau_cho_noi_dung_khac_nhau(tmp_path):
    a = _viet(tmp_path, "a.pdf", b"X" * 5000)
    c = _viet(tmp_path, "c.pdf", b"Y" * 5000)
    assert dedup.file_digest(a) != dedup.file_digest(c)


def test_group_duplicates_gom_dung_nhom(tmp_path):
    a = _viet(tmp_path, "a.pdf", b"X" * 5000)
    b = _viet(tmp_path, "b.pdf", b"X" * 5000)
    c = _viet(tmp_path, "c.pdf", b"Y" * 5000)
    dai_dien, ban_sao = dedup.group_duplicates([a, b, c])
    assert len(dai_dien) == 2                 # 2 nội dung riêng biệt
    assert ban_sao == {b: a}                  # b là bản sao của a
    assert a not in ban_sao and c not in ban_sao


def test_group_duplicates_giu_thu_tu_file_dau_lam_dai_dien(tmp_path):
    a = _viet(tmp_path, "a.pdf", b"Z" * 100)
    b = _viet(tmp_path, "b.pdf", b"Z" * 100)
    _, ban_sao = dedup.group_duplicates([a, b])
    assert ban_sao[b] == a


def test_file_rong_khong_gay_loi(tmp_path):
    e = _viet(tmp_path, "rong.pdf", b"")
    dai_dien, ban_sao = dedup.group_duplicates([e])
    assert len(dai_dien) == 1
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

```bash
.venv/bin/python -m pytest tests/test_dedup.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'bctc.dedup'`

- [ ] **Step 3: Cài đặt module khử trùng lặp**

Tạo `bctc/dedup.py`:

```python
# -*- coding: utf-8 -*-
"""
Phát hiện file PDF trùng nội dung để khỏi xử lý lại.

Khảo sát corpus: 17,1% file (499/2919, 4,11 GB) là bản sao y hệt của file
khác, do các thư mục lưu trữ chồng chéo nhau. Xử lý lại chúng là đốt CPU vô ích.
"""
import hashlib


def file_digest(path, chunk=1024 * 1024):
    """SHA-256 của toàn bộ nội dung file, đọc theo khối để không ngốn RAM."""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def group_duplicates(paths):
    """
    Gom các file trùng nội dung.

    Trả về (dai_dien, ban_sao):
        dai_dien[digest] = đường dẫn file ĐẦU TIÊN mang nội dung đó
        ban_sao[path]    = đường dẫn file đại diện tương ứng

    File nào không đọc được thì coi như riêng biệt (không gộp), để lỗi được
    báo đúng theo từng file thay vì bị nuốt mất.
    """
    dai_dien = {}
    ban_sao = {}
    for p in paths:
        try:
            d = file_digest(p)
        except OSError:
            continue
        if d in dai_dien:
            ban_sao[p] = dai_dien[d]
        else:
            dai_dien[d] = p
    return dai_dien, ban_sao
```

- [ ] **Step 4: Chạy test để xác nhận thành công**

```bash
.venv/bin/python -m pytest tests/test_dedup.py -v
```

Expected: PASS (5 test)

- [ ] **Step 5: Nối vào `convert_many`**

Trong `bctc/engine.py`, thêm import và sửa vòng lặp. Thay toàn bộ thân vòng lặp `for i, p in enumerate(pdf_paths):` (dòng 107-131) bằng:

```python
    os.makedirs(out_dir, exist_ok=True)
    out = []
    total = len(pdf_paths)

    # File trùng nội dung chỉ xử lý một lần rồi chép kết quả sang tên còn lại.
    _, ban_sao = dedup.group_duplicates(pdf_paths)
    ket_qua_theo_file = {}
    if ban_sao:
        log("↩ Phát hiện %d file trùng nội dung — sẽ dùng lại kết quả."
            % len(ban_sao))

    for i, p in enumerate(pdf_paths):
        pause_wait()                 # chặn nếu đang tạm dừng
        if cancel():                 # dừng hẳn trước khi sang file mới
            on_file(i, "cancelled", None)
            log("⏹ Đã dừng theo yêu cầu.")
            break
        on_file(i, "start", None)
        try:
            goc = ban_sao.get(p)
            if goc is not None and goc in ket_qua_theo_file:
                r = _luu_ban_sao(p, out_dir, ket_qua_theo_file[goc], log)
            else:
                r = convert_pdf(p, out_dir, lang=lang, dpis=dpis, log=log,
                                file_progress=lambda frac, i=i: on_file(i, "progress", frac),
                                cancel=cancel, mode=mode)
                ket_qua_theo_file[p] = r
            on_file(i, "done", r)
            out.append(r)
        except Cancelled:
            on_file(i, "cancelled", None)
            log("⏹ Đã dừng theo yêu cầu.")
            break
        except Exception as e:
            log(f"   ✖ Lỗi: {e}")
            log("   ⋯ chi tiết:\n   " + traceback.format_exc().replace("\n", "\n   "))
            r = {"pdf": p, "name": os.path.basename(p),
                 "error": str(e), "out_path": None}
            on_file(i, "error", str(e))
            out.append(r)
        progress(i + 1, total)
    return out
```

Thêm import ở đầu file (cạnh các import `from .` khác):

```python
from . import dedup
```

Và thêm hàm phụ ngay trước `convert_many`:

```python
def _luu_ban_sao(pdf_path, out_dir, ket_qua_goc, log):
    """Ghi lại kết quả của file gốc dưới tên của file trùng nội dung."""
    name = os.path.splitext(os.path.basename(pdf_path))[0]
    out_path = os.path.join(out_dir, name + ".xlsx")
    excel_writer.save(name, ket_qua_goc["results"], out_path,
                      conflicts=ket_qua_goc.get("conflicts"))
    log("↩ %s — trùng nội dung với %s, dùng lại kết quả."
        % (name, ket_qua_goc["name"]))
    r = dict(ket_qua_goc)
    r.update({"pdf": pdf_path, "name": name, "out_path": out_path,
              "trung_voi": ket_qua_goc["name"]})
    return r
```

- [ ] **Step 6: Viết test tích hợp cho luồng khử trùng lặp**

Thêm vào cuối `tests/test_dedup.py`:

```python
def test_convert_many_khong_xu_ly_lai_file_trung(tmp_path, monkeypatch):
    """File trùng nội dung phải dùng lại kết quả, không gọi convert_pdf lần hai."""
    from bctc import engine

    a = _viet(tmp_path, "a.pdf", b"PDFGIA" * 500)
    b = _viet(tmp_path, "b.pdf", b"PDFGIA" * 500)
    out_dir = str(tmp_path / "out")

    goi = []

    def fake_convert_pdf(pdf_path, od, **kw):
        goi.append(pdf_path)
        return {"pdf": pdf_path, "name": os.path.basename(pdf_path),
                "out_path": os.path.join(od, "x.xlsx"),
                "rows": {}, "warnings": [], "checks": [], "conflicts": [],
                "results": {"CDKT": {}, "KQHDKD": {}, "LCTT": {}}}

    monkeypatch.setattr(engine, "convert_pdf", fake_convert_pdf)
    monkeypatch.setattr(engine.ocr, "configure_tesseract", lambda: ("x", "y"))
    monkeypatch.setattr(engine.ocr, "has_vietnamese", lambda: True)

    res = engine.convert_many([a, b], out_dir)

    assert len(goi) == 1, "convert_pdf phải chạy 1 lần, đang chạy %d lần" % len(goi)
    assert len(res) == 2, "vẫn phải trả kết quả cho cả 2 file"
    assert res[1].get("trung_voi") == os.path.basename(a)
```

- [ ] **Step 7: Chạy test**

```bash
.venv/bin/python -m pytest tests/test_dedup.py -v
```

Expected: PASS (6 test)

- [ ] **Step 8: Commit**

```bash
git add bctc/dedup.py bctc/engine.py tests/test_dedup.py
git commit -m "perf: khử trùng lặp file theo hash nội dung

17,1% corpus (499 file, 4,11 GB) là bản sao y hệt do các thư mục lưu trữ
chồng chéo. File trùng giờ chỉ xử lý một lần rồi ghi lại kết quả dưới tên
riêng của nó, vẫn xuất đủ file Excel cho người dùng."
```

---

### Task 9: Đường đọc lớp text kèm ba bộ lọc

Chỉ 12,2% corpus có lớp text dùng được, nhưng 9,4% có lớp text **mojibake** trả về hàng chục nghìn ký tự rác trông như hợp lệ. Không có bộ lọc thì tính năng này làm dữ liệu **tệ hơn** hiện trạng.

**Files:**
- Create: `bctc/textlayer.py`
- Modify: `bctc/parser.py` (`extract` dùng lớp text khi có)
- Test: `tests/test_textlayer.py`

**Interfaces:**
- Consumes: không có
- Produces:
  - `textlayer.MIN_CHARS_PER_PAGE = 200`
  - `textlayer.MIN_DIACRITIC_RATIO = 0.02`
  - `textlayer.diacritic_ratio(text: str) -> float`
  - `textlayer.strip_signature_text(text: str) -> str`
  - `textlayer.is_usable(doc) -> bool`
  - `textlayer.page_lines(page) -> list` — cùng cấu trúc `ocr.ocr_lines()` phần tử thứ 3

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_textlayer.py`:

```python
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
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

```bash
.venv/bin/python -m pytest tests/test_textlayer.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'bctc.textlayer'`

- [ ] **Step 3: Cài đặt module đọc lớp text**

Tạo `bctc/textlayer.py`:

```python
# -*- coding: utf-8 -*-
"""
Đọc lớp text sẵn có trong PDF, thay cho OCR — khi và chỉ khi lớp text đó
THẬT SỰ dùng được.

Khảo sát corpus (2.919 file):
  - 78,2% không có lớp text  -> phải OCR
  -  9,4% có lớp text MOJIBAKE -> phải OCR (nguy hiểm nhất)
  - 12,2% có lớp text dùng được -> đọc thẳng, chính xác tuyệt đối, gần như
    không tốn CPU

Mojibake là ca nguy hiểm: page.get_text() trả về hàng chục nghìn ký tự trông
như hợp lệ nhưng là rác ('BAD CAD TAl CHfNH RII~NG' thay vì 'BÁO CÁO TÀI
CHÍNH RIÊNG'). Nguyên nhân: bảng mã VNI/TCVN3 khai báo nhầm thành WinAnsi,
do OCR sẵn của máy scan Canon. Đọc chúng mà không lọc sẽ cho ra dữ liệu sai
một cách âm thầm — tệ hơn hiện trạng.

Ba bộ lọc, phải qua HẾT mới được dùng lớp text.
"""
import re
import unicodedata

# Ngưỡng ký tự tối thiểu mỗi trang. Đây là bộ lọc quan trọng nhất trong thực
# tế: file 33_Cty CP DL Dak Lak 2024.pdf có 38 trang nhưng chỉ 352 ký tự (toàn
# bộ là lớp phủ chữ ký số) mà tỷ lệ dấu vẫn đạt 0,126 — chỉ ngưỡng ký tự mới
# chặn được nó.
MIN_CHARS_PER_PAGE = 200

# Tỷ lệ ký tự có dấu tiếng Việt tối thiểu. Đo thực tế trên corpus:
# file text tốt trung vị 0,270; file mojibake 0,000.
MIN_DIACRITIC_RATIO = 0.02

SIGNATURE_MARKERS = (
    "digitally signed",
    "signature not verified",
    "ký bởi",
    "ky boi",
)


def diacritic_ratio(text):
    """Tỷ lệ ký tự chữ cái mang dấu tiếng Việt trên tổng ký tự chữ cái."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    co_dau = 0
    for c in letters:
        d = unicodedata.normalize("NFD", c)
        if len(d) > 1 or c in "đĐ":
            co_dau += 1
    return co_dau / float(len(letters))


def strip_signature_text(text):
    """Bỏ các dòng thuộc lớp phủ chữ ký số trước khi đánh giá chất lượng."""
    out = []
    for line in text.splitlines():
        low = line.lower()
        if any(m in low for m in SIGNATURE_MARKERS):
            continue
        out.append(line)
    return "\n".join(out)


def is_usable(doc):
    """
    True nếu lớp text của tài liệu đủ tin cậy để dùng thay OCR.

    Đánh giá trên toàn tài liệu chứ không từng trang: BCTC có trang bìa và
    trang ký tên gần như trống, xét riêng lẻ sẽ trượt oan.
    """
    try:
        raw = "".join(doc[i].get_text() for i in range(doc.page_count))
    except Exception:
        return False
    text = strip_signature_text(raw)
    if len(text.strip()) < MIN_CHARS_PER_PAGE * max(1, doc.page_count) * 0.25:
        return False
    return diacritic_ratio(text) >= MIN_DIACRITIC_RATIO


def page_lines(page):
    """
    Đọc một trang thành danh sách DÒNG, cùng cấu trúc mà ocr.ocr_lines() trả về
    (phần tử thứ 3), để parser dùng chung không phải rẽ nhánh.

    page.get_text("words") trả tuple 8 phần tử:
        (x0, y0, x1, y1, text, block_no, line_no, word_no)
    """
    rect = page.rect
    W = float(rect.width) or 1.0
    H = float(rect.height) or 1.0

    nhom = {}
    for x0, y0, x1, y1, txt, block_no, line_no, _word_no in page.get_text("words"):
        t = (txt or "").strip()
        if not t:
            continue
        w, h = x1 - x0, y1 - y0
        nhom.setdefault((block_no, line_no), []).append({
            "text": t,
            "left": x0, "top": y0, "width": w, "height": h,
            "conf": 100.0,                 # lớp text: coi như chắc chắn
            "cx": (x0 + w / 2.0) / W,
            "cy": (y0 + h / 2.0) / H,
            "right": x1 / W,
            "lx": x0 / W,
        })

    out = []
    for key in sorted(nhom, key=lambda k: min(wd["top"] for wd in nhom[k])):
        out.append(sorted(nhom[key], key=lambda wd: wd["left"]))
    return out
```

- [ ] **Step 4: Chạy test để xác nhận thành công**

```bash
.venv/bin/python -m pytest tests/test_textlayer.py -v
```

Expected: PASS (7 test)

- [ ] **Step 5: Nối vào parser**

Trong `bctc/parser.py`, thêm import:

```python
from . import textlayer
```

Trong `extract()`, thay khối render + OCR song song (dòng 313-327) bằng:

```python
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

    if dung_lop_text:
        # Lớp text tin cậy -> đọc thẳng, không OCR. Chính xác tuyệt đối và gần
        # như không tốn CPU.
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
```

Đồng thời trong `_scan_strip` (dòng 242-250), dùng lớp text khi có để việc định vị cũng không phải OCR:

```python
def _scan_strip(doc, i, lang, scan_dpi):
    """OCR dải đầu 1 trang -> (i, title_key_or_None)."""
    from PIL import Image
    page = doc[i]

    if getattr(doc, "_bctc_dung_lop_text", False):
        # Có lớp text tin cậy -> lấy chữ ở dải đầu trang, khỏi OCR.
        gioi_han = page.rect.y0 + (page.rect.y1 - page.rect.y0) * 0.42
        line_texts = [" ".join(w["text"] for w in ln)
                      for ln in textlayer.page_lines(page)
                      if ln and ln[0]["top"] <= gioi_han]
        return i, heading_in_lines(line_texts)

    pix = page.get_pixmap(dpi=scan_dpi, clip=fitz_rect(page, top_frac=0.42))
    img = ocr.preprocess(Image.frombytes("RGB", (pix.width, pix.height), pix.samples))
    _, _, lines = ocr.ocr_lines(img, lang=lang, psm=6, min_conf=20)
    line_texts = [" ".join(w["text"] for w in ln) for ln in lines]
    return i, heading_in_lines(line_texts)
```

Và trong `locate_pages`, đặt cờ trước khi quét:

```python
    nw = workers or MAX_WORKERS
    try:
        doc._bctc_dung_lop_text = textlayer.is_usable(doc)
    except Exception:
        pass
    lo, hi = (page_range or (0, doc.page_count))
```

- [ ] **Step 6: Chạy toàn bộ test**

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: PASS toàn bộ

- [ ] **Step 7: Đo lại và xác nhận không có hồi quy**

```bash
.venv/bin/python -m tests.regression.run_regression --out /tmp/sau-task9.json --tier2-sample 30
.venv/bin/python -c "
import json
a=json.load(open('docs/superpowers/plans/baseline-2026-07-19.json'))
b=json.load(open('/tmp/sau-task9.json'))
print('CPU-giây : %.1f -> %.1f' % (a['tier3']['cpu'], b['tier3']['cpu']))
print('thời gian: %.1f -> %.1f' % (a['tier3']['wall'], b['tier3']['wall']))
for k in ('CDKT','KQHDKD','LCTT'):
    x,y = 100*a['tier2']['coverage_avg'][k], 100*b['tier2']['coverage_avg'][k]
    print('độ phủ %-7s %.1f%% -> %.1f%%  %s' % (k,x,y,'OK' if y>=x-1 else 'HỒI QUY!'))
print('cân đối  : %.1f%% -> %.1f%%' % (100*a['tier2']['balance_pass_rate'],
                                        100*b['tier2']['balance_pass_rate']))
"
```

Expected: CPU-giây giảm; **không dòng nào in `HỒI QUY!`**. Nếu có, dừng lại và điều tra trước khi commit.

- [ ] **Step 8: Commit**

```bash
git add bctc/textlayer.py bctc/parser.py tests/test_textlayer.py
git commit -m "feat: đọc lớp text sẵn có khi tin cậy, kèm ba bộ lọc

12,2% corpus có lớp text dùng được -> đọc thẳng, chính xác tuyệt đối và gần
như không tốn CPU. Nhưng 9,4% có lớp text MOJIBAKE trả về hàng chục nghìn ký
tự rác trông như hợp lệ, nên bắt buộc phải lọc: đủ số ký tự, tỷ lệ dấu tiếng
Việt >= 0,02, và loại lớp phủ chữ ký số trước khi đánh giá.

Ngưỡng số ký tự mới là bộ lọc quan trọng nhất trong thực tế: file Đăk Lăk 2024
có 38 trang nhưng chỉ 352 ký tự chữ ký số, mà tỷ lệ dấu vẫn đạt 0,126.

textlayer.page_lines() trả đúng cấu trúc ocr.ocr_lines() nên parser dùng chung
không phải rẽ nhánh."
```

---

# GIAI ĐOẠN 2 — ĐÓNG GÓI WINDOWS

### Task 10: Chuyển sang onedir và bỏ UPX

Nguyên nhân gốc của khởi động chậm: `pdf2excel.spec` dòng 42 truyền `a.binaries, a.datas` thẳng vào `EXE()` mà không có `COLLECT()` → chế độ onefile. Mỗi lần mở app, bootloader giải nén toàn bộ payload ra `%TEMP%\_MEIxxxx`, Defender quét lại từng DLL, chạy xong xoá — rồi lặp lại lần sau.

**Files:**
- Modify: `pdf2excel.spec:42-56`
- Test: `tests/test_spec_dong_goi.py`

**Interfaces:**
- Consumes: không có
- Produces: `dist/BCTC_PDF_to_Excel/` (thư mục) thay vì `dist/BCTC_PDF_to_Excel.exe` (file lẻ)

- [ ] **Step 1: Viết test kiểm tra cấu hình đóng gói**

Tạo `tests/test_spec_dong_goi.py`:

```python
# -*- coding: utf-8 -*-
"""Canh các quyết định đóng gói không bị vô tình đảo ngược."""
import os
import re

SPEC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "pdf2excel.spec")


def _doc_spec():
    with open(SPEC, encoding="utf-8") as fh:
        return fh.read()


def test_dung_che_do_onedir():
    """Phải có COLLECT() — onefile giải nén lại toàn bộ payload MỖI lần mở."""
    src = _doc_spec()
    assert "COLLECT(" in src, "thiếu COLLECT() -> đang là onefile"


def test_exe_khong_om_binaries():
    """EXE() chỉ nhận a.scripts; binaries/datas do COLLECT() gom."""
    src = _doc_spec()
    m = re.search(r"exe\s*=\s*EXE\((.*?)\n\)", src, re.S)
    assert m, "không tìm thấy khối EXE("
    than = m.group(1)
    assert "a.binaries" not in than, "EXE() còn ôm a.binaries -> vẫn là onefile"
    assert "a.datas" not in than, "EXE() còn ôm a.datas -> vẫn là onefile"


def test_tat_upx():
    """UPX vừa tốn thời gian giải nén vừa kích hoạt false-positive antivirus."""
    src = _doc_spec()
    assert re.search(r"upx\s*=\s*False", src), "UPX chưa tắt"
    assert not re.search(r"upx\s*=\s*True", src), "còn chỗ đặt upx=True"
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

```bash
.venv/bin/python -m pytest tests/test_spec_dong_goi.py -v
```

Expected: FAIL cả 3 test (`thiếu COLLECT()`, `EXE() còn ôm a.binaries`, `UPX chưa tắt`)

- [ ] **Step 3: Sửa `pdf2excel.spec`**

Thay toàn bộ từ dòng 42 (`exe = EXE(`) đến hết file bằng:

```python
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,         # onedir: binaries/datas do COLLECT() gom
    name="BCTC_PDF_to_Excel",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                     # UPX: tốn thời gian giải nén mỗi lần chạy
                                   # + là tác nhân kinh điển gây false-positive
                                   # antivirus trên Windows
    console=False,                 # ứng dụng cửa sổ (không hiện terminal)
    disable_windowed_traceback=False,
    argv_emulation=True,           # macOS: nhận file kéo-thả vào icon
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON_FILE,
)

# onedir: giải nén MỘT lần lúc cài đặt, các lần mở sau chạy thẳng.
# Chế độ onefile cũ giải nén lại toàn bộ payload ra %TEMP% mỗi lần khởi động,
# rồi bị Windows Defender quét lại từ đầu — trên máy Win10 ổ HDD mất 30-90
# giây MỖI LẦN MỞ.
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="BCTC_PDF_to_Excel",
)

# macOS: gói thành .app
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="BCTC_PDF_to_Excel.app",
        icon=(_icns if os.path.exists(_icns) else None),
        bundle_identifier="vn.btg.bctc.pdf2excel",
        info_plist={
            "NSHighResolutionCapable": True,
            "CFBundleDisplayName": "BCTC PDF → Excel",
        },
    )
```

- [ ] **Step 4: Chạy test để xác nhận thành công**

```bash
.venv/bin/python -m pytest tests/test_spec_dong_goi.py -v
```

Expected: PASS (3 test)

- [ ] **Step 5: Đóng gói thử để xác nhận spec chạy được**

```bash
.venv/bin/python -m pip install -q pyinstaller
.venv/bin/python -m PyInstaller --noconfirm --clean pdf2excel.spec
ls -la dist/
```

Expected: có **thư mục** `dist/BCTC_PDF_to_Excel/` (không phải file .exe lẻ) chứa file thực thi và thư mục `_internal/`.

- [ ] **Step 6: Commit**

```bash
git add pdf2excel.spec tests/test_spec_dong_goi.py
git commit -m "build: chuyển sang onedir và tắt UPX

Chế độ onefile giải nén TOÀN BỘ payload ra %TEMP%\\_MEIxxxx mỗi lần mở app,
Defender quét lại từng DLL, chạy xong xoá rồi lặp lại lần sau — trên Win10 ổ
HDD mất 30-90 giây mỗi lần khởi động. onedir giải nén một lần lúc cài.

UPX vừa tốn thời gian giải nén mỗi lần chạy vừa là tác nhân kinh điển gây
false-positive antivirus."
```

---

### Task 11: Cắt gọn Tesseract trong CI

CI hiện copy **toàn bộ** `C:\Program Files\Tesseract-OCR` bằng `-Recurse`, gồm mọi DLL và mọi gói ngôn ngữ chocolatey cài kèm. Thêm nữa `vie.traineddata` bị đóng gói **hai lần**.

**Files:**
- Modify: `.github/workflows/build.yml:31-42`
- Modify: `pdf2excel.spec:10-18` (bỏ tessdata trùng)

**Interfaces:**
- Consumes: không có
- Produces: thư mục `tesseract/` gọn, chỉ chứa file cần thiết

- [ ] **Step 1: Sửa bước gom Tesseract trong CI**

Trong `.github/workflows/build.yml`, thay toàn bộ bước `Gói kèm Tesseract-OCR` (dòng 31-42) bằng:

```yaml
      - name: Gói kèm Tesseract-OCR (bản rút gọn)
        shell: pwsh
        run: |
          choco install tesseract -y --no-progress
          $src = "C:\Program Files\Tesseract-OCR"
          if (-not (Test-Path $src)) { $src = "C:\Program Files (x86)\Tesseract-OCR" }

          New-Item -ItemType Directory -Force -Path tesseract\tessdata | Out-Null

          # Chỉ lấy file thực thi và DLL. Copy -Recurse toàn bộ thư mục sẽ kéo
          # theo mọi gói ngôn ngữ chocolatey cài kèm và thư mục tài liệu, làm
          # phình gói cài lên hàng trăm MB.
          Copy-Item "$src\tesseract.exe" -Destination tesseract -Force
          Copy-Item "$src\*.dll" -Destination tesseract -Force

          # Chỉ ba gói ngôn ngữ thực sự dùng:
          #   vie = tiếng Việt (bản đi kèm repo), eng = dự phòng, osd = dò hướng trang
          Copy-Item "tessdata\vie.traineddata" -Destination "tesseract\tessdata\" -Force
          foreach ($lang in @("eng", "osd")) {
            $f = Join-Path $src "tessdata\$lang.traineddata"
            if (Test-Path $f) { Copy-Item $f -Destination "tesseract\tessdata\" -Force }
          }

          $mb = [math]::Round((Get-ChildItem tesseract -Recurse |
                Measure-Object -Property Length -Sum).Sum / 1MB, 1)
          Write-Host "Tesseract rút gọn: $mb MB"
          Get-ChildItem tesseract -Recurse -File | Select-Object -First 30 FullName
```

- [ ] **Step 2: Bỏ tessdata trùng trong spec**

Trong `pdf2excel.spec`, sửa khối `datas` (dòng 10-18):

```python
datas = [
    ("assets", "assets"),          # icon + sprite
]

# Tesseract-OCR portable đi kèm app (nếu có thư mục 'tesseract/').
# CI Windows tạo thư mục này -> app chạy độc lập, không cần cài Tesseract.
# vie.traineddata đã nằm trong tesseract/tessdata/ nên KHÔNG đóng gói thêm
# thư mục tessdata/ ở gốc — trước đây bị gói hai lần.
if os.path.isdir("tesseract"):
    datas.append(("tesseract", "tesseract"))
else:
    # Chạy từ mã nguồn / build macOS: dùng tessdata cạnh mã nguồn.
    datas.append(("tessdata", "tessdata"))
```

- [ ] **Step 3: Xác nhận `locate_tesseract` vẫn tìm được**

`bctc/ocr.py` dòng 73-83 ưu tiên `tessdata` nằm cạnh `tesseract`, sau đó mới tới `base/tessdata`. Cấu trúc mới vẫn khớp nhánh thứ nhất. Kiểm tra:

```bash
.venv/bin/python -c "
from bctc import ocr
t, td = ocr.locate_tesseract()
print('tesseract:', t)
print('tessdata :', td)
assert t, 'không tìm thấy tesseract'
"
```

Expected: in ra đường dẫn tesseract và tessdata hợp lệ.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/build.yml pdf2excel.spec
git commit -m "build: cắt gọn Tesseract, bỏ tessdata bị đóng gói hai lần

CI copy toàn bộ thư mục Tesseract bằng -Recurse, kéo theo mọi gói ngôn ngữ
chocolatey cài kèm và thư mục tài liệu. Giờ chỉ lấy tesseract.exe, các DLL,
và ba gói vie/eng/osd.

vie.traineddata trước đây nằm cả trong datas của spec lẫn trong thư mục
tesseract do CI tạo — đóng gói hai lần."
```

---

### Task 12: Bộ cài Inno Setup

**Files:**
- Create: `installer/BCTC_Setup.iss`
- Modify: `.github/workflows/build.yml` (bước đóng gói + upload)

**Interfaces:**
- Consumes: `dist/BCTC_PDF_to_Excel/` (Task 10)
- Produces: `installer/Output/BCTC_PDF_to_Excel-Setup.exe`

- [ ] **Step 1: Tạo kịch bản Inno Setup**

Tạo `installer/BCTC_Setup.iss`:

```iss
; Bộ cài Windows cho BCTC PDF -> Excel
; Dựng bằng: iscc installer\BCTC_Setup.iss
;
; Vì sao cần bộ cài: bản onedir giải nén MỘT lần lúc cài, các lần mở sau chạy
; thẳng (~2 giây). Bản onefile cũ giải nén lại toàn bộ payload ra %TEMP% mỗi
; lần khởi động - trên Win10 ổ HDD mất 30-90 giây MỖI LẦN.

#define AppName "BCTC PDF to Excel"
#define AppExe "BCTC_PDF_to_Excel.exe"
#define AppPublisher "BTG"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\BCTC_PDF_to_Excel
DefaultGroupName={#AppName}
OutputDir=Output
OutputBaseFilename=BCTC_PDF_to_Excel-Setup
Compression=lzma2/max
SolidCompression=yes
; Cài cho riêng người dùng nếu không có quyền admin - máy văn phòng thường
; bị khoá quyền cài đặt.
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#AppExe}

[Languages]
Name: "vietnamese"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Tao bieu tuong tren man hinh nen"; \
    GroupDescription: "Tuy chon:"

[Files]
Source: "..\dist\BCTC_PDF_to_Excel\*"; DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Go cai dat {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Mo ung dung ngay"; \
    Flags: nowait postinstall skipifsilent
```

- [ ] **Step 2: Thêm bước dựng bộ cài vào CI**

Trong `.github/workflows/build.yml`, thay bước `Đổi tên & gom` và bước `upload-artifact` của job `windows` bằng:

```yaml
      - name: Đọc số phiên bản
        id: ver
        shell: pwsh
        run: |
          $v = (Select-String -Path version.py -Pattern '__version__\s*=\s*"([^"]+)"').Matches[0].Groups[1].Value
          "version=$v" | Out-File -FilePath $env:GITHUB_OUTPUT -Append
          Write-Host "Phiên bản: $v"

      - name: Dựng bộ cài (Inno Setup)
        shell: pwsh
        run: |
          choco install innosetup -y --no-progress
          & "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" `
            "/DAppVersion=${{ steps.ver.outputs.version }}" `
            installer\BCTC_Setup.iss
          Get-ChildItem installer\Output

      - uses: actions/upload-artifact@v4
        with:
          name: BCTC_PDF_to_Excel-windows-setup
          path: installer/Output/BCTC_PDF_to_Excel-Setup.exe

      - name: Đính kèm Release (khi push tag v*)
        if: startsWith(github.ref, 'refs/tags/v')
        uses: softprops/action-gh-release@v2
        with:
          files: installer/Output/BCTC_PDF_to_Excel-Setup.exe
```

- [ ] **Step 3: Kiểm tra cú pháp YAML**

```bash
.venv/bin/python -c "
import sys
try:
    import yaml
except ImportError:
    sys.exit('bỏ qua: chưa cài pyyaml')
d = yaml.safe_load(open('.github/workflows/build.yml', encoding='utf-8'))
steps = d['jobs']['windows']['steps']
names = [s.get('name') or s.get('uses') for s in steps]
print('\n'.join('  %d. %s' % (i+1, n) for i, n in enumerate(names)))
assert any('Inno Setup' in (n or '') for n in names), 'thiếu bước dựng bộ cài'
print('YAML hợp lệ')
"
```

Expected: liệt kê các bước và in `YAML hợp lệ` (hoặc bỏ qua nếu chưa có pyyaml — cài bằng `.venv/bin/python -m pip install pyyaml`)

- [ ] **Step 4: Commit**

```bash
git add installer/ .github/workflows/build.yml
git commit -m "build: bộ cài Inno Setup cho Windows

Bản onedir cần bộ cài để giải nén một lần lúc cài đặt. Bộ cài cho phép chọn
cài theo người dùng khi không có quyền admin - máy văn phòng thường bị khoá."
```

---

### Task 13: Hoãn import nặng và thêm splash

`app.py` dòng 29 `from bctc import engine, ocr` kéo theo `fitz`, `pytesseract`, `PIL` ngay lúc khởi động (`ocr.py` dòng 29-31), chặn việc vẽ cửa sổ.

**Files:**
- Modify: `app.py:29`, `app.py:1267` (`_worker`), `app.py:1001`
- Test: `tests/test_khoi_dong.py`

**Interfaces:**
- Consumes: không có
- Produces: `app.MAX_FILES` giữ nguyên giá trị 150 mà không cần import `engine` lúc khởi động

- [ ] **Step 1: Viết test thất bại**

Tạo `tests/test_khoi_dong.py`:

```python
# -*- coding: utf-8 -*-
"""app.py không được kéo theo thư viện nặng lúc import."""
import re
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NANG = ("fitz", "pymupdf", "pytesseract", "PIL")


def test_import_app_khong_keo_theo_thu_vien_nang():
    ma = (
        "import sys; sys.argv=['app'];"
        "import importlib; importlib.import_module('app');"
        "print(','.join(sorted(m for m in sys.modules if m.split('.')[0] in %r)))"
        % (NANG,)
    )
    r = subprocess.run([sys.executable, "-c", ma], cwd=ROOT,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stderr
    nap = [m for m in r.stdout.strip().split(",") if m]
    assert not nap, "app.py kéo theo thư viện nặng lúc import: %s" % nap


def test_max_files_van_dung_150():
    src = open(os.path.join(ROOT, "app.py"), encoding="utf-8").read()
    assert re.search(r"^MAX_FILES\s*=\s*150", src, re.M), \
        "MAX_FILES phải là hằng số 150, không lấy từ engine lúc import"
```

- [ ] **Step 2: Chạy test để xác nhận thất bại**

```bash
.venv/bin/python -m pytest tests/test_khoi_dong.py -v
```

Expected: FAIL — liệt kê `fitz`, `PIL`, `pytesseract` bị nạp

- [ ] **Step 3: Hoãn import trong app.py**

Trong `app.py`, thay dòng 27-33:

```python
# cho phép chạy trực tiếp lẫn sau khi đóng gói
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from version import __version__ as APP_VERSION   # noqa: E402

# CỐ Ý KHÔNG import bctc.engine / bctc.ocr ở đây: chúng kéo theo fitz,
# pytesseract và PIL (hàng chục MB) khiến cửa sổ chậm hiện ra. Nạp lười trong
# _engine() ngay trước lúc thực sự cần.
_ENGINE = None
_OCR = None


def _engine():
    """Nạp lười lõi xử lý. Gọi từ luồng nền, không gọi lúc dựng giao diện."""
    global _ENGINE, _OCR
    if _ENGINE is None:
        from bctc import engine as _e, ocr as _o
        _ENGINE, _OCR = _e, _o
    return _ENGINE


def _ocr_mod():
    if _OCR is None:
        _engine()
    return _OCR


APP_TITLE = "BCTC PDF → Excel  •  Thông tư 200  •  v" + APP_VERSION
MAX_FILES = 150          # giữ đồng bộ với bctc.engine.MAX_FILES
```

- [ ] **Step 4: Sửa các chỗ dùng `engine` và `ocr`**

Tại dòng ~1001 (trong `_log_diagnostics`), thay `ocr.configure_tesseract()`:

```python
            _ocr_mod().configure_tesseract()
```

Trong `_worker` (dòng ~1267), thay lời gọi `engine.convert_many(...)`:

```python
            _engine().convert_many(
                files, out_dir, lang="vie", dpis=dpis, log=log, progress=prog,
```

Tìm mọi chỗ còn lại tham chiếu `engine.` hoặc `ocr.` ở phạm vi module và đổi sang `_engine().` / `_ocr_mod().`:

```bash
grep -n "\bengine\.\|\bocr\." app.py
```

Xử lý hết các dòng in ra (trừ dòng nằm trong hàm `_engine`/`_ocr_mod`).

- [ ] **Step 5: Thêm splash vào spec**

Trong `pdf2excel.spec`, thêm ngay sau dòng `pyz = PYZ(a.pure)`:

```python
# Splash: phản hồi thị giác ngay khi bấm mở, trong lúc Python + thư viện nạp.
# Chỉ hỗ trợ trên Windows/Linux (PyInstaller chưa hỗ trợ splash trên macOS).
_splash_img = os.path.join("assets", "icon_256.png")
splash = None
if sys.platform != "darwin" and os.path.exists(_splash_img):
    splash = Splash(
        _splash_img,
        binaries=a.binaries,
        datas=a.datas,
        text_pos=(10, 240),
        text_size=10,
        text_color="black",
    )
```

Rồi sửa `EXE(...)` và `COLLECT(...)` để nhận splash:

```python
_exe_args = [pyz, a.scripts]
if splash is not None:
    _exe_args.append(splash)
_exe_args.append([])

exe = EXE(
    *_exe_args,
    exclude_binaries=True,
```

```python
_coll_args = [exe]
if splash is not None:
    _coll_args.append(splash.binaries)
_coll_args += [a.binaries, a.datas]

coll = COLLECT(
    *_coll_args,
    strip=False,
```

Và trong `app.py`, tắt splash ngay khi cửa sổ hiện — thêm vào `App.__init__` ngay trước `self.deiconify()` (dòng ~671):

```python
        # Tắt splash của PyInstaller (nếu có) ngay khi giao diện sẵn sàng.
        try:
            import pyi_splash          # chỉ tồn tại trong bản đóng gói
            pyi_splash.close()
        except Exception:
            pass
        self.deiconify()
```

- [ ] **Step 6: Chạy test để xác nhận thành công**

```bash
.venv/bin/python -m pytest tests/test_khoi_dong.py -v
```

Expected: PASS (2 test)

- [ ] **Step 7: Chạy toàn bộ test và mở thử app**

```bash
.venv/bin/python -m pytest tests/ -v
.venv/bin/python app.py     # cửa sổ phải hiện lên bình thường; đóng lại
```

Expected: test PASS toàn bộ; cửa sổ mở được và chức năng chuyển đổi vẫn chạy.

- [ ] **Step 8: Commit**

```bash
git add app.py pdf2excel.spec tests/test_khoi_dong.py
git commit -m "perf: hoãn import thư viện nặng, thêm splash lúc khởi động

app.py import bctc.engine ở phạm vi module, kéo theo fitz + pytesseract + PIL
(hàng chục MB) trước khi vẽ được cửa sổ. Giờ nạp lười ngay trước lúc thực sự
cần, nên cửa sổ hiện gần như tức thì.

Splash cho phản hồi thị giác ngay khi bấm mở. PyInstaller chưa hỗ trợ splash
trên macOS nên chỉ bật ở Windows/Linux."
```

---

### Task 14: Đo tổng kết Đợt 1 và chốt kết quả

**Files:**
- Create: `docs/superpowers/plans/ket-qua-dot-1.md`

**Interfaces:**
- Consumes: toàn bộ Task 1-13

- [ ] **Step 1: Chạy bộ hồi quy đầy đủ**

```bash
.venv/bin/python -m tests.regression.run_regression \
    --out docs/superpowers/plans/sau-dot-1.json --tier2-sample 300
```

Expected: hoàn tất, in bảng TÓM TẮT.

- [ ] **Step 2: So sánh với baseline**

```bash
.venv/bin/python -c "
import json
a=json.load(open('docs/superpowers/plans/baseline-2026-07-19.json'))
b=json.load(open('docs/superpowers/plans/sau-dot-1.json'))
print('%-22s %10s %10s %10s' % ('Chỉ số','Trước','Sau','Thay đổi'))
def d(ten, x, y, don=''):
    ch = '—' if not x else '%+.0f%%' % (100*(y-x)/x)
    print('%-22s %10.1f %10.1f %10s' % (ten+don, x, y, ch))
d('CPU-giây', a['tier3']['cpu'], b['tier3']['cpu'])
d('Thời gian thực (s)', a['tier3']['wall'], b['tier3']['wall'])
d('RSS đỉnh (MB)', a['tier3']['peak_rss_mb'], b['tier3']['peak_rss_mb'])
for k in ('CDKT','KQHDKD','LCTT'):
    d('Độ phủ '+k+' (%)', 100*a['tier2']['coverage_avg'][k],
                          100*b['tier2']['coverage_avg'][k])
d('Cân đối đạt (%)', 100*a['tier2']['balance_pass_rate'],
                     100*b['tier2']['balance_pass_rate'])
if 'tier1' in a and 'tier1' in b:
    for k in ('dung','sot','lech','thua'):
        d('Tầng 1 '+k, a['tier1']['total'][k], b['tier1']['total'][k])
"
```

- [ ] **Step 3: Đo thời gian khởi động trên Windows**

Trên máy Windows 10 thật (hoặc máy ảo 4 GB RAM):

1. Cài bản `BCTC_PDF_to_Excel-Setup.exe` từ artifact CI.
2. Khởi động lại máy (để cache đĩa sạch, đúng điều kiện "mở nguội").
3. Bấm mở app, bấm đồng hồ từ lúc bấm tới lúc cửa sổ hiện đủ. Lặp 3 lần, lấy trung vị.

Ghi lại con số. **Tiêu chí G3: ≤ 3 giây.**

- [ ] **Step 4: Viết báo cáo kết quả**

Tạo `docs/superpowers/plans/ket-qua-dot-1.md` với: bảng so sánh từ Step 2, số đo khởi động từ Step 3, đối chiếu từng tiêu chí G3/G4/G5 đạt hay không, và ghi nhận baseline G1/G2 để Đợt 2 dùng.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/plans/
git commit -m "docs: kết quả đo Đợt 1"
```

---

## Tự rà soát kế hoạch

**Phủ spec:** GĐ0 §4.1→Task 1, §4.2→Task 1, §4.3→Task 2, §4.4→Task 3, §4.5 tầng 1/2→Task 3, tầng 3→Task 4, bộ chạy→Task 5. GĐ1 §5.1→Task 6, §5.2→Task 8, §5.3→Task 7, §5.4→Task 9. GĐ2 §6.2 mục 1-2→Task 10, mục 3→Task 11, mục 4→Task 12, mục 5-6→Task 13. §6.3 (SmartScreen) là ghi nhận thương mại, không có task — đúng chủ ý.

**Chưa phủ, chuyển sang Đợt 2:** toàn bộ §7 và §8, đúng như phân đợt ở spec §2.1.

**Nhất quán kiểu:** `worker_count(mode, logical)` dùng thống nhất ở Task 7 và 9. `textlayer.page_lines()` trả cùng cấu trúc `ocr.ocr_lines()[2]`, đã có test canh (Task 9 Step 1). `engine.convert_pdf` trả thêm khoá `results` ở Task 5 Step 2, được Task 8 (`_luu_ban_sao`) và Task 5 (`run_tier1`) dùng lại — nhất quán.

**Phụ thuộc giữa task:** Task 5 phải xong trước Task 6-9 (cần baseline để so). Task 8 phụ thuộc Task 5 Step 2 (khoá `results`). Task 10 phải xong trước Task 12 (bộ cài cần thư mục onedir). Task 13 Step 5 sửa cùng file `pdf2excel.spec` với Task 10 và 11 — làm tuần tự để tránh xung đột.
