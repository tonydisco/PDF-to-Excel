# Chẩn đoán "lệch dữ liệu" — 85 file CĐKT bóc được số nhưng SAI cân đối

Ngày 2026-07-25. Chẩn đoán READ-ONLY (không sửa `bctc/`, `tests/`). Nguồn tham
chiếu DUY NHẤT: file `.pdf` dưới `BTG document/`. Tín hiệu chất lượng tự chứa:
balance check của `engine._check_balance` (không dùng đáp án ngoài).

Mục tiêu: tìm MỘT fix thuật toán giá trị cao nhất để kéo nhóm "đọc-được-nhưng-sai"
(85 file, 28% của sweep n=300) về "cân đối đạt".

---

## 1. Nhóm mục tiêu & phương pháp

**Rổ 85 file** = từ `sweep-300-cuoi-dot-2.json` (`tier2.per_file`), lọc
`balance FAIL` (passed < total) và `coverage.CDKT ≥ 0.2` → **84 file** (khớp
"85 / 28%"). Phân tầng độ nặng (passed/total): **near-miss (≥0.66) 37 · mid 15 ·
catastrophic 32**. File "hợp nhất" trong rổ: 13–15 (near-miss: 6).

**Balance check** (tái lập nguyên văn): `results["CDKT"] = {mã: (cuối, đầu)}`;
mỗi cột năm chấm `270=440`, `100+200=270`, `300+400=440` (chỉ khi đủ toán hạng).

**Mẫu phân tầng n=30** trải 2007→2025, đủ 9 thư mục BCTC, đủ 18 nhóm (passed,total).
Chạy `parser.extract_consensus(dpis=(180,235))`, tái lập check, ghi 2 vế mỗi phép
fail. **Live balance khớp sweep gần tuyệt đối** (chỉ 1 file trôi do OCR variance)
→ tái lập tốt, kết luận đáng tin.

---

## 2. Bản đồ cơ chế (đếm trên mẫu, đã soi PDF xác minh)

### Định vị: vế NGUỒN VỐN sai áp đảo
Trên 45 cột-năm lỗi: phép `300+400=440` fail **31/45 (69%)**; quy về **một mình vế
nợ/vốn chủ (300/400/440): 24 cột**, vế tài sản (100/200/270): 10, cả hai: 7.
→ Điểm sai tập trung ở **tam giác 300 / 400 / 440**.

### Đếm theo cột-năm lỗi (n=45)
| Cơ chế | Cột | % | Tự sửa từ PDF? |
|---|---:|---:|---|
| **DIGIT** — sai 1 chữ số OCR ở 1 ô | 10 | 22% | ✅ re-OCR (mục 4) |
| **MINORITY/template** — hợp nhất, check thiếu dòng thiểu số | 8 | 18% | ✅ sửa công thức |
| **COLUMN/STRUCTURE** — mã đọc nhầm, rò nhãn, đảo dấu, rác | ~12 | ~27% | ✗ cần fix cấu trúc |
| **MULTI/OTHER** — nhiều chữ số bất quy tắc | ~15 | ~33% | một phần |

### Đếm theo FILE (n=30) — file "cân đối trở lại" nếu sửa hết cột lỗi
- **DIGIT_FIXABLE** (re-OCR 1 ô là cả file cân): **5** (17%)
- **MINORITY_FIXABLE** (sửa công thức thiểu số): **4** (13%)
- **HARD**: **21** (70%) — trong đó **5 file** có 1 cột DIGIT + 1 cột MULTI
  (re-OCR sửa được 1 phần, chưa flip hẳn)

---

## 3. Ví dụ từng rổ (2 vế thật của phép fail)

### DIGIT — sai 1 chữ số, target chốt bằng tam giác
- **01 DVTH Saigon (đầu năm):** `100+200 = 1.477.189.234.752` vs `270 =
  1.477.189.834.752` (lệch 600 triệu). `270=440=300+400` xác nhận 270 đúng ⇒ ô
  **100** sai: đọc …172.125.**1**35.754, đúng là …**7**35.754 (1↔7).
- **B1.3 (đầu năm):** `300+400 = 348.454.517.927` vs `440 = 348.454.517.027`
  (ô **440** lệch 900).
- **32 Lidovit (cuối):** ô **200** = 40.586.123.955, đúng 49.586.123.955 (0↔9, 9 tỷ).

### MINORITY — hợp nhất mẫu cũ (QĐ15): SỐ ĐÚNG, CHECK SAI
Bất biến đúng là `440 = 300 + 400 + [Lợi ích cổ đông thiểu số]`, nhưng check chỉ
có `300+400=440`. Độ lệch Δ = 440 − (300+400) **đúng bằng dòng thiểu số** (soi PDF):

| File | Δ (cuối / đầu) | Dòng "Lợi ích cổ đông thiểu số" trong PDF | Khớp |
|---|---|---|---|
| SVC 2007 | 45.650.892.992 / 20.379.802.256 | "LỢI ÍCH CỔ ĐÔNG THIẾU SỐ" | ✅ tuyệt đối |
| 20 SVC 2010 | 147.408.918.927 / 106.301.838.442 | mã 439 | ✅ |
| 33 Khanh Hoi Q1.2011 | 11.871.846.978 / 11.786.047.630 | mã 500 (tổng ghi mã 600) | ✅ |
| 25 Khanh Hoi 2012 | 9.872.658.293 / 12.359.477.640 | "C. LỢI ÍCH CỔ ĐÔNG THIỂU SỐ" | ✅ (±1) |

→ Đây là **cờ báo giả**: số bóc ra đúng từng đồng, chỉ do check bỏ sót dòng thiểu số.

### COLUMN/STRUCTURE — bắt nhầm ô/cột
- **11 Plaza 2011:** trang tài sản in "TÀI SẢN NGẮN HẠN **100** …72.424.457.906"
  nhưng OCR đọc mã thành "**400**" ⇒ tổng Vốn chủ (400) nhận nhầm 72.4 tỷ; 400 thật
  (430.6 tỷ) nằm ở dòng 410. Δ ~358 tỷ.
- **06 Phu Nhuan 2015 (riêng):** y hệt "100"→"400", 400 = 165.542.988.085 (thực ra
  là tài sản ngắn hạn).
- **10 O to Bac Au 2017:** nhãn "(440 = 300 + 400)" rò 1 chữ số "4" vào giá trị ⇒
  440 = 493.778.149.891 thay vì 93.778.149.891; cột kia 440 = 143.750.000 (rác).
- **04 Hoc Mon (cuối):** 440 đọc = **440** (đọc nhầm chính con số MÃ thành giá trị);
  270 = 2.9 tỷ (rác).

### MULTI/OTHER — nhiều chữ số bất quy tắc
- **26 BCTC 2013 (cuối):** `300+400 = …416.515` vs `440 = …416.552` (Δ 37, 2 chữ số
  đuôi — re-OCR nhiều khả năng cứu, nhưng không phải 1-chữ-số).
- **06 Phu Nhuan cty con 2013:** hợp nhất + 300 (178→478) & 400 (84.5→81.5) bị OCR
  mangle ⇒ compound; MI-check một mình KHÔNG cứu.

---

## 4. Câu hỏi mấu chốt: DIGIT có tự sửa bằng re-OCR không? — CÓ (4/4)

Với mỗi ô DIGIT: định vị dòng mã trên trang CĐKT, **render RIÊNG dải dòng đó ở dpi
300 & 400, OCR whitelist chữ-số** (`parser.DIGIT_WHITELIST`), so với target tam giác.

| File | Ô (cột) | OCR chính (SAI) | Re-OCR dpi 300/400 | Target | Khớp |
|---|---|---|---|---|---|
| 01 DVTH Saigon | 100 (đầu) | 172.125.**1**35.754 | 172.125.**7**35.754 | 172.125.735.754 | ✅ |
| 10 quy3 2015 | 100 (đầu) | 503.336.801.**0**29 | 503.336.801.**9**29 | …929 | ✅ |
| 32 Lidovit | 200 (cuối) | **4**0.586.123.955 | **49**.586.123.955 | 49.586.123.955 | ✅ |
| B1.3 | 440 (đầu) | 348.454.517.**0**27 | 348.454.517.**9**27 | …927 | ✅ |

**4/4 khôi phục đúng target ⇒ cân đối trở lại.** OCR toàn-trang lượt chính (dpi
180/235) sai 1 chữ số; render lại RIÊNG dòng ở dpi cao + whitelist đọc đúng. Vì
balance check đã biết target (tam giác từ 2 phép còn lại), có thể **GATE**: chỉ nhận
số đọc lại nếu == target ⇒ **không có rủi ro "ép cân" che lỗi thật**. Đây chính là
việc biến balance check từ cờ báo thụ động thành **cơ chế TỰ SỬA PDL-only**.

---

## 5. Ngoại suy ra 85 file (phân tầng near/mid/cat)

Tỷ lệ flip cả-file theo tầng (mẫu) × cỡ tầng của 84:

| Fix | near (37) | mid (15) | cat (32) | Tổng |
|---|---|---|---|---|
| DIGIT re-OCR | 0.33×37 ≈ 12 | 0.12×15 ≈ 2 | 0 | **~14** (12–16) |
| MINORITY check | — | — | — | **~6** (5–9, trần theo census 6 file HN near-miss) |

- **DIGIT re-OCR ~14 file** flip hẳn + ~5 file được sửa 1 phần.
- **MINORITY ~6 file** (số vốn đã đúng; census file "hợp nhất" near-miss = 6 là trần
  thực; ngoại suy tầng cho 12 nhưng lệch do mẫu cố ý lấy file hợp nhất).

---

## 6. KHUYẾN NGHỊ — fix giá trị cao nhất

### 🥇 #1 — RE-OCR TỰ SỬA Ô LỆCH 1-CHỮ-SỐ (balance check làm oracle). Kỳ vọng: **~14/85 file**.
Khi 1 phép cân đối fail mà **tam giác chốt được target ở ĐÚNG 1 ô** và độ lệch có
dạng 1-chữ-số (thay/mất/thêm 1 chữ số hoặc đảo 2 chữ số kề):
1. Định vị dòng của ô nghi ngờ trên trang CĐKT (đã có `detect_code_column` +
   `find_code_at`; đã có bbox dòng từ `ocr.ocr_lines`).
2. Render **RIÊNG dải dòng đó ở dpi 300–400**, OCR **whitelist chữ-số**
   (`DIGIT_WHITELIST` đã có sẵn — hạ tầng B-A3 mà mã nguồn đã ghi chú để dành).
3. **CHỈ nhận** số đọc lại nếu bằng target tam giác (gate an toàn, không ép cân).

Vì sao #1: (a) đúng trọng tâm "lệch data" — sửa số SAI thật; (b) đã chứng minh
**4/4 tự sửa được** từ PDF; (c) rủi ro thấp nhờ gate bằng target; (d) tái dùng hạ
tầng có sẵn (whitelist, bbox dòng, tam giác) — không cần model mới; (e) còn cải thiện
1 phần ~5 file HARD (mỗi file có 1 cột DIGIT).

### 🥈 #2 — CHECK NHẬN BIẾT LỢI ÍCH CỔ ĐÔNG THIỂU SỐ. Kỳ vọng: **~6/85 file**.
Với báo cáo **hợp nhất mẫu cũ (QĐ15)**, đổi bất biến vế nguồn vốn thành
`300 + 400 + [dòng "Lợi ích cổ đông thiểu số"] = 440` (dòng thiểu số hay mang mã
439/500). Rẻ, tất định, không tốn OCR. **Lưu ý**: đây là sửa CÔNG THỨC KIỂM TRA
(số đã đúng), không phải sửa "lệch data" — nó xóa **cờ báo giả** chứ không sửa số.
Nên làm song song #1 vì bổ trợ, không chồng lấn.

### Ngoài phạm vi 1-fix (ghi nhận cho đợt sau)
COLUMN/STRUCTURE (mã "100"→"400", rò nhãn "(440=300+400)", đảo dấu, bắt nhầm mã làm
giá trị) chiếm ~27% cột lỗi và ngự trị nhóm catastrophic (0/x) — cần xử lý riêng
(khử nhiễu cột mã, chặn token nhãn/công thức lọt vào giá trị), KHÔNG tự sửa bằng
re-OCR 1 ô.

---

## 7. Tóm tắt số liệu
- Rổ mục tiêu: **84 file** (near 37 / mid 15 / cat 32); vế nguồn vốn (300/400/440)
  sai ở **69%** cột lỗi.
- Cột-năm lỗi (n=45): DIGIT 10 · MINORITY 8 · STRUCTURE ~12 · MULTI ~15.
- File (n=30): DIGIT_FIXABLE 5 · MINORITY_FIXABLE 4 · HARD 21.
- **Fix #1 (re-OCR tự sửa 1-chữ-số): ~14/85 file; DIGIT tự sửa được — 4/4 spot-check.**
- Fix #2 (check thiểu số): ~6/85 file (số vốn đã đúng, xóa cờ báo giả).
